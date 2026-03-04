# SMEL - Schema Migration & Evolution Language

A formally defined language for schema migration and evolution between heterogeneous database systems, supporting 4 data models with a full 4×4 migration matrix.

## Overview

SMEL (Schema Migration & Evolution Language) provides a unified approach to:
- Define schema transformations across 4 heterogeneous database models
- Support cross-model migration between all model pairs (R↔D, R↔G, R↔C, D↔G, D↔C, G↔C)
- Support same-model schema evolution (R2R, D2D, G2G, C2C)
- Validate migration correctness through two-layer automated validation

## Supported Database Models

| Model | Representative DB | Schema Format | Entity Kind |
|-------|-------------------|---------------|-------------|
| **Relational** | PostgreSQL | SQL DDL (`.sql`) | TABLE |
| **Document** | MongoDB | JSON Schema (`.json`) | DOCUMENT |
| **Graph** | Neo4j | Cypher (`.cypher`) | VERTEX / EDGE |
| **Columnar** | Cassandra | CQL (`.cql`) | WIDE_COLUMN_TABLE |

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
# Opens at http://localhost:5586
```

The web interface provides:
- **Source Schemas** tab: View all 4 native schemas (SQL, JSON, Cypher, CQL)
- **Migration** tab: Run any migration, view SMEL script with syntax highlighting, operation results, source/target schema comparison, and validation results
- **Meta Schema** tab: Interactive card-based visualization of Meta V1/V2

### CLI
```bash
set PYTHONIOENCODING=utf-8  # Windows (for Unicode arrows in display)
python main.py
```

### Programmatic Usage
```python
from core import run_migration

# Cross-model migration (Northwind)
result = run_migration('northwind_r2d_specific')    # Relational -> Document
result = run_migration('northwind_d2g_pauschalisiert')  # Document -> Graph
result = run_migration('northwind_g2c_specific')    # Graph -> Columnar

# Same-model evolution (Northwind)
result = run_migration('northwind_r2r_specific')    # Relational V1 -> V2

# Person mini-example
result = run_migration('person_d2r_specific')       # Document -> Relational

