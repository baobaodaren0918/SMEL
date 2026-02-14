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
├── core.py                        # Migration engine
├── smel_listeners.py              # SMEL listeners for both grammars
├── parser_factory.py              # Parser factory (auto grammar selection)
└── web_server.py                  # Web interface
```

## Architecture

### 3-Step Pipeline

```
┌─────────────┐     Reverse Eng      ┌─────────────┐      SMEL         ┌─────────────┐     Forward Eng     ┌─────────────┐
│   Source     │ ──────────────────► │   Meta V1   │ ──────────────► │   Meta V2   │ ──────────────────► │   Target     │
│   Schema     │                      │  (Unified)  │                  │  (Unified)  │                      │   Schema     │
│ (DDL/JSON)   │                      │             │                  │             │                      │ (DDL/JSON)   │
└─────────────┘                      └─────────────┘                  └─────────────┘                      └─────────────┘
     │                                     │                                │                                    │
     │                                     │                                │                                    │
     ▼                                     ▼                                ▼                                    ▼
 PostgreSQL                           Unified                          Unified                             PostgreSQL
 MongoDB                              Meta-Schema                      Meta-Schema                         MongoDB
 Neo4j                                (Database                        (Database                           Neo4j
 Cassandra                            Agnostic)                        Agnostic)                           Cassandra
```

1. **Reverse Engineering**: Source schema (DDL/JSON) is parsed into the Unified Meta Schema (M-Model)
2. **SMEL Operations**: Meta V1 is transformed into Meta V2 via SMEL script operations
3. **Forward Engineering**: Meta V2 is exported to the target format (DDL/JSON)

The M-Model (Unified Meta Schema) serves as a database-agnostic intermediate representation, enabling any source/target combination.

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

## Example: Cross-Model Migration (D2R)

```smel
MIGRATION person_migration:1.0
FROM DOCUMENT TO RELATIONAL
USING person_schema:1

NEST person.name AS name
NEST person.address AS address
NEST person.employment AS employment
UNNEST person.employment.company:name AS company
    WITH employment.employment_id TO company.employment_id
UNWIND person.tags[] INTO person_tag
```

## Example: Same-Model Evolution (R2R)

```smel
MIGRATION person_pg1_to_pg2:1.0
FROM RELATIONAL TO RELATIONAL
USING person_schema:1

MERGE company, company_address INTO company
SPLIT person INTO person(person_id, vorname, nachname), person_detail(person_id, age, email)
RENAME_ATTRIBUTE vorname TO first_name IN person
CAST person_detail.age TO String
```

## Example: Same-Model Evolution (D2D)

```smel
MIGRATION person_mongo1_to_mongo2:1.0
FROM DOCUMENT TO DOCUMENT
USING person_schema:1

FLATTEN person.employment.company.address
RENAME_ATTRIBUTE vorname TO first_name IN name
CAST person.age TO Integer
ADD_ATTRIBUTE email TO person WITH TYPE String
```

## License

MIT License - See LICENSE file for details.
