"""
Layer 1 Validation: Meta Schema V2 Comparison.

Compares the migration result (Meta V2) against the expected target schema
parsed from the native schema file. Proves SMILE script correctness.

Pipeline position:
  Source -> [RE] -> Meta V1 -> [SMILE] -> Meta V2  <-  compare  ->  Expected Meta
                                       ^                          ^
                                  migration result       target native file parsed

Normalization:
  For Document targets, the migration result uses flat entity names (customer, address)
  while MongoDB adapter uses path names (orders.customer, orders.customer.address).
  The normalizer expands flat names to path names before comparison.
"""
from typing import Dict, Any, List, Optional
import copy


def _normalize_to_paths(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a flat-named meta dict to use path-based entity names.

    Migration results use flat names like 'customer', 'address' with embedded
    relationships linking them. MongoDB adapter uses path names like
    'orders.customer', 'orders.customer.address'.

    This function:
    1. Finds the root entity (document kind, not referenced as embedded target)
    2. Walks the embedded tree recursively
    3. Creates path-named entries, duplicating shared entities as needed
    """
    entities = {k: v for k, v in meta.items() if not k.startswith("__")}
    if not entities:
        return meta

    # Find root entity: has entity_kind 'document' and is not an embedded target
    embedded_targets = set()
    for e in entities.values():
        for emb in e.get("embedded", []):
            embedded_targets.add(emb.get("target", ""))

    roots = []
    for name, e in entities.items():
        if name not in embedded_targets:
            roots.append(name)

    if len(roots) != 1:
        # Can't normalize without a single root - return as-is
        return meta

    root_name = roots[0]
    result = {}

    # Copy special keys
    for k, v in meta.items():
        if k.startswith("__"):
            result[k] = v

    # Walk embedded tree and build path-based entries
    _walk_embedded(entities, root_name, root_name, result)

    return result


def _walk_embedded(entities: Dict, entity_name: str, path: str, result: Dict):
    """Recursively walk embedded tree and create path-based entity entries."""
    entity = entities.get(entity_name)
    if not entity:
        return

    # Create a copy with updated name and embedded targets
    new_entity = copy.deepcopy(entity)
    new_entity["name"] = path

    # Determine entity_kind: root keeps 'document', nested become 'embedded'
    if "." in path:
        new_entity["entity_kind"] = "embedded"

    # Update embedded target paths
    new_embedded = []
    for emb in new_entity.get("embedded", []):
        child_name = emb["target"]
        child_path = f"{path}.{emb['name']}"
        new_embedded.append({
            "name": emb["name"],
            "target": child_path,
            "cardinality": emb.get("cardinality", "1..1"),
        })
        # Recurse into child
        _walk_embedded(entities, child_name, child_path, result)

    new_entity["embedded"] = new_embedded
    result[path] = new_entity


def _diff_named(actual: List[Dict], expected: List[Dict],
                key_fn=lambda x: x['name']) -> tuple:
    """Compute by-key set diff over two lists of dicts.

    Returns (missing_keys_sorted, extra_keys_sorted, common_pairs_sorted).
    common_pairs is [(key, actual_item, expected_item), ...].
    """
    actual_map = {key_fn(item): item for item in actual}
    expected_map = {key_fn(item): item for item in expected}
    missing = sorted(set(expected_map) - set(actual_map))
    extra = sorted(set(actual_map) - set(expected_map))
    common = [(k, actual_map[k], expected_map[k])
              for k in sorted(set(actual_map) & set(expected_map))]
    return missing, extra, common


def _pack_diff(missing: List, extra: List, hard: Dict[str, list],
               warn: Dict[str, list]) -> Dict:
    """Pack a comparison result into the legacy validate_meta output shape.

    ``hard`` are issue-counted groups (missing/extra/mismatches).
    ``warn`` are warning groups (cardinality, key_type, FK, ...).
    Returns ``{}`` when there's nothing to report.
    """
    issue_count = len(missing) + len(extra) + sum(len(v) for v in hard.values())
    if issue_count == 0 and not any(warn.values()):
        return {}
    result: Dict[str, Any] = {"issue_count": issue_count}
    if missing:
        result["missing"] = missing
    if extra:
        result["extra"] = extra
    for k, v in hard.items():
        if v:
            result[k] = v
    for k, v in warn.items():
        if v:
            result[k] = v
    return result


def compare_meta_schemas(actual: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two meta schema dicts (from db_to_dict()) and return structured diff.

    Args:
        actual: Migration result meta schema dict
        expected: Expected target meta schema dict (from parsing native file)

    Returns:
        {
            "passed": bool,
            "summary": str,
            "entity_count": {"actual": int, "expected": int},
            "details": {
                "missing_entities": [...],
                "extra_entities": [...],
                "entity_diffs": { entity_name: { ... diffs ... } },
                "relationship_type_diffs": { ... }
            }
        }
    """
    # Extract entity names (skip __ special keys)
    actual_entities = {k for k in actual if not k.startswith("__")}
    expected_entities = {k for k in expected if not k.startswith("__")}

    missing = sorted(expected_entities - actual_entities)
    extra = sorted(actual_entities - expected_entities)
    common = sorted(actual_entities & expected_entities)

    entity_diffs = {}
    entity_warnings = {}
    total_issues = 0

    for name in common:
        diff = _compare_entity(actual[name], expected[name])
        if diff:
            ic = diff.get("issue_count", 0)
            if ic > 0:
                entity_diffs[name] = diff
                total_issues += ic
            else:
                # Only warnings, no hard issues
                entity_warnings[name] = diff

    # Compare relationship types (for graph schemas)
    rel_diffs = {}
    actual_rels = actual.get("__relationship_types__", {})
    expected_rels = expected.get("__relationship_types__", {})
    if actual_rels or expected_rels:
        rel_diffs = _compare_relationship_types(actual_rels, expected_rels)
        total_issues += rel_diffs.get("issue_count", 0)

    total_issues += len(missing) + len(extra)
    passed = total_issues == 0

    # Build summary
    if passed:
        summary = "PASS"
    else:
        parts = []
        if missing:
            parts.append(f"{len(missing)} missing entities")
        if extra:
            parts.append(f"{len(extra)} extra entities")
        if entity_diffs:
            parts.append(f"{len(entity_diffs)} entity mismatches")
        if rel_diffs.get("issue_count", 0) > 0:
            parts.append(f"relationship type mismatches")
        summary = f"FAIL ({', '.join(parts)})"

    return {
        "passed": passed,
        "summary": summary,
        "entity_count": {
            "actual": len(actual_entities),
            "expected": len(expected_entities),
        },
        "details": {
            "missing_entities": missing,
            "extra_entities": extra,
            "entity_diffs": entity_diffs,
            "entity_warnings": entity_warnings,
            "relationship_type_diffs": rel_diffs,
        }
    }


def _compare_entity(actual: Dict, expected: Dict) -> Dict:
    """Compare two serialized entity dicts. Returns diff dict or empty if equal.

    Hard issues (counted): missing/extra properties, type mismatches,
        missing/extra embedded, missing/extra references, missing/extra edges.
    Warnings (not counted): cardinality differences, key_type differences,
        FK constraint details, entity_kind differences.
    """
    diff = {}
    issue_count = 0
    warnings = {}

    # entity_kind: warning only (migration normalizes all to target kind)
    if actual.get("entity_kind") != expected.get("entity_kind"):
        warnings["entity_kind"] = {
            "actual": actual.get("entity_kind"),
            "expected": expected.get("entity_kind"),
        }

    # Compare properties (by name, type; key_type/cardinality as warnings)
    attr_diff = _compare_properties(
        actual.get("properties", []),
        expected.get("properties", [])
    )
    if attr_diff:
        diff["properties"] = attr_diff
        issue_count += attr_diff.get("issue_count", 0)

    # Compare constraints (PK structure only, FK as warning)
    constraint_diff = _compare_constraints(
        actual.get("constraints", []),
        expected.get("constraints", [])
    )
    if constraint_diff:
        if constraint_diff.get("issue_count", 0) > 0:
            diff["constraints"] = constraint_diff
            issue_count += constraint_diff.get("issue_count", 0)
        else:
            warnings["constraints"] = constraint_diff

    # Compare references (by name+target; cardinality as warning)
    ref_diff = _compare_references(
        actual.get("references", []),
        expected.get("references", [])
    )
    if ref_diff:
        diff["references"] = ref_diff
        issue_count += ref_diff.get("issue_count", 0)

    # Compare embedded (by name; cardinality as warning)
    emb_diff = _compare_embedded(
        actual.get("embedded", []),
        expected.get("embedded", [])
    )
    if emb_diff:
        diff["embedded"] = emb_diff
        issue_count += emb_diff.get("issue_count", 0)

    # Compare edges (by name+target+source; cardinality as warning)
    edge_diff = _compare_edges(
        actual.get("edges", []),
        expected.get("edges", [])
    )
    if edge_diff:
        diff["edges"] = edge_diff
        issue_count += edge_diff.get("issue_count", 0)

    if warnings:
        diff["warnings"] = warnings
    if issue_count > 0:
        diff["issue_count"] = issue_count
    return diff


def _compare_embedded(actual: List[Dict], expected: List[Dict]) -> Dict:
    """Embedded relationships: target mismatch is hard, cardinality is warning."""
    missing, extra, common = _diff_named(actual, expected)
    target_mismatches, cardinality_warnings = [], []
    for name, a, e in common:
        if a.get("target") != e.get("target"):
            target_mismatches.append({"name": name,
                                      "actual_target": a.get("target"),
                                      "expected_target": e.get("target")})
        if a.get("cardinality") != e.get("cardinality"):
            cardinality_warnings.append({"name": name,
                                         "actual": a.get("cardinality"),
                                         "expected": e.get("cardinality")})
    return _pack_diff(missing, extra,
                      hard={"target_mismatches": target_mismatches},
                      warn={"cardinality_warnings": cardinality_warnings})


def _compare_properties(actual: List[Dict], expected: List[Dict]) -> Dict:
    """Properties: type mismatch is hard; is_key/key_type/is_optional are warnings."""
    missing, extra, common = _diff_named(actual, expected)
    type_mismatches, key_warnings, optional_warnings = [], [], []
    for name, a, e in common:
        if a.get("type") != e.get("type"):
            type_mismatches.append({"attr": name,
                                    "actual": a.get("type"),
                                    "expected": e.get("type")})
        for field in ("is_key", "key_type"):
            if a.get(field) != e.get(field):
                key_warnings.append({"attr": name, "field": field,
                                     "actual": a.get(field),
                                     "expected": e.get(field)})
        if a.get("is_optional") != e.get("is_optional"):
            optional_warnings.append({"attr": name,
                                      "actual": a.get("is_optional"),
                                      "expected": e.get("is_optional")})
    return _pack_diff(missing, extra,
                      hard={"type_mismatches": type_mismatches},
                      warn={"key_warnings": key_warnings,
                            "optional_warnings": optional_warnings})


def _compare_references(actual: List[Dict], expected: List[Dict]) -> Dict:
    """References: target & edge_properties mismatch are hard, cardinality is warning."""
    missing, extra, common = _diff_named(actual, expected)
    target_mismatches, attr_mismatches, cardinality_warnings = [], [], []
    for name, a, e in common:
        if a.get("target") != e.get("target"):
            target_mismatches.append({"name": name,
                                      "actual_target": a.get("target"),
                                      "expected_target": e.get("target")})
        a_attrs = {at["name"]: at["type"] for at in a.get("edge_properties", [])}
        e_attrs = {at["name"]: at["type"] for at in e.get("edge_properties", [])}
        if a_attrs != e_attrs:
            attr_mismatches.append({"name": name,
                                    "actual": a_attrs, "expected": e_attrs})
        if a.get("cardinality") != e.get("cardinality"):
            cardinality_warnings.append({"name": name,
                                         "actual": a.get("cardinality"),
                                         "expected": e.get("cardinality")})
    return _pack_diff(missing, extra,
                      hard={"target_mismatches": target_mismatches,
                            "attr_mismatches": attr_mismatches},
                      warn={"cardinality_warnings": cardinality_warnings})


def _compare_edges(actual: List[Dict], expected: List[Dict]) -> Dict:
    """Edges: source & target mismatch are hard, cardinality is warning."""
    missing, extra, common = _diff_named(actual, expected)
    mismatches, cardinality_warnings = [], []
    for name, a, e in common:
        field_diffs = {f: {"actual": a.get(f), "expected": e.get(f)}
                       for f in ("target", "source") if a.get(f) != e.get(f)}
        if field_diffs:
            mismatches.append({"name": name, "diffs": field_diffs})
        if a.get("cardinality") != e.get("cardinality"):
            cardinality_warnings.append({"name": name,
                                         "actual": a.get("cardinality"),
                                         "expected": e.get("cardinality")})
    return _pack_diff(missing, extra,
                      hard={"mismatches": mismatches},
                      warn={"cardinality_warnings": cardinality_warnings})


def _compare_constraints(actual: List[Dict], expected: List[Dict]) -> Dict:
    """Constraints: PK structure mismatch is hard; FK + Cassandra PK-subtype are warnings."""
    # Bucket by constraint type
    actual_pk = [c for c in actual if c["type"] in ("PRIMARY_KEY", "UNIQUE")]
    expected_pk = [c for c in expected if c["type"] in ("PRIMARY_KEY", "UNIQUE")]
    actual_fk = [c for c in actual if c["type"] == "FOREIGN_KEY"]
    expected_fk = [c for c in expected if c["type"] == "FOREIGN_KEY"]

    # PKs are keyed by (type, sorted column tuple)
    pk_key = lambda c: (c["type"], tuple(sorted(c.get("columns", []))))
    actual_pk_set = {pk_key(c): c for c in actual_pk}
    expected_pk_set = {pk_key(c): c for c in expected_pk}
    missing_pk = [expected_pk_set[k] for k in sorted(set(expected_pk_set) - set(actual_pk_set))]
    extra_pk   = [actual_pk_set[k]   for k in sorted(set(actual_pk_set) - set(expected_pk_set))]

    pk_type_warnings = []
    for key in sorted(set(actual_pk_set) & set(expected_pk_set)):
        a_types = actual_pk_set[key].get("primary_key_types")
        e_types = expected_pk_set[key].get("primary_key_types")
        if a_types != e_types:
            pk_type_warnings.append({"columns": list(key[1]),
                                     "actual": a_types, "expected": e_types})

    # FK differences as a single warning entry (legacy shape)
    fk_key = lambda c: (c.get("column", ""), c.get("references_entity", ""))
    actual_fk_set = {fk_key(c) for c in actual_fk}
    expected_fk_set = {fk_key(c) for c in expected_fk}
    fk_warnings = []
    if actual_fk_set != expected_fk_set:
        fk_warnings.append({
            "missing_fks": sorted(expected_fk_set - actual_fk_set),
            "extra_fks":   sorted(actual_fk_set - expected_fk_set),
        })

    issue_count = len(missing_pk) + len(extra_pk)
    if issue_count == 0 and not fk_warnings and not pk_type_warnings:
        return {}
    result: Dict[str, Any] = {"issue_count": issue_count}
    if missing_pk:        result["missing_pk"] = missing_pk
    if extra_pk:          result["extra_pk"] = extra_pk
    if pk_type_warnings:  result["pk_type_warnings"] = pk_type_warnings
    if fk_warnings:       result["fk_warnings"] = fk_warnings
    return result


def _compare_relationship_types(actual: Dict, expected: Dict) -> Dict:
    """__relationship_types__: source/target/properties are hard; cardinality is warning."""
    missing = sorted(set(expected) - set(actual))
    extra   = sorted(set(actual) - set(expected))
    mismatches, cardinality_warnings = [], []
    for name in sorted(set(actual) & set(expected)):
        a, e = actual[name], expected[name]
        diffs = {f: {"actual": a.get(f), "expected": e.get(f)}
                 for f in ("source_entity", "target_entity")
                 if a.get(f) != e.get(f)}
        if a.get("cardinality") != e.get("cardinality"):
            cardinality_warnings.append({"name": name,
                                         "actual": a.get("cardinality"),
                                         "expected": e.get("cardinality")})
        a_attrs = {at["name"]: at["type"] for at in a.get("properties", [])}
        e_attrs = {at["name"]: at["type"] for at in e.get("properties", [])}
        if a_attrs != e_attrs:
            diffs["properties"] = {"actual": a_attrs, "expected": e_attrs}
        if diffs:
            mismatches.append({"name": name, "diffs": diffs})
    return _pack_diff(missing, extra,
                      hard={"mismatches": mismatches},
                      warn={"cardinality_warnings": cardinality_warnings})


def _resolve_target_file(config_key: str, target_type: str):
    """
    Resolve the target native file for validation.

    Priority:
    1. MIGRATION_TARGET_FILES: per-direction target (Person, same-model)
    2. TARGET_SCHEMA_FILES: shared target by type — *only* for Northwind
       cross-model configs, since the shared Northwind file is meaningful
       only when the source schema is also Northwind. Other configs
       (grammar_completeness etc.) get None → validation returns N/A.
    """
    from config import TARGET_SCHEMA_FILES, MIGRATION_TARGET_FILES

    # Check per-direction target first (strip _specific/_generalized suffix)
    base_key = config_key.rsplit("_", 1)[0] if config_key.endswith(("_specific", "_generalized")) else config_key
    target_file = MIGRATION_TARGET_FILES.get(base_key)
    if target_file and target_file.exists():
        return target_file

    # Fallback to the shared Northwind cross-model target — only valid when
    # the source itself is Northwind. Configs like grammar_completeness use
    # a synthetic schema and have no meaningful expected target.
    if config_key.startswith("northwind_"):
        target_file = TARGET_SCHEMA_FILES.get(target_type)
        if target_file and target_file.exists():
            return target_file

    return None


def validate_meta(result_dict: Dict[str, Any], target_type: str,
                  config_key: str = "") -> Dict[str, Any]:
    """
    Layer 1: Compare migration Meta V2 result against expected target schema.

    For Document targets, normalizes flat entity names to path-based names
    before comparison (migration uses 'customer', MongoDB adapter uses 'orders.customer').
    """
    from config import SOURCE_TYPE_DOCUMENT
    from Schema.adapters import ADAPTER_REGISTRY
    from core import db_to_dict

    target_file = _resolve_target_file(config_key, target_type)
    if not target_file:
        return {"passed": None, "summary": f"N/A (no target file for {config_key})", "details": {}}

    adapter_class = ADAPTER_REGISTRY.get(target_type)
    if not adapter_class:
        return {"passed": None, "summary": f"N/A (no adapter for {target_type})", "details": {}}

    try:
        expected_db = adapter_class.load_from_file(str(target_file))
        expected_meta = db_to_dict(expected_db)
    except Exception as e:
        return {"passed": False, "summary": f"FAIL (error parsing target: {e})", "details": {}}

    # Use raw Meta V2 from migration result
    # For Document targets, normalize flat entity names to path-based names
    actual_meta = result_dict.get("result", {})
    if target_type == SOURCE_TYPE_DOCUMENT:
        actual_meta = _normalize_to_paths(actual_meta)

    return compare_meta_schemas(actual_meta, expected_meta)
