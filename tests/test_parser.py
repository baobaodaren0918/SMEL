"""
SMEL Parser Test Script
Tests parsing of SMEL migration scripts using ANTLR4 generated parser.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for grammar imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener
from grammar.SMELLexer import SMELLexer
from grammar.SMELParser import SMELParser
from grammar.SMELListener import SMELListener


class SyntaxErrorListener(ErrorListener):
    """Custom error listener to collect syntax errors."""
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"Line {line}:{column} - {msg}")


class SMELPrintListener(SMELListener):
    """Listener that prints parsed operations."""
    def __init__(self):
        self.indent = 0

    def _print(self, text):
        print("  " * self.indent + text)

    def enterMigration(self, ctx):
        self._print("=== Migration ===")
        self.indent += 1

    def exitMigration(self, ctx):
        self.indent -= 1

    def enterMigrationDecl(self, ctx):
        name = ctx.identifier().getText()
        version = ctx.version().getText()
        self._print(f"Name: {name}:{version}")

    def enterFromToDecl(self, ctx):
        source = ctx.databaseType(0).getText()
        target = ctx.databaseType(1).getText()
        self._print(f"Direction: {source} -> {target}")

    def enterUsingDecl(self, ctx):
        schema = ctx.identifier().getText()
        version = ctx.version().getText()
        self._print(f"Schema: {schema}:{version}")

    def enterNest(self, ctx):
        source = ctx.identifier(0).getText()
        target = ctx.identifier(1).getText()
        alias = ctx.identifier(2).getText()
        self._print(f"NEST {source} INTO {target} AS {alias}")

    def enterUnnest(self, ctx):
        source = ctx.identifier(0).getText()
        target = ctx.identifier(1).getText()
        self._print(f"UNNEST {source} FROM {target}")

    def enterFlatten(self, ctx):
        source = ctx.qualifiedName().getText()
        target = ctx.identifier().getText()
        self._print(f"FLATTEN {source} AS {target}")

    def enterUnwind(self, ctx):
        source = ctx.qualifiedName().getText()
        alias = ctx.identifier().getText()
        self._print(f"UNWIND {source} AS {alias}")

    def enterReferenceDelete(self, ctx):
        ref = ctx.qualifiedName().getText()
        self._print(f"DELETE REFERENCE {ref}")

    def enterReferenceAdd(self, ctx):
        ref = ctx.qualifiedName().getText()
        target = ctx.identifier().getText()
        self._print(f"ADD REFERENCE {ref} TO {target}")

    def enterEntityDelete(self, ctx):
        name = ctx.identifier().getText()
        self._print(f"DELETE ENTITY {name}")

    def enterFeatureRename(self, ctx):
        old_name = ctx.identifier(0).getText()
        new_name = ctx.identifier(1).getText()
        entity = ctx.identifier(2).getText() if len(ctx.identifier()) > 2 else None
        if entity:
            self._print(f"RENAME {old_name} TO {new_name} IN {entity}")
        else:
            self._print(f"RENAME {old_name} TO {new_name}")


def parse_smel_file(filepath: str, verbose: bool = True) -> tuple[bool, list[str]]:
    """
    Parse a SMEL file and return success status and any errors.

    Args:
        filepath: Path to the .smel file
        verbose: Whether to print parse tree and operations

    Returns:
        Tuple of (success: bool, errors: list[str])
    """
    print(f"\n{'='*60}")
    print(f"Parsing: {filepath}")
    print('='*60)

    # Create input stream
    input_stream = FileStream(filepath, encoding='utf-8')

    # Lexer
    lexer = SMELLexer(input_stream)
    lexer.removeErrorListeners()
    error_listener = SyntaxErrorListener()
    lexer.addErrorListener(error_listener)

    # Token stream
    token_stream = CommonTokenStream(lexer)

    # Parser
    parser = SMELParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    # Parse from root rule
    tree = parser.migration()

    # Check for errors
    if error_listener.errors:
        print("\n[FAILED] Syntax errors found:")
        for error in error_listener.errors:
            print(f"  - {error}")
        return False, error_listener.errors

    print("\n[SUCCESS] No syntax errors")

    if verbose:
        # Print tree structure
        print("\n--- Parse Tree (LISP format) ---")
        print(tree.toStringTree(recog=parser))

        # Walk tree with listener
        print("\n--- Parsed Operations ---")
        walker = ParseTreeWalker()
        listener = SMELPrintListener()
        walker.walk(listener, tree)

    return True, []


def count_operations(filepath: str) -> dict:
    """Count different operation types in a SMEL file."""
    input_stream = FileStream(filepath, encoding='utf-8')
    lexer = SMELLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = SMELParser(token_stream)
    tree = parser.migration()

    counts = {
        'NEST': 0, 'UNNEST': 0, 'FLATTEN': 0, 'UNWIND': 0,
        'ADD': 0, 'DELETE': 0, 'DROP': 0, 'RENAME': 0,
        'COPY': 0, 'MOVE': 0, 'MERGE': 0, 'SPLIT': 0,
        'CAST': 0, 'LINKING': 0, 'EXTRACT': 0
    }

    # Count operations in tree (using new unified grammar)
    for op in tree.operation():
        if op.nest(): counts['NEST'] += 1
        elif op.unnest(): counts['UNNEST'] += 1
        elif op.flatten(): counts['FLATTEN'] += 1
        elif op.unwind(): counts['UNWIND'] += 1
        elif op.add(): counts['ADD'] += 1
        elif op.delete(): counts['DELETE'] += 1
        elif op.drop(): counts['DROP'] += 1
        elif op.rename(): counts['RENAME'] += 1
        elif op.copy(): counts['COPY'] += 1
        elif op.move(): counts['MOVE'] += 1
        elif op.merge(): counts['MERGE'] += 1
        elif op.split(): counts['SPLIT'] += 1
        elif op.cast(): counts['CAST'] += 1
        elif op.linking(): counts['LINKING'] += 1
        elif op.extract(): counts['EXTRACT'] += 1

    return {k: v for k, v in counts.items() if v > 0}


def main():
    """Main test function."""
    # Get test files directory
    tests_dir = Path(__file__).parent

    # Test files
    test_files = [
        tests_dir / "pg_to_mongo.smel",
        tests_dir / "mongo_to_pg.smel"
    ]

    results = []

    for filepath in test_files:
        if not filepath.exists():
            print(f"\n[SKIP] File not found: {filepath}")
            continue

        success, errors = parse_smel_file(str(filepath), verbose=True)
        results.append((filepath.name, success, errors))

        if success:
            counts = count_operations(str(filepath))
            print("\n--- Operation Counts ---")
            for op, count in counts.items():
                print(f"  {op}: {count}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    all_passed = True
    for name, success, errors in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}")
        if not success:
            all_passed = False

    print("="*60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
