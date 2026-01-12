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
# MIGRATION CONFIGURATIONS
# =============================================================================
# Define available migration scenarios with their source/target files

MIGRATION_CONFIGS = {
    # Relational to Document (PostgreSQL -> MongoDB)
    "r2d": {
        "source_file": SCHEMA_DIR / "pain001_postgresql.sql",
        "smel_file": TESTS_DIR / "pg_to_mongo.smel",
        "source_type": "Relational",
        "target_type": "Document",
    },
    # Document to Relational (MongoDB -> PostgreSQL)
    "d2r": {
        "source_file": SCHEMA_DIR / "pain001_mongodb.json",
        "smel_file": TESTS_DIR / "mongo_to_pg.smel",
        "source_type": "Document",
        "target_type": "Relational",
    },
    # Relational to Relational (SQL v1 -> v2)
    "r2r": {
        "source_file": SCHEMA_DIR / "pain001_postgresql.sql",
        "smel_file": TESTS_DIR / "sql_v1_to_v2.smel",
        "source_type": "Relational",
        "target_type": "Relational",
    },
    # Document to Document (MongoDB v1 -> v2)
    "d2d": {
        "source_file": SCHEMA_DIR / "pain001_mongodb.json",
        "smel_file": TESTS_DIR / "mongo_v1_to_v2.smel",
        "source_type": "Document",
        "target_type": "Document",
    },
    # Person Mini Example (MongoDB -> PostgreSQL)
    "person_d2r": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "person_mongo_to_pg_minibeispiel1.smel",
        "source_type": "Document",
        "target_type": "Relational",
    },
}

# Backward compatibility aliases
MIGRATION_CONFIGS["1"] = MIGRATION_CONFIGS["r2d"]
MIGRATION_CONFIGS["2"] = MIGRATION_CONFIGS["d2r"]


# =============================================================================
# EQUIVALENT ATTRIBUTE NAMES
# =============================================================================
# Attribute names that should be considered equivalent during validation

EQUIVALENT_ATTRS = {
    ('msg_id', '_id'),
    ('_id', 'msg_id'),
}
