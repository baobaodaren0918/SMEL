"""
MongoDB Adapter - Parse MongoDB JSON Schema to Unified Meta Schema.
Converts MongoDB JSON Schema (with bsonType) to Database/EntityType/Attribute objects.
"""
import json
from typing import Dict, Any, Optional, List
from ..unified_meta_schema import (
    Database, DatabaseType, EntityType, Attribute, Key, KeyType,
    Embedded, Cardinality, PrimitiveDataType, PrimitiveType
)


class MongoDBAdapter:
    """Adapter to parse MongoDB JSON Schema and create Unified Meta Schema."""

    # BSON type to PrimitiveType mapping
    TYPE_MAP = {
        'string': PrimitiveType.STRING,
        'int': PrimitiveType.INTEGER,
        'long': PrimitiveType.LONG,
        'double': PrimitiveType.DOUBLE,
        'decimal': PrimitiveType.DECIMAL,
        'bool': PrimitiveType.BOOLEAN,
        'date': PrimitiveType.DATE,
        'timestamp': PrimitiveType.TIMESTAMP,
        'objectId': PrimitiveType.STRING,
        'binData': PrimitiveType.BINARY,
        'null': PrimitiveType.NULL,
    }

    def __init__(self):
        self.database: Optional[Database] = None

    def parse(self, schema: Dict[str, Any], db_name: str = "database") -> Database:
        """Parse MongoDB JSON Schema and return Database object."""
        self.database = Database(db_name=db_name, db_type=DatabaseType.DOCUMENT)

        # Parse root document as main entity
        root_name = schema.get('title', 'root_document').lower().replace(' ', '_')
        root_entity = self._parse_object_schema(schema, root_name, is_root=True)
        self.database.add_entity_type(root_entity)

        return self.database

    def _parse_object_schema(self, schema: Dict[str, Any], name: str, is_root: bool = False) -> EntityType:
        """Parse an object schema into EntityType."""
        entity = EntityType(en_name=name)

        properties = schema.get('properties', {})
        required = set(schema.get('required', []))

        for prop_name, prop_schema in properties.items():
            prop_name_lower = prop_name.lower()
            is_required = prop_name in required

            # Handle different property types
            bson_type = prop_schema.get('bsonType') or prop_schema.get('type', 'string')

            if bson_type == 'object':
                # Embedded object
                embedded_entity = self._parse_object_schema(prop_schema, prop_name_lower)
                self.database.add_entity_type(embedded_entity)

                embedded = Embedded(
                    aggr_name=prop_name_lower,
                    aggregates=prop_name_lower,
                    cardinality=Cardinality.ONE_TO_ONE if is_required else Cardinality.ZERO_TO_ONE,
                    is_optional=not is_required
                )
                entity.add_relationship(embedded)

            elif bson_type == 'array':
                # Array - check if array of objects or primitives
                items = prop_schema.get('items', {})
                items_type = items.get('bsonType') or items.get('type', 'string')

                if items_type == 'object':
                    # Array of embedded objects
                    embedded_entity = self._parse_object_schema(items, prop_name_lower)
                    self.database.add_entity_type(embedded_entity)

                    embedded = Embedded(
                        aggr_name=prop_name_lower,
                        aggregates=prop_name_lower,
                        cardinality=Cardinality.ONE_TO_MANY if is_required else Cardinality.ZERO_TO_MANY,
                        is_optional=not is_required
                    )
                    entity.add_relationship(embedded)
                else:
                    # Array of primitives - treat as attribute
                    attr = Attribute(
                        attr_name=prop_name_lower,
                        data_type=self._parse_primitive_type(items_type, items),
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
                    key = Key(key_type=KeyType.PRIMARY)
                    key.add_attribute(attr)
                    entity.add_key(key)

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

    # Reverse mapping: PrimitiveType -> BSON type
    REVERSE_TYPE_MAP = {
        PrimitiveType.STRING: 'string',
        PrimitiveType.INTEGER: 'int',
        PrimitiveType.LONG: 'long',
        PrimitiveType.DOUBLE: 'double',
        PrimitiveType.DECIMAL: 'decimal',
        PrimitiveType.FLOAT: 'double',
        PrimitiveType.BOOLEAN: 'bool',
        PrimitiveType.DATE: 'date',
        PrimitiveType.TIMESTAMP: 'timestamp',
        PrimitiveType.BINARY: 'binData',
        PrimitiveType.UUID: 'string',
        PrimitiveType.NULL: 'null',
        PrimitiveType.TEXT: 'string',
    }

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
            schema["title"] = entity.en_name.replace('_', ' ')
            schema["description"] = f"MongoDB document schema for {entity.en_name}"

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
        """Export an attribute to MongoDB property schema."""
        bson_type = cls.REVERSE_TYPE_MAP.get(attr.data_type.primitive_type, 'string')

        prop = {
            "bsonType": bson_type
        }

        # Add maxLength for strings
        if attr.data_type.max_length and bson_type == 'string':
            prop["maxLength"] = attr.data_type.max_length

        return prop

    @classmethod
    def export_to_json_string(cls, database: Database, root_entity_name: str = None, indent: int = 2) -> str:
        """Export to formatted JSON string."""
        schema = cls.export_to_json(database, root_entity_name)
        return json.dumps(schema, indent=indent, ensure_ascii=False)
