"""SMILE transformer base — operation registry + state holder + shared helpers."""
import copy
import logging
from typing import Any, Dict, List, Optional

from Schema.unified_meta_schema import (
    Database, EntityType, Property, PrimitiveDataType, PrimitiveType,
)

logger = logging.getLogger(__name__)


# Handler registry — populated at class-definition time by @register_handler
# decorators on each mixin's _handle_* methods. Stores method *names*
# (not function objects) so the registry stays valid across subclassing and
# overrides — the binding to ``self`` happens later in
# ``SchemaTransformerBase.__init__`` via ``getattr``.
_HANDLER_REGISTRY: Dict["OpType", str] = {}  # noqa: F821 — OpType is a forward ref


def register_handler(op_type):
    """Bind an OpType to its handler method by name."""
    def decorator(method):
        if op_type in _HANDLER_REGISTRY:
            raise RuntimeError(
                f"Duplicate handler registration for {op_type}: "
                f"{_HANDLER_REGISTRY[op_type]} vs {method.__name__}"
            )
        _HANDLER_REGISTRY[op_type] = method.__name__
        return method
    return decorator


class SchemaTransformerBase:
    """The instance state every ``_handle_*`` mixin operates on."""

    def __init__(self, database: Database):
        self.database = copy.deepcopy(database)
        self.changes: List[str] = []
        # Snapshot of source-schema primary keys taken at construction; NOT
        # updated as handlers run. Consumed by the web UI to render key badges
        # and resolve FK targets; exported below under the JSON key
        # "key_registry" for backward compatibility with the frontend.
        self.source_key_snapshot: Dict[str, Dict[str, Any]] = {}
        # Per-operation change-tracking hint. Handlers MAY append entity names
        # via _touch(); if non-empty after a handler returns, run_apply() uses
        # it to skip deep-compare on entities the handler didn't touch. Empty
        # = fall back to full-DB diff (legacy behavior).
        self._touched: Optional[List[str]] = None
        self._init_source_keys()
        # Handler registry: OpType -> bound method (populated from
        # _HANDLER_REGISTRY, which @register_handler decorators below filled
        # in at class-definition time).
        self._handlers = {
            op_type: getattr(self, method_name)
            for op_type, method_name in _HANDLER_REGISTRY.items()
        }

    def _touch(self, *entity_names: str) -> None:
        """Hint to run_apply that this handler only modified the listed entities."""
        if self._touched is None:
            return  # not tracking right now (handler called outside run_apply)
        for n in entity_names:
            if n and n not in self._touched:
                self._touched.append(n)

    def _init_source_keys(self) -> None:
        """Populate source_key_snapshot from the source schema's primary keys."""
        for entity_name, entity in self.database.entity_types.items():
            pk = entity.get_primary_key()
            if not (pk and pk.unique_properties):
                continue
            pk_attrs = [
                entity.get_property_by_id(up.property_id)
                for up in pk.unique_properties
            ]
            pk_attrs = [a for a in pk_attrs if a is not None]
            if not pk_attrs:
                continue
            first = pk_attrs[0]
            self.source_key_snapshot[entity_name] = {
                "key_field": first.name,                       # backward compat (scalar)
                "key_fields": [a.name for a in pk_attrs],      # full composite tuple
                "key_type": first.data_type.primitive_type.value if hasattr(first.data_type, 'primitive_type') else "string",
                "prefix": None,
                "generated": False,
            }

    # ── Helper utilities (shared by multiple handlers) ──────────────────
    def _get_entity(self, name: str, op_name: str = "") -> Optional[EntityType]:
        """Look up an entity by name; print [NOTICE] and return None if missing."""
        entity = self.database.get_entity_type(name)
        if not entity and op_name:
            logger.info(f"{op_name} skipped: entity '{name}' not found")
        return entity

    def _split_path(self, path: str) -> tuple:
        """Split 'entity.attr' path into (entity_name, attr_or_field_name)."""
        parts = path.split(".")
        if len(parts) < 2:
            return ("", "")
        return ".".join(parts[:-1]), parts[-1]

    def _resolve_entity_attr(self, path: str, op_name: str = "") -> tuple:
        """Parse 'entity.attr' path, look up the entity, and return (entity, attr_name)."""
        entity_name, attr_name = self._split_path(path)
        if not entity_name:
            return (None, "")
        entity = self._get_entity(entity_name, op_name)
        return (entity, attr_name)
