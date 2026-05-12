"""Layer 2 Validation: Adapter Export Round-Trip Comparison."""
from typing import Dict, Any

from validation.meta import compare_meta_schemas


def validate_export(result_dict: Dict[str, Any], target_type: str,
                    config_key: str = "") -> Dict[str, Any]:
    """Layer 2: Parse exported target back and compare with expected target schema."""
    from Schema.adapters import ADAPTER_REGISTRY
    from core import db_to_dict
    from validation.meta import _resolve_target_file

    exported_target = result_dict.get("exported_target", "")
    if not exported_target:
        return {"passed": False, "summary": "FAIL (no exported target)", "details": {}}

    target_file = _resolve_target_file(config_key, target_type)
    if not target_file:
        # "Other reasons" (rather than the older "N/A") makes it explicit to
        # the user that this layer was not evaluated due to *external* state
        # (no expected target file registered for this config) — *not*
        # because of a script or adapter bug. Avoids the ambiguity of "N/A".
        return {"passed": None, "summary": f"Other reasons (no target file for {config_key})", "details": {}}

    adapter_class = ADAPTER_REGISTRY.get(target_type)
    if not adapter_class:
        return {"passed": None, "summary": f"Other reasons (no adapter for {target_type})", "details": {}}

    # Step 1: Parse the exported target back into Meta Schema
    try:
        roundtrip_db = _parse_exported(exported_target, target_type, adapter_class)
        roundtrip_meta = db_to_dict(roundtrip_db)
    except Exception as e:
        return {"passed": False, "summary": f"FAIL (error re-parsing export: {e})", "details": {}}

    # Step 2: Parse the expected target native file
    try:
        expected_db = adapter_class.load_from_file(str(target_file))
        expected_meta = db_to_dict(expected_db)
    except Exception as e:
        return {"passed": False, "summary": f"FAIL (error parsing target: {e})", "details": {}}

    # Step 3: Compare round-trip vs expected
    return compare_meta_schemas(roundtrip_meta, expected_meta)


def _parse_exported(exported_text: str, target_type: str, adapter_class) -> Any:
    """Parse exported target text back into a Database object."""
    return adapter_class().parse(exported_text, "roundtrip_validation")
