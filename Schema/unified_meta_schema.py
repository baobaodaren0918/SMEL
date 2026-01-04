# Supports: PostgreSQL, MongoDB, Neo4j, Cassandra

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json, uuid

class DatabaseType(str, Enum):
    """Abstract database model types (not product-specific)."""
    RELATIONAL = "relational"   # PostgreSQL, MySQL, Oracle, SQL Server...
    DOCUMENT = "document"       # MongoDB, CouchDB, DocumentDB, Firestore...
    GRAPH = "graph"             # Neo4j, ArangoDB, JanusGraph, TigerGraph...
    COLUMNAR = "columnar"       # Cassandra, HBase, ScyllaDB, ClickHouse...


class EntityKind(str, Enum):
    TABLE = "table"   # Standard relational table
    DOCUMENT = "document"  # Top-level collection document (root entity)
    EMBEDDED = "embedded"  # Nested/embedded document (non-root entity)
    VERTEX = "vertex"  # Graph node (also called "Node")
    EDGE = "edge"  # Graph relationship/edge
    WIDE_COLUMN_TABLE = "wide_column_table" # Cassandra table with partition/clustering keys


class PrimitiveType(str, Enum):
    STRING = "string";
    TEXT = "text";
    INTEGER = "integer";
    LONG = "long"
    DOUBLE = "double";
    FLOAT = "float";
    DECIMAL = "decimal";
    BOOLEAN = "boolean"
    DATE = "date";
    DATETIME = "datetime";
    TIMESTAMP = "timestamp"
    UUID = "uuid";
    BINARY = "binary";
    NULL = "null"
    OBJECT_ID = "objectId";
    INT32 = "int32";
    INT64 = "int64";
    DECIMAL128 = "decimal128"


class KeyType(str, Enum):
    """Key constraint types for different database systems."""
    # All databases
    PRIMARY = "PRIMARY"       # Unique row/document identifier
    UNIQUE = "UNIQUE"         # No duplicate values allowed
    # PostgreSQL (Relational)
    FOREIGN = "FOREIGN"       # References another table
    # Cassandra (Wide-Column Store)
    PARTITION = "PARTITION"   # Data distribution across nodes
    CLUSTERING = "CLUSTERING" # Sort order within partition


class Cardinality(str, Enum):
    ZERO_TO_ONE = "?";
    ONE_TO_ONE = "&";
    ZERO_TO_MANY = "*";
    ONE_TO_MANY = "+"

    @classmethod
    def from_symbol(cls, s: str) -> 'Cardinality':
        return {"?": cls.ZERO_TO_ONE, "&": cls.ONE_TO_ONE, "*": cls.ZERO_TO_MANY, "+": cls.ONE_TO_MANY}.get(s,
                                                                                                            cls.ONE_TO_ONE)

    def to_bounds(self) -> tuple:
        """Returns (min, max) bounds. -1 means unlimited (n), matching SMEL.g4 cardinalityType."""
        return {
            self.ZERO_TO_ONE: (0, 1),   # ? = optional, at most one
            self.ONE_TO_ONE: (1, 1),    # & = required, exactly one
            self.ZERO_TO_MANY: (0, -1), # * = optional, unlimited (-1 = n = infinity)
            self.ONE_TO_MANY: (1, -1)   # + = required, unlimited (-1 = n = infinity)
        }[self]

    def is_multiple(self) -> bool: return self in (self.ZERO_TO_MANY, self.ONE_TO_MANY)

    def is_required(self) -> bool: return self in (self.ONE_TO_ONE, self.ONE_TO_MANY)


# ============================================================================
# TYPE MAPPINGS
# ============================================================================

