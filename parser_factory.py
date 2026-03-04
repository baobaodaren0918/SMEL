"""
Parser Factory - Auto-select parser based on file extension

This module provides a unified entry point for parsing SMEL files.
It automatically selects the appropriate parser based on file extension:
- .smel     -> SMEL_Specific parser
- .smel_ps  -> SMEL_Pauschalisiert parser
"""
import sys
from pathlib import Path
from typing import Tuple, List

sys.path.insert(0, str(Path(__file__).parent))

from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener

# Import both grammars
from grammar.specific.SMEL_SpecificLexer import SMEL_SpecificLexer
from grammar.specific.SMEL_SpecificParser import SMEL_SpecificParser
from grammar.specific.SMEL_SpecificListener import SMEL_SpecificListener

from grammar.pauschalisiert.SMEL_PauschalisiertLexer import SMEL_PauschalisiertLexer
from grammar.pauschalisiert.SMEL_PauschalisiertParser import SMEL_PauschalisiertParser
from grammar.pauschalisiert.SMEL_PauschalisiertListener import SMEL_PauschalisiertListener

# Import custom listeners
from smel_listeners import SMELSpecificListener, SMELPauschalisiertListener


class SyntaxErrorListener(ErrorListener):
    """Custom error listener to collect syntax errors."""
    def __init__(self, grammar_type: str = ""):
        super().__init__()
        self.errors = []
        self.grammar_type = grammar_type

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        prefix = f"[{self.grammar_type}] " if self.grammar_type else ""
        self.errors.append(f"{prefix}Line {line}:{column} - {msg}")


def detect_grammar_type(file_path: str) -> str:
    """
    Detect which grammar to use based on file extension.

    Args:
        file_path: Path to SMEL file

    Returns:
        Grammar type: 'specific' or 'pauschalisiert'
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == '.smel_ps':
        return 'pauschalisiert'
    elif suffix == '.smel':
        # .smel files use the specific grammar
        return 'specific'
    else:
        raise ValueError(f"Unknown file extension: {suffix}. Expected .smel or .smel_ps")


def get_parser_components(grammar_type: str):
    """
    Get Lexer, Parser, and base Listener classes for the specified grammar.

    Args:
        grammar_type: 'specific' or 'pauschalisiert'

    Returns:
        Tuple of (Lexer class, Parser class, Listener base class)
    """
    if grammar_type == 'specific':
        return SMEL_SpecificLexer, SMEL_SpecificParser, SMEL_SpecificListener
    elif grammar_type == 'pauschalisiert':
        return SMEL_PauschalisiertLexer, SMEL_PauschalisiertParser, SMEL_PauschalisiertListener
    else:
        raise ValueError(f"Unknown grammar type: {grammar_type}. Expected 'specific' or 'pauschalisiert'")


def parse_smel_file(file_path: str, listener_class):
    """
    Parse a SMEL file using the appropriate grammar.

    Args:
        file_path: Path to SMEL file
        listener_class: Custom listener class (must inherit from appropriate base)

    Returns:
        Tuple of (listener instance, error_list)
    """
    # Detect grammar type
    grammar_type = detect_grammar_type(file_path)

    # Get parser components
    LexerClass, ParserClass, BaseListenerClass = get_parser_components(grammar_type)

    # Verify listener inherits from correct base
    if not issubclass(listener_class, BaseListenerClass):
        raise TypeError(
            f"Listener class must inherit from {BaseListenerClass.__name__} for {grammar_type} grammar"
        )

    # Create input stream
    input_stream = FileStream(file_path, encoding='utf-8')

    # Create lexer
    lexer = LexerClass(input_stream)

    # Create token stream
    token_stream = CommonTokenStream(lexer)

    # Create parser
    parser = ParserClass(token_stream)

    # Add error listener to both lexer and parser
    error_listener = SyntaxErrorListener(grammar_type)
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    # Parse
    tree = parser.migration()

    # Walk parse tree with listener
    listener = listener_class()
    walker = ParseTreeWalker()
    walker.walk(listener, tree)

    return listener, error_listener.errors


def get_grammar_info(file_path: str) -> dict:
    """
    Get information about which grammar will be used for a file.

    Args:
        file_path: Path to SMEL file

    Returns:
        Dict with grammar information
    """
    grammar_type = detect_grammar_type(file_path)
    LexerClass, ParserClass, ListenerClass = get_parser_components(grammar_type)

    return {
        'type': grammar_type,
        'file_extension': Path(file_path).suffix,
        'lexer': LexerClass.__name__,
        'parser': ParserClass.__name__,
        'listener_base': ListenerClass.__name__
    }


def parse_smel_auto(file_path: str):
    """
    Automatically parse a SMEL file using the appropriate grammar.

    This is the main entry point for parsing SMEL files. It:
    1. Detects the grammar type from file extension
    2. Selects the appropriate lexer, parser, and listener
    3. Parses the file and returns operations

    Args:
        file_path: Path to SMEL file (.smel or .smel_ps)

    Returns:
        Tuple of (context, operations, errors)
        - context: MigrationContext with header information
        - operations: List of Operation objects
        - errors: List of error messages (empty if no errors)
    """
    # Detect grammar type
    grammar_type = detect_grammar_type(file_path)

    # Get parser components
    LexerClass, ParserClass, _ = get_parser_components(grammar_type)

    # Select appropriate custom listener
    if grammar_type == 'specific':
        ListenerClass = SMELSpecificListener
    elif grammar_type == 'pauschalisiert':
        ListenerClass = SMELPauschalisiertListener
    else:
        raise ValueError(f"Unknown grammar type: {grammar_type}. Expected 'specific' or 'pauschalisiert'")

    # Create input stream
    input_stream = FileStream(file_path, encoding='utf-8')

    # Create lexer
    lexer = LexerClass(input_stream)

    # Create token stream
    token_stream = CommonTokenStream(lexer)

    # Create parser
    parser = ParserClass(token_stream)

    # Add error listener to both lexer and parser
    error_listener = SyntaxErrorListener(grammar_type)
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    # Parse
    tree = parser.migration()

    # Walk parse tree with listener
    listener = ListenerClass()
    walker = ParseTreeWalker()
    walker.walk(listener, tree)

    return listener.context, listener.operations, error_listener.errors
