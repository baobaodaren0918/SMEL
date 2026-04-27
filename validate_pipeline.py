"""
Unified pipeline validation with explicit blame attribution.

Wraps Layer 1 (validate_meta — Meta V2 vs expected) and Layer 2
(validate_export — round-trip vs expected) into a single call, and assigns
blame:

* ``smile_script``   — Layer 1 failed: the SMILE script produced a wrong Meta V2
* ``adapter``        — Layer 1 passed but Layer 2 failed: the adapter mis-translates Meta V2 → DDL → Meta
* ``ok``             — both layers passed
* ``unverifiable``   — at least one layer is N/A (no expected target file or no adapter)

Existing top-level ``validation_meta`` / ``validation_export`` keys are still
populated for backward compatibility with the web UI; the new
``validation_blame`` key surfaces the diagnosis explicitly.
"""
from typing import Dict, Any

from validate_meta import validate_meta
from validate_export import validate_export


def validate_pipeline(result_dict: Dict[str, Any], target_type: str,
                      config_key: str = "") -> Dict[str, Any]:
    """Run both validation layers and produce a single unified result.

    Returns a dict with:
      * layer1: the Layer 1 (Meta V2 vs expected) report
      * layer2: the Layer 2 (round-trip vs expected) report
      * blame:  one of {"ok", "smile_script", "adapter", "unverifiable"}
      * summary: short human-readable line for the UI / CLI
    """
    layer1 = validate_meta(result_dict, target_type, config_key)
    layer2 = validate_export(result_dict, target_type, config_key)

    l1_passed = layer1.get("passed")
    l2_passed = layer2.get("passed")

    if l1_passed is None or l2_passed is None:
        blame = "unverifiable"
        summary = "validation skipped (no expected target file or adapter)"
    elif l1_passed and l2_passed:
        blame = "ok"
        summary = "both layers passed"
    elif not l1_passed:
        # Layer 1 fail dominates — the SMILE script produced the wrong Meta V2,
        # so any Layer 2 outcome is a downstream consequence.
        blame = "smile_script"
        summary = "Layer 1 failed → SMILE script produced wrong Meta V2"
    else:
        # l1_passed and not l2_passed — Meta V2 matches expected, but the
        # adapter export/round-trip diverges → adapter is the culprit.
        blame = "adapter"
        summary = "Layer 1 passed but Layer 2 failed → adapter export/parse mismatch"

    return {
        "layer1": layer1,
        "layer2": layer2,
        "blame": blame,
        "summary": summary,
    }
