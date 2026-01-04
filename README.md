# SMEL - Schema Migration & Evolution Language

A formally defined language for schema migration and evolution between relational and NoSQL database systems, developed as part of a Master's thesis.

## Overview

SMEL (Schema Migration & Evolution Language) provides a unified approach to:
- Define schema transformations across heterogeneous database systems
- Support bidirectional migration between SQL and NoSQL databases
- Support schema evolution within the same database type
- Build upon the Orion taxonomy and research from Darwin platform

## Supported Migration Directions

| Option | Direction | Description | SMEL Script |
|--------|-----------|-------------|-------------|
| 1 | Relational → Document | Cross-model migration | `pg_to_mongo.smel` |
| 2 | Document → Relational | Cross-model migration | `mongo_to_pg.smel` |
| 3 | Relational → Relational | Schema evolution (v1 → v2) | `sql_v1_to_v2.smel` |
| 4 | Document → Document | Schema evolution (v1 → v2) | `mongo_v1_to_v2.smel` |

## Workflow

```
┌─────────────┐     Reverse Eng      ┌─────────────┐      SMEL         ┌─────────────┐     Forward Eng     ┌─────────────┐
│   Source    │ ──────────────────► │   Meta V1   │ ──────────────► │   Meta V2   │ ──────────────────► │   Target    │
│   Schema    │                      │  (Unified)  │                  │  (Unified)  │                      │   Schema    │
│ (DDL/JSON)  │                      │             │                  │             │                      │ (DDL/JSON)  │
└─────────────┘                      └─────────────┘                  └─────────────┘                      └─────────────┘
```

## Installation

### Prerequisites
- Python 3.10+
- ANTLR4 runtime

### Setup
```bash
# Clone the repository
git clone https://github.com/baobaodaren0918/SMEL.git
cd SMEL

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Generate Parser (if needed)
```bash
# Windows
.venv\Scripts\antlr4 -Dlanguage=Python3 -visitor grammar/SMEL.g4

# Linux/Mac
antlr4 -Dlanguage=Python3 -visitor grammar/SMEL.g4
```

## Usage

### Command Line Interface (CLI)

```bash
python main.py
```

Output:
```
============================================================
 SMEL - Schema Migration & Evolution Language
============================================================

  Cross-Model Migration:
  [1] Relational -> Document
  [2] Document -> Relational

  Schema Evolution (Same Model):
  [3] Relational -> Relational (SQL v1 -> v2)
  [4] Document -> Document (MongoDB v1 -> v2)

  [0] Exit

Choice:
```

### Web Interface

```bash
python web_server.py
```

Opens automatically at `http://localhost:5570` with:
- Schema Comparison view (Source vs Target)
- Migration Process view (4-column: Source | Meta V1 | Meta V2 | Target)
- SMEL Script view with step-by-step operations

### Programmatic Usage

```python
from core import run_migration

# Run migration (options: 'r2d', 'd2r', 'r2r', 'd2d')
result = run_migration('d2r')  # Document -> Relational

# Access results
print(result['source_type'])        # 'Document'
print(result['target_type'])        # 'Relational'
print(result['exported_target'])    # Generated PostgreSQL DDL
print(result['operations_count'])   # Number of SMEL operations applied
```

## Project Structure

```
SMEL/
├── grammar/
│   ├── SMEL.g4                 # ANTLR4 grammar definition
│   ├── SMELLexer.py            # Generated lexer
│   ├── SMELParser.py           # Generated parser
│   └── SMELListener.py         # Generated listener
├── Schema/
│   ├── adapters/
│   │   ├── postgresql_adapter.py   # PostgreSQL ↔ Unified Meta
│   │   └── mongodb_adapter.py      # MongoDB ↔ Unified Meta
│   ├── unified_meta_schema.py      # Unified Meta Schema classes
│   ├── pain001_postgresql.sql      # Sample PostgreSQL schema
│   ├── pain001_postgresql_v2.sql   # Sample PostgreSQL schema v2
│   ├── pain001_mongodb.json        # Sample MongoDB schema
│   └── pain001_mongodb_v2.json     # Sample MongoDB schema v2
├── tests/
│   ├── pg_to_mongo.smel            # Relational → Document script
│   ├── mongo_to_pg.smel            # Document → Relational script
│   ├── sql_v1_to_v2.smel           # SQL evolution script
│   └── mongo_v1_to_v2.smel         # MongoDB evolution script
├── core.py                     # Core migration logic
├── main.py                     # CLI interface
├── web_server.py               # Web interface
├── requirements.txt
└── README.md
```

## SMEL Language Syntax

### Migration Script Structure
```
MIGRATION <name>:<version>
FROM <source_type> TO <target_type>
USING <schema>:<version>

<operations>
```

### Supported Operations

#### Schema Evolution (within same database)
| Operation | Syntax | Description |
|-----------|--------|-------------|
| RENAME | `RENAME old TO new IN entity` | Rename attribute |
| RENAME ENTITY | `RENAME ENTITY old TO new` | Rename entity |
| ADD ATTRIBUTE | `ADD ATTRIBUTE name TO entity WITH TYPE type` | Add new attribute |
| ADD ENTITY | `ADD ENTITY name WITH ATTRIBUTES (...)` | Add new entity |
| DELETE ATTRIBUTE | `DELETE ATTRIBUTE entity.attr` | Delete attribute |
| DELETE ENTITY | `DELETE ENTITY name` | Delete entity |
| EXTRACT | `EXTRACT (a,b,c) FROM entity INTO new` | Extract attributes to new entity |
| COPY | `COPY source.attr TO target.attr` | Copy attribute |

#### Schema Migration (across databases)
| Operation | Syntax | Description |
|-----------|--------|-------------|
| NEST | `NEST source INTO target AS alias` | Embed entity as nested object |
| FLATTEN | `FLATTEN entity.embedded INTO new` | Extract embedded to table |
| UNWIND | `UNWIND entity.array AS new` | Unwind array to table |
| ADD REFERENCE | `ADD REFERENCE entity.fk TO target` | Add foreign key reference |

### Example SMEL Script
```sql
-- Document to Relational Migration
MIGRATION pain001_d2r:1.0
FROM DOCUMENT TO RELATIONAL
USING pain001_schema:1

-- Flatten embedded party structures
FLATTEN payment_message.initg_pty INTO party
    ADD REFERENCE payment_message.initg_pty_id TO party

-- Unwind payment_info array
UNWIND payment_message.payment_info[] AS payment_info
    GENERATE KEY pmt_inf_id FROM pmt_inf_id
    ADD REFERENCE payment_info.msg_id TO payment_message
```

## Sample Schema (pain001)

Based on ISO 20022 pain.001 (Customer Credit Transfer Initiation):

| Entity | PostgreSQL | MongoDB |
|--------|------------|---------|
| party | Table with party_id PK | Embedded in payment_message |
| account | Table with acct_id PK | Embedded in payment_info |
| payment_message | Table with msg_id PK | Root document with _id |
| payment_info | Table with pmt_inf_id PK | Array in payment_message |
| credit_transfer_tx | Table with tx_id PK | Array in payment_info |
| remittance_info | Table with rmt_id PK | Array in credit_transfer_tx |

## License

This project is part of a Master's thesis at FernUniversität in Hagen.
