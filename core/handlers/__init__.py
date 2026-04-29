"""Handler mixins composed into ``core.SchemaTransformer``.

Importing this package (or any single mixin module) triggers the
``@register_handler`` decorators which populate the module-level
``_HANDLER_REGISTRY`` in ``transformer_base``.
"""
from core.handlers.structural import StructuralHandlersMixin
from core.handlers.crud import CRUDHandlersMixin
from core.handlers.keys_constraints import KeysConstraintsHandlersMixin
from core.handlers.reshape import ReshapeHandlersMixin

__all__ = [
    'StructuralHandlersMixin',
    'CRUDHandlersMixin',
    'KeysConstraintsHandlersMixin',
    'ReshapeHandlersMixin',
]