print(result['exported_target'])     # Generated target schema
print(result['validation_meta'])     # Layer 1 validation result
print(result['validation_export'])   # Layer 2 validation result
```

### Run Tests
```bash
python tests/test_full_flow.py
# Tests all 40 migration configs (8 Person + 32 Northwind)
```

## Migration Matrix

### Full 4×4 Matrix (16 directions)

|  | → Relational | → Document | → Graph | → Columnar |
|--|:---:|:---:|:---:|:---:|
| **Relational →** | R2R | R2D | R2G | R2C |
| **Document →** | D2R | D2D | D2G | D2C |
| **Graph →** | G2R | G2D | G2G | G2C |
| **Columnar →** | C2R | C2D | C2G | C2C |

Each direction has both **Specific** (`.smel`) and **Pauschalisiert** (`.smel_ps`) grammar variants.

### Test Datasets

| Dataset | Entities | Configs | Description |
|---------|----------|---------|-------------|
| **Person** | 7 entities | 8 (4 directions × 2 grammars) | Simple example: person with nested address, employment, company |
| **Northwind** | 8 entities | 32 (16 directions × 2 grammars) | Full example: orders, products, customers, employees, etc. |
| **Total** | — | **40 configs** | — |

## Project Structure

```
SMEL/
├── grammar/
│   ├── SMEL_Specific.g4              # Specific operations grammar
│   ├── SMEL_Pauschalisiert.g4        # Generalized operations grammar
│   ├── specific/                      # Generated ANTLR parser (Specific)
│   ├── pauschalisiert/                # Generated ANTLR parser (Pauschalisiert)
│   └── antlr-4.13.2-complete.jar
├── Schema/
│   ├── unified_meta_schema.py         # Unified Meta-Schema (M-Model)
│   └── adapters/
│       ├── __init__.py                # ADAPTER_REGISTRY
│       ├── postgresql_adapter.py      # PostgreSQL RE/FE adapter
│       ├── mongodb_adapter.py         # MongoDB RE/FE adapter
│       ├── neo4j_adapter.py           # Neo4j RE/FE adapter
│       └── cassandra_adapter.py       # Cassandra RE/FE adapter
├── tests/
│   ├── person_postgresql.sql          # Person: PostgreSQL source
│   ├── person_mongodb.json            # Person: MongoDB source
│   ├── northwind_postgresql.sql       # Northwind: PostgreSQL schema (8 tables)
│   ├── northwind_mongodb.json         # Northwind: MongoDB schema (1 orders document)
│   ├── northwind_neo4j.cypher         # Northwind: Neo4j schema (7 nodes, 7 relationships)
│   ├── northwind_cassandra.cql        # Northwind: Cassandra schema (8 wide-column tables)
│   ├── specific/                      # Specific grammar scripts (.smel)
│   │   ├── person_*.smel              # 4 Person scripts (D2R, R2D, R2R, D2D)
│   │   └── northwind_*.smel           # 16 Northwind scripts (full 4×4 matrix)
│   ├── pauschalisiert/                # Pauschalisiert grammar scripts (.smel_ps)
│   │   ├── person_*.smel_ps           # 4 Person scripts
│   │   └── northwind_*.smel_ps        # 16 Northwind scripts
│   └── test_full_flow.py              # Automated test for all 40 configs
├── config.py                          # Migration registry & configuration
├── core.py                            # Migration engine (SchemaTransformer)
├── smel_listeners.py                  # ANTLR listeners for both grammars
├── parser_factory.py                  # Parser factory (auto grammar detection)
├── validate_meta.py                   # Layer 1 validation (SMEL script correctness)
├── validate_export.py                 # Layer 2 validation (adapter export correctness)
├── main.py                            # CLI entry point
└── web_server.py                      # Web interface
```

## Architecture

### End-to-End Pipeline

```
 Source Schema          SMEL Script           Unified Meta-Schema            Target Schema
 (SQL/JSON/             (.smel/.smel_ps)      (M-Model)                      (SQL/JSON/
  Cypher/CQL)                                                                 Cypher/CQL)
 ─────────────         ─────────────────     ───────────────────            ─────────────
      │                       │                     │                             ▲
      ▼                       ▼                     ▼                             │
 ┌──────────┐          ┌──────────────┐      ┌──────────┐    ┌──────────┐  ┌──────────┐
 │ Step 1   │          │   Step 2     │      │  Step 3  │    │  Step 3  │  │  Step 4  │
 │ Reverse  │─────────►│   SMEL       │─────►│  Meta V1 │───►│  Meta V2 │─►│ Forward  │
 │ Engineer │          │   Parsing    │      │          │    │          │  │ Engineer │
 └──────────┘          └──────────────┘      └──────────┘    └──────────┘  └──────────┘
                                                                                │
                                              ┌──────────────────────────────────┘
                                              ▼
                                        ┌──────────┐
                                        │  Step 5  │
                                        │Validation│
                                        │ (2-Layer)│
                                        └──────────┘
```

#### Step 1: Reverse Engineering — Source Schema → Meta V1

Converts a native schema file into the **Unified Meta-Schema (M-Model)**.

| Source Type | Adapter | Method |
|-------------|---------|--------|
| PostgreSQL (`.sql`) | `PostgreSQLAdapter` | `load_from_file()` → `parse()` |
| MongoDB (`.json`) | `MongoDBAdapter` | `load_from_file()` → `parse()` |
| Neo4j (`.cypher`) | `Neo4jAdapter` | `load_from_file()` → `parse_cypher()` |
| Cassandra (`.cql`) | `CassandraAdapter` | `load_from_file()` → `parse()` |

Each adapter maps native types to unified `PrimitiveType` enums (e.g., `VARCHAR(255)` → `STRING`, `bsonType: "int"` → `INTEGER`).

#### Step 2: SMEL Parsing — Script → Operation List

Parses `.smel` or `.smel_ps` files into executable `Operation` objects via ANTLR4.

1. File extension determines grammar: `.smel` → `SMEL_Specific.g4`, `.smel_ps` → `SMEL_Pauschalisiert.g4`
2. ANTLR lexer/parser builds a parse tree
3. Custom listener walks the tree, creating `Operation(op_type, params)` objects

#### Step 3: Transformation — Meta V1 → Meta V2

`SchemaTransformer` deep-copies Meta V1, then applies each operation via handler methods (e.g., `_handle_nest()`, `_handle_split()`, `_handle_add_key()`). Entity kinds are automatically normalized to the target model (e.g., TABLE → DOCUMENT, VERTEX → WIDE_COLUMN_TABLE).

#### Step 4: Forward Engineering — Meta V2 → Target Schema

Converts the transformed M-Model back into a native schema format.

| Target Type | Adapter | Method |
|-------------|---------|--------|
| PostgreSQL | `PostgreSQLAdapter` | `export_to_sql()` |
| MongoDB | `MongoDBAdapter` | `export_to_json_string()` |
| Neo4j | `Neo4jAdapter` | `export_to_cypher()` |
| Cassandra | `CassandraAdapter` | `export_to_cql()` |

#### Step 5: Two-Layer Validation

Automated validation for cross-model Northwind migrations (24 configs):

| Layer | File | What it proves | Method |
|-------|------|---------------|--------|
| **Layer 1** | `validate_meta.py` | SMEL script correctness | Compare Meta V2 result against expected target (parsed from native file) |
| **Layer 2** | `validate_export.py` | Adapter FE correctness | Parse exported target back → compare against expected target (round-trip) |

Validation compares: entity names, attributes (name, type), constraints (PK structure), references, embedded relationships, edges, and relationship types. Cardinality and key_type differences are reported as warnings rather than failures.

### The Unified Meta-Schema (M-Model)

The M-Model (`Schema/unified_meta_schema.py`) is the central abstraction that makes cross-model migration possible.

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
                   │(Table/Doc/  │      │  (Graph edges) │
                   │ Vertex/WCT) │      └────────────────┘
                   └──────┬──────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
      ┌───────────┐ ┌────────────┐ ┌────────────┐
      │ Attribute │ │Relationship│ │ Constraint │
      │           │ │            │ │            │
      │ - name    │ │ - Reference│ │ - Unique   │
      │ - type    │ │ - Embedded │ │ - FK       │
      │ - is_key  │ │ - Edge     │ │ - PK type  │
      │ - key_type│ │ - card.    │ │   (simple/ │
      └───────────┘ └────────────┘ │   partition│
                                   │  /cluster) │
                                   └────────────┘
```