_TYPE_MAPS = {
    DatabaseType.RELATIONAL: {
        PrimitiveType.STRING: "VARCHAR(255)", PrimitiveType.TEXT: "TEXT", PrimitiveType.INTEGER: "INTEGER",
        PrimitiveType.LONG: "BIGINT", PrimitiveType.DOUBLE: "DOUBLE PRECISION", PrimitiveType.FLOAT: "REAL",
        PrimitiveType.DECIMAL: "DECIMAL", PrimitiveType.BOOLEAN: "BOOLEAN", PrimitiveType.DATE: "DATE",
        PrimitiveType.DATETIME: "TIMESTAMP", PrimitiveType.TIMESTAMP: "TIMESTAMP", PrimitiveType.UUID: "UUID",
        PrimitiveType.BINARY: "BYTEA", PrimitiveType.NULL: "NULL", PrimitiveType.OBJECT_ID: "VARCHAR(24)",
        PrimitiveType.INT32: "INTEGER", PrimitiveType.INT64: "BIGINT", PrimitiveType.DECIMAL128: "DECIMAL",
    },
    DatabaseType.DOCUMENT: {  # MongoDB, CouchDB, etc.
        PrimitiveType.STRING: "string", PrimitiveType.TEXT: "string", PrimitiveType.INTEGER: "int",
        PrimitiveType.LONG: "long", PrimitiveType.DOUBLE: "double", PrimitiveType.FLOAT: "double",
        PrimitiveType.DECIMAL: "decimal", PrimitiveType.BOOLEAN: "bool", PrimitiveType.DATE: "date",
        PrimitiveType.DATETIME: "date", PrimitiveType.TIMESTAMP: "timestamp", PrimitiveType.UUID: "binData",
        PrimitiveType.BINARY: "binData", PrimitiveType.NULL: "null", PrimitiveType.OBJECT_ID: "objectId",
        PrimitiveType.INT32: "int", PrimitiveType.INT64: "long", PrimitiveType.DECIMAL128: "decimal",
    },
    DatabaseType.GRAPH: {  # Neo4j, ArangoDB, etc.
        PrimitiveType.STRING: "String", PrimitiveType.TEXT: "String", PrimitiveType.INTEGER: "Integer",
        PrimitiveType.LONG: "Long", PrimitiveType.DOUBLE: "Double", PrimitiveType.FLOAT: "Float",
        PrimitiveType.DECIMAL: "Double", PrimitiveType.BOOLEAN: "Boolean", PrimitiveType.DATE: "Date",
        PrimitiveType.DATETIME: "DateTime", PrimitiveType.TIMESTAMP: "DateTime", PrimitiveType.UUID: "String",
        PrimitiveType.BINARY: "ByteArray", PrimitiveType.NULL: "null", PrimitiveType.OBJECT_ID: "String",
        PrimitiveType.INT32: "Integer", PrimitiveType.INT64: "Long", PrimitiveType.DECIMAL128: "Double",
    },
    DatabaseType.COLUMNAR: {  # Cassandra, HBase, etc.
        PrimitiveType.STRING: "text", PrimitiveType.TEXT: "text", PrimitiveType.INTEGER: "int",
        PrimitiveType.LONG: "bigint", PrimitiveType.DOUBLE: "double", PrimitiveType.FLOAT: "float",
        PrimitiveType.DECIMAL: "decimal", PrimitiveType.BOOLEAN: "boolean", PrimitiveType.DATE: "date",
        PrimitiveType.DATETIME: "timestamp", PrimitiveType.TIMESTAMP: "timestamp", PrimitiveType.UUID: "uuid",
        PrimitiveType.BINARY: "blob", PrimitiveType.NULL: "text", PrimitiveType.OBJECT_ID: "text",
        PrimitiveType.INT32: "int", PrimitiveType.INT64: "bigint", PrimitiveType.DECIMAL128: "decimal",
    },
}


def _get_native_type(ptype: PrimitiveType, db: DatabaseType):
    return _TYPE_MAPS[db][ptype]


# ============================================================================
# DATA TYPES
# ============================================================================

@dataclass
class DataType(ABC):
    @abstractmethod
    def to_native(self, db: DatabaseType) -> str: pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]: pass # Any subclass inheriting from this class must implement the to_native() and to_dict() methods.


@dataclass
class PrimitiveDataType(DataType): # ← Inherits from DataType
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
        for k, v in [("max_length", self.max_length), ("precision", self.precision), ("scale", self.scale)]:
            if v: d[k] = v
        return d


@dataclass
class ListDataType(DataType):
    element_type: DataType

    def to_native(self, db: DatabaseType) -> str:
        m = {DatabaseType.RELATIONAL: f"{self.element_type.to_native(db)}[]", DatabaseType.DOCUMENT: "array",
             DatabaseType.GRAPH: f"List<{self.element_type.to_native(db)}>",
             DatabaseType.COLUMNAR: f"list<{self.element_type.to_native(db)}>"}
        return m.get(db, "array")

    def to_dict(self) -> Dict[str, Any]: return {"kind": "list", "element_type": self.element_type.to_dict()}


