"""Handlers for structural reshaping ops — NEST/UNNEST, FLATTEN/UNFLATTEN, WIND/UNWIND.

These are the document-level "rearrange the tree" operators: they don't
add or remove logical fields, they just shift how those fields are
nested. They cluster naturally because their helpers (e.g.
``_build_unnest_target_entity``) are shared across NEST and UNNEST.
"""

import copy
import logging
from typing import List

from Schema.unified_meta_schema import (
    EntityType, Property,
    ForeignKeyConstraint,
    Reference, Embedded, Cardinality,
    PrimitiveDataType, PrimitiveType, ListDataType,
)
from parser.params import (
    OperationResult,
    NestParams, UnnestParams, FlattenParams, UnflattenParams,
    WindParams, UnwindParams,
)
from parser.listeners import OpType
from core.transformer import register_handler

logger = logging.getLogger(__name__)



class StructuralHandlersMixin:
    """Mixin contributing one focused subset of `_handle_*` methods to ``SchemaTransformer``."""

    @register_handler(OpType.NEST)
    def _handle_nest(self, params: NestParams) -> OperationResult:
        """
        NEST: Embed separate table into parent as nested object (denormalization).

        Syntax: NEST suppliers:company_name,phone IN products.supplier WHERE products.supplier_id = suppliers.supplier_id

        Example: NEST suppliers:company_name,phone IN products.supplier WHERE products.supplier_id = suppliers.supplier_id
          Before: products { product_id, supplier_id }
                  suppliers { supplier_id, company_name, phone }
          After:  products { product_id, supplier: { company_name, phone } }

        Parameters:
        - source: suppliers (source entity to embed)
        - target: products (target entity)
        - alias: supplier (embedded field name)
        - properties: [company_name, phone] (properties to embed)
        - source_fk: products.supplier_id (source FK for matching)
        - target_pk: suppliers.supplier_id (target PK for matching)

        Note: source entity is not removed automatically; use DELETE_ENTITY explicitly
        if the source table should be dropped after the embedding.
        """
        source_name = params.source
        target_name = params.target
        alias = params.alias
        properties = params.properties

        source_entity = self._get_entity(source_name, "NEST")
        target_entity = self._get_entity(target_name, "NEST")
        if not source_entity or not target_entity:
            return OperationResult.skipped("nest: precondition not met")

        # Determine embedding cardinality based on FK direction:
        #   - target holds FK to source (e.g., orders.customer_id → customers):
        #     each target has ONE source → embed as object (1..1 or 0..1)
        #   - source holds FK to target (e.g., order_details.order_id → orders):
        #     each target has MANY sources → embed as array (1..n or 0..n)
        cardinality = Cardinality.ONE_TO_ONE
        # Check if SOURCE has FK pointing to TARGET → many-to-one → embed as array
        for rel in source_entity.relationships:
            if isinstance(rel, Reference) and rel.get_target_entity_name() == target_name:
                # Source holds FK to target: many sources per target → ONE_TO_MANY
                cardinality = Cardinality.ONE_TO_MANY if not rel.is_optional else Cardinality.ZERO_TO_MANY
                break
        # Check if TARGET has FK pointing to SOURCE → one-to-one → embed as object
        if cardinality == Cardinality.ONE_TO_ONE:
            for rel in target_entity.relationships:
                if isinstance(rel, Reference) and rel.get_target_entity_name() == source_name:
                    cardinality = Cardinality.ONE_TO_ONE if not rel.is_optional else Cardinality.ZERO_TO_ONE
                    break

        # Create embedded entity with specified properties (or all non-FK properties if not specified)
        fk_attr_names = {rel.ref_name for rel in source_entity.get_references()}
        embedded_entity = EntityType(object_name=[alias])

        nested = params.nested

        if properties:
            # Use specified properties
            for attr_name in properties:
                attr = source_entity.get_property(attr_name)
                if attr:
                    embedded_entity.add_property(Property(attr.name, attr.data_type, False, attr.is_optional))
        else:
            # Use all non-FK properties (backward compatibility)
            for attr in source_entity.properties:
                if attr.name not in fk_attr_names:
                    embedded_entity.add_property(Property(attr.name, attr.data_type, False, attr.is_optional))

        # Copy nested embedded relationships from source entity
        # e.g., NEST company:name, address{street,city} -> copy "address" Embedded from company
        for nested_obj in nested:
            nested_name = nested_obj['name']
            for rel in source_entity.get_embedded():
                if rel.aggr_name == nested_name:
                    embedded_entity.add_relationship(
                        Embedded(aggr_name=nested_name, aggregates=rel.aggregates,
                                 cardinality=rel.cardinality, is_optional=rel.is_optional))
                    break

        # Remove FK reference from target to source
        fk_removed = False
        for rel in list(target_entity.relationships):
            if isinstance(rel, Reference) and rel.get_target_entity_name() == source_name:
                # Also remove matching ForeignKeyConstraint
                fk_attr = target_entity.get_property(rel.ref_name)
                if fk_attr:
                    target_entity.constraints = [
                        c for c in target_entity.constraints
                        if not (c.kind == "foreign_key" and
                                any(fkp.property_id == fk_attr.meta_id for fkp in c.foreign_key_properties))
                    ]
                target_entity.remove_relationship(rel.ref_name)
                target_entity.remove_property(rel.ref_name)
                fk_removed = True

        # Fallback cardinality: when no Reference objects exist (non-relational sources),
        # infer from WHERE clause direction. If source holds the FK → many sources per target → array.
        if cardinality == Cardinality.ONE_TO_ONE:
            source_fk_param = params.source_fk
            if source_fk_param and "." in source_fk_param:
                fk_entity, _ = source_fk_param.split(".", 1)
                if fk_entity == source_name:
                    # Source holds FK to target → ONE_TO_MANY (array)
                    cardinality = Cardinality.ONE_TO_MANY

        # Fallback: remove FK property from target using WHERE clause
        # (for non-relational sources that don't have Reference objects)
        if not fk_removed:
            source_fk = params.source_fk
            if source_fk and "." in source_fk:
                fk_entity, fk_attr = source_fk.split(".", 1)
                if fk_entity == target_name:
                    target_entity.remove_property(fk_attr)

        self.database.add_entity_type(embedded_entity)
        target_entity.add_relationship(Embedded(aggr_name=alias, aggregates=alias, cardinality=cardinality,
                                                is_optional=not cardinality.is_required()))
        self._touch(source_name, target_name, alias)
        self.changes.append(f"NEST:{target_name}.{alias}")
        return OperationResult.ok()

    @register_handler(OpType.FLATTEN)
    def _handle_flatten(self, params: FlattenParams) -> OperationResult:
        """
        FLATTEN: Flatten nested object fields into parent table (reduce depth by 1).

        Reference: André Conrad - "Die Operation FLATTEN erstellt aus dem Objekt in der Spalte
                   jeweils eine Spalte für jedes Attribut dieses Objekts"

        Example: FLATTEN customers.address
          Before: customers { customer_id, address: { street, city, region } }
          After:  customers { customer_id, address_street, address_city, address_region }

        The nested object's fields are flattened with a prefix (nested_fieldname).
        """
        source_path = params.source

        # Parse path: customers.address -> parent=customers, nested=address
        parent_path, nested_name = self._split_path(source_path)
        if not parent_path:
            return OperationResult.skipped("flatten: precondition not met")

        parent_entity = self._get_entity(parent_path, "FLATTEN")
        if not parent_entity:
            return OperationResult.skipped("flatten: precondition not met")

        # Try to find the embedded entity
        embedded_entity = None
        full_embedded_path = source_path

        # Check parent's relationships for the embedded
        for rel in parent_entity.get_embedded():
            if rel.aggr_name == nested_name:
                embedded_entity = self.database.get_entity_type(rel.aggregates)
                if embedded_entity:
                    full_embedded_path = rel.aggregates
                break

        # Fallback: try direct path lookup
        if not embedded_entity:
            embedded_entity = self.database.get_entity_type(full_embedded_path)

        if not embedded_entity:
            logger.info(f"FLATTEN skipped: embedded '{full_embedded_path}' not found")
            return OperationResult.skipped("flatten: precondition not met")

        # Flatten: copy all properties from embedded entity to parent with prefix
        prefix = nested_name + "_"
        for attr in embedded_entity.properties:
            new_attr_name = prefix + attr.name
            if not parent_entity.get_property(new_attr_name):
                parent_entity.add_property(Property(
                    new_attr_name, attr.data_type, False, attr.is_optional
                ))

        # Remove the embedded relationship from parent
        for rel in list(parent_entity.relationships):
            if isinstance(rel, Embedded) and rel.aggr_name == nested_name:
                parent_entity.remove_relationship(rel.aggr_name)
                break

        # Remove the nested entity (optional, as it's now integrated into parent)
        self.database.remove_entity_type(full_embedded_path)

        self._touch(parent_path, full_embedded_path)
        self.changes.append(f"FLATTEN:{source_path}")
        return OperationResult.ok()

    @register_handler(OpType.UNFLATTEN)
    def _handle_unflatten(self, params: UnflattenParams) -> OperationResult:
        """
        UNFLATTEN: Combine flat fields into nested object (reverse of FLATTEN).

        Example: UNFLATTEN customers:street, city, region AS address
          Before: customers { customer_id, street, city, region }
          After:  customers { customer_id, address: { street, city, region } }

        The specified fields are moved into a new nested object.
        """
        entity_name = params.entity
        fields = params.fields
        nested_name = params.nested_name

        entity = self._get_entity(entity_name, "UNFLATTEN")
        if not entity:
            return OperationResult.skipped("unflatten: precondition not met")

        # Create new embedded entity for the nested object
        nested_entity = EntityType(object_name=[nested_name])

        # Move specified fields from parent to nested entity
        for field_name in fields:
            attr = entity.get_property(field_name)
            if attr:
                nested_entity.add_property(Property(
                    attr.name, attr.data_type, attr.is_key, attr.is_optional
                ))
                entity.remove_property(field_name)

        # Add nested entity to database
        self.database.add_entity_type(nested_entity)

        # Add embedded relationship from parent to nested
        entity.add_relationship(Embedded(
            aggr_name=nested_name,
            aggregates=nested_name,
            cardinality=Cardinality.ONE_TO_ONE
        ))

        self._touch(entity_name, nested_name)
        self.changes.append(f"UNFLATTEN:{entity_name}({','.join(fields)})->{nested_name}")
        return OperationResult.ok()

    @register_handler(OpType.UNNEST)
    def _handle_unnest(self, params: UnnestParams) -> OperationResult:
        """
        UNNEST: Extract nested object to separate table (normalization).

        Syntax: UNNEST orders.customer:company_name,phone AS customers WITH orders.order_id TO customers.order_id

        Example:
          Before: orders { order_id, customer: { company_name, phone } }
          After:  orders { order_id }
                  customers { order_id, company_name, phone }
        """
        source_path = params.source_path
        target_name = params.target
        if not source_path or not target_name:
            return OperationResult.skipped("unnest: precondition not met")

        # New parser format uses [{'name': 'company', ...}]; legacy is just ['company'].
        nested_objects = [
            item['name'] if isinstance(item, dict) else item
            for item in params.nested
        ]

        parent_path, nested_name = self._split_path(source_path)
        if not parent_path:
            return OperationResult.skipped("unnest: precondition not met")
        parent_entity = self._get_entity(parent_path, "UNNEST")
        if not parent_entity:
            return OperationResult.skipped("unnest: precondition not met")

        embedded_entity, embedded_rel, full_embedded_path = self._resolve_unnest_source(
            parent_entity, nested_name, source_path
        )

        new_entity = self._build_unnest_target_entity(
            target_name, params.carry_fields, parent_entity,
            params.properties, embedded_entity
        )

        embedded_map = self._collect_embedded_map(embedded_entity)
        self._transfer_nested_embeddeds(
            new_entity, nested_objects, embedded_map,
            old_prefix=full_embedded_path, new_prefix=target_name
        )

        self.database.add_entity_type(new_entity)
        if embedded_rel:
            parent_entity.remove_relationship(embedded_rel.aggr_name)
        if embedded_entity:
            self.database.remove_entity_type(full_embedded_path)

        self._touch(parent_path, target_name, full_embedded_path)
        self.changes.append(f"UNNEST:{source_path}->{target_name}")
        return OperationResult.ok()

    def _resolve_unnest_source(self, parent_entity, nested_name, source_path):
        """Locate the embedded entity referenced by an UNNEST.

        Prefer a matching Embedded relationship on the parent (which gives us
        the authoritative aggregates path); fall back to a direct lookup of
        the source_path when no relationship was declared.

        Returns (embedded_entity_or_None, embedded_rel_or_None, full_path).
        """
        full_path = source_path
        for rel in parent_entity.get_embedded():
            if rel.aggr_name == nested_name:
                embedded_entity = self.database.get_entity_type(rel.aggregates)
                if embedded_entity:
                    full_path = rel.aggregates
                return embedded_entity, rel, full_path
        return self.database.get_entity_type(full_path), None, full_path

    def _build_unnest_target_entity(self, target_name, carry_fields, parent_entity,
                                    properties, embedded_entity):
        """Construct the new entity extracted by UNNEST.

        Populated in two passes: carry_fields copied from the parent (WITH
        clause, e.g. `orders.order_id TO customers.order_id`) and the
        specified properties copied from the embedded source (falling back to
        STRING when a name is not found on the source).
        """
        new_entity = EntityType(object_name=[target_name])

        for carry in carry_fields:
            source_field = carry.get("source", "")
            field_name = carry.get("field_name", "")
            source_attr_name = source_field.split(".")[-1] if source_field else source_field
            source_attr = parent_entity.get_property(source_attr_name)
            field_type = source_attr.data_type if source_attr else PrimitiveDataType(PrimitiveType.STRING)
            new_entity.add_property(Property(field_name, field_type, False, False))

        for field_name in properties:
            attr = embedded_entity.get_property(field_name) if embedded_entity else None
            if attr:
                new_entity.add_property(Property(
                    attr.name, attr.data_type, False, attr.is_optional
                ))
            else:
                new_entity.add_property(Property(
                    field_name, PrimitiveDataType(PrimitiveType.STRING), False, True
                ))

        return new_entity

    def _collect_embedded_map(self, entity):
        """Return {aggr_name: Embedded} for all Embedded relationships on `entity`."""
        if not entity:
            return {}
        return {rel.aggr_name: rel for rel in entity.relationships if isinstance(rel, Embedded)}

    def _transfer_nested_embeddeds(self, new_entity, nested_objects, embedded_map,
                                   old_prefix, new_prefix):
        """Relocate any embedded objects named in the UNNEST field list from
        under the old source path to under the new target.

        For each explicitly listed embedded (e.g. `UNNEST orders.customer:
        company_name, address` – `address` moves with it), all entities whose
        path begins with `old_prefix` are re-homed under `new_prefix`, inner
        Embedded.aggregates paths are rewritten, and a fresh Embedded
        relationship is attached to `new_entity`.
        """
        specified = set(nested_objects) & set(embedded_map.keys())
        if not specified:
            return

        for emb_name in specified:
            inner_rel = embedded_map[emb_name]
            emb_old_path = inner_rel.aggregates         # e.g., "orders.customer.address"
            emb_new_path = f"{new_prefix}.{emb_name}"   # e.g., "customer.address"

            # All entities at or below the old path need to move with the embedded.
            to_update = [emb_old_path]
            for entity_name in list(self.database.entity_types.keys()):
                if entity_name.startswith(emb_old_path + "."):
                    to_update.append(entity_name)

            for old_path in to_update:
                new_path = new_prefix + old_path[len(old_prefix):]
                nested_entity = self.database.get_entity_type(old_path)
                if not nested_entity:
                    continue
                self.database.remove_entity_type(old_path)
                nested_entity.object_name = new_path.split(".")
                self.database.add_entity_type(nested_entity)
                # Inner Embedded.aggregates that still point to old prefix must follow.
                for rel in nested_entity.relationships:
                    if isinstance(rel, Embedded) and rel.aggregates.startswith(old_prefix + "."):
                        rel.aggregates = new_prefix + rel.aggregates[len(old_prefix):]

            new_entity.add_relationship(Embedded(
                aggr_name=inner_rel.aggr_name,
                aggregates=emb_new_path,
                cardinality=inner_rel.cardinality,
                is_optional=inner_rel.is_optional,
            ))

    @register_handler(OpType.UNWIND)
    def _handle_unwind(self, params: UnwindParams) -> OperationResult:
        """
        UNWIND: Expand array field.

        Supports two modes:
        1. Create new table: UNWIND customers.tags[] INTO customer_tag
           Creates a new table for the array elements.
        2. Expand in place: UNWIND customer_tag.value
           Expands the array within an existing table (per reference definition).

        The subsequent ADD KEY and ADD CONSTRAINT operations define the structure.
        """
        mode = params.mode
        source_path = params.source

        if mode == "expand_in_place":
            # Mode 2: Expand in place - UNWIND customer_tag.tags
            # Transform array property to its element type (for schema transformation)
            # e.g., tags: ListDataType(STRING) -> tags: STRING
            entity, attr_name = self._resolve_entity_attr(source_path)
            if entity:
                attr = entity.get_property(attr_name)
                if attr and hasattr(attr.data_type, 'element_type'):
                    # Convert ListDataType to its element type
                    attr.data_type = attr.data_type.element_type
                    entity_name = self._split_path(source_path)[0]
                    self._touch(entity_name)
                    self.changes.append(f"UNWIND_INPLACE:{entity_name}.{attr_name}")
                    return OperationResult.ok()
            return OperationResult.skipped("unwind: precondition not met")

        # Mode 1: Create new table
        target_name = params.target
        if not target_name:
            return OperationResult.skipped("unwind: precondition not met")

        # Parse source path: customers.tags[] -> parent=customers, array_name=tags
        parent_path, array_name = self._split_path(source_path.replace("[]", ""))
        if not parent_path:
            return OperationResult.skipped("unwind: precondition not met")

        parent_entity = self._get_entity(parent_path, "UNWIND")
        if not parent_entity:
            return OperationResult.skipped("unwind: precondition not met")

        # Check if source is an array property
        attr = parent_entity.get_property(array_name)
        primitive_element_type = None
        if attr and hasattr(attr.data_type, 'element_type'):
            primitive_element_type = attr.data_type.element_type

        # Create new entity for array elements
        new_entity = EntityType(object_name=[target_name])

        # If it's a primitive array, add 'value' column
        if primitive_element_type:
            new_entity.add_property(Property("value", primitive_element_type, False, False))

        # Add new entity to database
        self.database.add_entity_type(new_entity)
        self.changes.append(f"UNWIND:{target_name}")

        # Remove the array property from parent
        if attr:
            parent_entity.remove_property(array_name)
        self._touch(parent_path, target_name)
        return OperationResult.ok()

    @register_handler(OpType.WIND)
    def _handle_wind(self, params: WindParams) -> OperationResult:
        """
        WIND: Convert scalar property back to array (reverse of UNWIND).

        Syntax: WIND customer_tag.tags
          Before: customer_tag { customer_id, tags } (multiple rows, scalar)
          After:  customer_tag { customer_id, tags[] } (single row, array)
          Reverse of: UNWIND customer_tag.tags

        Note: Cross-entity movement is handled by MERGE, not WIND.
        """
        source_path = params.source
        entity, attr_name = self._resolve_entity_attr(source_path)
        if entity:
            attr = entity.get_property(attr_name)
            if attr:
                # Convert scalar type to ListDataType (reverse of UNWIND which does List -> scalar)
                # Skip if already a ListDataType to avoid double-wrapping
                if not isinstance(attr.data_type, ListDataType):
                    attr.data_type = ListDataType(element_type=attr.data_type)
                entity_name = self._split_path(source_path)[0]
                self._touch(entity_name)
                self.changes.append(f"WIND:{entity_name}.{attr_name}")
                return OperationResult.ok()
        return OperationResult.skipped("wind: precondition not met")