Key design: `EntityType.object_name` is a `List[str]` representing the hierarchical path. A top-level table `person` has `["person"]`, while a nested object `person.address` has `["person", "address"]`.

## SMEL Operations

### Structural Operations

| Operation | Description | Typical Use |
|-----------|-------------|-------------|
| `NEST` | Embed reference target as nested object | R2D: table → embedded document |
| `UNNEST` | Extract nested object to separate entity | D2R: embedded document → table |
| `FLATTEN` | Merge child fields into parent (reduce depth) | D2R: flatten nested address |
| `UNFLATTEN` | Group flat fields into nested object | R2D: flat columns → nested object |
| `UNWIND` | Expand array field to separate rows | D2R: array → table rows |
| `WIND` | Convert field back to array | R2D: column → array |
| `MERGE` | Combine two entities into one | R2R: denormalize tables |
| `SPLIT` | Vertical partition into separate entities | R2R: split table |
| `TRANSFORM` | Convert relationship to entity or vice versa | G2R: edge → table |

### Field Operations

| Operation | Description |
|-----------|-------------|
| `ADD_ATTRIBUTE` | Add new field to entity |
| `DELETE_ATTRIBUTE` | Remove field from entity |
| `RENAME_ATTRIBUTE` | Rename field within entity |
| `COPY_ATTRIBUTE` | Copy field to another entity |
| `MOVE_ATTRIBUTE` | Move field to another entity |
| `CAST_ATTRIBUTE` | Change field data type |

### Key & Constraint Operations

| Operation | Description |
|-----------|-------------|
| `ADD_PRIMARY_KEY` | Add primary key |
| `DELETE_PRIMARY_KEY` | Remove primary key |
| `ADD_FOREIGN_KEY` | Add foreign key constraint |
| `DELETE_FOREIGN_KEY` | Remove foreign key constraint |
| `ADD_UNIQUE_KEY` | Add unique constraint |
| `DELETE_UNIQUE_KEY` | Remove unique constraint |
| `ADD_PARTITION_KEY` | Add Cassandra partition key |
| `ADD_CLUSTERING_KEY` | Add Cassandra clustering key |
| `DELETE_PARTITION_KEY` | Remove Cassandra partition key |
| `DELETE_CLUSTERING_KEY` | Remove Cassandra clustering key |
| `DELETE_CONSTRAINT` | Remove constraint (FK) by field |

### Entity & Relationship Operations

| Operation | Description |
|-----------|-------------|
| `ADD_ENTITY` | Add new entity |
| `DELETE_ENTITY` | Remove entity |
| `RENAME_ENTITY` | Rename entity |
| `ADD_REFERENCE` | Add foreign key reference |
| `DELETE_REFERENCE` | Remove foreign key reference |
| `ADD_EMBEDDED` | Add embedded relationship |
| `DELETE_EMBEDDED` | Remove embedded relationship |
| `ADD_RELTYPE` | Add graph relationship type |
| `DELETE_RELTYPE` | Remove graph relationship type |
| `RENAME_RELTYPE` | Rename graph relationship type |
| `ADD_LABEL` | Add graph node label |
| `DELETE_LABEL` | Remove graph node label |

