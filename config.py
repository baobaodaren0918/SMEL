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


# Northwind source schema files keyed by product name (for web UI / inspector)
NORTHWIND_SCHEMA_FILES = {
    "postgresql": TESTS_DIR / "northwind_postgresql.sql",
    "mongodb":    TESTS_DIR / "northwind_mongodb.json",
    "neo4j":      TESTS_DIR / "northwind_neo4j.cypher",
    "cassandra":  TESTS_DIR / "northwind_cassandra.cql",
}

# Map product name -> internal SOURCE_TYPE constant (for web UI)
PRODUCT_TO_SOURCE_TYPE = {
    "postgresql": SOURCE_TYPE_RELATIONAL,
    "mongodb":    SOURCE_TYPE_DOCUMENT,
    "neo4j":      SOURCE_TYPE_GRAPH,
    "cassandra":  SOURCE_TYPE_COLUMNAR,
}

# Northwind target schema files for cross-model validation
# Maps target_type -> native schema file (ground truth for comparison)
TARGET_SCHEMA_FILES = {
    SOURCE_TYPE_RELATIONAL: TESTS_DIR / "northwind_postgresql.sql",
    SOURCE_TYPE_DOCUMENT:   TESTS_DIR / "northwind_mongodb.json",
    SOURCE_TYPE_GRAPH:      TESTS_DIR / "northwind_neo4j.cypher",
    SOURCE_TYPE_COLUMNAR:   TESTS_DIR / "northwind_cassandra.cql",
}

