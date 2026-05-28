"""Unified pipeline validation with explicit blame attribution.

The pipeline applies two preparation steps and three authoritative layers:
  - Layer Preparation I  (``derive_layer0``):  did the SMILE script run cleanly?
  - Layer Preparation II (``validate_integrity``): is the resulting metamodel
    internally consistent (no dangling UUIDs, no UP.meta_id duplicates)?
  - Layer 1 (``validate_meta``): does Meta V2 match the expected target?
  - Layer 2 (``validate_export``): does export -> re-parse round-trip match?
  - Layer 3 (``validate_text_diff``): does the exported native text match
    the ground-truth target under set-based normalization?

Layer 1/2/3 are the thesis-documented correctness layers; the two
Preparation steps are pre-validation gates that surface different
failure classes (script crash vs. internal model inconsistency)."""
from typing import Any, Dict, List

from validation.meta import validate_meta
from validation.export import validate_export
from validation.integrity import validate_integrity
from validation.text_diff import validate_text_diff


def derive_layer0(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Layer Preparation I: did the SMILE script run cleanly?"""
    stats = result_dict.get("execution_stats", {})
    total = stats.get("total", 0)
    success = stats.get("success", 0)
    skipped = stats.get("skipped", 0)
    error = stats.get("error", 0)

    # Real entities only — strip the bookkeeping sidecars
    # (``__relationship_types__`` / ``__db_meta__``).
    result_entities = {
        k for k in result_dict.get("result", {}) if not k.startswith("__")
    }

    passed = (
        total > 0
        and error == 0
        and skipped == 0
        and len(result_entities) > 0
    )

    if passed:
        return {
            "passed": True,
            "summary": f"PASS ({total} ops succeeded)",
            "details": {
                "total": total,
                "success": success,
                "skipped": 0,
                "error": 0,
                "failed_steps": [],
            },
        }

    # Collect failed steps for the user-facing "where did it fail?" answer.
    # Both ``skipped`` and ``error`` are listed — they are different kinds
    # of failure (deliberate skip vs unexpected exception) but both are
    # symptoms the user typically wants to see.
    failed_steps: List[Dict[str, Any]] = []
    for op in result_dict.get("operations_detail", []):
        if op.get("status") in ("skipped", "error"):
            failed_steps.append({
                "step": op.get("step"),
                "type": op.get("type"),
                "original_keyword": op.get("original_keyword") or op.get("type"),
                "status": op.get("status"),
                "reason": op.get("reason", ""),
            })

    if total == 0:
        summary = "FAIL (no operations executed — script empty or unparseable)"
    elif len(result_entities) == 0:
        summary = "FAIL (script ran but produced 0 entities)"
    else:
        # ``X errored, Y skipped of Z`` — concise enough for a single status line
        # while still distinguishing the two failure kinds.
        parts = []
        if error:
            parts.append(f"{error} errored")
        if skipped:
            parts.append(f"{skipped} skipped")
        joined = ", ".join(parts) if parts else "0 failed"
        summary = f"FAIL ({joined} of {total})"

    return {
        "passed": False,
        "summary": summary,
        "details": {
            "total": total,
            "success": success,
            "skipped": skipped,
            "error": error,
            "failed_steps": failed_steps,
        },
    }


def derive_blame(layer0: Dict[str, Any], layer1: Dict[str, Any],
                 layer2: Dict[str, Any],
                 layer3: Dict[str, Any]) -> tuple:
    """Pick a verdict from Layer Preparation I + Layer 1/2/3. Preparation I
    dominates, then L1/L2; L3 contributes the ``text_diff`` verdict only
    when L1 and L2 both pass. Layer Preparation II (integrity) is a
    non-blocking diagnostic and is not consumed here."""
    # Layer Preparation I dominates: if the script didn't run cleanly,
    # Layer 1/2/3 outcomes on the partial / wrong Meta V2 don't add
    # information.
    if not layer0.get("passed"):
        return ("script_failed",
                f"Script Execution failed — {layer0.get('summary', '')}")

    l1_passed = layer1.get("passed")
    l2_passed = layer2.get("passed")
    l3_passed = layer3.get("passed")

    if l1_passed is None or l2_passed is None:
        return ("unverifiable",
                "validation skipped (no expected target file or adapter)")

    if not l1_passed and not l2_passed:
        return ("both",
                "Both Layer 1 and Layer 2 failed — Meta V2 is wrong and "
                "the adapter export/parse cycle does not round-trip to the "
                "expected target")

    if not l1_passed:
        return ("smile_script",
                "Layer 1 failed — Meta V2 mismatches expected target")

    if not l2_passed:
        return ("adapter",
                "Layer 2 failed — adapter export/parse cycle mismatches "
                "expected target")

    # Layer 1 and Layer 2 passed; Layer 3 is the final gate.
    if l3_passed is False:
        return ("text_diff",
                "Layer 3 failed — exported native text does not match the "
                "hand-written ground truth under set-based normalization "
                "(PSM style drift)")

    # l3_passed is True, or None (skipped because no normalizer / no target)
    return ("ok",
            "all validation layers passed"
            if l3_passed
            else "Layer 1 and Layer 2 passed (Layer 3 not evaluated)")


def validate_pipeline(result_dict: Dict[str, Any], target_type: str,
                      config_key: str = "") -> Dict[str, Any]:
    """Run Layer Preparation I + II and Layer 1/2/3, and derive a unified
    verdict. Layer Preparation II (integrity) is a non-blocking diagnostic —
    it surfaces dangling UUID references in the post-script metamodel (see
    ``validation/integrity.py``) but does not influence ``blame`` because
    L1/L2 are the authoritative correctness gates."""
    layer0 = derive_layer0(result_dict)
    layer1 = validate_meta(result_dict, target_type, config_key)
    layer2 = validate_export(result_dict, target_type, config_key)
    layer3 = validate_text_diff(result_dict, target_type, config_key)

    # Integrity check runs on the Database object stashed by run_migration
    # at result_dict["__result_db"]. Skipped silently if absent.
    integrity = (validate_integrity(result_dict["__result_db"])
                 if result_dict.get("__result_db") is not None
                 else {"passed": None, "summary": "Other reasons (no result_db)",
                       "violations": []})

    blame, summary = derive_blame(layer0, layer1, layer2, layer3)

    return {
        "layer0": layer0,
        "layer1": layer1,
        "layer2": layer2,
        "layer3": layer3,
        "integrity": integrity,
        "blame": blame,
        "summary": summary,
    }
