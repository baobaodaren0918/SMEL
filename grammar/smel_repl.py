#!/usr/bin/env python3
"""
SMEL (Schema Migration and Evolution Language) - Interactive REPL with Auto-completion

This demonstrates the discoverability advantage of hierarchical command syntax.
When user types "ADD " and presses Tab, they see all available sub-commands.

The command hierarchy directly mirrors the SMEL.g4 grammar structure.
"""

from prompt_toolkit import prompt
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style

# ============================================================================
# SMEL Command Hierarchy - Derived from SMEL.g4 grammar
# ============================================================================
# This structure directly reflects the hierarchical design in the grammar:
#   operation: nest | unnest | flatten | copy | move | merge | split
#            | cast | linking | extract | add | delete | drop | rename
#
# The nested dict enables keyword-level auto-completion, demonstrating
# the "discoverability" advantage of hierarchical command design.
# ============================================================================

# Data types from grammar (for CAST operation)
DATA_TYPES = {
    "String": None, "Text": None, "Int": None, "Integer": None,
    "Long": None, "Double": None, "Float": None, "Decimal": None,
    "Boolean": None, "Date": None, "DateTime": None, "Timestamp": None,
    "UUID": None, "Binary": None
}

# Cardinality types (for WITH CARDINALITY clause)
CARDINALITY_TYPES = {
    "ONE_TO_ONE": None,
    "ONE_TO_MANY": None,
    "ZERO_TO_ONE": None,
    "ZERO_TO_MANY": None
}

# Key types from grammar
KEY_TYPES = {
    "PRIMARY": {"KEY": {"TO": None}},
    "UNIQUE": {"KEY": {"TO": None}},
    "FOREIGN": {"KEY": {"TO": None}},
    "PARTITION": {"KEY": {"TO": None}},    # Cassandra
    "CLUSTERING": {"KEY": {"TO": None}}    # Cassandra
}

# Database model types (abstract, not product-specific)
DATABASE_TYPES = {
    "RELATIONAL": None,
    "DOCUMENT": None,
    "GRAPH": None,
    "COLUMNAR": None
}

