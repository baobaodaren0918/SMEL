"""
Layer 3 Validation: Text-level diff between FE-exported native and the
project's hand-written ground-truth native file, with set-based normalization.

Pipeline position:
  Meta V2 -> [Adapter FE] -> exported native text
                                    |
                                    +-- compare with native ground-truth file
                                        (same shape Layer 1 / Layer 2 use)

What "set-based" means here
---------------------------
Schema equivalence is set-equivalence, not text-equivalence:

  * JSON Schema spec (draft 2020-12 6.5.3) defines ``required`` as a set
    (elements MUST be unique).
  * Codd's relational model treats tables as unordered sets of attributes.
  * Mainstream schema-diff tools (Liquibase, Flyway, Atlas, apgdiff, ...)
    all ignore textual ordering and compare at the element level.

Layer 3 therefore strips formatting noise (header comments, blank lines,
keyword case) AND treats table order, column order within a table, and
JSON object/array ordering as *non-differences*. What remains is the
schema's structural content.

Layer 3 vs Layer 1 / Layer 2
----------------------------
* Layer 1 (validate_meta):   M_V2 == parse(native_target)?  -- PIM equivalence
* Layer 2 (validate_export): parse(export(M_V2)) == parse(native_target)?
                                -- adapter round-trip
* Layer 3 (validate_text_diff): export(M_V2) ~set~ native_target?
                                -- exporter style alignment with the
                                   project's chosen native style

Layer 1 / Layer 2 can pass while Layer 3 fails -- that surfaces a
PSM-style drift between adapter output and the project's hand-written
ground truth (e.g. the adapter writes precision constraints the ground
truth omits, or uses an executable form where the ground truth uses a
comment form).
"""
from typing import Any, Dict, List
import difflib
import json
import re

from config import (
    SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT,
    SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR,
)


# ---------------------------------------------------------------------------
# Per-paradigm normalizers
# ---------------------------------------------------------------------------

# Mongo / JSON Schema: title and description are descriptive metadata not
# part of the schema's structural content; sort_keys handles object member
# order, the ``required`` array order, and collection order.
_JSON_NOISE_KEYS = ("title", "description", "$schema", "version")


def _normalize_json(text: str) -> str:
    obj = json.loads(text)

    def walk(o: Any) -> None:
        if isinstance(o, dict):
            for k in _JSON_NOISE_KEYS:
                o.pop(k, None)
            # JSON Schema ``required`` is a set (spec 6.5.3: elements MUST be
            # unique), so its element order carries no semantics. ``sort_keys``
            # only sorts dict keys, not array contents -- we sort it here.
            req = o.get("required")
            if isinstance(req, list) and all(isinstance(x, str) for x in req):
                o["required"] = sorted(req)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return json.dumps(obj, sort_keys=True, indent=2)


