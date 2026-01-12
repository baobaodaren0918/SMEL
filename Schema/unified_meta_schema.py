# Unified Meta Schema - Supports: PostgreSQL, MongoDB, Neo4j, Cassandra
# Based on André Conrad's meta_model design with extensions

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class DatabaseType(str, Enum):
    """Abstract database model types (not product-specific)."""
    RELATIONAL = "relational"   # PostgreSQL, MySQL, Oracle, SQL Server...
    DOCUMENT = "document"       # MongoDB, CouchDB, DocumentDB, Firestore...
    GRAPH = "graph"             # Neo4j, ArangoDB, JanusGraph, TigerGraph...
    COLUMNAR = "columnar"       # Cassandra, HBase, ScyllaDB, ClickHouse...


class EntityKind(str, Enum):
    TABLE = "table"                       # Standard relational table
    DOCUMENT = "document"                 # Top-level collection document (root entity)
    EMBEDDED = "embedded"                 # Nested/embedded document (non-root entity)
    VERTEX = "vertex"                     # Graph node (also called "Node")
    EDGE = "edge"                         # Graph relationship/edge
    WIDE_COLUMN_TABLE = "wide_column_table"  # Cassandra table with partition/clustering keys


class PrimitiveType(str, Enum):
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    LONG = "long"
    DOUBLE = "double"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"  # Use TIMESTAMP for datetime (DATETIME removed as duplicate)
    UUID = "uuid"
    BINARY = "binary"
    NULL = "null"
    OBJECT_ID = "objectId"
    INT32 = "int32"
    INT64 = "int64"
    DECIMAL128 = "decimal128"


class PKTypeEnum(str, Enum):
    """Primary key type for different database systems (from André Conrad)."""
    SIMPLE = "simple"           # Standard primary key
    PARTITION = "partition"     # Cassandra partition key
    CLUSTERING = "clustering"   # Cassandra clustering key


class Cardinality(str, Enum):
    ZERO_TO_ONE = "0..1"    # Optional, at most one
    ONE_TO_ONE = "1..1"     # Required, exactly one
    ZERO_TO_MANY = "0..n"   # Optional, unlimited
    ONE_TO_MANY = "1..n"    # Required, at least one

    @classmethod
    def from_symbol(cls, s: str) -> 'Cardinality':
        mapping = {
            "?": cls.ZERO_TO_ONE, "0..1": cls.ZERO_TO_ONE,
            "&": cls.ONE_TO_ONE, "1..1": cls.ONE_TO_ONE,
            "*": cls.ZERO_TO_MANY, "0..n": cls.ZERO_TO_MANY,
            "+": cls.ONE_TO_MANY, "1..n": cls.ONE_TO_MANY
        }
        return mapping.get(s, cls.ONE_TO_ONE)

    def to_bounds(self) -> tuple:
        """Returns (min, max) bounds. -1 means unlimited."""
        return {
            self.ZERO_TO_ONE: (0, 1),
            self.ONE_TO_ONE: (1, 1),
            self.ZERO_TO_MANY: (0, -1),
            self.ONE_TO_MANY: (1, -1)
        }[self]

    def is_multiple(self) -> bool:
        return self in (self.ZERO_TO_MANY, self.ONE_TO_MANY)

    def is_required(self) -> bool:
        return self in (self.ONE_TO_ONE, self.ONE_TO_MANY)


# ============================================================================
# TYPE MAPPINGS
# ============================================================================

