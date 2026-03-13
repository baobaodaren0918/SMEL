"""
Layer 1 Validation: Meta Schema V2 Comparison.

Compares the migration result (Meta V2) against the expected target schema
parsed from the native schema file. Proves SMEL script correctness.

Pipeline position:
  Source -> [RE] -> Meta V1 -> [SMEL] -> Meta V2  <-  compare  ->  Expected Meta
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

    Hard issues (counted): missing/extra attributes, type mismatches,
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

    # Compare attributes (by name, type; key_type/cardinality as warnings)
    attr_diff = _compare_attributes(
        actual.get("attributes", []),
        expected.get("attributes", [])
    )
    if attr_diff:
        diff["attributes"] = attr_diff
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
    """Compare embedded lists by name.

    Hard issues: missing/extra embedded, target entity mismatches.
    Warnings: cardinality differences (SMEL operations default to 1..1
    and don't explicitly control embedded cardinality).
    """
    actual_map = {item["name"]: item for item in actual}
    expected_map = {item["name"]: item for item in expected}

    missing = sorted(set(expected_map) - set(actual_map))
    extra = sorted(set(actual_map) - set(expected_map))
    target_mismatches = []
    cardinality_warnings = []

    for name in sorted(set(actual_map) & set(expected_map)):
        a = actual_map[name]
        e = expected_map[name]
        if a.get("target") != e.get("target"):
            target_mismatches.append({
                "name": name,
                "actual_target": a.get("target"),
                "expected_target": e.get("target"),
            })
        if a.get("cardinality") != e.get("cardinality"):
            cardinality_warnings.append({
                "name": name,
                "actual": a.get("cardinality"),
                "expected": e.get("cardinality"),
            })

    issue_count = len(missing) + len(extra) + len(target_mismatches)
    if issue_count == 0 and not cardinality_warnings:
        return {}

    result = {"issue_count": issue_count}
    if missing:
        result["missing"] = missing
    if extra:
        result["extra"] = extra
    if target_mismatches:
        result["target_mismatches"] = target_mismatches
    if cardinality_warnings:
        result["cardinality_warnings"] = cardinality_warnings
    return result


def _compare_attributes(actual: List[Dict], expected: List[Dict]) -> Dict:
    """Compare attribute lists by name.

    Hard issues: missing/extra attributes, type mismatches.
    Warnings: is_key, key_type, and is_optional differences (representation-level).
    """
    actual_map = {a["name"]: a for a in actual}
    expected_map = {a["name"]: a for a in expected}

    missing = sorted(set(expected_map) - set(actual_map))
    extra = sorted(set(actual_map) - set(expected_map))

    type_mismatches = []
    key_warnings = []
    optional_warnings = []

    for name in sorted(set(actual_map) & set(expected_map)):
        a = actual_map[name]
        e = expected_map[name]
        if a.get("type") != e.get("type"):
            type_mismatches.append({
                "attr": name,
                "actual": a.get("type"),
                "expected": e.get("type"),
            })
        # is_key and key_type are warnings (not hard failures)
        if a.get("is_key") != e.get("is_key"):
            key_warnings.append({
                "attr": name,
                "field": "is_key",
                "actual": a.get("is_key"),
                "expected": e.get("is_key"),
            })
        if a.get("key_type") != e.get("key_type"):
            key_warnings.append({
                "attr": name,
                "field": "key_type",
                "actual": a.get("key_type"),
                "expected": e.get("key_type"),
            })
        # is_optional (nullability) differs across DB types — warning
        if a.get("is_optional") != e.get("is_optional"):
            optional_warnings.append({
                "attr": name,
                "actual": a.get("is_optional"),
                "expected": e.get("is_optional"),
            })

    issue_count = len(missing) + len(extra) + len(type_mismatches)
    if issue_count == 0 and not key_warnings and not optional_warnings:
        return {}

    result = {"issue_count": issue_count}
    if missing:
        result["missing"] = missing
    if extra:
        result["extra"] = extra
    if type_mismatches:
        result["type_mismatches"] = type_mismatches
    if key_warnings:
        result["key_warnings"] = key_warnings
    if optional_warnings:
        result["optional_warnings"] = optional_warnings
    return result


def _compare_references(actual: List[Dict], expected: List[Dict]) -> Dict:
    """Compare references by name+target.

    Hard issues: missing/extra references, target mismatches, edge_attributes mismatches.
    Warnings: cardinality differences.
    """
    actual_map = {item["name"]: item for item in actual}
    expected_map = {item["name"]: item for item in expected}

    missing = sorted(set(expected_map) - set(actual_map))
    extra = sorted(set(actual_map) - set(expected_map))
    target_mismatches = []
    attr_mismatches = []
    cardinality_warnings = []

    for name in sorted(set(actual_map) & set(expected_map)):
        a = actual_map[name]
        e = expected_map[name]
        if a.get("target") != e.get("target"):
            target_mismatches.append({
                "name": name,
                "actual_target": a.get("target"),
                "expected_target": e.get("target"),
            })
        # Compare edge_attributes (if either side has them)
        a_attrs = {at["name"]: at["type"] for at in a.get("edge_attributes", [])}
        e_attrs = {at["name"]: at["type"] for at in e.get("edge_attributes", [])}
        if a_attrs != e_attrs:
            attr_mismatches.append({
                "name": name,
                "actual": a_attrs,
                "expected": e_attrs,
            })
        if a.get("cardinality") != e.get("cardinality"):
            cardinality_warnings.append({
                "name": name,
                "actual": a.get("cardinality"),
                "expected": e.get("cardinality"),
            })

    issue_count = len(missing) + len(extra) + len(target_mismatches) + len(attr_mismatches)
    if issue_count == 0 and not cardinality_warnings:
        return {}

    result = {"issue_count": issue_count}
    if missing:
        result["missing"] = missing
    if extra:
        result["extra"] = extra
    if target_mismatches:
        result["target_mismatches"] = target_mismatches
    if attr_mismatches:
        result["attr_mismatches"] = attr_mismatches
    if cardinality_warnings:
        result["cardinality_warnings"] = cardinality_warnings
    return result


def _compare_edges(actual: List[Dict], expected: List[Dict]) -> Dict:
    """Compare edges by name. Target/source mismatches are issues, cardinality is warning."""
    actual_map = {item["name"]: item for item in actual}
    expected_map = {item["name"]: item for item in expected}

    missing = sorted(set(expected_map) - set(actual_map))
    extra = sorted(set(actual_map) - set(expected_map))
    mismatches = []
    cardinality_warnings = []

    for name in sorted(set(actual_map) & set(expected_map)):
        a = actual_map[name]
        e = expected_map[name]
        field_diffs = {}
        for f in ["target", "source"]:
            if a.get(f) != e.get(f):
                field_diffs[f] = {"actual": a.get(f), "expected": e.get(f)}
        if field_diffs:
            mismatches.append({"name": name, "diffs": field_diffs})
        if a.get("cardinality") != e.get("cardinality"):
            cardinality_warnings.append({
                "name": name,
                "actual": a.get("cardinality"),
                "expected": e.get("cardinality"),
            })

    issue_count = len(missing) + len(extra) + len(mismatches)
    if issue_count == 0 and not cardinality_warnings:
        return {}

    result = {"issue_count": issue_count}
    if missing:
        result["missing"] = missing
    if extra:
        result["extra"] = extra
    if mismatches:
        result["mismatches"] = mismatches
    if cardinality_warnings:
        result["cardinality_warnings"] = cardinality_warnings
    return result


def _compare_constraints(actual: List[Dict], expected: List[Dict]) -> Dict:
    """Compare constraint lists.

    Hard issues: missing/extra PK constraints.
    Warnings: FK differences, primary_key_types differences
        (e.g. Cassandra PARTITION vs CLUSTERING key distinction).
    """
    # Separate PK and FK constraints
    actual_pk = [c for c in actual if c["type"] in ("PRIMARY_KEY", "UNIQUE")]
    expected_pk = [c for c in expected if c["type"] in ("PRIMARY_KEY", "UNIQUE")]
    actual_fk = [c for c in actual if c["type"] == "FOREIGN_KEY"]
    expected_fk = [c for c in expected if c["type"] == "FOREIGN_KEY"]

    # Compare PKs by column set
    def _pk_key(c):
        return (c["type"], tuple(sorted(c.get("columns", []))))

    actual_pk_set = {_pk_key(c): c for c in actual_pk}
    expected_pk_set = {_pk_key(c): c for c in expected_pk}

    missing_pk = [expected_pk_set[k] for k in sorted(set(expected_pk_set) - set(actual_pk_set))]
    extra_pk = [actual_pk_set[k] for k in sorted(set(actual_pk_set) - set(expected_pk_set))]

    # Compare primary_key_types on matching PKs (warning, not hard issue)
    pk_type_warnings = []
    for key in sorted(set(actual_pk_set) & set(expected_pk_set)):
        a_types = actual_pk_set[key].get("primary_key_types")
        e_types = expected_pk_set[key].get("primary_key_types")
        if a_types != e_types:
            pk_type_warnings.append({
                "columns": list(key[1]),
                "actual": a_types,
                "expected": e_types,
            })

    # FK differences are warnings
    def _fk_key(c):
        return (c.get("column", ""), c.get("references_entity", ""))

    actual_fk_set = {_fk_key(c) for c in actual_fk}
    expected_fk_set = {_fk_key(c) for c in expected_fk}
    fk_warnings = []
    if actual_fk_set != expected_fk_set:
        fk_warnings.append({
            "missing_fks": sorted(expected_fk_set - actual_fk_set),
            "extra_fks": sorted(actual_fk_set - expected_fk_set),
        })

    issue_count = len(missing_pk) + len(extra_pk)
    if issue_count == 0 and not fk_warnings and not pk_type_warnings:
        return {}

    result = {"issue_count": issue_count}
    if missing_pk:
        result["missing_pk"] = missing_pk
    if extra_pk:
        result["extra_pk"] = extra_pk
    if pk_type_warnings:
        result["pk_type_warnings"] = pk_type_warnings
    if fk_warnings:
        result["fk_warnings"] = fk_warnings
    return result



def _compare_relationship_types(actual: Dict, expected: Dict) -> Dict:
    """Compare __relationship_types__ dicts.

    Hard issues: missing/extra relationship types, source/target/attribute mismatches.
    Warnings: cardinality differences (consistent with edges/references/embedded).
    """
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    mismatches = []
    cardinality_warnings = []

    for name in sorted(set(actual) & set(expected)):
        a = actual[name]
        e = expected[name]
        diffs = {}
        for field in ["source_entity", "target_entity"]:
            if a.get(field) != e.get(field):
                diffs[field] = {"actual": a.get(field), "expected": e.get(field)}
        # Cardinality is a warning (not a hard issue)
        if a.get("cardinality") != e.get("cardinality"):
            cardinality_warnings.append({
                "name": name,
                "actual": a.get("cardinality"),
                "expected": e.get("cardinality"),
            })
        # Compare relationship attributes
        a_attrs = {attr["name"]: attr["type"] for attr in a.get("attributes", [])}
        e_attrs = {attr["name"]: attr["type"] for attr in e.get("attributes", [])}
        if a_attrs != e_attrs:
            diffs["attributes"] = {"actual": a_attrs, "expected": e_attrs}
        if diffs:
            mismatches.append({"name": name, "diffs": diffs})

    issue_count = len(missing) + len(extra) + len(mismatches)
    if issue_count == 0 and not cardinality_warnings:
        return {}

    result = {"issue_count": issue_count}
    if missing:
        result["missing"] = missing
    if extra:
        result["extra"] = extra
    if mismatches:
        result["mismatches"] = mismatches
    if cardinality_warnings:
        result["cardinality_warnings"] = cardinality_warnings
    return result


def _resolve_target_file(config_key: str, target_type: str):
    """
    Resolve the target native file for validation.

    Priority:
    1. MIGRATION_TARGET_FILES: per-direction target (Person, same-model)
    2. TARGET_SCHEMA_FILES: shared target by type (Northwind cross-model)
    """
    from config import TARGET_SCHEMA_FILES, MIGRATION_TARGET_FILES

    # Check per-direction target first (strip _specific/_generalized suffix)
    base_key = config_key.rsplit("_", 1)[0] if config_key.endswith(("_specific", "_generalized")) else config_key
    target_file = MIGRATION_TARGET_FILES.get(base_key)
    if target_file and target_file.exists():
        return target_file

    # Fallback to shared target by type (Northwind cross-model)
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
