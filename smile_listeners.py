"""
SMILE Listeners - Parsers for the two SMILE grammar variants.

This module provides listener implementations for:
1. SMILE_Specific.g4 - Specific operations version (one keyword per op)
2. SMILE_Generalized.g4 - Generalized operations version (verb + object)

Both listeners share common logic through the BaseSMILEListener class.
"""
import sys
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from grammar.specific.SMILE_SpecificListener import SMILE_SpecificListener
from grammar.specific.SMILE_SpecificParser import SMILE_SpecificParser
from grammar.generalized.SMILE_GeneralizedListener import SMILE_GeneralizedListener
from grammar.generalized.SMILE_GeneralizedParser import SMILE_GeneralizedParser
from operation_params import (
    OpParams, KeyType,
    NestParams, UnnestParams, FlattenParams, UnflattenParams,
    WindParams, UnwindParams,
    AddEntityParams, DeleteEntityParams, RenameEntityParams, CopyEntityParams,
    AddPropertyParams, DeletePropertyParams, RenamePropertyParams,
    CopyPropertyParams, MovePropertyParams,
    AddKeyParams, DeleteKeyParams,
    AddForeignKeyParams, DeleteForeignKeyParams, CastConstraintParams,
    CastEntityParams,
    AddEmbeddedParams, DeleteEmbeddedParams,
    AddLabelParams, DeleteLabelParams,
    CastPropertyParams, MergeParams, SplitParams,
    RecardParams, TransformParams,
)


class OpType(str, Enum):
    """Operation types for SMILE schema migration operations.

    Values are lowercase strings matching handler method names in SchemaTransformer
    (e.g., OpType.NEST -> _handle_nest). Use .name for uppercase display (e.g., "NEST").
    """
    # Structure operations
    NEST = "nest"
    UNNEST = "unnest"
    FLATTEN = "flatten"
    UNFLATTEN = "unflatten"
    WIND = "wind"
    UNWIND = "unwind"
    # Entity operations
    ADD_ENTITY = "add_entity"
    DELETE_ENTITY = "delete_entity"
    RENAME_ENTITY = "rename_entity"
    COPY_ENTITY = "copy_entity"
    # Property operations
    ADD_PROPERTY = "add_property"
    DELETE_PROPERTY = "delete_property"
    RENAME_PROPERTY = "rename_property"
    COPY_PROPERTY = "copy_property"
    MOVE_PROPERTY = "move_property"
    # Key/Constraint operations
    ADD_KEY = "add_key"
    DELETE_KEY = "delete_key"
    ADD_FOREIGN_KEY = "add_foreign_key"
    DELETE_FOREIGN_KEY = "delete_foreign_key"
    CAST_CONSTRAINT = "cast_constraint"
    CAST_ENTITY = "cast_entity"
    # Embedded operations
    ADD_EMBEDDED = "add_embedded"
    DELETE_EMBEDDED = "delete_embedded"
    # Label operations (Graph)
    ADD_LABEL = "add_label"
    DELETE_LABEL = "delete_label"
    # Schema transformation
    TRANSFORM = "transform"
    MERGE = "merge"
    SPLIT = "split"
    CAST_PROPERTY = "cast_property"
    RECARD = "recard"


@dataclass
class MigrationContext:
    """Context information from SMILE script declaration."""
    name: str = ""
    version: str = ""
    is_evolution: bool = False
    source_db_type: str = ""
    target_db_type: str = ""
    schema_name: str = ""
    schema_version: str = ""
    target_schema_version: str = ""  # only for evolution: VERSION x TO y


@dataclass
class Operation:
    """Represents a single SMILE operation."""
    op_type: OpType
    params: OpParams  # typed payload; see operation_params.py for one dataclass per OpType
    original_keyword: str = ""  # Original keyword from source (e.g., "FLATTEN", "RENAME_PROPERTY")


