"""Verify that cross-model migration outputs match reference target schemas."""
from pathlib import Path
from core import run_migration
from config import (MIGRATION_CONFIGS, SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT,
                    SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR)
from Schema.adapters.postgresql_adapter import PostgreSQLAdapter
from Schema.adapters.mongodb_adapter import MongoDBAdapter
from Schema.adapters.neo4j_adapter import Neo4jAdapter
from Schema.adapters.cassandra_adapter import CassandraAdapter

TESTS_DIR = Path('tests')


def get_reference_db(target_type):
    """Load reference schema file into a Database object."""
    if target_type == SOURCE_TYPE_RELATIONAL:
        return PostgreSQLAdapter.load_from_file(str(TESTS_DIR / 'northwind_postgresql.sql'), 'ref')
    elif target_type == SOURCE_TYPE_DOCUMENT:
        return MongoDBAdapter.load_from_file(str(TESTS_DIR / 'northwind_mongodb.json'), 'ref')
    elif target_type == SOURCE_TYPE_GRAPH:
        return Neo4jAdapter.load_from_file(str(TESTS_DIR / 'northwind_neo4j.cypher'), 'ref')
    elif target_type == SOURCE_TYPE_COLUMNAR:
        return CassandraAdapter.load_from_file(str(TESTS_DIR / 'northwind_cassandra.cql'), 'ref')


def db_entity_attrs(db):
    """Extract {entity_name: sorted [attr_names]} from Database object."""
    result = {}
    for name, entity in db.entity_types.items():
        attrs = sorted([a.attr_name for a in entity.attributes])
        result[name] = attrs
    return result


def db_reltypes(db):
    """Extract relationship types from Database object."""
    result = {}
    for name, rt in db.relationship_types.items():
        result[name] = {
            'source': rt.source_entity,
            'target': rt.target_entity,
            'attrs': sorted([a.attr_name for a in rt.attributes]) if hasattr(rt, 'attributes') else []
        }
    return result


def result_entity_attrs(meta):
    """Extract {entity_name: sorted [attr_names]} from migration result dict."""
    result = {}
    for name, entity in meta.items():
        if name.startswith('__') or not isinstance(entity, dict):
            continue
        attrs = sorted([a['name'] for a in entity.get('attributes', [])])
        result[name] = attrs
    return result


def result_reltypes(meta):
    """Extract relationship types from migration result dict."""
    rts = meta.get('__relationship_types__', {})
    result = {}
    for name, rt in rts.items():
        result[name] = {
            'source': rt.get('source_entity', ''),
            'target': rt.get('target_entity', ''),
            'attrs': sorted([a['name'] for a in rt.get('attributes', [])])
        }
    return result


# Cache reference databases
ref_cache = {}
for tt in [SOURCE_TYPE_RELATIONAL, SOURCE_TYPE_DOCUMENT, SOURCE_TYPE_GRAPH, SOURCE_TYPE_COLUMNAR]:
    ref_cache[tt] = get_reference_db(tt)

# Cross-model migrations (specific grammar only)
specific_keys = sorted([
    k for k, v in MIGRATION_CONFIGS.items()
    if k.startswith('northwind_') and v['source_type'] != v['target_type'] and k.endswith('_specific')
])

issues = []
ok_count = 0

