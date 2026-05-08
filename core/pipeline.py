"""Pipeline orchestration — the four-step flow that turns a source schema into a target one.

``run_migration`` is the public entry point used by main.py and the web UI;
internally it sequences ``run_load`` (parse SMILE + load source), constructs
a ``SchemaTransformer``, calls ``run_apply`` (execute every operation),
then ``run_export`` (paradigm-normalize + adapter export).

This module also assembles ``SchemaTransformer`` from its four handler
mixins and the base class. It is the assembly point — placing the class
here (rather than in ``core/__init__.py``) keeps the package init free of
imports that would otherwise create cycles when downstream code imports
``run_migration`` and indirectly imports the mixins.
"""
import copy
import logging
import dataclasses
from typing import Any, Dict

from Schema.unified_meta_schema import DatabaseType
from Schema.adapters import ADAPTER_REGISTRY
from config import (
    MIGRATION_CONFIGS,
    SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT,
    SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR,
)

from core.transformer import SchemaTransformerBase
from core.handlers.structural import StructuralHandlersMixin
from core.handlers.crud import CRUDHandlersMixin
from core.handlers.keys_constraints import KeysConstraintsHandlersMixin
from core.handlers.reshape import ReshapeHandlersMixin
from core.serialization import (
    db_to_dict, db_to_source_dict, parse_original_source,
)
from core.normalization import (
    _calculate_changes,
    normalize_entity_kinds,
    normalize_document_cardinality,
    normalize_document_full_paths,
)

logger = logging.getLogger(__name__)


# SMILE syntax highlighting data (single source of truth for web_server.py frontend)
# Generated from grammar token definitions — update here when grammar changes
SMILE_SYNTAX = {
    "keywords": [
        # Header keywords
        'MIGRATION', 'FROM', 'TO', 'USING', 'AS', 'INTO', 'WITH', 'WHERE', 'IN', 'KEY', 'AND', 'ON',
        # Database model types
        'RELATIONAL', 'DOCUMENT', 'GRAPH', 'COLUMNAR',
        # Structure operations (shared by both grammars)
        'NEST', 'UNNEST', 'FLATTEN', 'UNFLATTEN', 'UNWIND', 'WIND',
        # CRUD verbs (Generalized grammar uses these directly)
        'ADD', 'DELETE', 'REMOVE', 'RENAME', 'COPY', 'MOVE', 'MERGE', 'SPLIT', 'CAST', 'RECARD', 'TRANSFORM',
        # Type parameters
        'PROPERTY', 'ATTRIBUTE', 'ATTRIBUTES', 'CONSTRAINT', 'EMBEDDED', 'ENTITY', 'LABEL', 'RELATIONSHIP',
        # Key types
        'PRIMARY', 'UNIQUE', 'FOREIGN', 'PARTITION', 'CLUSTERING',
        'REFERENCE', 'REFERENCES', 'COLUMNS', 'STRUCTURE',
        # Cardinality
        'CARDINALITY', 'ONE_TO_ONE', 'ONE_TO_MANY', 'ZERO_TO_ONE', 'ZERO_TO_MANY',
        # Specific grammar compound keywords
        'ADD_PROPERTY', 'ADD_EMBEDDED', 'ADD_ENTITY', 'ADD_LABEL',
        'ADD_PRIMARY_KEY', 'ADD_FOREIGN_KEY', 'ADD_UNIQUE_KEY',
        'ADD_PARTITION_KEY', 'ADD_CLUSTERING_KEY',
        'ADD_CONSTRAINT',
        'DELETE_PROPERTY', 'DELETE_EMBEDDED', 'DELETE_ENTITY', 'DELETE_LABEL',
        'DELETE_PRIMARY_KEY', 'DELETE_UNIQUE_KEY', 'DELETE_FOREIGN_KEY',
        'DELETE_PARTITION_KEY', 'DELETE_CLUSTERING_KEY',
        'DELETE_CONSTRAINT',
        'RENAME_PROPERTY', 'RENAME_ENTITY',
        'COPY_PROPERTY', 'COPY_ENTITY', 'MOVE_PROPERTY',
        'CAST_PROPERTY', 'CAST_CONSTRAINT',
        'NODE', 'DOCUMENT_ID',
        # ADD_CONSTRAINT body keywords (REFERENCE/CHECK/EXISTENCE branches)
        'LOGICAL', 'EXISTENCE', 'CHECK', 'MATCHES', 'RAW',
        'NOT', 'OR', 'IS',
    ],
    "types": [
        'String', 'Text', 'Int', 'Integer', 'Long', 'Double', 'Float',
        'Decimal', 'Boolean', 'Date', 'DateTime', 'Timestamp', 'UUID', 'Binary',
    ],
}