class BaseSMILEListener:
    """
    Base class with shared parsing logic for all SMILE variants.

    This class provides common helper methods used by all listener implementations.
    """

    def __init__(self):
        self.context = MigrationContext()
        self.operations: List[Operation] = []

    # ========== Helper methods for parsing clauses ==========

    def _parse_condition_pairs(self, condition_ctx):
        """Recursively parse condition tree into list of (left = right) join pairs.

        Supports:
          a.x = b.y                        → [{"left": "a.x", "right": "b.y"}]
          a.x = b.y AND a.z = b.z          → [{"left": "a.x", ...}, {"left": "a.z", ...}]
          (a.x = b.y) AND a.z = b.z        → same, with parentheses
        """
        pairs = []
        # Leaf: qualifiedName EQUALS qualifiedName
        qns = condition_ctx.qualifiedName()
        if qns and len(qns) == 2:
            pairs.append({
                "left": qns[0].getText(),
                "right": qns[1].getText()
            })
        # Recursive: condition AND condition  /  (condition)
        sub_conditions = condition_ctx.condition()
        if sub_conditions:
            for sub in sub_conditions:
                pairs.extend(self._parse_condition_pairs(sub))
        return pairs

    def _parse_property_clauses(self, clause_list):
        """Parse property clauses: WITH TYPE, WITH DEFAULT, NOT NULL.
        Returns list of dicts, e.g. [{'type': 'TYPE', 'data_type': 'String'}, {'type': 'NOT_NULL'}]
        """
        result = []
        for clause in clause_list:
            if hasattr(clause, 'withTypeClause') and clause.withTypeClause():
                result.append({'type': 'TYPE', 'data_type': clause.withTypeClause().dataType().getText()})
            elif hasattr(clause, 'withDefaultClause') and clause.withDefaultClause():
                result.append({'type': 'DEFAULT', 'value': clause.withDefaultClause().literal().getText()})
            elif hasattr(clause, 'notNullClause') and clause.notNullClause():
                result.append({'type': 'NOT_NULL'})
        return result

    def _parse_reference_clauses(self, clause_list):
        """Parse reference clauses"""
        result = {}
        for clause in clause_list:
            if hasattr(clause, 'withCardinalityClause') and clause.withCardinalityClause():
                result['cardinality'] = clause.withCardinalityClause().cardinalityType().getText()
            elif hasattr(clause, 'usingKeyClause') and clause.usingKeyClause():
                result['key'] = clause.usingKeyClause().identifier().getText()
            elif hasattr(clause, 'whereClause') and clause.whereClause():
                result['where'] = clause.whereClause().condition().getText()
        return result

    def _parse_embedded_clauses(self, clause_list):
        """Parse embedded clauses.
        Returns list of dicts, e.g. [{'type': 'CARDINALITY', 'value': 'ONE_TO_ONE'}]
        """
        result = []
        for clause in clause_list:
            if hasattr(clause, 'withCardinalityClause') and clause.withCardinalityClause():
                result.append({'type': 'CARDINALITY', 'value': clause.withCardinalityClause().cardinalityType().getText()})
            elif hasattr(clause, 'withStructureClause') and clause.withStructureClause():
                ids = clause.withStructureClause().identifierList()
                result.append({'type': 'STRUCTURE', 'fields': [id.getText() for id in ids.identifier()]})
        return result

    def _parse_entity_clauses(self, clause_list):
        """Parse entity clauses.
        Returns list of dicts, e.g. [{'type': 'PROPERTIES', 'properties': [{'name': 'id', 'data_type': 'String'}, ...]}, {'type': 'KEY', 'key_name': 'id'}]
        """
        result = []
        for clause in clause_list:
            if hasattr(clause, 'withPropertiesClause') and clause.withPropertiesClause():
                prop_def_list = clause.withPropertiesClause().propertyDefList()
                props = []
                for prop_def in prop_def_list.propertyDef():
                    props.append({
                        'name': prop_def.identifier().getText(),
                        'data_type': prop_def.dataType().getText()
                    })
                result.append({'type': 'PROPERTIES', 'properties': props})
            elif hasattr(clause, 'withKeyClause') and clause.withKeyClause():
                result.append({'type': 'KEY', 'key_name': clause.withKeyClause().identifier().getText()})
        return result

    def _parse_key_columns(self, key_columns_ctx):
        """
        Parse key columns - supports qualifiedName (entity.field) or composite keys.

        Returns: (key_columns_list, entity_name)
        - For qualifiedName: (["field"], "entity") or (["field"], None)
        - For composite: (["a", "b"], None)
        """
        if key_columns_ctx.qualifiedName():
            # New: qualifiedName supports entity.field syntax
            full_path = key_columns_ctx.qualifiedName().getText()
            parts = full_path.split(".")
            if len(parts) == 2:
                # Explicit entity.field syntax: address.address_id -> (["address_id"], "address")
                entity_name = parts[0]
                field_name = parts[1]
                return [field_name], entity_name
            else:
                # Single identifier (no dot): just field name
                return [full_path], None
        elif key_columns_ctx.identifierList():
            # Composite key (id1, id2, id3)
            return [id.getText() for id in key_columns_ctx.identifierList().identifier()], None
        return [], None

    def _parse_key_clauses(self, clause_list):
        """Parse key clauses"""
        result = {}
        for clause in clause_list:
            if hasattr(clause, 'referencesClause') and clause.referencesClause():
                ref = clause.referencesClause()
                result['references'] = {
                    'table': ref.identifier().getText(),
                    'columns': [id.getText() for id in ref.identifierList().identifier()]
                }
            elif hasattr(clause, 'withColumnsClause') and clause.withColumnsClause():
                ids = clause.withColumnsClause().identifierList()
                result['columns'] = [id.getText() for id in ids.identifier()]
        return result

    def _parse_unnest_field_list(self, field_list_ctx, parser_module):
        """
        Recursively parse UNNEST field list to separate properties and nested objects.

        Grammar structure:
          unnestFieldList: unnestField (COMMA unnestField)*;
          unnestField: identifier                                    # SimpleField
                     | identifier LBRACE unnestFieldList RBRACE      # NestedField

        Args:
            field_list_ctx: The unnestFieldList context from parser
            parser_module: Either SMILE_SpecificParser or SMILE_GeneralizedParser

        Returns:
            tuple: (properties, nested)
                   - properties: list of simple property names ['position', 'name']
                   - nested: list of nested object dicts [{'name': 'company', 'children': {...}}]
        """
        properties = []
        nested = []

        for field_ctx in field_list_ctx.unnestField():
            if isinstance(field_ctx, parser_module.SimpleFieldContext):
                # Simple property: position, name, street, city
                properties.append(field_ctx.identifier().getText())
            elif isinstance(field_ctx, parser_module.NestedFieldContext):
                # Nested object: company{name, address{street, city}}
                nested_name = field_ctx.identifier().getText()
                # Recursively parse nested field list
                nested_field_list = field_ctx.unnestFieldList()
                child_props, child_nested = self._parse_unnest_field_list(nested_field_list, parser_module)
                nested.append({
                    'name': nested_name,
                    'properties': child_props,
                    'nested': child_nested
                })

        return properties, nested


# ==============================================================================
# SMILE_Specific Listener - For SMILE_Specific.g4
# ==============================================================================

