"""Layer 1 Validation: Meta Schema V2 Comparison."""
from typing import Dict, Any
import copy


def _normalize_to_paths(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a flat-named meta dict to use path-based entity names."""
    entities = {k: v for k, v in meta.items() if not k.startswith("__")}
    if not entities:
        return meta

    embedded_targets = set()
    for e in entities.values():
        for emb in e.get("embedded", []):
            embedded_targets.add(emb.get("target", ""))

    roots = [name for name in entities if name not in embedded_targets]
    if not roots:
        # Fully cyclic / orphan-free graph — nothing to anchor on. Leave as-is
        # rather than guess; the caller's diff will surface the problem.
        return meta

    result: Dict[str, Any] = {}

    # Preserve any meta-level scratch keys (e.g. ``__db_name``) untouched.
    for k, v in meta.items():
        if k.startswith("__"):
            result[k] = v

    # Walk each root's subtree independently. ``_walk_embedded`` writes into
    # ``result`` in-place, keyed by dotted path, so multiple roots contribute
    # disjoint key ranges.
    for root_name in roots:
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
    """Compare two meta schema dicts (from db_to_dict()) and return structured diff."""
    from diff.engine import compute_diff
    from diff.formatters import to_validation_report
    diff = compute_diff(actual, expected)
    return to_validation_report(diff, actual, expected)


def _resolve_target_file(config_key: str, target_type: str):
    """Resolve the target native file for validation."""
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
    """Layer 1: Compare migration Meta V2 result against expected target schema."""
    from config import SOURCE_TYPE_DOCUMENT
    from Schema.adapters import ADAPTER_REGISTRY
    from core import db_to_dict

    target_file = _resolve_target_file(config_key, target_type)
    if not target_file:
        # "Other reasons" rather than "N/A": this layer was skipped because
        # of *external* state (no expected target file registered for this
        # config), not because of a script or adapter bug. Makes the verdict
        # source unambiguous to the user.
        return {"passed": None, "summary": f"Other reasons (no target file for {config_key})", "details": {}}

    adapter_class = ADAPTER_REGISTRY.get(target_type)
    if not adapter_class:
        return {"passed": None, "summary": f"Other reasons (no adapter for {target_type})", "details": {}}

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
