# SMEL - Schema Migration & Evolution Language

A formally defined DSL for schema migration and evolution between heterogeneous database systems, supporting 4 data models with a full 4×4 migration matrix and two-layer automated validation.

> **Note:** The language is referred to as **SMILE** (Schema Migration and Evolution Language) in the accompanying thesis. The codebase retains the earlier working title **SMEL** in file and module names.

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

python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

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
- **Migration** tab: Run any migration, view SMEL script with syntax highlighting, step-by-step operation results, source/target schema comparison, and validation results
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
result = run_migration('northwind_d2g_generalized') # Document -> Graph
result = run_migration('northwind_g2c_specific')    # Graph -> Columnar

# Same-model evolution (Northwind)
result = run_migration('northwind_r2r_specific')    # Relational V1 -> V2

print(result['exported_target'])     # Generated target schema
print(result['validation_meta'])     # Layer 1 validation result
print(result['validation_export'])   # Layer 2 validation result
```

### Run Tests
```bash
python -m pytest tests/ -q
# 72 tests: 32 full-flow (Northwind) + 40 parser tests

python -m pytest tests/test_full_flow.py -k r2d -q
# Run only tests matching a keyword
```

## Migration Matrix

### Full 4×4 Matrix (16 directions)

|  | → Relational | → Document | → Graph | → Columnar |
|--|:---:|:---:|:---:|:---:|
| **Relational →** | R2R | R2D | R2G | R2C |
| **Document →** | D2R | D2D | D2G | D2C |
| **Graph →** | G2R | G2D | G2G | G2C |
| **Columnar →** | C2R | C2D | C2G | C2C |

- Diagonal (R2R, D2D, G2G, C2C) = **same-model evolution**
- Off-diagonal = **cross-model migration**
- Each direction has both **Specific** (`.smel`) and **Generalized** (`.smel_gen`) grammar variants = **32 Northwind configs**

### Test Dataset: Northwind

The Northwind dataset (8 entities: orders, products, customers, employees, categories, suppliers, shippers, order\_details) exists as 4 independent native schema files:

| Native File | Model |
|-------------|-------|
| `tests/northwind_postgresql.sql` | Relational |
| `tests/northwind_mongodb.json` | Document |
| `tests/northwind_neo4j.cypher` | Graph |
| `tests/northwind_cassandra.cql` | Columnar |

## Project Structure

```
SMEL/
├── grammar/
│   ├── specific/                      # Specific grammar (38 keywords)
│   │   ├── SMEL_Specific.g4
│   │   └── generate_parser.bat
│   ├── generalized/                   # Generalized grammar (26 composable tokens)
│   │   ├── SMEL_Generalized.g4
│   │   └── generate_parser.bat
│   └── antlr-4.13.2-complete.jar
├── Schema/
│   ├── unified_meta_schema.py         # M-Model+ Meta Schema
│   └── adapters/
│       ├── __init__.py                # ADAPTER_REGISTRY
│       ├── postgresql_adapter.py      # PostgreSQL RE/FE
│       ├── mongodb_adapter.py         # MongoDB RE/FE
│       ├── neo4j_adapter.py           # Neo4j RE/FE
│       └── cassandra_adapter.py       # Cassandra RE/FE
├── tests/
│   ├── northwind_*.sql/json/cypher/cql  # 4 source schemas
│   ├── northwind_*_target.*             # 4 evolution targets (V2)
│   ├── specific/                        # 20 Specific scripts (.smel)
│   ├── generalized/                     # 20 Generalized scripts (.smel_gen)
│   ├── test_full_flow.py                # 32 Northwind migration tests
│   └── test_parser.py                   # 40 parser tests
├── core.py                            # SchemaTransformer (30 operation handlers)
├── smel_listeners.py                  # ANTLR listeners (Specific + Generalized)
├── parser_factory.py                  # Grammar auto-detection by file extension
├── config.py                          # Migration registry (40 configs)
├── validate_meta.py                   # Layer 1: Meta V2 vs expected schema
├── validate_export.py                 # Layer 2: Export round-trip verification
├── main.py                            # CLI entry point
└── web_server.py                      # Web interface (Flask)
```

## Architecture

### Five-Phase Pipeline

```
 Source Schema        SMEL Script (.smel/.smel_gen)         Target Schema
 (SQL/JSON/                      │                          (SQL/JSON/
  Cypher/CQL)                    │                           Cypher/CQL)
      │                          ▼                                ▲
      │                   ┌──────────────┐                        │
      │                   │   Phase 2    │                        │
      │                   │ SMEL Parsing │                        │
      │                   │  (ANTLR 4)   │                        │
      │                   └──────┬───────┘                        │
      ▼                     Operations                            │
 ┌──────────┐  Meta V1  ┌──────────────┐  Meta V2  ┌──────────┐  │
 │ Phase 1  │──────────►│   Phase 3    │──────────►│ Phase 4  │──┘
 │ Reverse  │           │SchemaTransf. │           │ Forward  │
 │ Engineer │           │ (30 handlers)│           │ Engineer │
 └──────────┘           └──────────────┘           └──────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────┐          ┌─────────────┐
                        │   Phase 5   │          │   Phase 5   │
                        │  Layer 1    │          │  Layer 2    │
                        │ Validation  │          │ Validation  │
                        │(Meta V2 vs  │          │(Export → RE │
                        │ expected)   │          │ round-trip) │
                        └─────────────┘          └─────────────┘