@dataclass
class SetDataType(DataType):
    element_type: DataType

    def to_native(self, db: DatabaseType) -> str:
        if db == DatabaseType.COLUMNAR: return f"set<{self.element_type.to_native(db)}>"
        return f"{self.element_type.to_native(db)}[]" if db == DatabaseType.RELATIONAL else "array"

    def to_dict(self) -> Dict[str, Any]: return {"kind": "set", "element_type": self.element_type.to_dict()}


@dataclass
class MapDataType(DataType):
    key_type: DataType
    value_type: DataType

    def to_native(self, db: DatabaseType) -> str:
        if db == DatabaseType.COLUMNAR: return f"map<{self.key_type.to_native(db)}, {self.value_type.to_native(db)}>"
        return {"RELATIONAL": "JSONB", "DOCUMENT": "object", "GRAPH": "Map"}.get(db.name, "JSONB")

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "map", "key_type": self.key_type.to_dict(), "value_type": self.value_type.to_dict()}


# SCHEMA ELEMENTS

def _uid() -> str: return str(uuid.uuid4())

@dataclass
class Attribute: #What columns are in the table?
    attr_name: str
    data_type: DataType #Column Name
    is_key: bool = False
    is_optional: bool = True
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid) #Each record must have a unique identifier

    @property
    def name(self) -> str: return self.attr_name

    def to_dict(self) -> Dict[str, Any]: #Save as a JSON file for easy storage and transmission
        d = {"kind": "attribute", "meta_id": self.meta_id, "attr_name": self.attr_name,
             "data_type": self.data_type.to_dict(), "is_key": self.is_key, "is_optional": self.is_optional}
        if self.description: d["description"] = self.description
        return d


@dataclass
class Key:
    key_type: KeyType #PRIMARY, UNIQUE, PostgreSQL：FOREIGN, Cassandra：Partition, CLUSTERING
    key_attributes: List[Attribute] = field(default_factory=list) #Key composition
    is_managed: bool = True #True if the value is auto-generated by the DB (e.g., Auto-Inc); False if it must be set manually.
    referenced_entity: Optional[str] = None # Is this a foreign key? Which table does it reference?
    referenced_attributes: List[str] = field(default_factory=list)#Which columns in the referenced table? (Required only for Foreign Keys)

    def add_attribute(self, attr: Attribute):
        attr.is_key = True
        if attr not in self.key_attributes: self.key_attributes.append(attr)

    def get_attribute_names(self) -> List[str]:
        return [a.attr_name for a in self.key_attributes]

    def to_dict(self) -> Dict[str, Any]:
        d = {"key_type": self.key_type.value, "attributes": self.get_attribute_names(), "is_managed": self.is_managed}
        if self.referenced_entity: d.update(referenced_entity=self.referenced_entity,
                                            referenced_attributes=self.referenced_attributes)
        return d


@dataclass
class Relationship(ABC):
    cardinality: Cardinality = Cardinality.ONE_TO_ONE
    is_optional: bool = True
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid)

    @property
    def lower_bound(self) -> int: return self.cardinality.to_bounds()[0]

    @property
    def upper_bound(self) -> int: return self.cardinality.to_bounds()[1]

    @abstractmethod
    def get_target_entity_name(self) -> str: pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]: pass


@dataclass
class Reference(Relationship):
    ref_name: str = ""
    refs_to: Union['EntityType', str] = ""
    edge_attributes: List[Attribute] = field(default_factory=list)

    def get_target_entity_name(self) -> str:
        return self.refs_to if isinstance(self.refs_to, str) else (self.refs_to.en_name if self.refs_to else "")

    def to_dict(self) -> Dict[str, Any]:
        d = {"kind": "reference", "meta_id": self.meta_id, "ref_name": self.ref_name,
             "refs_to": self.get_target_entity_name(), "cardinality": self.cardinality.value,
             "is_optional": self.is_optional}
        if self.edge_attributes: d["edge_attributes"] = [a.to_dict() for a in self.edge_attributes]
        if self.description: d["description"] = self.description
        return d


