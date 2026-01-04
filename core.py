"""
SMEL Core - Shared logic for Schema Migration & Evolution Language

This module contains the core components shared by main.py (CLI) and web_server.py (Web UI):
- SMELParserListener: Parse SMEL files
- SchemaTransformer: Execute transformation operations
- parse_smel(): Parse SMEL file and return operations
- db_to_dict(): Convert Database to JSON-serializable dict
"""
import sys
import copy
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener
from grammar.SMELLexer import SMELLexer
from grammar.SMELParser import SMELParser
from grammar.SMELListener import SMELListener
from Schema.unified_meta_schema import (
    Database, DatabaseType, EntityType, Attribute, Key, KeyType,
    Reference, Embedded, Aggregate, Cardinality, PrimitiveDataType, PrimitiveType,
    StructuralVariation, RelationshipType
)
from Schema.adapters import PostgreSQLAdapter, MongoDBAdapter

# Path constants
SCHEMA_DIR = Path(__file__).parent / "Schema"
TESTS_DIR = Path(__file__).parent / "tests"

# Equivalent attribute names for validation
EQUIVALENT_ATTRS = {('msg_id', '_id'), ('_id', 'msg_id')}


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


class SMELParserListener(SMELListener):
    """Parse SMEL file and extract operations."""

    def __init__(self):
        self.context = MigrationContext()
        self.operations: List[Operation] = []

    def enterMigrationDecl(self, ctx):
        self.context.name = ctx.identifier().getText()
        self.context.version = ctx.version().getText()

    def enterFromToDecl(self, ctx):
        self.context.source_db_type = ctx.databaseType(0).getText()
        self.context.target_db_type = ctx.databaseType(1).getText()

    def enterNest(self, ctx):
        self.operations.append(Operation("NEST", {
            "source": ctx.identifier(0).getText(),
            "target": ctx.identifier(1).getText(),
            "alias": ctx.identifier(2).getText(),
            "clauses": self._parse_nest_clauses(ctx.nestClause())
        }))

    def enterFlatten(self, ctx):
        self.operations.append(Operation("FLATTEN", {
            "source": ctx.qualifiedName().getText(),
            "target": ctx.identifier().getText(),
            "clauses": self._parse_flatten_clauses(ctx.flattenClause())
        }))

    def enterUnwind(self, ctx):
        self.operations.append(Operation("UNWIND", {
            "source": ctx.qualifiedName().getText(),
            "alias": ctx.identifier().getText(),
            "clauses": self._parse_unwind_clauses(ctx.unwindClause())
        }))

    # ========== ADD sub-rule handlers (Orion-style branching) ==========

    def enterAttributeAdd(self, ctx):
        """ADD ATTRIBUTE email TO Customer WITH TYPE String NOT NULL"""
        clauses = self._parse_attribute_clauses(ctx.attributeClause())
        self.operations.append(Operation("ADD_ATTRIBUTE", {
            "name": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText() if len(ctx.identifier()) > 1 else None,
            "clauses": clauses
        }))

    def enterReferenceAdd(self, ctx):
        """ADD REFERENCE customer_id TO Order WITH CARDINALITY ONE_TO_MANY"""
        clauses = self._parse_reference_clauses(ctx.referenceClause())
        self.operations.append(Operation("ADD_REFERENCE", {
            "reference": ctx.qualifiedName().getText(),
            "target": ctx.identifier().getText(),
            "clauses": clauses
        }))

    def enterEmbeddedAdd(self, ctx):
        """ADD EMBEDDED address TO Customer WITH CARDINALITY ONE_TO_ONE"""
        clauses = self._parse_embedded_clauses(ctx.embeddedClause())
        self.operations.append(Operation("ADD_EMBEDDED", {
            "name": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText(),
            "clauses": clauses
        }))

    def enterEntityAdd(self, ctx):
        """ADD ENTITY Product WITH ATTRIBUTES (id, name)"""
        clauses = self._parse_entity_clauses(ctx.entityClause())
        self.operations.append(Operation("ADD_ENTITY", {
            "name": ctx.identifier().getText(),
            "clauses": clauses
        }))

    # ========== DELETE sub-rule handlers (Orion-style branching) ==========

    def enterAttributeDelete(self, ctx):
        """DELETE ATTRIBUTE Customer.email"""
        self.operations.append(Operation("DELETE_ATTRIBUTE", {
            "target": ctx.qualifiedName().getText()
        }))

    def enterReferenceDelete(self, ctx):
        """DELETE REFERENCE Customer.order_id"""
        self.operations.append(Operation("DELETE_REFERENCE", {
            "reference": ctx.qualifiedName().getText()
        }))

    def enterEmbeddedDelete(self, ctx):
        """DELETE EMBEDDED Customer.address"""
        self.operations.append(Operation("DELETE_EMBEDDED", {
            "embedded": ctx.qualifiedName().getText()
        }))

    def enterEntityDelete(self, ctx):
        """DELETE ENTITY Customer"""
        self.operations.append(Operation("DELETE_ENTITY", {
            "name": ctx.identifier().getText()
        }))

    # ========== ADD sub-rule handlers for key, variation, relType ==========

    def enterKeyAdd(self, ctx):
        """ADD PRIMARY KEY id TO Customer"""
        self.operations.append(Operation("ADD_KEY", {
            "key_type": ctx.keyType().getText(),
            "key_name": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText() if len(ctx.identifier()) > 1 else None,
            "clauses": self._parse_key_clauses(ctx.keyClause())
        }))

    def enterVariationAdd(self, ctx):
        """ADD VARIATION v1 TO Customer WITH ATTRIBUTES (a, b)"""
        self.operations.append(Operation("ADD_VARIATION", {
            "variation_id": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText(),
            "clauses": self._parse_variation_clauses(ctx.variationClause())
        }))

    def enterRelTypeAdd(self, ctx):
        """ADD RELTYPE ACTED_IN FROM Actor TO Movie"""
        clauses = self._parse_reltype_clauses(ctx.relTypeClause())
        self.operations.append(Operation("ADD_RELTYPE", {
            "name": ctx.identifier(0).getText(),
            "source": ctx.identifier(1).getText(),
            "target": ctx.identifier(2).getText(),
            "clauses": clauses
        }))

    # ========== DROP sub-rule handlers ==========

    def enterKeyDrop(self, ctx):
        """DROP PRIMARY KEY id FROM Customer"""
        self.operations.append(Operation("DROP_KEY", {
            "key_type": ctx.keyType().getText(),
            "key_name": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText() if len(ctx.identifier()) > 1 else None
        }))

    def enterVariationDrop(self, ctx):
        """DROP VARIATION v1 FROM Customer"""
        self.operations.append(Operation("DROP_VARIATION", {
            "variation_id": ctx.identifier(0).getText(),
            "entity": ctx.identifier(1).getText()
        }))

    def enterRelTypeDrop(self, ctx):
        """DROP RELTYPE ACTED_IN"""
        self.operations.append(Operation("DROP_RELTYPE", {
            "name": ctx.identifier().getText()
        }))

    def enterUnnest(self, ctx):
        """UNNEST embedded FROM Parent [AS alias]"""
        clauses = []
        for c in ctx.unnestClause():
            if c.AS():
                clauses.append({"type": "AS", "alias": c.identifier().getText()})
            elif c.usingKeyClause():
                clauses.append({"type": "USING_KEY", "value": c.usingKeyClause().identifier().getText()})
        self.operations.append(Operation("UNNEST", {
            "embedded": ctx.identifier(0).getText(),
            "parent": ctx.identifier(1).getText(),
            "clauses": clauses
        }))

    # ========== RENAME sub-rule handlers ==========

    def enterFeatureRename(self, ctx):
        """RENAME oldName TO newName [IN Entity]"""
        self.operations.append(Operation("RENAME", {
            "old_name": ctx.identifier(0).getText(),
            "new_name": ctx.identifier(1).getText(),
            "entity": ctx.identifier(2).getText() if len(ctx.identifier()) > 2 else None
        }))

    def enterEntityRename(self, ctx):
        """RENAME ENTITY OldName TO NewName"""
        self.operations.append(Operation("RENAME_ENTITY", {
            "old_name": ctx.identifier(0).getText(),
            "new_name": ctx.identifier(1).getText()
        }))

    def enterRelTypeRename(self, ctx):
        """RENAME RELTYPE oldName TO newName"""
        self.operations.append(Operation("RENAME_RELTYPE", {
            "old_name": ctx.identifier(0).getText(),
            "new_name": ctx.identifier(1).getText()
        }))

    def enterCopy(self, ctx):
        """COPY source TO target"""
        self.operations.append(Operation("COPY", {
            "source": ctx.qualifiedName(0).getText(),
            "target": ctx.qualifiedName(1).getText()
        }))

    def enterMove(self, ctx):
        """MOVE source TO target"""
        self.operations.append(Operation("MOVE", {
            "source": ctx.qualifiedName(0).getText(),
            "target": ctx.qualifiedName(1).getText()
        }))

    def enterMerge(self, ctx):
        """MERGE A, B INTO C [AS alias]"""
        self.operations.append(Operation("MERGE", {
            "source1": ctx.identifier(0).getText(),
            "source2": ctx.identifier(1).getText(),
            "target": ctx.identifier(2).getText(),
            "alias": ctx.identifier(3).getText() if len(ctx.identifier()) > 3 else None
        }))

    def enterSplit(self, ctx):
        """SPLIT source INTO A, B"""
        self.operations.append(Operation("SPLIT", {
            "source": ctx.identifier(0).getText(),
            "target1": ctx.identifier(1).getText(),
            "target2": ctx.identifier(2).getText()
        }))


    def enterCast(self, ctx):
        """CAST Entity.field TO dataType"""
        self.operations.append(Operation("CAST", {
            "target": ctx.qualifiedName().getText(),
            "data_type": ctx.dataType().getText()
        }))

    def enterLinking(self, ctx):
        """LINKING source TO target"""
        self.operations.append(Operation("LINKING", {
            "source": ctx.qualifiedName().getText(),
            "target": ctx.identifier().getText()
        }))

    def enterExtract(self, ctx):
        """EXTRACT (a,b,c) FROM Entity INTO NewEntity [clauses]"""
        attrs = [id.getText() for id in ctx.identifierList().identifier()]
        clauses = self._parse_extract_clauses(ctx.extractClause())
        self.operations.append(Operation("EXTRACT", {
            "attributes": attrs,
            "source": ctx.identifier(0).getText(),
            "target": ctx.identifier(1).getText(),
            "clauses": clauses
        }))


    def _parse_attribute_clauses(self, clauses) -> List[Dict]:
        """Parse attributeClause: withTypeClause | withDefaultClause | notNullClause."""
        result = []
        for c in clauses:
            if c.withTypeClause():
                result.append({"type": "TYPE", "data_type": c.withTypeClause().dataType().getText()})
            elif c.withDefaultClause():
                result.append({"type": "DEFAULT", "value": c.withDefaultClause().literal().getText()})
            elif c.notNullClause():
                result.append({"type": "NOT_NULL"})
        return result

    def _parse_reference_clauses(self, clauses) -> List[Dict]:
        """Parse referenceClause: withCardinalityClause | usingKeyClause | whereClause."""
        result = []
        for c in clauses:
            if c.withCardinalityClause():
                result.append({"type": "CARDINALITY", "value": c.withCardinalityClause().cardinalityType().getText()})
            elif c.usingKeyClause():
                result.append({"type": "USING_KEY", "value": c.usingKeyClause().identifier().getText()})
            elif c.whereClause():
                result.append({"type": "WHERE", "condition": c.whereClause().condition().getText()})
        return result

    def _parse_embedded_clauses(self, clauses) -> List[Dict]:
        """Parse embeddedClause: withCardinalityClause | withStructureClause."""
        result = []
        for c in clauses:
            if c.withCardinalityClause():
                result.append({"type": "CARDINALITY", "value": c.withCardinalityClause().cardinalityType().getText()})
            elif c.withStructureClause():
                result.append({"type": "STRUCTURE",
                               "fields": [id.getText() for id in c.withStructureClause().identifierList().identifier()]})
        return result

    def _parse_entity_clauses(self, clauses) -> List[Dict]:
        """Parse entityClause: withAttributesClause | withKeyClause."""
        result = []
        for c in clauses:
            if c.withAttributesClause():
                result.append({"type": "ATTRIBUTES",
                               "attributes": [id.getText() for id in c.withAttributesClause().identifierList().identifier()]})
            elif c.withKeyClause():
                result.append({"type": "KEY", "key_name": c.withKeyClause().identifier().getText()})
        return result

    def _parse_extract_clauses(self, clauses) -> List[Dict]:
        """Parse EXTRACT operation clauses."""
        result = []
        for c in clauses:
            if c.generateKeyClause():
                gk = c.generateKeyClause()
                result.append({"type": "GENERATE_KEY", "key_name": gk.identifier(0).getText(),
                               "mode": "SERIAL" if gk.SERIAL() else "FROM",
                               "from_field": gk.identifier(1).getText() if gk.FROM() else None})
            elif c.addReferenceClause():
                result.append({"type": "ADD_REFERENCE", "ref_name": c.addReferenceClause().identifier(0).getText(),
                               "target": c.addReferenceClause().identifier(1).getText()})
        return result

    def _parse_reltype_clauses(self, clauses) -> List[Dict]:
        """Parse RELTYPE operation clauses."""
        result = []
        for c in clauses:
            if c.withPropertiesClause():
                result.append({"type": "PROPERTIES",
                               "properties": [id.getText() for id in c.withPropertiesClause().identifierList().identifier()]})
            elif c.withCardinalityClause():
                result.append({"type": "CARDINALITY", "value": c.withCardinalityClause().cardinalityType().getText()})
        return result

    def _parse_nest_clauses(self, clauses) -> List[Dict]:
        result = []
        for c in clauses:
            if c.withCardinalityClause():
                result.append({"type": "CARDINALITY", "value": c.withCardinalityClause().cardinalityType().getText()})
            elif c.usingKeyClause():
                result.append({"type": "USING_KEY", "value": c.usingKeyClause().identifier().getText()})
        return result

    def _parse_flatten_clauses(self, clauses) -> List[Dict]:
        return [{"type": "ADD_REFERENCE", "ref_name": c.addReferenceClause().identifier(0).getText(),
                 "target": c.addReferenceClause().identifier(1).getText()}
                for c in clauses if c.addReferenceClause()]

    def _parse_unwind_clauses(self, clauses) -> List[Dict]:
        result = []
        for c in clauses:
            if c.generateKeyClause():
                gk = c.generateKeyClause()
                result.append({"type": "GENERATE_KEY", "key_name": gk.identifier(0).getText(),
                               "mode": "SERIAL" if gk.SERIAL() else "FROM",
                               "from_field": gk.identifier(1).getText() if gk.FROM() else None})
            elif c.addReferenceClause():
                result.append({"type": "ADD_REFERENCE", "ref_name": c.addReferenceClause().identifier(0).getText(),
                               "target": c.addReferenceClause().identifier(1).getText()})
        return result

    def _parse_key_clauses(self, clauses) -> List[Dict]:
        result = []
        for c in clauses:
            if c.referencesClause():
                ref = c.referencesClause()
                result.append({"type": "REFERENCES", "target": ref.identifier().getText(),
                               "columns": [id.getText() for id in ref.identifierList().identifier()]})
            elif c.withColumnsClause():
                result.append({"type": "COLUMNS",
                               "columns": [id.getText() for id in c.withColumnsClause().identifierList().identifier()]})
        return result

    def _parse_variation_clauses(self, clauses) -> List[Dict]:
        result = []
        for c in clauses:
            if c.withAttributesClause():
                result.append({"type": "ATTRIBUTES",
                               "attributes": [id.getText() for id in c.withAttributesClause().identifierList().identifier()]})
            elif c.withRelationshipsClause():
                result.append({"type": "RELATIONSHIPS",
                               "relationships": [id.getText() for id in c.withRelationshipsClause().identifierList().identifier()]})
            elif c.withCountClause():
                result.append({"type": "COUNT", "count": int(c.withCountClause().INTEGER_LITERAL().getText())})
        return result


