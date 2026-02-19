# SMEL - Schema Migration & Evolution Language

A formally defined language for schema migration and evolution between heterogeneous database systems.

## Overview

SMEL (Schema Migration & Evolution Language) provides a unified approach to:
- Define schema transformations across heterogeneous database systems
- Support bidirectional migration between SQL and NoSQL databases (D2R, R2D)
- Support same-model schema evolution (R2R, D2D)

## Supported Database Models

- **RELATIONAL**: PostgreSQL, MySQL, Oracle, SQL Server
- **DOCUMENT**: MongoDB, CouchDB, DocumentDB
- **GRAPH**: Neo4j, ArangoDB
- **COLUMNAR**: Cassandra, HBase

## Installation

### Prerequisites
- Python 3.10+
- ANTLR 4.13.2

### Setup
```bash
git clone https://github.com/baobaodaren0918/SMEL.git
cd SMEL

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Web Interface
```bash
python web_server.py
# Opens at http://localhost:5582
```

### Programmatic Usage
```python
from core import run_migration

# Cross-model migration
result = run_migration('person_d2r_specific')       # Document -> Relational
result = run_migration('person_r2d_pauschalisiert')  # Relational -> Document

# Same-model evolution
result = run_migration('person_r2r_specific')        # Relational -> Relational V2
result = run_migration('person_d2d_specific')        # Document -> Document V2

print(result['exported_target'])  # Generated target schema
```

### Run Tests
```bash
python tests/test_full_flow.py
# Tests all 8 directions: D2R(2) + R2D(2) + R2R(2) + D2D(2)
```

## Supported Migration Directions

| Direction | Source | Target | Description |
|-----------|--------|--------|-------------|
| D2R | MongoDB (Document) | PostgreSQL (Relational) | Cross-model migration |
| R2D | PostgreSQL (Relational) | MongoDB (Document) | Cross-model migration |
| R2R | PostgreSQL V1 | PostgreSQL V2 | Same-model evolution |
| D2D | MongoDB V1 | MongoDB V2 | Same-model evolution |

Each direction has both **Specific** (`.smel`) and **Pauschalisiert** (`.smel_ps`) grammar variants, totaling 8 test scenarios.

## Project Structure

```
SMEL/
├── grammar/
│   ├── SMEL_Specific.g4           # Specific operations grammar (ADD_ATTRIBUTE, DELETE_ENTITY, ...)
│   ├── SMEL_Pauschalisiert.g4     # Generalized operations grammar (ADD_PS, DELETE_PS, ...)
│   ├── specific/                   # Generated parser for Specific grammar
│   │   ├── SMEL_SpecificLexer.py
│   │   ├── SMEL_SpecificParser.py
│   │   ├── SMEL_SpecificListener.py
│   │   └── SMEL_SpecificVisitor.py
│   ├── pauschalisiert/            # Generated parser for Pauschalisiert grammar
│   │   ├── SMEL_PauschalisiertLexer.py
│   │   ├── SMEL_PauschalisiertParser.py
│   │   ├── SMEL_PauschalisiertListener.py
│   │   └── SMEL_PauschalisiertVisitor.py
│   ├── antlr-4.13.2-complete.jar
│   └── generate_parser_*.bat      # Parser generation scripts
├── Schema/
│   ├── adapters/
│   │   ├── postgresql_adapter.py  # PostgreSQL reverse/forward engineering
│   │   └── mongodb_adapter.py     # MongoDB reverse/forward engineering
│   └── unified_meta_schema.py     # Unified meta-schema (M-Model)
├── tests/
│   ├── person_postgresql.sql      # Source: PostgreSQL schema
│   ├── person_mongodb.json        # Source: MongoDB schema
│   ├── specific/                  # Specific grammar test scripts (.smel)
│   │   ├── person_mongo_to_pg_minibeispiel.smel       # D2R
│   │   ├── person_pg_to_mongo_minibeispiel.smel       # R2D
│   │   ├── person_pg1_to_pg2_minibeispiel.smel        # R2R
│   │   └── person_mongo1_to_mongo2_minibeispiel.smel  # D2D
│   ├── pauschalisiert/            # Pauschalisiert grammar test scripts (.smel_ps)
│   │   ├── person_mongo_to_pg_minibeispiel.smel_ps    # D2R
│   │   ├── person_pg_to_mongo_minibeispiel.smel_ps    # R2D
│   │   ├── person_pg1_to_pg2_minibeispiel.smel_ps     # R2R
│   │   └── person_mongo1_to_mongo2_minibeispiel.smel_ps # D2D
│   └── test_full_flow.py          # Full flow verification (8 directions)
├── config.py                      # Configuration & migration registry
├── core.py                        # Migration engine (SchemaTransformer)
├── smel_listeners.py              # ANTLR listeners for both grammars
├── parser_factory.py              # Parser factory (auto grammar detection)
├── main.py                        # CLI entry point
└── web_server.py                  # Web interface
```

## Architecture

### End-to-End Pipeline

The complete processing pipeline consists of 4 stages. Below is the full logic chain from source schema to target schema, showing which files and functions are involved at each step.

```
 Source Schema          SMEL Script             Unified Meta-Schema              Target Schema
 (DDL / JSON)          (.smel / .smel_ps)       (M-Model)                        (DDL / JSON)
 ─────────────         ─────────────────        ───────────────────              ─────────────
      │                       │                        │                               ▲
      │                       │                        │                               │
      ▼                       ▼                        ▼                               │
 ┌──────────┐          ┌──────────────┐         ┌──────────┐    ┌──────────┐    ┌──────────┐
 │ Step 1   │          │   Step 2     │         │  Step 3  │    │  Step 3  │    │  Step 4  │
 │ Reverse  │────────►│   SMEL       │────────►│  Meta V1 │───►│  Meta V2 │───►│ Forward  │
 │ Engineer │          │   Parsing    │         │          │    │          │    │ Engineer │
 └──────────┘          └──────────────┘         └──────────┘    └──────────┘    └──────────┘
