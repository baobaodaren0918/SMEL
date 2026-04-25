"""
Render OpRecord lists from schema_diff into SMILE scripts.

Each operation knows two output forms:
  - Specific      (e.g. "ADD_PROPERTY email TO Customer WITH TYPE String")
  - Generalized   (e.g. "ADD PROPERTY email TO Customer WITH TYPE String")

Rendering is template-driven (operations.json carries the keyword tokens),
but each op's parameter formatting lives here in code because the clause
shapes differ enough that a pure template would be illegible.

Public API:

    render_script(
        op_records: list[dict],
        source_db_type: str,                 # "RELATIONAL"|"DOCUMENT"|"GRAPH"|"COLUMNAR"
        target_db_type: str,
        migration_name: str = "generated_migration",
        schema_name: str = "generated_schema",
        version: str = "1.0",
        evolution: bool = False,             # True -> "EVOLUTION" header instead of "MIGRATION"
        syntax: str = "specific",            # "specific" | "generalized"
        header_comment: str | None = None,
    ) -> str
"""
from __future__ import annotations

from typing import Dict, List, Optional, Any


# ============================================================================
# KEYWORD MAP — single source of truth
# Mirrors grammar/smile_operations.json so renderer can run without loading it.
# ============================================================================

_KW: Dict[str, Dict[str, str]] = {
    "ADD_PROPERTY":         {"specific": "ADD_PROPERTY",         "generalized": "ADD PROPERTY"},
    "ADD_FOREIGN_KEY":      {"specific": "ADD_FOREIGN_KEY",      "generalized": "ADD FOREIGN KEY"},
    "ADD_PRIMARY_KEY":      {"specific": "ADD_PRIMARY_KEY",      "generalized": "ADD PRIMARY KEY"},
    "ADD_UNIQUE_KEY":       {"specific": "ADD_UNIQUE_KEY",       "generalized": "ADD UNIQUE KEY"},
    "ADD_PARTITION_KEY":    {"specific": "ADD_PARTITION_KEY",    "generalized": "ADD PARTITION KEY"},
    "ADD_CLUSTERING_KEY":   {"specific": "ADD_CLUSTERING_KEY",   "generalized": "ADD CLUSTERING KEY"},
    "ADD_LABEL":            {"specific": "ADD_LABEL",            "generalized": "ADD LABEL"},
    "ADD_EMBEDDED":         {"specific": "ADD_EMBEDDED",         "generalized": "ADD EMBEDDED"},
    "ADD_ENTITY":           {"specific": "ADD_ENTITY",           "generalized": "ADD ENTITY"},
    "DELETE_PROPERTY":      {"specific": "DELETE_PROPERTY",      "generalized": "DELETE PROPERTY"},
    "DELETE_FOREIGN_KEY":   {"specific": "DELETE_FOREIGN_KEY",   "generalized": "DELETE FOREIGN KEY"},
    "DELETE_EMBEDDED":      {"specific": "DELETE_EMBEDDED",      "generalized": "DELETE EMBEDDED"},
    "DELETE_ENTITY":        {"specific": "DELETE_ENTITY",        "generalized": "DELETE ENTITY"},
    "DELETE_PRIMARY_KEY":   {"specific": "DELETE_PRIMARY_KEY",   "generalized": "DELETE PRIMARY KEY"},
    "DELETE_UNIQUE_KEY":    {"specific": "DELETE_UNIQUE_KEY",    "generalized": "DELETE UNIQUE KEY"},
    "DELETE_PARTITION_KEY": {"specific": "DELETE_PARTITION_KEY", "generalized": "DELETE PARTITION KEY"},
    "DELETE_CLUSTERING_KEY":{"specific": "DELETE_CLUSTERING_KEY","generalized": "DELETE CLUSTERING KEY"},
    "DELETE_LABEL":         {"specific": "DELETE_LABEL",         "generalized": "DELETE LABEL"},
    "RENAME_PROPERTY":      {"specific": "RENAME_PROPERTY",      "generalized": "RENAME PROPERTY"},
    "RENAME_ENTITY":        {"specific": "RENAME_ENTITY",        "generalized": "RENAME ENTITY"},
    "FLATTEN":              {"specific": "FLATTEN",              "generalized": "FLATTEN"},
    "UNFLATTEN":            {"specific": "UNFLATTEN",            "generalized": "UNFLATTEN"},
    "UNNEST":               {"specific": "UNNEST",               "generalized": "UNNEST"},
    "NEST":                 {"specific": "NEST",                 "generalized": "NEST"},
    "WIND":                 {"specific": "WIND",                 "generalized": "WIND"},
    "UNWIND":               {"specific": "UNWIND",               "generalized": "UNWIND"},
    "COPY_PROPERTY":        {"specific": "COPY_PROPERTY",        "generalized": "COPY PROPERTY"},
    "COPY_ENTITY":          {"specific": "COPY_ENTITY",          "generalized": "COPY ENTITY"},
    "MOVE_PROPERTY":        {"specific": "MOVE_PROPERTY",        "generalized": "MOVE PROPERTY"},
    "MERGE":                {"specific": "MERGE",                "generalized": "MERGE"},
    "SPLIT":                {"specific": "SPLIT",                "generalized": "SPLIT"},
    "CAST_PROPERTY":        {"specific": "CAST_PROPERTY",        "generalized": "CAST PROPERTY"},
    "CAST_CONSTRAINT":      {"specific": "CAST_CONSTRAINT",      "generalized": "CAST CONSTRAINT"},
    "CAST_ENTITY":          {"specific": "CAST_ENTITY",          "generalized": "CAST ENTITY"},
    "RECARD":               {"specific": "RECARD",               "generalized": "RECARD"},
    "TRANSFORM":            {"specific": "TRANSFORM",            "generalized": "TRANSFORM"},
}