_TYPE_MAPS = {
    DatabaseType.RELATIONAL: {
        PrimitiveType.STRING: "VARCHAR(255)", PrimitiveType.TEXT: "TEXT", PrimitiveType.INTEGER: "INTEGER",
        PrimitiveType.LONG: "BIGINT", PrimitiveType.DOUBLE: "DOUBLE PRECISION", PrimitiveType.FLOAT: "REAL",
        PrimitiveType.DECIMAL: "DECIMAL", PrimitiveType.BOOLEAN: "BOOLEAN", PrimitiveType.DATE: "DATE",
        PrimitiveType.TIMESTAMP: "TIMESTAMP", PrimitiveType.UUID: "UUID",
        PrimitiveType.BINARY: "BYTEA", PrimitiveType.NULL: "NULL", PrimitiveType.OBJECT_ID: "VARCHAR(24)",
        PrimitiveType.INT32: "INTEGER", PrimitiveType.INT64: "BIGINT", PrimitiveType.DECIMAL128: "DECIMAL",
    },
    DatabaseType.DOCUMENT: {
        PrimitiveType.STRING: "string", PrimitiveType.TEXT: "string", PrimitiveType.INTEGER: "int",
        PrimitiveType.LONG: "long", PrimitiveType.DOUBLE: "double", PrimitiveType.FLOAT: "double",
        PrimitiveType.DECIMAL: "decimal", PrimitiveType.BOOLEAN: "bool", PrimitiveType.DATE: "date",
        PrimitiveType.TIMESTAMP: "timestamp", PrimitiveType.UUID: "binData",
        PrimitiveType.BINARY: "binData", PrimitiveType.NULL: "null", PrimitiveType.OBJECT_ID: "objectId",
        PrimitiveType.INT32: "int", PrimitiveType.INT64: "long", PrimitiveType.DECIMAL128: "decimal",
    },
    DatabaseType.GRAPH: {
        PrimitiveType.STRING: "String", PrimitiveType.TEXT: "String", PrimitiveType.INTEGER: "Integer",
        PrimitiveType.LONG: "Long", PrimitiveType.DOUBLE: "Double", PrimitiveType.FLOAT: "Float",
        PrimitiveType.DECIMAL: "Double", PrimitiveType.BOOLEAN: "Boolean", PrimitiveType.DATE: "Date",
        PrimitiveType.TIMESTAMP: "DateTime", PrimitiveType.UUID: "String",
        PrimitiveType.BINARY: "ByteArray", PrimitiveType.NULL: "null", PrimitiveType.OBJECT_ID: "String",
        PrimitiveType.INT32: "Integer", PrimitiveType.INT64: "Long", PrimitiveType.DECIMAL128: "Double",
    },
    DatabaseType.COLUMNAR: {
        PrimitiveType.STRING: "text", PrimitiveType.TEXT: "text", PrimitiveType.INTEGER: "int",
        PrimitiveType.LONG: "bigint", PrimitiveType.DOUBLE: "double", PrimitiveType.FLOAT: "float",
        PrimitiveType.DECIMAL: "decimal", PrimitiveType.BOOLEAN: "boolean", PrimitiveType.DATE: "date",
        PrimitiveType.TIMESTAMP: "timestamp", PrimitiveType.UUID: "uuid",
        PrimitiveType.BINARY: "blob", PrimitiveType.NULL: "text", PrimitiveType.OBJECT_ID: "text",
        PrimitiveType.INT32: "int", PrimitiveType.INT64: "bigint", PrimitiveType.DECIMAL128: "decimal",
    },
}


def _get_native_type(ptype: PrimitiveType, db: DatabaseType) -> str:
    return _TYPE_MAPS[db][ptype]


# ============================================================================
# ADAPTER TYPE MAPPINGS (Centralized)
# ============================================================================
# These mappings are used by adapters for parsing and exporting schemas.
# All adapters should import these from here to avoid duplication.

