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
from typing import Dict, Any
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

    Thin wrapper over the unified ``database_diff.compute_diff`` engine plus
    the ``database_diff_formatters.to_validation_report`` formatter. Both
    Layer 1 and the per-op UI panel now share the same comparison engine.

    Args:
        actual: Migration result meta schema dict
        expected: Expected target meta schema dict (from parsing native file)
    """
    from database_diff import compute_diff
    from database_diff_formatters import to_validation_report
    diff = compute_diff(actual, expected)
    return to_validation_report(diff, actual, expected)


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
