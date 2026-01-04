#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Meta Schema Inspector Tool
用于查看 Meta V1 (Import后) 和 Meta V2 (SMEL执行后) 的结构

使用方法:
    # 查看 Meta V1 (从源Schema导入)
    python inspect_meta.py --source Schema/pain001_postgresql.sql
    python inspect_meta.py --source Schema/pain001_mongodb.json

    # 查看 Meta V2 (执行SMEL后)
    python inspect_meta.py --source Schema/pain001_postgresql.sql --smel tests/pg_to_mongo.smel
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Schema.unified_meta_schema import Database, Reference, Aggregate


def import_schema(source_path: str) -> Database:
    """Import schema from file based on extension."""
    ext = os.path.splitext(source_path)[1].lower()

    if ext == '.sql':
        from Schema.adapters.postgresql_adapter import PostgreSQLAdapter
        return PostgreSQLAdapter.load_from_file(source_path)
    elif ext == '.json':
        from Schema.adapters.mongodb_adapter import MongoDBAdapter
        return MongoDBAdapter.load_from_file(source_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def execute_smel(db: Database, smel_path: str) -> Database:
    """Execute SMEL script on database."""
    # Import main.py functions to reuse parsing and transformation logic
    import main

    # Parse SMEL file
    context, operations, errors = main.parse_smel(smel_path)

    if errors:
        print(f"SMEL Parse errors: {errors}")
        return db

    # Apply transformations
    transformer = main.SchemaTransformer(db)
    result_db = transformer.execute(operations)

    return result_db


def print_database(db: Database, title: str = "Meta Schema"):
    """Pretty print database structure."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print(f"Database: {db.db_name}")
    print(f"Type: {db.db_type.value}")
    print(f"Entities: {len(db.entity_types)}")
    print("-" * 70)

    for entity_name in sorted(db.entity_types.keys()):
        entity = db.get_entity_type(entity_name)
        print(f"\n[Entity] {entity_name}")

        # Attributes
        if entity.attributes:
            print("  Attributes:")
            for attr in entity.attributes:
                key_mark = " (PK)" if attr.is_key else ""
                opt_mark = " (optional)" if attr.is_optional else ""
                print(f"    - {attr.name}: {attr.data_type}{key_mark}{opt_mark}")

        # Relationships (contains both Reference and Aggregate/Embedded)
        if entity.relationships:
            references = [r for r in entity.relationships if isinstance(r, Reference)]
            aggregates = [r for r in entity.relationships if isinstance(r, Aggregate)]

            if references:
                print("  References (FK):")
                for ref in references:
                    target = ref.get_target_entity_name()
                    print(f"    -> {ref.ref_name} -> {target}")

            if aggregates:
                print("  Embedded/Aggregates:")
                for agg in aggregates:
                    target = agg.get_target_entity_name()
                    print(f"    <> {agg.aggr_name} -> {target} [{agg.cardinality.value}]")

    print("\n" + "=" * 70)


def print_smel_preview(db: Database, direction: str):
    """Print helpful hints for writing SMEL scripts."""
    print("\n" + "-" * 70)
    print("  SMEL Script Writing Reference")
    print("-" * 70)

    if direction == "to_document":
        print("\n  Direction: RELATIONAL -> DOCUMENT")
        print("  Available operations: NEST, DELETE REFERENCE\n")
        print("  Example SMEL statements:")

        for entity_name in db.entity_types.keys():
            entity = db.get_entity_type(entity_name)
            references = [r for r in entity.relationships if isinstance(r, Reference)]
            for ref in references:
                target = ref.get_target_entity_name()
                print(f"    NEST {target} INTO {entity_name} AS <alias>")
                print(f"        WITH CARDINALITY ONE_TO_ONE")
                print(f"        -- or --")
                print(f"    DELETE REFERENCE {entity_name}.{ref.ref_name}")
                print()
    else:
        print("\n  Direction: DOCUMENT -> RELATIONAL")
        print("  Available operations: FLATTEN, UNWIND, ADD REFERENCE\n")
        print("  Example SMEL statements:")

        from Schema.unified_meta_schema import Cardinality
        for entity_name in db.entity_types.keys():
            entity = db.get_entity_type(entity_name)
            aggregates = [r for r in entity.relationships if isinstance(r, Aggregate)]
            for agg in aggregates:
                target = agg.get_target_entity_name()
                if agg.cardinality in [Cardinality.ONE_TO_ONE, Cardinality.ZERO_TO_ONE]:
                    print(f"    FLATTEN {entity_name}.{agg.aggr_name} AS {target}")
                    print(f"        ADD REFERENCE {agg.aggr_name}_id TO {target}")
                else:
                    print(f"    UNWIND {entity_name}.{agg.aggr_name}[] AS {target}")
                    print(f"        GENERATE KEY <key_name> AS SERIAL")
                    print(f"        ADD REFERENCE <fk_name> TO {entity_name}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description='Inspect Meta Schema structure (V1 or V2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View Meta V1 from PostgreSQL
  python inspect_meta.py --source Schema/pain001_postgresql.sql

  # View Meta V1 from MongoDB
  python inspect_meta.py --source Schema/pain001_mongodb.json

  # View Meta V2 after SMEL execution
  python inspect_meta.py --source Schema/pain001_postgresql.sql --smel tests/pg_to_mongo.smel

  # Show SMEL writing hints
  python inspect_meta.py --source Schema/pain001_postgresql.sql --hints
        """
    )

    parser.add_argument('--source', '-s', required=True,
                        help='Source schema file (.sql or .json)')
    parser.add_argument('--smel', '-m',
                        help='SMEL script to execute (optional, for Meta V2)')
    parser.add_argument('--hints', '-H', action='store_true',
                        help='Show SMEL writing hints based on Meta V1')

    args = parser.parse_args()

    # Import source schema -> Meta V1
    print(f"\nLoading source: {args.source}")
    db = import_schema(args.source)

    if args.smel:
        # Show Meta V1 first
        print_database(db, "Meta V1 (Before SMEL)")

        # Execute SMEL -> Meta V2
        print(f"\nExecuting SMEL: {args.smel}")
        db = execute_smel(db, args.smel)
        print_database(db, "Meta V2 (After SMEL)")
    else:
        # Just show Meta V1
        print_database(db, "Meta V1 (Imported)")

        if args.hints:
            # Determine direction based on source type
            ext = os.path.splitext(args.source)[1].lower()
            direction = "to_document" if ext == '.sql' else "to_relational"
            print_smel_preview(db, direction)


if __name__ == '__main__':
    main()