SMEL_COMMANDS = {
    # ========================================================================
    # ADD - Unified entry point for adding schema elements
    # ========================================================================
    # Grammar: add: ADD (attributeAdd | referenceAdd | embeddedAdd | entityAdd
    #                   | keyAdd | variationAdd | relTypeAdd);
    "ADD": {
        "ATTRIBUTE": {                      # ADD ATTRIBUTE name TO Entity
            "TO": None,
            "WITH": {
                "TYPE": DATA_TYPES,
                "DEFAULT": None
            },
            "NOT": {"NULL": None}
        },
        "REFERENCE": {"TO": None},          # ADD REFERENCE ref_id TO Entity
        "EMBEDDED": {"TO": None},           # ADD EMBEDDED address TO Customer
        "ENTITY": {                         # ADD ENTITY Product
            "WITH": {
                "ATTRIBUTES": None,
                "KEY": None
            }
        },
        "PRIMARY": {"KEY": {"TO": None}},   # ADD PRIMARY KEY id TO Entity
        "UNIQUE": {"KEY": {"TO": None}},    # ADD UNIQUE KEY email TO Entity
        "FOREIGN": {"KEY": {"TO": None}},   # ADD FOREIGN KEY ref TO Entity
        "PARTITION": {"KEY": {"TO": None}}, # ADD PARTITION KEY id TO Entity (Cassandra)
        "CLUSTERING": {"KEY": {"TO": None}},# ADD CLUSTERING KEY ts TO Entity (Cassandra)
        "VARIATION": {"TO": None},          # ADD VARIATION v1 TO Entity (U-Schema)
        "RELTYPE": {"FROM": {"TO": None}}   # ADD RELTYPE KNOWS FROM Person TO Person (Graph)
    },

    # ========================================================================
    # DELETE - Remove schema elements
    # ========================================================================
    # Grammar: delete: DELETE (attributeDelete | referenceDelete
    #                         | embeddedDelete | entityDelete);
    "DELETE": {
        "ATTRIBUTE": None,                  # DELETE ATTRIBUTE Entity.field
        "REFERENCE": None,                  # DELETE REFERENCE Entity.ref_id
        "EMBEDDED": None,                   # DELETE EMBEDDED Entity.address
        "ENTITY": None                      # DELETE ENTITY EntityName
    },

    # ========================================================================
    # DROP - Drop constraints and structural elements
    # ========================================================================
    # Grammar: drop: DROP (keyDrop | variationDrop | relTypeDrop);
    "DROP": {
        "PRIMARY": {"KEY": {"FROM": None}}, # DROP PRIMARY KEY id FROM Entity
        "UNIQUE": {"KEY": {"FROM": None}},  # DROP UNIQUE KEY email FROM Entity
        "FOREIGN": {"KEY": {"FROM": None}}, # DROP FOREIGN KEY ref FROM Entity
        "PARTITION": {"KEY": {"FROM": None}},
        "CLUSTERING": {"KEY": {"FROM": None}},
        "VARIATION": {"FROM": None},        # DROP VARIATION v1 FROM Entity
        "RELTYPE": None                     # DROP RELTYPE KNOWS
    },

    # ========================================================================
    # RENAME - Rename schema elements
    # ========================================================================
    # Grammar: rename: RENAME (attributeRename | entityRename | relTypeRename);
    "RENAME": {
        "ENTITY": {"TO": None},             # RENAME ENTITY OldName TO NewName
        "RELTYPE": {"TO": None},            # RENAME RELTYPE OLD TO NEW (Graph)
        "TO": {"IN": None}                  # RENAME oldAttr TO newAttr IN Entity
    },

    # ========================================================================
    # Structural Transformation Operations
    # ========================================================================

    # NEST - Embed separate entity into parent (Relational -> Document)
    # Grammar: nest: NEST identifier INTO identifier AS identifier nestClause*;
    "NEST": {
        "INTO": {
            "AS": {
                "WITH": {"CARDINALITY": CARDINALITY_TYPES},
                "USING": {"KEY": None},
                "WHERE": None
            }
        }
    },

    # UNNEST - Extract embedded document to separate entity (Document -> Relational)
    # Grammar: unnest: UNNEST identifier FROM identifier unnestClause*;
    "UNNEST": {
        "FROM": {
            "AS": None,
            "USING": {"KEY": None}
        }
    },

    # FLATTEN - Unified extraction for embedded objects and arrays
    # Grammar: flatten: FLATTEN qualifiedName AS identifier flattenClause*;
    "FLATTEN": {
        "AS": {
            "GENERATE": {
                "KEY": {
                    "AS": {
                        "SERIAL": None,
                        "STRING": {"PREFIX": None}
                    },
                    "FROM": None
                }
            },
            "ADD": {"REFERENCE": {"TO": None}},
            "RENAME": {"TO": None}
        }
    },

    # ========================================================================
    # Data Movement Operations
    # ========================================================================

    # COPY - Duplicate attribute (keeps original)
    # Grammar: copy: COPY qualifiedName TO qualifiedName;
    "COPY": {"TO": None},                   # COPY Entity.field TO Entity.newField

    # MOVE - Relocate attribute (removes original)
    # Grammar: move: MOVE qualifiedName TO qualifiedName;
    "MOVE": {"TO": None},                   # MOVE Entity.field TO OtherEntity.field

    # MERGE - Combine two entities
    # Grammar: merge: MERGE identifier COMMA identifier INTO identifier;
    "MERGE": {"INTO": {"AS": None}},        # MERGE A, B INTO C AS alias

    # SPLIT - Divide entity into two
    # Grammar: split: SPLIT identifier INTO identifier COMMA identifier;
    "SPLIT": {"INTO": None},                # SPLIT Entity INTO A, B

    # CAST - Change data type
    # Grammar: cast: CAST qualifiedName TO dataType;
    "CAST": {"TO": DATA_TYPES},             # CAST Entity.field TO Integer

    # LINKING - Create relationship
    # Grammar: linking: LINKING qualifiedName TO identifier;
    "LINKING": {"TO": None},                # LINKING Order.customer TO Customer

    # EXTRACT - Extract attributes to new entity
    # Grammar: extract: EXTRACT (identifierList) FROM identifier INTO identifier;
    "EXTRACT": {"FROM": {"INTO": None}},    # EXTRACT (a,b,c) FROM Entity INTO NewEntity

    # ========================================================================
    # Migration Header (for complete script context)
    # ========================================================================
    "MIGRATION": {
        "FROM": {
            "RELATIONAL": {"TO": DATABASE_TYPES, "USING": None},
            "DOCUMENT": {"TO": DATABASE_TYPES, "USING": None},
            "GRAPH": {"TO": DATABASE_TYPES, "USING": None},
            "COLUMNAR": {"TO": DATABASE_TYPES, "USING": None}
        }
    },

    # ========================================================================
    # Utility Commands (REPL-specific)
    # ========================================================================
    "SHOW": {
        "SCHEMA": None,
        "OPERATIONS": None,
        "HISTORY": None
    },
    "HELP": None,
    "EXIT": None
}

# ============================================================================
# Style Configuration
# ============================================================================

style = Style.from_dict({
    'completion-menu.completion': 'bg:#008888 #ffffff',
    'completion-menu.completion.current': 'bg:#00aaaa #000000',
    'scrollbar.background': 'bg:#88aaaa',
    'scrollbar.button': 'bg:#222222',
})

# ============================================================================
# REPL Implementation
# ============================================================================