# Module-level constant: maps SOURCE_TYPE string -> DatabaseType enum.
# Used by run_export to set the result Database's db_type before passing
# it to the target adapter.
_DB_TYPE_MAP = {
    SOURCE_TYPE_RELATIONAL: DatabaseType.RELATIONAL,
    SOURCE_TYPE_DOCUMENT: DatabaseType.DOCUMENT,
    SOURCE_TYPE_GRAPH: DatabaseType.GRAPH,
    SOURCE_TYPE_COLUMNAR: DatabaseType.COLUMNAR,
}


class SchemaTransformer(
    StructuralHandlersMixin,
    CRUDHandlersMixin,
    KeysConstraintsHandlersMixin,
    ReshapeHandlersMixin,
    SchemaTransformerBase,
):
    """Transform a schema based on parsed SMILE operations.

    All instance state and shared helpers live in ``SchemaTransformerBase``;
    each ``_handle_*`` operation method comes from one of the four handler
    mixins. The class body is intentionally empty — no orchestration logic
    belongs here, just the multi-inheritance composition.
    """
    pass



def run_load(source_file, smile_file, source_type: str):
    """Step 1 — Resolve adapters, read source schema + SMILE script, parse the
    script, and snapshot Meta V1.

    Returns:
        (source_adapter, source_db, meta_v1_db, smile_content, raw_source,
         operations, errors)
        — `errors` is a non-empty list when the SMILE script has parse errors;
        callers should bail out in that case.
    """
    from parser.factory import parse_smile_auto

    source_adapter = ADAPTER_REGISTRY.get(source_type)
    if not source_adapter:
        raise ValueError(f"No adapter for source type: {source_type}. Available: {list(ADAPTER_REGISTRY.keys())}")

    raw_source = source_file.read_text(encoding='utf-8') if hasattr(source_file, 'read_text') else open(source_file, encoding='utf-8').read()
    smile_content = smile_file.read_text(encoding='utf-8') if hasattr(smile_file, 'read_text') else open(smile_file, encoding='utf-8').read()

    # Source DDL → Meta V1 (Database)
    source_db = source_adapter.load_from_file(str(source_file), "source")
    meta_v1_db = copy.deepcopy(source_db)

    context, operations, errors = parse_smile_auto(str(smile_file))
    return source_adapter, source_db, meta_v1_db, smile_content, raw_source, operations, errors


