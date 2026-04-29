"""Handlers for entity-level reshaping ops — MERGE, SPLIT, CAST_PROPERTY, CAST_ENTITY.

These are the "semantic restructure" ops: MERGE collapses two entities
into one, SPLIT vertically partitions an entity, CAST_PROPERTY changes a
column's data type, CAST_ENTITY changes an entity's paradigm-kind. They
don't share helpers with the structural NEST/UNNEST family — the nesting
ops shuffle existing trees, while these ops change identity / topology.
"""

import copy
import logging

from typing import Dict, List, Optional, Any

from Schema.unified_meta_schema import (
    Database, DatabaseType, EntityType, EntityKind, Property,
    UniqueConstraint, ForeignKeyConstraint, UniqueProperty, ForeignKeyProperty, PKTypeEnum,
    Reference, Embedded, Edge, Cardinality,
    PrimitiveDataType, PrimitiveType, ListDataType,
    TypeMappings,
    CARDINALITY_MAP, KEY_TYPE_MAP, TYPE_STR_MAP,
)
from parser.params import (
    OpParams, OperationResult,
    NestParams, UnnestParams, FlattenParams, UnflattenParams,
    WindParams, UnwindParams,
    AddEntityParams, DeleteEntityParams, RenameEntityParams, CopyEntityParams,
    AddPropertyParams, DeletePropertyParams, RenamePropertyParams,
    CopyPropertyParams, MovePropertyParams,
    AddKeyParams, DeleteKeyParams, KeyType,
    AddForeignKeyParams, DeleteForeignKeyParams, CastConstraintParams,
    CastEntityParams,
    AddEmbeddedParams, DeleteEmbeddedParams,
    AddLabelParams, DeleteLabelParams,
    CastPropertyParams, MergeParams, SplitParams,
    RecardParams, TransformParams,
)
from parser.listeners import OpType
from core.transformer import register_handler

logger = logging.getLogger(__name__)



