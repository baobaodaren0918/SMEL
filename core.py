"""
SMEL Core - Shared logic for Schema Migration & Evolution Language

This module contains the core components shared by main.py (CLI) and web_server.py (Web UI):
- SchemaTransformer: Execute transformation operations
- db_to_dict(): Convert Database to JSON-serializable dict

Note: For parsing SMEL files, use parser_factory.parse_smel_auto() which supports
both SMEL_Specific (.smel) and SMEL_Generalized (.smel_gen) grammars.
"""
import sys
import copy
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))
from Schema.unified_meta_schema import (
    Database, DatabaseType, EntityType, EntityKind, Attribute,
    UniqueConstraint, ForeignKeyConstraint, UniqueProperty, ForeignKeyProperty, PKTypeEnum,
    Reference, Embedded, Edge, Cardinality, PrimitiveDataType, PrimitiveType, ListDataType,
    TypeMappings
)
from Schema.adapters import ADAPTER_REGISTRY
from config import (
    MIGRATION_CONFIGS,
    SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT,
    SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR,
)
from smel_listeners import MigrationContext, Operation, OpType

# SMEL syntax highlighting data (single source of truth for web_server.py frontend)
# Generated from grammar token definitions — update here when grammar changes
SMEL_SYNTAX = {
    "keywords": [
        # Header keywords
        'MIGRATION', 'FROM', 'TO', 'USING', 'AS', 'INTO', 'WITH', 'WHERE', 'IN', 'KEY', 'AND', 'DELETION', 'ON',
        # Database model types
        'RELATIONAL', 'DOCUMENT', 'GRAPH', 'COLUMNAR',
        # Structure operations (shared by both grammars)
        'NEST', 'UNNEST', 'FLATTEN', 'UNFLATTEN', 'UNWIND', 'WIND',
        # CRUD verbs (Generalized grammar uses these directly)
        'ADD', 'DELETE', 'REMOVE', 'RENAME', 'COPY', 'MOVE', 'MERGE', 'SPLIT', 'CAST', 'RECARD', 'TRANSFORM',
        # Type parameters
        'ATTRIBUTE', 'ATTRIBUTES', 'CONSTRAINT', 'EMBEDDED', 'ENTITY', 'LABEL', 'RELATIONSHIP',
        # Key types
        'PRIMARY', 'UNIQUE', 'FOREIGN', 'PARTITION', 'CLUSTERING',
        'REFERENCE', 'REFERENCES', 'COLUMNS', 'STRUCTURE',
        # Cardinality
        'CARDINALITY', 'ONE_TO_ONE', 'ONE_TO_MANY', 'ZERO_TO_ONE', 'ZERO_TO_MANY',
        # Specific grammar compound keywords
        'ADD_ATTRIBUTE', 'ADD_CONSTRAINT', 'ADD_EMBEDDED', 'ADD_ENTITY', 'ADD_LABEL',
        'ADD_PRIMARY_KEY', 'ADD_FOREIGN_KEY', 'ADD_UNIQUE_KEY',
        'ADD_PARTITION_KEY', 'ADD_CLUSTERING_KEY',
        'DELETE_ATTRIBUTE', 'DELETE_CONSTRAINT', 'DELETE_EMBEDDED', 'DELETE_ENTITY', 'DELETE_LABEL',
        'DELETE_PRIMARY_KEY', 'DELETE_UNIQUE_KEY', 'DELETE_FOREIGN_KEY',
        'DELETE_PARTITION_KEY', 'DELETE_CLUSTERING_KEY',
        'RENAME_ATTRIBUTE', 'RENAME_ENTITY',
        'COPY_ATTRIBUTE', 'COPY_ENTITY', 'MOVE_ATTRIBUTE',
        'CAST_ATTRIBUTE', 'CAST_CONSTRAINT',
        'NODE', 'DOCUMENT_ID',
    ],
    "types": [
        'String', 'Text', 'Int', 'Integer', 'Long', 'Double', 'Float',
        'Decimal', 'Boolean', 'Date', 'DateTime', 'Timestamp', 'UUID', 'Binary',
    ],
}

# Module-level constant: maps SOURCE_TYPE string -> DatabaseType enum
_DB_TYPE_MAP = {
    SOURCE_TYPE_RELATIONAL: DatabaseType.RELATIONAL,
    SOURCE_TYPE_DOCUMENT: DatabaseType.DOCUMENT,
    SOURCE_TYPE_GRAPH: DatabaseType.GRAPH,
    SOURCE_TYPE_COLUMNAR: DatabaseType.COLUMNAR,
}

# Default EntityKind for each database type (for normalizing newly created entities)
_ENTITY_KIND_DEFAULT = {
    SOURCE_TYPE_RELATIONAL: EntityKind.TABLE,
    SOURCE_TYPE_DOCUMENT:   EntityKind.DOCUMENT,
    SOURCE_TYPE_GRAPH:      EntityKind.VERTEX,
    SOURCE_TYPE_COLUMNAR:   EntityKind.WIDE_COLUMN_TABLE,
}


