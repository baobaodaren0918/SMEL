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
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener
from Schema.unified_meta_schema import (
    Database, DatabaseType, EntityType, Attribute,
    UniqueConstraint, ForeignKeyConstraint, UniqueProperty, ForeignKeyProperty, PKTypeEnum,
    Reference, Embedded, Cardinality, PrimitiveDataType, PrimitiveType, ListDataType,
    StructuralVariation, RelationshipType, TypeMappings
)
from Schema.adapters import PostgreSQLAdapter, MongoDBAdapter
from config import SCHEMA_DIR, TESTS_DIR, EQUIVALENT_ATTRS, MIGRATION_CONFIGS


@dataclass
class MigrationContext:
    """Context information from SMEL migration declaration."""
    name: str = ""
    version: str = ""
    source_db_type: str = ""
    target_db_type: str = ""


@dataclass
class Operation:
    """Represents a single SMEL operation."""
    op_type: str
    params: Dict[str, Any] = field(default_factory=dict)


class SyntaxErrorListener(ErrorListener):
    """Custom error listener to collect syntax errors."""
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"Line {line}:{column} - {msg}")


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

    def __init__(self, database: Database):
        self.database = copy.deepcopy(database)
        self.changes: List[str] = []
        self.key_registry: Dict[str, Dict[str, Any]] = {}
        self._last_created_entity: Optional[str] = None  # Track last created entity for ADD_KEY/ADD_REFERENCE
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

    def _auto_prefix(self, entity_name: str) -> str:
        """
        Generate automatic prefix from entity name: first 3 chars + last char.
        Examples: employment -> empt, company -> comy, address -> adds
        """
        name = entity_name.lower().replace("_", "")
        if len(name) <= 4:
            return name
        return name[:3] + name[-1]

    def execute(self, operations: List[Operation]) -> Database:
        """Execute all operations and return transformed database."""
        for op in operations:
            handler = getattr(self, f"_handle_{op.op_type.lower()}", None)
            if handler:
                handler(op.params)
        return self.database

    def _handle_nest(self, params: Dict) -> None:
        """
        NEST: Embed separate table into parent as nested object (denormalization).

        Reference: Bianca Meier - NEST vendor:id,name,country IN product.vendor WHERE vendor.id = product.vendorid [with Deletion]
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
        cardinality = Cardinality.ONE_TO_ONE

        # Backward compatibility: support old "clauses" format
        for c in params.get("clauses", []):
            if c["type"] == "CARDINALITY":
                cardinality = self.CARDINALITY_MAP.get(c["value"], Cardinality.ONE_TO_ONE)

        source_entity = self.database.get_entity_type(source_name)
        target_entity = self.database.get_entity_type(target_name)
        if not source_entity or not target_entity:
            return

        # Create embedded entity with specified attributes (or all non-FK attributes if not specified)
        fk_attr_names = {rel.ref_name for rel in source_entity.get_references()}
        embedded_entity = EntityType(object_name=[alias])

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

        self.database.add_entity_type(embedded_entity)
        target_entity.add_relationship(Embedded(aggr_name=alias, aggregates=alias, cardinality=cardinality,
                                                is_optional=not cardinality.is_required()))
        self.changes.append(f"NEST:{target_name}.{alias}")

        # Remove FK reference from target to source
        for rel in list(target_entity.relationships):
            if isinstance(rel, Reference) and rel.get_target_entity_name() == source_name:
                target_entity.remove_relationship(rel.ref_name)
                target_entity.remove_attribute(rel.ref_name)

        # Delete source entity if WITH DELETION is specified
        if with_deletion:
            self.database.remove_entity_type(source_name)
            self.changes.append(f"DELETE_ENTITY:{source_name}")

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
            return

        # Flatten: copy all attributes from embedded entity to parent with prefix
        prefix = nested_name + "_"
        for attr in embedded_entity.attributes:
            new_attr_name = prefix + attr.attr_name
            if not parent_entity.get_attribute(new_attr_name):
                parent_entity.add_attribute(Attribute(
                    new_attr_name, attr.data_type, attr.is_key, attr.is_optional
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

        Example: UNFLATTEN person(vorname, nachname) AS name
          Before: person { vorname, nachname, age }
          After:  person { name: { vorname, nachname }, age }

        The specified fields are moved into a new nested object.
        """
        entity_name = params["entity"]
        fields = params["fields"]
        nested_name = params["nested_name"]

        entity = self.database.get_entity_type(entity_name)
        if not entity:
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

        Reference: Bianca Meier - reverse of NEST operation
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

        The subsequent ADD_PS KEY and ADD_PS REFERENCE operations define the structure.
        """
        mode = params.get("mode", "create_table")
        source_path = params.get("source", "")

        if mode == "expand_in_place":
            # Mode 2: Expand in place - UNWIND person_tag.tags
            # Transform array attribute to its element type (for schema transformation)
            # e.g., tags: ListDataType(STRING) -> tags: STRING
            parts = source_path.split(".")
            if len(parts) >= 2:
                entity_name = parts[0]
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
        self._last_created_entity = target_name  # Track for subsequent ADD_KEY/ADD_REFERENCE
        self.changes.append(f"UNWIND:{target_name}")

        # Remove the array attribute from parent
        if attr:
            parent_entity.remove_attribute(array_name)

    def _handle_wind(self, params: Dict) -> None:
        """
        WIND: Collect multiple rows into array field (reverse of UNWIND).

        Example: WIND person_tag INTO person.tags WHERE person_tag.person_id = person.person_id
          Before: person_tag { person_id, tag_value } (multiple rows)
          After:  person { tags: ["value1", "value2", ...] }

        Note: WITH DELETION optionally removes source entity after collecting.
        """
        source_entity_name = params["source"]  # person_tag
        target_entity_name = params["target"]  # person
        array_name = params["array_name"]      # tags
        with_deletion = params.get("with_deletion", False)

        source_entity = self.database.get_entity_type(source_entity_name)
        target_entity = self.database.get_entity_type(target_entity_name)

        if not source_entity or not target_entity:
            return

        # Find the value attribute in source entity (the field to collect into array)
        # Usually it's a non-key, non-FK field
        value_attr = None
        for attr in source_entity.attributes:
            if not attr.is_key and attr.attr_name not in [r.ref_name for r in source_entity.get_references()]:
                value_attr = attr
                break

        if not value_attr:
            # Fallback: use first non-key attribute
            for attr in source_entity.attributes:
                if not attr.is_key:
                    value_attr = attr
                    break

        # Create array attribute in target entity
        if value_attr:
            array_type = ListDataType(element_type=value_attr.data_type)
        else:
            array_type = ListDataType(element_type=PrimitiveDataType(PrimitiveType.STRING))

        target_entity.add_attribute(Attribute(array_name, array_type, False, True))

        # Optionally delete source entity
        if with_deletion:
            self.database.remove_entity_type(source_entity_name)

        self.changes.append(f"WIND:{source_entity_name}->{target_entity_name}.{array_name}")

    def _handle_delete_reference(self, params: Dict) -> None:
        parts = params["reference"].split(".")
        if len(parts) != 2:
            return
        entity = self.database.get_entity_type(parts[0])
        if entity:
            entity.remove_relationship(parts[1])
            entity.remove_attribute(parts[1])

    def _handle_delete_embedded(self, params: Dict) -> None:
        parts = params["embedded"].split(".")
        if len(parts) != 2:
            return
        parent_name, embedded_name = parts[0], parts[1].replace("[]", "")
        parent_entity = self.database.get_entity_type(parent_name)
        if parent_entity:
            parent_entity.remove_relationship(embedded_name)
            self.database.remove_entity_type(embedded_name)
            self.changes.append(f"DELETE_EMBEDDED:{parent_name}.{embedded_name}")

    def _handle_add_reference(self, params: Dict) -> None:
        """ADD_PS REFERENCE entity.field REFERENCES target_table(target_column) WITH CARDINALITY"""
        # New explicit syntax: entity, field_name, target_table, target_column
        field_name = params.get("field_name")
        target_table = params.get("target_table")
        target_column = params.get("target_column")
        entity_name = params.get("entity")

        # Fallback to old syntax: reference (entity.field), target
        if not field_name and "reference" in params:
            parts = params["reference"].split(".")
            if len(parts) != 2:
                return
            entity_name = parts[0]
            field_name = parts[1]
            target_table = params.get("target")
            target_column = None
        elif not entity_name:
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

        # Parse cardinality from clauses
        # clauses can be a dict (from _parse_reference_clauses) or a list
        cardinality = Cardinality.ONE_TO_ONE  # Default
        clauses = params.get("clauses", {})
        if isinstance(clauses, dict):
            # Dict format: {'cardinality': 'ONE_TO_MANY', ...}
            if 'cardinality' in clauses:
                cardinality = self.CARDINALITY_MAP.get(clauses['cardinality'], Cardinality.ONE_TO_ONE)
        else:
            # List format: [{'type': 'CARDINALITY', 'value': 'ONE_TO_MANY'}, ...]
            for clause in clauses:
                if isinstance(clause, dict) and clause.get("type") == "CARDINALITY":
                    cardinality = self.CARDINALITY_MAP.get(clause.get("value"), Cardinality.ONE_TO_ONE)
                elif isinstance(clause, str) and clause in self.CARDINALITY_MAP:
                    cardinality = self.CARDINALITY_MAP.get(clause, Cardinality.ONE_TO_ONE)

        entity.add_relationship(Reference(ref_name=field_name, refs_to=target_table,
                                          cardinality=cardinality, is_optional=True))
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
                type_map = {
                    "STRING": PrimitiveType.STRING, "TEXT": PrimitiveType.TEXT,
                    "INT": PrimitiveType.INTEGER, "INTEGER": PrimitiveType.INTEGER,
                    "LONG": PrimitiveType.LONG, "DOUBLE": PrimitiveType.DOUBLE,
                    "FLOAT": PrimitiveType.FLOAT, "DECIMAL": PrimitiveType.DECIMAL,
                    "BOOLEAN": PrimitiveType.BOOLEAN, "DATE": PrimitiveType.DATE,
                    "TIMESTAMP": PrimitiveType.TIMESTAMP,
                    "UUID": PrimitiveType.UUID, "BINARY": PrimitiveType.BINARY
                }
                data_type = PrimitiveDataType(type_map.get(type_str, PrimitiveType.STRING))
            elif c["type"] == "NOT_NULL":
                is_optional = False

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if entity:
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
        if len(parts) == 2:
            entity = self.database.get_entity_type(parts[0])
            if entity:
                entity.remove_attribute(parts[1])
                self.changes.append(f"DELETE_ATTR:{target}")

    def _handle_delete_entity(self, params: Dict) -> None:
        """DELETE ENTITY Customer"""
        name = params["name"]
        self.database.remove_entity_type(name)
        self.changes.append(f"DELETE_ENTITY:{name}")

    def _handle_delete_key(self, params: Dict) -> None:
        """DELETE PRIMARY/FOREIGN/UNIQUE KEY - destructive removal"""
        self._remove_key_constraint(params, operation="DELETE")

    def _handle_delete_variation(self, params: Dict) -> None:
        """DELETE VARIATION v1 FROM Customer"""
        entity_name = params["entity"]
        variation_id = params["variation_id"]

        entity = self.database.get_entity_type(entity_name)
        if not entity:
            return

        # Remove the variation
        entity.variations = [v for v in entity.variations if v.variation_id != variation_id]
        self.changes.append(f"DELETE_VARIATION:{entity_name}.{variation_id}")

    def _handle_delete_reltype(self, params: Dict) -> None:
        """DELETE RELTYPE ACTED_IN (graph database)"""
        reltype_name = params["name"]
        # In a full implementation, this would remove the relationship type from graph schema
        self.changes.append(f"DELETE_RELTYPE:{reltype_name}")

    def _handle_delete_index(self, params: Dict) -> None:
        """DELETE INDEX idx_name FROM Customer"""
        index_name = params.get("name")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return

        # Index deletion: Remove from metadata
        self.changes.append(f"DELETE_INDEX:{entity_name}.{index_name}")

    def _handle_delete_label(self, params: Dict) -> None:
        """DELETE LABEL Employee FROM Person (graph database)"""
        label = params.get("label")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return

        # Label deletion: Remove from entity metadata
        self.changes.append(f"DELETE_LABEL:{entity_name}.{label}")

    def _handle_add_index(self, params: Dict) -> None:
        """ADD INDEX idx_name ON Customer (email, name)"""
        index_name = params.get("name")
        entity_name = params.get("entity")
        columns = params.get("columns", [])

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity or not columns:
            return

        # Index implementation: Store as metadata (simplified)
        # In a full implementation, this would create an IndexConstraint
        self.changes.append(f"ADD_INDEX:{entity_name}.{index_name}({', '.join(columns)})")

    def _handle_add_label(self, params: Dict) -> None:
        """ADD LABEL Employee TO Person (graph database)"""
        label = params.get("label")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity or not label:
            return

        # Label implementation: Add to entity metadata (graph-specific)
        # In a full implementation, this would add label to EntityType
        self.changes.append(f"ADD_LABEL:{entity_name}.{label}")

    def _handle_add_key(self, params: Dict) -> None:
        """ADD_PS KEY id AS String OR ADD_PS PRIMARY KEY (id1, id2) TO Customer"""
        entity_name = params.get("entity")
        key_columns = params.get("key_columns", [])  # List of column names
        key_type_str = self.KEY_TYPE_MAP.get(params.get("key_type", "PRIMARY"), "primary")
        data_type_str = params.get("data_type")  # New: AS dataType syntax

        # Parse data type if specified
        if data_type_str:
            type_map = {
                "STRING": PrimitiveType.STRING, "TEXT": PrimitiveType.TEXT,
                "INT": PrimitiveType.INTEGER, "INTEGER": PrimitiveType.INTEGER,
                "LONG": PrimitiveType.LONG, "DOUBLE": PrimitiveType.DOUBLE,
                "FLOAT": PrimitiveType.FLOAT, "DECIMAL": PrimitiveType.DECIMAL,
                "BOOLEAN": PrimitiveType.BOOLEAN, "DATE": PrimitiveType.DATE,
                "TIMESTAMP": PrimitiveType.TIMESTAMP,
                "UUID": PrimitiveType.UUID, "BINARY": PrimitiveType.BINARY
            }
            key_data_type = PrimitiveDataType(type_map.get(data_type_str.upper(), PrimitiveType.STRING))
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
            for c in params.get("clauses", []):
                if c["type"] == "REFERENCES":
                    ref_entity_name = c["target"]
                    ref_attrs = c["columns"]
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

        # Remove existing primary key constraints before adding new one
        if isinstance(constraint, UniqueConstraint) and constraint.is_primary_key:
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
                        self.changes.append(f"DROP_KEY:{entity_name}.({key_names_str})")
                        return

    def _handle_add_variation(self, params: Dict) -> None:
        entity_name = params["entity"]
        variation_id = params["variation_id"]

        entity = self.database.get_entity_type(entity_name)
        if not entity:
            return

        attributes, relationships, count = [], [], 0
        for c in params.get("clauses", []):
            if c["type"] == "ATTRIBUTES":
                for attr_name in c["attributes"]:
                    attr = entity.get_attribute(attr_name)
                    if attr:
                        attributes.append(attr)
            elif c["type"] == "RELATIONSHIPS":
                for rel_name in c["relationships"]:
                    for rel in entity.relationships:
                        if (hasattr(rel, 'ref_name') and rel.ref_name == rel_name) or \
                           (hasattr(rel, 'aggr_name') and rel.aggr_name == rel_name):
                            relationships.append(rel)
            elif c["type"] == "COUNT":
                count = c["count"]

        variation = StructuralVariation(variation_id=variation_id, attributes=attributes,
                                        relationships=relationships, count=count)
        entity.add_variation(variation)
        self.changes.append(f"ADD_VARIATION:{entity_name}.{variation_id}")

    def _handle_remove_variation(self, params: Dict) -> None:
        """REMOVE VARIATION v1 FROM Customer - non-destructive"""
        entity_name = params["entity"]
        variation_id = params["variation_id"]

        entity = self.database.get_entity_type(entity_name)
        if not entity:
            return

        for var in list(entity.variations):
            if var.variation_id == variation_id:
                entity.variations.remove(var)
                self.changes.append(f"REMOVE_VARIATION:{entity_name}.{variation_id}")
                return

    def _handle_remove_index(self, params: Dict) -> None:
        """REMOVE INDEX idx_name FROM Customer - non-destructive"""
        index_name = params.get("name")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return

        # Index removal: Remove from metadata (non-destructive)
        self.changes.append(f"REMOVE_INDEX:{entity_name}.{index_name}")

    def _handle_remove_label(self, params: Dict) -> None:
        """REMOVE LABEL Manager FROM Person - non-destructive (graph database)"""
        label = params.get("label")
        entity_name = params.get("entity")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return

        # Label removal: Remove from entity metadata (non-destructive)
        self.changes.append(f"REMOVE_LABEL:{entity_name}.{label}")

    def _handle_rename(self, params: Dict) -> None:
        """RENAME: Rename an attribute (feature) within an entity."""
        old_name = params["old_name"]
        new_name = params["new_name"]
        entity_name = params.get("entity")

        if entity_name:
            # Rename attribute within entity
            entity = self.database.get_entity_type(entity_name)
            if entity:
                attr = entity.get_attribute(old_name)
                if attr:
                    attr.attr_name = new_name
                    self.changes.append(f"RENAME:{entity_name}.{old_name}->{new_name}")
        else:
            # Fallback: Rename entity itself (for backward compatibility)
            entity = self.database.get_entity_type(old_name)
            if entity:
                self.database.remove_entity_type(old_name)
                # Update object_name: keep parent path, change last element
                entity.object_name = entity.parent_path + [new_name]
                self.database.add_entity_type(entity)
                self.changes.append(f"RENAME:{old_name}->{new_name}")

    def _handle_rename_entity(self, params: Dict) -> None:
        """RENAME ENTITY: Rename an entity."""
        old_name = params["old_name"]
        new_name = params["new_name"]

        entity = self.database.get_entity_type(old_name)
        if entity:
            self.database.remove_entity_type(old_name)
            # Update object_name: keep parent path, change last element
            entity.object_name = entity.parent_path + [new_name]
            self.database.add_entity_type(entity)
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

    def _handle_move(self, params: Dict) -> None:
        """MOVE: Move attribute from one entity to another."""
        source_path = params["source"]
        target_path = params["target"]

        source_parts = source_path.split(".")
        target_parts = target_path.split(".")

        if len(source_parts) == 2 and len(target_parts) == 2:
            # Move attribute
            src_entity = self.database.get_entity_type(source_parts[0])
            tgt_entity = self.database.get_entity_type(target_parts[0])
            if src_entity and tgt_entity:
                src_attr = src_entity.get_attribute(source_parts[1])
                if src_attr:
                    # Add to target
                    new_attr = Attribute(target_parts[1], src_attr.data_type, False, src_attr.is_optional)
                    tgt_entity.add_attribute(new_attr)
                    # Remove from source
                    src_entity.remove_attribute(source_parts[1])
                    self.changes.append(f"MOVE:{source_path}->{target_path}")

    def _handle_merge(self, params: Dict) -> None:
        """MERGE: Merge two entities into one."""
        source1_name = params["source1"]
        source2_name = params["source2"]
        target_name = params["target"]

        source1 = self.database.get_entity_type(source1_name)
        source2 = self.database.get_entity_type(source2_name)
        if not source1 or not source2:
            return

        # Create new entity with combined attributes
        new_entity = EntityType(object_name=[target_name])

        # Add attributes from source1
        for attr in source1.attributes:
            new_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, attr.is_key, attr.is_optional))

        # Add attributes from source2 (avoid duplicates)
        existing_names = {a.attr_name for a in new_entity.attributes}
        for attr in source2.attributes:
            if attr.attr_name not in existing_names:
                new_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, False, attr.is_optional))

        # Copy primary key from source1
        pk = source1.get_primary_key()
        if pk:
            new_entity.add_constraint(copy.deepcopy(pk))

        self.database.add_entity_type(new_entity)

        # Remove source entities if different from target
        if source1_name != target_name:
            self.database.remove_entity_type(source1_name)
        if source2_name != target_name:
            self.database.remove_entity_type(source2_name)

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
        self._handle_split_flat(params)

    def _handle_split_flat(self, params: Dict) -> None:
        """Handle flat split (vertical partitioning)."""
        source_name = params.get("source")
        parts = params.get("parts", [])

        # Fallback to old syntax if no parts specified
        if not parts and "target1" in params:
            parts = [
                {"name": params["target1"], "fields": []},
                {"name": params["target2"], "fields": []}
            ]

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

            # Each part reuses the source primary key with updated property_ids
            if pk:
                new_pk = copy.deepcopy(pk)
                # Update property_ids to point to new attribute meta_ids
                for up in new_pk.unique_properties:
                    if up.property_id in meta_id_map:
                        up.property_id = meta_id_map[up.property_id]
                new_entity.add_constraint(new_pk)

            self.database.add_entity_type(new_entity)
            created_entities.append(part_name)

        # Remove source if different from all targets
        if source_name not in [p["name"] for p in parts]:
            self.database.remove_entity_type(source_name)

        parts_str = ",".join(created_entities)
        self.changes.append(f"SPLIT:{source_name}->{parts_str}")

    def _handle_add(self, params: Dict) -> None:
        """ADD: Add attribute, reference, embedded, entity, or variation."""
        feature_type = params["feature_type"].upper()
        name = params["name"]
        entity_name = params.get("entity")
        clauses = params.get("clauses", [])

        # Parse data type from clauses
        data_type = PrimitiveDataType(PrimitiveType.STRING)
        is_optional = True
        cardinality = Cardinality.ONE_TO_ONE

        for c in clauses:
            if c["type"] == "TYPE":
                type_str = c["data_type"].upper()
                type_map = {
                    "STRING": PrimitiveType.STRING, "TEXT": PrimitiveType.TEXT,
                    "INT": PrimitiveType.INTEGER, "INTEGER": PrimitiveType.INTEGER,
                    "LONG": PrimitiveType.LONG, "DOUBLE": PrimitiveType.DOUBLE,
                    "FLOAT": PrimitiveType.FLOAT, "DECIMAL": PrimitiveType.DECIMAL,
                    "BOOLEAN": PrimitiveType.BOOLEAN, "DATE": PrimitiveType.DATE,
                    "TIMESTAMP": PrimitiveType.TIMESTAMP,
                    "UUID": PrimitiveType.UUID, "BINARY": PrimitiveType.BINARY
                }
                data_type = PrimitiveDataType(type_map.get(type_str, PrimitiveType.STRING))
            elif c["type"] == "NOT_NULL":
                is_optional = False
            elif c["type"] == "CARDINALITY":
                cardinality = self.CARDINALITY_MAP.get(c["value"], Cardinality.ONE_TO_ONE)

        if feature_type == "ATTRIBUTE":
            entity = self.database.get_entity_type(entity_name) if entity_name else None
            if entity:
                entity.add_attribute(Attribute(name, data_type, False, is_optional))
                self.changes.append(f"ADD_ATTR:{entity_name}.{name}")

        elif feature_type == "ENTITY":
            new_entity = EntityType(object_name=[name])
            self.database.add_entity_type(new_entity)
            self.changes.append(f"ADD_ENTITY:{name}")

        elif feature_type == "REFERENCE":
            entity = self.database.get_entity_type(entity_name) if entity_name else None
            if entity:
                entity.add_attribute(Attribute(name, PrimitiveDataType(PrimitiveType.INTEGER), False, is_optional))
                entity.add_relationship(Reference(ref_name=name, refs_to="", cardinality=cardinality, is_optional=is_optional))
                self.changes.append(f"ADD_REF:{entity_name}.{name}")

        elif feature_type == "EMBEDDED":
            entity = self.database.get_entity_type(entity_name) if entity_name else None
            if entity:
                entity.add_relationship(Embedded(aggr_name=name, aggregates=name, cardinality=cardinality, is_optional=is_optional))
                self.changes.append(f"ADD_EMBEDDED:{entity_name}.{name}")

    def _handle_delete(self, params: Dict) -> None:
        """DELETE: Delete attribute, reference, embedded, entity, or variation."""
        feature_type = params["feature_type"].upper()
        target = params["target"]

        parts = target.split(".")

        if feature_type == "ATTRIBUTE":
            if len(parts) == 2:
                entity = self.database.get_entity_type(parts[0])
                if entity:
                    entity.remove_attribute(parts[1])
                    self.changes.append(f"DELETE_ATTR:{target}")

        elif feature_type == "ENTITY":
            self.database.remove_entity_type(parts[0])
            self.changes.append(f"DELETE_ENTITY:{parts[0]}")

        elif feature_type == "REFERENCE":
            if len(parts) == 2:
                entity = self.database.get_entity_type(parts[0])
                if entity:
                    entity.remove_relationship(parts[1])
                    entity.remove_attribute(parts[1])
                    self.changes.append(f"DELETE_REF:{target}")

        elif feature_type == "EMBEDDED":
            if len(parts) == 2:
                entity = self.database.get_entity_type(parts[0])
                if entity:
                    entity.remove_relationship(parts[1])
                    self.changes.append(f"DELETE_EMBEDDED:{target}")

    def _handle_cast(self, params: Dict) -> None:
        """CAST: Change attribute data type."""
        target = params["target"]
        new_type_str = params.get("data_type", params.get("type", "STRING")).upper()

        parts = target.split(".")
        if len(parts) != 2:
            return

        entity = self.database.get_entity_type(parts[0])
        if not entity:
            return

        attr = entity.get_attribute(parts[1])
        if not attr:
            return

        type_map = {
            "STRING": PrimitiveType.STRING, "TEXT": PrimitiveType.TEXT,
            "INT": PrimitiveType.INTEGER, "INTEGER": PrimitiveType.INTEGER,
            "LONG": PrimitiveType.LONG, "DOUBLE": PrimitiveType.DOUBLE,
            "FLOAT": PrimitiveType.FLOAT, "DECIMAL": PrimitiveType.DECIMAL,
            "BOOLEAN": PrimitiveType.BOOLEAN, "DATE": PrimitiveType.DATE,
            "TIMESTAMP": PrimitiveType.TIMESTAMP,
            "UUID": PrimitiveType.UUID, "BINARY": PrimitiveType.BINARY
        }
        new_type = type_map.get(new_type_str, PrimitiveType.STRING)
        attr.data_type = PrimitiveDataType(new_type)
        self.changes.append(f"CAST:{target}->{new_type_str}")

    def _handle_linking(self, params: Dict) -> None:
        """LINKING: Create a reference link between entities."""
        source = params["source"]
        target = params["target"]

        parts = source.split(".")
        if len(parts) != 2:
            return

        entity = self.database.get_entity_type(parts[0])
        if not entity:
            return

        # Add reference attribute if not exists
        if not entity.get_attribute(parts[1]):
            entity.add_attribute(Attribute(parts[1], PrimitiveDataType(PrimitiveType.INTEGER), False, True))

        entity.add_relationship(Reference(ref_name=parts[1], refs_to=target,
                                          cardinality=Cardinality.ONE_TO_ONE, is_optional=True))
        self.changes.append(f"LINKING:{source}->{target}")

    def _handle_extract(self, params: Dict) -> None:
        """EXTRACT: Extract attributes from entity to create new entity."""
        attributes = params["attributes"]
        source_name = params["source"]
        target_name = params["target"]
        clauses = params.get("clauses", [])

        source = self.database.get_entity_type(source_name)
        if not source:
            return

        # Create new entity with extracted attributes
        new_entity = EntityType(object_name=[target_name])

        # Process clauses for key generation
        pk_name = None
        ref_clauses = []
        for c in clauses:
            if c["type"] == "GENERATE_KEY":
                pk_name = c["key_name"]
                pk_type = PrimitiveDataType(PrimitiveType.INTEGER)
                pk_attr = Attribute(pk_name, pk_type, True, False)
                new_entity.add_attribute(pk_attr)
                constraint = UniqueConstraint(
                    is_primary_key=True,
                    is_managed=True,
                    unique_properties=[UniqueProperty(primary_key_type=PKTypeEnum.SIMPLE, property_id=pk_attr.meta_id)]
                )
                new_entity.add_constraint(constraint)
            elif c["type"] == "ADD_REFERENCE":
                ref_clauses.append(c)

        # Copy specified attributes
        for attr_name in attributes:
            attr = source.get_attribute(attr_name)
            if attr and attr_name != pk_name:
                new_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, False, attr.is_optional))
                # Remove from source
                source.remove_attribute(attr_name)

        # Add references
        for c in ref_clauses:
            new_entity.add_attribute(Attribute(c["ref_name"], PrimitiveDataType(PrimitiveType.INTEGER), False, False))
            new_entity.add_relationship(Reference(ref_name=c["ref_name"], refs_to=c["target"],
                                                  cardinality=Cardinality.ONE_TO_ONE, is_optional=False))

        self.database.add_entity_type(new_entity)
        self.changes.append(f"EXTRACT:{source_name}->{target_name}")

    def _handle_add_reltype(self, params: Dict) -> None:
        """ADD RELTYPE: Add a graph relationship type (Neo4j)."""
        name = params["name"]
        source = params["source"]
        target = params["target"]
        clauses = params.get("clauses", [])

        cardinality = Cardinality.ZERO_TO_MANY
        properties = []

        for c in clauses:
            if c["type"] == "CARDINALITY":
                cardinality = self.CARDINALITY_MAP.get(c["value"], Cardinality.ZERO_TO_MANY)
            elif c["type"] == "PROPERTIES":
                properties = c["properties"]

        rel_type = RelationshipType(rel_name=name, source_entity=source, target_entity=target, cardinality=cardinality)

        # Add properties as attributes
        for prop_name in properties:
            rel_type.add_attribute(Attribute(prop_name, PrimitiveDataType(PrimitiveType.STRING), False, True))

        self.database.add_relationship_type(rel_type)
        self.changes.append(f"ADD_RELTYPE:{name}")

    def _handle_delete_reltype(self, params: Dict) -> None:
        """DELETE RELTYPE: Remove a graph relationship type (deprecated, use DROP)."""
        name = params["name"]
        self.database.remove_relationship_type(name)
        self.changes.append(f"DELETE_RELTYPE:{name}")

    def _handle_drop_reltype(self, params: Dict) -> None:
        """DROP RELTYPE: Remove a graph relationship type."""
        name = params["name"]
        self.database.remove_relationship_type(name)
        self.changes.append(f"DROP_RELTYPE:{name}")

    def _handle_rename_reltype(self, params: Dict) -> None:
        """RENAME RELTYPE: Rename a graph relationship type."""
        old_name = params["old_name"]
        new_name = params["new_name"]

        rel_type = self.database.get_relationship_type(old_name)
        if rel_type:
            self.database.remove_relationship_type(old_name)
            rel_type.rel_name = new_name
            self.database.add_relationship_type(rel_type)
            self.changes.append(f"RENAME_RELTYPE:{old_name}->{new_name}")


def db_to_dict(db: Database) -> Dict[str, Any]:
    """
    Convert Database to a JSON-serializable dictionary (Unified Meta Schema format).

    Args:
        db: Database instance

    Returns:
        Dictionary representation of the database
    """
    entities = {}
    for name, entity in db.entity_types.items():
        def get_type_str(data_type):
            """Convert data type to string representation."""
            if hasattr(data_type, 'primitive_type'):
                return data_type.primitive_type.value
            elif hasattr(data_type, 'element_type'):
                # ListDataType - show as array[element_type]
                element = get_type_str(data_type.element_type)
                return f"array[{element}]"
            return 'unknown'

        entities[name] = {
            "name": name,
            "attributes": [
                {
                    "name": a.attr_name,
                    "type": get_type_str(a.data_type),
                    "is_key": a.is_key,
                    "is_optional": a.is_optional
                }
                for a in entity.attributes
            ],
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
            ]
        }
    return entities


# Type mappings for source format display (from centralized TypeMappings)


def _get_source_type_str(attr: Attribute, source_type: str) -> str:
    """Get the original type string for an attribute based on source database type."""
    primitive = attr.data_type.primitive_type if hasattr(attr.data_type, 'primitive_type') else PrimitiveType.STRING

    if source_type == "Relational":
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
    else:
        # MongoDB format (bsonType, using centralized TypeMappings)
        return TypeMappings.PRIMITIVE_TO_MONGO_DISPLAY.get(primitive, 'string')


def db_to_source_dict(db: Database, source_type: str) -> Dict[str, Any]:
    """
    Convert Database to a JSON-serializable dictionary with original source format types.

    Args:
        db: Database instance
        source_type: "Relational" or "Document"

    Returns:
        Dictionary representation with original type names (e.g., SERIAL, VARCHAR(35), bsonType)
    """
    entities = {}
    for name, entity in db.entity_types.items():
        entities[name] = {
            "name": name,
            "attributes": [
                {
                    "name": a.attr_name,
                    "type": _get_source_type_str(a, source_type),
                    "is_key": a.is_key,
                    "is_optional": a.is_optional
                }
                for a in entity.attributes
            ],
            "references": [
                {
                    "name": r.ref_name,
                    "target": r.get_target_entity_name()
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
            ]
        }
    return entities


def parse_original_source(raw_source: str, source_type: str) -> Dict[str, Any]:
    """
    Parse raw source schema into a nested structure for display.
    For MongoDB: returns the original nested document structure.
    For PostgreSQL: returns the table structure.
    """
    import json

    if source_type == "Document":
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

    else:
        # Relational (PostgreSQL) - parse SQL DDL
        # For now, return a simplified structure from raw DDL
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
                    col_type = parts[1]
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


def _calculate_changes(prev: Dict, after: Dict, op) -> Dict:
    """Calculate the changes made by an operation."""
    changes = {
        "affected_entities": [],
        "new_entities": [],
        "deleted_entities": [],
        "modified_entities": []
    }

    prev_names = set(prev.keys())
    after_names = set(after.keys())

    # New entities
    for name in after_names - prev_names:
        changes["new_entities"].append(name)
        changes["affected_entities"].append({
            "name": name,
            "status": "new",
            "entity": after[name]
        })

    # Deleted entities
    for name in prev_names - after_names:
        changes["deleted_entities"].append(name)
        changes["affected_entities"].append({
            "name": name,
            "status": "deleted",
            "entity": prev[name]
        })

    # Modified entities
    for name in prev_names & after_names:
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

        new_attrs = set(after_attrs.keys()) - set(prev_attrs.keys())
        deleted_attrs = set(prev_attrs.keys()) - set(after_attrs.keys())
        new_embedded = set(after_embedded.keys()) - set(prev_embedded.keys())
        deleted_embedded = set(prev_embedded.keys()) - set(after_embedded.keys())
        new_refs = set(after_refs.keys()) - set(prev_refs.keys())
        deleted_refs = set(prev_refs.keys()) - set(after_refs.keys())

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

        if new_attrs or deleted_attrs or new_embedded or deleted_embedded or new_refs or deleted_refs or type_changed_attrs:
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
                "type_changed_attributes": type_changed_attrs
            })

    return changes


def sort_by_dependency(operations: List, initial_entities: set) -> List:
    """
    Sort operations by dependency order using multi-pass scanning.

    Args:
        operations: List of Operation objects
        initial_entities: Set of entity names that already exist (source entities)

    Returns:
        List of operations sorted by dependency order

    Raises:
        ValueError: If circular dependency is detected
    """
    # Separate FLATTEN operations from others
    flatten_ops = []
    other_ops = []

    for op in operations:
        if op.op_type == "FLATTEN":
            flatten_ops.append(op)
        else:
            other_ops.append(op)

    # Build dependency info for FLATTEN operations
    # Each FLATTEN creates a new entity and may reference other entities
    op_dependencies = {}
    for op in flatten_ops:
        target = op.params.get("target")
        refs = []
        for clause in op.params.get("clauses", []):
            if clause.get("type") == "ADD_REFERENCE":
                ref_target = clause.get("target")
                if ref_target:
                    refs.append(ref_target)
        op_dependencies[target] = {
            "op": op,
            "refs": refs
        }

    # Sort FLATTEN operations by dependency
    sorted_flatten = []
    resolved = set(initial_entities)
    remaining = list(flatten_ops)
    max_iterations = len(flatten_ops) + 1
    iterations = 0

    while remaining and iterations < max_iterations:
        iterations += 1
        progress = False

        for op in remaining[:]:
            target = op.params.get("target")
            deps = op_dependencies.get(target, {}).get("refs", [])

            # Check if all dependencies are resolved
            if all(dep in resolved for dep in deps):
                sorted_flatten.append(op)
                remaining.remove(op)
                resolved.add(target)
                progress = True

        if not progress and remaining:
            # No progress made - circular dependency detected
            unresolved = [op.params.get("target") for op in remaining]
            raise ValueError(f"Circular dependency detected among: {unresolved}")

    # Return: other ops first (CAST, COPY, RENAME etc.), then sorted FLATTEN ops
    # Actually, FLATTEN should come first to create entities, then other operations modify them
    return sorted_flatten + other_ops


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
    entities_to_remove = []
    for entity_name in list(db.entity_types.keys()):
        if "." in entity_name:
            # This is an embedded entity path like "person.address"
            # Check if a flattened table was created for this path's last component
            short_name = entity_name.split(".")[-1]
            # Also check if any flattened target matches this entity
            entities_to_remove.append(entity_name)

    for entity_name in entities_to_remove:
        db.remove_entity_type(entity_name)

    # Remove embedded relationships from all remaining entities
    # (they've been converted to reference relationships)
    for entity in db.entity_types.values():
        embedded_to_remove = []
        for rel in entity.relationships:
            if isinstance(rel, Embedded):
                embedded_to_remove.append(rel.aggr_name)

        for rel_name in embedded_to_remove:
            entity.remove_relationship(rel_name)


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

    # Determine adapters based on source/target types
    source_adapter = PostgreSQLAdapter if source_type == "Relational" else MongoDBAdapter
    target_adapter = PostgreSQLAdapter if target_type == "Relational" else MongoDBAdapter

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
    # For new syntax (ADD_PS KEY, ADD_PS REFERENCE after FLATTEN/UNWIND),
    # the order in the file is intentional and should be preserved
    for i, op in enumerate(operations):
        prev_count = len(transformer.database.entity_types)
        prev_snapshot = db_to_dict(transformer.database)
        prev_changes_len = len(transformer.changes)

        handler = getattr(transformer, f"_handle_{op.op_type.lower()}", None)
        if handler:
            handler(op.params)

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
            "type": op.op_type,
            "original_keyword": op.original_keyword if hasattr(op, 'original_keyword') and op.original_keyword else op.op_type,
            "params": op.params,
            "entity_count_before": prev_count,
            "entity_count_after": new_count,
            "changes": changes_detail,
            "status": status
        })

    result_db = transformer.database
    result_db.db_type = DatabaseType.DOCUMENT if target_type == "Document" else DatabaseType.RELATIONAL

    # Cleanup: Remove embedded entities and relationships that have been flattened
    # This ensures the ER diagram shows only the normalized structure
    _cleanup_flattened_entities(result_db, transformer.changes)

    # Step 3: Export Meta V2 -> Target DDL
    if target_adapter == MongoDBAdapter:
        exported_target = MongoDBAdapter.export_to_json_string(result_db)
    else:
        exported_target = PostgreSQLAdapter.export_to_sql(result_db)

    return {
        "source_type": source_type,
        "target_type": target_type,
        "raw_source": raw_source,
        "exported_target": exported_target,
        "smel_content": smel_content,
        "smel_file": smel_file.name,
        "operations_detail": operations_detail,
        "original_source": parse_original_source(raw_source, source_type),  # Original nested structure (before reverse eng)
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
