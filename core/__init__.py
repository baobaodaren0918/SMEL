"""SMILE core package — public surface."""
from core.serialization import (
    db_to_dict,
    db_to_source_dict,
    parse_original_source,
)
from core.normalization import (
    normalize_entity_kinds,
    normalize_document_cardinality,
)
from core.pipeline import (
    SchemaTransformer,
    SMILE_SYNTAX,
    run_load,
    run_apply,
    run_export,
    run_migration,
)

__all__ = [
    'SchemaTransformer',
    'run_migration',
    'run_load',
    'run_apply',
    'run_export',
    'db_to_dict',
    'db_to_source_dict',
    'parse_original_source',
    'normalize_entity_kinds',
    'normalize_document_cardinality',
    'SMILE_SYNTAX',
]
