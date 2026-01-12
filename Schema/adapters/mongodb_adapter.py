"""
MongoDB Adapter - Parse MongoDB JSON Schema to Unified Meta Schema.
Converts MongoDB JSON Schema (with bsonType) to Database/EntityType/Attribute objects.

This adapter provides bidirectional conversion:
  - parse(): MongoDB JSON Schema -> Unified Meta Schema
  - export_to_json(): Unified Meta Schema -> MongoDB JSON Schema

Data Flow:
  MongoDB JSON Schema                    Unified Meta Schema
  ─────────────────────────────────────────────────────────────
  { "bsonType": "string" }        ->     PrimitiveType.STRING
  { "bsonType": "objectId" }      ->     PrimitiveType.OBJECT_ID
  { "bsonType": "array", items }  ->     ListDataType / Embedded
  { "bsonType": "object" }        ->     EntityType (nested)
"""
import json
from typing import Dict, Any, Optional, List
from ..unified_meta_schema import (
    Database, DatabaseType, EntityType, Attribute,
    UniqueConstraint, UniqueProperty, PKTypeEnum,
    Embedded, Cardinality, PrimitiveDataType, PrimitiveType, ListDataType,
    TypeMappings
)


class MongoDBAdapter:
    """
    Adapter to parse MongoDB JSON Schema and create Unified Meta Schema.

    This class acts as a translator between MongoDB's JSON Schema format
    and the internal Unified Meta Schema used by SMEL.

    Example:
        adapter = MongoDBAdapter()
        database = adapter.parse(mongo_schema, db_name="mydb")
    """

    # BSON type to PrimitiveType mapping (from centralized TypeMappings)
    TYPE_MAP = TypeMappings.MONGODB_TO_PRIMITIVE

    def __init__(self):
        self.database: Optional[Database] = None

    def parse(self, schema: Dict[str, Any], db_name: str = "database") -> Database:
        """
        Parse MongoDB JSON Schema and return Database object.

        Example Input (MongoDB JSON Schema):
            {
                "title": "person",
                "bsonType": "object",
                "properties": {
                    "_id": {"bsonType": "objectId"},
                    "name": {"bsonType": "string"},
                    "age": {"bsonType": "int"}
                }
            }

        Example Output (Unified Meta Schema):
            Database(
                db_name="person",
                db_type=DatabaseType.DOCUMENT,
                entity_types={
                    "person": EntityType(
                        object_name=["person"],
                        attributes=[
                            Attribute("_id", OBJECT_ID, is_key=True),
                            Attribute("name", STRING),
                            Attribute("age", INTEGER)
                        ]
                    )
                }
            )
        """
        self.database = Database(db_name=db_name, db_type=DatabaseType.DOCUMENT)

        # Parse root document as main entity
        root_name = schema.get('title', 'root_document').lower().replace(' ', '_')
        root_entity = self._parse_object_schema(schema, root_name, parent_path=[], is_root=True)
        self.database.add_entity_type(root_entity)

        return self.database

    def _parse_object_schema(self, schema: Dict[str, Any], name: str, parent_path: List[str] = None, is_root: bool = False) -> EntityType:
        """
        Parse an object schema into EntityType.

        Uses André Conrad's object_name: List[str] design for nested paths.

        Example - Nested object:
            Input: person.address (parent_path=["person"], name="address")
            Output: EntityType(object_name=["person", "address"])

        Example - Deep nested:
            Input: person.address.location (parent_path=["person", "address"], name="location")
            Output: EntityType(object_name=["person", "address", "location"])
        """
        if parent_path is None:
            parent_path = []
        # Build full object_name path (from André Conrad)
        # Example: parent_path=["person"], name="address" -> ["person", "address"]
        object_name = parent_path + [name]
        entity = EntityType(object_name=object_name)

        properties = schema.get('properties', {})
        required = set(schema.get('required', []))

        for prop_name, prop_schema in properties.items():
            prop_name_lower = prop_name.lower()
            is_required = prop_name in required

            # Handle different property types
            bson_type = prop_schema.get('bsonType') or prop_schema.get('type', 'string')

            if bson_type == 'object':
                # Embedded object - pass current entity's object_name as parent_path
                # Example: { "address": { "bsonType": "object", "properties": {...} } }
                #   -> Creates EntityType(object_name=["person", "address"])
                #   -> Creates Embedded relationship with Cardinality.ONE_TO_ONE
                embedded_entity = self._parse_object_schema(prop_schema, prop_name_lower, parent_path=object_name)
                self.database.add_entity_type(embedded_entity)

                embedded = Embedded(
                    aggr_name=prop_name_lower,
                    aggregates=embedded_entity.full_path,  # Use full path for reference
                    cardinality=Cardinality.ONE_TO_ONE if is_required else Cardinality.ZERO_TO_ONE,
                    is_optional=not is_required
                )
                entity.add_relationship(embedded)

            elif bson_type == 'array':
                # Array - check if array of objects or primitives
                # Example 1 (object array): { "items": [{"name": "a"}, {"name": "b"}] }
                #   -> Creates Embedded with Cardinality.ONE_TO_MANY
                # Example 2 (primitive array): { "tags": ["tag1", "tag2"] }
                #   -> Creates Attribute with ListDataType
                items = prop_schema.get('items', {})
                items_type = items.get('bsonType') or items.get('type', 'string')

                if items_type == 'object':
                    # Array of embedded objects - pass current entity's object_name as parent_path
                    # Example: { "items": { "bsonType": "array", "items": { "bsonType": "object" } } }
                    #   -> Creates EntityType for the embedded object
                    #   -> Creates Embedded with Cardinality.ONE_TO_MANY (or ZERO_TO_MANY)
                    embedded_entity = self._parse_object_schema(items, prop_name_lower, parent_path=object_name)
                    self.database.add_entity_type(embedded_entity)

                    embedded = Embedded(
                        aggr_name=prop_name_lower,
                        aggregates=embedded_entity.full_path,  # Use full path for reference
                        cardinality=Cardinality.ONE_TO_MANY if is_required else Cardinality.ZERO_TO_MANY,
                        is_optional=not is_required
                    )
                    entity.add_relationship(embedded)
                else:
                    # Array of primitives - use ListDataType to preserve array semantics
                    # Example: { "tags": { "bsonType": "array", "items": { "bsonType": "string" } } }
                    #   -> Attribute("tags", ListDataType(element_type=PrimitiveDataType(STRING)))
                    element_type = self._parse_primitive_type(items_type, items)
                    attr = Attribute(
                        attr_name=prop_name_lower,
                        data_type=ListDataType(element_type=element_type),
                        is_key=False,
                        is_optional=not is_required
                    )
                    entity.add_attribute(attr)

            else:
                # Primitive type
                is_key = prop_name == '_id'
                attr = Attribute(
                    attr_name=prop_name_lower,
                    data_type=self._parse_primitive_type(bson_type, prop_schema),
                    is_key=is_key,
                    is_optional=not is_required and not is_key
                )
                entity.add_attribute(attr)

                # Add primary key if _id
                if is_key:
                    constraint = UniqueConstraint(
                        is_primary_key=True,
                        is_managed=True,
                        unique_properties=[UniqueProperty(primary_key_type=PKTypeEnum.SIMPLE, property_id=attr.meta_id)]
                    )
                    entity.add_constraint(constraint)

        return entity

    def _parse_primitive_type(self, bson_type: str, schema: Dict[str, Any]) -> PrimitiveDataType:
        """Parse BSON type to PrimitiveDataType."""
        primitive = self.TYPE_MAP.get(bson_type, PrimitiveType.STRING)

        max_length = schema.get('maxLength')
        # MongoDB doesn't have precision/scale in JSON Schema, but we can infer from description

        return PrimitiveDataType(
            primitive_type=primitive,
            max_length=max_length
        )

    @staticmethod
    def load_from_file(file_path: str, db_name: str = None) -> Database:
        """Load MongoDB JSON Schema from file and parse to Database."""
        with open(file_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        if db_name is None:
            db_name = schema.get('title', 'mongodb_schema')

        adapter = MongoDBAdapter()
        return adapter.parse(schema, db_name)

    # ========== Export Methods ==========
    # These methods convert Unified Meta Schema back to MongoDB JSON Schema

    # Reverse mapping (from centralized TypeMappings)
    # Used when exporting back to MongoDB format
    REVERSE_TYPE_MAP = TypeMappings.PRIMITIVE_TO_MONGODB

    @classmethod
    def export_to_json(cls, database: Database, root_entity_name: str = None) -> Dict[str, Any]:
        """
        Export Unified Meta Schema to MongoDB JSON Schema format.

        Args:
            database: The Database object to export
            root_entity_name: Name of the root document entity (auto-detected if not provided)

        Returns:
            MongoDB JSON Schema as a dictionary
        """
        # Find root entity (the one that contains others via Embedded relationships)
        if root_entity_name is None:
            root_entity_name = cls._find_root_entity(database)

        root_entity = database.get_entity_type(root_entity_name)
        if not root_entity:
            raise ValueError(f"Root entity '{root_entity_name}' not found")

        return cls._export_entity_to_schema(database, root_entity, is_root=True)

    @classmethod
    def _find_root_entity(cls, database: Database) -> str:
        """Find the root entity (typically 'payment_message' or similar)."""
        from ..unified_meta_schema import Embedded

        # Entities that are embedded by others
        embedded_entities = set()
        for entity in database.entity_types.values():
            for rel in entity.relationships:
                if isinstance(rel, Embedded):
                    embedded_entities.add(rel.get_target_entity_name())

        # Root = entity that has Embedded relationships but is not embedded by anyone
        for name, entity in database.entity_types.items():
            has_embedded = any(isinstance(r, Embedded) for r in entity.relationships)
            if has_embedded and name not in embedded_entities:
                return name

        # Fallback: first entity with embedded relationships
        for name, entity in database.entity_types.items():
            if any(isinstance(r, Embedded) for r in entity.relationships):
                return name

        # Last fallback: first entity
        return next(iter(database.entity_types.keys()))

    @classmethod
    def _export_entity_to_schema(cls, database: Database, entity: EntityType, is_root: bool = False) -> Dict[str, Any]:
        """Export a single entity to MongoDB JSON Schema format."""
        from ..unified_meta_schema import Embedded, Cardinality

        schema = {
            "bsonType": "object",
            "required": [],
            "properties": {}
        }

        if is_root:
            schema["$schema"] = "http://json-schema.org/draft-07/schema#"
            schema["title"] = entity.name.replace('_', ' ')
            schema["description"] = f"MongoDB document schema for {entity.name}"

        # Process attributes
        for attr in entity.attributes:
            prop_name = attr.attr_name
            # Convert _id for root document
            if is_root and attr.is_key and prop_name != '_id':
                prop_name = '_id'

            prop_schema = cls._export_attribute_to_property(attr)
            schema["properties"][prop_name] = prop_schema

            if not attr.is_optional:
                schema["required"].append(prop_name)

        # Process embedded relationships
        for rel in entity.relationships:
            if isinstance(rel, Embedded):
                embedded_entity = database.get_entity_type(rel.get_target_entity_name())
                if not embedded_entity:
                    continue

                embedded_schema = cls._export_entity_to_schema(database, embedded_entity, is_root=False)

                # Check if it's an array (ONE_TO_MANY, ZERO_TO_MANY)
                if rel.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.ZERO_TO_MANY):
                    schema["properties"][rel.aggr_name] = {
                        "bsonType": "array",
                        "description": f"{rel.aggr_name} array",
                        "items": embedded_schema
                    }
                else:
                    schema["properties"][rel.aggr_name] = embedded_schema

                if rel.cardinality.is_required():
                    schema["required"].append(rel.aggr_name)

        # Clean up empty required list
        if not schema["required"]:
            del schema["required"]

        return schema

    @classmethod
    def _export_attribute_to_property(cls, attr: Attribute) -> Dict[str, Any]:
        """
        Export an attribute to MongoDB property schema.

        Example 1 - Primitive type:
            Input:  Attribute("name", PrimitiveDataType(STRING))
            Output: {"bsonType": "string"}

        Example 2 - Array type:
            Input:  Attribute("tags", ListDataType(element_type=PrimitiveDataType(STRING)))
            Output: {"bsonType": "array", "items": {"bsonType": "string"}}

        Example 3 - ObjectId type:
            Input:  Attribute("_id", PrimitiveDataType(OBJECT_ID))
            Output: {"bsonType": "objectId"}
        """
        data_type = attr.data_type

        # Handle ListDataType (arrays)
        # Example: ListDataType(STRING) -> {"bsonType": "array", "items": {"bsonType": "string"}}
        if isinstance(data_type, ListDataType):
            element_type = data_type.element_type
            if isinstance(element_type, PrimitiveDataType):
                element_bson_type = cls.REVERSE_TYPE_MAP.get(element_type.primitive_type, 'string')
                return {
                    "bsonType": "array",
                    "items": {"bsonType": element_bson_type}
                }
            else:
                # Default to string array if element type is unknown
                return {
                    "bsonType": "array",
                    "items": {"bsonType": "string"}
                }

        # Handle PrimitiveDataType
        if isinstance(data_type, PrimitiveDataType):
            bson_type = cls.REVERSE_TYPE_MAP.get(data_type.primitive_type, 'string')
            prop = {"bsonType": bson_type}

            # Add maxLength for strings
            if data_type.max_length and bson_type == 'string':
                prop["maxLength"] = data_type.max_length

            return prop

        # Default fallback
        return {"bsonType": "string"}

    @classmethod
    def export_to_json_string(cls, database: Database, root_entity_name: str = None, indent: int = 2) -> str:
        """Export to formatted JSON string."""
        schema = cls.export_to_json(database, root_entity_name)
        return json.dumps(schema, indent=indent, ensure_ascii=False)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