class TypeMappings:
    """Centralized type mappings for all database adapters."""

    # -------------------------------------------------------------------------
    # PostgreSQL Mappings
    # -------------------------------------------------------------------------
    # SQL type string -> PrimitiveType (for parsing DDL)
    POSTGRESQL_TO_PRIMITIVE = {
        # Auto-increment types
        'SERIAL': PrimitiveType.INTEGER,
        'BIGSERIAL': PrimitiveType.LONG,
        # Integer types
        'INTEGER': PrimitiveType.INTEGER,
        'INT': PrimitiveType.INTEGER,
        'BIGINT': PrimitiveType.LONG,
        'SMALLINT': PrimitiveType.INTEGER,
        # Decimal types
        'DECIMAL': PrimitiveType.DECIMAL,
        'NUMERIC': PrimitiveType.DECIMAL,
        'REAL': PrimitiveType.FLOAT,
        'DOUBLE PRECISION': PrimitiveType.DOUBLE,
        'FLOAT': PrimitiveType.FLOAT,
        # String types
        'VARCHAR': PrimitiveType.STRING,
        'CHAR': PrimitiveType.STRING,
        'TEXT': PrimitiveType.STRING,
        # Boolean
        'BOOLEAN': PrimitiveType.BOOLEAN,
        'BOOL': PrimitiveType.BOOLEAN,
        # Date/Time types
        'DATE': PrimitiveType.DATE,
        'TIMESTAMP': PrimitiveType.TIMESTAMP,
        'TIME': PrimitiveType.TIMESTAMP,
        # Other types
        'UUID': PrimitiveType.UUID,
        'BYTEA': PrimitiveType.BINARY,
        'JSON': PrimitiveType.STRING,
        'JSONB': PrimitiveType.STRING,
    }

    # PrimitiveType -> SQL type string (for exporting DDL)
    PRIMITIVE_TO_POSTGRESQL = {
        PrimitiveType.INTEGER: 'INTEGER',
        PrimitiveType.LONG: 'BIGINT',
        PrimitiveType.STRING: 'VARCHAR',
        PrimitiveType.TEXT: 'TEXT',
        PrimitiveType.DECIMAL: 'DECIMAL',
        PrimitiveType.FLOAT: 'REAL',
        PrimitiveType.DOUBLE: 'DOUBLE PRECISION',
        PrimitiveType.BOOLEAN: 'BOOLEAN',
        PrimitiveType.DATE: 'DATE',
        PrimitiveType.TIMESTAMP: 'TIMESTAMP',
        PrimitiveType.UUID: 'UUID',
        PrimitiveType.BINARY: 'BYTEA',
        PrimitiveType.OBJECT_ID: 'VARCHAR',
    }

    # -------------------------------------------------------------------------
    # MongoDB Mappings
    # -------------------------------------------------------------------------
    # BSON type string -> PrimitiveType (for parsing JSON Schema)
    MONGODB_TO_PRIMITIVE = {
        'string': PrimitiveType.STRING,
        'int': PrimitiveType.INTEGER,
        'long': PrimitiveType.LONG,
        'double': PrimitiveType.DOUBLE,
        'decimal': PrimitiveType.DECIMAL,
        'bool': PrimitiveType.BOOLEAN,
        'date': PrimitiveType.DATE,
        'timestamp': PrimitiveType.TIMESTAMP,
        'objectId': PrimitiveType.OBJECT_ID,
        'binData': PrimitiveType.BINARY,
        'null': PrimitiveType.NULL,
    }

    # PrimitiveType -> BSON type string (for exporting JSON Schema)
    PRIMITIVE_TO_MONGODB = {
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
        PrimitiveType.OBJECT_ID: 'objectId',
    }

    # -------------------------------------------------------------------------
    # Display Mappings (for UI/reports)
    # -------------------------------------------------------------------------
    # PrimitiveType -> PostgreSQL display format
    PRIMITIVE_TO_PG_DISPLAY = {
        PrimitiveType.INTEGER: 'INTEGER',
        PrimitiveType.LONG: 'BIGINT',
        PrimitiveType.STRING: 'VARCHAR',
        PrimitiveType.TEXT: 'TEXT',
        PrimitiveType.DECIMAL: 'DECIMAL',
        PrimitiveType.FLOAT: 'REAL',
        PrimitiveType.DOUBLE: 'DOUBLE PRECISION',
        PrimitiveType.BOOLEAN: 'BOOLEAN',
        PrimitiveType.DATE: 'DATE',
        PrimitiveType.TIMESTAMP: 'TIMESTAMP',
        PrimitiveType.UUID: 'UUID',
        PrimitiveType.BINARY: 'BYTEA',
    }

    # PrimitiveType -> MongoDB display format
    PRIMITIVE_TO_MONGO_DISPLAY = {
        PrimitiveType.STRING: 'string',
        PrimitiveType.INTEGER: 'int',
        PrimitiveType.LONG: 'long',
        PrimitiveType.DOUBLE: 'double',
        PrimitiveType.DECIMAL: 'decimal',
        PrimitiveType.FLOAT: 'double',
        PrimitiveType.BOOLEAN: 'bool',
        PrimitiveType.DATE: 'date',
        PrimitiveType.TIMESTAMP: 'timestamp',
        PrimitiveType.UUID: 'string',
        PrimitiveType.BINARY: 'binData',
        PrimitiveType.OBJECT_ID: 'objectId',
    }


# ============================================================================
# DATA TYPES
# ============================================================================

def _uid() -> str:
    return str(uuid.uuid4())


@dataclass
class DataType(ABC):
    @abstractmethod
    def to_native(self, db: DatabaseType) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataType':
        """Factory method to create appropriate DataType subclass."""
        kind = data.get("kind", "primitive")
        if kind == "primitive":
            return PrimitiveDataType.from_dict(data)
        elif kind == "list":
            return ListDataType.from_dict(data)
        elif kind == "set":
            return SetDataType.from_dict(data)
        elif kind == "map":
            return MapDataType.from_dict(data)
        raise ValueError(f"Unknown DataType kind: {kind}")


