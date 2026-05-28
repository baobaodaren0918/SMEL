"""Layer Preparation II — Metamodel Integrity Check.

Runs in parallel with the script-execution gate (Layer Preparation I).
Together they form the two pre-validation steps that precede the three
authoritative correctness layers documented in the thesis (Layer 1 / 2
/ 3 — meta-comparison, round-trip, text-fidelity).

Scans the in-memory ``Database`` for invariant violations:

  1. ``ForeignKeyProperty.points_to_unique_property_id`` resolves to a
     live ``UniqueProperty.meta_id`` somewhere in the database.
  2. ``UniqueProperty.property_id`` resolves to a live ``Property.meta_id``
     in the holding entity.
  3. ``ForeignKeyProperty.property_id`` resolves to a live ``Property``
     in the holding entity.
  4. ``CheckConstraint.target_property_id`` / ``ExistenceConstraint.target_property_id``
     resolve to a live ``Property``.
  5. ``UniqueProperty.meta_id`` is unique across the entire database
     (no UUID collisions from ``copy.deepcopy`` in SPLIT/MERGE/COPY_ENTITY).

These violations indicate dangling internal pointers that would silently
mis-resolve at serialization time. The check is read-only — it does not
mutate the database; callers decide whether a violation is a hard fail
or a warning.
"""
from typing import Any, Dict, List


def validate_integrity(database) -> Dict[str, Any]:
    """Scan the metamodel for invariant violations. Returns a dict with
    ``passed`` (bool), ``summary`` (str), and ``violations`` (list)."""
    violations: List[Dict[str, Any]] = []

    # Pass 1: collect live IDs grouped by which entity holds them.
    live_property_ids: Dict[str, str] = {}        # prop_meta_id -> entity_name
    live_up_meta_ids: Dict[str, List[str]] = {}   # up_meta_id  -> [entity_names]

    for entity in database.entity_types.values():
        ent_name = entity.full_path
        for prop in entity.properties:
            live_property_ids[prop.meta_id] = ent_name
        for c in entity.constraints:
            if c.kind == "unique":
                for up in c.unique_properties:
                    live_up_meta_ids.setdefault(up.meta_id, []).append(ent_name)

    # Check 5: duplicate UP meta_id across entities (UUID collision)
    for up_id, holders in live_up_meta_ids.items():
        if len(holders) > 1:
            violations.append({
                "type": "duplicate_up_meta_id",
                "meta_id_prefix": up_id[:8],
                "entities": holders,
            })

    live_up_set = set(live_up_meta_ids.keys())

    # Pass 2: check all pointers
    for entity in database.entity_types.values():
        ent_name = entity.full_path
        ent_prop_ids = {p.meta_id for p in entity.properties}

        for c in entity.constraints:
            if c.kind == "unique":
                for up in c.unique_properties:
                    # Check 2: UP.property_id must resolve in the same entity
                    if up.property_id not in ent_prop_ids:
                        violations.append({
                            "type": "dangling_up_property_id",
                            "entity": ent_name,
                            "up_meta_id_prefix": up.meta_id[:8],
                            "dangling_property_id_prefix": up.property_id[:8],
                        })
            elif c.kind == "foreign_key":
                for fkp in c.foreign_key_properties:
                    # Check 3: FK source column must resolve in the holding entity
                    if fkp.property_id not in ent_prop_ids:
                        violations.append({
                            "type": "dangling_fk_source_property_id",
                            "entity": ent_name,
                            "dangling_property_id_prefix": fkp.property_id[:8],
                        })
                    # Check 1: FK target UP must resolve somewhere in the DB
                    if fkp.points_to_unique_property_id not in live_up_set:
                        src_attr = entity.get_property_by_id(fkp.property_id)
                        col_name = src_attr.name if src_attr else "<missing>"
                        violations.append({
                            "type": "dangling_fk_target_up_id",
                            "entity": ent_name,
                            "fk_column": col_name,
                            "dangling_up_id_prefix": fkp.points_to_unique_property_id[:8],
                        })
            elif c.kind == "check":
                # Check 4a: CheckConstraint.target_property_id
                if c.target_property_id and c.target_property_id not in ent_prop_ids:
                    violations.append({
                        "type": "dangling_check_target_property_id",
                        "entity": ent_name,
                        "dangling_property_id_prefix": c.target_property_id[:8],
                    })
            elif c.kind == "existence":
                # Check 4b: ExistenceConstraint.target_property_id
                if c.target_property_id and c.target_property_id not in ent_prop_ids:
                    violations.append({
                        "type": "dangling_existence_target_property_id",
                        "entity": ent_name,
                        "dangling_property_id_prefix": c.target_property_id[:8],
                    })

    return {
        "passed": len(violations) == 0,
        "summary": (f"PASS (0 violations)" if not violations
                    else f"FAIL ({len(violations)} violations)"),
        "violations": violations,
    }