class SMILESpecificListener(SMILE_SpecificListener, BaseSMILEListener):
    """
    Listener for SMILE_Specific.g4 grammar.

    Uses specific keywords like ADD_PROPERTY, DELETE_ENTITY, RENAME_PROPERTY.
    """

    def __init__(self):
        BaseSMILEListener.__init__(self)

    # Header parsing (same for all versions)
    def enterMigrationDecl(self, ctx):
        self.context.is_evolution = False
        self.context.name = ctx.identifier().getText()
        self.context.version = ctx.version().getText()

    def enterEvolutionDecl(self, ctx):
        self.context.is_evolution = True
        self.context.name = ctx.identifier().getText()
        self.context.version = ctx.version().getText()

    def enterUsingDecl(self, ctx):
        self.context.schema_name = ctx.identifier().getText()
        self.context.schema_version = ctx.version(0).getText()
        if len(ctx.version()) > 1:
            self.context.target_schema_version = ctx.version(1).getText()

    def enterFromToDecl(self, ctx):
        self.context.source_db_type = ctx.databaseType(0).getText()
        self.context.target_db_type = ctx.databaseType(1).getText()

    # Structure operations
    def enterFlatten(self, ctx):
        # New syntax: FLATTEN qualifiedName
        # Flattens nested object fields into parent table (reduce depth by 1)
        # Example: FLATTEN customers.address
        #   Before: customers { name: { first_name, last_name }, age }
        #   After:  customers { name_first_name, name_last_name, age }
        self.operations.append(Operation(OpType.FLATTEN, FlattenParams(
            source=ctx.qualifiedName().getText()
        ), original_keyword="FLATTEN"))

    def enterUnflatten(self, ctx):
        # UNFLATTEN - Combine flat fields into nested object (reverse of FLATTEN)
        # Example: UNFLATTEN customers:first_name, last_name AS name
        #   Before: customers { first_name, last_name, age }
        #   After:  customers { name: { first_name, last_name }, age }
        entity = ctx.identifier(0).getText()  # customers
        fields = [id.getText() for id in ctx.identifierList().identifier()]  # [first_name, last_name]
        nested_name = ctx.identifier(1).getText()  # name
        self.operations.append(Operation(OpType.UNFLATTEN, UnflattenParams(
            entity=entity,
            fields=fields,
            nested_name=nested_name,
        ), original_keyword="UNFLATTEN"))

    def enterUnwind(self, ctx):
        source = ctx.qualifiedName().getText()
        target = ctx.identifier().getText() if ctx.identifier() else None

        if target:
            # Mode 1: Create new table - UNWIND customers.tags[] INTO customer_tag
            self.operations.append(Operation(OpType.UNWIND, UnwindParams(
                mode="create_table",
                source=source,
                target=target,
            ), original_keyword="UNWIND"))
        else:
            # Mode 2: Expand in place - UNWIND customer_tag.value
            self.operations.append(Operation(OpType.UNWIND, UnwindParams(
                mode="expand_in_place",
                source=source,
            ), original_keyword="UNWIND"))

    def enterWind(self, ctx):
        # WIND - Convert scalar property back to array (reverse of UNWIND)
        # Syntax: WIND customer_tag.tags
        # Cross-entity movement is handled by MERGE, not WIND.
        source = ctx.qualifiedName().getText()  # customer_tag.tags
        self.operations.append(Operation(OpType.WIND, WindParams(
            source=source,
        ), original_keyword="WIND"))

    def enterNest(self, ctx):
        # Syntax: NEST identifier COLON unnestFieldList IN qualifiedName WHERE condition
        # Example: NEST address:street,city IN customers.address WHERE address.customer_id = customers.customer_id
        # Example: NEST address:street,city IN customers.address WHERE address.customer_id = customers.customer_id AND address.dept_id = customers.dept_id
        source_entity = ctx.identifier().getText()  # address
        target_location = ctx.qualifiedName().getText()  # customers.address (single qualifiedName in rule)

        # Parse WHERE condition(s): supports single or AND-chained conditions
        join_conditions = self._parse_condition_pairs(ctx.condition())
        source_fk = join_conditions[0]["left"] if join_conditions else ""
        target_pk = join_conditions[0]["right"] if join_conditions else ""

        # Parse target location: customers.address -> target_entity=customers, embedded_name=address
        target_parts = target_location.split(".")
        target_entity = target_parts[0] if target_parts else target_location
        embedded_name = target_parts[1] if len(target_parts) > 1 else source_entity

        # Parse field list: properties to embed
        properties, nested = self._parse_unnest_field_list(
            ctx.unnestFieldList(), SMILE_SpecificParser)

        self.operations.append(Operation(OpType.NEST, NestParams(
            source=source_entity,       # source entity to embed (address)
            target=target_entity,       # target entity (customers)
            alias=embedded_name,        # embedded field name (address)
            properties=properties,      # properties to embed (street, city)
            nested=nested,              # nested objects
            source_fk=source_fk,        # first join condition left (address.customer_id)
            target_pk=target_pk,        # first join condition right (customers.customer_id)
            join_conditions=join_conditions,  # all join conditions
        ), original_keyword="NEST"))

    def enterUnnest(self, ctx):
        # New syntax: UNNEST qualifiedName COLON unnestFieldList AS identifier (WITH unnestCarryList)?
        # Example: UNNEST customers.address:street,city AS address WITH customers.customer_id TO address.customer_id
        # Example with multiple carry fields:
        #   UNNEST customers.employment:position AS employment
        #       WITH customers.customer_id TO employment.customer_id, customers.dept_id TO employment.dept_id
        #   - WITH clause: copy fields from source to new table (can carry multiple fields)
        source_path = ctx.qualifiedName().getText()  # customers.address (single qualifiedName in unnest rule)
        target_name = ctx.identifier().getText()  # address (identifier after AS)

        # Parse carry fields (WITH clause is optional)
        carry_fields = []
        if ctx.unnestCarryList():
            for carry_field in ctx.unnestCarryList().unnestCarryField():
                # unnestCarryField has two qualifiedName: source AS target
                source_field = carry_field.qualifiedName(0).getText()  # customers.customer_id
                target_field = carry_field.qualifiedName(1).getText()  # address.customer_id
                # Extract just the field name from target path
                target_parts = target_field.split(".")
                field_name = target_parts[-1] if target_parts else target_field
                carry_fields.append({
                    "source": source_field,      # customers.customer_id
                    "target": target_field,      # address.customer_id
                    "field_name": field_name     # customer_id
                })

        # Parse field list: recursively separate properties and nested objects
        properties, nested = self._parse_unnest_field_list(
            ctx.unnestFieldList(), SMILE_SpecificParser)

        self.operations.append(Operation(OpType.UNNEST, UnnestParams(
            source_path=source_path,
            properties=properties,  # Regular properties ['street', 'city']
            nested=nested,          # Nested objects [{'name': 'company', 'properties': [...], 'nested': [...]}]
            target=target_name,
            carry_fields=carry_fields,  # List of fields to copy from source to new table
        ), original_keyword="UNNEST"))

    # ADD operations - each has its own method
    def enterAdd_property(self, ctx):
        self.operations.append(Operation(OpType.ADD_PROPERTY, AddPropertyParams(
            name=ctx.identifier(0).getText(),
            entity=ctx.identifier(1).getText() if len(ctx.identifier()) > 1 else None,
            clauses=self._parse_property_clauses(ctx.propertyClause()),
        )))

    def enterAdd_foreign_key(self, ctx):
        # ADD_FOREIGN_KEY entity.field REFERENCES table(column)
        # Supports explicit entity.field syntax: ADD_FOREIGN_KEY address.customer_id REFERENCES customers(customer_id)
        qualified_name = ctx.qualifiedName().getText()
        parts = qualified_name.split(".")
        if len(parts) == 2:
            entity_name = parts[0]
            field_name = parts[1]
        else:
            entity_name = None
            field_name = qualified_name

        identifiers = ctx.identifier()
        self.operations.append(Operation(OpType.ADD_FOREIGN_KEY, AddForeignKeyParams(
            entity=entity_name,
            field_name=field_name,
            target_table=identifiers[0].getText(),
            target_column=identifiers[1].getText(),
            clauses=self._parse_reference_clauses(ctx.constraintClause()),
        ), original_keyword="ADD_FOREIGN_KEY"))

    def enterAdd_embedded(self, ctx):
        self.operations.append(Operation(OpType.ADD_EMBEDDED, AddEmbeddedParams(
            name=ctx.identifier(0).getText(),
            entity=ctx.identifier(1).getText(),
            clauses=self._parse_embedded_clauses(ctx.embeddedClause()),
        )))

    def enterAdd_entity(self, ctx):
        identifiers = ctx.identifier()
        params = AddEntityParams(
            name=identifiers[0].getText(),
            clauses=self._parse_entity_clauses(ctx.entityClause()),
        )
        # FROM source TO target (EDGE entity / relationship type)
        if len(identifiers) >= 3:
            params.source_entity = identifiers[1].getText()
            params.target_entity = identifiers[2].getText()
        # WITH CARDINALITY
        if ctx.cardinalityType():
            params.cardinality = ctx.cardinalityType().getText()
        self.operations.append(Operation(OpType.ADD_ENTITY, params))

    def enterAdd_primary_key(self, ctx):
        # New syntax supports: ADD_PRIMARY_KEY address.address_id AS String
        data_type = ctx.dataType().getText() if ctx.dataType() else None
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        # Entity priority: explicit TO clause > entity from qualifiedName path
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.ADD_KEY, AddKeyParams(
            key_type=KeyType.PRIMARY,
            key_columns=key_columns,
            data_type=data_type,
            entity=entity_name,
            clauses=self._parse_key_clauses(ctx.keyClause()),
        ), original_keyword="ADD_PRIMARY_KEY"))

    def enterAdd_unique_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.ADD_KEY, AddKeyParams(
            key_type=KeyType.UNIQUE,
            key_columns=key_columns,
            entity=entity_name,
            clauses=self._parse_key_clauses(ctx.keyClause()),
        )))

    def enterAdd_partition_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.ADD_KEY, AddKeyParams(
            key_type=KeyType.PARTITION,
            key_columns=key_columns,
            entity=entity_name,
            clauses=self._parse_key_clauses(ctx.keyClause()),
        )))

    def enterAdd_clustering_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.ADD_KEY, AddKeyParams(
            key_type=KeyType.CLUSTERING,
            key_columns=key_columns,
            entity=entity_name,
            clauses=self._parse_key_clauses(ctx.keyClause()),
        )))

    def enterAdd_label(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation(OpType.ADD_LABEL, AddLabelParams(
            label=identifiers[0].getText(),
            entity=identifiers[1].getText() if len(identifiers) > 1 else None,
        )))

    # DELETE operations
    def enterDelete_property(self, ctx):
        self.operations.append(Operation(OpType.DELETE_PROPERTY, DeletePropertyParams(
            target=ctx.qualifiedName().getText(),
        )))

    def enterDelete_foreign_key(self, ctx):
        self.operations.append(Operation(OpType.DELETE_FOREIGN_KEY, DeleteForeignKeyParams(
            reference=ctx.qualifiedName().getText(),
        ), original_keyword="DELETE_FOREIGN_KEY"))

    def enterDelete_embedded(self, ctx):
        self.operations.append(Operation(OpType.DELETE_EMBEDDED, DeleteEmbeddedParams(
            embedded=ctx.qualifiedName().getText(),
        )))

    def enterDelete_entity(self, ctx):
        self.operations.append(Operation(OpType.DELETE_ENTITY, DeleteEntityParams(
            name=ctx.identifier().getText(),
        )))

    def enterDelete_primary_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.DELETE_KEY, DeleteKeyParams(
            key_type=KeyType.PRIMARY,
            key_columns=key_columns,
            entity=entity_name,
        )))

    def enterDelete_unique_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.DELETE_KEY, DeleteKeyParams(
            key_type=KeyType.UNIQUE,
            key_columns=key_columns,
            entity=entity_name,
        )))

    def enterDelete_partition_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.DELETE_KEY, DeleteKeyParams(
            key_type=KeyType.PARTITION,
            key_columns=key_columns,
            entity=entity_name,
        )))

    def enterDelete_clustering_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.DELETE_KEY, DeleteKeyParams(
            key_type=KeyType.CLUSTERING,
            key_columns=key_columns,
            entity=entity_name,
        )))

    def enterDelete_label(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation(OpType.DELETE_LABEL, DeleteLabelParams(
            label=identifiers[0].getText(),
            entity=identifiers[1].getText() if len(identifiers) > 1 else None,
        )))

    # RENAME operations
    def enterRename_property(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation(OpType.RENAME_PROPERTY, RenamePropertyParams(
            old_name=identifiers[0].getText(),
            new_name=identifiers[1].getText() if len(identifiers) > 1 else None,
            entity=identifiers[2].getText() if len(identifiers) > 2 else None,
        ), original_keyword="RENAME_PROPERTY"))

    def enterRename_entity(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation(OpType.RENAME_ENTITY, RenameEntityParams(
            old_name=identifiers[0].getText(),
            new_name=identifiers[1].getText() if len(identifiers) > 1 else None,
        )))

    # Simple operations
    def enterCopy_property(self, ctx):
        identifiers = ctx.identifier()
        property_name = identifiers[0].getText()
        source_entity = identifiers[1].getText()
        target_entity = identifiers[2].getText()
        self.operations.append(Operation(OpType.COPY_PROPERTY, CopyPropertyParams(
            source=f"{source_entity}.{property_name}",
            target=f"{target_entity}.{property_name}",
        ), original_keyword="COPY_PROPERTY"))

    def enterCopy_entity(self, ctx):
        identifiers = ctx.identifier()
        params = CopyEntityParams(
            source=identifiers[0].getText(),
            target=identifiers[1].getText(),
        )
        if len(identifiers) >= 4:
            params.source_entity = identifiers[2].getText()
            params.target_entity = identifiers[3].getText()
        self.operations.append(Operation(OpType.COPY_ENTITY, params, original_keyword="COPY_ENTITY"))

    def enterMove_property(self, ctx):
        identifiers = ctx.identifier()
        property_name = identifiers[0].getText()
        source_entity = identifiers[1].getText()
        target_entity = identifiers[2].getText()
        self.operations.append(Operation(OpType.MOVE_PROPERTY, MovePropertyParams(
            source=f"{source_entity}.{property_name}",
            target=f"{target_entity}.{property_name}",
        ), original_keyword="MOVE_PROPERTY"))

    def enterMerge(self, ctx):
        self.operations.append(Operation(OpType.MERGE, MergeParams(
            source1=ctx.identifier(0).getText(),
            source2=ctx.identifier(1).getText(),
            target=ctx.identifier(2).getText(),
            alias=ctx.identifier(3).getText() if len(ctx.identifier()) > 3 else None,
        )))

    def enterSplit(self, ctx):
        # New syntax: SPLIT identifier INTO splitPart (SEMICOLON splitPart)+
        # Vertical partitioning - divides one entity into multiple separate entities
        # Example: SPLIT customers INTO customers:customer_id, first_name, last_name, age; customer_tag:customer_id, tags
        #   Before: customers { customer_id, first_name, last_name, age, tags[] }
        #   After:  customers { customer_id, first_name, last_name, age }
        #          customer_tag { customer_id, tags[] }
        source_entity = ctx.identifier().getText()
        split_parts = ctx.splitPart() if isinstance(ctx.splitPart(), list) else [ctx.splitPart()]

        parts = []
        for part in split_parts:
            part_name = part.identifier().getText()
            part_fields = [id.getText() for id in part.identifierList().identifier()]
            parts.append({
                "name": part_name,
                "fields": part_fields
            })

        self.operations.append(Operation(OpType.SPLIT, SplitParams(
            source=source_entity,
            parts=parts,
        ), original_keyword="SPLIT"))

    def enterCast_property(self, ctx):
        self.operations.append(Operation(OpType.CAST_PROPERTY, CastPropertyParams(
            target=ctx.qualifiedName().getText(),
            type=ctx.dataType().getText(),
        ), original_keyword="CAST_PROPERTY"))

    def enterCast_constraint(self, ctx):
        ct = ctx.constraintKeyType()
        if ct.PRIMARY():
            constraint_type = "PRIMARY_KEY"
        elif ct.UNIQUE():
            constraint_type = "UNIQUE_KEY"
        elif ct.PARTITION():
            constraint_type = "PARTITION_KEY"
        elif ct.NODE():
            constraint_type = "NODE_KEY"
        elif ct.DOCUMENT_ID():
            constraint_type = "DOCUMENT_ID"
        elif ct.CLUSTERING():
            constraint_type = "CLUSTERING_KEY"
        else:
            raise ValueError(f"Unknown constraint type in CAST_CONSTRAINT: {ct.getText()}")
        self.operations.append(Operation(OpType.CAST_CONSTRAINT, CastConstraintParams(
            target=ctx.qualifiedName().getText(),
            constraint_type=constraint_type,
        ), original_keyword="CAST_CONSTRAINT"))

    def enterCast_entity(self, ctx):
        self.operations.append(Operation(OpType.CAST_ENTITY, CastEntityParams(
            target=ctx.identifier().getText(),
            entity_kind=ctx.databaseType().getText().upper(),
        ), original_keyword="CAST_ENTITY"))

    def enterRecard(self, ctx):
        self.operations.append(Operation(OpType.RECARD, RecardParams(
            target=ctx.qualifiedName().getText(),
            cardinality=ctx.cardinalityType().getText(),
        ), original_keyword="RECARD"))

    def enterTransform(self, ctx):
        name = ctx.identifier().getText()
        target_ctx = ctx.transformTarget()

        if isinstance(target_ctx, SMILE_SpecificParser.TransformToRelationshipContext):
            params = TransformParams(
                name=name,
                target_type="RELATIONSHIP",
                source_entity=target_ctx.identifier(0).getText(),
                target_entity=target_ctx.identifier(1).getText(),
            )
            if target_ctx.cardinalityType():
                params.cardinality = target_ctx.cardinalityType().getText()
            self.operations.append(Operation(OpType.TRANSFORM, params, original_keyword="TRANSFORM"))
        else:
            self.operations.append(Operation(OpType.TRANSFORM, TransformParams(
                name=name,
                target_type="ENTITY",
            ), original_keyword="TRANSFORM"))