```

| Phase | Component | Input → Output |
|-------|-----------|---------------|
| 1. Reverse Engineering | `ADAPTER_REGISTRY[source_type]` | Native DDL → Meta V1 (M-Model+) |
| 2. SMEL Parsing | `parser_factory.parse_smel_auto()` | `.smel`/`.smel_gen` → `Operation` list |
| 3. Transformation | `SchemaTransformer` (30 handlers) | Meta V1 + Operations → Meta V2 |
| 4. Forward Engineering | `ADAPTER_REGISTRY[target_type]` | Meta V2 → Target DDL |
| 5. Validation | `validate_meta` + `validate_export` | Two-layer correctness check |

### Two-Layer Validation

| Layer | File | What it proves | How |
|-------|------|---------------|-----|
| **Layer 1** | `validate_meta.py` | SMEL script correctness | Meta V2 vs expected target schema |
| **Layer 2** | `validate_export.py` | Adapter FE correctness | Exported target → RE round-trip vs expected |

For **cross-model** migrations, the 4 original Northwind files form a closed validation loop — each file is both source (outgoing) and expected target (incoming). No manually written ground truth needed.

For **same-model** evolution, dedicated target files (`northwind_r2r_target.sql`, etc.) serve as expected output.

### M-Model+ Meta Schema

The hub representation (`Schema/unified_meta_schema.py`) that makes cross-model migration possible:

```
Database
  └── EntityType (TABLE / DOCUMENT / VERTEX / WIDE_COLUMN_TABLE / EDGE)
        ├── Attribute (name, data_type, is_key, is_optional)
        ├── Constraint
        │     ├── UniqueConstraint (PK: simple / partition / clustering)
        │     └── ForeignKeyConstraint
        └── Relationship (ABC)
              ├── Reference (FK → target entity)
              ├── Embedded (nested object / array)
              └── Edge (graph relationship)