```

#### Step 1: Reverse Engineering — Source Schema to Meta V1

Converts a database-specific schema file into the **Unified Meta-Schema (M-Model)**, a database-agnostic intermediate representation.

| Component | File | Function |
|-----------|------|----------|
| Entry point | `core.py` | `run_migration()` line 1768 |
| PostgreSQL adapter | `Schema/adapters/postgresql_adapter.py` | `PostgreSQLAdapter.load_from_file()` → `parse()` |
| MongoDB adapter | `Schema/adapters/mongodb_adapter.py` | `MongoDBAdapter.load_from_file()` → `parse()` |
| Type mapping | `Schema/unified_meta_schema.py` | `TypeMappings.POSTGRESQL_TO_PRIMITIVE` / `MONGODB_TO_PRIMITIVE` |

**What happens:**
- PostgreSQL: DDL is parsed with regex to extract `CREATE TABLE` statements, column types are mapped to `PrimitiveType` enums (e.g., `VARCHAR(255)` → `STRING`), `REFERENCES` clauses become `Reference` relationships
- MongoDB: JSON Schema is parsed recursively, nested `bsonType: "object"` becomes `Embedded` relationships, arrays with primitive items become `ListDataType` attributes

**Output:** A `Database` object containing `EntityType`s with `Attribute`s, `Relationship`s (Reference/Embedded), and `Constraint`s (PK/FK/Unique)

#### Step 2: SMEL Parsing — Script to Operation List

Parses a `.smel` or `.smel_ps` file into a list of executable `Operation` objects.

| Component | File | Function |
|-----------|------|----------|
| Entry point | `core.py` | `run_migration()` line 1772-1773 |
| Grammar detection | `parser_factory.py` | `detect_grammar_type()` — selects grammar by file extension |
| ANTLR parsing | `parser_factory.py` | `parse_smel_auto()` — lexer → tokens → parse tree |
| Specific listener | `smel_listeners.py` | `SMELSpecificListener` — walks parse tree, creates Operations |
| Pauschalisiert listener | `smel_listeners.py` | `SMELPauschalisiertListener` — same role, different keyword set |

**What happens:**
1. File extension determines grammar: `.smel` → `SMEL_Specific.g4`, `.smel_ps` → `SMEL_Pauschalisiert.g4`
2. ANTLR4 lexer tokenizes the SMEL script, parser builds a parse tree
3. A custom listener walks the tree, calling `enterXxx()` methods for each grammar rule
4. Each listener method creates an `Operation(op_type, params)` and appends to `self.operations`

**Output:** A tuple of `(MigrationContext, List[Operation], List[errors])`

#### Step 3: Transformation — Meta V1 to Meta V2

Applies each parsed `Operation` to the meta-schema, transforming it step by step.

| Component | File | Function |
|-----------|------|----------|
| Entry point | `core.py` | `run_migration()` line 1778-1823 |
| Transformer | `core.py` | `SchemaTransformer.__init__()` — deep-copies Meta V1 as working copy |
| Operation dispatch | `core.py` | `SchemaTransformer.apply()` → `_handle_{op_type}()` |

**What happens:**
- `SchemaTransformer` creates a deep copy of Meta V1 as its working `Database`
- For each `Operation`, the transformer calls the corresponding handler (e.g., `_handle_unnest()`, `_handle_split()`, `_handle_rename()`)
- Each handler mutates the internal `Database` object: adding/removing `EntityType`s, `Attribute`s, `Relationship`s, `Constraint`s
- Changes are tracked for audit (`self.changes`)

**Output:** The transformed `Database` object (Meta V2) and a list of operation results

#### Step 4: Forward Engineering — Meta V2 to Target Schema

Converts the transformed M-Model back into a database-specific schema format.

| Component | File | Function |
|-----------|------|----------|
| Entry point | `core.py` | `run_migration()` line 1832-1836 |
| PostgreSQL export | `Schema/adapters/postgresql_adapter.py` | `PostgreSQLAdapter.export_to_sql()` |
| MongoDB export | `Schema/adapters/mongodb_adapter.py` | `MongoDBAdapter.export_to_json_string()` |
| Type mapping | `Schema/unified_meta_schema.py` | `TypeMappings.PRIMITIVE_TO_POSTGRESQL` / `PRIMITIVE_TO_MONGODB` |

**What happens:**
- PostgreSQL: Topologically sorts entities by FK dependencies, generates `CREATE TABLE` DDL with columns, primary keys, and `REFERENCES` clauses
- MongoDB: Recursively builds JSON Schema with nested objects for `Embedded` relationships, arrays for `ONE_TO_MANY` cardinality

**Output:** A string containing the target schema (SQL DDL or JSON Schema)

### The Unified Meta-Schema (M-Model)

The M-Model (`Schema/unified_meta_schema.py`) is the central abstraction that makes cross-model migration possible. All adapters convert to/from this single representation.

```
                        ┌────────────────────────────────┐
                        │        Database                │
                        │  - entity_types: Dict          │
                        │  - relationship_types: Dict    │
                        │  - db_type: DatabaseType       │
                        └────────────┬───────────────────┘
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                   ┌─────────────┐      ┌────────────────┐
                   │ EntityType  │      │RelationshipType│
                   │ (Table/Doc) │      │  (Neo4j only)  │
                   └──────┬──────┘      └────────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
      ┌───────────┐ ┌────────────┐ ┌────────────┐
      │ Attribute │ │Relationship│ │ Constraint │
      │           │ │            │ │            │
      │ - name    │ │ - Reference│ │ - Unique   │
      │ - type    │ │ - Embedded │ │ - FK       │
      │ - is_key  │ │ - card.    │ │            │
      └───────────┘ └────────────┘ └────────────┘
