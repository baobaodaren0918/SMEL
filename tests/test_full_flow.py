"""Full flow verification for Person Mini Example - Tests both grammar variants"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core import run_migration


def run_test(direction: str):
    """Run a single migration test and print results."""
    print(f"\n{'=' * 70}")
    print(f"TESTING: {direction}")
    print("=" * 70)

    r = run_migration(direction)

    if "error" in r:
        print(f"[ERROR] {r['error']}")
        return False

    # Helper to filter out __relationship_types__ and other special keys
    def filter_entities(d):
        return {k: v for k, v in d.items() if not k.startswith('__')}

    # ========== 1. Source Schema Analysis ==========
    print("\n[1] SOURCE SCHEMA")
    print("-" * 50)
    print(f"Source Type: {r['source_type']}")
    source_filtered = filter_entities(r['source'])
    print(f"Source Entities: {list(source_filtered.keys())}")

    for name, entity in source_filtered.items():
        print(f"\n  Entity: {name}")
        print(f"    Attributes: {[a['name'] for a in entity['attributes']]}")
        print(f"    Embedded: {[e['name'] for e in entity.get('embedded', [])]}")
        print(f"    References: {[ref['name'] for ref in entity.get('references', [])]}")

    # ========== 2. Meta V1 (After Reverse Engineering) ==========
    print("\n\n[2] META V1 (Unified Meta Schema after Reverse Engineering)")
    print("-" * 50)
    meta_v1_filtered = filter_entities(r['meta_v1'])
    print(f"Meta V1 Entities: {list(meta_v1_filtered.keys())}")

    for name, entity in meta_v1_filtered.items():
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
    result_filtered = filter_entities(r['result'])
    print(f"Meta V2 Entities: {list(result_filtered.keys())}")

    for name, entity in result_filtered.items():
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
    print("\n\n[5] TARGET SCHEMA")
    print("-" * 50)
    print(f"Target Type: {r['target_type']}")
    print("\nGenerated DDL/JSON:")
    print(r['exported_target'])

    # ========== 6. Validation ==========
    print("\n[6] VALIDATION")
    print("-" * 50)

    # Check execution stats
    stats = r.get('execution_stats', {})
    print(f"Operations: {stats.get('total', 0)} total, {stats.get('success', 0)} success, {stats.get('skipped', 0)} skipped")

    source_type = r['source_type']
    target_type = r['target_type']

    if source_type == 'Document' and target_type == 'Relational':
        # D2R: Check expected relational tables
        expected_entities = {'person', 'address', 'employment', 'company', 'company_address', 'person_tag', 'person_knows'}
        actual_entities = set(k for k in r['result'].keys() if not k.startswith('__'))
        print(f"Expected Entities: {expected_entities}")
        print(f"Actual Entities: {actual_entities}")
        entity_pass = expected_entities == actual_entities
        print(f"Entity Check: {'PASS' if entity_pass else 'FAIL'}")

        # Check person_knows has composite PK
        person_knows = r['result'].get('person_knows', {})
        pk_attrs = [a['name'] for a in person_knows.get('attributes', []) if a.get('is_key')]
        print(f"\nperson_knows PK columns: {pk_attrs}")
        pk_pass = len(pk_attrs) == 2
        print(f"Composite PK Check: {'PASS' if pk_pass else 'FAIL'}")

        # Check FK references
        person_knows_refs = [ref['target'] for ref in person_knows.get('references', [])]
        print(f"person_knows FK targets: {person_knows_refs}")
        ref_pass = person_knows_refs == ['person', 'person']
        print(f"Self-Reference Check: {'PASS' if ref_pass else 'FAIL'}")

        return entity_pass and pk_pass and ref_pass

    elif source_type == 'Relational' and target_type == 'Document':
        # R2D: Check expected document structure
        actual_entities = set(k for k in r['result'].keys() if not k.startswith('__'))
        print(f"Result Entities: {actual_entities}")
        person = r['result'].get('person', {})
        has_embedded = len(person.get('embedded', [])) > 0
        print(f"Person has embedded: {'PASS' if has_embedded else 'FAIL'}")
        if has_embedded:
            emb_names = [e['name'] for e in person['embedded']]
            print(f"  Embedded: {emb_names}")
        return has_embedded

    elif source_type == 'Relational' and target_type == 'Relational':
        # R2R: Check expected evolved relational tables
        expected_entities = {'person', 'person_detail', 'address', 'employment', 'company', 'tag', 'person_knows'}
        actual_entities = set(k for k in r['result'].keys() if not k.startswith('__'))
        print(f"Expected Entities: {expected_entities}")
        print(f"Actual Entities: {actual_entities}")
        entity_pass = expected_entities == actual_entities
        print(f"Entity Check: {'PASS' if entity_pass else 'FAIL'}")

        # Check person_detail exists with expected attributes
        person_detail = r['result'].get('person_detail', {})
        detail_attrs = [a['name'] for a in person_detail.get('attributes', [])]
        print(f"person_detail attributes: {detail_attrs}")
        detail_pass = 'age' in detail_attrs and 'email' in detail_attrs
        print(f"person_detail Check: {'PASS' if detail_pass else 'FAIL'}")

        # Check company has merged address fields
        company = r['result'].get('company', {})
        company_attrs = [a['name'] for a in company.get('attributes', [])]
        print(f"company attributes: {company_attrs}")
        merge_pass = 'street' in company_attrs and 'city' in company_attrs
        print(f"Company Merge Check: {'PASS' if merge_pass else 'FAIL'}")

        return entity_pass and detail_pass and merge_pass

    elif source_type == 'Document' and target_type == 'Document':
        # D2D: Check expected evolved document structure
        actual_entities = set(k for k in r['result'].keys() if not k.startswith('__'))
        print(f"Result Entities: {actual_entities}")

        # Check person entity has new attributes
        person = r['result'].get('person', {})
        person_attrs = [a['name'] for a in person.get('attributes', [])]
        print(f"person attributes: {person_attrs}")
        has_email = 'email' in person_attrs
        print(f"Person has email: {'PASS' if has_email else 'FAIL'}")

        # Check company.address was flattened (no more 3-level nesting)
        # After FLATTEN, company should have street and city directly
        company_key = None
        for key in actual_entities:
            if 'company' in key and 'address' not in key:
                company_key = key
                break
        if company_key:
            company = r['result'].get(company_key, {})
            company_attrs = [a['name'] for a in company.get('attributes', [])]
            print(f"company attributes: {company_attrs}")
            flatten_pass = 'street' in company_attrs and 'city' in company_attrs
            print(f"Flatten Check: {'PASS' if flatten_pass else 'FAIL'}")
        else:
            flatten_pass = False
            print(f"Flatten Check: FAIL (company entity not found)")

        return has_email and flatten_pass

    elif source_type == 'Graph' and target_type == 'Graph':
        # G2G: Check expected evolved graph nodes (20 nodes V1 -> 17 nodes V2)
        # Structural changes: MERGE City+Country→Location, TRANSFORM Award→rel, DELETE Address
        actual_entities = set(e for e in r['result'].keys() if not e.startswith('__'))
        print(f"Result Entities: {actual_entities}")

        # Check Person node has expected attributes
        person = r['result'].get('Person', {})
        person_attrs = [a['name'] for a in person.get('attributes', [])]
        print(f"Person attributes: {person_attrs}")
        has_email = 'email' in person_attrs
        has_first_name = 'first_name' in person_attrs
        has_phone = 'phone' in person_attrs
        has_bio = 'bio' in person_attrs
        print(f"Person has email: {'PASS' if has_email else 'FAIL'}")
        print(f"Person has first_name: {'PASS' if has_first_name else 'FAIL'}")
        print(f"Person has phone: {'PASS' if has_phone else 'FAIL'}")
        print(f"Person has bio: {'PASS' if has_bio else 'FAIL'}")

        # Check Company was renamed to Organization
        has_org = 'Organization' in actual_entities
        no_company = 'Company' not in actual_entities
        print(f"Organization exists: {'PASS' if has_org else 'FAIL'}")
        print(f"Company removed: {'PASS' if no_company else 'FAIL'}")

        # Check MERGE: City + Country → Location
        has_location = 'Location' in actual_entities
        no_city = 'City' not in actual_entities
        no_country = 'Country' not in actual_entities
        print(f"Location exists (MERGE): {'PASS' if has_location else 'FAIL'}")
        print(f"City removed (MERGE): {'PASS' if no_city else 'FAIL'}")
        print(f"Country removed (MERGE): {'PASS' if no_country else 'FAIL'}")
        # Verify Location has merged attributes
        location = r['result'].get('Location', {})
        loc_attrs = [a['name'] for a in location.get('attributes', [])]
        has_city_name = 'city_name' in loc_attrs
        has_continent = 'continent' in loc_attrs
        print(f"Location has city_name: {'PASS' if has_city_name else 'FAIL'}")
        print(f"Location has continent: {'PASS' if has_continent else 'FAIL'}")

        # Check TRANSFORM: Award → relationship (node removed)
        no_award = 'Award' not in actual_entities
        print(f"Award removed (TRANSFORM): {'PASS' if no_award else 'FAIL'}")

        # Check Address was deleted
        no_address = 'Address' not in actual_entities
        print(f"Address removed (DELETE): {'PASS' if no_address else 'FAIL'}")

        # Check renames
        has_cert = 'Certification' in actual_entities
        has_paper = 'Paper' in actual_entities
        print(f"Certification exists: {'PASS' if has_cert else 'FAIL'}")
        print(f"Paper exists: {'PASS' if has_paper else 'FAIL'}")

        # Check entity count (17 nodes: 20 - 2 merge + 1 Location - 1 Award - 1 Address)
        entity_count_pass = len(actual_entities) == 17
        print(f"Entity count (expect 17): {len(actual_entities)} {'PASS' if entity_count_pass else 'FAIL'}")

        return (has_email and has_first_name and has_phone and has_bio
                and has_org and no_company and has_location and no_city and no_country
                and has_city_name and has_continent and no_award and no_address
                and has_cert and has_paper and entity_count_pass)

    elif source_type == 'Columnar' and target_type == 'Columnar':
        # C2C: Check expected evolved columnar tables
        actual_entities = set(e for e in r['result'].keys() if not e.startswith('__'))
        print(f"Result Entities: {actual_entities}")

        # Check person table has renamed fields
        person = r['result'].get('person', {})
        person_attrs = [a['name'] for a in person.get('attributes', [])]
        print(f"person attributes: {person_attrs}")
        has_first_name = 'first_name' in person_attrs
        has_email = 'email' in person_attrs
        print(f"person has first_name: {'PASS' if has_first_name else 'FAIL'}")
        print(f"person has email: {'PASS' if has_email else 'FAIL'}")

        # Check person_activity was renamed to activity_log
        has_activity_log = 'activity_log' in actual_entities
        no_person_activity = 'person_activity' not in actual_entities
        print(f"activity_log exists: {'PASS' if has_activity_log else 'FAIL'}")
        print(f"person_activity removed: {'PASS' if no_person_activity else 'FAIL'}")

        return has_first_name and has_email and has_activity_log and no_person_activity

    else:
        print(f"Unknown direction: {source_type} -> {target_type}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("SMEL FULL FLOW VERIFICATION (Person)")
    print("=" * 70)

    results = {}

    # ---- Person Tests (8) ----
    print("\n" + "=" * 70)
    print("PERSON MINI EXAMPLE (8 tests)")
    print("=" * 70)
    for direction in ["person_d2r_specific", "person_d2r_pauschalisiert",
                       "person_r2d_specific", "person_r2d_pauschalisiert",
                       "person_r2r_specific", "person_r2r_pauschalisiert",
                       "person_d2d_specific", "person_d2d_pauschalisiert"]:
        results[direction] = run_test(direction)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_pass = True
    passed_count = 0
    for direction, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {direction}")
        if not passed:
            all_pass = False
        else:
            passed_count += 1

    print("=" * 70)
    print(f"  Person: {passed_count}/12 passed")
    print("=" * 70)
    print(f"OVERALL: {'ALL 12 PASSED' if all_pass else 'SOME FAILED'}")
    print("=" * 70)