class SchemaTransformer:
    """Transform schema based on SMEL operations."""

    CARDINALITY_MAP = {
        "ONE_TO_ONE": Cardinality.ONE_TO_ONE,
        "ONE_TO_MANY": Cardinality.ONE_TO_MANY,
        "ZERO_TO_ONE": Cardinality.ZERO_TO_ONE,
        "ZERO_TO_MANY": Cardinality.ZERO_TO_MANY,
    }

    # Key type mapping for SMEL operations
    KEY_TYPE_MAP = {
        "PRIMARY": "primary",
        "UNIQUE": "unique",
        "FOREIGN": "foreign",
        "PARTITION": PKTypeEnum.PARTITION,
        "CLUSTERING": PKTypeEnum.CLUSTERING,
    }

    # Data type string -> PrimitiveType mapping (used by ADD_ATTRIBUTE, ADD_KEY, CAST)
    TYPE_STR_MAP = {
        "STRING": PrimitiveType.STRING, "TEXT": PrimitiveType.TEXT,
        "INT": PrimitiveType.INTEGER, "INTEGER": PrimitiveType.INTEGER,
        "LONG": PrimitiveType.LONG, "DOUBLE": PrimitiveType.DOUBLE,
        "FLOAT": PrimitiveType.FLOAT, "DECIMAL": PrimitiveType.DECIMAL,
        "BOOLEAN": PrimitiveType.BOOLEAN, "DATE": PrimitiveType.DATE,
        "TIMESTAMP": PrimitiveType.TIMESTAMP,
        "UUID": PrimitiveType.UUID, "BINARY": PrimitiveType.BINARY,
        "DATETIME": PrimitiveType.TIMESTAMP
    }

    def __init__(self, database: Database):
        self.database = copy.deepcopy(database)
        self.changes: List[str] = []
        self.key_registry: Dict[str, Dict[str, Any]] = {}
        self._last_created_entity: Optional[str] = None  # Track last created entity for ADD_KEY/ADD_CONSTRAINT
        self._explicitly_cast_entities: set = set()  # Entities explicitly cast via CAST_ENTITY (skip in normalization)
        self._init_source_keys()
        # Handler registry: OpType -> method (used by run_migration dispatch loop)
        self._handlers = {
            OpType.NEST: self._handle_nest,
            OpType.UNNEST: self._handle_unnest,
            OpType.FLATTEN: self._handle_flatten,
            OpType.UNFLATTEN: self._handle_unflatten,
            OpType.WIND: self._handle_wind,
            OpType.UNWIND: self._handle_unwind,
            OpType.ADD_ENTITY: self._handle_add_entity,
            OpType.DELETE_ENTITY: self._handle_delete_entity,
            OpType.RENAME_ENTITY: self._handle_rename_entity,
            OpType.COPY_ENTITY: self._handle_copy_entity,
            OpType.ADD_ATTRIBUTE: self._handle_add_attribute,
            OpType.DELETE_ATTRIBUTE: self._handle_delete_attribute,
            OpType.RENAME: self._handle_rename,
            OpType.COPY: self._handle_copy,
            OpType.MOVE: self._handle_move,
            OpType.ADD_KEY: self._handle_add_key,
            OpType.DELETE_KEY: self._handle_delete_key,
            OpType.ADD_CONSTRAINT: self._handle_add_constraint,
            OpType.DELETE_CONSTRAINT: self._handle_delete_constraint,
            OpType.CAST_CONSTRAINT: self._handle_cast_constraint,
            OpType.CAST_ENTITY: self._handle_cast_entity,
            OpType.ADD_EMBEDDED: self._handle_add_embedded,
            OpType.DELETE_EMBEDDED: self._handle_delete_embedded,
            OpType.ADD_LABEL: self._handle_add_label,
            OpType.DELETE_LABEL: self._handle_delete_label,
            OpType.TRANSFORM: self._handle_transform,
            OpType.MERGE: self._handle_merge,
            OpType.SPLIT: self._handle_split,
            OpType.CAST: self._handle_cast,
            OpType.RECARD: self._handle_recard,
        }

    def _init_source_keys(self) -> None:
        """Initialize key_registry with existing entities' primary keys."""
        for entity_name, entity in self.database.entity_types.items():
            pk = entity.get_primary_key()
            if pk and pk.unique_properties:
                pk_attr = entity.get_attribute_by_id(pk.unique_properties[0].property_id)
                if pk_attr:
                    self.key_registry[entity_name] = {
                        "key_field": pk_attr.attr_name,
                        "key_type": pk_attr.data_type.primitive_type.value if hasattr(pk_attr.data_type, 'primitive_type') else "string",
                        "prefix": None,
                        "generated": False
                    }

    # ── Helper utilities (shared by multiple handlers) ──────────────────

    def _get_entity(self, name: str, op_name: str = "") -> Optional[EntityType]:
        """Look up an entity by name; print [NOTICE] and return None if missing."""
        entity = self.database.get_entity_type(name)
        if not entity and op_name:
            print(f"[NOTICE] {op_name} skipped: entity '{name}' not found")
        return entity

    def _split_path(self, path: str) -> tuple:
        """Split 'entity.attr' path into (entity_name, attr_or_field_name).

        Returns ("", "") if path has fewer than 2 parts.
        """
        parts = path.split(".")
        if len(parts) < 2:
            return ("", "")
        return ".".join(parts[:-1]), parts[-1]

    def _resolve_entity_attr(self, path: str, op_name: str = "") -> tuple:
        """Parse 'entity.attr' path, look up the entity, and return (entity, attr_name).

        Returns (None, "") on failure (with optional [NOTICE] print).
        """
        entity_name, attr_name = self._split_path(path)
        if not entity_name:
            return (None, "")
        entity = self._get_entity(entity_name, op_name)
        return (entity, attr_name)

    def _handle_nest(self, params: Dict) -> bool:
        """
        NEST: Embed separate table into parent as nested object (denormalization).

        Syntax: NEST address:street,city IN person.address WHERE address.person_id = person.person_id [WITH DELETION]

        Example: NEST_PS address:street,city IN person.address WHERE address.person_id = person.person_id
          Before: person { person_id }
                  address { person_id, street, city }
          After:  person { person_id, address: { street, city } }

        Parameters:
        - source: address (source entity to embed)
        - target: person (target entity)
        - alias: address (embedded field name)
        - attributes: [street, city] (attributes to embed)
        - source_fk: address.person_id (source FK for matching)
        - target_pk: person.person_id (target PK for matching)
        - with_deletion: True/False (delete source after embedding)
        """
        source_name = params.get("source")
        target_name = params.get("target")
        alias = params.get("alias")
        attributes = params.get("attributes", [])
        with_deletion = params.get("with_deletion", False)

        source_entity = self._get_entity(source_name, "NEST")
        target_entity = self._get_entity(target_name, "NEST")
        if not source_entity or not target_entity:
            return False

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

        # Create embedded entity with specified attributes (or all non-FK attributes if not specified)
        fk_attr_names = {rel.ref_name for rel in source_entity.get_references()}
        embedded_entity = EntityType(object_name=[alias])

        nested = params.get("nested", [])

        if attributes:
            # Use specified attributes
            for attr_name in attributes:
                attr = source_entity.get_attribute(attr_name)
                if attr:
                    embedded_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, False, attr.is_optional))
        else:
            # Use all non-FK attributes (backward compatibility)
            for attr in source_entity.attributes:
                if attr.attr_name not in fk_attr_names:
                    embedded_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, False, attr.is_optional))

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
                fk_attr = target_entity.get_attribute(rel.ref_name)
                if fk_attr:
                    target_entity.constraints = [
                        c for c in target_entity.constraints
                        if not (isinstance(c, ForeignKeyConstraint) and
                                any(fkp.property_id == fk_attr.meta_id for fkp in c.foreign_key_properties))
                    ]
                target_entity.remove_relationship(rel.ref_name)
                target_entity.remove_attribute(rel.ref_name)
                fk_removed = True

        # Fallback cardinality: when no Reference objects exist (non-relational sources),
        # infer from WHERE clause direction. If source holds the FK → many sources per target → array.
        if cardinality == Cardinality.ONE_TO_ONE:
            source_fk_param = params.get("source_fk", "")
            if source_fk_param and "." in source_fk_param:
                fk_entity, _ = source_fk_param.split(".", 1)
                if fk_entity == source_name:
                    # Source holds FK to target → ONE_TO_MANY (array)
                    cardinality = Cardinality.ONE_TO_MANY

        # Fallback: remove FK attribute from target using WHERE clause
        # (for non-relational sources that don't have Reference objects)
        if not fk_removed:
            source_fk = params.get("source_fk", "")
            if source_fk and "." in source_fk:
                fk_entity, fk_attr = source_fk.split(".", 1)
                if fk_entity == target_name:
                    target_entity.remove_attribute(fk_attr)

        # Delete source entity BEFORE adding the new embedded entity
        # (otherwise when source_name == alias, remove would delete the newly created entity)
        if with_deletion:
            self.database.remove_entity_type(source_name)
            self.changes.append(f"DELETE_ENTITY:{source_name}")

        self.database.add_entity_type(embedded_entity)
        target_entity.add_relationship(Embedded(aggr_name=alias, aggregates=alias, cardinality=cardinality,
                                                is_optional=not cardinality.is_required()))
        self.changes.append(f"NEST:{target_name}.{alias}")
        return True

    def _handle_flatten(self, params: Dict) -> bool:
        """
        FLATTEN: Flatten nested object fields into parent table (reduce depth by 1).

        Reference: André Conrad - "Die Operation FLATTEN erstellt aus dem Objekt in der Spalte
                   jeweils eine Spalte für jedes Attribut dieses Objekts"

        Example: FLATTEN_PS person.name
          Before: person { name: { vorname, nachname }, age }
          After:  person { name_vorname, name_nachname, age }

        The nested object's fields are flattened with a prefix (nested_fieldname).
        """
        source_path = params["source"]

        # Parse path: person.name -> parent=person, nested=name
        parent_path, nested_name = self._split_path(source_path)
        if not parent_path:
            return False

        parent_entity = self._get_entity(parent_path, "FLATTEN")
        if not parent_entity:
            return False

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
            print(f"[NOTICE] FLATTEN skipped: embedded '{full_embedded_path}' not found")
            return False

        # Flatten: copy all attributes from embedded entity to parent with prefix
        prefix = nested_name + "_"
        for attr in embedded_entity.attributes:
            new_attr_name = prefix + attr.attr_name
            if not parent_entity.get_attribute(new_attr_name):
                parent_entity.add_attribute(Attribute(
                    new_attr_name, attr.data_type, False, attr.is_optional
                ))

        # Remove the embedded relationship from parent
        for rel in list(parent_entity.relationships):
            if isinstance(rel, Embedded) and rel.aggr_name == nested_name:
                parent_entity.remove_relationship(rel.aggr_name)
                break

        # Remove the nested entity (optional, as it's now integrated into parent)
        self.database.remove_entity_type(full_embedded_path)

        self.changes.append(f"FLATTEN:{source_path}")
        return True

    def _handle_unflatten(self, params: Dict) -> bool:
        """
        UNFLATTEN: Combine flat fields into nested object (reverse of FLATTEN).

        Example: UNFLATTEN person:vorname, nachname AS name
          Before: person { vorname, nachname, age }
          After:  person { name: { vorname, nachname }, age }

        The specified fields are moved into a new nested object.
        """
        entity_name = params["entity"]
        fields = params["fields"]
        nested_name = params["nested_name"]

        entity = self._get_entity(entity_name, "UNFLATTEN")
        if not entity:
            return False

        # Create new embedded entity for the nested object
        nested_entity = EntityType(object_name=[nested_name])

        # Move specified fields from parent to nested entity
        for field_name in fields:
            attr = entity.get_attribute(field_name)
            if attr:
                nested_entity.add_attribute(Attribute(
                    attr.attr_name, attr.data_type, attr.is_key, attr.is_optional
                ))
                entity.remove_attribute(field_name)

        # Add nested entity to database
        self.database.add_entity_type(nested_entity)

        # Add embedded relationship from parent to nested
        entity.add_relationship(Embedded(
            aggr_name=nested_name,
            aggregates=nested_name,
            cardinality=Cardinality.ONE_TO_ONE
        ))

        self.changes.append(f"UNFLATTEN:{entity_name}({','.join(fields)})->{nested_name}")
        return True

    def _handle_unnest(self, params: Dict) -> bool:
        """
        UNNEST: Extract nested object to separate table (normalization).

        Syntax: UNNEST person.address:street,city AS address WITH person.person_id TO address.person_id

        Multiple carry fields:
          UNNEST person.employment:position AS employment
              WITH person.person_id TO employment.person_id, person.dept_id TO employment.dept_id

        Example: UNNEST_PS person.address:street,city AS address WITH person.person_id TO address.person_id
          Before: person { person_id, address: { street, city } }
          After:  person { person_id }
                  address { person_id, street, city }

        Parameters:
        - source_path: person.address (the nested path to extract)
        - attributes: [street, city] (attributes to include)
        - nested: [] (nested objects to transfer, from {braces})
        - target: address (the new table name)
        - carry_fields: [{'source': 'person.person_id', 'target': 'address.person_id', 'field_name': 'person_id'}]
                        List of fields to copy from source to new table
        """
        source_path = params.get("source_path")
        attributes = params.get("attributes", [])  # Regular attributes
        nested_raw = params.get("nested", [])  # Nested objects from parser
        target_name = params.get("target")
        carry_fields = params.get("carry_fields", [])  # Fields to copy from source

        # Extract nested object names from the new recursive format
        # New format: [{'name': 'company', 'attributes': [...], 'nested': [...]}]
        # Old format: ['company', 'address'] (for backward compatibility)
        nested_objects = []
        for item in nested_raw:
            if isinstance(item, dict):
                nested_objects.append(item['name'])
            else:
                nested_objects.append(item)

        if not source_path or not target_name:
            return False

        # Parse source path: person.address -> parent=person, nested=address
        parent_path, nested_name = self._split_path(source_path)
        if not parent_path:
            return False

        # Get parent entity
        parent_entity = self._get_entity(parent_path, "UNNEST")
        if not parent_entity:
            return False

        # Try to find the embedded entity
        embedded_entity = None
        full_embedded_path = source_path
        embedded_rel = None

        # Check parent's relationships for the embedded
        for rel in parent_entity.get_embedded():
            if rel.aggr_name == nested_name:
                embedded_entity = self.database.get_entity_type(rel.aggregates)
                embedded_rel = rel
                if embedded_entity:
                    full_embedded_path = rel.aggregates
                break

        # Fallback: try direct path lookup
        if not embedded_entity:
            embedded_entity = self.database.get_entity_type(full_embedded_path)

        # Create new entity
        new_entity = EntityType(object_name=[target_name])

        # Add carry fields (fields copied from parent table to new table)
        # These are the fields specified in WITH clause, e.g.:
        #   WITH person.person_id AS address.person_id, person.dept_id AS address.dept_id
        for carry in carry_fields:
            source_field = carry.get("source", "")  # e.g., person.person_id
            field_name = carry.get("field_name", "")  # e.g., person_id

            # Parse source field to get the attribute name
            source_parts = source_field.split(".")
            source_attr_name = source_parts[-1] if source_parts else source_field

            # Get the source attribute's type from parent entity
            source_attr = parent_entity.get_attribute(source_attr_name)
            field_type = source_attr.data_type if source_attr else PrimitiveDataType(PrimitiveType.STRING)

            # Add the field to the new entity
            carry_attr = Attribute(field_name, field_type, False, False)
            new_entity.add_attribute(carry_attr)

        # Collect embedded relationship names from the source entity
        embedded_map = {}  # name -> Embedded relationship
        if embedded_entity:
            for rel in embedded_entity.relationships:
                if isinstance(rel, Embedded):
                    embedded_map[rel.aggr_name] = rel

        # EXPLICIT DESIGN: attributes and nested are already separated by the parser
        # - attributes: regular fields like 'position', 'name'
        # - nested_objects: nested objects like 'company', 'address' (from {braces})
        specified_embedded = set(nested_objects) & set(embedded_map.keys())

        # Add specified attributes from embedded entity
        for field_name in attributes:
            if embedded_entity:
                attr = embedded_entity.get_attribute(field_name)
                if attr:
                    new_entity.add_attribute(Attribute(
                        attr.attr_name, attr.data_type, False, attr.is_optional
                    ))
                else:
                    # Field not found, add as string
                    new_entity.add_attribute(Attribute(
                        field_name, PrimitiveDataType(PrimitiveType.STRING), False, True
                    ))
            else:
                new_entity.add_attribute(Attribute(
                    field_name, PrimitiveDataType(PrimitiveType.STRING), False, True
                ))

        # EXPLICIT DESIGN: Only transfer embedded objects that are specified in the field list
        # e.g., UNNEST person.employment:position,company -> only transfer 'company' if listed
        if embedded_entity and specified_embedded:
            old_prefix = full_embedded_path  # e.g., "person.employment"
            new_prefix = target_name          # e.g., "employment"

            # For each specified embedded object, transfer it and all its nested entities
            for emb_name in specified_embedded:
                inner_rel = embedded_map.get(emb_name)
                if not inner_rel:
                    continue

                # Collect all entities under this embedded object path
                emb_old_path = inner_rel.aggregates  # e.g., "person.employment.company"
                emb_new_path = f"{new_prefix}.{emb_name}"  # e.g., "employment.company"

                # Update paths for this embedded and all its nested entities
                entities_to_update = [emb_old_path]
                for entity_name in list(self.database.entity_types.keys()):
                    if entity_name.startswith(emb_old_path + "."):
                        entities_to_update.append(entity_name)

                for old_entity_path in entities_to_update:
                    # person.employment.company -> employment.company
                    # person.employment.company.address -> employment.company.address
                    new_entity_path = new_prefix + old_entity_path[len(old_prefix):]

                    nested_entity = self.database.get_entity_type(old_entity_path)
                    if nested_entity:
                        self.database.remove_entity_type(old_entity_path)
                        nested_entity.object_name = new_entity_path.split(".")
                        self.database.add_entity_type(nested_entity)

                        # Update embedded relationships within this entity
                        for rel in nested_entity.relationships:
                            if isinstance(rel, Embedded):
                                if rel.aggregates.startswith(old_prefix + "."):
                                    rel.aggregates = new_prefix + rel.aggregates[len(old_prefix):]

                # Add the embedded relationship to the new entity
                new_rel = Embedded(
                    aggr_name=inner_rel.aggr_name,
                    aggregates=emb_new_path,
                    cardinality=inner_rel.cardinality,
                    is_optional=inner_rel.is_optional
                )
                new_entity.add_relationship(new_rel)

        # Add new entity to database
        self.database.add_entity_type(new_entity)
        self._last_created_entity = target_name

        # Remove the embedded relationship from parent
        if embedded_rel:
            parent_entity.remove_relationship(embedded_rel.aggr_name)

        # Remove the original embedded entity (but inner entities are already transferred)
        if embedded_entity:
            self.database.remove_entity_type(full_embedded_path)

        self.changes.append(f"UNNEST:{source_path}->{target_name}")
        return True

    def _handle_unwind(self, params: Dict) -> bool:
        """
        UNWIND: Expand array field.

        Supports two modes:
        1. Create new table: UNWIND_PS person.tags[] INTO person_tag
           Creates a new table for the array elements.
        2. Expand in place: UNWIND_PS person_tag.value
           Expands the array within an existing table (per reference definition).

        The subsequent ADD_PS KEY and ADD_PS CONSTRAINT operations define the structure.
        """
        mode = params.get("mode", "create_table")
        source_path = params.get("source", "")

        if mode == "expand_in_place":
            # Mode 2: Expand in place - UNWIND person_tag.tags
            # Transform array attribute to its element type (for schema transformation)
            # e.g., tags: ListDataType(STRING) -> tags: STRING
            entity, attr_name = self._resolve_entity_attr(source_path)
            if entity:
                attr = entity.get_attribute(attr_name)
                if attr and hasattr(attr.data_type, 'element_type'):
                    # Convert ListDataType to its element type
                    attr.data_type = attr.data_type.element_type
                    entity_name = self._split_path(source_path)[0]
                    self.changes.append(f"UNWIND_INPLACE:{entity_name}.{attr_name}")
                    return True
            return False

        # Mode 1: Create new table
        target_name = params.get("target")
        if not target_name:
            return False

        # Parse source path: person.tags[] -> parent=person, array_name=tags
        parent_path, array_name = self._split_path(source_path.replace("[]", ""))
        if not parent_path:
            return False

        parent_entity = self._get_entity(parent_path, "UNWIND")
        if not parent_entity:
            return False

        # Check if source is an array attribute
        attr = parent_entity.get_attribute(array_name)
        primitive_element_type = None
        if attr and hasattr(attr.data_type, 'element_type'):
            primitive_element_type = attr.data_type.element_type

        # Create new entity for array elements
        new_entity = EntityType(object_name=[target_name])

        # If it's a primitive array, add 'value' column
        if primitive_element_type:
            new_entity.add_attribute(Attribute("value", primitive_element_type, False, False))

        # Add new entity to database
        self.database.add_entity_type(new_entity)
        self._last_created_entity = target_name  # Track for subsequent ADD_KEY/ADD_CONSTRAINT
        self.changes.append(f"UNWIND:{target_name}")

        # Remove the array attribute from parent
        if attr:
            parent_entity.remove_attribute(array_name)
        return True

    def _handle_wind(self, params: Dict) -> bool:
        """
        WIND: Convert scalar attribute back to array (reverse of UNWIND).

        Syntax: WIND person_tag.tags
          Before: person_tag { person_id, tags } (multiple rows, scalar)
          After:  person_tag { person_id, tags[] } (single row, array)
          Reverse of: UNWIND person_tag.tags

        Note: Cross-entity movement is handled by MERGE, not WIND.
        """
        source_path = params.get("source", "")
        entity, attr_name = self._resolve_entity_attr(source_path)
        if entity:
            attr = entity.get_attribute(attr_name)
            if attr:
                # Convert scalar type to ListDataType (reverse of UNWIND which does List -> scalar)
                # Skip if already a ListDataType to avoid double-wrapping
                if not isinstance(attr.data_type, ListDataType):
                    attr.data_type = ListDataType(element_type=attr.data_type)
                entity_name = self._split_path(source_path)[0]
                self.changes.append(f"WIND:{entity_name}.{attr_name}")
                return True
        return False

    def _handle_delete_constraint(self, params: Dict) -> bool:
        entity_name, ref_name = self._split_path(params["reference"])
        entity = self._get_entity(entity_name) if entity_name else None
        if entity:
            # Remove the Reference relationship
            entity.remove_relationship(ref_name)
            # Also remove the matching ForeignKeyConstraint from entity.constraints
            # (matches SQL semantics: DROP CONSTRAINT removes FK but keeps the column)
            fk_attr = entity.get_attribute(ref_name)
            if fk_attr:
                entity.constraints = [
                    c for c in entity.constraints
                    if not (isinstance(c, ForeignKeyConstraint) and
                            any(fkp.property_id == fk_attr.meta_id for fkp in c.foreign_key_properties))
                ]
            self.changes.append(f"DELETE_CONSTRAINT:{entity_name}.{ref_name}")
            return True
        return False

    def _handle_delete_embedded(self, params: Dict) -> bool:
        parent_name, embedded_name = self._split_path(params["embedded"])
        embedded_name = embedded_name.replace("[]", "")
        parent_entity = self._get_entity(parent_name, "DELETE_EMBEDDED") if parent_name else None
        if not parent_entity:
            return False
        # Find the full entity path from the Embedded relationship
        full_path = f"{parent_name}.{embedded_name}"
        for rel in parent_entity.get_embedded():
            if rel.aggr_name == embedded_name:
                full_path = rel.aggregates
                break
        parent_entity.remove_relationship(embedded_name)
        self.database.remove_entity_type(full_path)
        self.changes.append(f"DELETE_EMBEDDED:{parent_name}.{embedded_name}")
        return True

    def _handle_add_constraint(self, params: Dict) -> bool:
        """ADD_CONSTRAINT entity.field REFERENCES target_table(target_column) WITH CARDINALITY"""
        field_name = params.get("field_name")
        target_table = params.get("target_table")
        target_column = params.get("target_column")
        entity_name = params.get("entity")

        if not entity_name:
            # Use last created entity if no entity specified
            entity_name = self._last_created_entity

        if not entity_name or not field_name or not target_table:
            return False

        entity = self._get_entity(entity_name, "ADD_CONSTRAINT")
        if not entity:
            return False

        # Get target entity's primary key type for FK attribute
        target_entity = self._get_entity(target_table)
        fk_type = PrimitiveDataType(PrimitiveType.INTEGER)
        if target_entity:
            target_pk = target_entity.get_primary_key()
            if target_pk and target_pk.unique_properties:
                pk_attr = target_entity.get_attribute_by_id(target_pk.unique_properties[0].property_id)
                if pk_attr:
                    fk_type = pk_attr.data_type

        if not entity.get_attribute(field_name):
            entity.add_attribute(Attribute(field_name, fk_type, False, True))

        # Parse cardinality from clauses (dict format from _parse_reference_clauses)
        cardinality = Cardinality.ONE_TO_ONE
        clauses = params.get("clauses", {})
        if 'cardinality' in clauses:
            cardinality = self.CARDINALITY_MAP.get(clauses['cardinality'], Cardinality.ONE_TO_ONE)

        # Avoid duplicate Reference (if already exists, update it)
        existing_ref = next(
            (r for r in entity.relationships if isinstance(r, Reference) and r.ref_name == field_name),
            None
        )
        if existing_ref:
            existing_ref.refs_to = target_table
            existing_ref.cardinality = cardinality
        else:
            entity.add_relationship(Reference(ref_name=field_name, refs_to=target_table,
                                              cardinality=cardinality, is_optional=not cardinality.is_required()))

        # Sync FK attribute's is_optional with cardinality requirement
        fk_attr = entity.get_attribute(field_name)
        if fk_attr and cardinality.is_required():
            fk_attr.is_optional = False

        # Also create ForeignKeyConstraint for consistency with ADD_KEY FOREIGN
        if fk_attr:
            target_up_id = self._get_target_unique_property_id(target_table, target_column)
            # Avoid duplicate FK constraint
            has_fk = any(
                isinstance(c, ForeignKeyConstraint) and
                any(fkp.property_id == fk_attr.meta_id for fkp in c.foreign_key_properties)
                for c in entity.constraints
            )
            if not has_fk:
                fk_prop = ForeignKeyProperty(property_id=fk_attr.meta_id, points_to_unique_property_id=target_up_id)
                entity.add_constraint(ForeignKeyConstraint(is_managed=True, foreign_key_properties=[fk_prop]))

        self.changes.append(f"ADD_REF:{entity_name}.{field_name}")
        return True

    def _handle_add_attribute(self, params: Dict) -> bool:
        """ADD ATTRIBUTE email TO Customer WITH TYPE String NOT NULL"""
        name = params["name"]
        entity_name = params.get("entity")
        clauses = params.get("clauses", [])

        # Parse data type and options from clauses
        data_type = PrimitiveDataType(PrimitiveType.STRING)
        is_optional = True

        for c in clauses:
            if c["type"] == "TYPE":
                type_str = c["data_type"].upper()
                data_type = PrimitiveDataType(self.TYPE_STR_MAP.get(type_str, PrimitiveType.STRING))
            elif c["type"] == "NOT_NULL":
                is_optional = False

        entity = self._get_entity(entity_name, "ADD_ATTRIBUTE") if entity_name else None
        if not entity:
            return False
        entity.add_attribute(Attribute(name, data_type, False, is_optional))
        self.changes.append(f"ADD_ATTR:{entity_name}.{name}")
        return True

    def _handle_add_embedded(self, params: Dict) -> bool:
        """ADD EMBEDDED address TO Customer WITH CARDINALITY ONE_TO_ONE"""
        name = params["name"]
        entity_name = params["entity"]
        clauses = params.get("clauses", [])

        cardinality = Cardinality.ONE_TO_ONE
        for c in clauses:
            if c["type"] == "CARDINALITY":
                cardinality = self.CARDINALITY_MAP.get(c["value"], Cardinality.ONE_TO_ONE)

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if entity:
            is_optional = not cardinality.is_required()
            entity.add_relationship(Embedded(aggr_name=name, aggregates=name, cardinality=cardinality, is_optional=is_optional))
            # Create the child entity so ADD_ATTRIBUTE can target it
            if not self.database.get_entity_type(name):
                self.database.add_entity_type(EntityType(object_name=[name]))
            self.changes.append(f"ADD_EMBEDDED:{entity_name}.{name}")
            return True
        return False

    def _handle_add_entity(self, params: Dict) -> bool:
        """ADD_ENTITY Product WITH ATTRIBUTES (id String, name String)
        Also handles EDGE entities: ADD_ENTITY name FROM src TO tgt WITH ATTRIBUTES (...)
        """
        name = params["name"]
        clauses = params.get("clauses", [])
        source_entity = params.get("source_entity")
        target_entity = params.get("target_entity")

        new_entity = EntityType(object_name=[name])

        # Process clauses for attributes and key (shared by regular and EDGE entities)
        key_name = None
        for c in clauses:
            if c["type"] == "ATTRIBUTES":
                for attr_def in c["attributes"]:
                    attr_name = attr_def["name"]
                    data_type_str = attr_def.get("data_type", "String").upper()
                    prim_type = self.TYPE_STR_MAP.get(data_type_str, PrimitiveType.STRING)
                    new_entity.add_attribute(Attribute(attr_name, PrimitiveDataType(prim_type), False, True))
            elif c["type"] == "KEY":
                key_name = c["key_name"]

        # EDGE entity (relationship type): set kind and source/target
        if source_entity and target_entity:
            new_entity.entity_kind = EntityKind.EDGE
            new_entity.source_entity = source_entity
            new_entity.target_entity = target_entity

            # Resolve cardinality (default: ZERO_TO_MANY)
            cardinality = Cardinality.ZERO_TO_MANY
            if "cardinality" in params:
                cardinality = self.CARDINALITY_MAP.get(params["cardinality"], Cardinality.ZERO_TO_MANY)
            new_entity.edge_cardinality = cardinality

            # Validate source and target exist
            source_ent = self.database.get_entity_type(source_entity)
            if not source_ent:
                print(f"[NOTICE] ADD_ENTITY (EDGE) skipped: source entity '{source_entity}' not found")
                return False
            target_ent = self.database.get_entity_type(target_entity)
            if not target_ent:
                print(f"[NOTICE] ADD_ENTITY (EDGE) skipped: target entity '{target_entity}' not found")
                return False

            # Add Edge to source entity's relationships
            edge = Edge(
                rel_type_name=name,
                source_entity=source_entity,
                target_entity=target_entity,
                cardinality=cardinality
            )
            source_ent.add_relationship(edge)

            self.database.add_entity_type(new_entity)
            self.changes.append(f"ADD_ENTITY:{name}({source_entity}->{target_entity})")
            return True

        # Regular entity: set primary key if specified
        if key_name:
            attr = new_entity.get_attribute(key_name)
            if attr:
                attr.is_key = True
                attr.is_optional = False
                constraint = UniqueConstraint(
                    is_primary_key=True,
                    is_managed=True,
                    unique_properties=[UniqueProperty(primary_key_type=PKTypeEnum.SIMPLE, property_id=attr.meta_id)]
                )
                new_entity.add_constraint(constraint)

        self.database.add_entity_type(new_entity)
        self.changes.append(f"ADD_ENTITY:{name}")
        return True

    def _handle_delete_attribute(self, params: Dict) -> bool:
        """DELETE ATTRIBUTE Customer.email"""
        target = params["target"]
        entity, attr_name = self._resolve_entity_attr(target)
        if not entity:
            return False

        # Get meta_id before removal for constraint cleanup
        attr = entity.get_attribute(attr_name)
        attr_meta_id = attr.meta_id if attr else None

        entity.remove_attribute(attr_name)

        # Clean up constraints referencing the deleted attribute
        if attr_meta_id:
            entity.constraints = [
                c for c in entity.constraints
                if not (isinstance(c, UniqueConstraint) and
                        any(up.property_id == attr_meta_id for up in c.unique_properties))
                and not (isinstance(c, ForeignKeyConstraint) and
                         any(fkp.property_id == attr_meta_id for fkp in c.foreign_key_properties))
            ]
        # Clean up Reference relationships matching the deleted attribute
        for rel in list(entity.relationships):
            if isinstance(rel, Reference) and rel.ref_name == attr_name:
                entity.remove_relationship(attr_name)
                break

        self.changes.append(f"DELETE_ATTR:{target}")
        return True

    def _handle_delete_entity(self, params: Dict) -> bool:
        """DELETE ENTITY Customer (also handles EDGE entities)"""
        name = params["name"]
        deleted_entity = self._get_entity(name, "DELETE_ENTITY")
        if not deleted_entity:
            return False

        # If deleting an EDGE entity, clean up Edge from source entity
        if deleted_entity.entity_kind == EntityKind.EDGE and deleted_entity.source_entity:
            source_ent = self.database.get_entity_type(deleted_entity.source_entity)
            if source_ent:
                source_ent.remove_relationship(name)

        # Collect deleted entity's attribute meta_ids for FK cleanup
        deleted_attr_ids = set()
        for attr in deleted_entity.attributes:
            deleted_attr_ids.add(attr.meta_id)
        deleted_up_ids = set()
        for c in deleted_entity.constraints:
            if isinstance(c, UniqueConstraint):
                for up in c.unique_properties:
                    deleted_up_ids.add(up.meta_id)

        self.database.remove_entity_type(name)
        # Clean up cross-references in other entities (Reference, Embedded, and Edge)
        for other_entity in self.database.entity_types.values():
            other_entity.relationships = [
                rel for rel in other_entity.relationships
                if not (hasattr(rel, 'refs_to') and rel.refs_to == name)
                and not (hasattr(rel, 'aggregates') and rel.aggregates == name)
                and not (isinstance(rel, Edge) and (rel.source_entity == name or rel.target_entity == name))
            ]
            # Clean up ForeignKeyConstraints pointing to the deleted entity
            if deleted_up_ids:
                other_entity.constraints = [
                    c for c in other_entity.constraints
                    if not (isinstance(c, ForeignKeyConstraint) and
                            any(fkp.points_to_unique_property_id in deleted_up_ids
                                for fkp in c.foreign_key_properties))
                ]
        # Clean up EDGE entities that reference the deleted entity
        edges_to_remove = [
            e_name for e_name, e in self.database.entity_types.items()
            if e.entity_kind == EntityKind.EDGE and (e.source_entity == name or e.target_entity == name)
        ]
        for e_name in edges_to_remove:
            self.database.remove_entity_type(e_name)
        self.changes.append(f"DELETE_ENTITY:{name}")
        return True

    def _handle_delete_key(self, params: Dict) -> bool:
        """DELETE PRIMARY/FOREIGN/UNIQUE KEY - destructive removal"""
        return self._remove_key_constraint(params, operation="DELETE")

    def _handle_delete_label(self, params: Dict) -> bool:
        """DELETE LABEL Employee FROM Person (graph database)"""
        label = params.get("label")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return False

        if label in entity.labels:
            entity.labels.remove(label)
        self.changes.append(f"DELETE_LABEL:{entity_name}.{label}")
        return True

    def _handle_add_label(self, params: Dict) -> bool:
        """ADD LABEL Employee TO Person (graph database)"""
        label = params.get("label")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity or not label:
            return False

        if label not in entity.labels:
            entity.labels.append(label)
        self.changes.append(f"ADD_LABEL:{entity_name}.{label}")
        return True

    def _handle_add_key(self, params: Dict) -> bool:
        """ADD_PS KEY id AS String OR ADD_PS PRIMARY KEY (id1, id2) TO Customer"""
        entity_name = params.get("entity")
        key_columns = params.get("key_columns", [])  # List of column names
        key_type_str = self.KEY_TYPE_MAP.get(params.get("key_type", "PRIMARY"), "primary")
        data_type_str = params.get("data_type")  # New: AS dataType syntax

        # Parse data type if specified
        if data_type_str:
            key_data_type = PrimitiveDataType(self.TYPE_STR_MAP.get(data_type_str.upper(), PrimitiveType.STRING))
        else:
            key_data_type = PrimitiveDataType(PrimitiveType.INTEGER)

        # If no entity specified, use the last created entity from key_registry
        if not entity_name and self._last_created_entity:
            print(f"[NOTICE] ADD_KEY: no entity specified, using last created entity '{self._last_created_entity}'")
            entity_name = self._last_created_entity

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not key_columns:
            return False

        # If entity doesn't exist yet, create a minimal one or defer
        if not entity:
            print(f"[NOTICE] ADD_KEY: entity '{entity_name}' not found, auto-creating")
            # Create entity with just the key
            entity = EntityType(object_name=[entity_name] if entity_name else ["unnamed"])
            self.database.add_entity_type(entity)

        # Get or create attributes for all key columns
        key_attrs = []
        for col_name in key_columns:
            attr = entity.get_attribute(col_name)
            if not attr:
                attr = Attribute(col_name, key_data_type, True, False)
                entity.add_attribute(attr)
            else:
                attr.is_key = True
                attr.is_optional = False
                if data_type_str:
                    attr.data_type = key_data_type
            key_attrs.append(attr)

        # Determine PKTypeEnum for partition/clustering keys
        pk_type_enum = PKTypeEnum.SIMPLE
        if isinstance(key_type_str, PKTypeEnum):
            pk_type_enum = key_type_str
            key_type_str = "primary"  # Partition/Clustering are variants of primary key

        if key_type_str == "foreign":
            # Create ForeignKeyConstraint
            fk_props = []
            ref_entity_name = None
            ref_attrs = []
            clauses = params.get("clauses", {})
            if "references" in clauses:
                ref_entity_name = clauses["references"]["table"]
                ref_attrs = clauses["references"]["columns"]
            for i, attr in enumerate(key_attrs):
                target_attr = ref_attrs[i] if i < len(ref_attrs) else (ref_attrs[0] if ref_attrs else "")
                target_up_id = self._get_target_unique_property_id(ref_entity_name, target_attr)
                fk_props.append(ForeignKeyProperty(
                    property_id=attr.meta_id,
                    points_to_unique_property_id=target_up_id
                ))
            constraint = ForeignKeyConstraint(is_managed=True, foreign_key_properties=fk_props)
        else:
            # Create UniqueConstraint (primary or unique) - supports composite keys
            unique_props = [UniqueProperty(primary_key_type=pk_type_enum, property_id=attr.meta_id)
                           for attr in key_attrs]
            constraint = UniqueConstraint(
                is_primary_key=(key_type_str == "primary"),
                is_managed=True,
                unique_properties=unique_props
            )

        # Handle primary key constraint addition
        if isinstance(constraint, UniqueConstraint) and constraint.is_primary_key:
            if pk_type_enum in (PKTypeEnum.PARTITION, PKTypeEnum.CLUSTERING):
                # PARTITION/CLUSTERING: append to existing PK constraint if present
                existing_pk = None
                for old_c in entity.constraints:
                    if isinstance(old_c, UniqueConstraint) and old_c.is_primary_key:
                        existing_pk = old_c
                        break
                if existing_pk:
                    # Append new key columns to existing composite PK (skip duplicates)
                    existing_ids = {up.property_id for up in existing_pk.unique_properties}
                    for up in constraint.unique_properties:
                        if up.property_id not in existing_ids:
                            existing_pk.unique_properties.append(up)
                    key_names_str = ", ".join(key_columns)
                    self.changes.append(f"ADD_KEY:{entity_name}.({key_names_str})")
                    return True
            else:
                # Regular PRIMARY KEY: replace existing PK
                # Clear is_key on old PK attributes
                for old_c in entity.constraints:
                    if isinstance(old_c, UniqueConstraint) and old_c.is_primary_key:
                        for up in old_c.unique_properties:
                            old_attr = entity.get_attribute_by_id(up.property_id)
                            if old_attr and old_attr.attr_name not in key_columns:
                                old_attr.is_key = False
                # Remove old PK constraints
                entity.constraints = [c for c in entity.constraints
                                      if not (isinstance(c, UniqueConstraint) and c.is_primary_key)]

        entity.add_constraint(constraint)
        key_names_str = ", ".join(key_columns)
        self.changes.append(f"ADD_KEY:{entity_name}.({key_names_str})")
        return True

    def _get_target_unique_property_id(self, target_entity_name: str, target_attr_name: str) -> str:
        """Get the UniqueProperty meta_id for a target entity's attribute (for FK references)."""
        if not target_entity_name:
            return ""
        target_entity = self.database.get_entity_type(target_entity_name)
        if not target_entity:
            return ""
        target_pk = target_entity.get_primary_key()
        if not target_pk or not target_pk.unique_properties:
            return ""
        # If target_attr_name is specified, find matching UniqueProperty
        if target_attr_name:
            for up in target_pk.unique_properties:
                attr = target_entity.get_attribute_by_id(up.property_id)
                if attr and attr.attr_name == target_attr_name:
                    return up.meta_id
        # Default to first UniqueProperty
        return target_pk.unique_properties[0].meta_id

    def _remove_key_constraint(self, params: Dict, operation: str = "DELETE") -> bool:
        """Helper method for DELETE_KEY operations"""
        entity_name = params.get("entity")
        key_columns = params.get("key_columns", [])  # List of column names
        key_type_str = self.KEY_TYPE_MAP.get(params["key_type"], "primary")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity or not key_columns:
            return False

        key_columns_set = set(key_columns)

        for constraint in list(entity.constraints):
            if key_type_str == "foreign" and isinstance(constraint, ForeignKeyConstraint):
                # Check if all FK columns match
                fk_attr_names = set()
                for fk_prop in constraint.foreign_key_properties:
                    fk_attr = entity.get_attribute_by_id(fk_prop.property_id)
                    if fk_attr:
                        fk_attr_names.add(fk_attr.attr_name)
                if fk_attr_names == key_columns_set:
                    entity.constraints.remove(constraint)
                    for fk_prop in constraint.foreign_key_properties:
                        fk_attr = entity.get_attribute_by_id(fk_prop.property_id)
                        if fk_attr:
                            fk_attr.is_key = False
                    key_names_str = ", ".join(key_columns)
                    self.changes.append(f"{operation}_KEY:{entity_name}.({key_names_str})")
                    return True

            elif key_type_str in ("primary", "unique") and isinstance(constraint, UniqueConstraint):
                is_primary = (key_type_str == "primary")
                if constraint.is_primary_key == is_primary:
                    # Check if all constraint columns match
                    constraint_attr_names = set()
                    for up in constraint.unique_properties:
                        up_attr = entity.get_attribute_by_id(up.property_id)
                        if up_attr:
                            constraint_attr_names.add(up_attr.attr_name)
                    if constraint_attr_names == key_columns_set:
                        entity.constraints.remove(constraint)
                        for up in constraint.unique_properties:
                            up_attr = entity.get_attribute_by_id(up.property_id)
                            if up_attr:
                                up_attr.is_key = False
                        key_names_str = ", ".join(key_columns)
                        self.changes.append(f"{operation}_KEY:{entity_name}.({key_names_str})")
                        return True

            elif isinstance(key_type_str, PKTypeEnum) and isinstance(constraint, UniqueConstraint):
                # Cassandra PARTITION/CLUSTERING keys: remove matching properties
                removed_any = False
                for up in list(constraint.unique_properties):
                    if up.primary_key_type == key_type_str:
                        up_attr = entity.get_attribute_by_id(up.property_id)
                        if up_attr and up_attr.attr_name in key_columns_set:
                            constraint.unique_properties.remove(up)
                            up_attr.is_key = False
                            removed_any = True
                if removed_any:
                    key_names_str = ", ".join(key_columns)
                    self.changes.append(f"{operation}_KEY:{entity_name}.({key_names_str})")
                    if not constraint.unique_properties:
                        entity.constraints.remove(constraint)
                    return True
        return False

    def _handle_rename(self, params: Dict) -> bool:
        """RENAME: Rename an attribute within an entity."""
        old_name = params["old_name"]
        new_name = params["new_name"]
        entity_name = params.get("entity")

        if not entity_name:
            print(f"[NOTICE] RENAME skipped: no entity specified for '{old_name}'")
            return False

        entity = self._get_entity(entity_name, "RENAME")
        if not entity:
            return False

        attr = entity.get_attribute(old_name)
        if attr:
            attr.attr_name = new_name
            # Update Reference.ref_name if this attribute is a FK
            for rel in entity.relationships:
                if isinstance(rel, Reference) and rel.ref_name == old_name:
                    rel.ref_name = new_name
                    break
            self.changes.append(f"RENAME:{entity_name}.{old_name}->{new_name}")
            return True
        return False

    def _handle_rename_entity(self, params: Dict) -> bool:
        """RENAME ENTITY: Rename an entity."""
        old_name = params["old_name"]
        new_name = params["new_name"]

        entity = self._get_entity(old_name, "RENAME_ENTITY")
        if not entity:
            return False
        # Collision check: prevent overwriting an existing entity
        if self.database.get_entity_type(new_name):
            print(f"[NOTICE] RENAME_ENTITY skipped: target '{new_name}' already exists")
            return False

        self.database.remove_entity_type(old_name)
        # Update object_name: keep parent path, change last element
        entity.object_name = entity.parent_path + [new_name]
        self.database.add_entity_type(entity)
        # Update cross-references in other entities
        for other_entity in self.database.entity_types.values():
            for rel in other_entity.relationships:
                if hasattr(rel, 'refs_to') and rel.refs_to == old_name:
                    rel.refs_to = new_name
                if hasattr(rel, 'aggregates') and rel.aggregates == old_name:
                    rel.aggregates = new_name
                if isinstance(rel, Edge):
                    if rel.source_entity == old_name:
                        rel.source_entity = new_name
                    if rel.target_entity == old_name:
                        rel.target_entity = new_name
        # Update EDGE entity source/target references
        for e in self.database.entity_types.values():
            if e.entity_kind == EntityKind.EDGE:
                if e.source_entity == old_name:
                    e.source_entity = new_name
                if e.target_entity == old_name:
                    e.target_entity = new_name
        # If renaming an EDGE entity, update Edge.rel_type_name on source entity
        if entity.entity_kind == EntityKind.EDGE and entity.source_entity:
            source_ent = self.database.get_entity_type(entity.source_entity)
            if source_ent:
                for rel in source_ent.relationships:
                    if isinstance(rel, Edge) and rel.rel_type_name == old_name:
                        rel.rel_type_name = new_name
        self.changes.append(f"RENAME_ENTITY:{old_name}->{new_name}")
        return True

    def _handle_copy(self, params: Dict) -> bool:
        """
        COPY: Copy attribute from source to target.

        Supports nested paths for embedded objects:
        - COPY person.address.street TO address.street
          Source: entity="person.address", attr="street"
          Target: entity="address", attr="street"
        """
        source_path = params["source"]
        target_path = params["target"]

        src_entity, src_attr_name = self._resolve_entity_attr(source_path)
        tgt_entity, tgt_attr_name = self._resolve_entity_attr(target_path)

        if src_entity and tgt_entity:
            # Copy attribute
            src_attr = src_entity.get_attribute(src_attr_name)
            if src_attr:
                new_attr = Attribute(tgt_attr_name, src_attr.data_type, False, src_attr.is_optional)
                tgt_entity.add_attribute(new_attr)
                self.changes.append(f"COPY:{source_path}->{target_path}")
                return True
        elif "." not in source_path and "." not in target_path:
            # Copy entity
            src_entity = self.database.get_entity_type(source_path)
            if src_entity:
                new_entity = copy.deepcopy(src_entity)
                # Update object_name with new target name
                new_entity.object_name = [target_parts[0]]
                self.database.add_entity_type(new_entity)
                self.changes.append(f"COPY:{source_path}->{target_path}")
                return True
        return False

    def _handle_copy_entity(self, params: Dict) -> bool:
        """COPY_ENTITY: Duplicate an entire entity with all its structure.

        Reference: PRISM "COPY TABLE R INTO S", CoDEL "Addtable(S, R)"
        Deep copies the source entity (attributes, keys, constraints, relationships)
        and adds it as a new entity with the target name.

        Example: COPY_ENTITY person AS employee
        Example: COPY_ENTITY works_at AS employed_at FROM person TO company  (EDGE)
        """
        source_name = params["source"]
        target_name = params["target"]
        source_entity_name = params.get("source_entity")
        target_entity_name = params.get("target_entity")

        src_entity = self._get_entity(source_name, "COPY_ENTITY")
        if not src_entity:
            return False

        # EDGE requires explicit FROM...TO
        if src_entity.entity_kind == EntityKind.EDGE and not (source_entity_name and target_entity_name):
            print(f"[ERROR] COPY_ENTITY failed: source '{source_name}' is an EDGE entity, FROM...TO is required")
            return False

        # Non-EDGE must not use FROM...TO
        if src_entity.entity_kind != EntityKind.EDGE and (source_entity_name or target_entity_name):
            print(f"[ERROR] COPY_ENTITY failed: source '{source_name}' is not an EDGE entity, FROM...TO is not allowed (use CAST_ENTITY to change entity kind)")
            return False

        new_entity = copy.deepcopy(src_entity)
        new_entity.object_name = [target_name]
        # Update relationship paths that reference the old entity name
        for rel in new_entity.relationships:
            if isinstance(rel, Embedded):
                if rel.aggregates.startswith(source_name + "."):
                    rel.aggregates = target_name + rel.aggregates[len(source_name):]
                elif rel.aggregates == source_name:
                    rel.aggregates = target_name
            elif isinstance(rel, Reference):
                if rel.refs_to == source_name:
                    rel.refs_to = target_name
            elif isinstance(rel, Edge):
                if rel.source_entity == source_name:
                    rel.source_entity = target_name

        # Handle EDGE: set explicit FROM...TO and add Edge to source VERTEX
        if source_entity_name and target_entity_name:
            new_entity.source_entity = source_entity_name
            new_entity.target_entity = target_entity_name
            new_entity.entity_kind = EntityKind.EDGE
            # Add Edge relationship to source VERTEX
            source_ent = self.database.get_entity_type(source_entity_name)
            if source_ent:
                source_ent.add_relationship(Edge(
                    rel_type_name=target_name,
                    source_entity=source_entity_name,
                    target_entity=target_entity_name,
                    cardinality=src_entity.edge_cardinality if hasattr(src_entity, 'edge_cardinality') and src_entity.edge_cardinality else Cardinality.ZERO_TO_MANY
                ))

        self.database.add_entity_type(new_entity)
        self.changes.append(f"COPY_ENTITY:{source_name}->{target_name}")
        return True

    def _handle_move(self, params: Dict) -> bool:
        """MOVE: Move attribute from one entity to another."""
        source_path = params["source"]
        target_path = params["target"]

        src_entity, src_attr_name = self._resolve_entity_attr(source_path)
        tgt_entity, tgt_attr_name = self._resolve_entity_attr(target_path)

        if src_entity and tgt_entity:
                src_attr = src_entity.get_attribute(src_attr_name)
                if src_attr:
                    # Add to target
                    new_attr = Attribute(tgt_attr_name, src_attr.data_type, False, src_attr.is_optional)
                    tgt_entity.add_attribute(new_attr)
                    # Remove from source
                    src_entity.remove_attribute(src_attr_name)
                    self.changes.append(f"MOVE:{source_path}->{target_path}")
                    return True
        return False

    def _handle_merge(self, params: Dict) -> bool:
        """MERGE: Merge two entities into one."""
        source1_name = params["source1"]
        source2_name = params["source2"]
        target_name = params["target"]

        source1 = self._get_entity(source1_name, "MERGE")
        source2 = self._get_entity(source2_name, "MERGE")
        if not source1 or not source2:
            return False

        # EDGE entities cannot be merged
        if source1.entity_kind == EntityKind.EDGE:
            print(f"[ERROR] MERGE failed: entity '{source1_name}' is an EDGE entity, MERGE does not support EDGE")
            return False
        if source2.entity_kind == EntityKind.EDGE:
            print(f"[ERROR] MERGE failed: entity '{source2_name}' is an EDGE entity, MERGE does not support EDGE")
            return False

        # Create new entity with combined attributes
        new_entity = EntityType(object_name=[target_name])

        # Track old->new meta_id mapping for constraint property_id remap
        meta_id_map = {}

        # Add attributes from source1
        for attr in source1.attributes:
            new_attr = Attribute(attr.attr_name, attr.data_type, attr.is_key, attr.is_optional)
            meta_id_map[attr.meta_id] = new_attr.meta_id
            new_entity.add_attribute(new_attr)

        # Add attributes from source2 (avoid duplicates)
        existing_names = {a.attr_name for a in new_entity.attributes}
        for attr in source2.attributes:
            if attr.attr_name not in existing_names:
                new_attr = Attribute(attr.attr_name, attr.data_type, attr.is_key, attr.is_optional)
                meta_id_map[attr.meta_id] = new_attr.meta_id
                new_entity.add_attribute(new_attr)

        # Copy constraints from source1 with remapped property_ids
        has_pk = False
        for constraint in source1.constraints:
            new_c = copy.deepcopy(constraint)
            if isinstance(new_c, UniqueConstraint):
                if new_c.is_primary_key:
                    has_pk = True
                for up in new_c.unique_properties:
                    if up.property_id in meta_id_map:
                        up.property_id = meta_id_map[up.property_id]
            elif isinstance(new_c, ForeignKeyConstraint):
                for fkp in new_c.foreign_key_properties:
                    if fkp.property_id in meta_id_map:
                        fkp.property_id = meta_id_map[fkp.property_id]
            new_entity.add_constraint(new_c)

        # Copy constraints from source2 (skip duplicate PK)
        for constraint in source2.constraints:
            new_c = copy.deepcopy(constraint)
            if isinstance(new_c, UniqueConstraint):
                if new_c.is_primary_key and has_pk:
                    continue  # Skip duplicate primary key
                for up in new_c.unique_properties:
                    if up.property_id in meta_id_map:
                        up.property_id = meta_id_map[up.property_id]
            elif isinstance(new_c, ForeignKeyConstraint):
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

        self.changes.append(f"MERGE:{source1_name},{source2_name}->{target_name}")
        return True

    def _handle_split(self, params: Dict) -> bool:
        """
        SPLIT: Divide one entity into multiple separate entities (vertical partitioning).

        Reference: André Conrad - "SPLIT Person into Person:id, firstname, lastname AND knows:id, knows"

        Example: SPLIT_PS person INTO person(person_id, vorname, nachname, age), person_tag(person_id, tags)
          Before: person { person_id, vorname, nachname, age, tags[] }
          After:  person { person_id, vorname, nachname, age }
                 person_tag { person_id, tags[] }

        Note: Fields can be duplicated across parts (e.g., person_id in both parts for FK relationship).
        """
        source_name = params.get("source")
        parts = params.get("parts", [])

        source = self.database.get_entity_type(source_name)
        if not source or not parts:
            return False

        # EDGE entities cannot be split
        if source.entity_kind == EntityKind.EDGE:
            print(f"[ERROR] SPLIT failed: entity '{source_name}' is an EDGE entity, SPLIT does not support EDGE")
            return False

        pk = source.get_primary_key()
        created_entities = []

        # First pass: create NEW entities (parts with different name than source).
        # Must happen before modifying source, so attribute copying works.
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
                    attr = source.get_attribute(field_name)
                    if attr:
                        # Create new attribute with is_key preserved from source
                        new_attr = Attribute(
                            attr.attr_name, attr.data_type, attr.is_key, attr.is_optional
                        )
                        meta_id_map[attr.meta_id] = new_attr.meta_id
                        new_entity.add_attribute(new_attr)
            else:
                # Fallback: split attributes evenly (old behavior)
                attrs = list(source.attributes)
                mid = len(attrs) // 2
                if i == 0:
                    selected_attrs = attrs[:mid] if mid > 0 else attrs[:1]
                else:
                    selected_attrs = attrs[mid:] if mid > 0 else attrs[1:]

                for attr in selected_attrs:
                    new_attr = Attribute(
                        attr.attr_name, attr.data_type, attr.is_key, attr.is_optional
                    )
                    meta_id_map[attr.meta_id] = new_attr.meta_id
                    new_entity.add_attribute(new_attr)

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
            attrs_to_remove = [a.attr_name for a in source.attributes
                               if a.attr_name not in keep_fields]
            for attr_name in attrs_to_remove:
                source.remove_attribute(attr_name)

        # Remove source if different from all targets
        if source_name not in [p["name"] for p in parts]:
            self.database.remove_entity_type(source_name)

        parts_str = ",".join(created_entities)
        self.changes.append(f"SPLIT:{source_name}->{parts_str}")
        return True

    def _handle_cast(self, params: Dict) -> bool:
        """CAST: Change attribute data type."""
        target = params["target"]
        new_type_str = params.get("data_type", params.get("type", "STRING")).upper()

        entity, attr_name = self._resolve_entity_attr(target, "CAST")
        if not entity:
            return False

        attr = entity.get_attribute(attr_name)
        if not attr:
            print(f"[NOTICE] CAST skipped: attribute '{attr_name}' not found")
            return False

        new_type = self.TYPE_STR_MAP.get(new_type_str, PrimitiveType.STRING)
        attr.data_type = PrimitiveDataType(new_type)
        self.changes.append(f"CAST:{target}->{new_type_str}")
        return True

    def _handle_cast_constraint(self, params: Dict) -> bool:
        """CAST_CONSTRAINT: Change the type of a constraint.

        Reference: Orion "Cast Reference" - change the type of a constraint.
        Example: CAST_CONSTRAINT person.email TO UNIQUE KEY
        Example: CAST_CONSTRAINT person.city TO PARTITION KEY
        """
        target = params["target"]
        new_type = params["constraint_type"]  # PRIMARY_KEY, UNIQUE_KEY, PARTITION_KEY, CLUSTERING_KEY, NODE_KEY, DOCUMENT_ID

        entity, attr_name = self._resolve_entity_attr(target)
        if not entity:
            return False

        # Find the attribute
        attr = entity.get_attribute(attr_name)
        if not attr:
            return False

        # Find constraint containing this attribute and modify its type
        for constraint in entity.constraints:
            if isinstance(constraint, UniqueConstraint):
                for up in constraint.unique_properties:
                    if up.property_id == attr.meta_id:
                        if new_type == "PRIMARY_KEY":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.SIMPLE
                        elif new_type == "UNIQUE_KEY":
                            constraint.is_primary_key = False
                        elif new_type == "PARTITION_KEY":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.PARTITION
                        elif new_type == "CLUSTERING_KEY":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.CLUSTERING
                        elif new_type == "NODE_KEY":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.NODE_KEY
                        elif new_type == "DOCUMENT_ID":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.DOCUMENT_ID
                        self.changes.append(f"CAST_CONSTRAINT:{target}->{new_type}")
                        return True
        return False

    def _handle_cast_entity(self, params: Dict) -> bool:
        """CAST_ENTITY: Change the entity_kind of an entity type (cross-paradigm type conversion).

        Overrides automatic entity_kind normalization for this entity.
        For VERTEX<->EDGE conversion, use TRANSFORM instead.
        Example: CAST_ENTITY orders TO DOCUMENT
        Example: CAST_ENTITY person TO GRAPH
        """
        target = params["target"]
        entity_kind_str = params["entity_kind"]

        entity = self._get_entity(target, "CAST_ENTITY")
        if not entity:
            return False

        # EDGE entities must use TRANSFORM, not CAST_ENTITY
        if entity.entity_kind == EntityKind.EDGE:
            print(f"[ERROR] CAST_ENTITY failed: entity '{target}' is an EDGE entity, use TRANSFORM INTO ENTITY first")
            return False

        kind_map = {
            "RELATIONAL": EntityKind.TABLE,
            "DOCUMENT": EntityKind.DOCUMENT,
            "GRAPH": EntityKind.VERTEX,
            "COLUMNAR": EntityKind.WIDE_COLUMN_TABLE,
        }

        new_kind = kind_map.get(entity_kind_str)
        if not new_kind:
            return False
        entity.entity_kind = new_kind

        self._explicitly_cast_entities.add(target)
        self.changes.append(f"CAST_ENTITY:{target}->{entity_kind_str}")
        return True

    def _handle_recard(self, params: Dict) -> bool:
        """RECARD: Change the multiplicity/cardinality of a reference.

        Reference: Orion "Mult Reference" - change the multiplicity of a reference.
        Example: RECARD person.address_id TO ONE_TO_MANY
        """
        target = params["target"]
        new_cardinality_str = params["cardinality"]

        entity, ref_name = self._resolve_entity_attr(target)
        if not entity:
            return False

        new_cardinality = self.CARDINALITY_MAP.get(new_cardinality_str, None)
        if not new_cardinality:
            return False

        # Find the reference relationship and update its cardinality
        for rel in entity.relationships:
            if isinstance(rel, Reference) and rel.ref_name == ref_name:
                rel.cardinality = new_cardinality
                self.changes.append(f"RECARD:{target}->{new_cardinality_str}")
                return True
            elif isinstance(rel, Edge) and rel.rel_type_name == ref_name:
                rel.cardinality = new_cardinality
                self.changes.append(f"RECARD:{target}->{new_cardinality_str}")
                return True
        return False

    def _handle_transform(self, params: Dict) -> bool:
        """TRANSFORM: Convert between entity (node) and relationship type (edge).

        Based on Hausler et al. - nodeToRel / relToNode graph evolution operations.

        TO RELATIONSHIP: EntityType (VERTEX) -> EntityType (EDGE)
          - Changes entity_kind to EDGE, sets source/target
          - Adds Edge to source entity's relationships

        TO ENTITY: EntityType (EDGE) -> EntityType (VERTEX)
          - Changes entity_kind to VERTEX, clears source/target
          - Removes Edge from source entity's relationships
        """
        name = params["name"]
        target_type = params["target_type"]

        if target_type == "RELATIONSHIP":
            source_entity_name = params["source_entity"]
            target_entity_name = params["target_entity"]

            entity = self._get_entity(name, "TRANSFORM")
            if not entity:
                return False

            # Resolve cardinality (default: ZERO_TO_MANY)
            cardinality = Cardinality.ZERO_TO_MANY
            if "cardinality" in params:
                cardinality = self.CARDINALITY_MAP.get(params["cardinality"], Cardinality.ZERO_TO_MANY)

            # Convert VERTEX -> EDGE
            entity.entity_kind = EntityKind.EDGE
            entity.source_entity = source_entity_name
            entity.target_entity = target_entity_name
            entity.edge_cardinality = cardinality

            # Add Edge to source entity's relationships (avoid duplicates)
            source_ent = self.database.get_entity_type(source_entity_name)
            if source_ent:
                existing_edge = any(
                    isinstance(r, Edge) and r.rel_type_name == name
                    for r in source_ent.relationships
                )
                if not existing_edge:
                    edge = Edge(
                        rel_type_name=name,
                        source_entity=source_entity_name,
                        target_entity=target_entity_name,
                        cardinality=cardinality
                    )
                    source_ent.add_relationship(edge)

            self.changes.append(f"TRANSFORM:{name}->RELATIONSHIP({source_entity_name},{target_entity_name})")
            return True

        elif target_type == "ENTITY":
            edge_entity = self._get_entity(name, "TRANSFORM")
            if not edge_entity or edge_entity.entity_kind != EntityKind.EDGE:
                return False

            # Remove Edge from source entity's relationships
            if edge_entity.source_entity:
                source_ent = self.database.get_entity_type(edge_entity.source_entity)
                if source_ent:
                    source_ent.remove_relationship(name)

            # Convert EDGE -> VERTEX
            edge_entity.entity_kind = EntityKind.VERTEX
            edge_entity.source_entity = None
            edge_entity.target_entity = None
            edge_entity.edge_cardinality = None

            self.changes.append(f"TRANSFORM:{name}->ENTITY")
            return True
        return False



