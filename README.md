# SMILE - Schema Migration & Evolution Language

A formally defined DSL for schema migration and evolution between heterogeneous database systems, supporting 4 data models with a full 4×4 migration matrix and two-layer automated validation.

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
git clone https://github.com/baobaodaren0918/SMILE-3.0.git
cd SMILE-3.0

python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

## Usage

### Web Interface
```bash
python web_server.py
# Opens at http://localhost:5601
```

The web interface provides five tabs:
- **Source Schemas** — inspect any of the 4 native schemas (SQL, JSON, Cypher, CQL) and the resulting Meta V1
- **User Transformation** — point at a source DDL, pick a target DB, generate a SMILE header, edit the script in the in-browser Ace editor (autocomplete + syntax highlighting), validate, then run; the resulting Meta V2 and Target Schema panels are rendered read-only
- **Schema Comparison** — side-by-side card view of Meta V1 vs Meta V2 with structural diff highlighting
- **SMILE Script** — script rendering and syntax-highlighted preview for any registered migration config
- **Migration / Evolution Process** — full pipeline run (parse → transform → export → validate) with step-by-step operation log and Layer 1 / Layer 2 validation results

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
# 73 tests: 32 full-flow (Northwind 4×4 × 2 grammars) + 41 parser tests
#           (20 specific + 20 generalized + 1 grammar-completeness script)

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
- Each direction has both **Specific** (`.smile`) and **Generalized** (`.smile_gen`) grammar variants = **32 Northwind configs**

In addition to the 32 Northwind configs, the registry includes 8 **Person** mini-dataset configs (used as a smaller smoke-test surface) and 1 **grammar-completeness** script that exercises the operations not naturally hit by the Northwind matrix — **41 configs in total**.

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
SMILE/
├── grammar/
│   ├── specific/                      # Specific grammar (dedicated underscore-form keywords)
│   │   ├── SMILE_Specific.g4
│   │   └── generate_parser.bat
│   ├── generalized/                   # Generalized grammar (verb + object composition)
│   │   ├── SMILE_Generalized.g4
│   │   └── generate_parser.bat
│   ├── smile_operations.json          # Single source of truth for all 36 ops (used by
│   │                                  #   schema_diff, script_renderer, and editor autocomplete)
│   └── antlr-4.13.2-complete.jar
├── Schema/
│   ├── unified_meta_schema.py         # M-Model+ Meta Schema
│   └── adapters/
│       ├── __init__.py                # ADAPTER_REGISTRY
│       ├── postgresql_adapter.py      # PostgreSQL RE/FE
│       ├── mongodb_adapter.py         # MongoDB RE/FE
│       ├── neo4j_adapter.py           # Neo4j RE/FE
│       └── cassandra_adapter.py       # Cassandra RE/FE
├── static/
│   └── smile-app.js                   # Web UI app code (extracted from web_server.py)
├── tests/
│   ├── northwind_*.sql/json/cypher/cql  # 4 source schemas (Northwind, all 4 paradigms)
│   ├── northwind_*_target.*             # Same-model evolution targets (V2)
│   ├── person_*                         # Person mini-dataset (8 configs)
│   ├── specific/                        # 20 Specific scripts (.smile)   — 16 Northwind + 4 Person
│   ├── generalized/                     # 20 Generalized scripts (.smile_gen)
│   ├── grammar_completeness/            # source.sql + test_all_unused.smile
│   │                                    #   (exercises the 9 ops not hit by the matrix)
│   ├── test_full_flow.py                # 32 Northwind migration tests
│   └── test_parser.py                   # 41 parser tests
├── core.py                            # SchemaTransformer (30 handler methods covering 36 surface ops)
│                                      #   plus run_load / run_apply / run_export pipeline helpers
├── smile_listeners.py                  # ANTLR listeners (Specific + Generalized)
├── parser_factory.py                  # Grammar auto-detection by file extension
├── operation_params.py                # Per-op param dataclasses (NestParams, UnnestParams, ...)
├── schema_inspector.py                # Reverse-engineer any source DDL → Meta V1 (web UI only)
├── schema_diff.py                     # Meta V1 vs Meta V2 → OpRecord list (used by script_renderer)
├── script_renderer.py                 # OpRecord list → Specific or Generalized SMILE script
├── config.py                          # Migration registry (41 configs: 32 Northwind + 8 Person + 1 grammar-completeness)
├── validate_meta.py                   # Layer 1: Meta V2 vs expected schema
├── validate_export.py                 # Layer 2: Export round-trip verification
├── main.py                            # CLI entry point
└── web_server.py                      # Web interface (http.server, port 5601)
```

## Architecture

### Five-Phase Pipeline

```
 Source Schema        SMILE Script (.smile/.smile_gen)         Target Schema
 (SQL/JSON/                      │                          (SQL/JSON/
  Cypher/CQL)                    │                           Cypher/CQL)
      │                          ▼                                ▲
      │                   ┌──────────────┐                        │
      │                   │   Phase 2    │                        │
      │                   │ SMILE Parsing │                        │
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
| 1. Reverse Engineering | `ADAPTER_REGISTRY[source_type]` (driven by `core.run_load`) | Native DDL → Meta V1 (M-Model+) |
| 2. SMILE Parsing | `parser_factory.parse_smile_auto()` | `.smile` / `.smile_gen` → `Operation` list |
| 3. Transformation | `SchemaTransformer` (30 handlers, called via `core.run_apply`) | Meta V1 + Operations → Meta V2 |
| 4. Forward Engineering | `ADAPTER_REGISTRY[target_type]` (driven by `core.run_export`) | Meta V2 → Target DDL |
| 5. Validation | `validate_meta` + `validate_export` | Two-layer correctness check |

