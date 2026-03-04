"""
SMEL Configuration - Centralized path and settings management.

This module contains all configurable paths and settings for the SMEL project.
Users can modify these values to customize the behavior of the migration tool.
"""
from pathlib import Path

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Base directory (project root)
BASE_DIR = Path(__file__).parent

# Schema files directory (contains PostgreSQL .sql and MongoDB .json schemas)
SCHEMA_DIR = BASE_DIR / "Schema"

# Tests directory (contains .smel migration scripts and test data)
TESTS_DIR = BASE_DIR / "tests"

# Grammar directory (contains ANTLR4 grammar and generated parser)
GRAMMAR_DIR = BASE_DIR / "grammar"


# =============================================================================
# SOURCE/TARGET TYPE CONSTANTS
# =============================================================================
# Used throughout the codebase — never use raw strings for these.

SOURCE_TYPE_RELATIONAL = "Relational"
SOURCE_TYPE_DOCUMENT = "Document"
SOURCE_TYPE_GRAPH = "Graph"
SOURCE_TYPE_COLUMNAR = "Columnar"

# Human-readable product names for each abstract DB type
DB_TYPE_DISPLAY_NAME = {
    SOURCE_TYPE_RELATIONAL: "PostgreSQL",
    SOURCE_TYPE_DOCUMENT:   "MongoDB",
    SOURCE_TYPE_GRAPH:      "Neo4j",
    SOURCE_TYPE_COLUMNAR:   "Cassandra",
}

# Export format labels (shown when displaying generated target output)
DB_TYPE_EXPORT_LABEL = {
    SOURCE_TYPE_RELATIONAL: "PostgreSQL DDL",
    SOURCE_TYPE_DOCUMENT:   "MongoDB JSON Schema",
    SOURCE_TYPE_GRAPH:      "Neo4j Cypher",
    SOURCE_TYPE_COLUMNAR:   "Cassandra CQL",
}


# Northwind target schema files for cross-model validation
# Maps target_type -> native schema file (ground truth for comparison)
TARGET_SCHEMA_FILES = {
    SOURCE_TYPE_RELATIONAL: TESTS_DIR / "northwind_postgresql.sql",
    SOURCE_TYPE_DOCUMENT:   TESTS_DIR / "northwind_mongodb.json",
    SOURCE_TYPE_GRAPH:      TESTS_DIR / "northwind_neo4j.cypher",
    SOURCE_TYPE_COLUMNAR:   TESTS_DIR / "northwind_cassandra.cql",
}


# =============================================================================
# MIGRATION CONFIGURATIONS
# =============================================================================
# Define available migration scenarios with their source/target files

