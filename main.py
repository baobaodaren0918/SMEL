"""SMEL CLI - Command Line Interface for Schema Migration & Evolution Language"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core import run_migration
from config import MIGRATION_CONFIGS

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Menu choice -> config key mapping
CHOICE_MAP = {
    "1": "person_d2r_specific",
    "2": "person_d2r_pauschalisiert",
    "3": "person_r2d_specific",
    "4": "person_r2d_pauschalisiert",
}


def print_operations(operations_detail):
    """Print operation execution results."""
    for op in operations_detail:
        keyword = op.get("original_keyword", op["type"])
        if op["status"] == "success":
            print(f"         {GREEN}[OK]{RESET} {keyword}")
        else:
            print(f"         {YELLOW}[SKIP]{RESET} {keyword} (no effect)")


def print_schema_comparison(result):
    """Print source and result schema side by side."""
    source_type = result["source_type"]
    target_type = result["target_type"]
    meta_v1 = result["meta_v1"]
    meta_v2 = result["result"]
    changes = result["changes"]
    col_width = 38

    # Collect highlights from changes
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

    total_width = col_width * 2 + 3
    print("\n" + "=" * total_width)
    print(f"{BOLD} SCHEMA TRANSFORMATION: {source_type} -> {target_type}{RESET}")
    print("=" * total_width)

    print(f"\n  {GREEN}{BOLD}[EMBED]{RESET} = Embedded   {CYAN}[REF]{RESET} = Reference/FK")
    print()

    headers = ["Meta V1 (Source)", "Meta V2 (Result)"]
    print("-" * total_width)
    print(" | ".join(h.center(col_width) for h in headers))
    print("-" * total_width)

    all_entities = set(list(meta_v1.keys()) + list(meta_v2.keys()))
    for entity_name in sorted(all_entities):
        columns = []
        max_lines = 0

        for i, schema in enumerate([meta_v1, meta_v2]):
            entity = schema.get(entity_name)
            if entity:
                lines = [f"  {entity['name']}".ljust(col_width)]
                for attr in entity.get("attributes", []):
                    marker = "[PK]" if attr["is_key"] else ("?" if attr["is_optional"] else "")
                    is_highlighted = (i == 1 and entity_name in new_entities)
                    prefix = f"{GREEN}" if is_highlighted else ""
                    suffix = f"{RESET}" if is_highlighted else ""
                    line = f"    {attr['name']}: {attr['type']} {marker}"
                    lines.append(f"{prefix}{line}{suffix}".ljust(col_width + (len(prefix) + len(suffix) if is_highlighted else 0)))
                for ref in entity.get("references", []):
                    ref_key = f"{entity_name}.{ref['name']}"
                    is_highlighted = (i == 1 and ref_key in ref_highlights)
                    prefix = f"{CYAN}" if is_highlighted else ""
                    suffix = f"{RESET}" if is_highlighted else ""
                    line = f"    -> {ref['name']} -> {ref['target']}"
                    lines.append(f"{prefix}{line}{suffix}".ljust(col_width + (len(prefix) + len(suffix) if is_highlighted else 0)))
                for emb in entity.get("embedded", []):
                    emb_key = f"{entity_name}.{emb['name']}"
                    is_highlighted = (i == 1 and emb_key in nest_highlights)
                    prefix = f"{GREEN}{BOLD}" if is_highlighted else ""
                    suffix = f"{RESET}" if is_highlighted else ""
                    line = f"    <> {emb['name']} [{emb['cardinality']}]"
                    lines.append(f"{prefix}{line}{suffix}".ljust(col_width + (len(prefix) + len(suffix) if is_highlighted else 0)))
            else:
                lines = [f"  {YELLOW}({entity_name} --){RESET}".ljust(col_width + len(YELLOW) + len(RESET))]

            columns.append(lines)
            max_lines = max(max_lines, len(lines))

        for col_lines in columns:
            while len(col_lines) < max_lines:
                col_lines.append(" " * col_width)

        for row in range(max_lines):
            print(" | ".join(columns[j][row] for j in range(2)))
        print("-" * total_width)


def print_exported_target(result):
    """Print the exported Target Schema in native format."""
    target_type = result["target_type"]
    exported = result["exported_target"]

    print()
    print("=" * 80)
    print(f"{BOLD} EXPORTED TARGET SCHEMA ({target_type}){RESET}")
    print("=" * 80)
    print()

    if target_type == "Document":
        print(f"{CYAN}MongoDB JSON Schema:{RESET}")
    else:
        print(f"{CYAN}PostgreSQL DDL:{RESET}")
    print("-" * 80)
    print(exported)
    print("-" * 80)


def main():
    print(f"\n{BOLD}{'=' * 60}")
    print(" SMEL - Schema Migration & Evolution Language")
    print(f"{'=' * 60}{RESET}")
    print(f"\n  {CYAN}Document -> Relational:{RESET}")
    print("  [1] Person: MongoDB -> PostgreSQL (Specific)")
    print("  [2] Person: MongoDB -> PostgreSQL (Pauschalisiert)")
    print(f"\n  {CYAN}Relational -> Document:{RESET}")
    print("  [3] Person: PostgreSQL -> MongoDB (Specific)")
    print("  [4] Person: PostgreSQL -> MongoDB (Pauschalisiert)")
    print("\n  [0] Exit")

    try:
        choice = input("\nChoice: ").strip()
    except (KeyboardInterrupt, EOFError):
        return 0

    if choice == "0":
        return 0

    direction = CHOICE_MAP.get(choice)
    if not direction:
        print("Invalid choice")
        return 1

    config = MIGRATION_CONFIGS[direction]
    source_type = config["source_type"]
    target_type = config["target_type"]
    smel_file = config["smel_file"]

    # Check files exist
    for f in [config["source_file"], config["smel_file"]]:
        if not f.exists():
            print(f"{RED}[ERROR] File not found: {f}{RESET}")
            return 1

    # Run migration via core.run_migration()
    print(f"\n{CYAN}[Step 1] Reverse Engineering -> Meta V1{RESET}")
    print(f"\n{CYAN}[Step 2] Transformation: Meta V1 + {smel_file.name} -> Meta V2{RESET}")

    result = run_migration(direction)

    if result.get("error"):
        print(f"{RED}[ERROR] {result['error']}{RESET}")
        return 1

    # Print operation execution results
    operations_detail = result.get("operations_detail", [])
    print_operations(operations_detail)

    exec_stats = result.get("execution_stats", {})
    success_count = exec_stats.get("success", 0)
    skipped_count = exec_stats.get("skipped", 0)
    if skipped_count == 0:
        print(f"         {GREEN}{BOLD}All {success_count} operations executed successfully{RESET}")
    else:
        print(f"         {YELLOW}Executed: {success_count}, Skipped: {skipped_count}{RESET}")
    print(f"         Result has {result['stats']['result_count']} entities")

    print(f"\n{CYAN}[Step 3] Forward Engineering: Meta V2 -> Generated {target_type} DDL{RESET}")
    print(f"         Generated {len(result['exported_target'])} characters")

    # Display results
    print_schema_comparison(result)
    print_exported_target(result)

    # Summary
    print(f"\n{BOLD}{'=' * 50}")
    print(" SUMMARY")
    print(f"{'=' * 50}{RESET}")
    print(f"\n  Source: {result['stats']['source_count']} entities ({source_type})")
    print(f"  Result: {result['stats']['result_count']} entities after {result['operations_count']} operations")
    print(f"  Direction: {source_type} -> {target_type}")
    print(f"\n  {GREEN}{BOLD}[OK] TRANSFORMATION COMPLETE{RESET}")
    print(f"  {'=' * 30}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