def _kw(op: str, syntax: str) -> str:
    info = _KW.get(op)
    if not info:
        return op  # unknown — emit raw (will be a parser error, but clear in output)
    return info["specific" if syntax == "specific" else "generalized"]


# ============================================================================
# PER-OPERATION FORMATTERS
# ============================================================================

def _fmt_columns(cols: List[str]) -> str:
    """Format key columns: single column or (col1, col2, ...)."""
    cols = list(cols or [])
    if len(cols) == 1:
        return cols[0]
    return "(" + ", ".join(cols) + ")"


def _fmt_qualified(entity: str, field: str) -> str:
    return f"{entity}.{field}"


def _render_op(op: str, params: Dict[str, Any], syntax: str) -> str:
    kw = _kw(op, syntax)

    if op == "ADD_PROPERTY":
        line = f"{kw} {params['name']} TO {params['entity']}"
        if params.get("data_type"):
            line += f" WITH TYPE {params['data_type']}"
        if params.get("default") is not None:
            line += f" WITH DEFAULT {params['default']}"
        if params.get("not_null"):
            line += " NOT NULL"
        return line

    if op == "ADD_FOREIGN_KEY":
        line = (f"{kw} {_fmt_qualified(params['entity'], params['field'])} "
                f"REFERENCES {params['target_entity']}({params['target_field']})")
        if params.get("cardinality"):
            line += f" WITH CARDINALITY {params['cardinality']}"
        if params.get("using_key"):
            line += f" USING KEY {params['using_key']}"
        if params.get("where"):
            line += f" WHERE {params['where']}"
        return line

    if op in ("ADD_PRIMARY_KEY", "ADD_UNIQUE_KEY",
              "ADD_PARTITION_KEY", "ADD_CLUSTERING_KEY"):
        cols = _fmt_columns(params.get("columns", []))
        target = (f"{params['entity']}.{cols}"
                  if len(params.get("columns", [])) == 1 and params.get("entity")
                  else cols)
        line = f"{kw} {target}"
        if params.get("data_type"):
            line += f" AS {params['data_type']}"
        if params.get("entity") and len(params.get("columns", [])) != 1:
            line += f" TO {params['entity']}"
        return line

    if op == "ADD_LABEL":
        return f"{kw} {params['label']} TO {params['entity']}"

    if op == "ADD_EMBEDDED":
        line = f"{kw} {params['name']} TO {params['entity']}"
        if params.get("cardinality"):
            line += f" WITH CARDINALITY {params['cardinality']}"
        if params.get("structure"):
            line += " WITH STRUCTURE (" + ", ".join(params["structure"]) + ")"
        return line

    if op == "ADD_ENTITY":
        line = f"{kw} {params['name']}"
        ee = params.get("edge_endpoints")
        if ee:
            line += f" FROM {ee['source']} TO {ee['target']}"
        if params.get("edge_cardinality"):
            line += f" WITH CARDINALITY {params['edge_cardinality']}"
        props = params.get("properties") or []
        if props:
            line += " WITH PROPERTIES (" + ", ".join(f"{n} {t}" for n, t in props) + ")"
        if params.get("key"):
            line += f" WITH KEY {params['key']}"
        return line

    if op == "DELETE_PROPERTY":
        return f"{kw} {_fmt_qualified(params['entity'], params['field'])}"

    if op == "DELETE_FOREIGN_KEY":
        return f"{kw} {_fmt_qualified(params['entity'], params['field'])}"

    if op == "DELETE_EMBEDDED":
        return f"{kw} {_fmt_qualified(params['entity'], params['field'])}"

    if op == "DELETE_ENTITY":
        return f"{kw} {params['name']}"

    if op in ("DELETE_PRIMARY_KEY", "DELETE_UNIQUE_KEY",
              "DELETE_PARTITION_KEY", "DELETE_CLUSTERING_KEY"):
        cols = _fmt_columns(params.get("columns", []))
        line = f"{kw} {cols}"
        if params.get("entity"):
            line += f" FROM {params['entity']}"
        return line

    if op == "DELETE_LABEL":
        return f"{kw} {params['label']} FROM {params['entity']}"

    if op == "RENAME_PROPERTY":
        line = f"{kw} {params['old_name']} TO {params['new_name']}"
        if params.get("entity"):
            line += f" IN {params['entity']}"
        return line

    if op == "RENAME_ENTITY":
        return f"{kw} {params['old_name']} TO {params['new_name']}"

    if op == "FLATTEN":
        return f"{kw} {_fmt_qualified(params['entity'], params['nested'])}"

    if op == "UNFLATTEN":
        fields = ", ".join(params.get("fields", []))
        return f"{kw} {params['entity']}:{fields} AS {params['nested_name']}"

    if op == "NEST":
        fields = ", ".join(params.get("fields", []))
        line = (f"{kw} {params['source']}:{fields} "
                f"IN {_fmt_qualified(params['parent'], params['embed_name'])}")
        if params.get("where"):
            line += f" WHERE {params['where']}"
        return line

    if op == "UNNEST":
        fields = ", ".join(params.get("fields", []))
        line = (f"{kw} {_fmt_qualified(params['entity'], params['nested'])}:{fields} "
                f"AS {params['new_entity']}")
        carry = params.get("carry") or []
        if carry:
            line += " WITH " + ", ".join(f"{a} TO {b}" for a, b in carry)
        return line

    if op == "WIND":
        return f"{kw} {_fmt_qualified(params['entity'], params['field'])}"

    if op == "UNWIND":
        line = f"{kw} {_fmt_qualified(params['entity'], params['field'])}"
        if params.get("new_entity"):
            line += f" INTO {params['new_entity']}"
        return line

    if op == "COPY_PROPERTY":
        return f"{kw} {params['name']} FROM {params['src']} TO {params['dst']}"

    if op == "COPY_ENTITY":
        line = f"{kw} {params['name']} AS {params['new_name']}"
        ee = params.get("edge_endpoints")
        if ee:
            line += f" FROM {ee['source']} TO {ee['target']}"
        return line

    if op == "MOVE_PROPERTY":
        return f"{kw} {params['name']} FROM {params['src']} TO {params['dst']}"

    if op == "MERGE":
        line = f"{kw} {params['a']}, {params['b']} INTO {params['c']}"
        if params.get("alias"):
            line += f" AS {params['alias']}"
        return line

    if op == "SPLIT":
        parts = params.get("parts") or []
        rendered = "; ".join(f"{name}:{', '.join(fields)}" for name, fields in parts)
        return f"{kw} {params['entity']} INTO {rendered}"

    if op == "CAST_PROPERTY":
        return f"{kw} {_fmt_qualified(params['entity'], params['field'])} TO {params['data_type']}"

    if op == "CAST_CONSTRAINT":
        return f"{kw} {_fmt_qualified(params['entity'], params['field'])} TO {params['constraint_type']}"

    if op == "CAST_ENTITY":
        return f"{kw} {params['entity']} TO {params['database_type']}"

    if op == "RECARD":
        return f"{kw} {_fmt_qualified(params['entity'], params['field'])} TO {params['cardinality']}"

    if op == "TRANSFORM":
        if (params.get("into") or "").upper() == "RELATIONSHIP":
            line = f"{kw} {params['entity']} INTO RELATIONSHIP FROM {params['source']} TO {params['target']}"
            if params.get("cardinality"):
                line += f" WITH CARDINALITY {params['cardinality']}"
            return line
        return f"{kw} {params['entity']} INTO ENTITY"

    return f"-- UNKNOWN OP: {op} {params}"


