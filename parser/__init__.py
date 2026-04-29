"""SMILE parser package — ANTLR listeners, parser factory, op param dataclasses.

Public surface is the listener factory ``parse_smile_auto`` and the
``OpParams`` dataclass family every handler consumes. The ANTLR-generated
parser/lexer modules live separately under the top-level ``grammar/``
package and are picked up by ``factory.get_parser_components`` based on
the file extension.
"""
from parser.factory import (
    parse_smile_auto,
    get_grammar_info,
    get_parser_components,
    SyntaxErrorListener,
)
from parser.listeners import (
    SMILESpecificListener,
    SMILEGeneralizedListener,
    MigrationContext,
    Operation,
    OpType,
)
