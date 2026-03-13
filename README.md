# SMEL - Schema Migration & Evolution Language

A formally defined language for schema migration and evolution between heterogeneous database systems, supporting 4 data models with a full 4×4 migration matrix.

## Overview

SMEL (Schema Migration & Evolution Language) provides a unified approach to:
- Define schema transformations across 4 heterogeneous database models
- Support cross-model migration between all model pairs (R↔D, R↔G, R↔C, D↔G, D↔C, G↔C)
- Support same-model schema evolution (R2R, D2D, G2G, C2C)
- Validate migration correctness through three-layer automated validation

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
# Opens at http://localhost:5594
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
result = run_migration('northwind_d2g_generalized')  # Document -> Graph
result = run_migration('northwind_g2c_specific')    # Graph -> Columnar

# Same-model evolution (Northwind)
result = run_migration('northwind_r2r_specific')    # Relational V1 -> V2

print(result['exported_target'])     # Generated target schema
print(result['validation_meta'])     # Layer 1 validation result
print(result['validation_export'])   # Layer 2 validation result
```

### Run Tests
```bash
python tests/test_full_flow.py
# Tests all 32 Northwind migration configs (8 same-model + 24 cross-model)

python tests/test_full_flow.py --only r2d
# Run only tests matching a prefix
```

## Migration Matrix

### Full 4×4 Matrix (16 directions)

|  | → Relational | → Document | → Graph | → Columnar |
|--|:---:|:---:|:---:|:---:|
| **Relational →** | R2R | R2D | R2G | R2C |
| **Document →** | D2R | D2D | D2G | D2C |
| **Graph →** | G2R | G2D | G2G | G2C |
| **Columnar →** | C2R | C2D | C2G | C2C |

Each direction has both **Specific** (`.smel`) and **Generalized** (`.smel_gen`) grammar variants.

### Test Dataset: Northwind

The **Northwind** dataset (8 entities: orders, products, customers, employees, categories, suppliers, shippers, order_details) serves as the primary test corpus. It exists as 4 independent native schema files — one per database model:

| Native File | Model | Format |
|-------------|-------|--------|
| `northwind_postgresql.sql` | Relational | SQL DDL |
| `northwind_mongodb.json` | Document | JSON Schema |
| `northwind_neo4j.cypher` | Graph | Cypher |
| `northwind_cassandra.cql` | Columnar | CQL |

These 4 files produce **32 migration configs** (16 directions × 2 grammar variants), tested automatically via `test_full_flow.py`.

## Project Structure

```
SMEL/
├── grammar/
│   ├── specific/                      # Specific grammar + generated parser
│   │   ├── SMEL_Specific.g4
│   │   └── generate_parser.bat
│   ├── generalized/                   # Generalized grammar + generated parser
│   │   ├── SMEL_Generalized.g4
│   │   └── generate_parser.bat
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
│   ├── generalized/                   # Generalized grammar scripts (.smel_gen)
│   │   ├── person_*.smel_gen          # 4 Person scripts
│   │   └── northwind_*.smel_gen       # 16 Northwind scripts
│   └── test_full_flow.py              # Automated test for all 32 Northwind configs
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
 Source Schema        SMEL Script (.smel/.smel_gen)         Target Schema
 (SQL/JSON/                      │                          (SQL/JSON/
  Cypher/CQL)                    │                           Cypher/CQL)
      │                          ▼                                ▲
      │                   ┌──────────────┐                        │
      │                   │   Step 2     │                        │
      │                   │ SMEL Parsing │                        │
      │                   │  (ANTLR4)    │                        │
      │                   └──────┬───────┘                        │
      ▼                     Operations                            │
 ┌──────────┐  Meta V1  ┌──────────────┐  Meta V2  ┌──────────┐  │
 │ Step 1   │──────────►│   Step 3     │──────────►│  Step 4  │──┘
 │ Reverse  │           │Transformation│           │ Forward  │
 │ Engineer │           │ (apply ops)  │           │ Engineer │
 └──────────┘           └──────────────┘           └──────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────┐          ┌─────────────┐
                        │   Step 5    │          │   Step 5    │
                        │  Layer 1    │          │  Layer 2    │
                        │ Validation  │          │ Validation  │
                        │(Meta V2 vs  │          │(Export → RE │
                        │ expected)   │          │ vs expected)│
                        └─────────────┘          └─────────────┘

 Layer 0: Execution check — no skipped ops, non-empty result
 Layer 1: Meta V2 result  ←compare→  Expected target (parsed from native file)
 Layer 2: Exported target ←RE parse→ Round-trip Meta  ←compare→  Expected target
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

Parses `.smel` or `.smel_gen` files into executable `Operation` objects via ANTLR4.

1. File extension determines grammar: `.smel` → `specific/SMEL_Specific.g4`, `.smel_gen` → `generalized/SMEL_Generalized.g4`
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

#### Step 5: Three-Layer Validation