def _get_type_str(data_type) -> str:
    """Convert data type to string representation."""
    if hasattr(data_type, 'primitive_type'):
        return data_type.primitive_type.value
    elif hasattr(data_type, 'key_type'):
        # MapDataType - check before element_type since Map may also have it
        key = _get_type_str(data_type.key_type)
        val = _get_type_str(data_type.value_type)
        return f"map[{key},{val}]"
    elif hasattr(data_type, 'element_type'):
        # ListDataType / SetDataType
        element = _get_type_str(data_type.element_type)
        if type(data_type).__name__ == 'SetDataType':
            return f"set[{element}]"
        return f"array[{element}]"
    return 'unknown'


def _serialize_entity(name: str, entity) -> Dict[str, Any]:
    """Serialize a single EntityType to dict (shared by db_to_dict and db_to_source_dict)."""
    # Serialize constraints
    constraints = []
    for c in entity.constraints:
        if isinstance(c, UniqueConstraint):
            pk_attr_names = []
            pk_types = []
            for up in c.unique_properties:
                attr = entity.get_attribute_by_id(up.property_id)
                pk_attr_names.append(attr.attr_name if attr else up.property_id)
                pk_types.append(up.primary_key_type.value)
            constraint_dict = {
                "type": "PRIMARY_KEY" if c.is_primary_key else "UNIQUE",
                "columns": pk_attr_names,
            }
            # Include primary_key_type for Cassandra PARTITION/CLUSTERING distinction
            if any(t != "simple" for t in pk_types):
                constraint_dict["primary_key_types"] = pk_types
            constraints.append(constraint_dict)
        elif isinstance(c, ForeignKeyConstraint):
            for fkp in c.foreign_key_properties:
                attr = entity.get_attribute_by_id(fkp.property_id)
                col_name = attr.attr_name if attr else fkp.property_id
                # Resolve target entity from Reference relationships matching this FK column
                ref_target = ""
                for rel in entity.relationships:
                    if isinstance(rel, Reference) and rel.ref_name == col_name:
                        ref_target = rel.get_target_entity_name()
                        break
                constraints.append({
                    "type": "FOREIGN_KEY",
                    "column": col_name,
                    "references_entity": ref_target,
                    "references_property": fkp.points_to_unique_property_id
                })

    # Build pk_type_map for Cassandra PARTITION/CLUSTERING key_type
    pk_type_map = {}
    for c in entity.constraints:
        if isinstance(c, UniqueConstraint) and c.is_primary_key:
            for up in c.unique_properties:
                attr = entity.get_attribute_by_id(up.property_id)
                attr_name = attr.attr_name if attr else up.property_id
                pk_val = up.primary_key_type.value
                if pk_val != "simple":
                    pk_type_map[attr_name] = pk_val

    # Build attribute list with optional key_type
    serialized_attrs = []
    for a in entity.attributes:
        attr_dict = {
            "name": a.attr_name,
            "type": _get_type_str(a.data_type),
            "is_key": a.is_key,
            "is_optional": a.is_optional,
        }
        if a.attr_name in pk_type_map:
            attr_dict["key_type"] = pk_type_map[a.attr_name]
        serialized_attrs.append(attr_dict)

    return {
        "name": name,
        "entity_kind": entity.entity_kind.value,
        "attributes": serialized_attrs,
        "constraints": constraints,
        "references": [
            {
                "name": r.ref_name,
                "target": r.get_target_entity_name(),
                "cardinality": r.cardinality.value if hasattr(r, 'cardinality') else '1..1',
                **({"edge_attributes": [
                    {"name": a.attr_name, "type": _get_type_str(a.data_type)}
                    for a in r.edge_attributes
                ]} if r.edge_attributes else {})
            }
            for r in entity.relationships if isinstance(r, Reference)
        ],
        "embedded": [
            {
                "name": r.aggr_name,
                "target": r.get_target_entity_name(),
                "cardinality": r.cardinality.value
            }
            for r in entity.relationships if isinstance(r, Embedded)
        ],
        "edges": [
            {
                "name": r.rel_type_name,
                "target": r.get_target_entity_name(),
                "source": r.source_entity,
                "cardinality": r.cardinality.value
            }
            for r in entity.relationships if isinstance(r, Edge)
        ],
        "labels": getattr(entity, 'labels', [])
    }