def _split_top_level(s: str) -> List[str]:
    """Split a comma-separated string but ignore commas inside parentheses
    (so ``PRIMARY KEY ((a, b), c)`` stays as a single chunk)."""
    parts: List[str] = []
    depth = 0
    cur: List[str] = []
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def _normalize_sql_like(text: str, comment_prefix: str) -> str:
    """SQL / CQL: strip comments and blank lines, lowercase keywords, then
    parse each ``CREATE TABLE`` statement and sort its column / constraint
    list. Tables are emitted in alphabetical order. The result is a
    deterministic string that captures *what* a schema declares, not in
    *what order* the file declares it."""
    # 1. Strip line comments + blank lines, collapse whitespace.
    cleaned: List[str] = []
    for raw in text.splitlines():
        i = raw.find(comment_prefix)
        if i >= 0:
            raw = raw[:i]
        s = raw.strip()
        if s:
            cleaned.append(s)
    flat = " ".join(cleaned)
    # Collapse runs of whitespace introduced by joining.
    flat = re.sub(r"\s+", " ", flat)

    # 2. Split on ';' to separate statements.
    statements: List[str] = []
    for stmt in flat.split(";"):
        s = stmt.strip()
        if not s:
            continue
        # Lowercase keywords (rough but sufficient for diff).
        s = re.sub(
            r"\b(CREATE|TABLE|PRIMARY|KEY|FOREIGN|REFERENCES|NOT|NULL|"
            r"VARCHAR|INT|INTEGER|TEXT|DATE|TIMESTAMP|BOOLEAN|NUMERIC|"
            r"DECIMAL|SERIAL|BIGINT|UNIQUE|CHECK|DEFAULT|WITH|ON|"
            r"DELETE|UPDATE|CASCADE|CONSTRAINT|INDEX|DOUBLE|PRECISION|"
            r"PARTITION|CLUSTERING|ORDER|BY|ASC|DESC)\b",
            lambda m: m.group(0).lower(),
            s,
            flags=re.IGNORECASE,
        )
        # 3. For CREATE TABLE statements: parse out (name, body) and sort body.
        m = re.match(r"create\s+table\s+(\w+)\s*\((.*)\)\s*$", s, re.DOTALL)
        if m:
            name = m.group(1)
            body = m.group(2)
            cols = [c.strip() for c in _split_top_level(body) if c.strip()]
            cols_sorted = sorted(cols)
            s = f"create table {name} ({', '.join(cols_sorted)})"
        statements.append(s)

    # 4. Sort statements (tables) alphabetically.
    return "\n".join(sorted(statements))