`core.run_migration()` is a thin orchestrator on top of the three pipeline helpers (`run_load`, `run_apply`, `run_export`) so each phase can also be invoked independently from the web UI's User Transformation flow.

### Two-Layer Validation

| Layer | File | What it proves | How |
|-------|------|---------------|-----|
| **Layer 1** | `validate_meta.py` | SMILE script correctness | Meta V2 vs expected target schema |
| **Layer 2** | `validate_export.py` | Adapter FE correctness | Exported target → RE round-trip vs expected |

For **cross-model** migrations, the 4 original Northwind files form a closed validation loop — each file is both source (outgoing) and expected target (incoming). No manually written ground truth needed.

For **same-model** evolution, dedicated target files (`northwind_r2r_target.sql`, etc.) serve as expected output.

### M-Model+ Meta Schema

The hub representation (`Schema/unified_meta_schema.py`) that makes cross-model migration possible:

```
Database
  └── EntityType (TABLE / DOCUMENT / VERTEX / WIDE_COLUMN_TABLE / EDGE)
        ├── Property (name, data_type, is_key, is_optional)
        ├── Constraint
        │     ├── UniqueConstraint (PK: simple / partition / clustering)
        │     └── ForeignKeyConstraint
        └── Relationship (ABC)
              ├── Reference (FK → target entity)
              ├── Embedded (nested object / array)
              └── Edge (graph relationship)
```

## SMILE Operations (36 surface ops)

The grammar exposes 36 named operations grouped as **9 structural + 6 property + 4 entity + 11 key/constraint + 2 type/cardinality + 4 embedded/label**. Many of them collapse at the IR level — e.g. `ADD_PRIMARY_KEY` / `ADD_UNIQUE_KEY` / `ADD_PARTITION_KEY` / `ADD_CLUSTERING_KEY` all dispatch through a single `_handle_add_key` — so `core.py` ships 30 unique handler methods. The single source of truth for the surface op set is `grammar/smile_operations.json` (also consumed by the web-UI Ace autocomplete).

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

### Property Operations (6)

| Operation | Description |
|-----------|-------------|
| `ADD_PROPERTY` | Add field to entity |
| `DELETE_PROPERTY` | Remove field from entity |
| `RENAME_PROPERTY` | Rename field |
| `COPY_PROPERTY` | Copy field to another entity |
| `MOVE_PROPERTY` | Move field to another entity |
| `CAST_PROPERTY` | Change property data type |