```

## SMEL Operations (30 total)

### Structural Operations (9)

| Operation | Description | Typical Use |
|-----------|-------------|-------------|
| `NEST` | Embed entity as nested object | R→D: table → embedded document |
| `UNNEST` | Extract nested object to entity | D→R: embedded → table |
| `FLATTEN` | Merge child fields into parent | D→R: flatten nested address |
| `UNFLATTEN` | Group flat fields into nested object | R→D: columns → sub-object |
| `WIND` | Convert scalar to array | R→D: column → array |
| `UNWIND` | Expand array to rows/entity | D→R: array → table |
| `MERGE` | Combine two entities | R2R: denormalize |
| `SPLIT` | Partition entity vertically | R2R: split table |
| `TRANSFORM` | Entity ↔ Relationship conversion | R↔G: table ↔ edge |

### Attribute Operations (5)

| Operation | Description |
|-----------|-------------|
| `ADD_ATTRIBUTE` | Add field to entity |
| `DELETE_ATTRIBUTE` | Remove field from entity |
| `RENAME_ATTRIBUTE` | Rename field |
| `COPY_ATTRIBUTE` | Copy field to another entity |
| `MOVE_ATTRIBUTE` | Move field to another entity |

### Entity Operations (4)

| Operation | Description |
|-----------|-------------|
| `ADD_ENTITY` | Create new entity (supports EDGE with FROM...TO) |
| `DELETE_ENTITY` | Remove entity (cleans up cross-references) |
| `RENAME_ENTITY` | Rename entity (updates all references) |
| `COPY_ENTITY` | Deep-copy entity structure |

### Key & Constraint Operations (7)

| Operation | Description |
|-----------|-------------|
| `ADD_PRIMARY_KEY` / `ADD_UNIQUE_KEY` / `ADD_FOREIGN_KEY` | Add key constraint |
| `DELETE_PRIMARY_KEY` / `DELETE_UNIQUE_KEY` / `DELETE_FOREIGN_KEY` | Remove key constraint |
| `ADD_PARTITION_KEY` / `ADD_CLUSTERING_KEY` | Add Cassandra-specific key |
| `DELETE_PARTITION_KEY` / `DELETE_CLUSTERING_KEY` | Remove Cassandra-specific key |
| `ADD_CONSTRAINT` | Add FK reference with cardinality |
| `DELETE_CONSTRAINT` | Remove FK reference by field |
| `CAST_CONSTRAINT` | Change constraint type (e.g., UNIQUE → PARTITION) |

### Type & Cardinality Operations (3)

| Operation | Description |
|-----------|-------------|
| `CAST_ATTRIBUTE` | Change attribute data type |
| `CAST_ENTITY` | Change entity kind (e.g., TABLE → DOCUMENT) |
| `RECARD` | Change relationship cardinality |

### Embedded & Label Operations (4)

| Operation | Description |
|-----------|-------------|
| `ADD_EMBEDDED` / `DELETE_EMBEDDED` | Add/remove embedded relationship |
| `ADD_LABEL` / `DELETE_LABEL` | Add/remove graph node label |

## Grammar Variants

Two functionally equivalent grammars — same abstract syntax, different concrete syntax:

| Grammar | Extension | Keywords | Example |
|---------|-----------|----------|---------|
| **Specific** | `.smel` | 38 dedicated | `ADD_ATTRIBUTE name TO person WITH TYPE String` |
| **Generalized** | `.smel_gen` | 26 composable | `ADD ATTRIBUTE name TO person WITH TYPE String` |

The Generalized grammar reduces keyword count by ~32% through verb+object composition (6 verbs × 5 object types + modifiers). Structural operations (`NEST`, `UNNEST`, `FLATTEN`, `UNFLATTEN`, `WIND`, `UNWIND`, `MERGE`, `SPLIT`, `TRANSFORM`) are identical in both variants.

## SMEL Script Examples

### Cross-Model: Relational → Document (R2D)

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

### Same-Model Evolution: Relational V1 → V2 (R2R)

```smel
MIGRATION northwind_pg1_to_pg2:1.0
FROM RELATIONAL TO RELATIONAL
USING northwind_schema:1

-- Denormalize: merge categories into products
DELETE_CONSTRAINT products.category_id
DELETE_ATTRIBUTE products.category_id
DELETE_PRIMARY_KEY category_id FROM categories
DELETE_ATTRIBUTE categories.category_id
MERGE categories, products INTO products

-- Vertical partition: split customer contacts
SPLIT customers INTO customers:customer_id, company_name, street, city, region,
  postal_code, country; customer_contacts:customer_id, contact_name, contact_title,
  phone, fax

-- Add new entities for territory management
ADD_ENTITY region WITH ATTRIBUTES (region_id String, region_description String)
ADD_ENTITY territories WITH ATTRIBUTES (territory_id String, territory_description String, region_id String)
```

## Regenerating Parsers

After modifying `.g4` grammar files:

```bash
cd grammar/specific
java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMEL_Specific.g4

cd grammar/generalized
java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMEL_Generalized.g4
```

## License

MIT License