def _normalize_cypher(text: str) -> str:
    """Cypher: split into ``// Node:`` and ``// Relationship:`` blocks,
    lowercase, sort the ``// Properties:`` list inside each block, then sort
    blocks themselves. Header comments and blank lines are stripped."""
    blocks: List[List[str]] = []
    cur: List[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("// Node:") or s.startswith("// Relationship:"):
            if cur:
                blocks.append(cur)
                cur = []
        cur.append(s)
    if cur:
        blocks.append(cur)
    # Drop any "preamble" block that is not anchored to a Node / Relationship
    # heading -- those are file-level header comments.
    blocks = [b for b in blocks
              if b and (b[0].startswith("// Node:") or b[0].startswith("// Relationship:"))]

    # Cardinality lines are descriptive comments in Cypher (the language
    # itself does not enforce cardinality), and the project's native files
    # use a different documentation phrasing than the FE
    # ("// Per X: 0..n Y; per Y: 0..n X" vs "// Cardinality: 0..n"). Both
    # are stylistic choices that carry no structural information beyond the
    # relationship's existence and direction, so Layer 3 ignores them.
    _CARD_RE = re.compile(r"^//\s*(cardinality|per\s+\w+):", re.IGNORECASE)

    normalized: List[str] = []
    for blk in blocks:
        out: List[str] = []
        for l in blk:
            s = re.sub(r"\s+", " ", l).lower()
            if _CARD_RE.match(s):
                continue
            m = re.match(r"^//\s*properties:\s*(.+)$", s)
            if m:
                items = sorted(p.strip() for p in m.group(1).split(","))
                s = f"// properties: {', '.join(items)}"
            out.append(s)
        normalized.append("\n".join(out))
    return "\n\n".join(sorted(normalized))


_NORMALIZERS = {
    SOURCE_TYPE_DOCUMENT:   _normalize_json,
    SOURCE_TYPE_RELATIONAL: lambda t: _normalize_sql_like(t, "--"),
    SOURCE_TYPE_COLUMNAR:   lambda t: _normalize_sql_like(t, "--"),
    SOURCE_TYPE_GRAPH:      _normalize_cypher,
}


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def validate_text_diff(result_dict: Dict[str, Any], target_type: str,
                       config_key: str = "") -> Dict[str, Any]:
    """
    Layer 3: Compare FE-exported native text against the project's
    hand-written ground-truth native file under set-based normalization.

    Returns the same shape as Layer 1 / Layer 2: ``{passed, summary, details}``.
    ``passed=None`` means the layer was not evaluated (no target file or no
    normalizer for the target type) -- treated as ``unverifiable`` upstream.
    """
    from validation.meta import _resolve_target_file

    exported = result_dict.get("exported_target", "")
    if not exported:
        return {"passed": False, "summary": "FAIL (no exported target)", "details": {}}

    target_file = _resolve_target_file(config_key, target_type)
    if not target_file:
        return {"passed": None,
                "summary": f"Other reasons (no target file for {config_key})",
                "details": {}}

    normalizer = _NORMALIZERS.get(target_type)
    if normalizer is None:
        return {"passed": None,
                "summary": f"Other reasons (no Layer 3 normalizer for {target_type})",
                "details": {}}

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            native = f.read()
    except OSError as e:
        return {"passed": False, "summary": f"FAIL (cannot read {target_file}: {e})",
                "details": {}}

    try:
        n_exported = normalizer(exported)
        n_native = normalizer(native)
    except Exception as e:
        return {"passed": False,
                "summary": f"FAIL (normalization error: {type(e).__name__}: {e})",
                "details": {}}

    if n_exported == n_native:
        return {
            "passed": True,
            "summary": "PASS (text matches under set-based normalization)",
            "details": {
                "target_file": str(target_file),
                "normalized_lines": len(n_exported.splitlines()),
            },
        }

    diff = list(difflib.unified_diff(
        n_native.splitlines(), n_exported.splitlines(),
        "native(norm)", "exported(norm)", lineterm=""))
    minus = [l for l in diff if l.startswith("-") and not l.startswith("---")]
    plus = [l for l in diff if l.startswith("+") and not l.startswith("+++")]

    return {
        "passed": False,
        "summary": f"FAIL ({len(minus)} only-in-native, {len(plus)} only-in-export "
                   f"lines after normalization)",
        "details": {
            "target_file": str(target_file),
            "diff_preview": diff[:60],
            "native_norm_lines": len(n_native.splitlines()),
            "exported_norm_lines": len(n_exported.splitlines()),
        },
    }


# ---------------------------------------------------------------------------
# Standalone runner: report on the 4 cross-paradigm directions
# ---------------------------------------------------------------------------

def _report(directions: List[str]) -> int:
    """Run validate_text_diff over the given config keys and print a table.
    Returns process exit code (0 if all pass / unverifiable, 1 if any fail)."""
    from core import run_migration

    print("=" * 76)
    print("Layer 3: Text-level diff against project ground-truth (set-based)")
    print("=" * 76)
    print(f"{'direction':<36} {'verdict':<10} {'summary'}")
    print("-" * 76)

    failed = 0
    for key in directions:
        result = run_migration(key)
        if result.get("error"):
            print(f"{key:<36} {'ERROR':<10} {result['error']}")
            failed += 1
            continue
        report = validate_text_diff(
            result_dict=result,
            target_type=result["target_type"],
            config_key=key,
        )
        verdict = ("PASS" if report["passed"]
                   else "SKIP" if report["passed"] is None
                   else "FAIL")
        if verdict == "FAIL":
            failed += 1
        print(f"{key:<36} {verdict:<10} {report['summary']}")
    print("-" * 76)
    print(f"{len(directions)} directions, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    # The 4 cross-paradigm directions the thesis discusses (specific grammar).
    # Add more keys here to extend coverage (e.g. all 12 cross-paradigm or
    # all 32 Northwind configs).
    DEFAULT_DIRECTIONS = [
        "northwind_r2d_specific",  # PG -> Mongo
        "northwind_d2r_specific",  # Mongo -> PG
        "northwind_r2g_specific",  # PG -> Neo4j
        "northwind_r2c_specific",  # PG -> Cass
    ]
    raise SystemExit(_report(DEFAULT_DIRECTIONS))