@dataclass
class Aggregate(Relationship):
    aggr_name: str = ""
    aggregates: Union['EntityType', str] = ""

    def get_target_entity_name(self) -> str:
        return self.aggregates if isinstance(self.aggregates, str) else (
            self.aggregates.en_name if self.aggregates else "")

    def is_array(self) -> bool: return self.cardinality.is_multiple()

    def to_dict(self) -> Dict[str, Any]:
        d = {"kind": "aggregate", "meta_id": self.meta_id, "aggr_name": self.aggr_name,
             "aggregates": self.get_target_entity_name(), "cardinality": self.cardinality.value,
             "is_optional": self.is_optional, "is_array": self.is_array()}
        if self.description: d["description"] = self.description
        return d


Embedded = Aggregate  # Alias


@dataclass
class StructuralVariation:
    variation_id: int
    attributes: List[Attribute] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    count: int = 0
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None

    def add_attribute(self, attr: Attribute):
        if attr not in self.attributes: self.attributes.append(attr)

    def add_relationship(self, rel: Relationship):
        if rel not in self.relationships: self.relationships.append(rel)

    def get_attribute(self, name: str) -> Optional[Attribute]:
        return next((a for a in self.attributes if a.attr_name == name), None)

    def to_dict(self) -> Dict[str, Any]:
        d = {"variation_id": self.variation_id, "attributes": [a.to_dict() for a in self.attributes],
             "relationships": [r.to_dict() for r in self.relationships], "count": self.count}
        if self.first_timestamp: d["first_timestamp"] = self.first_timestamp
        if self.last_timestamp: d["last_timestamp"] = self.last_timestamp
        return d

# ENTITY TYPE


@dataclass
class EntityType:#Unifies the definition of database entities.
    en_name: str
    entity_kind: EntityKind = EntityKind.TABLE
    is_root: bool = True
    keys: List[Key] = field(default_factory=list)
    attributes: List[Attribute] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    variations: List[StructuralVariation] = field(default_factory=list)
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid)

    @property
    def name(self) -> str:
        return self.en_name

    # Key methods
    def add_key(self, key: Key):
        """Add a key constraint to the entity."""
        self.keys.append(key)

    # Return single key (at most one per table)
    def get_primary_key(self) -> Optional[Key]:
        """Get the primary key (each table has at most one)."""
        return next((k for k in self.keys if k.key_type == KeyType.PRIMARY), None)

    def get_partition_key(self) -> Optional[Key]:
        """Get the partition key for Cassandra (each table has at most one)."""
        return next((k for k in self.keys if k.key_type == KeyType.PARTITION), None)

    # Return list (may have multiple)
    def get_unique_keys(self) -> List[Key]:
        """Get all unique constraints (a table may have multiple)."""
        return [k for k in self.keys if k.key_type == KeyType.UNIQUE]

    def get_foreign_keys(self) -> List[Key]:
        """Get all foreign keys (a table may have multiple)."""
        return [k for k in self.keys if k.key_type == KeyType.FOREIGN]

    def get_clustering_keys(self) -> List[Key]:
        """Get all clustering keys for Cassandra (may have multiple)."""
        return [k for k in self.keys if k.key_type == KeyType.CLUSTERING]

    # Attribute methods
    def add_attribute(self, attr: Attribute):
        self.attributes.append(attr)

    def get_attribute(self, name: str) -> Optional[Attribute]:
        return next((a for a in self.attributes if a.attr_name == name), None)

    def remove_attribute(self, name: str) -> Optional[Attribute]:
        for i, a in enumerate(self.attributes):
            if a.attr_name == name: return self.attributes.pop(i)
        return None

    # Relationship methods
    def add_relationship(self, rel: Relationship):
        self.relationships.append(rel)

    def get_references(self) -> List[Reference]:
        return [r for r in self.relationships if isinstance(r, Reference)]

    def get_aggregates(self) -> List[Aggregate]:
        return [r for r in self.relationships if isinstance(r, Aggregate)]

    def remove_relationship(self, name: str) -> Optional[Relationship]:
        for i, r in enumerate(self.relationships):
            if (r.ref_name if isinstance(r, Reference) else r.aggr_name) == name: return self.relationships.pop(i)
        return None

    # Variation methods
    def add_variation(self, v: StructuralVariation):
        self.variations.append(v)

    def get_variation(self, vid: int) -> Optional[StructuralVariation]:
        return next((v for v in self.variations if v.variation_id == vid), None)

    def to_dict(self) -> Dict[str, Any]:
        d = {"meta_id": self.meta_id, "en_name": self.en_name, "entity_kind": self.entity_kind.value,
             "is_root": self.is_root,
             "keys": [k.to_dict() for k in self.keys], "attributes": [a.to_dict() for a in self.attributes],
             "relationships": [r.to_dict() for r in self.relationships]}
        if self.variations: d["variations"] = [v.to_dict() for v in self.variations]
        if self.description: d["description"] = self.description
        return d


