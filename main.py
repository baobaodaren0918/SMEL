"""SMEL CLI - Command Line Interface for Schema Migration & Evolution Language"""
import sys
import copy
from pathlib import Path
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).parent))

from Schema.unified_meta_schema import Database, DatabaseType, EntityType, Reference
from Schema.adapters import PostgreSQLAdapter, MongoDBAdapter
from core import (
    SCHEMA_DIR, TESTS_DIR, EQUIVALENT_ATTRS,
    parse_smel, SchemaTransformer,
    PG_REVERSE_TYPE_MAP, MONGO_REVERSE_TYPE_MAP
)

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _get_source_type_str(attr, source_type: str) -> str:
    """Get the original type string for an attribute based on source database type."""
    from Schema.unified_meta_schema import PrimitiveType
    primitive = attr.data_type.primitive_type if hasattr(attr.data_type, 'primitive_type') else PrimitiveType.STRING

    if source_type == "Relational":
        base_type = PG_REVERSE_TYPE_MAP.get(primitive, 'VARCHAR')
        if base_type == 'INTEGER' and attr.is_key:
            return 'SERIAL'
        if base_type == 'VARCHAR':
            max_len = attr.data_type.max_length if hasattr(attr.data_type, 'max_length') and attr.data_type.max_length else 255
            return f"VARCHAR({max_len})"
        if base_type == 'DECIMAL':
            precision = attr.data_type.precision if hasattr(attr.data_type, 'precision') and attr.data_type.precision else 13
            scale = attr.data_type.scale if hasattr(attr.data_type, 'scale') and attr.data_type.scale else 2
            return f"DECIMAL({precision},{scale})"
        return base_type
    else:
        return MONGO_REVERSE_TYPE_MAP.get(primitive, 'string')


def get_source_entity_lines(entity: EntityType, width: int, source_type: str) -> List[str]:
    """Format entity as lines with original source format types."""
    lines = []
    lines.append(f"  {entity.en_name}".ljust(width))

    # Get reference names for FK display
    ref_targets = {r.ref_name: r.get_target_entity_name() for r in entity.relationships if hasattr(r, 'refs_to')}

    for attr in entity.attributes:
        marker = "[PK]" if attr.is_key else ("?" if attr.is_optional else "")
        type_str = _get_source_type_str(attr, source_type)

        # Check if this attribute is a FK
        if attr.attr_name in ref_targets:
            line = f"    {attr.attr_name}: {type_str} -> {ref_targets[attr.attr_name]} {marker}"
        else:
            line = f"    {attr.attr_name}: {type_str} {marker}"
        lines.append(line.ljust(width))

    # Show embedded relationships (for MongoDB source)
    for rel in entity.relationships:
        if hasattr(rel, 'aggregates'):
            lines.append(f"    <> {rel.aggr_name} [{rel.cardinality.value}]".ljust(width))

    return lines


def _get_type_str(data_type) -> str:
    """Get type string from any DataType (handles ListDataType, etc.)."""
    if hasattr(data_type, 'primitive_type'):
        return data_type.primitive_type.value
    elif hasattr(data_type, 'element_type'):
        # ListDataType or SetDataType
        elem_str = _get_type_str(data_type.element_type)
        return f"{elem_str}[]"
    elif hasattr(data_type, 'key_type'):
        # MapDataType
        return "map"
    return "unknown"


