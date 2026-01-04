# SMEL - Schema Migration & Evolution Language

A formally defined language for schema migration and evolution between relational and NoSQL database systems, developed as part of a Master's thesis.

## Overview

SMEL (Schema Migration & Evolution Language) is a formally defined language that provides a unified approach to:
- Define schema transformations across heterogeneous database systems
- Support bidirectional migration between SQL and NoSQL databases
- Integrate schema evolution operations from the Orion taxonomy 
- Build upon schema evolution research from the Darwin platform (Störl & Klettke) and Meier's Master thesis

## Supported Database Types

| Type | Implementation | Entity | Key              | Reference | Aggregation |
|------|----------------|--------|------------------|-----------|-------------|
| **Relational** | PostgreSQL | Table | Primary Key      | Foreign Key | — |
| **Document** | MongoDB | Collection | Document Key     | Document Reference | Embedded Document |
| **Columnar** | Cassandra | Table | Partition Key + Clustering Key(s) | Table Reference | UDT |
| **Graph** | Neo4j | Node Label | —¹               | Relationship Type | — |

> ¹ Graph databases identify nodes via internal IDs or optional property constraints, 
>   but do not have a formal Key concept equivalent to relational Primary Keys.

## Process
```
┌─────────────────────────┐          ┌─────────────────────────┐
│      Source Schema      │          │       SMEL Script       │
│ (Relational | Document  │          │  (Evolution & Migration │
│  | Columnar | Graph)    │          │       Operations)       │
└───────────┬─────────────┘          └───────────┬─────────────┘
            │                                    │
            ▼                                    ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│    Unified Meta Schema  │          │     ANTLR4 Parser       │
│          (V1)           │          │      (SMELParser)       │     right side is core task
└───────────┬─────────────┘          └───────────┬─────────────┘
            │                                    │
            │                                    ▼
            │                        ┌─────────────────────────┐
            │                        │       Parse Tree        │
            │                        └───────────┬─────────────┘
            │                                    │
            └────────────────┬───────────────────┘
                             │
                             ▼
                  ┌─────────────────────────┐
                  │        Executor         │
                  │      (SMELExecutor)     │
                  │                         │
                  │  Schema V1 + Parse Tree │
                  │           ↓             │
                  │  Check: Preview Changes │
                  │  Run: Apply Operations  │
                  └───────────┬─────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │    Unified Meta Schema  │
                  │          (V2)           │
                  └───────────┬─────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │      Target Schema      │
                  │ (Relational | Document  │
                  │  | Columnar | Graph)    │
                  └─────────────────────────┘
```

```
SMEL Operations
├── Schema Evolution (Orion-based, within same database)
│   ├── Schema Type:     ADD, DELETE, RENAME, EXTRACT, SPLIT, MERGE
│   ├── Variation:       DELVAR, ADAPT, UNION
│   ├── Feature:         DELETE, RENAME, COPY, MOVE, NEST, UNNEST
│   ├── Attribute:       ADD, CAST, PROMOTE, DEMOTE
│   ├── Reference:       ADD, CAST, MULT, MORPH
│   └── Aggregate:       ADD, MULT, MORPH
│
└── Schema Migration (Meier-based, across databases)
    ├── Single-type:  ADD, DELETE, RENAME, FLATTEN, UNWIND, CAST
    └── Multi-type:   COPY, MOVE, MERGE, SPLIT, NEST, LINKING
```
> **Note:** SMEL Operations and Mapping Rules (EntityType Mapping & DataType Mapping) in this Master Thesis is a work in progress and not finalized.
## Test Schema

Schema of **UniBench SF1** for Master's thesis validation.

| Data Model | Target Database | Entities |
|------------|-----------------|----------|
| **Graph** | Neo4j | Person, Post, Tag |
| **Relational** | PostgreSQL | Customer, Vendor |
| **Document** | MongoDB | Product, Order |

> **Note**: UniBench does not include Columnar schema.

## Installation
```bash
pip install -r requirements.txt
pip install antlr4-python3-runtime
```

## Usage

### Workflow
```
Define SMEL.g4 (ANTLR4 grammar file in EBNF notation)
│
▼
Generate Parser/Lexer (antlr4, SMEL.g4)
│
▼
Load source schema → Unified Meta Schema (V1)
│
▼
Load SMEL script → Lexer → Parser → Parse Tree
│
▼
Run: Schema (V1) + Parse Tree → Executor → Schema (V2) (python main.py)
     (includes syntax validation and schema comparison)
│
▼
Target schema generated
```

### Command Line Interface
```bash
# Generate Parser/Lexer from grammar
antlr4 -Dlanguage=Python3 grammar/SMEL.g4 -o grammar

# Run: execute schema migration & evolution (includes syntax validation)
python main.py
```

### Programmatic Usage
```python
from antlr4 import CommonTokenStream, FileStream
# from grammar.SMELLexer import SMELLexer
# from grammar.SMELParser import SMELParser
# from grammar.SMELExecutor import SMELExecutor
# from Schema.unified_meta_schema import UnifiedMetaSchema

# 1. Load source schema → Unified Meta Schema (V1)
# schema = UnifiedMetaSchema.load_from_file("<source_schema>")

# 2. Load and parse SMEL script (FileStream → Lexer → Parser)
# input_stream = FileStream("<smel_script>")
# lexer = SMELLexer(input_stream)
# token_stream = CommonTokenStream(lexer)
# parser = SMELParser(token_stream)

# 3. Get parse tree
# tree = parser.migration()

# 4. Run: Schema (V1) + Parse Tree → Executor → Schema (V2) (main.py)
# updated_schema = executor.run(tree)

# 5. Save target schema
# updated_schema.save_to_file("<target_schema>")
```

### Project Structure
```
schema_evolution_language/
├── grammar/
│   └── SMEL.g4                      # ANTLR4 grammar definition
├── Schema/
│   └── unified_meta_schema.py       # Unified Meta Schema classes
├── tests/
│   └── test_smel.py                 # Test suite
├── main.py                          # Run: execute migration & evolution (includes validation)
├── requirements.txt
└── README.md
```


## Language Syntax

### Migration Script Structure
```
MIGRATION <name>:<version>
FROM <source_type> TO <target_type>
USING <schema>:<version>

<operations>
```


## Running Tests

> **Note**: Test suite will be implemented during the validation phase.
```bash
#cd schema_evolution_language
#pip install pytest
#pytest tests/test_smel.py -v
```
