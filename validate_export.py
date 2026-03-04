"""
Layer 2 Validation: Adapter Export Round-Trip Comparison.

Parses the exported target (DDL/JSON/Cypher/CQL) back into Meta Schema,
then compares against the expected target schema from the native file.
Proves adapter forward engineering correctness.

Pipeline position:
  Meta V2 → [Adapter FE] → Exported Target → [Adapter RE] → Round-trip Meta
                                                                  ↑
                                                     compare with expected Meta
                                                     (from native target file)
"""
from typing import Dict, Any
import json

from validate_meta import compare_meta_schemas


def validate_export(result_dict: Dict[str, Any], target_type: str,
                    config_key: str = "") -> Dict[str, Any]:
    """
    Layer 2: Parse exported target back and compare with expected target schema.

    Args:
        result_dict: Output from run_migration()
        target_type: Target database type
        config_key: Migration config key

    Returns:
        Validation result dict with passed/summary/details
    """
    from config import TARGET_SCHEMA_FILES
    from Schema.adapters import ADAPTER_REGISTRY
    from core import db_to_dict

    # Only validate cross-model Northwind migrations
    source_type = result_dict.get("source_type", "")
    if source_type == target_type:
        return {"passed": None, "summary": "N/A (same-model)", "details": {}}

    if not config_key.startswith("northwind_"):
        return {"passed": None, "summary": "N/A (not Northwind)", "details": {}}

    exported_target = result_dict.get("exported_target", "")
    if not exported_target:
        return {"passed": False, "summary": "FAIL (no exported target)", "details": {}}

    target_file = TARGET_SCHEMA_FILES.get(target_type)
    if not target_file or not target_file.exists():
        return {"passed": None, "summary": f"N/A (no target file for {target_type})", "details": {}}

    adapter_class = ADAPTER_REGISTRY.get(target_type)
    if not adapter_class:
        return {"passed": None, "summary": f"N/A (no adapter for {target_type})", "details": {}}

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
    from config import (
        SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT,
        SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR,
    )

    adapter = adapter_class()

    if target_type == SOURCE_TYPE_RELATIONAL:
        return adapter.parse(exported_text, "roundtrip_validation")
    elif target_type == SOURCE_TYPE_DOCUMENT:
        schema = json.loads(exported_text)
        return adapter.parse(schema, "roundtrip_validation")
    elif target_type == SOURCE_TYPE_GRAPH:
        return adapter.parse_cypher(exported_text, "roundtrip_validation")
    elif target_type == SOURCE_TYPE_COLUMNAR:
        return adapter.parse(exported_text, "roundtrip_validation")
    else:
        raise ValueError(f"Unknown target type: {target_type}")