#
# Example 1: Parse MongoDB JSON Schema to Unified Meta Schema
# ------------------------------------------------------------
#
# mongo_schema = {
#     "title": "person",
#     "bsonType": "object",
#     "properties": {
#         "_id": {"bsonType": "objectId"},
#         "name": {"bsonType": "string"},
#         "age": {"bsonType": "int"},
#         "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
#         "address": {
#             "bsonType": "object",
#             "properties": {
#                 "street": {"bsonType": "string"},
#                 "city": {"bsonType": "string"}
#             }
#         }
#     }
# }
#
# adapter = MongoDBAdapter()
# database = adapter.parse(mongo_schema, db_name="mydb")
#
# Result:
#   database.db_name = "mydb"
#   database.db_type = DatabaseType.DOCUMENT
#   database.entity_types = {
#       "person": EntityType(
#           object_name=["person"],
#           attributes=[
#               Attribute("_id", PrimitiveType.OBJECT_ID, is_key=True),
#               Attribute("name", PrimitiveType.STRING),
#               Attribute("age", PrimitiveType.INTEGER),
#               Attribute("tags", ListDataType(element_type=PrimitiveDataType(STRING)))
#           ],
#           relationships=[
#               Embedded(aggr_name="address", aggregates="person.address", cardinality=ZERO_TO_ONE)
#           ]
#       ),
#       "person.address": EntityType(
#           object_name=["person", "address"],  # from André Conrad
#           attributes=[
#               Attribute("street", PrimitiveType.STRING),
#               Attribute("city", PrimitiveType.STRING)
#           ]
#       )
#   }
#
#
# Example 2: Load from file
# -------------------------
#
# database = MongoDBAdapter.load_from_file("person.json", db_name="mydb")
#
#
# Example 3: Export back to MongoDB JSON Schema
# ---------------------------------------------
#
# json_schema = MongoDBAdapter.export_to_json(database)
# json_string = MongoDBAdapter.export_to_json_string(database, indent=2)
#
# Result preserves types:
#   {"bsonType": "objectId"} -> OBJECT_ID -> {"bsonType": "objectId"}
#   {"bsonType": "array", "items": ...} -> ListDataType -> {"bsonType": "array", "items": ...}
#