def run_apply(transformer: 'SchemaTransformer', operations) -> tuple:
    """Step 2 — Apply parsed operations to a transformer's database, tracking
    per-op success/skip/error and a diff of the entities each op touched.

    Three terminal statuses are recorded per op:

      * ``success`` — handler returned a truthy ``OperationResult``.
      * ``skipped`` — handler returned a falsy ``OperationResult`` (with a
        ``reason``); a *deliberate* business-level skip such as "entity
        not found" or "no-op". Counted in ``skipped_count``.
      * ``error``   — the handler raised an unexpected exception. Almost
        always a real bug in the handler or its inputs, *not* a deliberate
        skip. Counted in its own ``error_count`` so callers can fail loud
        on bugs without conflating them with intentional skips. The full
        traceback is logged via ``logger.exception`` (no longer just the
        message), so the underlying defect is visible in CI output.

    The pipeline does not abort on error so that subsequent ops still get
    reported — a single broken handler shouldn't blank out the rest of the
    migration trace. Callers that want strict behavior can assert
    ``error_count == 0`` after the call (test_full_flow does this via the
    ``operations_detail`` status field).

    Performance:
      - One ``db_to_dict`` snapshot per op (the previous "after" is reused
        as the next "before"), down from two.
      - ``status == "skipped"`` ops reuse ``prev_snapshot`` directly — the
        handler returned via an early-return guard before mutating, so
        the database is byte-identical to the previous snapshot and we
        can skip serialization entirely. ``status == "error"`` still
        snapshots, since an exception may have been thrown mid-mutation.
      - Handlers may opportunistically call ``self._touch(name)`` to
        declare which entities they modified. When set,
        ``_calculate_changes`` skips deep-compare for unchanged entities.

    Returns:
        (operations_detail, success_count, skipped_count, error_count)
    """
    operations_detail = []
    success_count = 0
    skipped_count = 0
    error_count = 0

    # One snapshot before the first op; reuse the "after" of step N as the "before"
    # of step N+1 so we only serialize the database once per op (not twice).
    prev_snapshot = db_to_dict(transformer.database)

    for i, op in enumerate(operations):
        prev_count = len(transformer.database.entity_types)
        transformer._touched = []           # reset per-op hint

        handler = transformer._handlers.get(op.op_type)
        reason = None
        if handler:
            try:
                result = handler(op.params)
                if result:
                    status = "success"
                    success_count += 1
                else:
                    status = "skipped"
                    skipped_count += 1
                    reason = result.reason if hasattr(result, "reason") else None
            except Exception as e:
                # Bugs in handlers should never be conflated with deliberate
                # skips. logger.exception() includes the full traceback so the
                # underlying defect is visible without re-running. The op is
                # recorded as status="error" and counted separately so that
                # CI / callers can fail loud rather than swallow real bugs.
                logger.exception(
                    "Step %d: Operation %s raised %s — handler bug",
                    i + 1, op.op_type.name, type(e).__name__,
                )
                status = "error"
                reason = f"{type(e).__name__}: {e}"
                error_count += 1
        else:
            logger.info(f"Unknown operation type: {op.op_type.name}")
            status = "skipped"
            reason = f"unknown op_type: {op.op_type.name}"
            skipped_count += 1

        new_count = len(transformer.database.entity_types)
        if status == "skipped":
            # Handler returned via early-return guard without mutating —
            # reuse prev_snapshot to avoid a redundant db_to_dict serialization.
            after_snapshot = prev_snapshot
        else:
            after_snapshot = db_to_dict(transformer.database)
        # Pass the hint when the handler reported what it touched; else None
        # (full-DB diff, legacy behavior).
        hint = list(transformer._touched) if transformer._touched else None
        changes_detail = _calculate_changes(prev_snapshot, after_snapshot, op, hint)

        detail = {
            "step": i + 1,
            "type": op.op_type.name,
            "original_keyword": op.original_keyword if op.original_keyword else op.op_type.name,
            "params": dataclasses.asdict(op.params),
            "entity_count_before": prev_count,
            "entity_count_after": new_count,
            "changes": changes_detail,
            "status": status,
        }
        if reason:
            detail["reason"] = reason
        operations_detail.append(detail)
        # roll forward — current "after" becomes next "before"
        prev_snapshot = after_snapshot

    transformer._touched = None
    return operations_detail, success_count, skipped_count, error_count


def run_export(transformer: 'SchemaTransformer', source_type: str, target_type: str) -> tuple:
    """Step 3 — Set target db_type, normalize entity_kind, and export Meta V2
    via the target adapter.

    Returns:
        (result_db, exported_target, target_adapter)
    """
    target_adapter = ADAPTER_REGISTRY.get(target_type)
    if not target_adapter:
        raise ValueError(f"No adapter for target type: {target_type}. Available: {list(ADAPTER_REGISTRY.keys())}")

    result_db = transformer.database
    if target_type not in _DB_TYPE_MAP:
        raise ValueError(f"Unknown target_type: {target_type}")
    result_db.db_type = _DB_TYPE_MAP[target_type]

    # Skip-list now lives on each EntityType.kind_locked (set by CAST_ENTITY).
    # Two passes with a single responsibility each — the previous combined
    # function silently mixed entity-kind translation with Document-specific
    # cardinality promotion, which made the call site read ambiguously.
    normalize_entity_kinds(result_db, target_type)
    normalize_document_cardinality(result_db, source_type)
    # Document-specific: promote any simple-name embedded entities (left
    # behind by NEST / UNFLATTEN when source-side embedded chains were
    # carried forward) to canonical ``parent.child`` full paths. This is
    # the structural counterpart of the Mongo adapter's parse-time
    # ``parent_path=object_name`` recursion and closes the round-trip
    # cycle ``Mongo -> X -> Mongo'`` that previously diverged on entity
    # full_path naming.
    if target_type == SOURCE_TYPE_DOCUMENT:
        normalize_document_full_paths(result_db)
    exported_target = target_adapter.export(result_db)
    return result_db, exported_target, target_adapter