class ReshapeHandlersMixin:
    """Mixin contributing one focused subset of `_handle_*` methods to ``SchemaTransformer``."""

    @register_handler(OpType.MERGE)
    def _handle_merge(self, params: MergeParams) -> OperationResult:
        """MERGE: Merge two entities into one."""
        source1_name = params.source1
        source2_name = params.source2
        target_name = params.target

        source1 = self._get_entity(source1_name, "MERGE")
        source2 = self._get_entity(source2_name, "MERGE")
        if not source1 or not source2:
            return OperationResult.skipped("merge: precondition not met")

        # EDGE entities cannot be merged
        if source1.entity_kind == EntityKind.EDGE:
            logger.error(f"MERGE failed: entity '{source1_name}' is an EDGE entity, MERGE does not support EDGE")
            return OperationResult.skipped("merge: precondition not met")
        if source2.entity_kind == EntityKind.EDGE:
            logger.error(f"MERGE failed: entity '{source2_name}' is an EDGE entity, MERGE does not support EDGE")
            return OperationResult.skipped("merge: precondition not met")

        # Create new entity with combined properties
        new_entity = EntityType(object_name=[target_name])

        # Track old->new meta_id mapping for constraint property_id remap
        meta_id_map = {}

        # Add properties from source1
        for attr in source1.properties:
            new_attr = Property(attr.name, attr.data_type, attr.is_key, attr.is_optional)
            meta_id_map[attr.meta_id] = new_attr.meta_id
            new_entity.add_property(new_attr)

        # Add properties from source2 (avoid duplicates)
        existing_names = {a.name for a in new_entity.properties}
        for attr in source2.properties:
            if attr.name not in existing_names:
                new_attr = Property(attr.name, attr.data_type, attr.is_key, attr.is_optional)
                meta_id_map[attr.meta_id] = new_attr.meta_id
                new_entity.add_property(new_attr)

        # Copy constraints from source1 with remapped property_ids
        has_pk = False
        for constraint in source1.constraints:
            new_c = copy.deepcopy(constraint)
            if new_c.kind == "unique":
                if new_c.is_primary_key:
                    has_pk = True
                for up in new_c.unique_properties:
                    if up.property_id in meta_id_map:
                        up.property_id = meta_id_map[up.property_id]
            elif new_c.kind == "foreign_key":
                for fkp in new_c.foreign_key_properties:
                    if fkp.property_id in meta_id_map:
                        fkp.property_id = meta_id_map[fkp.property_id]
            new_entity.add_constraint(new_c)

        # Copy constraints from source2 (skip duplicate PK)
        for constraint in source2.constraints:
            new_c = copy.deepcopy(constraint)
            if new_c.kind == "unique":
                if new_c.is_primary_key and has_pk:
                    continue  # Skip duplicate primary key
                for up in new_c.unique_properties:
                    if up.property_id in meta_id_map:
                        up.property_id = meta_id_map[up.property_id]
            elif new_c.kind == "foreign_key":
                for fkp in new_c.foreign_key_properties:
                    if fkp.property_id in meta_id_map:
                        fkp.property_id = meta_id_map[fkp.property_id]
            new_entity.add_constraint(new_c)

        # Helper to get relationship identifier
        def _rel_id(r):
            if isinstance(r, Reference): return ('ref', r.ref_name)
            if isinstance(r, Embedded): return ('emb', r.aggr_name)
            if isinstance(r, Edge): return ('edge', r.rel_type_name)
            return ('other', id(r))

        # Copy relationships from source1 (Embedded, Reference, etc.)
        for rel in source1.relationships:
            new_entity.add_relationship(copy.deepcopy(rel))

        # Copy relationships from source2 (avoid duplicates by type+name)
        existing_rel_ids = {_rel_id(r) for r in new_entity.relationships}
        for rel in source2.relationships:
            if _rel_id(rel) not in existing_rel_ids:
                new_entity.add_relationship(copy.deepcopy(rel))

        self.database.add_entity_type(new_entity)

        # Remove source entities if different from target
        removed_sources = []
        if source1_name != target_name:
            self.database.remove_entity_type(source1_name)
            removed_sources.append(source1_name)
        if source2_name != target_name:
            self.database.remove_entity_type(source2_name)
            removed_sources.append(source2_name)

        # Update cross-references in other entities pointing to removed sources
        for old_name in removed_sources:
            for other_entity in self.database.entity_types.values():
                for rel in other_entity.relationships:
                    if hasattr(rel, 'refs_to') and rel.refs_to == old_name:
                        rel.refs_to = target_name
                    if hasattr(rel, 'aggregates') and rel.aggregates == old_name:
                        rel.aggregates = target_name
                    if isinstance(rel, Edge):
                        if rel.source_entity == old_name:
                            rel.source_entity = target_name
                        if rel.target_entity == old_name:
                            rel.target_entity = target_name
            # Update EDGE entity source/target references
            for e in self.database.entity_types.values():
                if e.entity_kind == EntityKind.EDGE:
                    if e.source_entity == old_name:
                        e.source_entity = target_name
                    if e.target_entity == old_name:
                        e.target_entity = target_name

        self._touch(source1_name, source2_name, target_name)
        self.changes.append(f"MERGE:{source1_name},{source2_name}->{target_name}")
        return OperationResult.ok()

    @register_handler(OpType.SPLIT)
    def _handle_split(self, params: SplitParams) -> OperationResult:
        """
        SPLIT: Divide one entity into multiple separate entities (vertical partitioning).

        Reference: André Conrad - "SPLIT Person into Person:id, firstname, lastname AND knows:id, knows"

        Example: SPLIT customers INTO customers:customer_id, company_name, street, city, region; customer_contacts:customer_id, contact_name, phone, fax
          Before: customers { customer_id, company_name, contact_name, phone, fax, street, city, region }
          After:  customers { customer_id, company_name, street, city, region }
                 customer_contacts { customer_id, contact_name, phone, fax }

        Note: Fields can be duplicated across parts (e.g., customer_id in both parts for FK relationship).
        """
        source_name = params.source
        parts = params.parts

        source = self.database.get_entity_type(source_name)
        if not source or not parts:
            return OperationResult.skipped("split: precondition not met")

        # EDGE entities cannot be split
        if source.entity_kind == EntityKind.EDGE:
            logger.error(f"SPLIT failed: entity '{source_name}' is an EDGE entity, SPLIT does not support EDGE")
            return OperationResult.skipped("split: precondition not met")

        pk = source.get_primary_key()
        created_entities = []

        # First pass: create NEW entities (parts with different name than source).
        # Must happen before modifying source, so property copying works.
        source_part_fields = None  # track fields for in-place source modification

        for i, part in enumerate(parts):
            part_name = part["name"]
            part_fields = part.get("fields", [])

            # When part_name == source_name, defer in-place modification to second pass
            if part_name == source_name:
                source_part_fields = part_fields
                created_entities.append(part_name)
                continue

            new_entity = EntityType(object_name=[part_name])

            # Track old->new meta_id mapping for constraint updates
            meta_id_map = {}

            # If fields are explicitly specified, use them
            if part_fields:
                for field_name in part_fields:
                    attr = source.get_property(field_name)
                    if attr:
                        # Create new property with is_key preserved from source
                        new_attr = Property(
                            attr.name, attr.data_type, attr.is_key, attr.is_optional
                        )
                        meta_id_map[attr.meta_id] = new_attr.meta_id
                        new_entity.add_property(new_attr)
            else:
                # Fallback: split properties evenly (old behavior)
                attrs = list(source.properties)
                mid = len(attrs) // 2
                if i == 0:
                    selected_attrs = attrs[:mid] if mid > 0 else attrs[:1]
                else:
                    selected_attrs = attrs[mid:] if mid > 0 else attrs[1:]

                for attr in selected_attrs:
                    new_attr = Property(
                        attr.name, attr.data_type, attr.is_key, attr.is_optional
                    )
                    meta_id_map[attr.meta_id] = new_attr.meta_id
                    new_entity.add_property(new_attr)

            # Each part reuses the source primary key (only if ALL PK attrs are in this part)
            if pk:
                all_pk_in_part = all(up.property_id in meta_id_map for up in pk.unique_properties)
                if all_pk_in_part:
                    new_pk = copy.deepcopy(pk)
                    for up in new_pk.unique_properties:
                        up.property_id = meta_id_map[up.property_id]
                    new_entity.add_constraint(new_pk)

            self.database.add_entity_type(new_entity)
            created_entities.append(part_name)

        # Second pass: modify source in-place (preserves edges, embedded, references)
        if source_part_fields is not None:
            keep_fields = set(source_part_fields)
            attrs_to_remove = [a.name for a in source.properties
                               if a.name not in keep_fields]
            for attr_name in attrs_to_remove:
                source.remove_property(attr_name)

        # Remove source if different from all targets
        if source_name not in [p["name"] for p in parts]:
            self.database.remove_entity_type(source_name)

        parts_str = ",".join(created_entities)
        self._touch(source_name, *created_entities)
        self.changes.append(f"SPLIT:{source_name}->{parts_str}")
        return OperationResult.ok()

    @register_handler(OpType.CAST_PROPERTY)
    def _handle_cast_property(self, params: CastPropertyParams) -> OperationResult:
        """CAST_PROPERTY: Change property data type."""
        target = params.target
        new_type_str = (params.data_type or params.type or "STRING").upper()

        entity, attr_name = self._resolve_entity_attr(target, "CAST_PROPERTY")
        if not entity:
            return OperationResult.skipped("cast_property: precondition not met")

        attr = entity.get_property(attr_name)
        if not attr:
            logger.info(f"CAST_PROPERTY skipped: property '{attr_name}' not found")
            return OperationResult.skipped("cast_property: precondition not met")

        new_type = TYPE_STR_MAP.get(new_type_str, PrimitiveType.STRING)
        attr.data_type = PrimitiveDataType(new_type)
        self._touch(entity.name)
        self.changes.append(f"CAST_PROP:{target}->{new_type_str}")
        return OperationResult.ok()

    @register_handler(OpType.CAST_ENTITY)
    def _handle_cast_entity(self, params: CastEntityParams) -> OperationResult:
        """CAST_ENTITY: Change the entity_kind of an entity type (cross-paradigm type conversion).

        Overrides automatic entity_kind normalization for this entity.
        For VERTEX<->EDGE conversion, use TRANSFORM instead.
        Example: CAST_ENTITY orders TO DOCUMENT
        Example: CAST_ENTITY customers TO GRAPH
        """
        target = params.target
        entity_kind_str = params.entity_kind

        entity = self._get_entity(target, "CAST_ENTITY")
        if not entity:
            return OperationResult.skipped("cast_entity: precondition not met")

        # EDGE entities must use TRANSFORM, not CAST_ENTITY
        if entity.entity_kind == EntityKind.EDGE:
            logger.error(f"CAST_ENTITY failed: entity '{target}' is an EDGE entity, use TRANSFORM INTO ENTITY first")
            return OperationResult.skipped("cast_entity: precondition not met")

        kind_map = {
            "RELATIONAL": EntityKind.TABLE,
            "DOCUMENT": EntityKind.DOCUMENT,
            "GRAPH": EntityKind.VERTEX,
            "COLUMNAR": EntityKind.WIDE_COLUMN_TABLE,
        }

        new_kind = kind_map.get(entity_kind_str)
        if not new_kind:
            return OperationResult.skipped("cast_entity: precondition not met")
        entity.entity_kind = new_kind
        entity.kind_locked = True   # tell normalize_entity_kinds() to skip
        self._touch(target)
        self.changes.append(f"CAST_ENTITY:{target}->{entity_kind_str}")
        return OperationResult.ok()