```

Key design: `EntityType.object_name` is a `List[str]` representing the hierarchical path. A top-level table like `person` has `["person"]`, while a nested object like `person.address` has `["person", "address"]`. This enables the M-Model to represent both flat relational tables and deeply nested document structures.

### Key Generation & Dependency Resolution

When extracting nested structures (Document -> Relational), SMEL automatically manages primary key generation:

```
NEST person.employment AS employment
    GENERATE KEY id AS String PREFIX "emp"
    ADD REFERENCE person_id TO person
```

**Key Registry** tracks generated keys for traceability:

| Entity | Key Field | Prefix | Format | Source |
|--------|-----------|--------|--------|--------|
| person | _id | - | (original) | - |
| employment | id | emp | emp_{uuid6} | person |
| company | id | comp | comp_{uuid6} | employment |

**Auto Prefix Generation**: If PREFIX is not specified, automatically generates from entity name (first 3 + last 1 character):
- `employment` -> `empt`
- `company` -> `comy`
- `address` -> `adds`

**Dependency Sorting**: Operations are automatically sorted by dependency order, so users don't need to worry about the execution sequence.

## SMEL Operations

### Structural Operations

| Operation | Description | Use Case |
|-----------|-------------|----------|
| NEST | Embed reference target as nested object | R2D: table -> embedded document |
| UNNEST | Extract nested object to separate entity | D2R: embedded document -> table |
| FLATTEN | Merge child entity into parent (reduce depth) | D2D: reduce nesting level |
| UNFLATTEN | Group flat fields into nested object | R2D: flat columns -> nested object |
| UNWIND | Expand array field to separate entity/rows | D2R: array -> table |
| WIND | Convert scalar field back to array | R2D: column -> array |
| MERGE | Combine two entities into one (denormalization) | R2R: merge tables |
| SPLIT | Vertical partition into separate entities | R2R: split table |

### Field Operations

| Operation | Description |
|-----------|-------------|
| ADD_ATTRIBUTE | Add new field to entity |
| DELETE_ATTRIBUTE | Remove field from entity |
| RENAME_ATTRIBUTE | Rename field within entity |
| COPY | Copy field to another entity |
| MOVE | Move field to another entity |
| CAST | Change field data type |

### Key & Constraint Operations

| Operation | Description |
|-----------|-------------|
| ADD_PRIMARY_KEY | Add primary key to entity |
| DELETE_PRIMARY_KEY | Remove primary key |
| ADD_FOREIGN_KEY | Add foreign key constraint |
| DELETE_FOREIGN_KEY | Remove foreign key constraint |
| ADD_UNIQUE_KEY | Add unique constraint |
| DELETE_UNIQUE_KEY | Remove unique constraint |

### Reference & Entity Operations

| Operation | Description |
|-----------|-------------|
| ADD_REFERENCE | Add foreign key reference between entities |
| DELETE_REFERENCE | Remove foreign key reference |
| ADD_EMBEDDED | Add embedded relationship |
| DELETE_EMBEDDED | Remove embedded relationship |
| ADD_ENTITY | Add new entity |
| DELETE_ENTITY | Remove entity |
| RENAME_ENTITY | Rename entity |
| LINKING | Link entities via reference relationship |

## Grammar Variants

SMEL provides two grammar variants:

1. **SMEL_Specific.g4** (`.smel`): Uses specific keywords (e.g., `ADD_ATTRIBUTE`, `DELETE_ENTITY`, `MERGE`)
2. **SMEL_Pauschalisiert.g4** (`.smel_ps`): Uses parameterized operations (e.g., `ADD_PS ATTRIBUTE`, `DELETE_PS ENTITY`, `MERGE_PS`)

Both grammars are functionally equivalent and generate the same internal operations. See `grammar/README.md` for detailed comparison.

## SMEL Script Examples

### SMEL Script Location & Application

All SMEL test scripts are located under the `tests/` directory, organized by grammar variant:

```
tests/
├── person_mongodb.json                          # MongoDB source schema
├── person_postgresql.sql                        # PostgreSQL source schema
├── specific/                                    # Scripts using Specific grammar
│   ├── person_mongo_to_pg_minibeispiel.smel     # D2R: MongoDB -> PostgreSQL
│   ├── person_pg_to_mongo_minibeispiel.smel     # R2D: PostgreSQL -> MongoDB
│   ├── person_pg1_to_pg2_minibeispiel.smel      # R2R: PostgreSQL V1 -> V2
│   └── person_mongo1_to_mongo2_minibeispiel.smel # D2D: MongoDB V1 -> V2
└── pauschalisiert/                              # Scripts using Pauschalisiert grammar
    ├── person_mongo_to_pg_minibeispiel.smel_ps
    ├── person_pg_to_mongo_minibeispiel.smel_ps
    ├── person_pg1_to_pg2_minibeispiel.smel_ps
    └── person_mongo1_to_mongo2_minibeispiel.smel_ps