@dataclass
class PrimitiveDataType(DataType):
    primitive_type: PrimitiveType
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None

    def to_native(self, db: DatabaseType) -> str:
        base = _get_native_type(self.primitive_type, db)
        if db == DatabaseType.RELATIONAL:
            if self.primitive_type == PrimitiveType.STRING and self.max_length:
                return f"VARCHAR({self.max_length})"
            if self.primitive_type == PrimitiveType.DECIMAL and self.precision:
                return f"DECIMAL({self.precision},{self.scale or 0})"
        return base

    def to_dict(self) -> Dict[str, Any]:
        d = {"kind": "primitive", "type": self.primitive_type.value}
        if self.max_length:
            d["max_length"] = self.max_length
        if self.precision:
            d["precision"] = self.precision
        if self.scale:
            d["scale"] = self.scale
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrimitiveDataType':
        try:
            pt = PrimitiveType(data.get("type", "string"))
        except ValueError:
            pt = PrimitiveType.STRING
        return cls(
            primitive_type=pt,
            max_length=data.get("max_length"),
            precision=data.get("precision"),
            scale=data.get("scale")
        )


@dataclass
class ListDataType(DataType):
    element_type: DataType

    def to_native(self, db: DatabaseType) -> str:
        m = {
            DatabaseType.RELATIONAL: f"{self.element_type.to_native(db)}[]",
            DatabaseType.DOCUMENT: "array",
            DatabaseType.GRAPH: f"List<{self.element_type.to_native(db)}>",
            DatabaseType.COLUMNAR: f"list<{self.element_type.to_native(db)}>"
        }
        return m.get(db, "array")

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "list", "element_type": self.element_type.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ListDataType':
        element_type = DataType.from_dict(data.get("element_type", {"kind": "primitive", "type": "string"}))
        return cls(element_type=element_type)


@dataclass
class SetDataType(DataType):
    element_type: DataType

    def to_native(self, db: DatabaseType) -> str:
        if db == DatabaseType.COLUMNAR:
            return f"set<{self.element_type.to_native(db)}>"
        return f"{self.element_type.to_native(db)}[]" if db == DatabaseType.RELATIONAL else "array"

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "set", "element_type": self.element_type.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SetDataType':
        element_type = DataType.from_dict(data.get("element_type", {"kind": "primitive", "type": "string"}))
        return cls(element_type=element_type)


@dataclass
class MapDataType(DataType):
    key_type: DataType
    value_type: DataType

    def to_native(self, db: DatabaseType) -> str:
        if db == DatabaseType.COLUMNAR:
            return f"map<{self.key_type.to_native(db)}, {self.value_type.to_native(db)}>"
        return {"RELATIONAL": "JSONB", "DOCUMENT": "object", "GRAPH": "Map"}.get(db.name, "JSONB")

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "map", "key_type": self.key_type.to_dict(), "value_type": self.value_type.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MapDataType':
        key_type = DataType.from_dict(data.get("key_type", {"kind": "primitive", "type": "string"}))
        value_type = DataType.from_dict(data.get("value_type", {"kind": "primitive", "type": "string"}))
        return cls(key_type=key_type, value_type=value_type)


# ============================================================================
# ATTRIBUTE
# ============================================================================

@dataclass
class Attribute:
    attr_name: str
    data_type: DataType
    is_key: bool = False
    is_optional: bool = True
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid)

    @property
    def name(self) -> str:
        return self.attr_name

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "kind": "attribute",
            "meta_id": self.meta_id,
            "attr_name": self.attr_name,
            "data_type": self.data_type.to_dict(),
            "is_key": self.is_key,
            "is_optional": self.is_optional
        }
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Attribute':
        dt = DataType.from_dict(data.get("data_type", {"kind": "primitive", "type": "string"}))
        return cls(
            attr_name=data.get("attr_name", ""),
            data_type=dt,
            is_key=data.get("is_key", False),
            is_optional=data.get("is_optional", True),
            description=data.get("description"),
            meta_id=data.get("meta_id", _uid())
        )


# ============================================================================
# CONSTRAINTS (from André Conrad)
# ============================================================================