## Grammar Variants

SMEL provides two functionally equivalent grammars:

| Grammar | File Extension | Example |
|---------|---------------|---------|
| **Specific** | `.smel` | `ADD_ATTRIBUTE name TO person WITH TYPE String` |
| **Pauschalisiert** | `.smel_ps` | `ADD_PS ATTRIBUTE name TO person WITH TYPE String` |

Keyword mapping examples:

| Specific | Pauschalisiert |
|----------|----------------|
| `RENAME_ENTITY` | `RENAME_PS ENTITY` |
| `ADD_ATTRIBUTE` | `ADD_PS ATTRIBUTE` |
| `DELETE_CONSTRAINT` | `DELETE_PS CONSTRAINT` |
| `ADD_PRIMARY_KEY` | `ADD_PS KEY` |
| `ADD_PARTITION_KEY` | `ADD_PS PARTITION KEY` |
| `ADD_CLUSTERING_KEY` | `ADD_PS CLUSTERING KEY` |
| `NEST` / `UNNEST` / `MERGE` / `SPLIT` | `NEST_PS` / `UNNEST_PS` / `MERGE_PS` / `SPLIT_PS` |

## SMEL Script Examples

### Cross-Model: Relational → Document (R2D)

PostgreSQL 3NF tables → MongoDB nested document (Northwind):

```smel
MIGRATION northwind_pg_to_mongo:1.0
FROM RELATIONAL TO DOCUMENT
USING northwind_schema:1

-- Embed tables as nested objects (deepest first)
NEST categories:category_name, description IN products.category
  WHERE products.category_id = categories.category_id WITH DELETION
NEST suppliers:company_name, contact_name, ... IN products.supplier
  WHERE products.supplier_id = suppliers.supplier_id WITH DELETION

-- Group flat shipping fields into nested object
UNFLATTEN orders:ship_address, ship_city, ship_region, ship_postal_code, ship_country
  AS ship_destination

-- Rename PK for MongoDB convention
RENAME_ATTRIBUTE order_id TO _id IN orders
```

### Cross-Model: Relational → Graph (R2G)

PostgreSQL tables → Neo4j nodes + relationships:

```smel
MIGRATION northwind_pg_to_neo4j:1.0
FROM RELATIONAL TO GRAPH
USING northwind_schema:1

-- Convert FK relationships to graph edges
TRANSFORM orders.customer_id REFERENCES customers TO RELATIONSHIP PURCHASED
TRANSFORM orders.employee_id REFERENCES employees TO RELATIONSHIP SOLD
TRANSFORM orders.shipper_id REFERENCES shippers TO RELATIONSHIP SHIPPED_VIA

-- Self-reference becomes graph edge
TRANSFORM employees.reports_to REFERENCES employees TO RELATIONSHIP REPORTS_TO
```

### Cross-Model: Graph → Columnar (G2C)

Neo4j graph → Cassandra wide-column tables:

```smel
MIGRATION northwind_neo4j_to_cass:1.0
FROM GRAPH TO COLUMNAR
USING northwind_schema:1

-- Convert graph edge with properties to entity
TRANSFORM CONTAINS TO ENTITY
RENAME_ENTITY CONTAINS TO order_details

-- Delete relationships, add FK-like columns
DELETE_RELTYPE SUPPLIES
ADD_ATTRIBUTE supplier_id TO products WITH TYPE String

-- Restructure keys for Cassandra query patterns
DELETE_PRIMARY_KEY product_id FROM products
ADD_PARTITION_KEY (category_id, supplier_id) TO products
ADD_CLUSTERING_KEY product_id TO products
```

### Same-Model Evolution: Relational → Relational (R2R)

```smel
MIGRATION person_pg1_to_pg2:1.0
FROM RELATIONAL TO RELATIONAL
USING person_schema:1

MERGE company, company_address INTO company
SPLIT person INTO person:person_id, vorname, nachname;
  person_detail:person_id, age, email, phone
RENAME_ATTRIBUTE vorname TO first_name IN person
CAST person_detail.age TO String
```

## Regenerating Parsers

After modifying `.g4` grammar files:

```bash
java -jar grammar/antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -listener -o grammar/specific grammar/SMEL_Specific.g4
java -jar grammar/antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -listener -o grammar/pauschalisiert grammar/SMEL_Pauschalisiert.g4
```

## License

MIT License - See LICENSE file for details.