def _serialize_relationship_types(db: Database) -> Dict[str, Any]:
    """Serialize EDGE entities as relationship_types."""
    result = {}
    for name, e in db.entity_types.items():
        if e.entity_kind != EntityKind.EDGE:
            continue
        result[name] = {
            "rel_name": e.name,
            "source_entity": e.source_entity or "",
            "target_entity": e.target_entity or "",
            "attributes": [
                {"name": a.attr_name, "type": _get_type_str(a.data_type)}
                for a in e.attributes
            ],
            "cardinality": (e.edge_cardinality or Cardinality.ZERO_TO_MANY).value
        }
    return result


def db_to_dict(db: Database) -> Dict[str, Any]:
    """
    Convert Database to a JSON-serializable dictionary (Unified Meta Schema format).

    Returns dict with "entities" and optionally "relationship_types" keys.
    """
    entities = {}
    for name, entity in db.entity_types.items():
        if entity.entity_kind == EntityKind.EDGE:
            continue  # EDGE entities are serialized as relationship_types
        entities[name] = _serialize_entity(name, entity)

    result = entities  # Keep flat entity dict for backward compatibility with web UI

    # Attach relationship_types (derived from EDGE entities)
    rel_types = _serialize_relationship_types(db)
    if rel_types:
        result["__relationship_types__"] = rel_types

    # Include database-level metadata
    result["__db_meta__"] = {
        "db_name": db.db_name,
        "db_type": db.db_type.value,
    }

    return result