def get_entity_lines(entity: EntityType, width: int, highlights: Set[str] = None) -> List[str]:
    """Format entity as lines with Unified Meta Schema format, with optional highlighting."""
    highlights = highlights or set()
    lines = []

    name = entity.en_name
    if name in highlights:
        lines.append(f"{GREEN}{BOLD}  {name}{RESET}".ljust(width + len(GREEN) + len(BOLD) + len(RESET)))
    else:
        lines.append(f"  {name}".ljust(width))

    for attr in entity.attributes:
        marker = "[PK]" if attr.is_key else ("?" if attr.is_optional else "")
        type_str = _get_type_str(attr.data_type)
        line = f"    {attr.attr_name}: {type_str} {marker}"
        lines.append(line.ljust(width))

    for rel in entity.relationships:
        if hasattr(rel, 'refs_to'):
            rel_key = f"{entity.en_name}.{rel.ref_name}"
            if rel_key in highlights:
                line = f"{CYAN}    -> {rel.ref_name} -> {rel.refs_to}{RESET}"
                lines.append(line.ljust(width + len(CYAN) + len(RESET)))
            else:
                lines.append(f"    -> {rel.ref_name} -> {rel.refs_to}".ljust(width))
        elif hasattr(rel, 'aggregates'):
            emb_key = f"{entity.en_name}.{rel.aggr_name}"
            if emb_key in highlights:
                line = f"{GREEN}{BOLD}    <> {rel.aggr_name} [{rel.cardinality.value}]{RESET}"
                lines.append(line.ljust(width + len(GREEN) + len(BOLD) + len(RESET)))
            else:
                lines.append(f"    <> {rel.aggr_name} [{rel.cardinality.value}]".ljust(width))

    return lines


def print_three_meta_schemas(source_db: Database, meta_v1_db: Database, meta_v2_db: Database,
                             source_type: str, target_type: str, changes: List[str]):
    """Print 3 schemas side by side: Source (original format), Meta V1, Meta V2 (with highlighting)."""
    col_width = 38

    nest_highlights = set()
    ref_highlights = set()
    new_entities = set()

    for change in changes:
        if change.startswith("NEST:"):
            nest_highlights.add(change[5:])
        elif change.startswith("ADD_REF:"):
            ref_highlights.add(change[8:])
        elif change.startswith("FLATTEN:"):
            new_entities.add(change.split(":")[1])

    headers = [f"Source ({source_type})", "Meta V1 (Unified)", "Meta V2 (Result)"]
    databases = [source_db, meta_v1_db, meta_v2_db]

    total_width = col_width * 3 + 6
    print("\n" + "=" * total_width)
    print(f"{BOLD} SCHEMA TRANSFORMATION: {source_type} -> {target_type}{RESET}")
    print("=" * total_width)

    print(f"\n  {GREEN}{BOLD}[EMBED]{RESET} = Embedded structure   {CYAN}[REF]{RESET} = Reference/FK")
    print()

    print("-" * total_width)
    header_line = " | ".join(h.center(col_width) for h in headers)
    print(header_line)
    print("-" * total_width)

    all_entities = set()
    for db in databases:
        all_entities.update(db.entity_types.keys())

    for entity_name in sorted(all_entities):
        entity_lines = []
        max_lines = 0

        for i, db in enumerate(databases):
            entity = db.get_entity_type(entity_name)
            if entity:
                if i == 0:
                    # First column: Source with original format types
                    lines = get_source_entity_lines(entity, col_width, source_type)
                else:
                    # Second and third columns: Unified Meta Schema format
                    highlights = set()
                    if i == 2:
                        highlights.update(nest_highlights)
                        highlights.update(ref_highlights)
                        highlights.update(new_entities)
                    lines = get_entity_lines(entity, col_width, highlights)
            else:
                lines = [f"  {YELLOW}({entity_name} --){RESET}".ljust(col_width + len(YELLOW) + len(RESET))]

            entity_lines.append(lines)
            max_lines = max(max_lines, len(lines))

        for lines in entity_lines:
            while len(lines) < max_lines:
                lines.append(" " * col_width)

        for row in range(max_lines):
            print(" | ".join(entity_lines[j][row] for j in range(3)))
        print("-" * total_width)


def print_exported_target(result_db: Database, target_type: str):
    """Print the exported Target Schema in native format."""
    print()
    print("=" * 80)
    print(f"{BOLD} EXPORTED TARGET SCHEMA ({target_type}){RESET}")
    print("=" * 80)
    print()

    if target_type == "Document":
        exported = MongoDBAdapter.export_to_json_string(result_db)
        print(f"{CYAN}MongoDB JSON Schema:{RESET}")
        print("-" * 80)
        print(exported)
    else:
        exported = PostgreSQLAdapter.export_to_sql(result_db)
        print(f"{CYAN}PostgreSQL DDL:{RESET}")
        print("-" * 80)
        print(exported)

    print("-" * 80)


