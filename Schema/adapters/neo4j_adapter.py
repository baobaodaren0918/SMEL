"""
Neo4j Adapter - Parse Neo4j Graph JSON Schema to Unified Meta Schema.
Converts Neo4j node/relationship definitions to Database/EntityType/Property objects.

This adapter provides bidirectional conversion:
  - load_from_file(): Neo4j Graph JSON -> Unified Meta Schema
  - export_to_cypher(): Unified Meta Schema -> Cypher DDL (constraints + comments)

Data Flow:
  Neo4j Graph JSON                       Unified Meta Schema
  ─────────────────────────────────────────────────────────────
  Node label "customers"              ->     EntityType(entity_kind=VERTEX)
  Relationship type "PURCHASED"     ->     EntityType(EDGE) + Edge
  Property { "type": "string" }    ->     PrimitiveType.STRING
  primary_key field                ->     UniqueConstraint (is_primary_key=True)

Design: from Andre Conrad
"""
import json
import re
from typing import Dict, Any, Optional, List, Union
from ..unified_meta_schema import (
    Database, DatabaseType, EntityType, EntityKind, Property,
    UniqueConstraint, UniqueProperty, PKTypeEnum,
    Edge, Cardinality, PrimitiveDataType, PrimitiveType,
    TypeMappings
)
from ._base import DatabaseAdapter


