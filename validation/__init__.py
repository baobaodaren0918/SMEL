"""SMILE validation package — Layer 1 (Meta V2 vs target file) + Layer 2
(round-trip via adapter export) + the ``validate_pipeline`` blame-attribution
wrapper that combines them into a single verdict.
"""
from validation.meta import validate_meta, compare_meta_schemas
from validation.export import validate_export
from validation.pipeline import validate_pipeline