def validate_schemas(generated_db: Database, target_db: Database) -> tuple:
    """Compare generated schema with hand-written target schema."""
    details = []

    gen_entities = set(generated_db.entity_types.keys())
    tgt_entities = set(target_db.entity_types.keys())

    common = gen_entities & tgt_entities
    only_in_gen = gen_entities - tgt_entities
    only_in_tgt = tgt_entities - gen_entities

    details.append(f"    Entities in Generated: {len(gen_entities)}")
    details.append(f"    Entities in Target:    {len(tgt_entities)}")
    details.append(f"    Common entities:       {len(common)}")

    if only_in_gen:
        details.append(f"    {YELLOW}Extra in Generated: {', '.join(sorted(only_in_gen))}{RESET}")
    if only_in_tgt:
        details.append(f"    {RED}Missing (in Target but not Generated): {', '.join(sorted(only_in_tgt))}{RESET}")

    attr_mismatches = []
    for name in common:
        gen_entity = generated_db.get_entity_type(name)
        tgt_entity = target_db.get_entity_type(name)

        gen_attrs = {a.attr_name for a in gen_entity.attributes}
        tgt_attrs = {a.attr_name for a in tgt_entity.attributes}

        missing_attrs = tgt_attrs - gen_attrs
        if missing_attrs:
            attr_mismatches.append(f"{name}: missing {missing_attrs}")

    if attr_mismatches:
        details.append(f"    {YELLOW}Attribute differences:{RESET}")
        for m in attr_mismatches[:5]:
            details.append(f"      - {m}")

    passed = len(only_in_tgt) == 0
    return passed, details