MIGRATION_CONFIGS = {
    # Person: MongoDB -> PostgreSQL (Specific Grammar)
    "person_d2r_specific": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "person_mongo_to_pg_minibeispiel.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Person: MongoDB \u2192 PostgreSQL (Specific)",
    },
    # Person: MongoDB -> PostgreSQL (Pauschalisiert Grammar)
    "person_d2r_pauschalisiert": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "pauschalisiert" / "person_mongo_to_pg_minibeispiel.smel_ps",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Person: MongoDB \u2192 PostgreSQL (Pauschalisiert)",
    },
    # Person: PostgreSQL -> MongoDB (Specific Grammar)
    "person_r2d_specific": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "person_pg_to_mongo_minibeispiel.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Person: PostgreSQL \u2192 MongoDB (Specific)",
    },
    # Person: PostgreSQL -> MongoDB (Pauschalisiert Grammar)
    "person_r2d_pauschalisiert": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "person_pg_to_mongo_minibeispiel.smel_ps",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Person: PostgreSQL \u2192 MongoDB (Pauschalisiert)",
    },
    # Person: PostgreSQL V1 -> PostgreSQL V2 (Specific Grammar)
    "person_r2r_specific": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "person_pg1_to_pg2_minibeispiel.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Person: PostgreSQL \u2192 PostgreSQL V2 (Specific)",
    },
    # Person: PostgreSQL V1 -> PostgreSQL V2 (Pauschalisiert Grammar)
    "person_r2r_pauschalisiert": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "person_pg1_to_pg2_minibeispiel.smel_ps",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Person: PostgreSQL \u2192 PostgreSQL V2 (Pauschalisiert)",
    },
    # Person: MongoDB V1 -> MongoDB V2 (Specific Grammar)
    "person_d2d_specific": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "person_mongo1_to_mongo2_minibeispiel.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Person: MongoDB \u2192 MongoDB V2 (Specific)",
    },
    # Person: MongoDB V1 -> MongoDB V2 (Pauschalisiert Grammar)
    "person_d2d_pauschalisiert": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "pauschalisiert" / "person_mongo1_to_mongo2_minibeispiel.smel_ps",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Person: MongoDB \u2192 MongoDB V2 (Pauschalisiert)",
    },

    # =========================================================================
    # NORTHWIND — Same-Model Evolution (R→R, D→D, G→G, C→C)
    # =========================================================================

    # Northwind: PostgreSQL V1 -> PostgreSQL V2
    "northwind_r2r_specific": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "northwind_pg1_to_pg2.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: PostgreSQL \u2192 PostgreSQL V2 (Specific)",
    },
    "northwind_r2r_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_pg1_to_pg2.smel_ps",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: PostgreSQL \u2192 PostgreSQL V2 (Pauschalisiert)",
    },

    # Northwind: MongoDB V1 -> MongoDB V2
    "northwind_d2d_specific": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "northwind_mongo1_to_mongo2.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: MongoDB \u2192 MongoDB V2 (Specific)",
    },
    "northwind_d2d_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_mongo1_to_mongo2.smel_ps",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: MongoDB \u2192 MongoDB V2 (Pauschalisiert)",
    },

    # Northwind: Neo4j V1 -> Neo4j V2
    "northwind_g2g_specific": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "specific" / "northwind_graph1_to_graph2.smel",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: Neo4j \u2192 Neo4j V2 (Specific)",
    },
    "northwind_g2g_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_graph1_to_graph2.smel_ps",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: Neo4j \u2192 Neo4j V2 (Pauschalisiert)",
    },

    # Northwind: Cassandra V1 -> Cassandra V2
    "northwind_c2c_specific": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "specific" / "northwind_cass1_to_cass2.smel",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: Cassandra \u2192 Cassandra V2 (Specific)",
    },
    "northwind_c2c_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_cass1_to_cass2.smel_ps",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: Cassandra \u2192 Cassandra V2 (Pauschalisiert)",
    },

    # =========================================================================
    # NORTHWIND — Cross-Model Migration (grouped by source)
    # =========================================================================

    # --- From PostgreSQL ---
    "northwind_r2d_specific": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "northwind_pg_to_mongo.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: PostgreSQL \u2192 MongoDB (Specific)",
    },
    "northwind_r2d_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_pg_to_mongo.smel_ps",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: PostgreSQL \u2192 MongoDB (Pauschalisiert)",
    },
    "northwind_r2g_specific": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "northwind_pg_to_neo4j.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: PostgreSQL \u2192 Neo4j (Specific)",
    },
    "northwind_r2g_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_pg_to_neo4j.smel_ps",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: PostgreSQL \u2192 Neo4j (Pauschalisiert)",
    },
    "northwind_r2c_specific": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "northwind_pg_to_cass.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: PostgreSQL \u2192 Cassandra (Specific)",
    },
    "northwind_r2c_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_pg_to_cass.smel_ps",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: PostgreSQL \u2192 Cassandra (Pauschalisiert)",
    },

    # --- From MongoDB ---
    "northwind_d2r_specific": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "northwind_mongo_to_pg.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: MongoDB \u2192 PostgreSQL (Specific)",
    },
    "northwind_d2r_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_mongo_to_pg.smel_ps",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: MongoDB \u2192 PostgreSQL (Pauschalisiert)",
    },
    "northwind_d2g_specific": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "northwind_mongo_to_neo4j.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: MongoDB \u2192 Neo4j (Specific)",
    },
    "northwind_d2g_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_mongo_to_neo4j.smel_ps",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: MongoDB \u2192 Neo4j (Pauschalisiert)",
    },
    "northwind_d2c_specific": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "northwind_mongo_to_cass.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: MongoDB \u2192 Cassandra (Specific)",
    },
    "northwind_d2c_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_mongo_to_cass.smel_ps",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: MongoDB \u2192 Cassandra (Pauschalisiert)",
    },

    # --- From Neo4j ---
    "northwind_g2r_specific": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "specific" / "northwind_neo4j_to_pg.smel",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: Neo4j \u2192 PostgreSQL (Specific)",
    },
    "northwind_g2r_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_neo4j_to_pg.smel_ps",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: Neo4j \u2192 PostgreSQL (Pauschalisiert)",
    },
    "northwind_g2d_specific": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "specific" / "northwind_neo4j_to_mongo.smel",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: Neo4j \u2192 MongoDB (Specific)",
    },
    "northwind_g2d_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_neo4j_to_mongo.smel_ps",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: Neo4j \u2192 MongoDB (Pauschalisiert)",
    },
    "northwind_g2c_specific": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "specific" / "northwind_neo4j_to_cass.smel",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: Neo4j \u2192 Cassandra (Specific)",
    },
    "northwind_g2c_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_neo4j_to_cass.smel_ps",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: Neo4j \u2192 Cassandra (Pauschalisiert)",
    },

    # --- From Cassandra ---
    "northwind_c2r_specific": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "specific" / "northwind_cass_to_pg.smel",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: Cassandra \u2192 PostgreSQL (Specific)",
    },
    "northwind_c2r_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_cass_to_pg.smel_ps",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: Cassandra \u2192 PostgreSQL (Pauschalisiert)",
    },
    "northwind_c2d_specific": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "specific" / "northwind_cass_to_mongo.smel",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: Cassandra \u2192 MongoDB (Specific)",
    },
    "northwind_c2d_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_cass_to_mongo.smel_ps",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: Cassandra \u2192 MongoDB (Pauschalisiert)",
    },
    "northwind_c2g_specific": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "specific" / "northwind_cass_to_neo4j.smel",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: Cassandra \u2192 Neo4j (Specific)",
    },
    "northwind_c2g_pauschalisiert": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "northwind_cass_to_neo4j.smel_ps",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: Cassandra \u2192 Neo4j (Pauschalisiert)",
    },
}