### Entity Operations (4)

| Operation | Description |
|-----------|-------------|
| `ADD_ENTITY` | Create new entity (supports EDGE with FROM...TO) |
| `DELETE_ENTITY` | Remove entity (cleans up cross-references) |
| `RENAME_ENTITY` | Rename entity (updates all references) |
| `COPY_ENTITY` | Deep-copy entity structure |

### Key & Constraint Operations (11)

| Operation | Description |
|-----------|-------------|
| `ADD_PRIMARY_KEY` / `DELETE_PRIMARY_KEY` | Add or remove a primary key |
| `ADD_UNIQUE_KEY` / `DELETE_UNIQUE_KEY` | Add or remove a unique constraint |
| `ADD_FOREIGN_KEY` / `DELETE_FOREIGN_KEY` | Add (with `REFERENCES` + cardinality) or remove an FK |
| `ADD_PARTITION_KEY` / `DELETE_PARTITION_KEY` | Cassandra-specific partition key |
| `ADD_CLUSTERING_KEY` / `DELETE_CLUSTERING_KEY` | Cassandra-specific clustering key |
| `CAST_CONSTRAINT` | Change constraint type (e.g., `UNIQUE` → `PARTITION`) |

### Type & Cardinality Operations (2)

| Operation | Description |
|-----------|-------------|
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
| **Specific** | `.smile` | 38 dedicated | `ADD_PROPERTY name TO person WITH TYPE String` |
| **Generalized** | `.smile_gen` | 27 composable | `ADD PROPERTY name TO person WITH TYPE String` |

The Generalized grammar reduces keyword count by ~29% through verb+object composition (6 verbs × 5 object types + modifiers). Structural operations (`NEST`, `UNNEST`, `FLATTEN`, `UNFLATTEN`, `WIND`, `UNWIND`, `MERGE`, `SPLIT`, `TRANSFORM`) are identical in both variants.

## SMILE Script Examples

### Cross-Model: Relational → Document (R2D)

```smile
MIGRATION northwind_pg_to_mongo:1.0
FROM RELATIONAL TO DOCUMENT
USING adapted_northwind_schema VERSION 1

-- Embed tables as nested objects (deepest first)
NEST categories:category_name, description IN products.category
  WHERE products.category_id = categories.category_id
NEST suppliers:company_name, contact_name, ... IN products.supplier
  WHERE products.supplier_id = suppliers.supplier_id

-- Group flat shipping fields into nested object
UNFLATTEN orders:ship_address, ship_city, ship_region, ship_postal_code, ship_country
  AS ship_destination

-- Rename PK for MongoDB convention
RENAME_PROPERTY order_id TO _id IN orders
```

### Same-Model Evolution: Relational V1 → V2 (R2R)

```smile
EVOLUTION northwind_r2r:1.0
FROM RELATIONAL TO RELATIONAL
USING adapted_northwind_schema VERSION 1 TO 2

-- Denormalize: merge categories into products
DELETE_FOREIGN_KEY products.category_id
DELETE_PROPERTY products.category_id
DELETE_PRIMARY_KEY category_id FROM categories
DELETE_PROPERTY categories.category_id
MERGE categories, products INTO products

-- Vertical partition: split customer contacts
SPLIT customers INTO customers:customer_id, company_name, street, city, region,
  postal_code, country; customer_contacts:customer_id, contact_name, contact_title,
  phone, fax

-- Add new entities for territory management
ADD_ENTITY region WITH PROPERTIES (region_id String, region_description String)
ADD_ENTITY territories WITH PROPERTIES (territory_id String, territory_description String, region_id String)
```

## Regenerating Parsers

After modifying `.g4` grammar files:

```bash
cd grammar/specific
java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMILE_Specific.g4

cd grammar/generalized
java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMILE_Generalized.g4
```

## License

MIT License