for cfg_key in specific_keys:
    cfg = MIGRATION_CONFIGS[cfg_key]
    target_type = cfg['target_type']

    result = run_migration(cfg_key)
    result_meta = result.get('result', {})
    ref_db = ref_cache[target_type]

    # Get entity attrs from both
    res_attrs = result_entity_attrs(result_meta)
    ref_attrs = db_entity_attrs(ref_db)

    entry_issues = []

    # For Document targets, compare by short name (last path segment)
    # because NEST creates entities with short names while MongoDB adapter
    # uses dotted-path names (e.g., "customer" vs "orders.customer")
    if target_type == SOURCE_TYPE_DOCUMENT:
        # Normalize reference: dotted path -> short name, merge duplicates
        ref_normalized = {}
        for name, attrs in ref_attrs.items():
            short = name.rsplit('.', 1)[-1]
            ref_normalized.setdefault(short, set()).update(attrs)
        res_normalized = {}
        for name, attrs in res_attrs.items():
            short = name.rsplit('.', 1)[-1]
            res_normalized.setdefault(short, set()).update(attrs)

        missing_ents = set(ref_normalized.keys()) - set(res_normalized.keys())
        extra_ents = set(res_normalized.keys()) - set(ref_normalized.keys())
        if missing_ents:
            entry_issues.append(f'  missing entities: {missing_ents}')
        if extra_ents:
            entry_issues.append(f'  extra entities: {extra_ents}')
        for ename in sorted(set(ref_normalized.keys()) & set(res_normalized.keys())):
            m = ref_normalized[ename] - res_normalized[ename]
            x = res_normalized[ename] - ref_normalized[ename]
            if m or x:
                parts = []
                if m:
                    parts.append(f'missing={m}')
                if x:
                    parts.append(f'extra={x}')
                entry_issues.append(f'  {ename}: {" | ".join(parts)}')
    else:
        res_entities = set(res_attrs.keys())
        ref_entities = set(ref_attrs.keys())

        missing_ents = ref_entities - res_entities
        extra_ents = res_entities - ref_entities

        if missing_ents:
            entry_issues.append(f'  missing entities: {missing_ents}')
        if extra_ents:
            entry_issues.append(f'  extra entities: {extra_ents}')

        # Compare attributes per shared entity
        for ename in sorted(ref_entities & res_entities):
            r_attrs = set(res_attrs.get(ename, []))
            e_attrs = set(ref_attrs.get(ename, []))
            m = e_attrs - r_attrs
            x = r_attrs - e_attrs
            if m or x:
                parts = []
                if m:
                    parts.append(f'missing={m}')
                if x:
                    parts.append(f'extra={x}')
                entry_issues.append(f'  {ename}: {" | ".join(parts)}')

    # Compare relationship types (for graph targets)
    if target_type == SOURCE_TYPE_GRAPH:
        res_rts = result_reltypes(result_meta)
        ref_rts = db_reltypes(ref_db)
        missing_rts = set(ref_rts.keys()) - set(res_rts.keys())
        extra_rts = set(res_rts.keys()) - set(ref_rts.keys())
        if missing_rts:
            entry_issues.append(f'  missing reltypes: {missing_rts}')
        if extra_rts:
            entry_issues.append(f'  extra reltypes: {extra_rts}')
        for rt_name in sorted(set(ref_rts.keys()) & set(res_rts.keys())):
            ref_rt = ref_rts[rt_name]
            res_rt = res_rts[rt_name]
            if ref_rt['source'] != res_rt['source'] or ref_rt['target'] != res_rt['target']:
                entry_issues.append(
                    f'  {rt_name}: direction mismatch '
                    f'ref={ref_rt["source"]}->{ref_rt["target"]} '
                    f'got={res_rt["source"]}->{res_rt["target"]}'
                )
            if ref_rt['attrs'] != res_rt['attrs']:
                entry_issues.append(
                    f'  {rt_name}: attrs mismatch ref={ref_rt["attrs"]} got={res_rt["attrs"]}'
                )

    if entry_issues:
        issues.append(f'{cfg_key}:')
        issues.extend(entry_issues)
    else:
        ok_count += 1
        ent_count = len(ref_attrs)
        rt_count = len(db_reltypes(ref_db)) if target_type == SOURCE_TYPE_GRAPH else 0
        extra = f', {rt_count} reltypes' if rt_count else ''
        print(f'OK  {cfg_key} ({ent_count} entities{extra})')

print()
if issues:
    print('=== ISSUES FOUND ===')
    for i in issues:
        print(i)
    issue_count = len([i for i in issues if not i.startswith('  ')])
    print(f'\n{ok_count} OK, {issue_count} with issues out of {len(specific_keys)}')
else:
    print(f'All {len(specific_keys)} cross-model migrations match reference schemas!')