# Type mappings for source format display (from centralized TypeMappings)


def _get_source_type_str(attr: Attribute, source_type: str) -> str:
    """Get the original type string for an attribute based on source database type."""
    # Handle complex types first
    if not hasattr(attr.data_type, 'primitive_type'):
        if source_type == SOURCE_TYPE_RELATIONAL:
            if hasattr(attr.data_type, 'key_type'):
                return "JSONB"
            elif hasattr(attr.data_type, 'element_type'):
                return "JSONB"
            return "VARCHAR"
        elif source_type == SOURCE_TYPE_COLUMNAR:
            if hasattr(attr.data_type, 'key_type'):
                return "MAP"
            elif hasattr(attr.data_type, 'element_type'):
                return "LIST"
            return "TEXT"
        elif source_type == SOURCE_TYPE_GRAPH:
            if hasattr(attr.data_type, 'element_type'):
                return "list"
            return "string"
        elif source_type == SOURCE_TYPE_DOCUMENT:
            # Document (MongoDB)
            if hasattr(attr.data_type, 'key_type'):
                return "object"
            elif hasattr(attr.data_type, 'element_type'):
                return "array"
            return "string"
        else:
            return "unknown"

    primitive = attr.data_type.primitive_type

    if source_type == SOURCE_TYPE_RELATIONAL:
        # PostgreSQL format (using centralized TypeMappings)
        base_type = TypeMappings.PRIMITIVE_TO_PG_DISPLAY.get(primitive, 'VARCHAR')

        # Use SERIAL for integer PKs
        if base_type == 'INTEGER' and attr.is_key:
            return 'SERIAL'

        # Handle VARCHAR with length
        if base_type == 'VARCHAR':
            max_len = attr.data_type.max_length if hasattr(attr.data_type, 'max_length') and attr.data_type.max_length else 255
            return f"VARCHAR({max_len})"

        # Handle DECIMAL with precision/scale
        if base_type == 'DECIMAL':
            precision = attr.data_type.precision if hasattr(attr.data_type, 'precision') and attr.data_type.precision else 13
            scale = attr.data_type.scale if hasattr(attr.data_type, 'scale') and attr.data_type.scale else 2
            return f"DECIMAL({precision},{scale})"

        return base_type
    elif source_type == SOURCE_TYPE_GRAPH:
        # Neo4j format (using centralized TypeMappings)
        return TypeMappings.PRIMITIVE_TO_NEO4J.get(primitive, 'string')
    elif source_type == SOURCE_TYPE_COLUMNAR:
        # Cassandra format (using centralized TypeMappings)
        return TypeMappings.PRIMITIVE_TO_CASSANDRA.get(primitive, 'TEXT')
    elif source_type == SOURCE_TYPE_DOCUMENT:
        # MongoDB format (bsonType, using centralized TypeMappings)
        return TypeMappings.PRIMITIVE_TO_MONGO_DISPLAY.get(primitive, 'string')
    else:
        return str(primitive.value) if primitive else 'unknown'