# ============================================================================
# HEADER + DRIVER
# ============================================================================

def _render_header(
    migration_name: str,
    schema_name: str,
    version: str,
    source_db_type: str,
    target_db_type: str,
    evolution: bool,
    schema_version_to: Optional[str],
) -> str:
    kw = "EVOLUTION" if evolution else "MIGRATION"
    header = (
        f"{kw} {migration_name}:{version}\n"
        f"FROM {source_db_type.upper()} TO {target_db_type.upper()}\n"
        f"USING {schema_name} VERSION {version}"
    )
    if evolution and schema_version_to:
        header += f" TO {schema_version_to}"
    return header


def render_script(
    op_records: List[Dict[str, Any]],
    source_db_type: str,
    target_db_type: str,
    migration_name: str = "generated_migration",
    schema_name: str = "generated_schema",
    version: str = "1.0",
    evolution: bool = False,
    syntax: str = "specific",
    header_comment: Optional[str] = None,
    schema_version_to: Optional[str] = None,
) -> str:
    """Render an OpRecord list into a SMILE script in `syntax` ('specific' or 'generalized')."""
    lines: List[str] = []
    if header_comment:
        for ln in header_comment.splitlines():
            lines.append(f"-- {ln}")
        lines.append("")
    lines.append(_render_header(
        migration_name=migration_name,
        schema_name=schema_name,
        version=version,
        source_db_type=source_db_type,
        target_db_type=target_db_type,
        evolution=evolution,
        schema_version_to=schema_version_to,
    ))
    lines.append("")

    if not op_records:
        lines.append("-- (no schema differences detected)")
        return "\n".join(lines) + "\n"

    last_category: Optional[str] = None
    for rec in op_records:
        op = rec["op"]
        params = rec.get("params") or {}
        category = _category_of(op)
        if last_category and category != last_category:
            lines.append("")  # blank line between op groups
        last_category = category
        if rec.get("comment"):
            lines.append(f"-- {rec['comment']}")
        lines.append(_render_op(op, params, syntax))

    return "\n".join(lines) + "\n"