def run_migration(direction: str) -> Dict[str, Any]:
    """
    Run a complete migration and return results.

    Args:
        direction: a key in MIGRATION_CONFIGS (e.g. "northwind_r2d_specific").

    Returns:
        Dictionary with migration results including source, meta_v1, result, changes, etc.
    """
    if direction not in MIGRATION_CONFIGS:
        return {"error": f"Unknown direction: {direction}. Available: {list(MIGRATION_CONFIGS.keys())}"}

    config = MIGRATION_CONFIGS[direction]
    source_file = config.source_file
    smile_file = config.smile_file
    source_type = config.source_type
    target_type = config.target_type

    for f in [source_file, smile_file]:
        if not f.exists():
            return {"error": f"File not found: {f}"}

    # Step 1: source DDL → Meta V1, parse SMILE
    try:
        (source_adapter, source_db, meta_v1_db, smile_content, raw_source,
         operations, errors) = run_load(source_file, smile_file, source_type)
    except ValueError as e:
        return {"error": str(e)}
    if errors:
        return {"error": f"SMILE parse errors: {errors}"}

    # Step 2: apply ops → Meta V2
    transformer = SchemaTransformer(source_db)
    operations_detail, success_count, skipped_count, error_count = run_apply(transformer, operations)

    # Step 3: normalize + export Meta V2 → target DDL
    try:
        result_db, exported_target, _ = run_export(transformer, source_type, target_type)
    except ValueError as e:
        return {"error": str(e)}

    result_dict = {
        "source_type": source_type,
        "target_type": target_type,
        "raw_source": raw_source,
        "exported_target": exported_target,
        "smile_content": smile_content,
        "smile_file": smile_file.name,
        "operations_detail": operations_detail,
        "original_source": parse_original_source(raw_source, source_type),
        "target_nested": parse_original_source(exported_target, target_type),
        "source": db_to_source_dict(meta_v1_db, source_type),
        "meta_v1": db_to_dict(meta_v1_db),
        "result": db_to_dict(result_db),
        "target_with_db_types": db_to_source_dict(result_db, target_type),
        "changes": transformer.changes,
        "key_registry": transformer.source_key_snapshot,
        "operations_count": len(operations),
        "stats": {
            "source_count": len(meta_v1_db.entity_types),
            "result_count": len(result_db.entity_types)
        },
        "execution_stats": {
            "total": len(operations),
            "success": success_count,
            "skipped": skipped_count,
            "error": error_count,
        },
        "smile_syntax": SMILE_SYNTAX,
    }

    # Unified three-layer pipeline validation + blame attribution.
    # Top-level keys validation_layer0 / validation_meta / validation_export
    # are surfaced for the CLI / web UI / tests; ``validation_meta`` and
    # ``validation_export`` keep their pre-Layer-0 names for backwards
    # compatibility with existing front-end code that reads them directly.
    try:
        from validation.pipeline import validate_pipeline
        v = validate_pipeline(result_dict, target_type, direction)
        result_dict["validation_layer0"] = v["layer0"]
        result_dict["validation_meta"] = v["layer1"]
        result_dict["validation_export"] = v["layer2"]
        result_dict["validation_blame"] = v["blame"]
        result_dict["validation_summary"] = v["summary"]
    except Exception as e:
        err = {"passed": None, "summary": f"Error: {e}", "details": {}}
        result_dict["validation_layer0"] = err
        result_dict["validation_meta"] = err
        result_dict["validation_export"] = err
        result_dict["validation_blame"] = "unverifiable"
        result_dict["validation_summary"] = f"validation crashed: {e}"

    return result_dict