Every migration is automatically validated through three independent layers. Each layer isolates a different class of defects.

```
Layer 0   Execution check (no errors, no skipped ops, non-empty result)
          ──────────────────────────────────────────────────────────────

Layer 1   SMEL Script Correctness (validate_meta.py)
          ──────────────────────────────────────────────────────────────
          Meta V2 (raw)  ←── compare ──→  Expected Meta
                                            ▲
                                            │  Adapter RE
                                            │
                                          Target native file

Layer 2   Adapter FE Correctness (validate_export.py)
          ──────────────────────────────────────────────────────────────
          Meta V2 ──► Adapter FE ──► Exported Target (text)
                                          │
                                          │  Adapter RE  (round-trip)
                                          ▼
                                     Round-trip Meta  ←── compare ──→  Expected Meta
                                                                         ▲
                                                                         │  Adapter RE
                                                                         │
                                                                       Target native file
```

| Layer | File | What it proves | Fails when |
|-------|------|---------------|------------|
| **Layer 0** | `core.py` | Pipeline executes without errors | Any operation is skipped, throws an exception, or produces no entities |
| **Layer 1** | `validate_meta.py` | SMEL script transforms the schema correctly | Meta V2 diverges from the expected target schema (wrong ops, missing entities, etc.) |
| **Layer 2** | `validate_export.py` | Adapter FE serializes Meta V2 correctly | Exported text → RE round-trip diverges from expected (serialization or parsing bug) |

**How `compare_meta_schemas()` works:** Both layers share the same comparison function. It checks entity names, attribute names and types, constraints (PK structure), references (name, target), embedded relationships, edges, and relationship types. Cardinality differences and key-type representation differences (e.g., `SERIAL` vs `STRING`) are reported as **warnings** rather than hard failures.

##### Where does the "Expected Meta" come from?

The expected target is always derived from a **native schema file** parsed through the adapter's reverse engineering. The file selection depends on the migration type:

```
_resolve_target_file(config_key, target_type)
│
├── Same-model (R2R, D2D, G2G, C2C)
│   └── Uses auto-generated target file
│       e.g., tests/northwind_r2r_target.sql
│       (generated by running the migration once and saving the FE output)
│
└── Cross-model (R2D, D2R, R2G, ... all 12 directions)
    └── Uses the original native file of the TARGET model
        e.g., R2D → tests/northwind_mongodb.json
              D2G → tests/northwind_neo4j.cypher
              G2C → tests/northwind_cassandra.cql
```

##### Cross-Model Closed Loop

For cross-model migrations, the 4 original Northwind files form a **closed validation loop** — each file serves as both source (for outgoing migrations) and expected target (for incoming migrations):

```
         northwind_postgresql.sql
              ▲            │
     R is     │            │  R is
    target    │            │  source
              │            ▼
 northwind_cassandra.cql ←──→ northwind_mongodb.json
              ▲            │
     C is     │            │  D is
    target    │            │  source
              │            ▼
         northwind_neo4j.cypher
```

This means:
- `northwind_postgresql.sql` is the **expected target** for D2R, G2R, C2R
- `northwind_mongodb.json` is the **expected target** for R2D, G2D, C2D
- `northwind_neo4j.cypher` is the **expected target** for R2G, D2G, C2G
- `northwind_cassandra.cql` is the **expected target** for R2C, D2C, G2C

No manually written ground truth is needed for cross-model validation — the original hand-crafted schema files ARE the ground truth.

##### Document Target Normalization

When the target model is **Document** (MongoDB), a special normalization step is applied in Layer 1. The raw Meta V2 uses flat entity names (e.g., `orders`, `ship_destination`) from SMEL operations, but the MongoDB adapter's reverse engineering produces path-based names (e.g., `orders`, `orders.ship_destination`). The `_normalize_to_paths()` function converts flat names to match the adapter's naming convention before comparison.

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
| **Generalized** | `.smel_gen` | `ADD ATTRIBUTE name TO person WITH TYPE String` |

Keyword mapping examples:

| Specific | Generalized |
|----------|-------------|
| `RENAME_ENTITY` | `RENAME ENTITY` |
| `ADD_ATTRIBUTE` | `ADD ATTRIBUTE` |
| `DELETE_CONSTRAINT` | `DELETE CONSTRAINT` |
| `ADD_PRIMARY_KEY` | `ADD KEY` |
| `ADD_PARTITION_KEY` | `ADD PARTITION KEY` |
| `ADD_CLUSTERING_KEY` | `ADD CLUSTERING KEY` |
| `NEST` / `UNNEST` / `MERGE` / `SPLIT` | `NEST` / `UNNEST` / `MERGE` / `SPLIT` |

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
# From grammar/specific/ directory:
cd grammar/specific && java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMEL_Specific.g4

# From grammar/generalized/ directory:
cd grammar/generalized && java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMEL_Generalized.g4

# Or simply run the .bat file in each directory
```

## License

MIT License - See LICENSE file for details.