class Neo4jAdapter(DatabaseAdapter):
    """
    Adapter to parse Neo4j graph schema JSON and create Unified Meta Schema.

    This class acts as a translator between Neo4j's graph schema format
    and the internal Unified Meta Schema used by SMILE.

    Example:
        database = Neo4jAdapter.load_from_file("graph_schema.json", db_name="mydb")
    """

    # =========================================================================
    # TYPE MAPPING (from centralized TypeMappings)
    # =========================================================================
    TYPE_MAP = TypeMappings.NEO4J_TO_PRIMITIVE
    REVERSE_TYPE_MAP = TypeMappings.PRIMITIVE_TO_NEO4J

    # Cardinality mapping: JSON string -> Cardinality enum
    CARDINALITY_MAP: Dict[str, Cardinality] = {
        "1..1": Cardinality.ONE_TO_ONE,
        "1..n": Cardinality.ONE_TO_MANY,
        "0..1": Cardinality.ZERO_TO_ONE,
        "0..n": Cardinality.ZERO_TO_MANY,
    }

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    def __init__(self):
        """Initialize adapter with empty state."""
        self.database: Optional[Database] = None

    # =========================================================================
    # PARSE METHODS (JSON -> Unified Meta Schema)
    # =========================================================================

    def parse(self, schema: Union[Dict[str, Any], str], db_name: str = "database") -> Database:
        """
        Parse Neo4j graph schema and return Database object.

        Accepts:
          * a JSON dict (legacy);
          * a JSON string (auto-detected by leading ``{``/``[``);
          * a Cypher script (auto-detected; routed to ``parse_cypher``).

        Using the string form lets callers treat all four adapters uniformly
        via the ``DatabaseAdapter`` ABC.

        Example Input (Neo4j Graph JSON):
            {
                "nodes": [
                    {
                        "label": "customers",
                        "properties": [
                            {"name": "name", "type": "string"},
                            {"name": "age", "type": "integer"}
                        ],
                        "primary_key": "name"
                    },
                    {
                        "label": "orders",
                        "properties": [
                            {"name": "title", "type": "string"},
                            {"name": "year", "type": "integer"}
                        ],
                        "primary_key": "title"
                    }
                ],
                "relationships": [
                    {
                        "type": "PURCHASED",
                        "source": "customers",
                        "target": "orders",
                        "properties": [{"name": "role", "type": "string"}],
                        "cardinality": "0..n"
                    }
                ]
            }

        Example Output (Unified Meta Schema):
            Database(
                db_name="mydb",
                db_type=DatabaseType.GRAPH,
                entity_types={
                    "customers": EntityType(
                        object_name=["customers"],
                        entity_kind=EntityKind.VERTEX,
                        properties=[
                            Property("name", STRING, is_key=True),
                            Property("age", INTEGER)
                        ],
                        constraints=[UniqueConstraint(is_primary_key=True, ...)]
                    ),
                    "orders": EntityType(...)
                },
                    "PURCHASED": EntityType(
                        object_name=["PURCHASED"],
                        entity_kind=EntityKind.EDGE,
                        source_entity="customers",
                        target_entity="orders",
                        properties=[Property("role", STRING)],
                        edge_cardinality=ZERO_TO_MANY
                    )
            )

        Processing Flow:
            1. Create Database with db_type=GRAPH
            2. Parse each node -> EntityType(entity_kind=VERTEX)
            3. Parse each relationship -> EntityType(EDGE) + Edge on source entity
        """
        # Auto-detect string input (canonical entry per DatabaseAdapter ABC).
        if isinstance(schema, str):
            stripped = schema.lstrip()
            if stripped.startswith("{") or stripped.startswith("["):
                schema = json.loads(stripped)
            else:
                return self.parse_cypher(schema, db_name)
        self.database = Database(db_name=db_name, db_type=DatabaseType.GRAPH)

        # Step 1: Parse nodes -> EntityType with entity_kind=VERTEX
        nodes = schema.get("nodes", [])
        for node_def in nodes:
            entity = self._parse_node(node_def)
            self.database.add_entity_type(entity)

        # Step 2: Parse relationships -> EntityType(EDGE) + Edge
        relationships = schema.get("relationships", [])
        for rel_def in relationships:
            self._parse_relationship(rel_def)

        return self.database

    def _parse_node(self, node_def: Dict[str, Any]) -> EntityType:
        """
        Parse a single node definition into EntityType.

        Example:
            node_def = {
                "label": "customers",
                "properties": [
                    {"name": "name", "type": "string"},
                    {"name": "age", "type": "integer"}
                ],
                "primary_key": "name"
            }

            -> EntityType(
                 object_name=["customers"],
                 entity_kind=EntityKind.VERTEX,
                 properties=[
                     Property("name", STRING, is_key=True),
                     Property("age", INTEGER)
                 ],
                 constraints=[UniqueConstraint(is_primary_key=True, ...)]
               )
        """
        label = node_def.get("label", "Unknown")
        primary_key = node_def.get("primary_key")

        entity = EntityType(
            object_name=[label],
            entity_kind=EntityKind.VERTEX
        )

        # Parse properties -> Property objects
        properties = node_def.get("properties", [])
        for prop_def in properties:
            prop_name = prop_def.get("name", "")
            prop_type = prop_def.get("type", "string").lower()

            is_key = (prop_name == primary_key)
            data_type = self._parse_data_type(prop_type)

            attr = Property(
                name=prop_name,
                data_type=data_type,
                is_key=is_key,
                is_optional=not is_key
            )
            entity.add_property(attr)

            # Create primary key constraint
            if is_key:
                constraint = UniqueConstraint(
                    is_primary_key=True,
                    is_managed=True,
                    unique_properties=[
                        UniqueProperty(
                            primary_key_type=PKTypeEnum.NODE_KEY,
                            property_id=attr.meta_id
                        )
                    ]
                )
                entity.add_constraint(constraint)

        return entity

    def _parse_relationship(self, rel_def: Dict[str, Any]):
        """
        Parse a single relationship definition into EntityType(EDGE) and Edge.

        Creates two things:
          1. EntityType(EDGE) on Database (schema-level edge definition)
          2. Edge on source EntityType's relationships list (instance-level link)

        Example:
            rel_def = {
                "type": "PURCHASED",
                "source": "customers",
                "target": "orders",
                "properties": [{"name": "role", "type": "string"}],
                "cardinality": "0..n"
            }

            -> EntityType(EDGE)("PURCHASED", source="customers", target="orders", ...)
            -> Edge on customers entity (rel_type_name="PURCHASED", target="orders")
        """
        rel_name = rel_def.get("type", "RELATED_TO")
        source_label = rel_def.get("source", "")
        target_label = rel_def.get("target", "")
        cardinality_str = rel_def.get("cardinality", "0..n")
        cardinality = self.CARDINALITY_MAP.get(cardinality_str, Cardinality.ZERO_TO_MANY)

        # Parse relationship properties -> Property objects
        edge_properties = []
        for prop_def in rel_def.get("properties", []):
            prop_name = prop_def.get("name", "")
            prop_type = prop_def.get("type", "string").lower()
            data_type = self._parse_data_type(prop_type)

            attr = Property(
                name=prop_name,
                data_type=data_type,
                is_key=False,
                is_optional=True
            )
            edge_properties.append(attr)

        # Create EDGE EntityType (schema-level definition)
        edge_entity = EntityType(
            object_name=[rel_name],
            entity_kind=EntityKind.EDGE,
            source_entity=source_label,
            target_entity=target_label,
            edge_cardinality=cardinality,
            properties=edge_properties
        )
        self.database.add_entity_type(edge_entity)

        # Create Edge on source entity's relationships list
        source_entity = self.database.get_entity_type(source_label)
        if not source_entity:
            print(f"[NOTICE] Neo4j relationship '{rel_name}': source entity '{source_label}' not found, Edge not created")
        if source_entity:
            # Optionality is derived from cardinality minimum:
            # 0..1, 0..n → optional (minimum 0), 1..1, 1..n → required (minimum 1)
            is_edge_optional = cardinality in (Cardinality.ZERO_TO_ONE, Cardinality.ZERO_TO_MANY)
            edge = Edge(
                rel_type_name=rel_name,
                source_entity=source_label,
                target_entity=target_label,
                cardinality=cardinality,
                is_optional=is_edge_optional
            )
            source_entity.add_relationship(edge)

    def _parse_data_type(self, type_name: str) -> PrimitiveDataType:
        """
        Parse a Neo4j property type string to PrimitiveDataType.

        Examples:
            "string"    -> PrimitiveDataType(STRING)
            "integer"   -> PrimitiveDataType(INTEGER)
            "boolean"   -> PrimitiveDataType(BOOLEAN)
            "unknown"   -> PrimitiveDataType(STRING) (fallback)
        """
        primitive = self.TYPE_MAP.get(type_name, PrimitiveType.STRING)
        return PrimitiveDataType(primitive_type=primitive)

    # =========================================================================
    # CYPHER DDL PARSING
    # =========================================================================

    # Cardinality string to enum mapping for Cypher parsing
    CARDINALITY_STR_MAP: Dict[str, Cardinality] = {
        "1..1": Cardinality.ONE_TO_ONE,
        "1..n": Cardinality.ONE_TO_MANY,
        "0..1": Cardinality.ZERO_TO_ONE,
        "0..n": Cardinality.ZERO_TO_MANY,
    }

    def parse_cypher(self, cypher_content: str, db_name: str = "database") -> Database:
        """
        Parse Neo4j Cypher DDL text and return Database object.

        Parses the Cypher DDL format produced by export_to_cypher():
          // Node: <Label>
          CREATE CONSTRAINT ... FOR (n:<Label>) REQUIRE n.<field> IS UNIQUE;
          // Properties: field1 (type), field2 (type), ...

          // Relationship: <NAME> (<Source> -> <Target>)
          // Properties: field1 (type), ...
          // Cardinality: 0..n
        """
        self.database = Database(db_name=db_name, db_type=DatabaseType.GRAPH)

        lines = cypher_content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Parse node blocks: "// Node: <Label>" or "// Node: <Label>:<Extra1>:<Extra2>"
            node_match = re.match(r'^// Node:\s+([\w:]+)', line)
            if node_match:
                label_str = node_match.group(1)
                label_parts = label_str.split(':')
                label = label_parts[0]
                extra_labels = label_parts[1:] if len(label_parts) > 1 else []
                primary_key = None
                properties = []

                # Look ahead for Key/CREATE CONSTRAINT and Properties
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()

                    # // Key: <field> (comment-based format)
                    key_match = re.match(r'^// Key:\s+(\w+)', next_line)
                    if key_match:
                        primary_key = key_match.group(1)
                        j += 1
                        continue

                    # CREATE CONSTRAINT ... REQUIRE n.<field> IS UNIQUE/NODE KEY (executable format)
                    constraint_match = re.match(
                        r'CREATE CONSTRAINT .+ FOR \(n:[\w:]+\) REQUIRE n\.(\w+) IS (?:UNIQUE|NODE KEY);',
                        next_line
                    )
                    if constraint_match:
                        primary_key = constraint_match.group(1)
                        j += 1
                        continue

                    # // Properties: field1 (type), field2 (type)
                    props_match = re.match(r'^// Properties:\s+(.+)', next_line)
                    if props_match:
                        props_str = props_match.group(1)
                        for prop in re.findall(r'(\w+)\s+\((\w+)\)', props_str):
                            properties.append({"name": prop[0], "type": prop[1]})
                        j += 1
                        break  # Properties line ends the node block

                    # Empty line or next block -> end of this node
                    if next_line == '' or next_line.startswith('// Node:') or next_line.startswith('// Relationship:'):
                        break
                    j += 1

                # Build node definition and parse it
                node_def = {
                    "label": label,
                    "properties": properties,
                    "primary_key": primary_key
                }
                entity = self._parse_node(node_def)
                entity.labels = extra_labels
                self.database.add_entity_type(entity)
                i = j
                continue

            # Parse relationship blocks: "// Relationship: <NAME> (<Source> -> <Target>)"
            rel_match = re.match(r'^// Relationship:\s+(\w+)\s+\((\w+)\s+->\s+(\w+)\)', line)
            if rel_match:
                rel_name = rel_match.group(1)
                source_label = rel_match.group(2)
                target_label = rel_match.group(3)
                rel_properties = []
                cardinality_str = "0..n"

                # Look ahead for Properties and Cardinality
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()

                    props_match = re.match(r'^// Properties:\s+(.+)', next_line)
                    if props_match:
                        props_str = props_match.group(1)
                        for prop in re.findall(r'(\w+)\s+\((\w+)\)', props_str):
                            rel_properties.append({"name": prop[0], "type": prop[1]})
                        j += 1
                        continue

                    card_match = re.match(r'^// Cardinality:\s+(.+)', next_line)
                    if card_match:
                        cardinality_str = card_match.group(1).strip()
                        j += 1
                        break  # Cardinality ends the relationship block

                    # Empty line or next block -> end
                    if next_line == '' or next_line.startswith('// Node:') or next_line.startswith('// Relationship:'):
                        break
                    j += 1

                # Build relationship definition and parse it
                rel_def = {
                    "type": rel_name,
                    "source": source_label,
                    "target": target_label,
                    "properties": rel_properties,
                    "cardinality": cardinality_str
                }
                self._parse_relationship(rel_def)
                i = j
                continue

            i += 1

        return self.database

    # =========================================================================
    # LOAD FROM FILE
    # =========================================================================

    @staticmethod
    def load_from_file(file_path: str, db_name: str = None) -> Database:
        """
        Load Neo4j graph schema from file and parse to Database.
        Supports both JSON (.json) and Cypher DDL (.cypher) formats.

        Example:
            database = Neo4jAdapter.load_from_file("graph_schema.cypher", db_name="mydb")
            database = Neo4jAdapter.load_from_file("graph_schema.json", db_name="mydb")
        """
        from pathlib import Path

        if db_name is None:
            db_name = Path(file_path).stem

        adapter = Neo4jAdapter()

        if file_path.endswith('.cypher'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return adapter.parse_cypher(content, db_name)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    schema = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in Neo4j schema file '{file_path}': {e}")
            return adapter.parse(schema, db_name)

    # =========================================================================
    # EXPORT METHODS (Unified Meta Schema -> Cypher DDL)
    # =========================================================================

    @classmethod
    def export_to_cypher(cls, database: Database) -> str:
        """
        Export Unified Meta Schema to Neo4j Cypher DDL format.

        Generates constraint statements and property/relationship comments
        that describe the graph schema in a Cypher-compatible format.

        Example Output:
            // Neo4j Graph Schema
            // Generated by SMILE

            // Node: customers
            CREATE CONSTRAINT customer_name_unique IF NOT EXISTS
              FOR (n:customers) REQUIRE n.name IS UNIQUE;
            // Properties: name (string), age (integer)

            // Node: orders
            CREATE CONSTRAINT movie_title_unique IF NOT EXISTS
              FOR (n:orders) REQUIRE n.title IS UNIQUE;
            // Properties: title (string), year (integer)

            // Relationship: PURCHASED (customers -> orders)
            // Properties: role (string)
            // Cardinality: 0..n

            // Relationship: SOLD (customers -> orders)
            // Cardinality: 0..n
        """
        lines = []
        lines.append("// Neo4j Graph Schema")
        lines.append("// Generated by SMILE")

        # Export node entities (VERTEX kind only)
        for entity in database.entity_types.values():
            if entity.entity_kind == EntityKind.VERTEX:
                lines.append("")
                node_lines = cls._export_node(entity)
                lines.extend(node_lines)

        # Export relationship types (EDGE entities)
        for entity in database.entity_types.values():
            if entity.entity_kind == EntityKind.EDGE:
                lines.append("")
                rel_lines = cls._export_relationship(entity)
                lines.extend(rel_lines)

        return "\n".join(lines)

    @classmethod
    def _export_node(cls, entity: EntityType) -> List[str]:
        """
        Export a single node entity to Cypher constraint and property comments.

        Example Output:
            // Node: customers
            CREATE CONSTRAINT customer_name_unique IF NOT EXISTS
              FOR (n:customers) REQUIRE n.name IS UNIQUE;
            // Properties: name (string), age (integer)
        """
        lines = []
        label = entity.name
        # Include additional labels (e.g. customers:Employee)
        extra_labels = getattr(entity, 'labels', [])
        label_display = label + (''.join(f':{l}' for l in extra_labels) if extra_labels else '')
        lines.append(f"// Node: {label_display}")

        # Generate constraint for primary key property(s)
        pk_constraint = entity.get_primary_key()
        if pk_constraint and pk_constraint.unique_properties:
            pk_attrs = []
            for up in pk_constraint.unique_properties:
                pk_attr = entity.get_property_by_id(up.property_id)
                if pk_attr:
                    pk_attrs.append(pk_attr.name)
            if len(pk_attrs) == 1:
                constraint_name = f"{label.lower()}_{pk_attrs[0]}_unique"
                lines.append(
                    f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
                    f"FOR (n:{label_display}) REQUIRE n.{pk_attrs[0]} IS NODE KEY;"
                )
            elif len(pk_attrs) > 1:
                constraint_name = f"{label.lower()}_pk"
                props = ", ".join(f"n.{a}" for a in pk_attrs)
                lines.append(
                    f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
                    f"FOR (n:{label_display}) REQUIRE ({props}) IS NODE KEY;"
                )

        # Generate property comment listing all properties with types
        if entity.properties:
            prop_strs = []
            for attr in entity.properties:
                type_str = cls.REVERSE_TYPE_MAP.get(
                    attr.data_type.primitive_type, "string"
                ) if isinstance(attr.data_type, PrimitiveDataType) else "string"
                prop_strs.append(f"{attr.name} ({type_str})")
            lines.append(f"// Properties: {', '.join(prop_strs)}")

        return lines

    @classmethod
    def _export_relationship(cls, edge_entity: EntityType) -> List[str]:
        """
        Export a single EDGE entity type to Cypher comments.

        Example Output:
            // Relationship: PURCHASED (customers -> orders)
            // Properties: role (string)
            // Cardinality: 0..n
        """
        lines = []
        lines.append(
            f"// Relationship: {edge_entity.name} "
            f"({edge_entity.source_entity} -> {edge_entity.target_entity})"
        )

        # List relationship properties if any
        if edge_entity.properties:
            prop_strs = []
            for attr in edge_entity.properties:
                type_str = cls.REVERSE_TYPE_MAP.get(
                    attr.data_type.primitive_type, "string"
                ) if isinstance(attr.data_type, PrimitiveDataType) else "string"
                prop_strs.append(f"{attr.name} ({type_str})")
            lines.append(f"// Properties: {', '.join(prop_strs)}")

        # Cardinality comment
        cardinality = edge_entity.edge_cardinality or Cardinality.ZERO_TO_MANY
        lines.append(f"// Cardinality: {cardinality.value}")

        return lines

    @classmethod
    def export(cls, database: Database) -> str:
        """
        Convenience method that calls export_to_cypher().

        Example:
            cypher_ddl = Neo4jAdapter.export(database)
        """
        return cls.export_to_cypher(database)

    @classmethod
    def export_to_cypher_file(cls, database: Database, file_path: str) -> None:
        """
        Export to Cypher DDL file.

        Example:
            Neo4jAdapter.export_to_cypher_file(database, "output.cypher")
        """
        cypher = cls.export_to_cypher(database)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cypher)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