def print_banner():
    """Print welcome banner with usage tips"""
    print("""
+===========================================================================+
|             SMEL - Schema Migration & Evolution Language                  |
|                  Interactive REPL with Auto-completion                    |
+===========================================================================+
|  TIP: Type a command and press TAB to see available sub-commands          |
|                                                                           |
|  Examples:                                                                |
|    ADD <TAB>      -> ATTRIBUTE, REFERENCE, ENTITY, PRIMARY, VARIATION...  |
|    DELETE <TAB>   -> ATTRIBUTE, REFERENCE, EMBEDDED, ENTITY               |
|    DROP <TAB>     -> PRIMARY, UNIQUE, FOREIGN, VARIATION, RELTYPE         |
|    FLATTEN <TAB>  -> AS                                                   |
|    CAST <TAB>     -> TO                                                   |
|                                                                           |
|  Type 'HELP' for command reference, 'EXIT' to quit                        |
+---------------------------------------------------------------------------+
""")


def print_help():
    """Print comprehensive help information"""
    print("""
SMEL Command Reference
======================

Schema Evolution Operations:
  ADD <type> ...              - Add schema element
      ATTRIBUTE name TO entity [WITH TYPE datatype] [NOT NULL]
      REFERENCE ref TO entity
      EMBEDDED name TO entity
      ENTITY name [WITH ATTRIBUTES (...)]
      PRIMARY|UNIQUE|FOREIGN KEY col TO entity
      VARIATION name TO entity
      RELTYPE name FROM entity TO entity

  DELETE <type> ...           - Delete schema element
      ATTRIBUTE entity.field
      REFERENCE entity.ref
      EMBEDDED entity.embed
      ENTITY name

  DROP <type> ...             - Drop constraint/structure
      PRIMARY|UNIQUE|FOREIGN KEY col FROM entity
      VARIATION name FROM entity
      RELTYPE name

  RENAME ...                  - Rename element
      ENTITY old TO new
      RELTYPE old TO new
      oldField TO newField IN entity

Structural Transformations:
  NEST child INTO parent AS alias [WITH CARDINALITY ...]
  UNNEST embedded FROM parent [AS newEntity]
  FLATTEN entity.path AS newEntity
      [GENERATE KEY id AS SERIAL|STRING PREFIX "..."|FROM field]
      [ADD REFERENCE ref TO target]

Data Movement:
  COPY source.field TO target.field
  MOVE source.field TO target.field
  MERGE entityA, entityB INTO merged
  SPLIT entity INTO partA, partB
  CAST entity.field TO datatype
  LINKING source.ref TO target
  EXTRACT (fields) FROM entity INTO newEntity

Migration Header:
  MIGRATION name:version
  FROM RELATIONAL|DOCUMENT|GRAPH|COLUMNAR
  TO RELATIONAL|DOCUMENT|GRAPH|COLUMNAR
  USING schema:version

Utility:
  SHOW SCHEMA|OPERATIONS|HISTORY
  HELP
  EXIT

Press TAB after any keyword to see available completions!
""")


def execute_command(command: str):
    """Execute or simulate SMEL command"""
    cmd = command.strip()
    cmd_upper = cmd.upper()

    if not cmd:
        return

    if cmd_upper == "EXIT":
        print("Goodbye!")
        exit(0)
    elif cmd_upper == "HELP":
        print_help()
    elif cmd_upper.startswith("SHOW"):
        print(f"  -> Executing: {cmd}")
        print("  [Simulated - would display actual data in full implementation]")
    elif cmd_upper.startswith("ADD"):
        print(f"  [+] Schema evolution: {cmd}")
    elif cmd_upper.startswith("DELETE"):
        print(f"  [-] Schema evolution: {cmd}")
    elif cmd_upper.startswith("DROP"):
        print(f"  [-] Constraint dropped: {cmd}")
    elif cmd_upper.startswith("RENAME"):
        print(f"  [~] Renamed: {cmd}")
    elif cmd_upper.startswith("MIGRATION"):
        print(f"  [M] Migration header: {cmd}")
    elif cmd_upper.startswith(("NEST", "UNNEST", "FLATTEN")):
        print(f"  [T] Structure transformation: {cmd}")
    elif cmd_upper.startswith(("COPY", "MOVE", "MERGE", "SPLIT", "EXTRACT")):
        print(f"  [T] Data movement: {cmd}")
    elif cmd_upper.startswith("CAST"):
        print(f"  [T] Type conversion: {cmd}")
    elif cmd_upper.startswith("LINKING"):
        print(f"  [T] Relationship created: {cmd}")
    else:
        print(f"  [?] Unknown command: {cmd}")
        print("  Type 'HELP' for commands or press TAB for suggestions")


def main():
    """Main REPL loop demonstrating hierarchical command discovery"""
    print_banner()

    # Create nested completer - the command hierarchy enables discovery
    completer = NestedCompleter.from_nested_dict(SMEL_COMMANDS)

    # Command history for convenience
    history = FileHistory('.smel_history')

    while True:
        try:
            user_input = prompt(
                'SMEL> ',
                completer=completer,
                complete_while_typing=False,
                history=history,
                auto_suggest=AutoSuggestFromHistory(),
                style=style,
            )

            execute_command(user_input)

        except KeyboardInterrupt:
            print("\n  Use 'EXIT' to quit")
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