# Per-migration target schema files for two-layer validation
# Maps config_key prefix -> {target_type -> native file}
# Used when a migration direction has its own dedicated target file
# (e.g. Person D2R target differs from Person R2R target)
MIGRATION_TARGET_FILES = {
    # Person mini example
    "person_d2r":  TESTS_DIR / "person_d2r_target.sql",
    "person_r2d":  TESTS_DIR / "person_r2d_target.json",
    "person_r2r":  TESTS_DIR / "person_r2r_target.sql",
    "person_d2d":  TESTS_DIR / "person_d2d_target.json",
    # Northwind same-model evolution
    "northwind_r2r": TESTS_DIR / "northwind_r2r_target.sql",
    "northwind_d2d": TESTS_DIR / "northwind_d2d_target.json",
    "northwind_g2g": TESTS_DIR / "northwind_g2g_target.cypher",
    "northwind_c2c": TESTS_DIR / "northwind_c2c_target.cql",
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
    # Person: MongoDB -> PostgreSQL (Generalized Grammar)
    "person_d2r_generalized": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "generalized" / "person_mongo_to_pg_minibeispiel.smel_gen",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Person: MongoDB \u2192 PostgreSQL (Generalized)",
    },
    # Person: PostgreSQL -> MongoDB (Specific Grammar)
    "person_r2d_specific": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "person_pg_to_mongo_minibeispiel.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Person: PostgreSQL \u2192 MongoDB (Specific)",
    },
    # Person: PostgreSQL -> MongoDB (Generalized Grammar)
    "person_r2d_generalized": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "generalized" / "person_pg_to_mongo_minibeispiel.smel_gen",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Person: PostgreSQL \u2192 MongoDB (Generalized)",
    },
    # Person: PostgreSQL V1 -> PostgreSQL V2 (Specific Grammar)
    "person_r2r_specific": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "person_pg1_to_pg2_minibeispiel.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Person: PostgreSQL \u2192 PostgreSQL V2 (Specific)",
    },
    # Person: PostgreSQL V1 -> PostgreSQL V2 (Generalized Grammar)
    "person_r2r_generalized": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "generalized" / "person_pg1_to_pg2_minibeispiel.smel_gen",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Person: PostgreSQL \u2192 PostgreSQL V2 (Generalized)",
    },
    # Person: MongoDB V1 -> MongoDB V2 (Specific Grammar)
    "person_d2d_specific": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "person_mongo1_to_mongo2_minibeispiel.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Person: MongoDB \u2192 MongoDB V2 (Specific)",
    },
    # Person: MongoDB V1 -> MongoDB V2 (Generalized Grammar)
    "person_d2d_generalized": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "generalized" / "person_mongo1_to_mongo2_minibeispiel.smel_gen",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Person: MongoDB \u2192 MongoDB V2 (Generalized)",
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
    "northwind_r2r_generalized": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "generalized" / "northwind_pg1_to_pg2.smel_gen",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: PostgreSQL \u2192 PostgreSQL V2 (Generalized)",
    },

    # Northwind: MongoDB V1 -> MongoDB V2
    "northwind_d2d_specific": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "northwind_mongo1_to_mongo2.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: MongoDB \u2192 MongoDB V2 (Specific)",
    },
    "northwind_d2d_generalized": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "generalized" / "northwind_mongo1_to_mongo2.smel_gen",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: MongoDB \u2192 MongoDB V2 (Generalized)",
    },

    # Northwind: Neo4j V1 -> Neo4j V2
    "northwind_g2g_specific": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "specific" / "northwind_graph1_to_graph2.smel",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: Neo4j \u2192 Neo4j V2 (Specific)",
    },
    "northwind_g2g_generalized": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "generalized" / "northwind_graph1_to_graph2.smel_gen",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: Neo4j \u2192 Neo4j V2 (Generalized)",
    },

    # Northwind: Cassandra V1 -> Cassandra V2
    "northwind_c2c_specific": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "specific" / "northwind_cass1_to_cass2.smel",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: Cassandra \u2192 Cassandra V2 (Specific)",
    },
    "northwind_c2c_generalized": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "generalized" / "northwind_cass1_to_cass2.smel_gen",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: Cassandra \u2192 Cassandra V2 (Generalized)",
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
    "northwind_r2d_generalized": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "generalized" / "northwind_pg_to_mongo.smel_gen",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: PostgreSQL \u2192 MongoDB (Generalized)",
    },
    "northwind_r2g_specific": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "northwind_pg_to_neo4j.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: PostgreSQL \u2192 Neo4j (Specific)",
    },
    "northwind_r2g_generalized": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "generalized" / "northwind_pg_to_neo4j.smel_gen",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: PostgreSQL \u2192 Neo4j (Generalized)",
    },
    "northwind_r2c_specific": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "northwind_pg_to_cass.smel",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: PostgreSQL \u2192 Cassandra (Specific)",
    },
    "northwind_r2c_generalized": {
        "source_file": TESTS_DIR / "northwind_postgresql.sql",
        "smel_file": TESTS_DIR / "generalized" / "northwind_pg_to_cass.smel_gen",
        "source_type": SOURCE_TYPE_RELATIONAL,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: PostgreSQL \u2192 Cassandra (Generalized)",
    },

    # --- From MongoDB ---
    "northwind_d2r_specific": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "northwind_mongo_to_pg.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: MongoDB \u2192 PostgreSQL (Specific)",
    },
    "northwind_d2r_generalized": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "generalized" / "northwind_mongo_to_pg.smel_gen",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: MongoDB \u2192 PostgreSQL (Generalized)",
    },
    "northwind_d2g_specific": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "northwind_mongo_to_neo4j.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: MongoDB \u2192 Neo4j (Specific)",
    },
    "northwind_d2g_generalized": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "generalized" / "northwind_mongo_to_neo4j.smel_gen",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: MongoDB \u2192 Neo4j (Generalized)",
    },
    "northwind_d2c_specific": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "northwind_mongo_to_cass.smel",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: MongoDB \u2192 Cassandra (Specific)",
    },
    "northwind_d2c_generalized": {
        "source_file": TESTS_DIR / "northwind_mongodb.json",
        "smel_file": TESTS_DIR / "generalized" / "northwind_mongo_to_cass.smel_gen",
        "source_type": SOURCE_TYPE_DOCUMENT,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: MongoDB \u2192 Cassandra (Generalized)",
    },

    # --- From Neo4j ---
    "northwind_g2r_specific": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "specific" / "northwind_neo4j_to_pg.smel",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: Neo4j \u2192 PostgreSQL (Specific)",
    },
    "northwind_g2r_generalized": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "generalized" / "northwind_neo4j_to_pg.smel_gen",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: Neo4j \u2192 PostgreSQL (Generalized)",
    },
    "northwind_g2d_specific": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "specific" / "northwind_neo4j_to_mongo.smel",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: Neo4j \u2192 MongoDB (Specific)",
    },
    "northwind_g2d_generalized": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "generalized" / "northwind_neo4j_to_mongo.smel_gen",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: Neo4j \u2192 MongoDB (Generalized)",
    },
    "northwind_g2c_specific": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "specific" / "northwind_neo4j_to_cass.smel",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: Neo4j \u2192 Cassandra (Specific)",
    },
    "northwind_g2c_generalized": {
        "source_file": TESTS_DIR / "northwind_neo4j.cypher",
        "smel_file": TESTS_DIR / "generalized" / "northwind_neo4j_to_cass.smel_gen",
        "source_type": SOURCE_TYPE_GRAPH,
        "target_type": SOURCE_TYPE_COLUMNAR,
        "display_name": "Northwind: Neo4j \u2192 Cassandra (Generalized)",
    },

    # --- From Cassandra ---
    "northwind_c2r_specific": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "specific" / "northwind_cass_to_pg.smel",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: Cassandra \u2192 PostgreSQL (Specific)",
    },
    "northwind_c2r_generalized": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "generalized" / "northwind_cass_to_pg.smel_gen",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_RELATIONAL,
        "display_name": "Northwind: Cassandra \u2192 PostgreSQL (Generalized)",
    },
    "northwind_c2d_specific": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "specific" / "northwind_cass_to_mongo.smel",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: Cassandra \u2192 MongoDB (Specific)",
    },
    "northwind_c2d_generalized": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "generalized" / "northwind_cass_to_mongo.smel_gen",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_DOCUMENT,
        "display_name": "Northwind: Cassandra \u2192 MongoDB (Generalized)",
    },
    "northwind_c2g_specific": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "specific" / "northwind_cass_to_neo4j.smel",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: Cassandra \u2192 Neo4j (Specific)",
    },
    "northwind_c2g_generalized": {
        "source_file": TESTS_DIR / "northwind_cassandra.cql",
        "smel_file": TESTS_DIR / "generalized" / "northwind_cass_to_neo4j.smel_gen",
        "source_type": SOURCE_TYPE_COLUMNAR,
        "target_type": SOURCE_TYPE_GRAPH,
        "display_name": "Northwind: Cassandra \u2192 Neo4j (Generalized)",
    },
}