# ==============================================================================
# SMILE_Generalized Listener - For SMILE_Generalized.g4
# ==============================================================================

class SMILEGeneralizedListener(SMILE_GeneralizedListener, BaseSMILEListener):
    """
    Listener for SMILE_Generalized.g4 grammar.

    Uses generalized keywords like ADD, DELETE, RENAME with type parameters.
    Reuses helper methods from BaseSMILEListener for common parsing logic.
    """

    def __init__(self):
        BaseSMILEListener.__init__(self)

    # Header parsing (same for all versions)
    def enterMigrationDecl(self, ctx):
        self.context.is_evolution = False
        self.context.name = ctx.identifier().getText()
        self.context.version = ctx.version().getText()

    def enterEvolutionDecl(self, ctx):
        self.context.is_evolution = True
        self.context.name = ctx.identifier().getText()
        self.context.version = ctx.version().getText()

    def enterUsingDecl(self, ctx):
        self.context.schema_name = ctx.identifier().getText()
        self.context.schema_version = ctx.version(0).getText()
        if len(ctx.version()) > 1:
            self.context.target_schema_version = ctx.version(1).getText()

    def enterFromToDecl(self, ctx):
        self.context.source_db_type = ctx.databaseType(0).getText()
        self.context.target_db_type = ctx.databaseType(1).getText()

    # Structure operations
    def enterFlatten_gen(self, ctx):
        # New syntax: FLATTEN qualifiedName
        # Flattens nested object fields into parent table (reduce depth by 1)
        # Example: FLATTEN customers.address
        #   Before: customers { name: { first_name, last_name }, age }
        #   After:  customers { name_first_name, name_last_name, age }
        self.operations.append(Operation(OpType.FLATTEN, FlattenParams(
            source=ctx.qualifiedName().getText(),
        ), original_keyword="FLATTEN"))

    def enterUnflatten_gen(self, ctx):
        # UNFLATTEN - Combine flat fields into nested object (reverse of FLATTEN)
        # Example: UNFLATTEN customers:first_name, last_name AS name
        #   Before: customers { first_name, last_name, age }
        #   After:  customers { name: { first_name, last_name }, age }
        entity = ctx.identifier(0).getText()  # customers
        fields = [id.getText() for id in ctx.identifierList().identifier()]  # [first_name, last_name]
        nested_name = ctx.identifier(1).getText()  # name
        self.operations.append(Operation(OpType.UNFLATTEN, UnflattenParams(
            entity=entity,
            fields=fields,
            nested_name=nested_name,
        ), original_keyword="UNFLATTEN"))

    def enterUnwind_gen(self, ctx):
        source = ctx.qualifiedName().getText()
        target = ctx.identifier().getText() if ctx.identifier() else None

        if target:
            # Mode 1: Create new table - UNWIND customers.tags[] INTO customer_tag
            self.operations.append(Operation(OpType.UNWIND, UnwindParams(
                mode="create_table",
                source=source,
                target=target,
            ), original_keyword="UNWIND"))
        else:
            # Mode 2: Expand in place - UNWIND customer_tag.value
            self.operations.append(Operation(OpType.UNWIND, UnwindParams(
                mode="expand_in_place",
                source=source,
            ), original_keyword="UNWIND"))

    def enterWind_gen(self, ctx):
        # WIND - Convert scalar property back to array (reverse of UNWIND)
        # Syntax: WIND customer_tag.tags
        # Cross-entity movement is handled by MERGE, not WIND.
        source = ctx.qualifiedName().getText()  # customer_tag.tags
        self.operations.append(Operation(OpType.WIND, WindParams(
            source=source,
        ), original_keyword="WIND"))

    def enterNest_gen(self, ctx):
        # Syntax: NEST identifier COLON unnestFieldList IN qualifiedName WHERE condition
        # Example: NEST address:street,city IN customers.address WHERE address.customer_id = customers.customer_id
        # Example: NEST address:street,city IN customers.address WHERE address.customer_id = customers.customer_id AND address.dept_id = customers.dept_id
        source_entity = ctx.identifier().getText()  # address
        target_location = ctx.qualifiedName().getText()  # customers.address (single qualifiedName in rule)

        # Parse WHERE condition(s): supports single or AND-chained conditions
        join_conditions = self._parse_condition_pairs(ctx.condition())
        source_fk = join_conditions[0]["left"] if join_conditions else ""
        target_pk = join_conditions[0]["right"] if join_conditions else ""

        # Parse target location: customers.address -> target_entity=customers, embedded_name=address
        target_parts = target_location.split(".")
        target_entity = target_parts[0] if target_parts else target_location
        embedded_name = target_parts[1] if len(target_parts) > 1 else source_entity

        # Parse field list: properties to embed
        properties, nested = self._parse_unnest_field_list(
            ctx.unnestFieldList(), SMILE_GeneralizedParser)

        self.operations.append(Operation(OpType.NEST, NestParams(
            source=source_entity,       # source entity to embed (address)
            target=target_entity,       # target entity (customers)
            alias=embedded_name,        # embedded field name (address)
            properties=properties,      # properties to embed (street, city)
            nested=nested,              # nested objects
            source_fk=source_fk,        # first join condition left (address.customer_id)
            target_pk=target_pk,        # first join condition right (customers.customer_id)
            join_conditions=join_conditions,  # all join conditions
        ), original_keyword="NEST"))

    def enterUnnest_gen(self, ctx):
        # New syntax: UNNEST qualifiedName COLON unnestFieldList AS identifier (WITH unnestCarryList)?
        # Example: UNNEST customers.address:street,city AS address WITH customers.customer_id TO address.customer_id
        # Example with multiple carry fields:
        #   UNNEST customers.employment:position AS employment
        #       WITH customers.customer_id TO employment.customer_id, customers.dept_id TO employment.dept_id
        #   - WITH clause: copy fields from source to new table (can carry multiple fields)
        source_path = ctx.qualifiedName().getText()  # customers.address (single qualifiedName in unnest_gen rule)
        target_name = ctx.identifier().getText()  # address (identifier after AS)

        # Parse carry fields (WITH clause is optional)
        carry_fields = []
        if ctx.unnestCarryList():
            for carry_field in ctx.unnestCarryList().unnestCarryField():
                # unnestCarryField has two qualifiedName: source AS target
                source_field = carry_field.qualifiedName(0).getText()  # customers.customer_id
                target_field = carry_field.qualifiedName(1).getText()  # address.customer_id
                # Extract just the field name from target path
                target_parts = target_field.split(".")
                field_name = target_parts[-1] if target_parts else target_field
                carry_fields.append({
                    "source": source_field,      # customers.customer_id
                    "target": target_field,      # address.customer_id
                    "field_name": field_name     # customer_id
                })

        # Parse field list: recursively separate properties and nested objects
        properties, nested = self._parse_unnest_field_list(
            ctx.unnestFieldList(), SMILE_GeneralizedParser)

        self.operations.append(Operation(OpType.UNNEST, UnnestParams(
            source_path=source_path,
            properties=properties,  # Regular properties ['street', 'city']
            nested=nested,          # Nested objects [{'name': 'company', 'properties': [...], 'nested': [...]}]
            target=target_name,
            carry_fields=carry_fields,  # List of fields to copy from source to new table
        ), original_keyword="UNNEST"))

    # ADD operations - same internal structure as original SMILE
    def enterPropertyAdd(self, ctx):
        self.operations.append(Operation(OpType.ADD_PROPERTY, AddPropertyParams(
            name=ctx.identifier(0).getText(),
            entity=ctx.identifier(1).getText() if len(ctx.identifier()) > 1 else None,
            clauses=self._parse_property_clauses(ctx.propertyClause()),
        )))

    def enterForeignKeyAdd(self, ctx):
        # ADD FOREIGN KEY entity.field REFERENCES table(column)
        # Supports explicit entity.field syntax: ADD FOREIGN KEY address.customer_id REFERENCES customers(customer_id)
        qualified_name = ctx.qualifiedName().getText()
        parts = qualified_name.split(".")
        if len(parts) == 2:
            entity_name = parts[0]
            field_name = parts[1]
        else:
            entity_name = None
            field_name = qualified_name

        identifiers = ctx.identifier()
        self.operations.append(Operation(OpType.ADD_FOREIGN_KEY, AddForeignKeyParams(
            entity=entity_name,
            field_name=field_name,
            target_table=identifiers[0].getText(),
            target_column=identifiers[1].getText(),
            clauses=self._parse_reference_clauses(ctx.constraintClause()),
        ), original_keyword="ADD FOREIGN KEY"))

    def enterEmbeddedAdd(self, ctx):
        self.operations.append(Operation(OpType.ADD_EMBEDDED, AddEmbeddedParams(
            name=ctx.identifier(0).getText(),
            entity=ctx.identifier(1).getText(),
            clauses=self._parse_embedded_clauses(ctx.embeddedClause()),
        )))

    def enterEntityAdd(self, ctx):
        identifiers = ctx.identifier()
        params = AddEntityParams(
            name=identifiers[0].getText(),
            clauses=self._parse_entity_clauses(ctx.entityClause()),
        )
        # FROM source TO target (EDGE entity / relationship type)
        if len(identifiers) >= 3:
            params.source_entity = identifiers[1].getText()
            params.target_entity = identifiers[2].getText()
        # WITH CARDINALITY
        if ctx.cardinalityType():
            params.cardinality = ctx.cardinalityType().getText()
        self.operations.append(Operation(OpType.ADD_ENTITY, params))

    def enterKeyAdd(self, ctx):
        # New syntax: keyType? KEY qualifiedName (AS dataType)? (TO identifier)?
        # Supports explicit entity.field syntax: ADD KEY address.address_id AS String
        key_type = ctx.keyType().getText() if ctx.keyType() else "PRIMARY"  # Default to PRIMARY
        data_type = ctx.dataType().getText() if ctx.dataType() else None
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        # Entity priority: explicit TO clause > entity from qualifiedName path
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        # Build original keyword: ADD [keyType] KEY
        original_kw = "ADD " + (key_type + " " if key_type != "PRIMARY" else "") + "KEY"
        self.operations.append(Operation(OpType.ADD_KEY, AddKeyParams(
            key_type=key_type,
            key_columns=key_columns,
            data_type=data_type,
            entity=entity_name,
            clauses=self._parse_key_clauses(ctx.keyClause()),
        ), original_keyword=original_kw))

    def enterLabelAdd(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation(OpType.ADD_LABEL, AddLabelParams(
            label=identifiers[0].getText(),
            entity=identifiers[1].getText() if len(identifiers) > 1 else None,
        )))

    # DELETE operations
    def enterPropertyDelete(self, ctx):
        self.operations.append(Operation(OpType.DELETE_PROPERTY, DeletePropertyParams(
            target=ctx.qualifiedName().getText(),
        )))

    def enterForeignKeyDelete(self, ctx):
        self.operations.append(Operation(OpType.DELETE_FOREIGN_KEY, DeleteForeignKeyParams(
            reference=ctx.qualifiedName().getText(),
        ), original_keyword="DELETE FOREIGN KEY"))

    def enterEmbeddedDelete(self, ctx):
        self.operations.append(Operation(OpType.DELETE_EMBEDDED, DeleteEmbeddedParams(
            embedded=ctx.qualifiedName().getText(),
        )))

    def enterEntityDelete(self, ctx):
        self.operations.append(Operation(OpType.DELETE_ENTITY, DeleteEntityParams(
            name=ctx.identifier().getText(),
        )))

    def enterKeyDelete(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation(OpType.DELETE_KEY, DeleteKeyParams(
            key_type=ctx.keyType().getText(),
            key_columns=key_columns,
            entity=entity_name,
        )))

    def enterLabelDelete(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation(OpType.DELETE_LABEL, DeleteLabelParams(
            label=identifiers[0].getText(),
            entity=identifiers[1].getText() if len(identifiers) > 1 else None,
        )))

    # RENAME operations
    def enterPropertyRename(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation(OpType.RENAME_PROPERTY, RenamePropertyParams(
            old_name=identifiers[0].getText(),
            new_name=identifiers[1].getText() if len(identifiers) > 1 else None,
            entity=identifiers[2].getText() if len(identifiers) > 2 else None,
        ), original_keyword="RENAME PROPERTY"))

    def enterEntityRename(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation(OpType.RENAME_ENTITY, RenameEntityParams(
            old_name=identifiers[0].getText(),
            new_name=identifiers[1].getText() if len(identifiers) > 1 else None,
        )))

    # Simple operations
    def enterCopy_gen(self, ctx):
        if ctx.entityCopy():
            ec = ctx.entityCopy()
            identifiers = ec.identifier()
            params = CopyEntityParams(
                source=identifiers[0].getText(),
                target=identifiers[1].getText(),
            )
            if len(identifiers) >= 4:
                params.source_entity = identifiers[2].getText()
                params.target_entity = identifiers[3].getText()
            self.operations.append(Operation(OpType.COPY_ENTITY, params, original_keyword="COPY ENTITY"))
        else:
            pc = ctx.propertyCopy()
            identifiers = pc.identifier()
            property_name = identifiers[0].getText()
            source_entity = identifiers[1].getText()
            target_entity = identifiers[2].getText()
            self.operations.append(Operation(OpType.COPY_PROPERTY, CopyPropertyParams(
                source=f"{source_entity}.{property_name}",
                target=f"{target_entity}.{property_name}",
            ), original_keyword="COPY PROPERTY"))

    def enterMove_gen(self, ctx):
        identifiers = ctx.identifier()
        property_name = identifiers[0].getText()
        source_entity = identifiers[1].getText()
        target_entity = identifiers[2].getText()
        self.operations.append(Operation(OpType.MOVE_PROPERTY, MovePropertyParams(
            source=f"{source_entity}.{property_name}",
            target=f"{target_entity}.{property_name}",
        ), original_keyword="MOVE PROPERTY"))

    def enterMerge_gen(self, ctx):
        self.operations.append(Operation(OpType.MERGE, MergeParams(
            source1=ctx.identifier(0).getText(),
            source2=ctx.identifier(1).getText(),
            target=ctx.identifier(2).getText(),
            alias=ctx.identifier(3).getText() if len(ctx.identifier()) > 3 else None,
        )))

    def enterSplit_gen(self, ctx):
        # New syntax: SPLIT identifier INTO splitPartGen (SEMICOLON splitPartGen)+
        # Vertical partitioning - divides one entity into multiple separate entities
        # Example: SPLIT customers INTO customers:customer_id, first_name, last_name, age; customer_tag:customer_id, tags
        #   Before: customers { customer_id, first_name, last_name, age, tags[] }
        #   After:  customers { customer_id, first_name, last_name, age }
        #          customer_tag { customer_id, tags[] }
        source_entity = ctx.identifier().getText()
        split_parts = ctx.splitPartGen() if isinstance(ctx.splitPartGen(), list) else [ctx.splitPartGen()]

        parts = []
        for part in split_parts:
            part_name = part.identifier().getText()
            part_fields = [id.getText() for id in part.identifierList().identifier()]
            parts.append({
                "name": part_name,
                "fields": part_fields
            })

        self.operations.append(Operation(OpType.SPLIT, SplitParams(
            source=source_entity,
            parts=parts,
        ), original_keyword="SPLIT"))

    def enterCast_gen(self, ctx):
        if ctx.constraintCast():
            cc = ctx.constraintCast()
            ct = cc.constraintKeyType()
            if ct.PRIMARY():
                constraint_type = "PRIMARY_KEY"
            elif ct.UNIQUE():
                constraint_type = "UNIQUE_KEY"
            elif ct.PARTITION():
                constraint_type = "PARTITION_KEY"
            elif ct.NODE():
                constraint_type = "NODE_KEY"
            elif ct.DOCUMENT_ID():
                constraint_type = "DOCUMENT_ID"
            elif ct.CLUSTERING():
                constraint_type = "CLUSTERING_KEY"
            else:
                raise ValueError(f"Unknown constraint type in CAST CONSTRAINT: {ct.getText()}")
            self.operations.append(Operation(OpType.CAST_CONSTRAINT, CastConstraintParams(
                target=cc.qualifiedName().getText(),
                constraint_type=constraint_type,
            ), original_keyword="CAST CONSTRAINT"))
        elif ctx.entityCast():
            ec = ctx.entityCast()
            self.operations.append(Operation(OpType.CAST_ENTITY, CastEntityParams(
                target=ec.identifier().getText(),
                entity_kind=ec.databaseType().getText().upper(),
            ), original_keyword="CAST ENTITY"))
        else:
            pc = ctx.propertyCast()
            self.operations.append(Operation(OpType.CAST_PROPERTY, CastPropertyParams(
                target=pc.qualifiedName().getText(),
                type=pc.dataType().getText(),
            ), original_keyword="CAST PROPERTY"))

    def enterRecard_gen(self, ctx):
        self.operations.append(Operation(OpType.RECARD, RecardParams(
            target=ctx.qualifiedName().getText(),
            cardinality=ctx.cardinalityType().getText(),
        ), original_keyword="RECARD"))

    def enterTransform_gen(self, ctx):
        name = ctx.identifier().getText()
        target_ctx = ctx.transformTarget()

        if isinstance(target_ctx, SMILE_GeneralizedParser.TransformToRelationshipContext):
            params = TransformParams(
                name=name,
                target_type="RELATIONSHIP",
                source_entity=target_ctx.identifier(0).getText(),
                target_entity=target_ctx.identifier(1).getText(),
            )
            if target_ctx.cardinalityType():
                params.cardinality = target_ctx.cardinalityType().getText()
            self.operations.append(Operation(OpType.TRANSFORM, params, original_keyword="TRANSFORM"))
        else:
            self.operations.append(Operation(OpType.TRANSFORM, TransformParams(
                name=name,
                target_type="ENTITY",
            ), original_keyword="TRANSFORM"))