#
# Example 1: Parse Neo4j Graph JSON to Unified Meta Schema
# ---------------------------------------------------------
#
# graph_schema = {
#     "nodes": [
#         {
#             "label": "customers",
#             "properties": [
#                 {"name": "name", "type": "string"},
#                 {"name": "age", "type": "integer"}
#             ],
#             "primary_key": "name"
#         },
#         {
#             "label": "orders",
#             "properties": [
#                 {"name": "title", "type": "string"},
#                 {"name": "year", "type": "integer"}
#             ],
#             "primary_key": "title"
#         }
#     ],
#     "relationships": [
#         {
#             "type": "PURCHASED",
#             "source": "customers",
#             "target": "orders",
#             "properties": [{"name": "role", "type": "string"}],
#             "cardinality": "0..n"
#         },
#         {
#             "type": "SOLD",
#             "source": "customers",
#             "target": "orders",
#             "properties": [],
#             "cardinality": "0..n"
#         }
#     ]
# }
#
# adapter = Neo4jAdapter()
# database = adapter.parse(graph_schema, db_name="movies")
#
# Result:
#   database.db_name = "movies"
#   database.db_type = DatabaseType.GRAPH
#   database.entity_types = {
#       "customers": EntityType(
#           object_name=["customers"],
#           entity_kind=EntityKind.VERTEX,
#           properties=[
#               Property("name", STRING, is_key=True),
#               Property("age", INTEGER)
#           ],
#           constraints=[UniqueConstraint(is_primary_key=True, ...)],
#           relationships=[
#               Edge(rel_type_name="PURCHASED", target="orders"),
#               Edge(rel_type_name="SOLD", target="orders")
#           ]
#       ),
#       "orders": EntityType(
#           object_name=["orders"],
#           entity_kind=EntityKind.VERTEX,
#           properties=[
#               Property("title", STRING, is_key=True),
#               Property("year", INTEGER)
#           ]
#       )
#   }
#   database.relationship_types = {
#       "PURCHASED": EntityType(EDGE)(
#           rel_name="PURCHASED",
#           source_entity="customers",
#           target_entity="orders",
#           properties=[Property("role", STRING)],
#           cardinality=ZERO_TO_MANY
#       ),
#       "SOLD": EntityType(EDGE)(
#           rel_name="SOLD",
#           source_entity="customers",
#           target_entity="orders",
#           properties=[],
#           cardinality=ZERO_TO_MANY
#       )
#   }
#
#
# Example 2: Load from file
# -------------------------
#
# database = Neo4jAdapter.load_from_file("graph_schema.json", db_name="movies")
#
#
# Example 3: Export to Cypher DDL
# -------------------------------
#
# cypher_ddl = Neo4jAdapter.export_to_cypher(database)
# print(cypher_ddl)
#
# Output:
#   -- Neo4j Graph Schema
#   -- Generated by SMILE
#
#   -- Node: customers
#   CREATE CONSTRAINT customer_name_unique IF NOT EXISTS
#     FOR (n:customers) REQUIRE n.name IS UNIQUE;
#   -- Properties: name (string), age (integer)
#
#   -- Node: orders
#   CREATE CONSTRAINT movie_title_unique IF NOT EXISTS
#     FOR (n:orders) REQUIRE n.title IS UNIQUE;
#   -- Properties: title (string), year (integer)
#
#   -- Relationship: PURCHASED (customers -> orders)
#   -- Properties: role (string)
#   -- Cardinality: 0..n
#
#   -- Relationship: SOLD (customers -> orders)
#   -- Cardinality: 0..n
#
#
# Example 4: Export using convenience method
# -------------------------------------------
#
# cypher_ddl = Neo4jAdapter.export(database)
#
#
# Example 5: Export to file
# -------------------------
#
# Neo4jAdapter.export_to_cypher_file(database, "output.cypher")
#