class SchemaTransformer:
    """Transform schema based on SMEL operations."""

    CARDINALITY_MAP = {
        "ONE_TO_ONE": Cardinality.ONE_TO_ONE,
        "ONE_TO_MANY": Cardinality.ONE_TO_MANY,
        "ZERO_TO_ONE": Cardinality.ZERO_TO_ONE,
        "ZERO_TO_MANY": Cardinality.ZERO_TO_MANY,
    }

    KEY_TYPE_MAP = {
        "PRIMARY": KeyType.PRIMARY,
        "UNIQUE": KeyType.UNIQUE,
        "FOREIGN": KeyType.FOREIGN,
        "PARTITION": KeyType.PARTITION,
        "CLUSTERING": KeyType.CLUSTERING,
    }

    def __init__(self, database: Database):
        self.database = copy.deepcopy(database)
        self.changes: List[str] = []

    def execute(self, operations: List[Operation]) -> Database:
        """Execute all operations and return transformed database."""
        for op in operations:
            handler = getattr(self, f"_handle_{op.op_type.lower()}", None)
            if handler:
                handler(op.params)
        return self.database

    def _handle_nest(self, params: Dict) -> None:
        source_name, target_name, alias = params["source"], params["target"], params["alias"]
        cardinality = Cardinality.ONE_TO_ONE
        for c in params.get("clauses", []):
            if c["type"] == "CARDINALITY":
                cardinality = self.CARDINALITY_MAP.get(c["value"], Cardinality.ONE_TO_ONE)

        source_entity = self.database.get_entity_type(source_name)
        target_entity = self.database.get_entity_type(target_name)
        if not source_entity or not target_entity:
            return

        fk_attr_names = {rel.ref_name for rel in source_entity.get_references()}
        embedded_entity = EntityType(en_name=alias)
        for attr in source_entity.attributes:
            if attr.attr_name not in fk_attr_names:
                embedded_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, False, attr.is_optional))

        self.database.add_entity_type(embedded_entity)
        target_entity.add_relationship(Embedded(aggr_name=alias, aggregates=alias, cardinality=cardinality,
                                                is_optional=not cardinality.is_required()))
        self.changes.append(f"NEST:{target_name}.{alias}")

        for rel in list(target_entity.relationships):
            if isinstance(rel, Reference) and rel.get_target_entity_name() == source_name:
                target_entity.remove_relationship(rel.ref_name)
                target_entity.remove_attribute(rel.ref_name)

    def _handle_flatten(self, params: Dict) -> None:
        source_path, target_name = params["source"], params["target"]
        parts = source_path.split(".")
        if len(parts) < 2:
            return

        parent_name, embedded_name = parts[0], parts[1].replace("[]", "")
        parent_entity = self.database.get_entity_type(parent_name)
        embedded_entity = self.database.get_entity_type(embedded_name)
        if not parent_entity or not embedded_entity:
            return

        new_entity = EntityType(en_name=target_name)
        for attr in embedded_entity.attributes:
            new_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, attr.is_key, attr.is_optional))

        if not new_entity.get_primary_key() and new_entity.attributes:
            pk_attr = new_entity.attributes[0]
            pk_attr.is_key = True
            key = Key(key_type=KeyType.PRIMARY)
            key.add_attribute(pk_attr)
            new_entity.add_key(key)

        self.database.add_entity_type(new_entity)
        self.changes.append(f"FLATTEN:{target_name}")

        for c in params.get("clauses", []):
            if c["type"] == "ADD_REFERENCE":
                parent_entity.add_attribute(
                    Attribute(c["ref_name"], PrimitiveDataType(PrimitiveType.INTEGER), False, True))
                parent_entity.add_relationship(Reference(ref_name=c["ref_name"], refs_to=c["target"],
                                                         cardinality=Cardinality.ONE_TO_ONE, is_optional=True))
                self.changes.append(f"ADD_REF:{parent_name}.{c['ref_name']}")

        parent_entity.remove_relationship(embedded_name)
        if target_name != embedded_name:
            self.database.remove_entity_type(embedded_name)

    def _handle_unwind(self, params: Dict) -> None:
        source_path, alias = params["source"], params["alias"]
        parts = source_path.split(".")
        if len(parts) < 2:
            return

        parent_name, embedded_name = parts[0], parts[1].replace("[]", "")
        parent_entity = self.database.get_entity_type(parent_name)
        embedded_entity = self.database.get_entity_type(embedded_name)
        if not parent_entity or not embedded_entity:
            return

        new_entity = EntityType(en_name=alias)
        pk_name, ref_clauses = None, []

        for c in params.get("clauses", []):
            if c["type"] == "GENERATE_KEY":
                pk_name = c["key_name"]
                if c["mode"] == "FROM" and c.get("from_field"):
                    src_attr = embedded_entity.get_attribute(c["from_field"])
                    pk_type = src_attr.data_type if src_attr else PrimitiveDataType(PrimitiveType.STRING)
                else:
                    pk_type = PrimitiveDataType(PrimitiveType.INTEGER)
                pk_attr = Attribute(pk_name, pk_type, True, False)
                new_entity.add_attribute(pk_attr)
                key = Key(key_type=KeyType.PRIMARY)
                key.add_attribute(pk_attr)
                new_entity.add_key(key)
            elif c["type"] == "ADD_REFERENCE":
                ref_clauses.append(c)

        for attr in embedded_entity.attributes:
            if attr.attr_name != pk_name:
                new_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, False, attr.is_optional))

        for c in ref_clauses:
            target_entity = self.database.get_entity_type(c["target"])
            fk_type = PrimitiveDataType(PrimitiveType.INTEGER)
            if target_entity:
                target_pk = target_entity.get_primary_key()
                if target_pk and target_pk.key_attributes:
                    fk_type = target_pk.key_attributes[0].data_type
            new_entity.add_attribute(Attribute(c["ref_name"], fk_type, False, False))
            new_entity.add_relationship(Reference(ref_name=c["ref_name"], refs_to=c["target"],
                                                  cardinality=Cardinality.ONE_TO_ONE, is_optional=False))
            self.changes.append(f"ADD_REF:{alias}.{c['ref_name']}")

        for rel in embedded_entity.relationships:
            new_entity.add_relationship(copy.deepcopy(rel))

        self.database.add_entity_type(new_entity)
        self.changes.append(f"UNWIND:{alias}")
        parent_entity.remove_relationship(embedded_name)
        if alias != embedded_name:
            self.database.remove_entity_type(embedded_name)

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
        parts = params["reference"].split(".")
        if len(parts) != 2:
            return
        entity = self.database.get_entity_type(parts[0])
        if entity:
            if not entity.get_attribute(parts[1]):
                entity.add_attribute(Attribute(parts[1], PrimitiveDataType(PrimitiveType.INTEGER), False, True))
            entity.add_relationship(Reference(ref_name=parts[1], refs_to=params["target"],
                                              cardinality=Cardinality.ONE_TO_ONE, is_optional=True))
            self.changes.append(f"ADD_REF:{parts[0]}.{parts[1]}")

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
                    "DATETIME": PrimitiveType.DATETIME, "TIMESTAMP": PrimitiveType.TIMESTAMP,
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

        new_entity = EntityType(en_name=name)

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
                key = Key(key_type=KeyType.PRIMARY)
                key.add_attribute(attr)
                new_entity.add_key(key)

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

    def _handle_add_key(self, params: Dict) -> None:
        entity_name = params.get("entity")
        key_name = params["key_name"]
        key_type = self.KEY_TYPE_MAP.get(params["key_type"], KeyType.PRIMARY)

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return

        attr = entity.get_attribute(key_name)
        if not attr:
            attr = Attribute(key_name, PrimitiveDataType(PrimitiveType.INTEGER), True, False)
            entity.add_attribute(attr)
        else:
            attr.is_key = True

        key = Key(key_type=key_type)
        key.add_attribute(attr)

        for c in params.get("clauses", []):
            if c["type"] == "REFERENCES" and key_type == KeyType.FOREIGN:
                key.referenced_entity = c["target"]
                key.referenced_attributes = c["columns"]
            elif c["type"] == "COLUMNS":
                for col_name in c["columns"]:
                    col_attr = entity.get_attribute(col_name)
                    if col_attr and col_attr not in key.key_attributes:
                        key.add_attribute(col_attr)

        entity.add_key(key)
        self.changes.append(f"ADD_KEY:{entity_name}.{key_name}")

    def _handle_drop_key(self, params: Dict) -> None:
        entity_name = params.get("entity")
        key_name = params["key_name"]
        key_type = self.KEY_TYPE_MAP.get(params["key_type"], KeyType.PRIMARY)

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            return

        for key in list(entity.keys):
            if key.key_type == key_type:
                for attr in key.key_attributes:
                    if attr.attr_name == key_name:
                        entity.keys.remove(key)
                        attr.is_key = False
                        self.changes.append(f"DROP_KEY:{entity_name}.{key_name}")
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

    def _handle_drop_variation(self, params: Dict) -> None:
        entity_name = params["entity"]
        variation_id = params["variation_id"]

        entity = self.database.get_entity_type(entity_name)
        if not entity:
            return

        for var in list(entity.variations):
            if var.variation_id == variation_id:
                entity.variations.remove(var)
                self.changes.append(f"DROP_VARIATION:{entity_name}.{variation_id}")
                return

    def _handle_unnest(self, params: Dict) -> None:
        """UNNEST: Extract embedded object back to standalone entity."""
        embedded_name = params["embedded"]
        parent_name = params["parent"]

        parent_entity = self.database.get_entity_type(parent_name)
        if not parent_entity:
            return

        # Find the embedded relationship
        embedded_rel = None
        for rel in parent_entity.relationships:
            if isinstance(rel, Embedded) and rel.aggr_name == embedded_name:
                embedded_rel = rel
                break

        if not embedded_rel:
            return

        # Get alias from clauses if provided
        alias = embedded_name
        for c in params.get("clauses", []):
            if c["type"] == "AS":
                alias = c["alias"]

        # Get the embedded entity
        embedded_entity = self.database.get_entity_type(embedded_rel.get_target_entity_name())
        if not embedded_entity:
            return

        # Create new standalone entity
        new_entity = EntityType(en_name=alias)
        for attr in embedded_entity.attributes:
            new_entity.add_attribute(Attribute(attr.attr_name, attr.data_type, attr.is_key, attr.is_optional))
        for key in embedded_entity.keys:
            new_entity.add_key(copy.deepcopy(key))

        self.database.add_entity_type(new_entity)

        # Remove embedded relationship from parent
        parent_entity.remove_relationship(embedded_name)

        # Add reference from parent to new entity
        pk = new_entity.get_primary_key()
        fk_type = pk.key_attributes[0].data_type if pk and pk.key_attributes else PrimitiveDataType(PrimitiveType.INTEGER)
        fk_name = f"{alias}_id"
        parent_entity.add_attribute(Attribute(fk_name, fk_type, False, True))
        parent_entity.add_relationship(Reference(ref_name=fk_name, refs_to=alias,
                                                  cardinality=Cardinality.ONE_TO_ONE, is_optional=True))

        self.changes.append(f"UNNEST:{parent_name}.{embedded_name}")

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
                entity.en_name = new_name
                self.database.add_entity_type(entity)
                self.changes.append(f"RENAME:{old_name}->{new_name}")

    def _handle_rename_entity(self, params: Dict) -> None:
        """RENAME ENTITY: Rename an entity."""
        old_name = params["old_name"]
        new_name = params["new_name"]

        entity = self.database.get_entity_type(old_name)
        if entity:
            self.database.remove_entity_type(old_name)
            entity.en_name = new_name
            self.database.add_entity_type(entity)
            self.changes.append(f"RENAME_ENTITY:{old_name}->{new_name}")

    def _handle_copy(self, params: Dict) -> None:
        """COPY: Copy attribute or entity from source to target."""
        source_path = params["source"]
        target_path = params["target"]

        source_parts = source_path.split(".")
        target_parts = target_path.split(".")

        if len(source_parts) == 2 and len(target_parts) == 2:
            # Copy attribute: Entity.attr -> Entity.attr
            src_entity = self.database.get_entity_type(source_parts[0])
            tgt_entity = self.database.get_entity_type(target_parts[0])
            if src_entity and tgt_entity:
                src_attr = src_entity.get_attribute(source_parts[1])
                if src_attr:
                    new_attr = Attribute(target_parts[1], src_attr.data_type, False, src_attr.is_optional)
                    tgt_entity.add_attribute(new_attr)
                    self.changes.append(f"COPY:{source_path}->{target_path}")
        elif len(source_parts) == 1 and len(target_parts) == 1:
            # Copy entity
            src_entity = self.database.get_entity_type(source_parts[0])
            if src_entity:
                new_entity = copy.deepcopy(src_entity)
                new_entity.en_name = target_parts[0]
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
        new_entity = EntityType(en_name=target_name)

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
            new_entity.add_key(copy.deepcopy(pk))

        self.database.add_entity_type(new_entity)

        # Remove source entities if different from target
        if source1_name != target_name:
            self.database.remove_entity_type(source1_name)
        if source2_name != target_name:
            self.database.remove_entity_type(source2_name)

        self.changes.append(f"MERGE:{source1_name},{source2_name}->{target_name}")

    def _handle_split(self, params: Dict) -> None:
        """SPLIT: Split one entity into two."""
        source_name = params["source"]
        target1_name = params["target1"]
        target2_name = params["target2"]

        source = self.database.get_entity_type(source_name)
        if not source:
            return

        # Create two new entities, each gets half the attributes
        attrs = list(source.attributes)
        mid = len(attrs) // 2

        # Target1 gets first half (including PK)
        entity1 = EntityType(en_name=target1_name)
        for attr in attrs[:mid] if mid > 0 else attrs[:1]:
            entity1.add_attribute(Attribute(attr.attr_name, attr.data_type, attr.is_key, attr.is_optional))
        pk = source.get_primary_key()
        if pk:
            entity1.add_key(copy.deepcopy(pk))

        # Target2 gets second half
        entity2 = EntityType(en_name=target2_name)
        for attr in attrs[mid:] if mid > 0 else attrs[1:]:
            entity2.add_attribute(Attribute(attr.attr_name, attr.data_type, False, attr.is_optional))

        self.database.add_entity_type(entity1)
        self.database.add_entity_type(entity2)

        # Remove source if different from targets
        if source_name not in (target1_name, target2_name):
            self.database.remove_entity_type(source_name)

        self.changes.append(f"SPLIT:{source_name}->{target1_name},{target2_name}")

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
                    "DATETIME": PrimitiveType.DATETIME, "TIMESTAMP": PrimitiveType.TIMESTAMP,
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
            new_entity = EntityType(en_name=name)
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
        new_type_str = params["data_type"].upper()

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
            "DATETIME": PrimitiveType.DATETIME, "TIMESTAMP": PrimitiveType.TIMESTAMP,
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
        new_entity = EntityType(en_name=target_name)

        # Process clauses for key generation
        pk_name = None
        ref_clauses = []
        for c in clauses:
            if c["type"] == "GENERATE_KEY":
                pk_name = c["key_name"]
                pk_type = PrimitiveDataType(PrimitiveType.INTEGER)
                pk_attr = Attribute(pk_name, pk_type, True, False)
                new_entity.add_attribute(pk_attr)
                key = Key(key_type=KeyType.PRIMARY)
                key.add_attribute(pk_attr)
                new_entity.add_key(key)
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