def db_to_source_dict(db: Database, source_type: str) -> Dict[str, Any]:
    """
    Convert Database to a JSON-serializable dictionary with original source format types.

    Args:
        db: Database instance
        source_type: "Relational", "Document", "Graph", or "Columnar"

    Returns:
        Dictionary representation with original type names (e.g., SERIAL, VARCHAR(35), bsonType)
    """
    entities = {}
    for name, entity in db.entity_types.items():
        if entity.entity_kind == EntityKind.EDGE:
            continue  # EDGE entities are serialized as relationship_types
        # Build entity dict with source-specific types
        entity_dict = _serialize_entity(name, entity)
        # Override attribute type with source-specific format, preserve key_type etc.
        for i, a in enumerate(entity.attributes):
            if i < len(entity_dict["attributes"]):
                entity_dict["attributes"][i]["type"] = _get_source_type_str(a, source_type)
        entities[name] = entity_dict

    # Attach relationship_types (derived from EDGE entities)
    rel_types = _serialize_relationship_types(db)
    if rel_types:
        entities["__relationship_types__"] = rel_types

    # Include database-level metadata (consistent with db_to_dict)
    entities["__db_meta__"] = {
        "db_name": db.db_name,
        "db_type": db.db_type.value,
    }

    return entities


def parse_original_source(raw_source: str, source_type: str) -> Dict[str, Any]:
    """
    Parse raw source schema into a nested structure for display.
    For MongoDB: returns the original nested document structure.
    For PostgreSQL: returns the table structure.
    """
    import json

    if source_type == SOURCE_TYPE_DOCUMENT:
        # Parse MongoDB JSON schema - return nested structure
        try:
            schema = json.loads(raw_source)
            collection_name = schema.get("title", "document")

            def parse_properties(properties: Dict) -> List[Dict]:
                """Recursively parse properties into nested structure."""
                result = []
                for prop_name, prop_def in properties.items():
                    bson_type = prop_def.get("bsonType", "string")

                    if bson_type == "object":
                        # Nested object - recurse
                        nested_props = prop_def.get("properties", {})
                        result.append({
                            "name": prop_name,
                            "type": "object",
                            "nested": parse_properties(nested_props)
                        })
                    elif bson_type == "array":
                        # Array - check item type and recurse into items if object
                        items = prop_def.get("items", {})
                        item_type = items.get("bsonType", "string")
                        entry = {
                            "name": prop_name,
                            "type": "array",
                            "description": prop_def.get("description", "")
                        }
                        if item_type == "object" and "properties" in items:
                            entry["nested"] = parse_properties(items["properties"])
                        result.append(entry)
                    else:
                        # Primitive type
                        result.append({
                            "name": prop_name,
                            "type": bson_type,
                            "is_key": prop_name == "_id"
                        })
                return result

            properties = schema.get("properties", {})
            return {
                collection_name: {
                    "name": collection_name,
                    "type": "collection",
                    "attributes": parse_properties(properties)
                }
            }
        except json.JSONDecodeError:
            return {}

    elif source_type == SOURCE_TYPE_GRAPH:
        # Parse Neo4j Graph schema - supports both Cypher DDL and JSON formats
        import re as _re

        # Detect format: Cypher DDL contains "// Node:" or "CREATE CONSTRAINT"
        is_cypher = ('// Node:' in raw_source or 'CREATE CONSTRAINT' in raw_source)

        if is_cypher:
            # Parse Cypher DDL format (// Node: / CREATE CONSTRAINT / // Properties: / // Relationship:)
            result = {}
            lines = raw_source.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Node block
                node_match = _re.match(r'^// Node:\s+(\w+)', line)
                if node_match:
                    label = node_match.group(1)
                    pk = None
                    attrs = []
                    j = i + 1
                    while j < len(lines):
                        nl = lines[j].strip()
                        km = _re.match(r'^// Key:\s+(\w+)', nl)
                        if km:
                            pk = km.group(1)
                            j += 1
                            continue
                        cm = _re.match(r'CREATE CONSTRAINT .+ REQUIRE n\.(\w+) IS UNIQUE;', nl)
                        if cm:
                            pk = cm.group(1)
                            j += 1
                            continue
                        pm = _re.match(r'^// Properties:\s+(.+)', nl)
                        if pm:
                            for prop in _re.findall(r'(\w+)\s+\((\w+)\)', pm.group(1)):
                                attrs.append({"name": prop[0], "type": prop[1], "is_key": prop[0] == pk})
                            j += 1
                            break
                        if nl == '' or nl.startswith('// Node:') or nl.startswith('// Relationship:'):
                            break
                        j += 1
                    result[label] = {"name": label, "type": "vertex", "attributes": attrs}
                    i = j
                    continue

                # Relationship block
                rel_match = _re.match(r'^// Relationship:\s+(\w+)\s+\((\w+)\s+->\s+(\w+)\)', line)
                if rel_match:
                    rel_name = rel_match.group(1)
                    source = rel_match.group(2)
                    target = rel_match.group(3)
                    attrs = []
                    j = i + 1
                    while j < len(lines):
                        nl = lines[j].strip()
                        pm = _re.match(r'^// Properties:\s+(.+)', nl)
                        if pm:
                            for prop in _re.findall(r'(\w+)\s+\((\w+)\)', pm.group(1)):
                                attrs.append({"name": prop[0], "type": prop[1], "is_key": False})
                            j += 1
                            continue
                        cm = _re.match(r'^// Cardinality:', nl)
                        if cm:
                            j += 1
                            break
                        if nl == '' or nl.startswith('// Node:') or nl.startswith('// Relationship:'):
                            break
                        j += 1
                    result[f"[{rel_name}]"] = {
                        "name": f"{source} -[{rel_name}]-> {target}",
                        "type": "edge",
                        "attributes": attrs
                    }
                    i = j
                    continue
                i += 1
            return result
        else:
            # Parse JSON format (legacy)
            try:
                schema = json.loads(raw_source)
                result = {}
                for node_def in schema.get("nodes", []):
                    label = node_def.get("label", "Unknown")
                    pk = node_def.get("primary_key")
                    attrs = []
                    for prop in node_def.get("properties", []):
                        attrs.append({
                            "name": prop.get("name", ""),
                            "type": prop.get("type", "string"),
                            "is_key": prop.get("name") == pk
                        })
                    result[label] = {
                        "name": label,
                        "type": "vertex",
                        "attributes": attrs
                    }
                for rel_def in schema.get("relationships", []):
                    rel_name = rel_def.get("type", "RELATED_TO")
                    attrs = []
                    for prop in rel_def.get("properties", []):
                        attrs.append({
                            "name": prop.get("name", ""),
                            "type": prop.get("type", "string"),
                            "is_key": False
                        })
                    result[f"[{rel_name}]"] = {
                        "name": f"{rel_def.get('source', '')} -[{rel_name}]-> {rel_def.get('target', '')}",
                        "type": "edge",
                        "attributes": attrs
                    }
                return result
            except json.JSONDecodeError:
                return {}

    elif source_type == SOURCE_TYPE_COLUMNAR:
        # Parse Cassandra CQL DDL - return table structure with key_type
        import re
        tables = {}
        # Remove comments
        cql = re.sub(r'--.*$', '', raw_source, flags=re.MULTILINE)
        cql = re.sub(r'/\*.*?\*/', '', cql, flags=re.DOTALL)
        # Extract CREATE TABLE statements
        pattern = re.compile(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[\w.]+\.)?(\w+)\s*\((.*?)\)\s*(?:WITH\s+.*?)?;',
            re.DOTALL | re.IGNORECASE
        )
        for match in pattern.finditer(cql):
            table_name = match.group(1)
            table_body = match.group(2)

            # Step 1: Extract PRIMARY KEY clause (handles nested parens)
            partition_keys = []
            clustering_keys = []
            pk_match = re.search(
                r'PRIMARY\s+KEY\s*\(\s*\(([^)]+)\)\s*(?:,\s*(.+))?\)',
                table_body, re.IGNORECASE
            )
            if pk_match:
                # Composite: PRIMARY KEY ((partition_cols), clustering_cols)
                partition_keys = [k.strip() for k in pk_match.group(1).split(',')]
                if pk_match.group(2):
                    clustering_keys = [k.strip() for k in pk_match.group(2).split(',')]
            else:
                # Simple: PRIMARY KEY (col) or inline PRIMARY KEY
                pk_simple = re.search(
                    r'PRIMARY\s+KEY\s*\(([^)]+)\)',
                    table_body, re.IGNORECASE
                )
                if pk_simple:
                    partition_keys = [pk_simple.group(1).strip()]

            # Step 2: Parse column definitions with key_type
            attrs = []
            for col_def in table_body.split(','):
                col_def = col_def.strip()
                if not col_def or re.match(r'PRIMARY\s+KEY', col_def, re.IGNORECASE):
                    continue
                parts = col_def.split()
                if len(parts) >= 2:
                    col_name = parts[0]
                    col_type = parts[1]
                    # Check inline PRIMARY KEY
                    inline_pk = 'PRIMARY KEY' in col_def.upper()
                    if inline_pk:
                        partition_keys = [col_name]

                    key_type = None
                    if col_name in partition_keys:
                        key_type = "partition"
                    elif col_name in clustering_keys:
                        key_type = "clustering"

                    attrs.append({
                        "name": col_name,
                        "type": col_type,
                        "is_key": col_name in partition_keys or col_name in clustering_keys or inline_pk,
                        "key_type": key_type
                    })
            tables[table_name] = {
                "name": table_name,
                "type": "wide_column_table",
                "attributes": attrs
            }
        return tables

    elif source_type == SOURCE_TYPE_RELATIONAL:
        # Relational (PostgreSQL) - parse SQL DDL
        tables = {}
        current_table = None
        lines = raw_source.split('\n')

        for line in lines:
            line = line.strip()
            if line.upper().startswith('CREATE TABLE'):
                # Extract table name
                parts = line.split()
                if len(parts) >= 3:
                    table_name = parts[2].rstrip('(').strip()
                    current_table = table_name
                    tables[table_name] = {
                        "name": table_name,
                        "type": "table",
                        "attributes": []
                    }
            elif current_table and line and not line.startswith('--') and not line.startswith(')'):
                # Parse column definition
                if 'PRIMARY KEY' in line.upper() and '(' in line:
                    continue  # Skip composite primary key line
                parts = line.rstrip(',').split()
                if len(parts) >= 2:
                    col_name = parts[0]
                    # Capture multi-word types like DOUBLE PRECISION
                    stop_keywords = {'PRIMARY', 'NOT', 'NULL', 'REFERENCES', 'DEFAULT', 'UNIQUE', 'CHECK', 'CONSTRAINT'}
                    type_parts = []
                    for p in parts[1:]:
                        if p.upper() in stop_keywords:
                            break
                        type_parts.append(p)
                    col_type = ' '.join(type_parts) if type_parts else parts[1]
                    is_key = 'PRIMARY KEY' in line.upper()
                    is_fk = 'REFERENCES' in line.upper()
                    tables[current_table]["attributes"].append({
                        "name": col_name,
                        "type": col_type,
                        "is_key": is_key,
                        "is_fk": is_fk
                    })
            elif line.startswith(')'):
                current_table = None

        return tables

    else:
        return {}


