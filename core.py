"""
SMEL Core - Shared logic for Schema Migration & Evolution Language

This module contains the core components shared by main.py (CLI) and web_server.py (Web UI):
- SchemaTransformer: Execute transformation operations
- db_to_dict(): Convert Database to JSON-serializable dict

Note: For parsing SMEL files, use parser_factory.parse_smel_auto() which supports
both SMEL_Specific (.smel) and SMEL_Pauschalisiert (.smel_ps) grammars.
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
    RelationshipType, TypeMappings
)
from Schema.adapters import ADAPTER_REGISTRY
from config import (
    MIGRATION_CONFIGS,
    SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT,
    SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR,
)
from smel_listeners import MigrationContext, Operation, OpType

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
        self._init_source_keys()

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

    def _handle_nest(self, params: Dict) -> None:
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

        source_entity = self.database.get_entity_type(source_name)
        target_entity = self.database.get_entity_type(target_name)
        if not source_entity or not target_entity:
            missing = source_name if not source_entity else target_name
            print(f"[WARNING] NEST skipped: entity '{missing}' not found")
            return

        # Determine cardinality from existing FK reference (if target has a reference to source)
        cardinality = Cardinality.ONE_TO_ONE
        for rel in target_entity.relationships:
            if isinstance(rel, Reference) and rel.get_target_entity_name() == source_name:
                cardinality = rel.cardinality
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
                target_entity.remove_relationship(rel.ref_name)
                target_entity.remove_attribute(rel.ref_name)
                fk_removed = True

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

    def _handle_flatten(self, params: Dict) -> None:
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
        parts = source_path.split(".")
        if len(parts) < 2:
            return

        nested_name = parts[-1]
        parent_path = ".".join(parts[:-1])

        parent_entity = self.database.get_entity_type(parent_path)
        if not parent_entity:
            print(f"[WARNING] FLATTEN skipped: entity '{parent_path}' not found")
            return

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
            print(f"[WARNING] FLATTEN skipped: embedded '{full_embedded_path}' not found")
            return

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

    def _handle_unflatten(self, params: Dict) -> None:
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

        entity = self.database.get_entity_type(entity_name)
        if not entity:
            print(f"[WARNING] UNFLATTEN skipped: entity '{entity_name}' not found")
            return

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

    def _handle_unnest(self, params: Dict) -> None:
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
            return

        # Parse source path: person.address -> parent=person, nested=address
        path_parts = source_path.split(".")
        if len(path_parts) < 2:
            return

        nested_name = path_parts[-1]
        parent_path = ".".join(path_parts[:-1])

        # Get parent entity
        parent_entity = self.database.get_entity_type(parent_path)
        if not parent_entity:
            print(f"[WARNING] UNNEST skipped: entity '{parent_path}' not found")
            return

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

    def _handle_unwind(self, params: Dict) -> None:
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
            parts = source_path.split(".")
            if len(parts) >= 2:
                entity_name = ".".join(parts[:-1])
                attr_name = parts[-1]
                entity = self.database.get_entity_type(entity_name)
                if entity:
                    attr = entity.get_attribute(attr_name)
                    if attr and hasattr(attr.data_type, 'element_type'):
                        # Convert ListDataType to its element type
                        attr.data_type = attr.data_type.element_type
                        self.changes.append(f"UNWIND_INPLACE:{entity_name}.{attr_name}")
            return

        # Mode 1: Create new table
        target_name = params.get("target")
        if not target_name:
            return

        # Parse source path: person.tags[] -> parent=person, array_name=tags
        parts = source_path.replace("[]", "").split(".")
        if len(parts) < 2:
            return

        array_name = parts[-1]
        parent_path = ".".join(parts[:-1])

        parent_entity = self.database.get_entity_type(parent_path)
        if not parent_entity:
            print(f"[WARNING] UNWIND skipped: entity '{parent_path}' not found")
            return

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

    def _handle_wind(self, params: Dict) -> None:
        """
        WIND: Convert scalar attribute back to array (reverse of UNWIND).

        Syntax: WIND person_tag.tags
          Before: person_tag { person_id, tags } (multiple rows, scalar)
          After:  person_tag { person_id, tags[] } (single row, array)
          Reverse of: UNWIND person_tag.tags

        Note: Cross-entity movement is handled by MERGE, not WIND.
        """
        source_path = params.get("source", "")
        parts = source_path.split(".")
        if len(parts) >= 2:
            entity_name = ".".join(parts[:-1])
            attr_name = parts[-1]
            entity = self.database.get_entity_type(entity_name)
            if entity:
                attr = entity.get_attribute(attr_name)
                if attr:
                    # Convert scalar type to ListDataType (reverse of UNWIND which does List -> scalar)
                    # Skip if already a ListDataType to avoid double-wrapping
                    if not isinstance(attr.data_type, ListDataType):
                        attr.data_type = ListDataType(element_type=attr.data_type)
                    self.changes.append(f"WIND:{entity_name}.{attr_name}")

    def _handle_delete_constraint(self, params: Dict) -> None:
        parts = params["reference"].split(".")
        if len(parts) < 2:
            return
        entity_name = ".".join(parts[:-1])
        ref_name = parts[-1]
        entity = self.database.get_entity_type(entity_name)
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

    def _handle_delete_embedded(self, params: Dict) -> None:
        parts = params["embedded"].split(".")
        if len(parts) < 2:
            return
        parent_name = ".".join(parts[:-1])
        embedded_name = parts[-1].replace("[]", "")
        parent_entity = self.database.get_entity_type(parent_name)
        if not parent_entity:
            print(f"[WARNING] DELETE_EMBEDDED skipped: entity '{parent_name}' not found")
            return
        # Find the full entity path from the Embedded relationship
        full_path = f"{parent_name}.{embedded_name}"
        for rel in parent_entity.get_embedded():
            if rel.aggr_name == embedded_name:
                full_path = rel.aggregates
                break
        parent_entity.remove_relationship(embedded_name)
        self.database.remove_entity_type(full_path)
        self.changes.append(f"DELETE_EMBEDDED:{parent_name}.{embedded_name}")

    def _handle_add_constraint(self, params: Dict) -> None:
        """ADD_CONSTRAINT entity.field REFERENCES target_table(target_column) WITH CARDINALITY"""
        field_name = params.get("field_name")
        target_table = params.get("target_table")
        target_column = params.get("target_column")
        entity_name = params.get("entity")

        if not entity_name:
            # Use last created entity if no entity specified
            entity_name = self._last_created_entity

        if not entity_name or not field_name or not target_table:
            return

        entity = self.database.get_entity_type(entity_name)
        if not entity:
            return

        # Get target entity's primary key type for FK attribute
        target_entity = self.database.get_entity_type(target_table)
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

        # Also create ForeignKeyConstraint for consistency with ADD_KEY FOREIGN
        fk_attr = entity.get_attribute(field_name)
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

    def _handle_add_attribute(self, params: Dict) -> None:
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

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            print(f"[WARNING] ADD_ATTRIBUTE skipped: entity '{entity_name}' not found")
            return
        entity.add_attribute(Attribute(name, data_type, False, is_optional))
        self.changes.append(f"ADD_ATTR:{entity_name}.{name}")

    def _handle_add_embedded(self, params: Dict) -> None:
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
            self.changes.append(f"ADD_EMBEDDED:{entity_name}.{name}")

    def _handle_add_entity(self, params: Dict) -> None:
        """ADD ENTITY Product WITH ATTRIBUTES (id, name)"""
        name = params["name"]
        clauses = params.get("clauses", [])

        new_entity = EntityType(object_name=[name])

        # Process clauses for attributes and key
        key_name = None
        for c in clauses:
            if c["type"] == "ATTRIBUTES":
                for attr_name in c["attributes"]:
                    new_entity.add_attribute(Attribute(attr_name, PrimitiveDataType(PrimitiveType.STRING), False, True))
            elif c["type"] == "KEY":
                key_name = c["key_name"]

        # Set primary key if specified
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

    def _handle_delete_attribute(self, params: Dict) -> None:
        """DELETE ATTRIBUTE Customer.email"""
        target = params["target"]
        parts = target.split(".")
        if len(parts) >= 2:
            entity_name = ".".join(parts[:-1])
            attr_name = parts[-1]
            entity = self.database.get_entity_type(entity_name)
            if entity:
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

    def _handle_delete_entity(self, params: Dict) -> None:
        """DELETE ENTITY Customer"""
        name = params["name"]
        # Collect deleted entity's attribute meta_ids for FK cleanup
        deleted_entity = self.database.get_entity_type(name)
        if not deleted_entity:
            print(f"[WARNING] DELETE_ENTITY skipped: entity '{name}' not found")
            return
        deleted_attr_ids = set()
        if deleted_entity:
            for attr in deleted_entity.attributes:
                deleted_attr_ids.add(attr.meta_id)
            # Also collect UniqueProperty meta_ids (for points_to_unique_property_id)
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
            if deleted_entity and deleted_up_ids:
                other_entity.constraints = [
                    c for c in other_entity.constraints
                    if not (isinstance(c, ForeignKeyConstraint) and
                            any(fkp.points_to_unique_property_id in deleted_up_ids
                                for fkp in c.foreign_key_properties))
                ]
        # Clean up RelationshipTypes that reference the deleted entity
        rts_to_remove = [
            rt_name for rt_name, rt in self.database.relationship_types.items()
            if rt.source_entity == name or rt.target_entity == name
        ]
        for rt_name in rts_to_remove:
            self.database.remove_relationship_type(rt_name)
        self.changes.append(f"DELETE_ENTITY:{name}")

    def _handle_delete_key(self, params: Dict) -> None:
        """DELETE PRIMARY/FOREIGN/UNIQUE KEY - destructive removal"""
        self._remove_key_constraint(params, operation="DELETE")

    def _handle_delete_label(self, params: Dict) -> None:
        """DELETE LABEL Employee FROM Person (graph database)"""
        label = params.get("label")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return

        if label in entity.labels:
            entity.labels.remove(label)
        self.changes.append(f"DELETE_LABEL:{entity_name}.{label}")

    def _handle_add_label(self, params: Dict) -> None:
        """ADD LABEL Employee TO Person (graph database)"""
        label = params.get("label")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity or not label:
            return

        if label not in entity.labels:
            entity.labels.append(label)
        self.changes.append(f"ADD_LABEL:{entity_name}.{label}")

    def _handle_add_key(self, params: Dict) -> None:
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
            entity_name = self._last_created_entity

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not key_columns:
            return

        # If entity doesn't exist yet, create a minimal one or defer
        if not entity:
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
                    # Append new key columns to existing composite PK
                    existing_pk.unique_properties.extend(constraint.unique_properties)
                    key_names_str = ", ".join(key_columns)
                    self.changes.append(f"ADD_KEY:{entity_name}.({key_names_str})")
                    return
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

    def _handle_remove_key(self, params: Dict) -> None:
        """REMOVE PRIMARY/FOREIGN/UNIQUE KEY - non-destructive constraint removal"""
        self._remove_key_constraint(params, operation="REMOVE")

    def _remove_key_constraint(self, params: Dict, operation: str = "REMOVE") -> None:
        """Helper method for both DELETE_KEY and REMOVE_KEY operations"""
        entity_name = params.get("entity")
        key_columns = params.get("key_columns", [])  # List of column names
        key_type_str = self.KEY_TYPE_MAP.get(params["key_type"], "primary")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity or not key_columns:
            return

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
                    return

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
                        return

            elif isinstance(key_type_str, PKTypeEnum) and isinstance(constraint, UniqueConstraint):
                # Cassandra PARTITION/CLUSTERING keys: remove matching properties
                for up in list(constraint.unique_properties):
                    if up.primary_key_type == key_type_str:
                        up_attr = entity.get_attribute_by_id(up.property_id)
                        if up_attr and up_attr.attr_name in key_columns_set:
                            constraint.unique_properties.remove(up)
                            up_attr.is_key = False
                            key_names_str = ", ".join(key_columns)
                            self.changes.append(f"{operation}_KEY:{entity_name}.({key_names_str})")
                            if not constraint.unique_properties:
                                entity.constraints.remove(constraint)
                            return

    def _handle_remove_label(self, params: Dict) -> None:
        """REMOVE LABEL Manager FROM Person - non-destructive (graph database)"""
        label = params.get("label")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return

        if label in entity.labels:
            entity.labels.remove(label)
        self.changes.append(f"REMOVE_LABEL:{entity_name}.{label}")

    def _handle_rename(self, params: Dict) -> None:
        """RENAME: Rename an attribute within an entity."""
        old_name = params["old_name"]
        new_name = params["new_name"]
        entity_name = params.get("entity")

        if not entity_name:
            print(f"[WARNING] RENAME skipped: no entity specified for '{old_name}'")
            return

        entity = self.database.get_entity_type(entity_name)
        if not entity:
            print(f"[WARNING] RENAME skipped: entity '{entity_name}' not found")
            return

        attr = entity.get_attribute(old_name)
        if attr:
            attr.attr_name = new_name
            # Update Reference.ref_name if this attribute is a FK
            for rel in entity.relationships:
                if isinstance(rel, Reference) and rel.ref_name == old_name:
                    rel.ref_name = new_name
                    break
            self.changes.append(f"RENAME:{entity_name}.{old_name}->{new_name}")

    def _handle_rename_entity(self, params: Dict) -> None:
        """RENAME ENTITY: Rename an entity."""
        old_name = params["old_name"]
        new_name = params["new_name"]

        entity = self.database.get_entity_type(old_name)
        if not entity:
            print(f"[WARNING] RENAME_ENTITY skipped: entity '{old_name}' not found")
            return
        # Collision check: prevent overwriting an existing entity
        if self.database.get_entity_type(new_name):
            print(f"[WARNING] RENAME_ENTITY skipped: target '{new_name}' already exists")
            return

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
        # Update RelationshipType references in database.relationship_types
        for rt in self.database.relationship_types.values():
            if rt.source_entity == old_name:
                rt.source_entity = new_name
            if rt.target_entity == old_name:
                rt.target_entity = new_name
        self.changes.append(f"RENAME_ENTITY:{old_name}->{new_name}")

    def _handle_copy(self, params: Dict) -> None:
        """
        COPY: Copy attribute from source to target.

        Supports nested paths for embedded objects:
        - COPY person.address.street TO address.street
          Source: entity="person.address", attr="street"
          Target: entity="address", attr="street"
        """
        source_path = params["source"]
        target_path = params["target"]

        source_parts = source_path.split(".")
        target_parts = target_path.split(".")

        if len(source_parts) >= 2 and len(target_parts) >= 2:
            # Copy attribute: last part is attribute name, rest is entity path
            src_entity_path = ".".join(source_parts[:-1])
            src_attr_name = source_parts[-1]
            tgt_entity_path = ".".join(target_parts[:-1])
            tgt_attr_name = target_parts[-1]

            src_entity = self.database.get_entity_type(src_entity_path)
            tgt_entity = self.database.get_entity_type(tgt_entity_path)

            if src_entity and tgt_entity:
                src_attr = src_entity.get_attribute(src_attr_name)
                if src_attr:
                    new_attr = Attribute(tgt_attr_name, src_attr.data_type, False, src_attr.is_optional)
                    tgt_entity.add_attribute(new_attr)
                    self.changes.append(f"COPY:{source_path}->{target_path}")
        elif len(source_parts) == 1 and len(target_parts) == 1:
            # Copy entity
            src_entity = self.database.get_entity_type(source_parts[0])
            if src_entity:
                new_entity = copy.deepcopy(src_entity)
                # Update object_name with new target name
                new_entity.object_name = [target_parts[0]]
                self.database.add_entity_type(new_entity)
                self.changes.append(f"COPY:{source_path}->{target_path}")

    def _handle_copy_entity(self, params: Dict) -> None:
        """COPY_ENTITY: Duplicate an entire entity with all its structure.

        Reference: PRISM "COPY TABLE R INTO S", CoDEL "Addtable(S, R)"
        Deep copies the source entity (attributes, keys, constraints, relationships)
        and adds it as a new entity with the target name.

        Example: COPY_ENTITY person AS employee
        """
        source_name = params["source"]
        target_name = params["target"]

        src_entity = self.database.get_entity_type(source_name)
        if not src_entity:
            print(f"[WARNING] COPY_ENTITY skipped: entity '{source_name}' not found")
            return

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
        self.database.add_entity_type(new_entity)
        self.changes.append(f"COPY_ENTITY:{source_name}->{target_name}")

    def _handle_move(self, params: Dict) -> None:
        """MOVE: Move attribute from one entity to another."""
        source_path = params["source"]
        target_path = params["target"]

        source_parts = source_path.split(".")
        target_parts = target_path.split(".")

        if len(source_parts) >= 2 and len(target_parts) >= 2:
            # Move attribute - support nested paths like person.address.street
            src_entity_name = ".".join(source_parts[:-1])
            src_attr_name = source_parts[-1]
            tgt_entity_name = ".".join(target_parts[:-1])
            tgt_attr_name = target_parts[-1]
            src_entity = self.database.get_entity_type(src_entity_name)
            tgt_entity = self.database.get_entity_type(tgt_entity_name)
            if src_entity and tgt_entity:
                src_attr = src_entity.get_attribute(src_attr_name)
                if src_attr:
                    # Add to target
                    new_attr = Attribute(tgt_attr_name, src_attr.data_type, False, src_attr.is_optional)
                    tgt_entity.add_attribute(new_attr)
                    # Remove from source
                    src_entity.remove_attribute(src_attr_name)
                    self.changes.append(f"MOVE:{source_path}->{target_path}")

    def _handle_merge(self, params: Dict) -> None:
        """MERGE: Merge two entities into one."""
        source1_name = params["source1"]
        source2_name = params["source2"]
        target_name = params["target"]

        source1 = self.database.get_entity_type(source1_name)
        source2 = self.database.get_entity_type(source2_name)
        if not source1 or not source2:
            missing = source1_name if not source1 else source2_name
            print(f"[WARNING] MERGE skipped: entity '{missing}' not found")
            return

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
                new_attr = Attribute(attr.attr_name, attr.data_type, False, attr.is_optional)
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
            # Update RelationshipTypes
            for rt in self.database.relationship_types.values():
                if rt.source_entity == old_name:
                    rt.source_entity = target_name
                if rt.target_entity == old_name:
                    rt.target_entity = target_name

        self.changes.append(f"MERGE:{source1_name},{source2_name}->{target_name}")

    def _handle_split(self, params: Dict) -> None:
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
            return

        pk = source.get_primary_key()
        created_entities = []

        # Create each part entity
        for i, part in enumerate(parts):
            part_name = part["name"]
            part_fields = part.get("fields", [])

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

        # Remove source if different from all targets
        if source_name not in [p["name"] for p in parts]:
            self.database.remove_entity_type(source_name)

        parts_str = ",".join(created_entities)
        self.changes.append(f"SPLIT:{source_name}->{parts_str}")

    def _handle_cast(self, params: Dict) -> None:
        """CAST: Change attribute data type."""
        target = params["target"]
        new_type_str = params.get("data_type", params.get("type", "STRING")).upper()

        parts = target.split(".")
        if len(parts) < 2:
            return

        entity_name = ".".join(parts[:-1])
        attr_name = parts[-1]
        entity = self.database.get_entity_type(entity_name)
        if not entity:
            print(f"[WARNING] CAST skipped: entity '{entity_name}' not found")
            return

        attr = entity.get_attribute(attr_name)
        if not attr:
            print(f"[WARNING] CAST skipped: attribute '{attr_name}' not found in '{entity_name}'")
            return

        new_type = self.TYPE_STR_MAP.get(new_type_str, PrimitiveType.STRING)
        attr.data_type = PrimitiveDataType(new_type)
        self.changes.append(f"CAST:{target}->{new_type_str}")

    def _handle_cast_constraint(self, params: Dict) -> None:
        """CAST_CONSTRAINT: Change the type of a constraint.

        Reference: Orion "Cast Reference" - change the type of a constraint.
        Example: CAST_CONSTRAINT person.email TO UNIQUE KEY
        Example: CAST_CONSTRAINT person.city TO PARTITION KEY
        """
        target = params["target"]
        new_type = params["constraint_type"]  # PRIMARY_KEY, UNIQUE_KEY, PARTITION_KEY, CLUSTERING_KEY

        parts = target.split(".")
        if len(parts) < 2:
            return

        entity_name = ".".join(parts[:-1])
        attr_name = parts[-1]
        entity = self.database.get_entity_type(entity_name)
        if not entity:
            return

        # Find the attribute
        attr = next((a for a in entity.attributes if a.attr_name == attr_name), None)
        if not attr:
            return

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
                        self.changes.append(f"CAST_CONSTRAINT:{target}->{new_type}")
                        return

    def _handle_recard(self, params: Dict) -> None:
        """RECARD: Change the multiplicity/cardinality of a reference.

        Reference: Orion "Mult Reference" - change the multiplicity of a reference.
        Example: RECARD person.address_id TO ONE_TO_MANY
        """
        target = params["target"]
        new_cardinality_str = params["cardinality"]

        parts = target.split(".")
        if len(parts) < 2:
            return

        entity_name = ".".join(parts[:-1])
        ref_name = parts[-1]
        entity = self.database.get_entity_type(entity_name)
        if not entity:
            return

        new_cardinality = self.CARDINALITY_MAP.get(new_cardinality_str, None)
        if not new_cardinality:
            return

        # Find the reference relationship and update its cardinality
        for rel in entity.relationships:
            if isinstance(rel, Reference) and rel.ref_name == ref_name:
                rel.cardinality = new_cardinality
                self.changes.append(f"RECARD:{target}->{new_cardinality_str}")
                return
            elif isinstance(rel, Edge) and rel.rel_type_name == ref_name:
                rel.cardinality = new_cardinality
                self.changes.append(f"RECARD:{target}->{new_cardinality_str}")
                return

    def _handle_transform(self, params: Dict) -> None:
        """TRANSFORM: Convert between entity (node) and relationship type (edge).

        Based on Hausler et al. - nodeToRel / relToNode graph evolution operations.
        At meta-schema level: moves between database.entity_types and database.relationship_types.

        TO RELATIONSHIP: EntityType (VERTEX) -> RelationshipType
          - Removes entity from entity_types
          - Creates RelationshipType with preserved attributes
          - Adds Edge to source entity's relationships

        TO ENTITY: RelationshipType -> EntityType (VERTEX)
          - Removes relationship type from relationship_types
          - Removes Edge from source entity's relationships
          - Creates EntityType with VERTEX kind and preserved attributes
        """
        name = params["name"]
        target_type = params["target_type"]

        if target_type == "RELATIONSHIP":
            source_entity_name = params["source_entity"]
            target_entity_name = params["target_entity"]

            entity = self.database.get_entity_type(name)
            if not entity:
                print(f"[WARNING] TRANSFORM skipped: entity '{name}' not found")
                return

            # Create RelationshipType with preserved attributes
            rel_type = RelationshipType(
                rel_name=name,
                source_entity=source_entity_name,
                target_entity=target_entity_name,
                attributes=list(entity.attributes),
                cardinality=Cardinality.ZERO_TO_MANY
            )
            self.database.add_relationship_type(rel_type)

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
                        cardinality=Cardinality.ZERO_TO_MANY
                    )
                    source_ent.add_relationship(edge)

            # Remove original entity
            self.database.remove_entity_type(name)
            self.changes.append(f"TRANSFORM:{name}->RELATIONSHIP({source_entity_name},{target_entity_name})")

        elif target_type == "ENTITY":
            rel_type = self.database.get_relationship_type(name)
            if not rel_type:
                print(f"[WARNING] TRANSFORM skipped: relationship type '{name}' not found")
                return

            # Remove Edge from source entity's relationships
            if rel_type.source_entity:
                source_ent = self.database.get_entity_type(rel_type.source_entity)
                if source_ent:
                    source_ent.remove_relationship(name)

            # Create EntityType with VERTEX kind and preserved attributes
            new_entity = EntityType(
                object_name=[name],
                entity_kind=EntityKind.VERTEX,
                attributes=list(rel_type.attributes)
            )
            self.database.add_entity_type(new_entity)

            # Remove original relationship type
            self.database.remove_relationship_type(name)
            self.changes.append(f"TRANSFORM:{name}->ENTITY")

    # =========================================================================
    # RELTYPE operations - DB.Rty management (Graph database)
    # =========================================================================

    def _handle_add_reltype(self, params: Dict) -> None:
        """ADD_RELTYPE: Add new relationship type to DB.Rty.

        Example: ADD_RELTYPE works_at BETWEEN person AND company

        Creates a RelationshipType and adds an Edge to the source entity.
        """
        name = params.get("name")
        source_entity_name = params.get("source_entity")
        target_entity_name = params.get("target_entity")

        if not name or not source_entity_name or not target_entity_name:
            return

        # Validate that source and target entities exist (prevent orphaned RelationshipType)
        source_ent = self.database.get_entity_type(source_entity_name)
        if not source_ent:
            print(f"[WARNING] ADD_RELTYPE skipped: source entity '{source_entity_name}' not found")
            return
        target_ent = self.database.get_entity_type(target_entity_name)
        if not target_ent:
            print(f"[WARNING] ADD_RELTYPE skipped: target entity '{target_entity_name}' not found")
            return

        # Create RelationshipType
        rel_type = RelationshipType(
            rel_name=name,
            source_entity=source_entity_name,
            target_entity=target_entity_name,
            attributes=[],
            cardinality=Cardinality.ZERO_TO_MANY
        )
        self.database.add_relationship_type(rel_type)

        # Add Edge to source entity's relationships
        if source_ent:
            edge = Edge(
                rel_type_name=name,
                source_entity=source_entity_name,
                target_entity=target_entity_name,
                cardinality=Cardinality.ZERO_TO_MANY
            )
            source_ent.add_relationship(edge)

        self.changes.append(f"ADD_RELTYPE:{name}({source_entity_name}->{target_entity_name})")

    def _handle_delete_reltype(self, params: Dict) -> None:
        """DELETE_RELTYPE: Remove relationship type from DB.Rty.

        Example: DELETE_RELTYPE works_at

        Removes the RelationshipType and cleans up Edge from source entity.
        """
        name = params.get("name")
        if not name:
            return

        rel_type = self.database.get_relationship_type(name)
        if not rel_type:
            print(f"[WARNING] DELETE_RELTYPE skipped: relationship type '{name}' not found")
            return

        # Remove Edge from source entity's relationships
        if rel_type.source_entity:
            source_ent = self.database.get_entity_type(rel_type.source_entity)
            if source_ent:
                source_ent.remove_relationship(name)

        # Remove relationship type from database
        self.database.remove_relationship_type(name)
        self.changes.append(f"DELETE_RELTYPE:{name}")

    def _handle_rename_reltype(self, params: Dict) -> None:
        """RENAME_RELTYPE: Rename a relationship type in DB.Rty.

        Example: RENAME_RELTYPE works_at TO employed_at

        Updates the RelationshipType name and Edge references.
        """
        old_name = params.get("old_name")
        new_name = params.get("new_name")

        if not old_name or not new_name:
            return

        rel_type = self.database.get_relationship_type(old_name)
        if not rel_type:
            print(f"[WARNING] RENAME_RELTYPE skipped: relationship type '{old_name}' not found")
            return

        # Remove old and re-add with new name
        self.database.remove_relationship_type(old_name)
        rel_type.rel_name = new_name
        self.database.add_relationship_type(rel_type)

        # Update Edge references in source entity
        if rel_type.source_entity:
            source_ent = self.database.get_entity_type(rel_type.source_entity)
            if source_ent:
                for rel in source_ent.relationships:
                    if isinstance(rel, Edge) and rel.rel_type_name == old_name:
                        rel.rel_type_name = new_name

        self.changes.append(f"RENAME_RELTYPE:{old_name}->{new_name}")


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
                "cardinality": r.cardinality.value if hasattr(r, 'cardinality') else '1..1'
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
    """Serialize relationship_types from Database."""
    result = {}
    for name, rt in db.relationship_types.items():
        result[name] = {
            "rel_name": rt.rel_name,
            "source_entity": rt.source_entity,
            "target_entity": rt.target_entity,
            "attributes": [
                {"name": a.attr_name, "type": _get_type_str(a.data_type)}
                for a in rt.attributes
            ],
            "cardinality": rt.cardinality.value
        }
    return result


def db_to_dict(db: Database) -> Dict[str, Any]:
    """
    Convert Database to a JSON-serializable dictionary (Unified Meta Schema format).

    Returns dict with "entities" and optionally "relationship_types" keys.
    """
    entities = {}
    for name, entity in db.entity_types.items():
        entities[name] = _serialize_entity(name, entity)

    result = entities  # Keep flat entity dict for backward compatibility with web UI

    # Attach relationship_types as a special key (won't conflict with entity names)
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
        # Build entity dict with source-specific types
        entity_dict = _serialize_entity(name, entity)
        # Override attribute type with source-specific format, preserve key_type etc.
        for i, a in enumerate(entity.attributes):
            if i < len(entity_dict["attributes"]):
                entity_dict["attributes"][i]["type"] = _get_source_type_str(a, source_type)
        entities[name] = entity_dict

    # Attach relationship_types
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
                        # Array - check item type
                        items = prop_def.get("items", {})
                        item_type = items.get("bsonType", "string")
                        result.append({
                            "name": prop_name,
                            "type": f"array<{item_type}>",
                            "description": prop_def.get("description", "")
                        })
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

        # Check for constraint changes (ADD_KEY, REMOVE_KEY, CAST_CONSTRAINT)
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


def _cleanup_flattened_entities(db: Database, changes: List[str]) -> None:
    """
    Clean up embedded entities that have been flattened/split to standalone tables.

    After FLATTEN/SPLIT operations, the original embedded entities (e.g., person.address)
    and their embedded relationships should be removed from the result schema.
    This ensures the ER diagram shows only the new normalized structure.
    """
    # Collect names of flattened/split targets
    flattened_targets = set()
    for change in changes:
        if change.startswith("FLATTEN:") or change.startswith("UNWIND:") or change.startswith("SPLIT:"):
            # Handle both formats: "SPLIT:source->target" and "FLATTEN:target"
            parts = change.split(":")
            if len(parts) >= 2:
                target_part = parts[1]
                if "->" in target_part:
                    # Format: source->target or source->target1,target2
                    targets = target_part.split("->")[1]
                    for t in targets.split(","):
                        flattened_targets.add(t.strip())
                else:
                    flattened_targets.add(target_part)

    if not flattened_targets:
        return

    # Find embedded entities to remove (entities with "." in name are embedded paths)
    # Only remove if the short name matches a flattened target
    entities_to_remove = []
    for entity_name in list(db.entity_types.keys()):
        if "." in entity_name:
            short_name = entity_name.split(".")[-1]
            if short_name in flattened_targets:
                entities_to_remove.append(entity_name)

    for entity_name in entities_to_remove:
        db.remove_entity_type(entity_name)

    # Remove embedded relationships that reference flattened targets
    # Extract short names from flattened_targets for matching embedded aggr_name
    flattened_short_names = set()
    for t in flattened_targets:
        flattened_short_names.add(t.split(".")[-1])

    for entity in db.entity_types.values():
        embedded_to_remove = []
        for rel in entity.relationships:
            if isinstance(rel, Embedded) and rel.aggr_name in flattened_short_names:
                embedded_to_remove.append(rel.aggr_name)

        for rel_name in embedded_to_remove:
            entity.remove_relationship(rel_name)


def _normalize_entity_kinds(db: Database, target_type: str) -> None:
    """Normalize entity_kind for target database type.

    For cross-model migrations (e.g., R->G, G->R, D->C), entities may have
    entity_kind from the source DB type. This function converts ALL entities
    to match the target DB type so the target adapter can export them correctly.
    """
    target_kind = _ENTITY_KIND_DEFAULT.get(target_type, EntityKind.TABLE)
    for entity in db.entity_types.values():
        if entity.entity_kind != target_kind:
            entity.entity_kind = target_kind


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
        prev_changes_len = len(transformer.changes)

        handler = getattr(transformer, f"_handle_{op.op_type.value}", None)
        if handler:
            try:
                handler(op.params)
            except Exception as e:
                print(f"[ERROR] Step {i+1}: Operation {op.op_type.name} failed: {e}")
        else:
            print(f"[WARNING] Unknown operation type: {op.op_type.name}")

        new_count = len(transformer.database.entity_types)
        after_snapshot = db_to_dict(transformer.database)
        new_changes_len = len(transformer.changes)

        # Calculate changes for this operation
        changes_detail = _calculate_changes(prev_snapshot, after_snapshot, op)

        # Determine operation status: check if transformer.changes was updated
        # If no new change was recorded, the operation was skipped (e.g., entity not found)
        if new_changes_len > prev_changes_len:
            status = "success"
            success_count += 1
        else:
            status = "skipped"
            skipped_count += 1

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

    # Cleanup: Remove embedded entities and relationships that have been flattened
    # This ensures the ER diagram shows only the normalized structure
    _cleanup_flattened_entities(result_db, transformer.changes)

    # Normalize entity_kind for target database type
    _normalize_entity_kinds(result_db, target_type)

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
        }
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
