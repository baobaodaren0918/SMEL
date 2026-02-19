"""
SMEL Listeners - Parsers for all three SMEL grammar variants

This module provides listener implementations for:
1. SMEL_Specific.g4 - Specific operations version
2. SMEL_Pauschalisiert.g4 - Generalized operations version
3. SMEL.g4 - Original version (legacy)

All listeners share common logic through the BaseSMELListener class.
"""
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))

from grammar.specific.SMEL_SpecificListener import SMEL_SpecificListener
from grammar.specific.SMEL_SpecificParser import SMEL_SpecificParser
from grammar.pauschalisiert.SMEL_PauschalisiertListener import SMEL_PauschalisiertListener
from grammar.pauschalisiert.SMEL_PauschalisiertParser import SMEL_PauschalisiertParser


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
    original_keyword: str = ""  # Original keyword from source (e.g., "FLATTEN_PS", "RENAME_ATTRIBUTE")


class BaseSMELListener:
    """
    Base class with shared parsing logic for all SMEL variants.

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

    def _parse_attribute_clauses(self, clause_list):
        """Parse attribute clauses: WITH TYPE, WITH DEFAULT, NOT NULL.
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
        Returns list of dicts, e.g. [{'type': 'ATTRIBUTES', 'attributes': ['id', 'name']}, {'type': 'KEY', 'key_name': 'id'}]
        """
        result = []
        for clause in clause_list:
            if hasattr(clause, 'withAttributesClause') and clause.withAttributesClause():
                ids = clause.withAttributesClause().identifierList()
                result.append({'type': 'ATTRIBUTES', 'attributes': [id.getText() for id in ids.identifier()]})
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

    def _parse_variation_clauses(self, clause_list):
        """Parse variation clauses"""
        result = {}
        for clause in clause_list:
            if hasattr(clause, 'withAttributesClause') and clause.withAttributesClause():
                ids = clause.withAttributesClause().identifierList()
                result['attributes'] = [id.getText() for id in ids.identifier()]
            elif hasattr(clause, 'withRelationshipsClause') and clause.withRelationshipsClause():
                ids = clause.withRelationshipsClause().identifierList()
                result['relationships'] = [id.getText() for id in ids.identifier()]
            elif hasattr(clause, 'withCountClause') and clause.withCountClause():
                result['count'] = int(clause.withCountClause().INTEGER_LITERAL().getText())
        return result

    def _parse_reltype_clauses(self, clause_list):
        """Parse relationship type clauses"""
        result = {}
        for clause in clause_list:
            if hasattr(clause, 'withPropertiesClause') and clause.withPropertiesClause():
                ids = clause.withPropertiesClause().identifierList()
                result['properties'] = [id.getText() for id in ids.identifier()]
            elif hasattr(clause, 'withCardinalityClause') and clause.withCardinalityClause():
                result['cardinality'] = clause.withCardinalityClause().cardinalityType().getText()
        return result

    def _parse_unnest_field_list(self, field_list_ctx, parser_module):
        """
        Recursively parse UNNEST field list to separate attributes and nested objects.

        Grammar structure:
          unnestFieldList: unnestField (COMMA unnestField)*;
          unnestField: identifier                                    # AttributeField
                     | identifier LBRACE unnestFieldList RBRACE      # NestedField

        Args:
            field_list_ctx: The unnestFieldList context from parser
            parser_module: Either SMEL_SpecificParser or SMEL_PauschalisiertParser

        Returns:
            tuple: (attributes, nested)
                   - attributes: list of simple attribute names ['position', 'name']
                   - nested: list of nested object dicts [{'name': 'company', 'children': {...}}]
        """
        attributes = []
        nested = []

        for field_ctx in field_list_ctx.unnestField():
            if isinstance(field_ctx, parser_module.AttributeFieldContext):
                # Simple attribute: position, name, street, city
                attributes.append(field_ctx.identifier().getText())
            elif isinstance(field_ctx, parser_module.NestedFieldContext):
                # Nested object: company{name, address{street, city}}
                nested_name = field_ctx.identifier().getText()
                # Recursively parse nested field list
                nested_field_list = field_ctx.unnestFieldList()
                child_attrs, child_nested = self._parse_unnest_field_list(nested_field_list, parser_module)
                nested.append({
                    'name': nested_name,
                    'attributes': child_attrs,
                    'nested': child_nested
                })

        return attributes, nested


# ==============================================================================
# SMEL_Specific Listener - For SMEL_Specific.g4
# ==============================================================================

class SMELSpecificListener(SMEL_SpecificListener, BaseSMELListener):
    """
    Listener for SMEL_Specific.g4 grammar.

    Uses specific keywords like ADD_ATTRIBUTE, DELETE_ENTITY, RENAME_ATTRIBUTE.
    """

    def __init__(self):
        BaseSMELListener.__init__(self)

    # Header parsing (same for all versions)
    def enterMigrationDecl(self, ctx):
        self.context.name = ctx.identifier().getText()
        self.context.version = ctx.version().getText()

    def enterFromToDecl(self, ctx):
        self.context.source_db_type = ctx.databaseType(0).getText()
        self.context.target_db_type = ctx.databaseType(1).getText()

    # Structure operations
    def enterFlatten(self, ctx):
        # New syntax: FLATTEN qualifiedName
        # Flattens nested object fields into parent table (reduce depth by 1)
        # Example: FLATTEN person.name
        #   Before: person { name: { vorname, nachname }, age }
        #   After:  person { name_vorname, name_nachname, age }
        self.operations.append(Operation("FLATTEN", {
            "source": ctx.qualifiedName().getText()
        }, original_keyword="FLATTEN"))

    def enterUnflatten(self, ctx):
        # UNFLATTEN - Combine flat fields into nested object (reverse of FLATTEN)
        # Example: UNFLATTEN person(vorname, nachname) AS name
        #   Before: person { vorname, nachname, age }
        #   After:  person { name: { vorname, nachname }, age }
        entity = ctx.identifier(0).getText()  # person
        fields = [id.getText() for id in ctx.identifierList().identifier()]  # [vorname, nachname]
        nested_name = ctx.identifier(1).getText()  # name
        self.operations.append(Operation("UNFLATTEN", {
            "entity": entity,
            "fields": fields,
            "nested_name": nested_name
        }, original_keyword="UNFLATTEN"))

    def enterUnwind(self, ctx):
        source = ctx.qualifiedName().getText()
        target = ctx.identifier().getText() if ctx.identifier() else None

        if target:
            # Mode 1: Create new table - UNWIND person.tags[] INTO person_tag
            self.operations.append(Operation("UNWIND", {
                "mode": "create_table",
                "source": source,
                "target": target
            }, original_keyword="UNWIND"))
        else:
            # Mode 2: Expand in place - UNWIND person_tag.value
            self.operations.append(Operation("UNWIND", {
                "mode": "expand_in_place",
                "source": source
            }, original_keyword="UNWIND"))

    def enterWind(self, ctx):
        # WIND - Convert scalar attribute back to array (reverse of UNWIND)
        # Syntax: WIND person_tag.tags
        # Cross-entity movement is handled by MERGE, not WIND.
        source = ctx.qualifiedName().getText()  # person_tag.tags
        self.operations.append(Operation("WIND", {
            "source": source
        }, original_keyword="WIND"))

    def enterNest(self, ctx):
        # Syntax: NEST identifier COLON unnestFieldList IN qualifiedName WHERE condition (WITH DELETION)?
        # Example: NEST address:street,city IN person.address WHERE address.person_id = person.person_id WITH DELETION
        # Example: NEST address:street,city IN person.address WHERE address.person_id = person.person_id AND address.dept_id = person.dept_id
        source_entity = ctx.identifier().getText()  # address
        target_location = ctx.qualifiedName().getText()  # person.address (single qualifiedName in rule)
        with_deletion = ctx.DELETION() is not None  # WITH DELETION option

        # Parse WHERE condition(s): supports single or AND-chained conditions
        join_conditions = self._parse_condition_pairs(ctx.condition())
        source_fk = join_conditions[0]["left"] if join_conditions else ""
        target_pk = join_conditions[0]["right"] if join_conditions else ""

        # Parse target location: person.address -> target_entity=person, embedded_name=address
        target_parts = target_location.split(".")
        target_entity = target_parts[0] if target_parts else target_location
        embedded_name = target_parts[1] if len(target_parts) > 1 else source_entity

        # Parse field list: attributes to embed
        attributes, nested = self._parse_unnest_field_list(
            ctx.unnestFieldList(), SMEL_SpecificParser)

        self.operations.append(Operation("NEST", {
            "source": source_entity,       # source entity to embed (address)
            "target": target_entity,       # target entity (person)
            "alias": embedded_name,        # embedded field name (address)
            "attributes": attributes,      # attributes to embed (street, city)
            "nested": nested,              # nested objects
            "source_fk": source_fk,        # first join condition left (address.person_id)
            "target_pk": target_pk,        # first join condition right (person.person_id)
            "join_conditions": join_conditions,  # all join conditions
            "with_deletion": with_deletion # delete source after embedding
        }, original_keyword="NEST"))

    def enterUnnest(self, ctx):
        # New syntax: UNNEST qualifiedName COLON unnestFieldList AS identifier (WITH unnestCarryList)?
        # Example: UNNEST person.address:street,city AS address WITH person.person_id TO address.person_id
        # Example with multiple carry fields:
        #   UNNEST person.employment:position AS employment
        #       WITH person.person_id TO employment.person_id, person.dept_id TO employment.dept_id
        #   - WITH clause: copy fields from source to new table (can carry multiple fields)
        source_path = ctx.qualifiedName().getText()  # person.address (single qualifiedName in unnest rule)
        target_name = ctx.identifier().getText()  # address (identifier after AS)

        # Parse carry fields (WITH clause is optional)
        carry_fields = []
        if ctx.unnestCarryList():
            for carry_field in ctx.unnestCarryList().unnestCarryField():
                # unnestCarryField has two qualifiedName: source AS target
                source_field = carry_field.qualifiedName(0).getText()  # person.person_id
                target_field = carry_field.qualifiedName(1).getText()  # address.person_id
                # Extract just the field name from target path
                target_parts = target_field.split(".")
                field_name = target_parts[-1] if target_parts else target_field
                carry_fields.append({
                    "source": source_field,      # person.person_id
                    "target": target_field,      # address.person_id
                    "field_name": field_name     # person_id
                })

        # Parse field list: recursively separate attributes and nested objects
        attributes, nested = self._parse_unnest_field_list(
            ctx.unnestFieldList(), SMEL_SpecificParser)

        self.operations.append(Operation("UNNEST", {
            "source_path": source_path,
            "attributes": attributes,  # Regular attributes ['street', 'city']
            "nested": nested,          # Nested objects [{'name': 'company', 'attributes': [...], 'nested': [...]}]
            "target": target_name,
            "carry_fields": carry_fields  # List of fields to copy from source to new table
        }, original_keyword="UNNEST"))

    # ADD operations - each has its own method
    def enterAdd_attribute(self, ctx):
        self.operations.append(Operation("ADD_ATTRIBUTE", {
            "name": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText() if len(ctx.identifier()) > 1 else None,
            "clauses": self._parse_attribute_clauses(ctx.attributeClause())
        }))

    def enterAdd_reference(self, ctx):
        # New syntax: ADD_REFERENCE entity.field REFERENCES table(column)
        # Supports explicit entity.field syntax: ADD_REFERENCE address.person_id REFERENCES person(person_id)
        qualified_name = ctx.qualifiedName().getText()
        parts = qualified_name.split(".")
        if len(parts) == 2:
            entity_name = parts[0]
            field_name = parts[1]
        else:
            entity_name = None
            field_name = qualified_name

        identifiers = ctx.identifier()
        self.operations.append(Operation("ADD_REFERENCE", {
            "entity": entity_name,
            "field_name": field_name,
            "target_table": identifiers[0].getText(),
            "target_column": identifiers[1].getText(),
            "clauses": self._parse_reference_clauses(ctx.referenceClause())
        }, original_keyword="ADD_REFERENCE"))

    def enterAdd_embedded(self, ctx):
        self.operations.append(Operation("ADD_EMBEDDED", {
            "name": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText(),
            "clauses": self._parse_embedded_clauses(ctx.embeddedClause())
        }))

    def enterAdd_entity(self, ctx):
        self.operations.append(Operation("ADD_ENTITY", {
            "name": ctx.identifier().getText(),
            "clauses": self._parse_entity_clauses(ctx.entityClause())
        }))

    def enterAdd_primary_key(self, ctx):
        # New syntax supports: ADD_PRIMARY_KEY address.address_id AS String
        data_type = ctx.dataType().getText() if ctx.dataType() else None
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        # Entity priority: explicit TO clause > entity from qualifiedName path
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("ADD_KEY", {
            "key_type": "PRIMARY",
            "key_columns": key_columns,
            "data_type": data_type,
            "entity": entity_name,
            "clauses": self._parse_key_clauses(ctx.keyClause())
        }, original_keyword="ADD_PRIMARY_KEY"))

    def enterAdd_foreign_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("ADD_KEY", {
            "key_type": "FOREIGN",
            "key_columns": key_columns,
            "entity": entity_name,
            "clauses": self._parse_key_clauses(ctx.keyClause())
        }, original_keyword="ADD_FOREIGN_KEY"))

    def enterAdd_unique_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("ADD_KEY", {
            "key_type": "UNIQUE",
            "key_columns": key_columns,
            "entity": entity_name,
            "clauses": self._parse_key_clauses(ctx.keyClause())
        }))

    def enterAdd_partition_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("ADD_KEY", {
            "key_type": "PARTITION",
            "key_columns": key_columns,
            "entity": entity_name,
            "clauses": self._parse_key_clauses(ctx.keyClause())
        }))

    def enterAdd_clustering_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("ADD_KEY", {
            "key_type": "CLUSTERING",
            "key_columns": key_columns,
            "entity": entity_name,
            "clauses": self._parse_key_clauses(ctx.keyClause())
        }))

    def enterAdd_variation(self, ctx):
        self.operations.append(Operation("ADD_VARIATION", {
            "variation_id": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText(),
            "clauses": self._parse_variation_clauses(ctx.variationClause())
        }))

    def enterAdd_reltype(self, ctx):
        self.operations.append(Operation("ADD_RELTYPE", {
            "name": ctx.identifier(0).getText(),
            "source": ctx.identifier(1).getText(),
            "target": ctx.identifier(2).getText(),
            "clauses": self._parse_reltype_clauses(ctx.relTypeClause())
        }))

    def enterAdd_index(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        columns = [id.getText() for id in ctx.identifierList().identifier()]
        self.operations.append(Operation("ADD_INDEX", {
            "name": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None,
            "columns": columns
        }))

    def enterAdd_label(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("ADD_LABEL", {
            "label": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    # DELETE operations
    def enterDelete_attribute(self, ctx):
        self.operations.append(Operation("DELETE_ATTRIBUTE", {
            "target": ctx.qualifiedName().getText()
        }))

    def enterDelete_reference(self, ctx):
        self.operations.append(Operation("DELETE_REFERENCE", {
            "reference": ctx.qualifiedName().getText()
        }))

    def enterDelete_embedded(self, ctx):
        self.operations.append(Operation("DELETE_EMBEDDED", {
            "embedded": ctx.qualifiedName().getText()
        }))

    def enterDelete_entity(self, ctx):
        self.operations.append(Operation("DELETE_ENTITY", {
            "name": ctx.identifier().getText()
        }))

    def enterDelete_primary_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("DELETE_KEY", {
            "key_type": "PRIMARY",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterDelete_foreign_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("DELETE_KEY", {
            "key_type": "FOREIGN",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterDelete_unique_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("DELETE_KEY", {
            "key_type": "UNIQUE",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterDelete_partition_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("DELETE_KEY", {
            "key_type": "PARTITION",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterDelete_clustering_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("DELETE_KEY", {
            "key_type": "CLUSTERING",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterDelete_variation(self, ctx):
        self.operations.append(Operation("DELETE_VARIATION", {
            "variation_id": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText()
        }))

    def enterDelete_reltype(self, ctx):
        self.operations.append(Operation("DELETE_RELTYPE", {
            "name": ctx.identifier().getText()
        }))

    def enterDelete_index(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("DELETE_INDEX", {
            "name": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    def enterDelete_label(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("DELETE_LABEL", {
            "label": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    # REMOVE operations (non-destructive constraint removal)
    def enterRemove_index(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("REMOVE_INDEX", {
            "name": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    def enterRemove_unique_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("REMOVE_KEY", {
            "key_type": "UNIQUE",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterRemove_foreign_key(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("REMOVE_KEY", {
            "key_type": "FOREIGN",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterRemove_label(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("REMOVE_LABEL", {
            "label": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    def enterRemove_variation(self, ctx):
        self.operations.append(Operation("REMOVE_VARIATION", {
            "variation_id": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText()
        }))

    # RENAME operations
    def enterRename_attribute(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("RENAME", {
            "old_name": identifiers[0].getText(),
            "new_name": identifiers[1].getText() if len(identifiers) > 1 else None,
            "entity": identifiers[2].getText() if len(identifiers) > 2 else None
        }, original_keyword="RENAME_ATTRIBUTE"))

    def enterRename_entity(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("RENAME_ENTITY", {
            "old_name": identifiers[0].getText(),
            "new_name": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    def enterRename_reltype(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("RENAME_RELTYPE", {
            "old_name": identifiers[0].getText(),
            "new_name": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    # Simple operations
    def enterCopy(self, ctx):
        self.operations.append(Operation("COPY", {
            "source": ctx.qualifiedName(0).getText(),
            "target": ctx.qualifiedName(1).getText()
        }, original_keyword="COPY"))

    def enterMove(self, ctx):
        self.operations.append(Operation("MOVE", {
            "source": ctx.qualifiedName(0).getText(),
            "target": ctx.qualifiedName(1).getText()
        }))

    def enterMerge(self, ctx):
        self.operations.append(Operation("MERGE", {
            "source1": ctx.identifier(0).getText(),
            "source2": ctx.identifier(1).getText(),
            "target": ctx.identifier(2).getText(),
            "alias": ctx.identifier(3).getText() if len(ctx.identifier()) > 3 else None
        }))

    def enterSplit(self, ctx):
        # New syntax: SPLIT identifier INTO splitPart (SEMICOLON splitPart)+
        # Vertical partitioning - divides one entity into multiple separate entities
        # Example: SPLIT person INTO person:person_id, vorname, nachname, age; person_tag:person_id, tags
        #   Before: person { person_id, vorname, nachname, age, tags[] }
        #   After:  person { person_id, vorname, nachname, age }
        #          person_tag { person_id, tags[] }
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

        self.operations.append(Operation("SPLIT", {
            "source": source_entity,
            "parts": parts
        }, original_keyword="SPLIT"))

    def enterCast(self, ctx):
        self.operations.append(Operation("CAST", {
            "target": ctx.qualifiedName().getText(),
            "type": ctx.dataType().getText()
        }, original_keyword="CAST"))

    def enterLinking(self, ctx):
        self.operations.append(Operation("LINKING", {
            "source": ctx.qualifiedName().getText(),
            "target": ctx.identifier().getText()
        }))


# ==============================================================================
# SMEL_Pauschalisiert Listener - For SMEL_Pauschalisiert.g4
# ==============================================================================

class SMELPauschalisiertListener(SMEL_PauschalisiertListener, BaseSMELListener):
    """
    Listener for SMEL_Pauschalisiert.g4 grammar.

    Uses generalized keywords like ADD_PS, DELETE_PS, RENAME_PS with type parameters.
    Reuses helper methods from BaseSMELListener for common parsing logic.
    """

    def __init__(self):
        BaseSMELListener.__init__(self)

    # Header parsing (same for all versions)
    def enterMigrationDecl(self, ctx):
        self.context.name = ctx.identifier().getText()
        self.context.version = ctx.version().getText()

    def enterFromToDecl(self, ctx):
        self.context.source_db_type = ctx.databaseType(0).getText()
        self.context.target_db_type = ctx.databaseType(1).getText()

    # Structure operations
    def enterFlatten_ps(self, ctx):
        # New syntax: FLATTEN_PS qualifiedName
        # Flattens nested object fields into parent table (reduce depth by 1)
        # Example: FLATTEN_PS person.name
        #   Before: person { name: { vorname, nachname }, age }
        #   After:  person { name_vorname, name_nachname, age }
        self.operations.append(Operation("FLATTEN", {
            "source": ctx.qualifiedName().getText()
        }, original_keyword="FLATTEN_PS"))

    def enterUnflatten_ps(self, ctx):
        # UNFLATTEN_PS - Combine flat fields into nested object (reverse of FLATTEN)
        # Example: UNFLATTEN_PS person(vorname, nachname) AS name
        #   Before: person { vorname, nachname, age }
        #   After:  person { name: { vorname, nachname }, age }
        entity = ctx.identifier(0).getText()  # person
        fields = [id.getText() for id in ctx.identifierList().identifier()]  # [vorname, nachname]
        nested_name = ctx.identifier(1).getText()  # name
        self.operations.append(Operation("UNFLATTEN", {
            "entity": entity,
            "fields": fields,
            "nested_name": nested_name
        }, original_keyword="UNFLATTEN_PS"))

    def enterUnwind_ps(self, ctx):
        source = ctx.qualifiedName().getText()
        target = ctx.identifier().getText() if ctx.identifier() else None

        if target:
            # Mode 1: Create new table - UNWIND_PS person.tags[] INTO person_tag
            self.operations.append(Operation("UNWIND", {
                "mode": "create_table",
                "source": source,
                "target": target
            }, original_keyword="UNWIND_PS"))
        else:
            # Mode 2: Expand in place - UNWIND_PS person_tag.value
            self.operations.append(Operation("UNWIND", {
                "mode": "expand_in_place",
                "source": source
            }, original_keyword="UNWIND_PS"))

    def enterWind_ps(self, ctx):
        # WIND_PS - Convert scalar attribute back to array (reverse of UNWIND)
        # Syntax: WIND_PS person_tag.tags
        # Cross-entity movement is handled by MERGE_PS, not WIND_PS.
        source = ctx.qualifiedName().getText()  # person_tag.tags
        self.operations.append(Operation("WIND", {
            "source": source
        }, original_keyword="WIND_PS"))

    def enterNest_ps(self, ctx):
        # Syntax: NEST_PS identifier COLON unnestFieldList IN qualifiedName WHERE condition (WITH DELETION)?
        # Example: NEST_PS address:street,city IN person.address WHERE address.person_id = person.person_id WITH DELETION
        # Example: NEST_PS address:street,city IN person.address WHERE address.person_id = person.person_id AND address.dept_id = person.dept_id
        source_entity = ctx.identifier().getText()  # address
        target_location = ctx.qualifiedName().getText()  # person.address (single qualifiedName in rule)
        with_deletion = ctx.DELETION() is not None  # WITH DELETION option

        # Parse WHERE condition(s): supports single or AND-chained conditions
        join_conditions = self._parse_condition_pairs(ctx.condition())
        source_fk = join_conditions[0]["left"] if join_conditions else ""
        target_pk = join_conditions[0]["right"] if join_conditions else ""

        # Parse target location: person.address -> target_entity=person, embedded_name=address
        target_parts = target_location.split(".")
        target_entity = target_parts[0] if target_parts else target_location
        embedded_name = target_parts[1] if len(target_parts) > 1 else source_entity

        # Parse field list: attributes to embed
        attributes, nested = self._parse_unnest_field_list(
            ctx.unnestFieldList(), SMEL_PauschalisiertParser)

        self.operations.append(Operation("NEST", {
            "source": source_entity,       # source entity to embed (address)
            "target": target_entity,       # target entity (person)
            "alias": embedded_name,        # embedded field name (address)
            "attributes": attributes,      # attributes to embed (street, city)
            "nested": nested,              # nested objects
            "source_fk": source_fk,        # first join condition left (address.person_id)
            "target_pk": target_pk,        # first join condition right (person.person_id)
            "join_conditions": join_conditions,  # all join conditions
            "with_deletion": with_deletion # delete source after embedding
        }, original_keyword="NEST_PS"))

    def enterUnnest_ps(self, ctx):
        # New syntax: UNNEST_PS qualifiedName COLON unnestFieldList AS identifier (WITH unnestCarryList)?
        # Example: UNNEST_PS person.address:street,city AS address WITH person.person_id TO address.person_id
        # Example with multiple carry fields:
        #   UNNEST_PS person.employment:position AS employment
        #       WITH person.person_id TO employment.person_id, person.dept_id TO employment.dept_id
        #   - WITH clause: copy fields from source to new table (can carry multiple fields)
        source_path = ctx.qualifiedName().getText()  # person.address (single qualifiedName in unnest_ps rule)
        target_name = ctx.identifier().getText()  # address (identifier after AS)

        # Parse carry fields (WITH clause is optional)
        carry_fields = []
        if ctx.unnestCarryList():
            for carry_field in ctx.unnestCarryList().unnestCarryField():
                # unnestCarryField has two qualifiedName: source AS target
                source_field = carry_field.qualifiedName(0).getText()  # person.person_id
                target_field = carry_field.qualifiedName(1).getText()  # address.person_id
                # Extract just the field name from target path
                target_parts = target_field.split(".")
                field_name = target_parts[-1] if target_parts else target_field
                carry_fields.append({
                    "source": source_field,      # person.person_id
                    "target": target_field,      # address.person_id
                    "field_name": field_name     # person_id
                })

        # Parse field list: recursively separate attributes and nested objects
        attributes, nested = self._parse_unnest_field_list(
            ctx.unnestFieldList(), SMEL_PauschalisiertParser)

        self.operations.append(Operation("UNNEST", {
            "source_path": source_path,
            "attributes": attributes,  # Regular attributes ['street', 'city']
            "nested": nested,          # Nested objects [{'name': 'company', 'attributes': [...], 'nested': [...]}]
            "target": target_name,
            "carry_fields": carry_fields  # List of fields to copy from source to new table
        }, original_keyword="UNNEST_PS"))

    # ADD_PS operations - same internal structure as original SMEL
    def enterAttributeAdd(self, ctx):
        self.operations.append(Operation("ADD_ATTRIBUTE", {
            "name": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText() if len(ctx.identifier()) > 1 else None,
            "clauses": self._parse_attribute_clauses(ctx.attributeClause())
        }))

    def enterReferenceAdd(self, ctx):
        # New syntax: REFERENCE entity.field REFERENCES table(column)
        # Supports explicit entity.field syntax: ADD_PS REFERENCE address.person_id REFERENCES person(person_id)
        qualified_name = ctx.qualifiedName().getText()
        parts = qualified_name.split(".")
        if len(parts) == 2:
            entity_name = parts[0]
            field_name = parts[1]
        else:
            entity_name = None
            field_name = qualified_name

        identifiers = ctx.identifier()
        self.operations.append(Operation("ADD_REFERENCE", {
            "entity": entity_name,
            "field_name": field_name,
            "target_table": identifiers[0].getText(),
            "target_column": identifiers[1].getText(),
            "clauses": self._parse_reference_clauses(ctx.referenceClause())
        }, original_keyword="ADD_PS REFERENCE"))

    def enterEmbeddedAdd(self, ctx):
        self.operations.append(Operation("ADD_EMBEDDED", {
            "name": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText(),
            "clauses": self._parse_embedded_clauses(ctx.embeddedClause())
        }))

    def enterEntityAdd(self, ctx):
        self.operations.append(Operation("ADD_ENTITY", {
            "name": ctx.identifier().getText(),
            "clauses": self._parse_entity_clauses(ctx.entityClause())
        }))

    def enterKeyAdd(self, ctx):
        # New syntax: keyType? KEY qualifiedName (AS dataType)? (TO identifier)?
        # Supports explicit entity.field syntax: ADD_PS KEY address.address_id AS String
        key_type = ctx.keyType().getText() if ctx.keyType() else "PRIMARY"  # Default to PRIMARY
        data_type = ctx.dataType().getText() if ctx.dataType() else None
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        # Entity priority: explicit TO clause > entity from qualifiedName path
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        # Build original keyword: ADD_PS [keyType] KEY
        original_kw = "ADD_PS " + (key_type + " " if key_type != "PRIMARY" else "") + "KEY"
        self.operations.append(Operation("ADD_KEY", {
            "key_type": key_type,
            "key_columns": key_columns,
            "data_type": data_type,
            "entity": entity_name,
            "clauses": self._parse_key_clauses(ctx.keyClause())
        }, original_keyword=original_kw))

    def enterVariationAdd(self, ctx):
        self.operations.append(Operation("ADD_VARIATION", {
            "variation_id": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText(),
            "clauses": self._parse_variation_clauses(ctx.variationClause())
        }))

    def enterRelTypeAdd(self, ctx):
        self.operations.append(Operation("ADD_RELTYPE", {
            "name": ctx.identifier(0).getText(),
            "source": ctx.identifier(1).getText(),
            "target": ctx.identifier(2).getText(),
            "clauses": self._parse_reltype_clauses(ctx.relTypeClause())
        }))

    def enterIndexAdd(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        columns = [id.getText() for id in ctx.identifierList().identifier()]
        self.operations.append(Operation("ADD_INDEX", {
            "name": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None,
            "columns": columns
        }))

    def enterLabelAdd(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("ADD_LABEL", {
            "label": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    # DELETE_PS operations
    def enterAttributeDelete(self, ctx):
        self.operations.append(Operation("DELETE_ATTRIBUTE", {
            "target": ctx.qualifiedName().getText()
        }))

    def enterReferenceDelete(self, ctx):
        self.operations.append(Operation("DELETE_REFERENCE", {
            "reference": ctx.qualifiedName().getText()
        }))

    def enterEmbeddedDelete(self, ctx):
        self.operations.append(Operation("DELETE_EMBEDDED", {
            "embedded": ctx.qualifiedName().getText()
        }))

    def enterEntityDelete(self, ctx):
        self.operations.append(Operation("DELETE_ENTITY", {
            "name": ctx.identifier().getText()
        }))

    def enterKeyDelete(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("DELETE_KEY", {
            "key_type": ctx.keyType().getText(),
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterVariationDelete(self, ctx):
        self.operations.append(Operation("DELETE_VARIATION", {
            "variation_id": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText()
        }))

    def enterRelTypeDelete(self, ctx):
        self.operations.append(Operation("DELETE_RELTYPE", {
            "name": ctx.identifier().getText()
        }))

    def enterIndexDelete(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("DELETE_INDEX", {
            "name": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    def enterLabelDelete(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("DELETE_LABEL", {
            "label": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    # REMOVE_PS operations
    def enterIndexRemove(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("REMOVE_INDEX", {
            "name": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    def enterUniqueKeyRemove(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("REMOVE_KEY", {
            "key_type": "UNIQUE",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterForeignKeyRemove(self, ctx):
        key_columns, entity_from_path = self._parse_key_columns(ctx.keyColumns())
        entity_name = ctx.identifier().getText() if ctx.identifier() else entity_from_path
        self.operations.append(Operation("REMOVE_KEY", {
            "key_type": "FOREIGN",
            "key_columns": key_columns,
            "entity": entity_name
        }))

    def enterLabelRemove(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("REMOVE_LABEL", {
            "label": identifiers[0].getText(),
            "entity": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    def enterVariationRemove(self, ctx):
        self.operations.append(Operation("REMOVE_VARIATION", {
            "variation_id": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText()
        }))

    # RENAME_PS operations
    def enterAttributeRename(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("RENAME", {
            "old_name": identifiers[0].getText(),
            "new_name": identifiers[1].getText() if len(identifiers) > 1 else None,
            "entity": identifiers[2].getText() if len(identifiers) > 2 else None
        }, original_keyword="RENAME_PS ATTRIBUTE"))

    def enterEntityRename(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("RENAME_ENTITY", {
            "old_name": identifiers[0].getText(),
            "new_name": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    def enterRelTypeRename(self, ctx):
        identifiers = ctx.identifier() if isinstance(ctx.identifier(), list) else [ctx.identifier()]
        self.operations.append(Operation("RENAME_RELTYPE", {
            "old_name": identifiers[0].getText(),
            "new_name": identifiers[1].getText() if len(identifiers) > 1 else None
        }))

    # Simple operations with _PS suffix
    def enterCopy_ps(self, ctx):
        self.operations.append(Operation("COPY", {
            "source": ctx.qualifiedName(0).getText(),
            "target": ctx.qualifiedName(1).getText()
        }, original_keyword="COPY_PS"))

    def enterMove_ps(self, ctx):
        self.operations.append(Operation("MOVE", {
            "source": ctx.qualifiedName(0).getText(),
            "target": ctx.qualifiedName(1).getText()
        }))

    def enterMerge_ps(self, ctx):
        self.operations.append(Operation("MERGE", {
            "source1": ctx.identifier(0).getText(),
            "source2": ctx.identifier(1).getText(),
            "target": ctx.identifier(2).getText(),
            "alias": ctx.identifier(3).getText() if len(ctx.identifier()) > 3 else None
        }))

    def enterSplit_ps(self, ctx):
        # New syntax: SPLIT_PS identifier INTO splitPartPs (SEMICOLON splitPartPs)+
        # Vertical partitioning - divides one entity into multiple separate entities
        # Example: SPLIT_PS person INTO person:person_id, vorname, nachname, age; person_tag:person_id, tags
        #   Before: person { person_id, vorname, nachname, age, tags[] }
        #   After:  person { person_id, vorname, nachname, age }
        #          person_tag { person_id, tags[] }
        source_entity = ctx.identifier().getText()
        split_parts = ctx.splitPartPs() if isinstance(ctx.splitPartPs(), list) else [ctx.splitPartPs()]

        parts = []
        for part in split_parts:
            part_name = part.identifier().getText()
            part_fields = [id.getText() for id in part.identifierList().identifier()]
            parts.append({
                "name": part_name,
                "fields": part_fields
            })

        self.operations.append(Operation("SPLIT", {
            "source": source_entity,
            "parts": parts
        }, original_keyword="SPLIT_PS"))

    def enterCast_ps(self, ctx):
        self.operations.append(Operation("CAST", {
            "target": ctx.qualifiedName().getText(),
            "type": ctx.dataType().getText()
        }, original_keyword="CAST_PS"))

    def enterLinking_ps(self, ctx):
        self.operations.append(Operation("LINKING", {
            "source": ctx.qualifiedName().getText(),
            "target": ctx.identifier().getText()
        }))