def parse_smel(file_path: Path) -> tuple:
    """
    Parse SMEL file and return (context, operations, errors).

    Args:
        file_path: Path to .smel file

    Returns:
        Tuple of (MigrationContext, List[Operation], List[str] errors)
    """
    input_stream = FileStream(str(file_path), encoding='utf-8')
    lexer = SMELLexer(input_stream)
    lexer.removeErrorListeners()
    error_listener = SyntaxErrorListener()
    lexer.addErrorListener(error_listener)

    parser = SMELParser(CommonTokenStream(lexer))
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)
    tree = parser.migration()

    if error_listener.errors:
        return None, [], error_listener.errors

    listener = SMELParserListener()
    ParseTreeWalker().walk(listener, tree)
    return listener.context, listener.operations, []


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
        entities[name] = {
            "name": name,
            "attributes": [
                {
                    "name": a.attr_name,
                    "type": a.data_type.primitive_type.value if hasattr(a.data_type, 'primitive_type') else 'unknown',
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
                for r in entity.relationships if isinstance(r, Aggregate)
            ]
        }
    return entities


# Type mappings for source format display
PG_REVERSE_TYPE_MAP = {
    PrimitiveType.INTEGER: 'INTEGER',
    PrimitiveType.LONG: 'BIGINT',
    PrimitiveType.STRING: 'VARCHAR',
    PrimitiveType.TEXT: 'TEXT',
    PrimitiveType.DECIMAL: 'DECIMAL',
    PrimitiveType.FLOAT: 'REAL',
    PrimitiveType.DOUBLE: 'DOUBLE PRECISION',
    PrimitiveType.BOOLEAN: 'BOOLEAN',
    PrimitiveType.DATE: 'DATE',
    PrimitiveType.DATETIME: 'TIMESTAMP',
    PrimitiveType.TIMESTAMP: 'TIMESTAMP',
    PrimitiveType.UUID: 'UUID',
    PrimitiveType.BINARY: 'BYTEA',
}

MONGO_REVERSE_TYPE_MAP = {
    PrimitiveType.STRING: 'string',
    PrimitiveType.INTEGER: 'int',
    PrimitiveType.LONG: 'long',
    PrimitiveType.DOUBLE: 'double',
    PrimitiveType.DECIMAL: 'decimal',
    PrimitiveType.FLOAT: 'double',
    PrimitiveType.BOOLEAN: 'bool',
    PrimitiveType.DATE: 'date',
    PrimitiveType.DATETIME: 'timestamp',
    PrimitiveType.TIMESTAMP: 'timestamp',
    PrimitiveType.UUID: 'string',
    PrimitiveType.BINARY: 'binData',
    PrimitiveType.OBJECT_ID: 'objectId',
}


def _get_source_type_str(attr: Attribute, source_type: str) -> str:
    """Get the original type string for an attribute based on source database type."""
    primitive = attr.data_type.primitive_type if hasattr(attr.data_type, 'primitive_type') else PrimitiveType.STRING

    if source_type == "Relational":
        # PostgreSQL format
        base_type = PG_REVERSE_TYPE_MAP.get(primitive, 'VARCHAR')

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
        # MongoDB format (bsonType)
        return MONGO_REVERSE_TYPE_MAP.get(primitive, 'string')


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
                for r in entity.relationships if isinstance(r, Aggregate)
            ]
        }
    return entities


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

        if new_attrs or deleted_attrs or new_embedded or deleted_embedded or new_refs or deleted_refs:
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
                "deleted_references": list(deleted_refs)
            })

    return changes


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
    # Normalize direction values for backwards compatibility
    if direction == "1":
        direction = "r2d"
    elif direction == "2":
        direction = "d2r"

    if direction == "r2d":
        source_file = SCHEMA_DIR / "pain001_postgresql.sql"
        smel_file = TESTS_DIR / "pg_to_mongo.smel"
        source_type, target_type = "Relational", "Document"
        source_adapter = PostgreSQLAdapter
        target_adapter = MongoDBAdapter
    elif direction == "d2r":
        source_file = SCHEMA_DIR / "pain001_mongodb.json"
        smel_file = TESTS_DIR / "mongo_to_pg.smel"
        source_type, target_type = "Document", "Relational"
        source_adapter = MongoDBAdapter
        target_adapter = PostgreSQLAdapter
    elif direction == "r2r":
        source_file = SCHEMA_DIR / "pain001_postgresql.sql"
        smel_file = TESTS_DIR / "sql_v1_to_v2.smel"
        source_type, target_type = "Relational", "Relational"
        source_adapter = PostgreSQLAdapter
        target_adapter = PostgreSQLAdapter
    elif direction == "d2d":
        source_file = SCHEMA_DIR / "pain001_mongodb.json"
        smel_file = TESTS_DIR / "mongo_v1_to_v2.smel"
        source_type, target_type = "Document", "Document"
        source_adapter = MongoDBAdapter
        target_adapter = MongoDBAdapter
    else:
        return {"error": f"Unknown direction: {direction}"}

    for f in [source_file, smel_file]:
        if not f.exists():
            return {"error": f"File not found: {f}"}

    raw_source = source_file.read_text(encoding='utf-8')
    smel_content = smel_file.read_text(encoding='utf-8')

    # Step 1: Import source -> Meta V1
    source_db = source_adapter.load_from_file(str(source_file), "source")
    meta_v1_db = copy.deepcopy(source_db)

    # Step 2: Parse and execute SMEL -> Meta V2
    context, operations, errors = parse_smel(smel_file)
    if errors:
        return {"error": f"SMEL parse errors: {errors}"}

    # Execute operations and track step-by-step changes
    transformer = SchemaTransformer(source_db)
    operations_detail = []
    current_entity_count = len(source_db.entity_types)

    for i, op in enumerate(operations):
        prev_count = len(transformer.database.entity_types)
        prev_snapshot = db_to_dict(transformer.database)
        handler = getattr(transformer, f"_handle_{op.op_type.lower()}", None)
        if handler:
            handler(op.params)
        new_count = len(transformer.database.entity_types)
        after_snapshot = db_to_dict(transformer.database)

        # Calculate changes for this operation
        changes_detail = _calculate_changes(prev_snapshot, after_snapshot, op)

        operations_detail.append({
            "step": i + 1,
            "type": op.op_type,
            "params": op.params,
            "entity_count_before": prev_count,
            "entity_count_after": new_count,
            "changes": changes_detail
        })

    result_db = transformer.database
    result_db.db_type = DatabaseType.DOCUMENT if target_type == "Document" else DatabaseType.RELATIONAL

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
        "source": db_to_source_dict(meta_v1_db, source_type),  # Original format (SERIAL, VARCHAR, bsonType)
        "meta_v1": db_to_dict(meta_v1_db),                     # Unified Meta format (integer, string)
        "result": db_to_dict(result_db),                       # Unified Meta format (integer, string)
        "target_with_db_types": db_to_source_dict(result_db, target_type),  # Target format (SERIAL, VARCHAR, bsonType)
        "changes": transformer.changes,
        "operations_count": len(operations),
        "stats": {
            "source_count": len(meta_v1_db.entity_types),
            "result_count": len(result_db.entity_types)
        }
    }
