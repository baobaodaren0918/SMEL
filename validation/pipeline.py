"""
Unified pipeline validation with explicit blame attribution.

Three independent layers, evaluated in order, with the first failing layer
dominating the diagnosis:

* **Layer 0** (``derive_layer0``)  — *Did the SMILE script run cleanly?*
  Pass criteria: every operation reached terminal status ``"success"``,
  no ``"error"`` and no deliberate ``"skipped"``, and at least one entity
  is present in the result database. The check is derived from
  ``result_dict["execution_stats"]`` and ``result_dict["operations_detail"]``,
  both populated by ``core.run_apply``.

  Layer 0 is intentionally strict on ``skipped`` — a deliberate handler
  skip is a sign the script tried to operate on something that wasn't
  there (e.g. ``DELETE_PROPERTY foo.bar`` when ``foo.bar`` doesn't
  exist), which is almost always a script-side mistake. The pipeline
  itself does **not** abort on skip/error — every subsequent op is still
  attempted and recorded. Layer 0 only governs the *verdict*.

* **Layer 1** (``validate_meta``) — *Is Meta V2 correct?*
  Compares the SMILE-script-produced Meta V2 against the meta parsed
  from the expected target native file. Failure means the SMILE script
  produced the wrong meta model.

* **Layer 2** (``validate_export``) — *Is the target adapter correct?*
  Re-parses the exported native target and compares against the meta
  parsed from the expected target file. Failure means
  ``parse_T(export_T(M_V2)) ≠ parse_T(T_native)`` — i.e. the adapter's
  forward-engineering ``parse ∘ export`` cycle dropped or mistranslated
  information.

Blame priority (highest first):
    script_failed > smile_script > adapter > unverifiable > ok

* ``script_failed``  — Layer 0 failed. Downstream layers may report
                       further failures but those are consequences, not
                       independent diagnoses; we report the upstream
                       cause.
* ``smile_script``   — Layer 0 passed but Layer 1 failed: the script
                       ran cleanly yet produced the wrong Meta V2.
* ``adapter``        — Layer 1 passed but Layer 2 failed: Meta V2 is
                       correct, but the target adapter's export/parse
                       cycle corrupts it.
* ``unverifiable``   — Layer 0 passed but at least one of Layer 1 / Layer 2
                       is N/A (no expected target file or no adapter for
                       the target type — e.g. the grammar_completeness suite).
* ``ok``             — All three layers passed.

The top-level keys ``validation_layer0`` / ``validation_meta`` /
``validation_export`` / ``validation_blame`` / ``validation_summary`` on
the result dict are populated by ``core.run_migration`` from this
module's return value, and consumed by the CLI (``main.py``) and the
web UI (``smile-app.js``) to render per-layer cards.
"""
from typing import Any, Dict, List

from validation.meta import validate_meta
from validation.export import validate_export
from validation.text_diff import validate_text_diff


def derive_layer0(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Layer 0: did the SMILE script run cleanly?

    Returns a dict with the same shape as Layer 1 / Layer 2 reports
    (``passed`` / ``summary`` / ``details``) so downstream consumers can
    render all three layers uniformly.

    Pass criteria (all must hold):

    * ``total > 0``        — at least one operation was attempted
    * ``error == 0``       — no handler raised an unexpected exception
    * ``skipped == 0``     — no operation returned ``OperationResult.skipped``
    * result has ≥1 entity — the database isn't empty after applying ops

    On failure, ``details.failed_steps`` lists every non-``success`` op
    with its step number, op type, original SMILE keyword, status, and
    the reason the handler reported. This is the user-facing answer to
    "where did the script fail?".
    """
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
    """Choose which layer to blame and produce a human-readable summary.

    Verdict precedence:

    * ``script_failed`` — Layer 0 fails. Dominates because a broken script
      run produces a partial / wrong Meta V2, so downstream layers'
      outcomes are not independent evidence.
    * ``unverifiable`` — Layer 1 or Layer 2 cannot be evaluated (no
      expected target file or no adapter for the target type). Layer 3
      missing alone does not trigger this verdict because the text-level
      check has its own skip semantics that we surface in the L3 card.
    * ``both`` — Layer 1 AND Layer 2 both fail. Distinct verdict so a
      double meta-level failure is not silently collapsed onto a single
      layer.
    * ``smile_script`` — only Layer 1 fails (script error).
    * ``adapter`` — only Layer 2 fails (adapter export/parse error).
    * ``text_diff`` — Layer 1 and Layer 2 both pass, but Layer 3 fails.
      Surfaces a PSM-style drift between the FE-exported native and the
      project's hand-written ground truth (set-based text comparison).
      This is reported as its own verdict because earlier ``ok`` runs
      with a failing L3 hid real adapter / handler bugs (e.g. Cassandra
      clustering NOT NULL leaking into PG / Mongo, the maxLength
      cross-paradigm leak, the Neo4j ``CREATE CONSTRAINT`` vs ``// Key:``
      style mismatch). Treating the L3 failure as part of the verdict
      makes that class of bug visible without burying it inside ``ok``.
    * ``ok`` — Layer 1, Layer 2, and (if evaluated) Layer 3 all pass.
    """
    # Script Execution check dominates: if the script didn't run cleanly,
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
    """Run all validation layers and produce a single unified result.

    Returns a dict with:
      * ``layer0``   — Layer 0 (script execution) report
      * ``layer1``   — Layer 1 (Meta V2 vs expected) report
      * ``layer2``   — Layer 2 (round-trip vs expected) report
      * ``layer3``   — Layer 3 (exported text vs hand-written native, set-based) report
      * ``blame``    — one of {"script_failed", "smile_script", "adapter",
                        "both", "unverifiable", "ok"} -- Layer 3 does not
                        participate in blame attribution; an L3 failure when
                        L1/L2 pass is a *style alignment* signal (the FE
                        emits valid PSM but in a form that diverges from the
                        hand-written ground truth), not a correctness bug.
                        It is reported alongside the verdict so the user
                        can act on it independently.
      * ``summary``  — short human-readable line for the UI / CLI
    """
    layer0 = derive_layer0(result_dict)
    layer1 = validate_meta(result_dict, target_type, config_key)
    layer2 = validate_export(result_dict, target_type, config_key)
    layer3 = validate_text_diff(result_dict, target_type, config_key)

    blame, summary = derive_blame(layer0, layer1, layer2, layer3)

    return {
        "layer0": layer0,
        "layer1": layer1,
        "layer2": layer2,
        "layer3": layer3,
        "blame": blame,
        "summary": summary,
    }
