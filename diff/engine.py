"""DatabaseDiff — single source of truth for "how do two db_to_dict snapshots differ"."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# Sub-records used inside EntityDiff / RelationshipTypeDiff

@dataclass
class PropertyTypeChange:
    name: str
    left_type: str
    right_type: str


@dataclass
class TargetChange:
    name: str
    left_target: str
    right_target: str


@dataclass
class CardinalityChange:
    name: str
    left: str
    right: str


@dataclass
class EdgeTargetChange:
    """Source and/or target endpoint change on an edge or relationship_type."""
    name: str
    left_source: Optional[str] = None
    right_source: Optional[str] = None
    left_target: Optional[str] = None
    right_target: Optional[str] = None


@dataclass
class ReferenceAttrChange:
    """Edge-properties on a Reference relationship changed."""
    name: str
    left_attrs: Dict[str, str]
    right_attrs: Dict[str, str]


# Constraint diff

@dataclass
class ConstraintDiff:
    """Constraint comparison; PKs are by (type, columns), FKs grouped by entity."""
    missing_pk: List[Dict] = field(default_factory=list)   # only in right
    extra_pk: List[Dict] = field(default_factory=list)     # only in left
    pk_type_changes: List[Dict] = field(default_factory=list)  # PARTITION/CLUSTERING differs
    fk_missing: List[Tuple[str, str]] = field(default_factory=list)  # only in right
    fk_extra: List[Tuple[str, str]] = field(default_factory=list)    # only in left

    def is_empty(self) -> bool:
        return not (self.missing_pk or self.extra_pk or self.pk_type_changes
                    or self.fk_missing or self.fk_extra)


# Per-entity diff

@dataclass
class EntityDiff:
    """Structural diff for a single entity present on both sides."""
    name: str

    # Properties (by name)
    props_only_left: List[Dict] = field(default_factory=list)
    props_only_right: List[Dict] = field(default_factory=list)
    prop_type_changes: List[PropertyTypeChange] = field(default_factory=list)
    prop_key_warnings: List[Dict] = field(default_factory=list)
    prop_optional_warnings: List[Dict] = field(default_factory=list)

    # Embedded (by name)
    embedded_only_left: List[Dict] = field(default_factory=list)
    embedded_only_right: List[Dict] = field(default_factory=list)
    embedded_target_changes: List[TargetChange] = field(default_factory=list)
    embedded_cardinality_changes: List[CardinalityChange] = field(default_factory=list)

    # References (by name)
    refs_only_left: List[Dict] = field(default_factory=list)
    refs_only_right: List[Dict] = field(default_factory=list)
    ref_target_changes: List[TargetChange] = field(default_factory=list)
    ref_attr_changes: List[ReferenceAttrChange] = field(default_factory=list)
    ref_cardinality_changes: List[CardinalityChange] = field(default_factory=list)

    # Edges (by name) — present on the source-side entity for graph models
    edges_only_left: List[Dict] = field(default_factory=list)
    edges_only_right: List[Dict] = field(default_factory=list)
    edge_endpoint_changes: List[EdgeTargetChange] = field(default_factory=list)
    edge_cardinality_changes: List[CardinalityChange] = field(default_factory=list)

    # Whole-entity flags
    entity_kind_changed: bool = False
    entity_kind_left: Optional[str] = None
    entity_kind_right: Optional[str] = None
    constraint_diff: Optional[ConstraintDiff] = None

    def is_empty(self) -> bool:
        """True iff nothing on either side differs (including warnings)."""
        return not (
            self.props_only_left or self.props_only_right or self.prop_type_changes
            or self.prop_key_warnings or self.prop_optional_warnings
            or self.embedded_only_left or self.embedded_only_right
            or self.embedded_target_changes or self.embedded_cardinality_changes
            or self.refs_only_left or self.refs_only_right
            or self.ref_target_changes or self.ref_attr_changes or self.ref_cardinality_changes
            or self.edges_only_left or self.edges_only_right
            or self.edge_endpoint_changes or self.edge_cardinality_changes
            or self.entity_kind_changed
            or (self.constraint_diff is not None and not self.constraint_diff.is_empty())
        )

    def has_hard_issues(self) -> bool:
        """True if anything beyond a 'warning'-class difference exists."""
        return bool(
            self.props_only_left or self.props_only_right or self.prop_type_changes
            or self.embedded_only_left or self.embedded_only_right or self.embedded_target_changes
            or self.refs_only_left or self.refs_only_right or self.ref_target_changes
            or self.ref_attr_changes
            or self.edges_only_left or self.edges_only_right or self.edge_endpoint_changes
            or (self.constraint_diff is not None
                and (self.constraint_diff.missing_pk or self.constraint_diff.extra_pk))
        )


# Relationship_type diff (graph schemas only)

@dataclass
class RelationshipTypeDiff:
    name: str
    endpoint_changes: List[EdgeTargetChange] = field(default_factory=list)
    cardinality_changes: List[CardinalityChange] = field(default_factory=list)
    attr_mismatches: List[ReferenceAttrChange] = field(default_factory=list)


# Top-level diff

@dataclass
class DatabaseDiff:
    """Structural delta between two db_to_dict snapshots."""
    entities_only_left: List[str] = field(default_factory=list)
    entities_only_right: List[str] = field(default_factory=list)
    entity_diffs: Dict[str, EntityDiff] = field(default_factory=dict)

    # Graph relationship_types (the "__relationship_types__" sidecar)
    rels_only_left: List[str] = field(default_factory=list)
    rels_only_right: List[str] = field(default_factory=list)
    rel_diffs: Dict[str, RelationshipTypeDiff] = field(default_factory=dict)


# Core diff computation

def _by_name(items: List[Dict]) -> Dict[str, Dict]:
    return {x["name"]: x for x in items}


def _diff_entity(
    name: str,
    left: Dict,
    right: Dict,
) -> EntityDiff:
    diff = EntityDiff(name=name)

    if left.get("entity_kind") != right.get("entity_kind"):
        diff.entity_kind_changed = True
        diff.entity_kind_left = left.get("entity_kind")
        diff.entity_kind_right = right.get("entity_kind")

    # ---- Properties ----
    l_props = _by_name(left.get("properties", []))
    r_props = _by_name(right.get("properties", []))
    only_left = sorted(set(l_props) - set(r_props))
    only_right = sorted(set(r_props) - set(l_props))
    diff.props_only_left = [l_props[n] for n in only_left]
    diff.props_only_right = [r_props[n] for n in only_right]
    for n in sorted(set(l_props) & set(r_props)):
        a, b = l_props[n], r_props[n]
        if a.get("type") != b.get("type"):
            diff.prop_type_changes.append(
                PropertyTypeChange(name=n,
                                   left_type=a.get("type", ""),
                                   right_type=b.get("type", ""))
            )
        for fld in ("is_key", "key_type"):
            if a.get(fld) != b.get(fld):
                diff.prop_key_warnings.append({
                    "attr": n, "field": fld,
                    "left": a.get(fld), "right": b.get(fld),
                })
        if a.get("is_optional") != b.get("is_optional"):
            diff.prop_optional_warnings.append({
                "attr": n,
                "left": a.get("is_optional"),
                "right": b.get("is_optional"),
            })

    # ---- Embedded ----
    l_emb = _by_name(left.get("embedded", []))
    r_emb = _by_name(right.get("embedded", []))
    only_left = sorted(set(l_emb) - set(r_emb))
    only_right = sorted(set(r_emb) - set(l_emb))
    diff.embedded_only_left = [l_emb[n] for n in only_left]
    diff.embedded_only_right = [r_emb[n] for n in only_right]
    for n in sorted(set(l_emb) & set(r_emb)):
        a, b = l_emb[n], r_emb[n]
        if a.get("target") != b.get("target"):
            diff.embedded_target_changes.append(
                TargetChange(name=n,
                             left_target=a.get("target", ""),
                             right_target=b.get("target", ""))
            )
        if a.get("cardinality") != b.get("cardinality"):
            diff.embedded_cardinality_changes.append(
                CardinalityChange(name=n,
                                  left=a.get("cardinality", ""),
                                  right=b.get("cardinality", ""))
            )

    # ---- References ----
    l_ref = _by_name(left.get("references", []))
    r_ref = _by_name(right.get("references", []))
    only_left = sorted(set(l_ref) - set(r_ref))
    only_right = sorted(set(r_ref) - set(l_ref))
    diff.refs_only_left = [l_ref[n] for n in only_left]
    diff.refs_only_right = [r_ref[n] for n in only_right]
    for n in sorted(set(l_ref) & set(r_ref)):
        a, b = l_ref[n], r_ref[n]
        if a.get("target") != b.get("target"):
            diff.ref_target_changes.append(
                TargetChange(name=n,
                             left_target=a.get("target", ""),
                             right_target=b.get("target", ""))
            )
        a_attrs = {x["name"]: x.get("type", "") for x in a.get("edge_properties", [])}
        b_attrs = {x["name"]: x.get("type", "") for x in b.get("edge_properties", [])}
        if a_attrs != b_attrs:
            diff.ref_attr_changes.append(
                ReferenceAttrChange(name=n, left_attrs=a_attrs, right_attrs=b_attrs)
            )
        if a.get("cardinality") != b.get("cardinality"):
            diff.ref_cardinality_changes.append(
                CardinalityChange(name=n,
                                  left=a.get("cardinality", ""),
                                  right=b.get("cardinality", ""))
            )

    # ---- Edges ----
    l_edge = _by_name(left.get("edges", []))
    r_edge = _by_name(right.get("edges", []))
    only_left = sorted(set(l_edge) - set(r_edge))
    only_right = sorted(set(r_edge) - set(l_edge))
    diff.edges_only_left = [l_edge[n] for n in only_left]
    diff.edges_only_right = [r_edge[n] for n in only_right]
    for n in sorted(set(l_edge) & set(r_edge)):
        a, b = l_edge[n], r_edge[n]
        s_diff = a.get("source") != b.get("source")
        t_diff = a.get("target") != b.get("target")
        if s_diff or t_diff:
            diff.edge_endpoint_changes.append(EdgeTargetChange(
                name=n,
                left_source=a.get("source") if s_diff else None,
                right_source=b.get("source") if s_diff else None,
                left_target=a.get("target") if t_diff else None,
                right_target=b.get("target") if t_diff else None,
            ))
        if a.get("cardinality") != b.get("cardinality"):
            diff.edge_cardinality_changes.append(
                CardinalityChange(name=n,
                                  left=a.get("cardinality", ""),
                                  right=b.get("cardinality", ""))
            )

    # ---- Constraints ----
    diff.constraint_diff = _diff_constraints(
        left.get("constraints", []), right.get("constraints", [])
    )

    return diff


def _diff_constraints(left: List[Dict], right: List[Dict]) -> ConstraintDiff:
    """Compare constraint lists. PKs by (type, sorted columns); FKs by (column, target entity)."""
    cd = ConstraintDiff()
    l_pk = [c for c in left  if c.get("type") in ("PRIMARY_KEY", "UNIQUE")]
    r_pk = [c for c in right if c.get("type") in ("PRIMARY_KEY", "UNIQUE")]
    l_fk = [c for c in left  if c.get("type") == "FOREIGN_KEY"]
    r_fk = [c for c in right if c.get("type") == "FOREIGN_KEY"]

    pk_key = lambda c: (c["type"], tuple(sorted(c.get("columns", []))))
    l_pk_set = {pk_key(c): c for c in l_pk}
    r_pk_set = {pk_key(c): c for c in r_pk}
    cd.missing_pk = [r_pk_set[k] for k in sorted(set(r_pk_set) - set(l_pk_set))]
    cd.extra_pk   = [l_pk_set[k] for k in sorted(set(l_pk_set) - set(r_pk_set))]
    for k in sorted(set(l_pk_set) & set(r_pk_set)):
        l_types = l_pk_set[k].get("primary_key_types")
        r_types = r_pk_set[k].get("primary_key_types")
        if l_types != r_types:
            cd.pk_type_changes.append({
                "columns": list(k[1]),
                "left": l_types, "right": r_types,
            })

    fk_key = lambda c: (c.get("column", ""), c.get("references_entity", ""))
    l_fk_set = {fk_key(c) for c in l_fk}
    r_fk_set = {fk_key(c) for c in r_fk}
    cd.fk_missing = sorted(r_fk_set - l_fk_set)
    cd.fk_extra   = sorted(l_fk_set - r_fk_set)
    return cd


def _diff_relationship_types(left: Dict, right: Dict) -> Tuple[List[str], List[str], Dict[str, RelationshipTypeDiff]]:
    only_left = sorted(set(left) - set(right))
    only_right = sorted(set(right) - set(left))
    diffs: Dict[str, RelationshipTypeDiff] = {}
    for n in sorted(set(left) & set(right)):
        a, b = left[n], right[n]
        rd = RelationshipTypeDiff(name=n)
        if a.get("source_entity") != b.get("source_entity") or a.get("target_entity") != b.get("target_entity"):
            rd.endpoint_changes.append(EdgeTargetChange(
                name=n,
                left_source=a.get("source_entity"),
                right_source=b.get("source_entity"),
                left_target=a.get("target_entity"),
                right_target=b.get("target_entity"),
            ))
        if a.get("cardinality") != b.get("cardinality"):
            rd.cardinality_changes.append(CardinalityChange(
                name=n,
                left=a.get("cardinality", ""),
                right=b.get("cardinality", ""),
            ))
        a_attrs = {x["name"]: x.get("type", "") for x in a.get("properties", [])}
        b_attrs = {x["name"]: x.get("type", "") for x in b.get("properties", [])}
        if a_attrs != b_attrs:
            rd.attr_mismatches.append(ReferenceAttrChange(
                name=n, left_attrs=a_attrs, right_attrs=b_attrs,
            ))
        if rd.endpoint_changes or rd.cardinality_changes or rd.attr_mismatches:
            diffs[n] = rd
    return only_left, only_right, diffs


def compute_diff(
    left: Dict[str, Any],
    right: Dict[str, Any],
    only_entities: Optional[Set[str]] = None,
) -> DatabaseDiff:
    """Compute the structural diff between two ``db_to_dict`` snapshots."""
    diff = DatabaseDiff()

    l_names = {k for k in left  if not k.startswith("__")}
    r_names = {k for k in right if not k.startswith("__")}
    diff.entities_only_left  = sorted(l_names - r_names)
    diff.entities_only_right = sorted(r_names - l_names)

    common = l_names & r_names
    if only_entities is not None:
        common &= set(only_entities)
    for name in sorted(common):
        ediff = _diff_entity(name, left[name], right[name])
        if not ediff.is_empty():
            diff.entity_diffs[name] = ediff

    l_rels = left.get("__relationship_types__", {})
    r_rels = right.get("__relationship_types__", {})
    if l_rels or r_rels:
        diff.rels_only_left, diff.rels_only_right, diff.rel_diffs = (
            _diff_relationship_types(l_rels, r_rels)
        )

    return diff
