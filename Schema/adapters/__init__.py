"""Schema Adapters - Convert native schema formats to Unified Meta Schema."""
from ._base import DatabaseAdapter
from .postgresql_adapter import PostgreSQLAdapter
from .mongodb_adapter import MongoDBAdapter
from .neo4j_adapter import Neo4jAdapter
from .cassandra_adapter import CassandraAdapter

from config import (
    SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT,
    SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR,
)

__all__ = [
    'DatabaseAdapter',
    'PostgreSQLAdapter', 'MongoDBAdapter', 'Neo4jAdapter', 'CassandraAdapter',
    'ADAPTER_REGISTRY',
]

# Adapter Registry: Maps database type string to adapter class.
# Used by run_migration() to dynamically select the correct adapter
# instead of hardcoded if/else chains.
ADAPTER_REGISTRY = {
    SOURCE_TYPE_RELATIONAL: PostgreSQLAdapter,
    SOURCE_TYPE_DOCUMENT: MongoDBAdapter,
    SOURCE_TYPE_GRAPH: Neo4jAdapter,
    SOURCE_TYPE_COLUMNAR: CassandraAdapter,
}