@dataclass
class RelationshipType:
    """Neo4j edge type."""
    rel_name: str
    source_entity: Union[EntityType, str] = ""
    target_entity: Union[EntityType, str] = ""
    attributes: List[Attribute] = field(default_factory=list)
    cardinality: Cardinality = Cardinality.ZERO_TO_MANY
    description: Optional[str] = None
    meta_id: str = field(default_factory=_uid)

    @property
    def name(self) -> str: return self.rel_name

    def get_source_name(self) -> str: return self.source_entity if isinstance(self.source_entity, str) else (
        self.source_entity.en_name if self.source_entity else "")

    def get_target_name(self) -> str: return self.target_entity if isinstance(self.target_entity, str) else (
        self.target_entity.en_name if self.target_entity else "")

    def add_attribute(self, attr: Attribute): self.attributes.append(attr)

    def to_dict(self) -> Dict[str, Any]:
        d = {"meta_id": self.meta_id, "rel_name": self.rel_name, "source_entity": self.get_source_name(),
             "target_entity": self.get_target_name(), "attributes": [a.to_dict() for a in self.attributes],
             "cardinality": self.cardinality.value}
        if self.description: d["description"] = self.description
        return d

# DATABASE (TOP-LEVEL)
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
        self.entity_types[e.en_name] = e

    def get_entity_type(self, name: str) -> Optional[EntityType]:
        return self.entity_types.get(name)

    def remove_entity_type(self, name: str) -> Optional[EntityType]:
        return self.entity_types.pop(name, None)

    # RelationshipType management (Neo4j)
    def add_relationship_type(self, r: RelationshipType):
        self.relationship_types[r.rel_name] = r

    def get_relationship_type(self, name: str) -> Optional[RelationshipType]:
        return self.relationship_types.get(name)

    def remove_relationship_type(self, name: str) -> Optional[RelationshipType]:
        return self.relationship_types.pop(name, None)

    def increment_version(self) -> int:
        self.version += 1; return self.version

    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        d = {"meta_id": self.meta_id, "db_name": self.db_name, "db_type": self.db_type.value, "version": self.version,
             "entity_types": {n: e.to_dict() for n, e in self.entity_types.items()}}
        if self.relationship_types: d["relationship_types"] = {n: r.to_dict() for n, r in
                                                               self.relationship_types.items()}
        if self.description: d["description"] = self.description
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, path: str):
        open(path, 'w', encoding='utf-8').write(self.to_json())

    # Deserialization
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Database':
        db = cls(db_name=data.get("db_name", "unknown"), db_type=DatabaseType(data.get("db_type", "relational")),
                 version=data.get("version", 1), description=data.get("description"))
        if "meta_id" in data: db.meta_id = data["meta_id"]
        for e_data in data.get("entity_types", {}).values():
            if e := cls._create_entity(e_data): db.add_entity_type(e)
        for r_data in data.get("relationship_types", {}).values():
            if r := cls._create_rel_type(r_data): db.add_relationship_type(r)
        return db

    @classmethod
    def _create_entity(cls, data: Dict) -> Optional[EntityType]:
        try:
            kind = EntityKind(data.get("entity_kind", "table"))
        except:
            kind = EntityKind.TABLE
        e = EntityType(en_name=data.get("en_name", ""), entity_kind=kind, is_root=data.get("is_root", True),
                       description=data.get("description"))
        if "meta_id" in data: e.meta_id = data["meta_id"]
        for a in data.get("attributes", []):
            if attr := cls._create_attr(a): e.add_attribute(attr)
        for k in data.get("keys", []):
            if key := cls._create_key(k, e): e.add_key(key)
        for r in data.get("relationships", []):
            if rel := cls._create_rel(r): e.add_relationship(rel)
        for v in data.get("variations", []):
            if var := cls._create_var(v): e.add_variation(var)
        return e

    @classmethod
    def _create_attr(cls, data: Dict) -> Optional[Attribute]:
        if data.get("kind") != "attribute": return None
        dt = cls._create_dtype(data.get("data_type", {})) or PrimitiveDataType(PrimitiveType.STRING)
        a = Attribute(attr_name=data.get("attr_name", ""), data_type=dt, is_key=data.get("is_key", False),
                      is_optional=data.get("is_optional", True), description=data.get("description"))
        if "meta_id" in data: a.meta_id = data["meta_id"]
        return a

    @classmethod
    def _create_dtype(cls, data: Dict) -> Optional[DataType]:
        kind = data.get("kind", "primitive")
        if kind == "primitive":
            try:
                pt = PrimitiveType(data.get("type", "string"))
            except:
                pt = PrimitiveType.STRING
            return PrimitiveDataType(pt, data.get("max_length"), data.get("precision"), data.get("scale"))
        if kind == "list" and (el := cls._create_dtype(data.get("element_type", {}))): return ListDataType(el)
        if kind == "set" and (el := cls._create_dtype(data.get("element_type", {}))): return SetDataType(el)
        if kind == "map":
            kt, vt = cls._create_dtype(data.get("key_type", {})), cls._create_dtype(data.get("value_type", {}))
            if kt and vt: return MapDataType(kt, vt)
        return None

    @classmethod
    def _create_key(cls, data: Dict, entity: EntityType) -> Optional[Key]:
        try:
            kt = KeyType(data.get("key_type", "PRIMARY"))
        except:
            kt = KeyType.PRIMARY
        k = Key(key_type=kt, is_managed=data.get("is_managed", True), referenced_entity=data.get("referenced_entity"),
                referenced_attributes=data.get("referenced_attributes", []))
        for an in data.get("attributes", []):
            if a := entity.get_attribute(an): k.add_attribute(a)
        return k if k.key_attributes else None

    @classmethod
    def _create_rel(cls, data: Dict) -> Optional[Relationship]:
        kind, card = data.get("kind"), Cardinality.from_symbol(data.get("cardinality", "&"))
        if kind == "reference":
            r = Reference(ref_name=data.get("ref_name", ""), refs_to=data.get("refs_to", ""), cardinality=card,
                          is_optional=data.get("is_optional", True), description=data.get("description"))
            if "meta_id" in data: r.meta_id = data["meta_id"]
            for a in data.get("edge_attributes", []):
                if attr := cls._create_attr(a): r.edge_attributes.append(attr)
            return r
        if kind in ("aggregate", "embedded"):
            a = Aggregate(aggr_name=data.get("aggr_name", data.get("em_name", "")),
                          aggregates=data.get("aggregates", data.get("embeds", "")),
                          cardinality=card, is_optional=data.get("is_optional", True),
                          description=data.get("description"))
            if "meta_id" in data: a.meta_id = data["meta_id"]
            return a
        return None

    @classmethod
    def _create_var(cls, data: Dict) -> Optional[StructuralVariation]:
        v = StructuralVariation(variation_id=data.get("variation_id", 0), count=data.get("count", 0),
                                first_timestamp=data.get("first_timestamp"), last_timestamp=data.get("last_timestamp"))
        for a in data.get("attributes", []):
            if attr := cls._create_attr(a): v.add_attribute(attr)
        for r in data.get("relationships", []):
            if rel := cls._create_rel(r): v.add_relationship(rel)
        return v

    @classmethod
    def _create_rel_type(cls, data: Dict) -> Optional[RelationshipType]:
        r = RelationshipType(rel_name=data.get("rel_name", ""), source_entity=data.get("source_entity", ""),
                             target_entity=data.get("target_entity", ""),
                             cardinality=Cardinality.from_symbol(data.get("cardinality", "*")),
                             description=data.get("description"))
        if "meta_id" in data: r.meta_id = data["meta_id"]
        for a in data.get("attributes", []):
            if attr := cls._create_attr(a): r.add_attribute(attr)
        return r

    @classmethod
    def load_from_file(cls, path: str) -> 'Database':
        return cls.from_dict(json.load(open(path, 'r', encoding='utf-8')))


# Alias
UnifiedMetaSchema = Database

__all__ = ['DatabaseType', 'EntityKind', 'PrimitiveType', 'KeyType', 'Cardinality',
           'DataType', 'PrimitiveDataType', 'ListDataType', 'SetDataType', 'MapDataType',
           'Attribute', 'Key', 'Relationship', 'Reference', 'Aggregate', 'Embedded',
           'StructuralVariation', 'EntityType', 'RelationshipType', 'Database', 'UnifiedMetaSchema']