@dataclass
class UniqueProperty:
    """Property that is part of a unique/primary key constraint (from André Conrad).
    Uses property_id to reference Attribute by meta_id instead of embedding the object.
    """
    primary_key_type: PKTypeEnum
    property_id: str  # References Attribute.meta_id
    meta_id: str = field(default_factory=_uid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta_id": self.meta_id,
            "primary_key_type": self.primary_key_type.value,
            "property_id": self.property_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UniqueProperty':
        try:
            pk_type = PKTypeEnum(data.get("primary_key_type", "simple"))
        except ValueError:
            pk_type = PKTypeEnum.SIMPLE
        return cls(
            primary_key_type=pk_type,
            property_id=data.get("property_id", ""),
            meta_id=data.get("meta_id", _uid())
        )


@dataclass
class ForeignKeyProperty:
    """Property that is part of a foreign key constraint (from André Conrad).
    Uses IDs to reference properties instead of embedding objects.
    """
    property_id: str  # References Attribute.meta_id (the FK column)
    points_to_unique_property_id: str  # References target UniqueProperty.meta_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "points_to_unique_property_id": self.points_to_unique_property_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ForeignKeyProperty':
        return cls(
            property_id=data.get("property_id", ""),
            points_to_unique_property_id=data.get("points_to_unique_property_id", "")
        )


class Constraint(ABC):
    """Abstract base class for constraints."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Constraint':
        """Factory method to create appropriate Constraint subclass."""
        constraint_type = data.get("constraint_type")
        if constraint_type == "unique":
            return UniqueConstraint.from_dict(data)
        elif constraint_type == "foreign_key":
            return ForeignKeyConstraint.from_dict(data)
        raise ValueError(f"Unknown constraint type: {constraint_type}")


@dataclass
class UniqueConstraint(Constraint):
    """Unique or Primary Key constraint (from André Conrad)."""
    is_primary_key: bool
    is_managed: bool
    unique_properties: List[UniqueProperty] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_type": "unique",
            "is_primary_key": self.is_primary_key,
            "is_managed": self.is_managed,
            "unique_properties": [up.to_dict() for up in self.unique_properties]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UniqueConstraint':
        unique_props = [UniqueProperty.from_dict(up) for up in data.get("unique_properties", [])]
        return cls(
            is_primary_key=data.get("is_primary_key", False),
            is_managed=data.get("is_managed", True),
            unique_properties=unique_props
        )

    def get_property_ids(self) -> List[str]:
        """Get list of property IDs (Attribute meta_ids) in this constraint."""
        return [up.property_id for up in self.unique_properties]


@dataclass
class ForeignKeyConstraint(Constraint):
    """Foreign Key constraint (from André Conrad)."""
    is_managed: bool
    foreign_key_properties: List[ForeignKeyProperty] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_type": "foreign_key",
            "is_managed": self.is_managed,
            "foreign_key_properties": [fkp.to_dict() for fkp in self.foreign_key_properties]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ForeignKeyConstraint':
        fk_props = [ForeignKeyProperty.from_dict(fkp) for fkp in data.get("foreign_key_properties", [])]
        return cls(
            is_managed=data.get("is_managed", True),
            foreign_key_properties=fk_props
        )

    def get_property_ids(self) -> List[str]:
        """Get list of property IDs (Attribute meta_ids) in this constraint."""
        return [fkp.property_id for fkp in self.foreign_key_properties]


# ============================================================================
# RELATIONSHIPS
# ============================================================================

@dataclass
class Relationship(ABC):
    cardinality: Cardinality = Cardinality.ONE_TO_ONE
    is_optional: bool = True
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid)

    @property
    def lower_bound(self) -> int:
        return self.cardinality.to_bounds()[0]

    @property
    def upper_bound(self) -> int:
        return self.cardinality.to_bounds()[1]

    @abstractmethod
    def get_target_entity_name(self) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """Factory method to create appropriate Relationship subclass."""
        kind = data.get("kind")
        if kind == "reference":
            return Reference.from_dict(data)
        elif kind in ("aggregate", "embedded"):
            return Embedded.from_dict(data)
        raise ValueError(f"Unknown relationship kind: {kind}")


@dataclass
class Reference(Relationship):
    ref_name: str = ""
    refs_to: str = ""  # Entity name (string only, not object reference)
    edge_attributes: List[Attribute] = field(default_factory=list)

    def get_target_entity_name(self) -> str:
        return self.refs_to

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "kind": "reference",
            "meta_id": self.meta_id,
            "ref_name": self.ref_name,
            "refs_to": self.refs_to,
            "cardinality": self.cardinality.value,
            "is_optional": self.is_optional
        }
        if self.edge_attributes:
            d["edge_attributes"] = [a.to_dict() for a in self.edge_attributes]
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reference':
        edge_attrs = [Attribute.from_dict(a) for a in data.get("edge_attributes", [])]
        return cls(
            ref_name=data.get("ref_name", ""),
            refs_to=data.get("refs_to", ""),
            cardinality=Cardinality.from_symbol(data.get("cardinality", "1..1")),
            is_optional=data.get("is_optional", True),
            description=data.get("description"),
            meta_id=data.get("meta_id", _uid()),
            edge_attributes=edge_attrs
        )


@dataclass
class Embedded(Relationship):
    """Embedded/Aggregate relationship for nested documents (MongoDB style)."""
    aggr_name: str = ""
    aggregates: str = ""  # Entity name (string only, not object reference)

    def get_target_entity_name(self) -> str:
        return self.aggregates

    def is_array(self) -> bool:
        return self.cardinality.is_multiple()

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "kind": "embedded",
            "meta_id": self.meta_id,
            "aggr_name": self.aggr_name,
            "aggregates": self.aggregates,
            "cardinality": self.cardinality.value,
            "is_optional": self.is_optional,
            "is_array": self.is_array()
        }
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Embedded':
        return cls(
            aggr_name=data.get("aggr_name", data.get("em_name", "")),
            aggregates=data.get("aggregates", data.get("embeds", "")),
            cardinality=Cardinality.from_symbol(data.get("cardinality", "1..1")),
            is_optional=data.get("is_optional", True),
            description=data.get("description"),
            meta_id=data.get("meta_id", _uid())
        )


# Alias for backward compatibility
Aggregate = Embedded


# ============================================================================
# STRUCTURAL VARIATION
# ============================================================================

@dataclass
class StructuralVariation:
    variation_id: int
    attributes: List[Attribute] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    count: int = 0
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None

    def add_attribute(self, attr: Attribute):
        if attr not in self.attributes:
            self.attributes.append(attr)

    def add_relationship(self, rel: Relationship):
        if rel not in self.relationships:
            self.relationships.append(rel)

    def get_attribute(self, name: str) -> Optional[Attribute]:
        return next((a for a in self.attributes if a.attr_name == name), None)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "variation_id": self.variation_id,
            "attributes": [a.to_dict() for a in self.attributes],
            "relationships": [r.to_dict() for r in self.relationships],
            "count": self.count
        }
        if self.first_timestamp:
            d["first_timestamp"] = self.first_timestamp
        if self.last_timestamp:
            d["last_timestamp"] = self.last_timestamp
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuralVariation':
        attrs = [Attribute.from_dict(a) for a in data.get("attributes", [])]
        rels = [Relationship.from_dict(r) for r in data.get("relationships", [])]
        return cls(
            variation_id=data.get("variation_id", 0),
            attributes=attrs,
            relationships=rels,
            count=data.get("count", 0),
            first_timestamp=data.get("first_timestamp"),
            last_timestamp=data.get("last_timestamp")
        )


# ============================================================================
# ENTITY TYPE
# ============================================================================

@dataclass
class EntityType:
    """Unifies the definition of database entities (from André Conrad with List[str] naming)."""
    object_name: List[str]  # from André Conrad: ["schema", "table"] or ["collection", "embedded"]
    entity_kind: EntityKind = EntityKind.TABLE
    is_root: bool = True
    constraints: List[Constraint] = field(default_factory=list)
    attributes: List[Attribute] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    variations: List[StructuralVariation] = field(default_factory=list)
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid)

    @property
    def name(self) -> str:
        """Get simple name (last element of path)."""
        return self.object_name[-1] if self.object_name else ""

    @property
    def full_path(self) -> str:
        """Get full path as dot-separated string."""
        return ".".join(self.object_name)

    @property
    def parent_path(self) -> List[str]:
        """Get parent path (all elements except last)."""
        return self.object_name[:-1] if len(self.object_name) > 1 else []

    # Backward compatibility alias
    @property
    def en_name(self) -> str:
        """Backward compatibility: returns simple name."""
        return self.name

    # Constraint methods
    def add_constraint(self, constraint: Constraint):
        self.constraints.append(constraint)

    def get_primary_key(self) -> Optional[UniqueConstraint]:
        """Get the primary key constraint."""
        for c in self.constraints:
            if isinstance(c, UniqueConstraint) and c.is_primary_key:
                return c
        return None

    def get_unique_constraints(self) -> List[UniqueConstraint]:
        """Get all unique constraints (non-primary)."""
        return [c for c in self.constraints if isinstance(c, UniqueConstraint) and not c.is_primary_key]

    def get_foreign_keys(self) -> List[ForeignKeyConstraint]:
        """Get all foreign key constraints."""
        return [c for c in self.constraints if isinstance(c, ForeignKeyConstraint)]

    # Attribute methods
    def add_attribute(self, attr: Attribute):
        self.attributes.append(attr)

    def get_attribute(self, name: str) -> Optional[Attribute]:
        return next((a for a in self.attributes if a.attr_name == name), None)

    def get_attribute_by_id(self, meta_id: str) -> Optional[Attribute]:
        """Get attribute by its meta_id (used for constraint property_id lookup)."""
        return next((a for a in self.attributes if a.meta_id == meta_id), None)

    def remove_attribute(self, name: str) -> Optional[Attribute]:
        for i, a in enumerate(self.attributes):
            if a.attr_name == name:
                return self.attributes.pop(i)
        return None

    # Relationship methods
    def add_relationship(self, rel: Relationship):
        self.relationships.append(rel)

    def get_references(self) -> List[Reference]:
        return [r for r in self.relationships if isinstance(r, Reference)]

    def get_embedded(self) -> List[Embedded]:
        """Get all embedded relationships."""
        return [r for r in self.relationships if isinstance(r, Embedded)]

    # Backward compatibility alias
    def get_aggregates(self) -> List[Embedded]:
        return self.get_embedded()

    def remove_relationship(self, name: str) -> Optional[Relationship]:
        for i, r in enumerate(self.relationships):
            rel_name = r.ref_name if isinstance(r, Reference) else r.aggr_name
            if rel_name == name:
                return self.relationships.pop(i)
        return None

    # Variation methods
    def add_variation(self, v: StructuralVariation):
        self.variations.append(v)

    def get_variation(self, vid: int) -> Optional[StructuralVariation]:
        return next((v for v in self.variations if v.variation_id == vid), None)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "meta_id": self.meta_id,
            "object_name": self.object_name,  # from André Conrad: List[str]
            "entity_kind": self.entity_kind.value,
            "is_root": self.is_root,
            "constraints": [c.to_dict() for c in self.constraints],
            "attributes": [a.to_dict() for a in self.attributes],
            "relationships": [r.to_dict() for r in self.relationships]
        }
        if self.variations:
            d["variations"] = [v.to_dict() for v in self.variations]
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityType':
        try:
            kind = EntityKind(data.get("entity_kind", "table"))
        except ValueError:
            kind = EntityKind.TABLE

        constraints = [Constraint.from_dict(c) for c in data.get("constraints", [])]
        attrs = [Attribute.from_dict(a) for a in data.get("attributes", [])]
        rels = [Relationship.from_dict(r) for r in data.get("relationships", [])]
        variations = [StructuralVariation.from_dict(v) for v in data.get("variations", [])]

        # Support both old (en_name) and new (object_name) formats
        object_name = data.get("object_name")
        if object_name is None:
            # Backward compatibility: convert en_name to object_name
            en_name = data.get("en_name", "")
            object_name = en_name.split(".") if en_name else [""]

        return cls(
            object_name=object_name,
            entity_kind=kind,
            is_root=data.get("is_root", True),
            constraints=constraints,
            attributes=attrs,
            relationships=rels,
            variations=variations,
            description=data.get("description"),
            meta_id=data.get("meta_id", _uid())
        )


# ============================================================================
# RELATIONSHIP TYPE (Neo4j edge type)
# ============================================================================

@dataclass
class RelationshipType:
    """Neo4j edge type."""
    rel_name: str
    source_entity: str = ""  # Entity name (string only)
    target_entity: str = ""  # Entity name (string only)
    attributes: List[Attribute] = field(default_factory=list)
    cardinality: Cardinality = Cardinality.ZERO_TO_MANY
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid)

    @property
    def name(self) -> str:
        return self.rel_name

    def get_source_name(self) -> str:
        return self.source_entity

    def get_target_name(self) -> str:
        return self.target_entity

    def add_attribute(self, attr: Attribute):
        self.attributes.append(attr)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "meta_id": self.meta_id,
            "rel_name": self.rel_name,
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "attributes": [a.to_dict() for a in self.attributes],
            "cardinality": self.cardinality.value
        }
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationshipType':
        attrs = [Attribute.from_dict(a) for a in data.get("attributes", [])]
        return cls(
            rel_name=data.get("rel_name", ""),
            source_entity=data.get("source_entity", ""),
            target_entity=data.get("target_entity", ""),
            attributes=attrs,
            cardinality=Cardinality.from_symbol(data.get("cardinality", "0..n")),
            description=data.get("description"),
            meta_id=data.get("meta_id", _uid())
        )


# ============================================================================
# DATABASE (TOP-LEVEL)
# ============================================================================

@dataclass
class Database:
    db_name: str
    db_type: DatabaseType = DatabaseType.RELATIONAL
    entity_types: Dict[str, EntityType] = field(default_factory=dict)
    relationship_types: Dict[str, RelationshipType] = field(default_factory=dict)
    version: int = 1
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid)

    # Entity management
    def add_entity_type(self, e: EntityType):
        """Add entity using full_path as key."""
        self.entity_types[e.full_path] = e

    def get_entity_type(self, name: str) -> Optional[EntityType]:
        """Get entity by name (supports both full_path and simple name)."""
        # First try exact match (full_path)
        if name in self.entity_types:
            return self.entity_types.get(name)
        # Fallback: search by simple name for backward compatibility
        for entity in self.entity_types.values():
            if entity.name == name:
                return entity
        return None

    def remove_entity_type(self, name: str) -> Optional[EntityType]:
        """Remove entity by name (supports both full_path and simple name)."""
        if name in self.entity_types:
            return self.entity_types.pop(name, None)
        # Fallback: search by simple name
        for key, entity in list(self.entity_types.items()):
            if entity.name == name:
                return self.entity_types.pop(key, None)
        return None

    # RelationshipType management (Neo4j)
    def add_relationship_type(self, r: RelationshipType):
        self.relationship_types[r.rel_name] = r

    def get_relationship_type(self, name: str) -> Optional[RelationshipType]:
        return self.relationship_types.get(name)

    def remove_relationship_type(self, name: str) -> Optional[RelationshipType]:
        return self.relationship_types.pop(name, None)

    def increment_version(self) -> int:
        self.version += 1
        return self.version

    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "meta_id": self.meta_id,
            "db_name": self.db_name,
            "db_type": self.db_type.value,
            "version": self.version,
            "entity_types": {n: e.to_dict() for n, e in self.entity_types.items()}
        }
        if self.relationship_types:
            d["relationship_types"] = {n: r.to_dict() for n, r in self.relationship_types.items()}
        if self.description:
            d["description"] = self.description
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    # Deserialization
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Database':
        try:
            db_type = DatabaseType(data.get("db_type", "relational"))
        except ValueError:
            db_type = DatabaseType.RELATIONAL

        db = cls(
            db_name=data.get("db_name", "unknown"),
            db_type=db_type,
            version=data.get("version", 1),
            description=data.get("description"),
            meta_id=data.get("meta_id", _uid())
        )

        # Load entity types
        for e_data in data.get("entity_types", {}).values():
            entity = EntityType.from_dict(e_data)
            db.add_entity_type(entity)

        # Load relationship types
        for r_data in data.get("relationship_types", {}).values():
            rel_type = RelationshipType.from_dict(r_data)
            db.add_relationship_type(rel_type)

        return db

    @classmethod
    def load_from_file(cls, path: str) -> 'Database':
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))


# Alias
UnifiedMetaSchema = Database

__all__ = [
    'DatabaseType', 'EntityKind', 'PrimitiveType', 'PKTypeEnum', 'Cardinality',
    'DataType', 'PrimitiveDataType', 'ListDataType', 'SetDataType', 'MapDataType',
    'Attribute', 'Constraint', 'UniqueProperty', 'ForeignKeyProperty',
    'UniqueConstraint', 'ForeignKeyConstraint',
    'Relationship', 'Reference', 'Embedded',
    'StructuralVariation', 'EntityType', 'RelationshipType',
    'Database', 'UnifiedMetaSchema', 'TypeMappings'
]
