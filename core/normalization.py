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


def normalize_entity_kinds(db: Database, target_type: str) -> None:
    """Convert each entity's ``entity_kind`` to match the target paradigm.

    Cross-model migrations (e.g., R→G, G→R, D→C) leave entities tagged with
    the source paradigm's kind. The target adapter expects every non-EDGE
    entity to be in its own paradigm (TABLE / DOCUMENT / VERTEX /
    WIDE_COLUMN_TABLE), so this pass rewrites those tags in place.

    Document target carries an extra distinction: entities that are the
    target of an ``Embedded`` relationship become ``EMBEDDED`` rather than
    ``DOCUMENT`` (which is reserved for root collections). This matches the
    parse-time labelling produced by ``MongoDBAdapter._parse_object_schema``
    and keeps the meta model consistent in both directions.

    Entities marked ``kind_locked = True`` (set by ``CAST_ENTITY``) are
    preserved as-is — the user explicitly chose a kind that should survive
    paradigm normalization. EDGE entities are never normalized — they are
    relationship-type artifacts that don't belong to any single paradigm's
    "table" concept.
    """
    target_kind = _ENTITY_KIND_DEFAULT.get(target_type, EntityKind.TABLE)

    # For Document target, identify embedded entities (those that are the
    # target of any Embedded relationship) so we can label them EMBEDDED
    # rather than DOCUMENT.
    embedded_targets = set()
    if target_type == SOURCE_TYPE_DOCUMENT:
        for entity in db.entity_types.values():
            for rel in entity.relationships:
                if isinstance(rel, Embedded):
                    embedded_targets.add(rel.aggregates)

    for name, entity in db.entity_types.items():
        if entity.kind_locked:
            continue
        if entity.entity_kind == EntityKind.EDGE:
            continue  # EDGE entities are relationship types, never normalize
        # Document target: split into DOCUMENT (root collection) vs
        # EMBEDDED (sub-document). Other paradigms have no embedded concept,
        # so every entity ends up as a top-level structure.
        if (target_type == SOURCE_TYPE_DOCUMENT
                and entity.full_path in embedded_targets):
            desired = EntityKind.EMBEDDED
            desired_is_root = False
        else:
            desired = target_kind
            desired_is_root = True
        if entity.entity_kind != desired:
            entity.entity_kind = desired
        # Keep ``is_root`` aligned with the entity_kind decision so handler
        # outputs (e.g. NEST/UNFLATTEN that produce sub-documents) and adapter
        # parses converge on the same convention.
        if entity.is_root != desired_is_root:
            entity.is_root = desired_is_root


def normalize_document_full_paths(db: Database) -> None:
    """Walk Embedded relationships from each root entity and rewrite each
    embedded entity's ``object_name`` (full_path) to be
    ``parent_full_path + [aggr_name]``.

    Why this exists
    ---------------
    Handlers like ``NEST`` / ``UNFLATTEN`` that create new embedded entities
    only know the local alias they are introducing — they cannot, on their
    own, know the full chain of ancestors that the entity will end up under.
    A nested NEST (``NEST a IN parent.child`` where ``a`` itself contains
    further embedded children) leaves those grandchildren still pointing
    at their old, source-side full paths.

    This pass closes the loop: from each root entity, walk every
    ``Embedded`` relationship, recompute the ideal full path
    (``parent.aggr_name``), and rename both the embedded entity (its
    ``object_name`` and the dictionary key on ``database.entity_types``) and
    the ``Embedded.aggregates`` pointer that names it. The walk is
    breadth-first to avoid re-renaming an entity that has already been
    moved earlier in the traversal.

    Idempotent: running this on an already-normalized database is a no-op.
    Only called when the target paradigm is Document (the only paradigm
    where embedded entity full paths are part of the canonical
    representation). Cross-paradigm round-trip cycles
    (``Mongo -> X -> Mongo'``) close cleanly with this pass in place.
    """
    # Roots: any entity that is not the embedded target of another entity.
    embedded_targets = set()
    for e in db.entity_types.values():
        for rel in e.relationships:
            if isinstance(rel, Embedded):
                embedded_targets.add(rel.aggregates)
    roots = [e for e in db.entity_types.values()
             if e.full_path not in embedded_targets]

    # BFS rename map: old_full_path -> new_full_path.
    rename_map: Dict[str, str] = {}

    def _walk(parent_entity, parent_path: str) -> None:
        for rel in parent_entity.relationships:
            if not isinstance(rel, Embedded):
                continue
            child = db.get_entity_type(rel.aggregates)
            if child is None:
                continue
            target_path = f"{parent_path}.{rel.aggr_name}"
            old_path = child.full_path
            if old_path != target_path:
                rename_map[old_path] = target_path
                child.object_name = target_path.split(".")
                rel.aggregates = target_path
            else:
                # Already aligned — still update aggregates in case it
                # pointed to a stale simple name even though the entity
                # itself was renamed in an earlier walk.
                rel.aggregates = target_path
            _walk(child, target_path)

    for root in roots:
        _walk(root, root.full_path)

    # Apply dictionary key updates in one pass after the walk so we do not
    # mutate ``db.entity_types`` while iterating it.
    for old, new in rename_map.items():
        if old in db.entity_types and old != new:
            entity = db.entity_types.pop(old)
            db.entity_types[new] = entity


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