def _calculate_changes(prev: Dict, after: Dict, op) -> Dict:
    """Calculate the changes made by an operation."""
    changes = {
        "affected_entities": [],
        "new_entities": [],
        "deleted_entities": [],
        "modified_entities": [],
        "new_relationship_types": [],
        "deleted_relationship_types": [],
        "modified_relationship_types": []
    }

    # Separate entity keys from special keys (__relationship_types__)
    prev_entity_names = {k for k in prev.keys() if not k.startswith("__")}
    after_entity_names = {k for k in after.keys() if not k.startswith("__")}

    # Track relationship_type changes
    prev_rts = prev.get("__relationship_types__", {})
    after_rts = after.get("__relationship_types__", {})
    for rt_name in set(after_rts.keys()) - set(prev_rts.keys()):
        changes["new_relationship_types"].append(rt_name)
        changes["affected_entities"].append({
            "name": rt_name,
            "status": "new_reltype",
            "entity": after_rts[rt_name]
        })
    for rt_name in set(prev_rts.keys()) - set(after_rts.keys()):
        changes["deleted_relationship_types"].append(rt_name)
        changes["affected_entities"].append({
            "name": rt_name,
            "status": "deleted_reltype",
            "entity": prev_rts[rt_name]
        })

    # New entities
    for name in after_entity_names - prev_entity_names:
        changes["new_entities"].append(name)
        changes["affected_entities"].append({
            "name": name,
            "status": "new",
            "entity": after[name]
        })

    # Deleted entities
    for name in prev_entity_names - after_entity_names:
        changes["deleted_entities"].append(name)
        changes["affected_entities"].append({
            "name": name,
            "status": "deleted",
            "entity": prev[name]
        })

    # Modified entities
    for name in prev_entity_names & after_entity_names:
        prev_entity = prev[name]
        after_entity = after[name]

        # Check for changes in attributes
        prev_attrs = {a["name"]: a for a in prev_entity.get("attributes", [])}
        after_attrs = {a["name"]: a for a in after_entity.get("attributes", [])}

        # Check for changes in embedded
        prev_embedded = {e["name"]: e for e in prev_entity.get("embedded", [])}
        after_embedded = {e["name"]: e for e in after_entity.get("embedded", [])}

        # Check for changes in references
        prev_refs = {r["name"]: r for r in prev_entity.get("references", [])}
        after_refs = {r["name"]: r for r in after_entity.get("references", [])}

        # Check for changes in edges
        prev_edges = {e["name"]: e for e in prev_entity.get("edges", [])}
        after_edges = {e["name"]: e for e in after_entity.get("edges", [])}

        new_attrs = set(after_attrs.keys()) - set(prev_attrs.keys())
        deleted_attrs = set(prev_attrs.keys()) - set(after_attrs.keys())
        new_embedded = set(after_embedded.keys()) - set(prev_embedded.keys())
        deleted_embedded = set(prev_embedded.keys()) - set(after_embedded.keys())
        new_refs = set(after_refs.keys()) - set(prev_refs.keys())
        deleted_refs = set(prev_refs.keys()) - set(after_refs.keys())
        new_edges = set(after_edges.keys()) - set(prev_edges.keys())
        deleted_edges = set(prev_edges.keys()) - set(after_edges.keys())

        # Check for attribute TYPE changes (for CAST and UNWIND operations)
        type_changed_attrs = []
        for attr_name in set(prev_attrs.keys()) & set(after_attrs.keys()):
            prev_type = prev_attrs[attr_name].get("type", "")
            after_type = after_attrs[attr_name].get("type", "")
            if prev_type != after_type:
                type_changed_attrs.append({
                    "name": attr_name,
                    "old_type": prev_type,
                    "new_type": after_type
                })

        # Check for constraint changes (ADD_KEY, DELETE_KEY, CAST_CONSTRAINT)
        prev_constraints = prev_entity.get("constraints", [])
        after_constraints = after_entity.get("constraints", [])
        constraints_changed = prev_constraints != after_constraints

        # Check for entity_kind changes
        entity_kind_changed = (prev_entity.get("entity_kind") != after_entity.get("entity_kind"))

        if new_attrs or deleted_attrs or new_embedded or deleted_embedded or new_refs or deleted_refs or new_edges or deleted_edges or type_changed_attrs or constraints_changed or entity_kind_changed:
            changes["modified_entities"].append(name)
            changes["affected_entities"].append({
                "name": name,
                "status": "modified",
                "entity": after_entity,
                "new_attributes": [after_attrs[a] for a in new_attrs],
                "deleted_attributes": list(deleted_attrs),
                "new_embedded": [after_embedded[e] for e in new_embedded],
                "deleted_embedded": list(deleted_embedded),
                "new_references": [after_refs[r] for r in new_refs],
                "deleted_references": list(deleted_refs),
                "new_edges": [after_edges[e] for e in new_edges],
                "deleted_edges": list(deleted_edges),
                "type_changed_attributes": type_changed_attrs
            })

    return changes