def render_header_only(
    source_db_type: str,
    target_db_type: str,
    kind: str = "auto",         # "migration" | "evolution" | "auto"
    migration_name: str = "generated",
    schema_name: str = "generated_schema",
    version: str = "1.0",
    schema_version_to: str = "2.0",
    syntax: str = "specific",
) -> str:
    """Emit just the SMILE header — the user writes the operations themselves.

    kind="auto"  → MIGRATION when src ≠ tgt, EVOLUTION when src == tgt.
    kind="migration" / "evolution" → forced.
    Evolution headers use ``USING ... VERSION X TO Y`` (per the grammar).
    """
    src = (source_db_type or "").upper()
    tgt = (target_db_type or "").upper()
    if kind == "auto":
        is_evolution = src == tgt
    else:
        is_evolution = (kind == "evolution")
    keyword = "EVOLUTION" if is_evolution else "MIGRATION"
    name = (migration_name or "generated") + ("_evolution" if is_evolution else "_migration")
    using = f"USING {schema_name} VERSION {version}"
    if is_evolution:
        using += f" TO {schema_version_to}"
    lines = [
        f"{keyword} {name}:{version}",
        f"FROM {src} TO {tgt}",
        using,
        "",
        "-- TODO: write your operations below.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _category_of(op: str) -> str:
    if op.startswith("RENAME_"):
        return "rename"
    if op.startswith("ADD_"):
        return "add"
    if op.startswith("DELETE_"):
        return "delete"
    if op.startswith("CAST_"):
        return "cast"
    if op in ("FLATTEN", "UNFLATTEN", "NEST", "UNNEST", "WIND", "UNWIND", "TRANSFORM"):
        return "structure"
    return "other"
