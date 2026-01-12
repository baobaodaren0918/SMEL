"""Full flow verification for Person Mini Example"""
import json
from core import run_migration

print("=" * 70)
print("PERSON MINI EXAMPLE - FULL FLOW VERIFICATION")
print("=" * 70)

# Run migration
r = run_migration("person_d2r")

# ========== 1. Source Schema Analysis ==========
print("\n[1] SOURCE SCHEMA (MongoDB JSON Schema)")
print("-" * 50)
print(f"Source Type: {r['source_type']}")
print(f"Source Entities: {list(r['source'].keys())}")

for name, entity in r['source'].items():
    print(f"\n  Entity: {name}")
    print(f"    Attributes: {[a['name'] for a in entity['attributes']]}")
    print(f"    Embedded: {[e['name'] for e in entity.get('embedded', [])]}")
    print(f"    References: {[ref['name'] for ref in entity.get('references', [])]}")

# ========== 2. Meta V1 (After Reverse Engineering) ==========
print("\n\n[2] META V1 (Unified Meta Schema after Reverse Engineering)")
print("-" * 50)
print(f"Meta V1 Entities: {list(r['meta_v1'].keys())}")

for name, entity in r['meta_v1'].items():
    print(f"\n  Entity: {name}")
    print(f"    Attributes: {[a['name'] + (' [PK]' if a.get('is_key') else '') for a in entity['attributes']]}")
    if entity.get('embedded'):
        print(f"    Embedded: {[(e['name'], e['cardinality']) for e in entity['embedded']]}")

# ========== 3. SMEL Operations ==========
print("\n\n[3] SMEL OPERATIONS")
print("-" * 50)
print(f"Total Operations: {r['operations_count']}")

for i, op in enumerate(r['operations_detail'], 1):
    print(f"\n  Step {i}: {op['type']}")
    print(f"    Params: {op['params']}")
    print(f"    Entities: {op['entity_count_before']} -> {op['entity_count_after']}")

# ========== 4. Meta V2 (After SMEL Operations) ==========
print("\n\n[4] META V2 (Unified Meta Schema after SMEL Operations)")
print("-" * 50)
print(f"Meta V2 Entities: {list(r['result'].keys())}")

for name, entity in r['result'].items():
    print(f"\n  Entity: {name}")
    attrs = []
    for a in entity['attributes']:
        suffix = ''
        if a.get('is_key'):
            suffix = ' [PK]'
        attrs.append(a['name'] + suffix)
    print(f"    Attributes: {attrs}")
    if entity.get('references'):
        print(f"    References: {[(ref['name'], '->', ref['target']) for ref in entity['references']]}")

# ========== 5. Target Schema (After Forward Engineering) ==========
print("\n\n[5] TARGET SCHEMA (PostgreSQL DDL)")
print("-" * 50)
print(f"Target Type: {r['target_type']}")
print("\nGenerated DDL:")
print(r['exported_target'])

# ========== 6. Validation ==========
print("\n[6] VALIDATION")
print("-" * 50)

# Check entity count
expected_entities = {'person', 'address', 'person_tag', 'person_knows'}
actual_entities = set(r['result'].keys())
print(f"Expected Entities: {expected_entities}")
print(f"Actual Entities: {actual_entities}")
print(f"Entity Check: {'PASS' if expected_entities == actual_entities else 'FAIL'}")

# Check person_knows has composite PK
person_knows = r['result'].get('person_knows', {})
pk_attrs = [a['name'] for a in person_knows.get('attributes', []) if a.get('is_key')]
print(f"\nperson_knows PK columns: {pk_attrs}")
print(f"Composite PK Check: {'PASS' if len(pk_attrs) == 2 else 'FAIL'}")

# Check FK references
person_knows_refs = [ref['target'] for ref in person_knows.get('references', [])]
print(f"person_knows FK targets: {person_knows_refs}")
print(f"Self-Reference Check: {'PASS' if person_knows_refs == ['person', 'person'] else 'FAIL'}")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