def _normalize_entity_kinds(db: Database, target_type: str, source_type: str = "",
                            skip_entities: set = None) -> None:
    """Normalize entity_kind, PK types, and embedded cardinality for target database type.

    For cross-model migrations (e.g., R->G, G->R, D->C), entities may have
    entity_kind from the source DB type. This function converts ALL entities
    to match the target DB type so the target adapter can export them correctly.

    Entities in skip_entities (explicitly cast via CAST_ENTITY) are not normalized.

    Also normalizes:
    - PK types: SIMPLE <-> PARTITION/CLUSTERING for Columnar targets
    - Embedded cardinality: 0..1 -> 1..1, 0..n -> 1..n for Document targets
      (only for cross-model, not D->D where source cardinalities are already correct)
    """
    if skip_entities is None:
        skip_entities = set()
    target_kind = _ENTITY_KIND_DEFAULT.get(target_type, EntityKind.TABLE)
    for name, entity in db.entity_types.items():
        if name in skip_entities:
            continue
        if entity.entity_kind == EntityKind.EDGE:
            continue  # EDGE entities are relationship types, never normalize
        if entity.entity_kind != target_kind:
            entity.entity_kind = target_kind

    # PK type normalization (SIMPLE↔PARTITION) is now handled explicitly by
    # CAST_CONSTRAINT / CAST_PS CONSTRAINT in each cross-model SMEL script.

    # Normalize Embedded cardinality for cross-model Document targets
    # MongoDB JSON Schema uses "required" array, so RE always produces required cardinality
    # (ONE_TO_ONE for objects, ONE_TO_MANY for arrays). Normalize to match.
    # Skip for D->D: source MongoDB cardinalities are already correct.
    if target_type == SOURCE_TYPE_DOCUMENT and source_type != SOURCE_TYPE_DOCUMENT:
        for entity in db.entity_types.values():
            for rel in entity.relationships:
                if isinstance(rel, Embedded):
                    if rel.cardinality == Cardinality.ZERO_TO_ONE:
                        rel.cardinality = Cardinality.ONE_TO_ONE
                    elif rel.cardinality == Cardinality.ZERO_TO_MANY:
                        rel.cardinality = Cardinality.ONE_TO_MANY


def run_migration(direction: str) -> Dict[str, Any]:
    """
    Run a complete migration and return results.

    Args:
        direction: "r2d" for Relational->Document, "d2r" for Document->Relational,
                   "r2r" for Relational->Relational, "d2d" for Document->Document
                   (also accepts "1"/"2" for backwards compatibility)

    Returns:
        Dictionary with migration results including source, meta_v1, result, changes, etc.
    """
    # Get migration configuration from config.py
    if direction not in MIGRATION_CONFIGS:
        return {"error": f"Unknown direction: {direction}. Available: {list(MIGRATION_CONFIGS.keys())}"}

    config = MIGRATION_CONFIGS[direction]
    source_file = config["source_file"]
    smel_file = config["smel_file"]
    source_type = config["source_type"]
    target_type = config["target_type"]

    # Determine adapters based on source/target types (using adapter registry)
    source_adapter = ADAPTER_REGISTRY.get(source_type)
    target_adapter = ADAPTER_REGISTRY.get(target_type)
    if not source_adapter:
        return {"error": f"No adapter for source type: {source_type}. Available: {list(ADAPTER_REGISTRY.keys())}"}
    if not target_adapter:
        return {"error": f"No adapter for target type: {target_type}. Available: {list(ADAPTER_REGISTRY.keys())}"}

    for f in [source_file, smel_file]:
        if not f.exists():
            return {"error": f"File not found: {f}"}

    raw_source = source_file.read_text(encoding='utf-8')
    smel_content = smel_file.read_text(encoding='utf-8')

    # Step 1: Import source -> Meta V1
    source_db = source_adapter.load_from_file(str(source_file), "source")
    meta_v1_db = copy.deepcopy(source_db)

    # Step 2: Parse and execute SMEL -> Meta V2
    from parser_factory import parse_smel_auto
    context, operations, errors = parse_smel_auto(str(smel_file))
    if errors:
        return {"error": f"SMEL parse errors: {errors}"}

    # Execute operations and track step-by-step changes
    transformer = SchemaTransformer(source_db)
    operations_detail = []
    current_entity_count = len(source_db.entity_types)
    success_count = 0
    skipped_count = 0

    # Use original operation order from SMEL file
    # For new syntax (ADD_PS KEY, ADD_PS CONSTRAINT after FLATTEN/UNWIND),
    # the order in the file is intentional and should be preserved
    for i, op in enumerate(operations):
        prev_count = len(transformer.database.entity_types)
        prev_snapshot = db_to_dict(transformer.database)

        handler = transformer._handlers.get(op.op_type)
        if handler:
            try:
                success = handler(op.params)
                if success:
                    status = "success"
                    success_count += 1
                else:
                    status = "skipped"
                    skipped_count += 1
            except Exception as e:
                print(f"[ERROR] Step {i+1}: Operation {op.op_type.name} failed: {e}")
                status = "error"
                skipped_count += 1
        else:
            print(f"[NOTICE] Unknown operation type: {op.op_type.name}")
            status = "skipped"
            skipped_count += 1

        new_count = len(transformer.database.entity_types)
        after_snapshot = db_to_dict(transformer.database)

        # Calculate changes for this operation
        changes_detail = _calculate_changes(prev_snapshot, after_snapshot, op)

        operations_detail.append({
            "step": i + 1,
            "type": op.op_type.name,
            "original_keyword": op.original_keyword if op.original_keyword else op.op_type.name,
            "params": op.params,
            "entity_count_before": prev_count,
            "entity_count_after": new_count,
            "changes": changes_detail,
            "status": status
        })

    result_db = transformer.database
    # Set target database type dynamically (using module-level constant)
    if target_type not in _DB_TYPE_MAP:
        raise ValueError(f"Unknown target_type: {target_type}")
    result_db.db_type = _DB_TYPE_MAP[target_type]

    # Normalize entity_kind for target database type (skip explicitly cast entities)
    _normalize_entity_kinds(result_db, target_type, source_type, transformer._explicitly_cast_entities)

    # Step 3: Export Meta V2 -> Target DDL (polymorphic via adapter registry)
    exported_target = target_adapter.export(result_db)

    result_dict = {
        "source_type": source_type,
        "target_type": target_type,
        "raw_source": raw_source,
        "exported_target": exported_target,
        "smel_content": smel_content,
        "smel_file": smel_file.name,
        "operations_detail": operations_detail,
        "original_source": parse_original_source(raw_source, source_type),  # Original nested structure (before reverse eng)
        "target_nested": parse_original_source(exported_target, target_type),  # Target nested structure (for card view)
        "source": db_to_source_dict(meta_v1_db, source_type),  # Original format (SERIAL, VARCHAR, bsonType)
        "meta_v1": db_to_dict(meta_v1_db),                     # Unified Meta format (integer, string)
        "result": db_to_dict(result_db),                       # Unified Meta format (integer, string)
        "target_with_db_types": db_to_source_dict(result_db, target_type),  # Target format (SERIAL, VARCHAR, bsonType)
        "changes": transformer.changes,
        "key_registry": transformer.key_registry,
        "operations_count": len(operations),
        "stats": {
            "source_count": len(meta_v1_db.entity_types),
            "result_count": len(result_db.entity_types)
        },
        "execution_stats": {
            "total": len(operations),
            "success": success_count,
            "skipped": skipped_count
        },
        "smel_syntax": SMEL_SYNTAX,
    }

    # Two-layer validation for cross-model Northwind migrations
    try:
        from validate_meta import validate_meta
        from validate_export import validate_export
        result_dict["validation_meta"] = validate_meta(result_dict, target_type, direction)
        result_dict["validation_export"] = validate_export(result_dict, target_type, direction)
    except Exception as e:
        result_dict["validation_meta"] = {"passed": None, "summary": f"Error: {e}", "details": {}}
        result_dict["validation_export"] = {"passed": None, "summary": f"Error: {e}", "details": {}}

    return result_dict