def main():
    print(f"\n{BOLD}{'=' * 60}")
    print(" SMEL - Schema Migration & Evolution Language")
    print(f"{'=' * 60}{RESET}")
    print(f"\n  {CYAN}Cross-Model Migration:{RESET}")
    print("  [1] Relational -> Document")
    print("  [2] Document -> Relational")
    print(f"\n  {CYAN}Schema Evolution (Same Model):{RESET}")
    print("  [3] Relational -> Relational (SQL v1 -> v2)")
    print("  [4] Document -> Document (MongoDB v1 -> v2)")
    print(f"\n  {CYAN}Mini Examples:{RESET}")
    print("  [5] Person: MongoDB -> PostgreSQL (Mini Example)")
    print("\n  [0] Exit")

    try:
        choice = input("\nChoice: ").strip()
    except (KeyboardInterrupt, EOFError):
        return 0

    if choice == "0":
        return 0
    if choice not in ("1", "2", "3", "4", "5"):
        print("Invalid choice")
        return 1

    # Setup paths
    if choice == "1":
        source_file = SCHEMA_DIR / "pain001_postgresql.sql"
        target_file = SCHEMA_DIR / "pain001_mongodb.json"
        smel_file = TESTS_DIR / "pg_to_mongo.smel"
        source_type, target_type = "Relational", "Document"
        source_adapter = PostgreSQLAdapter
        target_adapter = MongoDBAdapter
    elif choice == "2":
        source_file = SCHEMA_DIR / "pain001_mongodb.json"
        target_file = SCHEMA_DIR / "pain001_postgresql.sql"
        smel_file = TESTS_DIR / "mongo_to_pg.smel"
        source_type, target_type = "Document", "Relational"
        source_adapter = MongoDBAdapter
        target_adapter = PostgreSQLAdapter
    elif choice == "3":
        source_file = SCHEMA_DIR / "pain001_postgresql.sql"
        target_file = SCHEMA_DIR / "pain001_postgresql_v2.sql"
        smel_file = TESTS_DIR / "sql_v1_to_v2.smel"
        source_type, target_type = "Relational", "Relational"
        source_adapter = PostgreSQLAdapter
        target_adapter = PostgreSQLAdapter
    elif choice == "4":
        source_file = SCHEMA_DIR / "pain001_mongodb.json"
        target_file = SCHEMA_DIR / "pain001_mongodb_v2.json"
        smel_file = TESTS_DIR / "mongo_v1_to_v2.smel"
        source_type, target_type = "Document", "Document"
        source_adapter = MongoDBAdapter
        target_adapter = MongoDBAdapter
    else:  # choice == "5"
        source_file = TESTS_DIR / "person_mongodb.json"
        target_file = TESTS_DIR / "person_postgresql.sql"
        smel_file = TESTS_DIR / "person_mongo_to_pg_minibeispiel1.smel"
        source_type, target_type = "Document", "Relational"
        source_adapter = MongoDBAdapter
        target_adapter = PostgreSQLAdapter

    # Check files exist
    for f in [source_file, target_file, smel_file]:
        if not f.exists():
            print(f"{RED}[ERROR] File not found: {f}{RESET}")
            return 1

    # Step 1: Reverse Engineering
    print(f"\n{CYAN}[Step 1] Reverse Engineering: {source_file.name} -> Meta V1{RESET}")
    source_db = source_adapter.load_from_file(str(source_file), "source")
    meta_v1_db = copy.deepcopy(source_db)
    print(f"         Loaded {len(source_db.entity_types)} entities")

    # Step 2: Transformation
    print(f"\n{CYAN}[Step 2] Transformation: Meta V1 + {smel_file.name} -> Meta V2{RESET}")
    context, operations, errors = parse_smel(smel_file)
    if errors:
        print(f"{RED}[ERROR] Parse errors: {errors}{RESET}")
        return 1

    transformer = SchemaTransformer(source_db)
    result_db = transformer.execute(operations)
    result_db.db_type = DatabaseType.DOCUMENT if target_type == "Document" else DatabaseType.RELATIONAL
    print(f"         Applied {len(operations)} operations, result has {len(result_db.entity_types)} entities")

    # Step 3: Forward Engineering
    print(f"\n{CYAN}[Step 3] Forward Engineering: Meta V2 -> Generated {target_type} DDL{RESET}")
    if target_type == "Document":
        generated_ddl = MongoDBAdapter.export_to_json_string(result_db)
    else:
        generated_ddl = PostgreSQLAdapter.export_to_sql(result_db)
    print(f"         Generated {len(generated_ddl)} characters")

    # Step 4: Validation
    print(f"\n{CYAN}[Step 4] Validation: Generated DDL vs {target_file.name}{RESET}")
    target_db = target_adapter.load_from_file(str(target_file), "target")
    validation_passed, validation_details = validate_schemas(result_db, target_db)

    # Display results
    print_three_meta_schemas(source_db, meta_v1_db, result_db, source_type, target_type, transformer.changes)
    print_exported_target(result_db, target_type)

    print(f"\n{BOLD}{'=' * 60}")
    print(" VALIDATION: Generated vs Hand-written Target")
    print(f"{'=' * 60}{RESET}")
    for detail in validation_details:
        print(f"  {detail}")

    print(f"\n  {'=' * 40}")
    if validation_passed:
        print(f"  {GREEN}{BOLD}[PASS] Schema structures match!{RESET}")
    else:
        print(f"  {YELLOW}{BOLD}[WARN] Schema differences detected{RESET}")
    print(f"  {'=' * 40}")

    # Summary
    print(f"\n{BOLD}{'=' * 50}")
    print(" SUMMARY")
    print(f"{'=' * 50}{RESET}")
    print(f"\n  Source: {source_file.name} ({len(source_db.entity_types)} entities)")
    print(f"  Target: {target_file.name} ({len(target_db.entity_types)} entities)")
    print(f"  Result: {len(result_db.entity_types)} entities after {len(operations)} operations")
    print(f"\n  {GREEN}{BOLD}[OK] TRANSFORMATION COMPLETE{RESET}")
    print(f"  {'=' * 30}\n")

    return 0 if validation_passed else 1


if __name__ == "__main__":
    sys.exit(main())