```

Each script is registered in `config.py` under `MIGRATION_CONFIGS`, which maps a config key (e.g., `"person_d2r_specific"`) to its source file, SMEL script, source type, and target type. The `run_migration()` function in `core.py` reads this config to wire everything together.

### Example: Cross-Model Migration (D2R)

MongoDB document with 3-level nesting and arrays -> 7 normalized PostgreSQL tables:

```smel
MIGRATION person_mongo_to_pg:1.0
FROM DOCUMENT TO RELATIONAL
USING person_schema:1

-- Extract nested objects (UNNEST)
UNNEST person.address:street,city AS address WITH person.person_id TO address.person_id
UNNEST person.employment:position, company{name, address{street, city}} AS employment WITH person.person_id TO employment.person_id
UNNEST employment.company:name, address{street, city} AS company WITH employment.employment_id TO company.employment_id
UNNEST company.address:street,city AS company_address WITH company.company_id TO company_address.company_id

-- Extract arrays (SPLIT + UNWIND)
SPLIT person INTO person:person_id, name, age, knows; person_tag:person_id, tags
UNWIND person_tag.tags

SPLIT person INTO person:person_id, name, age; person_knows:person_id, knows
UNWIND person_knows.knows

-- Finalize
FLATTEN person.name
CAST person.age TO Integer
```

### Example: Same-Model Evolution (R2R)

```smel
MIGRATION person_pg1_to_pg2:1.0
FROM RELATIONAL TO RELATIONAL
USING person_schema:1

MERGE company, company_address INTO company
SPLIT person INTO person:person_id, vorname, nachname; person_detail:person_id, age, email, phone
RENAME_ATTRIBUTE vorname TO first_name IN person
CAST person_detail.age TO String
```

### Example: Same-Model Evolution (D2D)

```smel
MIGRATION person_mongo1_to_mongo2:1.0
FROM DOCUMENT TO DOCUMENT
USING person_schema:1

FLATTEN person.employment.company.address
RENAME_ATTRIBUTE vorname TO first_name IN name
CAST person.age TO Integer
ADD_ATTRIBUTE email TO person WITH TYPE String
```

## Regenerating Parsers

After modifying `.g4` grammar files, regenerate the ANTLR parsers:

```bash
java -jar grammar/antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -listener -o grammar/specific grammar/SMEL_Specific.g4
java -jar grammar/antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -listener -o grammar/pauschalisiert grammar/SMEL_Pauschalisiert.g4
```

## License

MIT License - See LICENSE file for details.
