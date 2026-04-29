"""Cross-paradigm normalization passes — applied during ``run_export``.

Two single-responsibility helpers:

* ``normalize_entity_kinds`` — flips each non-EDGE entity's ``entity_kind``
  to the target paradigm so the target adapter can export it cleanly.
* ``normalize_document_cardinality`` — promotes ``Embedded`` cardinality
  from optional (``ZERO_TO_*``) to required (``ONE_TO_*``) when migrating
  *into* Document targets, mirroring MongoDB JSON Schema's required-or-not
  binary representation.

Plus ``_calculate_changes`` — thin wrapper around the unified
``database_diff`` engine that produces the per-op UI change record.
"""
from typing import Dict, List, Optional

from Schema.unified_meta_schema import (
    Cardinality, Database, EntityKind, Embedded,
)
from config import (
    SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT,
    SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR,
)


# Default EntityKind for each database type (used by normalize_entity_kinds).
_ENTITY_KIND_DEFAULT = {
    SOURCE_TYPE_RELATIONAL: EntityKind.TABLE,
    SOURCE_TYPE_DOCUMENT:   EntityKind.DOCUMENT,
    SOURCE_TYPE_GRAPH:      EntityKind.VERTEX,
    SOURCE_TYPE_COLUMNAR:   EntityKind.WIDE_COLUMN_TABLE,
}


def _calculate_changes(prev: Dict, after: Dict, op,
                       hint_entity_names: Optional[List[str]] = None) -> Dict:
    """Calculate the changes made by an operation (web-UI shape).

    Thin wrapper around the unified ``database_diff.compute_diff`` core +
    ``database_diff_formatters.to_ui_changes`` formatter. The shared core
    is the *single* source of truth for "how do two snapshots differ"; the
    Layer 1 / Layer 2 validators use the same engine via a different
    formatter.

    ``hint_entity_names`` restricts the per-entity deep-compare loop (the
    handler's ``_touch`` mechanism). Set-difference checks for added/deleted
    entities still scan the full key set so add/delete are never missed.
    """
    from diff.engine import compute_diff
    from diff.formatters import to_ui_changes
    only = set(hint_entity_names) if hint_entity_names is not None else None
    diff = compute_diff(prev, after, only_entities=only)
    return to_ui_changes(diff, prev, after)


def normalize_entity_kinds(db: Database, target_type: str,
                           skip_entities: set = None) -> None:
    """Convert each entity's ``entity_kind`` to match the target paradigm.

    Cross-model migrations (e.g., R→G, G→R, D→C) leave entities tagged with
    the source paradigm's kind. The target adapter expects every non-EDGE
    entity to be in its own paradigm (TABLE / DOCUMENT / VERTEX /
    WIDE_COLUMN_TABLE), so this pass rewrites those tags in place.

    Entities marked ``kind_locked = True`` (set by ``CAST_ENTITY``) are
    preserved as-is — the user explicitly chose a kind that should survive
    paradigm normalization. EDGE entities are never normalized — they are
    relationship-type artifacts that don't belong to any single paradigm's
    "table" concept. The legacy ``skip_entities`` parameter is honored for
    callers that pre-date ``kind_locked``.
    """
    if skip_entities is None:
        skip_entities = set()
    target_kind = _ENTITY_KIND_DEFAULT.get(target_type, EntityKind.TABLE)
    for name, entity in db.entity_types.items():
        if entity.kind_locked or name in skip_entities:
            continue
        if entity.entity_kind == EntityKind.EDGE:
            continue  # EDGE entities are relationship types, never normalize
        if entity.entity_kind != target_kind:
            entity.entity_kind = target_kind


def normalize_document_cardinality(db: Database, source_type: str) -> None:
    """Promote ``Embedded`` relationships to required cardinality for D targets.

    MongoDB's JSON Schema uses a top-level ``required`` array, so reverse
    engineering of a Mongo schema always produces ``ONE_TO_ONE`` for object
    sub-documents and ``ONE_TO_MANY`` for arrays — there is no representation
    for "optional but present-as-empty". When migrating *into* Document from
    a different paradigm, the source ``ZERO_TO_ONE`` / ``ZERO_TO_MANY``
    cardinalities don't round-trip through Mongo's schema, so we promote
    them here. D→D (source already Mongo) is skipped because its
    cardinalities are already in the right shape.
    """
    if source_type == SOURCE_TYPE_DOCUMENT:
        return
    for entity in db.entity_types.values():
        for rel in entity.relationships:
            if isinstance(rel, Embedded):
                if rel.cardinality == Cardinality.ZERO_TO_ONE:
                    rel.cardinality = Cardinality.ONE_TO_ONE
                elif rel.cardinality == Cardinality.ZERO_TO_MANY:
                    rel.cardinality = Cardinality.ONE_TO_MANY
