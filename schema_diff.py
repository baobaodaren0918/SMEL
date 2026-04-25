"""
Schema-diff engine: compare a source Database against a target Database
and produce an ordered list of SMILE operation records.

The output is paradigm-agnostic — it does NOT format the result as a
script. Use script_renderer.py to render the records into Specific
(.smile) or Generalized (.smile_gen) syntax.

Cross-paradigm structural ops (NEST / UNNEST / FLATTEN / UNFLATTEN /
UNWIND / WIND / TRANSFORM) cannot be inferred reliably from two schemas
alone. Pass them in via `mapping_hints`; they are emitted verbatim and
the affected fields are then suppressed from the auto-diff so we do
not double-emit ADD/DELETE for the same data.

Public API:

    diff_schemas(
        source_db, target_db,
        mapping_hints: dict | None = None,
        rename_threshold: float = 0.7,
    ) -> list[OpRecord]

OpRecord shape:

    {
        "op":     "ADD_PROPERTY",   # operation key from grammar/smile_operations.json
        "params": {...},            # operation-specific kwargs (see _format below)
        "comment": str | None,      # optional inline comment
    }
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set

from Schema.unified_meta_schema import (
    Database, EntityType, EntityKind, Property,
    UniqueConstraint, ForeignKeyConstraint, PKTypeEnum,
    Reference, Embedded, Edge, Cardinality,
)


# ============================================================================
# OPERATION RECORD
# ============================================================================

@dataclass
class OpRecord:
    op: str
    params: Dict[str, Any] = field(default_factory=dict)
    comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"op": self.op, "params": dict(self.params)}
        if self.comment:
            d["comment"] = self.comment
        return d


# ============================================================================
# SIMILARITY HELPERS
# ============================================================================

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _name_similarity(a: str, b: str) -> float:
    """0.0 .. 1.0 normalized name similarity (case-insensitive)."""
    a, b = a.lower(), b.lower()
    if not a or not b:
        return 0.0
    dist = _levenshtein(a, b)
    return 1.0 - (dist / max(len(a), len(b)))


def _property_set_similarity(a: List[Property], b: List[Property]) -> float:
    """Jaccard similarity over property names."""
    sa = {p.attr_name.lower() for p in a}
    sb = {p.attr_name.lower() for p in b}
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _entity_similarity(src: EntityType, tgt: EntityType) -> float:
    """Combined entity similarity: name + property overlap."""
    name_sim = _name_similarity(src.name, tgt.name)
    prop_sim = _property_set_similarity(src.properties, tgt.properties)
    return 0.6 * name_sim + 0.4 * prop_sim


# ============================================================================
# RENAME MATCHING
# ============================================================================

def _match_renames(
    source_only: List[str],
    target_only: List[str],
    src_db: Database,
    tgt_db: Database,
    threshold: float,
) -> List[Tuple[str, str]]:
    """Greedy best-match pairing: returns [(src_name, tgt_name), ...]."""
    pairs: List[Tuple[str, str, float]] = []
    for s in source_only:
        for t in target_only:
            sim = _entity_similarity(src_db.entity_types[s], tgt_db.entity_types[t])
            if sim >= threshold:
                pairs.append((s, t, sim))
    pairs.sort(key=lambda x: x[2], reverse=True)
    used_src: Set[str] = set()
    used_tgt: Set[str] = set()
    matched: List[Tuple[str, str]] = []
    for s, t, _sim in pairs:
        if s in used_src or t in used_tgt:
            continue
        used_src.add(s)
        used_tgt.add(t)
        matched.append((s, t))
    return matched


def _match_property_renames(
    src_props: List[Property],
    tgt_props: List[Property],
    threshold: float,
) -> List[Tuple[str, str]]:
    """Match deleted source props to added target props by name similarity."""
    pairs: List[Tuple[str, str, float]] = []
    for s in src_props:
        for t in tgt_props:
            sim = _name_similarity(s.attr_name, t.attr_name)
            if sim >= threshold:
                pairs.append((s.attr_name, t.attr_name, sim))
    pairs.sort(key=lambda x: x[2], reverse=True)
    used_src: Set[str] = set()
    used_tgt: Set[str] = set()
    matched: List[Tuple[str, str]] = []
    for s, t, _sim in pairs:
        if s in used_src or t in used_tgt:
            continue
        used_src.add(s)
        used_tgt.add(t)
        matched.append((s, t))
    return matched


# ============================================================================
# DATA TYPE -> SMILE TYPE STRING
# ============================================================================

_PRIM_TO_SMILE = {
    "string": "String", "text": "Text", "integer": "Integer",
    "long": "Long", "double": "Double", "float": "Float",
    "decimal": "Decimal", "boolean": "Boolean", "date": "Date",
    "timestamp": "Timestamp", "uuid": "UUID", "binary": "Binary",
    "objectId": "String", "int32": "Integer", "int64": "Long",
    "decimal128": "Decimal",
}


def _data_type_to_smile(dt: Any) -> str:
    """Best-effort mapping from a meta-schema DataType into a SMILE type token."""
    d = dt.to_dict() if hasattr(dt, "to_dict") else dict(dt or {})
    kind = d.get("kind", "primitive")
    if kind == "primitive":
        return _PRIM_TO_SMILE.get(d.get("type", "string"), "String")
    return "String"  # collections / nested types fall back to String for now


# ============================================================================
# CARDINALITY -> SMILE TOKEN
# ============================================================================

_CARD_TO_SMILE = {
    Cardinality.ONE_TO_ONE: "ONE_TO_ONE",
    Cardinality.ONE_TO_MANY: "ONE_TO_MANY",
    Cardinality.ZERO_TO_ONE: "ZERO_TO_ONE",
    Cardinality.ZERO_TO_MANY: "ZERO_TO_MANY",
}


def _card_to_smile(c: Optional[Cardinality]) -> Optional[str]:
    return _CARD_TO_SMILE.get(c) if c else None


# ============================================================================
# DB TYPE -> SMILE TOKEN
# ============================================================================

_DBTYPE_TO_SMILE = {
    "relational": "RELATIONAL",
    "document": "DOCUMENT",
    "graph": "GRAPH",
    "columnar": "COLUMNAR",
}


def _dbtype_to_smile(t: Any) -> str:
    if hasattr(t, "value"):
        t = t.value
    return _DBTYPE_TO_SMILE.get(str(t).lower(), str(t).upper())


def _entity_kind_to_db_token(kind: EntityKind) -> str:
    """Map EntityKind to the DB type token used by CAST_ENTITY."""
    if kind in (EntityKind.DOCUMENT, EntityKind.EMBEDDED):
        return "DOCUMENT"
    if kind in (EntityKind.VERTEX, EntityKind.EDGE):
        return "GRAPH"
    if kind == EntityKind.WIDE_COLUMN_TABLE:
        return "COLUMNAR"
    return "RELATIONAL"


# ============================================================================
# CONSTRAINT EXTRACTION
# ============================================================================

@dataclass
class _KeyInfo:
    """A flattened view of a key constraint for diffing."""
    pk_type: str            # "primary" | "unique" | "partition" | "clustering"
    columns: List[str]      # property names

    def signature(self) -> Tuple[str, Tuple[str, ...]]:
        return (self.pk_type, tuple(self.columns))


def _extract_keys(entity: EntityType) -> List[_KeyInfo]:
    keys: List[_KeyInfo] = []
    for c in entity.constraints:
        if not c.kind == "unique":
            continue
        column_names: List[str] = []
        pk_subtype: Optional[str] = None
        for up in c.unique_properties:
            prop = entity.get_property_by_id(up.property_id)
            if prop:
                column_names.append(prop.attr_name)
            if pk_subtype is None:
                if up.primary_key_type == PKTypeEnum.PARTITION:
                    pk_subtype = "partition"
                elif up.primary_key_type == PKTypeEnum.CLUSTERING:
                    pk_subtype = "clustering"
        if pk_subtype is None:
            pk_subtype = "primary" if c.is_primary_key else "unique"
        if column_names:
            keys.append(_KeyInfo(pk_type=pk_subtype, columns=column_names))
    return keys


@dataclass
class _FKInfo:
    fk_column: str
    target_entity: str
    target_column: str

    def signature(self) -> Tuple[str, str, str]:
        return (self.fk_column, self.target_entity, self.target_column)


def _extract_foreign_keys(entity: EntityType, db: Database) -> List[_FKInfo]:
    fks: List[_FKInfo] = []
    for c in entity.constraints:
        if not c.kind == "foreign_key":
            continue
        for fkp in c.foreign_key_properties:
            fk_prop = entity.get_property_by_id(fkp.property_id)
            target_entity_name = ""
            target_column_name = ""
            for tgt_e in db.entity_types.values():
                up = next(
                    (u for cc in tgt_e.constraints
                     if cc.kind == "unique"
                     for u in cc.unique_properties
                     if u.meta_id == fkp.points_to_unique_property_id),
                    None,
                )
                if up:
                    target_entity_name = tgt_e.name
                    tp = tgt_e.get_property_by_id(up.property_id)
                    if tp:
                        target_column_name = tp.attr_name
                    break
            if fk_prop and target_entity_name and target_column_name:
                fks.append(_FKInfo(
                    fk_column=fk_prop.attr_name,
                    target_entity=target_entity_name,
                    target_column=target_column_name,
                ))
    # Also pull from References (relationships) that are not declared as FK constraints
    for rel in entity.relationships:
        if rel.kind == "reference" and rel.refs_to:
            sig_col = rel.ref_name or f"{rel.refs_to}_id"
            target_pk_col = ""
            tgt = db.get_entity_type(rel.refs_to)
            if tgt:
                pk = tgt.get_primary_key()
                if pk and pk.unique_properties:
                    pp = tgt.get_property_by_id(pk.unique_properties[0].property_id)
                    if pp:
                        target_pk_col = pp.attr_name
            target_pk_col = target_pk_col or "id"
            sig = (sig_col, rel.refs_to, target_pk_col)
            if sig not in {f.signature() for f in fks}:
                fks.append(_FKInfo(
                    fk_column=sig_col,
                    target_entity=rel.refs_to,
                    target_column=target_pk_col,
                ))
    return fks


# ============================================================================
# MAIN DIFF
# ============================================================================

def diff_schemas(
    source_db: Database,
    target_db: Database,
    mapping_hints: Optional[Dict[str, Any]] = None,
    rename_threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """Return an ordered list of OpRecord dicts."""
    hints = mapping_hints or {}
    structural_hints = list(hints.get("structural", []))

    # Track which (entity, property) pairs are consumed by structural hints —
    # so we don't double-emit ADD/DELETE for the same data.
    suppressed_src_props: Set[Tuple[str, str]] = set()
    suppressed_tgt_props: Set[Tuple[str, str]] = set()
    suppressed_src_entities: Set[str] = set()
    suppressed_tgt_entities: Set[str] = set()

    structural_records: List[OpRecord] = []
    for h in structural_hints:
        rec = _hint_to_record(h, suppressed_src_props, suppressed_tgt_props,
                              suppressed_src_entities, suppressed_tgt_entities)
        if rec:
            structural_records.append(rec)

    # ---- Entity-level diff ----
    src_names = set(source_db.entity_types.keys()) - suppressed_src_entities
    tgt_names = set(target_db.entity_types.keys()) - suppressed_tgt_entities
    common = src_names & tgt_names

    source_only = sorted(src_names - tgt_names)
    target_only = sorted(tgt_names - src_names)

    rename_pairs = _match_renames(source_only, target_only,
                                  source_db, target_db, rename_threshold)
    renamed_src = {s for s, _ in rename_pairs}
    renamed_tgt = {t for _, t in rename_pairs}

    rename_records: List[OpRecord] = []
    for s, t in rename_pairs:
        rename_records.append(OpRecord(
            op="RENAME_ENTITY",
            params={"old_name": s, "new_name": t},
            comment="TODO: auto-detected by name+structure similarity, confirm intended",
        ))

    add_entity_records: List[OpRecord] = []
    for t in target_only:
        if t in renamed_tgt:
            continue
        ent = target_db.entity_types[t]
        add_entity_records.append(OpRecord(
            op="ADD_ENTITY",
            params={
                "name": ent.name,
                "properties": [
                    (p.attr_name, _data_type_to_smile(p.data_type))
                    for p in ent.properties
                ],
                "edge_endpoints": _edge_endpoints(ent),
                "edge_cardinality": _card_to_smile(ent.edge_cardinality),
            },
        ))

    delete_entity_records: List[OpRecord] = []
    for s in source_only:
        if s in renamed_src:
            continue
        delete_entity_records.append(OpRecord(
            op="DELETE_ENTITY",
            params={"name": s},
        ))

    # ---- Per-entity diff (matched + renamed) ----
    add_prop_records: List[OpRecord] = []
    delete_prop_records: List[OpRecord] = []
    rename_prop_records: List[OpRecord] = []
    cast_prop_records: List[OpRecord] = []
    add_pk_records: List[OpRecord] = []
    add_uk_records: List[OpRecord] = []
    add_partkey_records: List[OpRecord] = []
    add_clustkey_records: List[OpRecord] = []
    add_fk_records: List[OpRecord] = []
    add_embedded_records: List[OpRecord] = []
    add_label_records: List[OpRecord] = []
    delete_pk_records: List[OpRecord] = []
    delete_uk_records: List[OpRecord] = []
    delete_partkey_records: List[OpRecord] = []
    delete_clustkey_records: List[OpRecord] = []
    delete_fk_records: List[OpRecord] = []
    delete_embedded_records: List[OpRecord] = []
    delete_label_records: List[OpRecord] = []
    recard_records: List[OpRecord] = []
    cast_entity_records: List[OpRecord] = []

    pairs_to_diff: List[Tuple[str, str]] = [(n, n) for n in sorted(common)] + list(rename_pairs)

    for src_name, tgt_name in pairs_to_diff:
        s_ent = source_db.entity_types[src_name]
        t_ent = target_db.entity_types[tgt_name]
        # Use the target name in emitted operations (assume rename has already happened upstream)
        eff_name = tgt_name

        # entity_kind
        if s_ent.entity_kind != t_ent.entity_kind:
            new_kind_token = _entity_kind_to_db_token(t_ent.entity_kind)
            cast_entity_records.append(OpRecord(
                op="CAST_ENTITY",
                params={"entity": eff_name, "database_type": new_kind_token},
                comment="TODO: cross-paradigm change — verify entity_kind transition is correct",
            ))

        # properties
        s_props = {p.attr_name: p for p in s_ent.properties
                   if (src_name, p.attr_name) not in suppressed_src_props}
        t_props = {p.attr_name: p for p in t_ent.properties
                   if (tgt_name, p.attr_name) not in suppressed_tgt_props}

        s_only_names = sorted(set(s_props) - set(t_props))
        t_only_names = sorted(set(t_props) - set(s_props))

        prop_renames = _match_property_renames(
            [s_props[n] for n in s_only_names],
            [t_props[n] for n in t_only_names],
            rename_threshold,
        )
        renamed_sp = {a for a, _ in prop_renames}
        renamed_tp = {b for _, b in prop_renames}

        for old, new in prop_renames:
            rename_prop_records.append(OpRecord(
                op="RENAME_PROPERTY",
                params={"old_name": old, "new_name": new, "entity": eff_name},
                comment="TODO: auto-detected by name similarity, confirm intended",
            ))

        for n in t_only_names:
            if n in renamed_tp:
                continue
            p = t_props[n]
            add_prop_records.append(OpRecord(
                op="ADD_PROPERTY",
                params={
                    "name": p.attr_name,
                    "entity": eff_name,
                    "data_type": _data_type_to_smile(p.data_type),
                    "not_null": (not p.is_optional),
                },
            ))

        for n in s_only_names:
            if n in renamed_sp:
                continue
            delete_prop_records.append(OpRecord(
                op="DELETE_PROPERTY",
                params={"entity": eff_name, "field": n},
            ))

        # type changes on shared properties
        shared = set(s_props) & set(t_props)
        for n in sorted(shared):
            sp, tp = s_props[n], t_props[n]
            s_smile = _data_type_to_smile(sp.data_type)
            t_smile = _data_type_to_smile(tp.data_type)
            if s_smile != t_smile:
                cast_prop_records.append(OpRecord(
                    op="CAST_PROPERTY",
                    params={"entity": eff_name, "field": n, "data_type": t_smile},
                ))

        # constraint diff
        s_keys = {k.signature(): k for k in _extract_keys(s_ent)}
        t_keys = {k.signature(): k for k in _extract_keys(t_ent)}
        for sig, k in t_keys.items():
            if sig in s_keys:
                continue
            rec = _key_record(eff_name, k, action="add")
            if rec.op == "ADD_PRIMARY_KEY":
                add_pk_records.append(rec)
            elif rec.op == "ADD_UNIQUE_KEY":
                add_uk_records.append(rec)
            elif rec.op == "ADD_PARTITION_KEY":
                add_partkey_records.append(rec)
            elif rec.op == "ADD_CLUSTERING_KEY":
                add_clustkey_records.append(rec)
        for sig, k in s_keys.items():
            if sig in t_keys:
                continue
            rec = _key_record(eff_name, k, action="delete")
            if rec.op == "DELETE_PRIMARY_KEY":
                delete_pk_records.append(rec)
            elif rec.op == "DELETE_UNIQUE_KEY":
                delete_uk_records.append(rec)
            elif rec.op == "DELETE_PARTITION_KEY":
                delete_partkey_records.append(rec)
            elif rec.op == "DELETE_CLUSTERING_KEY":
                delete_clustkey_records.append(rec)

        # FK diff
        s_fks = {fk.signature(): fk for fk in _extract_foreign_keys(s_ent, source_db)}
        t_fks = {fk.signature(): fk for fk in _extract_foreign_keys(t_ent, target_db)}
        for sig, fk in t_fks.items():
            if sig in s_fks:
                continue
            add_fk_records.append(OpRecord(
                op="ADD_FOREIGN_KEY",
                params={
                    "entity": eff_name,
                    "field": fk.fk_column,
                    "target_entity": fk.target_entity,
                    "target_field": fk.target_column,
                },
            ))
        for sig, fk in s_fks.items():
            if sig in t_fks:
                continue
            delete_fk_records.append(OpRecord(
                op="DELETE_FOREIGN_KEY",
                params={"entity": eff_name, "field": fk.fk_column},
            ))

        # embedded relationships
        s_embed = {e.aggr_name: e for e in s_ent.relationships if e.kind == "embedded"}
        t_embed = {e.aggr_name: e for e in t_ent.relationships if e.kind == "embedded"}
        for n, e in t_embed.items():
            if n in s_embed:
                if s_embed[n].cardinality != e.cardinality:
                    new_card = _card_to_smile(e.cardinality)
                    if new_card:
                        recard_records.append(OpRecord(
                            op="RECARD",
                            params={"entity": eff_name, "field": n, "cardinality": new_card},
                        ))
                continue
            add_embedded_records.append(OpRecord(
                op="ADD_EMBEDDED",
                params={
                    "name": n,
                    "entity": eff_name,
                    "cardinality": _card_to_smile(e.cardinality),
                },
                comment="TODO: cross-model embedded structure — review NEST/UNNEST/FLATTEN if data needs migration",
            ))
        for n in s_embed:
            if n in t_embed:
                continue
            delete_embedded_records.append(OpRecord(
                op="DELETE_EMBEDDED",
                params={"entity": eff_name, "field": n},
            ))

        # graph labels (Neo4j: extra labels beyond entity name)
        s_labels = set(s_ent.labels)
        t_labels = set(t_ent.labels)
        for lbl in sorted(t_labels - s_labels):
            add_label_records.append(OpRecord(
                op="ADD_LABEL",
                params={"label": lbl, "entity": eff_name},
            ))
        for lbl in sorted(s_labels - t_labels):
            delete_label_records.append(OpRecord(
                op="DELETE_LABEL",
                params={"label": lbl, "entity": eff_name},
            ))

        # cardinality changes on References
        s_refs = {r.ref_name: r for r in s_ent.relationships if r.kind == "reference"}
        t_refs = {r.ref_name: r for r in t_ent.relationships if r.kind == "reference"}
        for n, r in t_refs.items():
            if n in s_refs and s_refs[n].cardinality != r.cardinality:
                new_card = _card_to_smile(r.cardinality)
                if new_card:
                    recard_records.append(OpRecord(
                        op="RECARD",
                        params={"entity": eff_name, "field": n, "cardinality": new_card},
                    ))

    # Final ordering: structural hints first (they shape entities), then
    # creates/renames, then constraints, then cardinality + cast, then deletes.
    ordered = (
        structural_records
        + rename_records
        + add_entity_records
        + rename_prop_records
        + add_prop_records
        + cast_prop_records
        + add_pk_records
        + add_uk_records
        + add_partkey_records
        + add_clustkey_records
        + add_fk_records
        + add_embedded_records
        + add_label_records
        + recard_records
        + cast_entity_records
        + delete_fk_records
        + delete_embedded_records
        + delete_label_records
        + delete_pk_records
        + delete_uk_records
        + delete_partkey_records
        + delete_clustkey_records
        + delete_prop_records
        + delete_entity_records
    )
    return [r.to_dict() for r in ordered]


# ============================================================================
# HELPERS
# ============================================================================

def _edge_endpoints(ent: EntityType) -> Optional[Dict[str, str]]:
    if ent.entity_kind == EntityKind.EDGE and ent.source_entity and ent.target_entity:
        return {"source": ent.source_entity, "target": ent.target_entity}
    return None


def _key_record(entity: str, k: _KeyInfo, action: str) -> OpRecord:
    op_map = {
        ("primary", "add"): "ADD_PRIMARY_KEY",
        ("primary", "delete"): "DELETE_PRIMARY_KEY",
        ("unique", "add"): "ADD_UNIQUE_KEY",
        ("unique", "delete"): "DELETE_UNIQUE_KEY",
        ("partition", "add"): "ADD_PARTITION_KEY",
        ("partition", "delete"): "DELETE_PARTITION_KEY",
        ("clustering", "add"): "ADD_CLUSTERING_KEY",
        ("clustering", "delete"): "DELETE_CLUSTERING_KEY",
    }
    return OpRecord(
        op=op_map[(k.pk_type, action)],
        params={"entity": entity, "columns": k.columns},
    )


# ============================================================================
# MAPPING HINTS
# ============================================================================
# Hint shapes (all keys lower-case):
#   {"op": "FLATTEN",  "entity": "person", "nested": "name"}
#   {"op": "UNFLATTEN","entity": "person", "fields": ["vorname","nachname"], "nested_name": "name"}
#   {"op": "NEST",     "source": "address", "fields": ["street","city"], "parent": "person", "embed_name": "address", "where": "person.address_id = address.id"}
#   {"op": "UNNEST",   "entity": "person", "nested": "address", "fields": ["street","city"], "new_entity": "address", "carry": [["person.id","address.person_id"]]}
#   {"op": "UNWIND",   "entity": "person", "field": "tags", "new_entity": "person_tag"}  (new_entity optional)
#   {"op": "WIND",     "entity": "person_tag", "field": "tags"}
#   {"op": "TRANSFORM","entity": "works_at", "into": "RELATIONSHIP", "source": "person", "target": "company", "cardinality": "ZERO_TO_MANY"}
#   {"op": "TRANSFORM","entity": "works_at", "into": "ENTITY"}
#
# Each hint may also carry "suppress": {"src_props":[["entity","field"]...], ...}
# to tell the auto-diff to ignore those entries (avoid double-emitting).

def _hint_to_record(
    h: Dict[str, Any],
    suppressed_src_props: Set[Tuple[str, str]],
    suppressed_tgt_props: Set[Tuple[str, str]],
    suppressed_src_entities: Set[str],
    suppressed_tgt_entities: Set[str],
) -> Optional[OpRecord]:
    op = (h.get("op") or "").upper()
    suppress = h.get("suppress") or {}
    for pair in suppress.get("src_props", []):
        suppressed_src_props.add(tuple(pair))
    for pair in suppress.get("tgt_props", []):
        suppressed_tgt_props.add(tuple(pair))
    for n in suppress.get("src_entities", []):
        suppressed_src_entities.add(n)
    for n in suppress.get("tgt_entities", []):
        suppressed_tgt_entities.add(n)

    if op == "FLATTEN":
        return OpRecord(op="FLATTEN", params={"entity": h["entity"], "nested": h["nested"]})
    if op == "UNFLATTEN":
        return OpRecord(op="UNFLATTEN", params={
            "entity": h["entity"],
            "fields": list(h.get("fields", [])),
            "nested_name": h["nested_name"],
        })
    if op == "NEST":
        return OpRecord(op="NEST", params={
            "source": h["source"],
            "fields": list(h.get("fields", [])),
            "parent": h["parent"],
            "embed_name": h["embed_name"],
            "where": h.get("where", ""),
        })
    if op == "UNNEST":
        return OpRecord(op="UNNEST", params={
            "entity": h["entity"],
            "nested": h["nested"],
            "fields": list(h.get("fields", [])),
            "new_entity": h["new_entity"],
            "carry": [list(c) for c in h.get("carry", [])],
        })
    if op == "UNWIND":
        return OpRecord(op="UNWIND", params={
            "entity": h["entity"],
            "field": h["field"],
            "new_entity": h.get("new_entity"),
        })
    if op == "WIND":
        return OpRecord(op="WIND", params={"entity": h["entity"], "field": h["field"]})
    if op == "TRANSFORM":
        into = (h.get("into") or "").upper()
        if into == "RELATIONSHIP":
            return OpRecord(op="TRANSFORM", params={
                "entity": h["entity"],
                "into": "RELATIONSHIP",
                "source": h["source"],
                "target": h["target"],
                "cardinality": h.get("cardinality"),
            })
        return OpRecord(op="TRANSFORM", params={
            "entity": h["entity"],
            "into": "ENTITY",
        })
    return None
