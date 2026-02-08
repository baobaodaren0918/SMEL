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
    # Person: MongoDB -> PostgreSQL (Specific Grammar)
    "person_d2r_specific": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "specific" / "person_mongo_to_pg_minibeispiel.smel",
        "source_type": "Document",
        "target_type": "Relational",
    },
    # Person: MongoDB -> PostgreSQL (Pauschalisiert Grammar)
    "person_d2r_pauschalisiert": {
        "source_file": TESTS_DIR / "person_mongodb.json",
        "smel_file": TESTS_DIR / "pauschalisiert" / "person_mongo_to_pg_minibeispiel.smel_ps",
        "source_type": "Document",
        "target_type": "Relational",
    },
    # Person: PostgreSQL -> MongoDB (Specific Grammar)
    "person_r2d_specific": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "specific" / "person_pg_to_mongo_minibeispiel.smel",
        "source_type": "Relational",
        "target_type": "Document",
    },
    # Person: PostgreSQL -> MongoDB (Pauschalisiert Grammar)
    "person_r2d_pauschalisiert": {
        "source_file": TESTS_DIR / "person_postgresql.sql",
        "smel_file": TESTS_DIR / "pauschalisiert" / "person_pg_to_mongo_minibeispiel.smel_ps",
        "source_type": "Relational",
        "target_type": "Document",
    },
}


# =============================================================================
# EQUIVALENT ATTRIBUTE NAMES
# =============================================================================
# Attribute names that should be considered equivalent during validation

EQUIVALENT_ATTRS = {
    ('msg_id', '_id'),
    ('_id', 'msg_id'),
}
