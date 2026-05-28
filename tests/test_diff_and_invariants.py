"""Unit tests for diff/engine.py and the post-PK-replacement FK relink.

These are deliberately small — they build minimal Database / dict fixtures
without going through the full parse/migrate pipeline, so the invariants
under test are exercised in isolation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import SchemaTransformer
from parser.params import AddKeyParams, OperationResult
from parser.listeners import OpType, KeyType
from Schema.unified_meta_schema import (
    Database, DatabaseType, EntityType, EntityKind,
    Property, PrimitiveDataType, PrimitiveType, PKTypeEnum, Cardinality,
    UniqueConstraint, UniqueProperty,
    ForeignKeyConstraint, ForeignKeyProperty,
    CheckConstraint, CheckCmp, Reference,
)
from diff.engine import _diff_constraints


# -----------------------------------------------------------------------------
# #54 PK relink regression test
# -----------------------------------------------------------------------------

def test_add_primary_key_relinks_incoming_fks():
    """After ADD_PRIMARY_KEY replaces an existing PK, an FK in another
    entity that pointed at the OLD UniqueProperty.meta_id must continue
    to resolve correctly — its points_to_unique_property_id must be
    rewritten to the NEW UniqueProperty.meta_id of the replacement PK."""
    db = Database(db_name="t", db_type=DatabaseType.RELATIONAL)

    # customers entity with PK on customer_id (old UP meta_id = ABC)
    customers = EntityType(object_name=["customers"])
    cust_pk_col = Property("customer_id", PrimitiveDataType(PrimitiveType.STRING),
                           is_key=True, is_optional=False)
    customers.add_property(cust_pk_col)
    old_up = UniqueProperty(primary_key_type=PKTypeEnum.SIMPLE,
                            property_id=cust_pk_col.meta_id)
    old_up_meta_id = old_up.meta_id
    customers.add_constraint(UniqueConstraint(
        is_primary_key=True, is_managed=True, unique_properties=[old_up]))
    db.add_entity_type(customers)

    # orders entity with FK pointing at customers.customer_id via old_up_meta_id
    orders = EntityType(object_name=["orders"])
    orders.add_property(Property("order_id", PrimitiveDataType(PrimitiveType.STRING),
                                 is_key=True, is_optional=False))
    fk_col = Property("customer_id", PrimitiveDataType(PrimitiveType.STRING),
                      is_key=False, is_optional=False)
    orders.add_property(fk_col)
    orders.add_constraint(ForeignKeyConstraint(
        is_managed=True,
        foreign_key_properties=[ForeignKeyProperty(
            property_id=fk_col.meta_id,
            points_to_unique_property_id=old_up_meta_id,
        )],
    ))
    # Reference relationship pairs the FK column to its target entity (used by
    # the serializer to resolve ``references_entity``).
    orders.add_relationship(Reference(
        ref_name="customer_id",
        refs_to="customers",
        cardinality=Cardinality.ONE_TO_ONE,
        is_optional=False,
        is_enforced=True,
    ))
    db.add_entity_type(orders)

    # Sanity: pre-replacement state
    assert orders.constraints[0].foreign_key_properties[0].points_to_unique_property_id == old_up_meta_id

    # Run ADD_PRIMARY_KEY customer_id TO customers — replaces the PK
    transformer = SchemaTransformer(db)
    result = transformer._handlers[OpType.ADD_KEY](AddKeyParams(
        key_type=KeyType.PRIMARY,
        key_columns=["customer_id"],
        entity="customers",
    ))
    assert result.success, f"ADD_PRIMARY_KEY failed: {result}"

    # The new PK has a fresh UniqueProperty meta_id
    new_customers = transformer.database.get_entity_type("customers")
    new_pk = new_customers.get_primary_key()
    new_up_meta_id = new_pk.unique_properties[0].meta_id
    assert new_up_meta_id != old_up_meta_id, "new PK should have a fresh UP meta_id"

    # The FK in orders must now point at the NEW UP, not the orphaned old one
    new_orders = transformer.database.get_entity_type("orders")
    fk = next(c for c in new_orders.constraints if c.kind == "foreign_key")
    assert fk.foreign_key_properties[0].points_to_unique_property_id == new_up_meta_id, (
        "FK target UP meta_id was not relinked after PK replacement — "
        f"still points at orphan {old_up_meta_id}"
    )


# -----------------------------------------------------------------------------
# #55 FK diff target column test
# -----------------------------------------------------------------------------

def test_fk_diff_distinguishes_target_columns():
    """Two FKs sharing (column, references_entity) but with different
    references_property values must be reported as missing+extra by
    _diff_constraints — regression for diff/engine.py:341 (FK identity
    must include the target column)."""
    left_constraints = [{
        "type": "FOREIGN_KEY",
        "column": "country",
        "references_entity": "countries",
        "references_property": "code",   # actual points at 'code'
    }]
    right_constraints = [{
        "type": "FOREIGN_KEY",
        "column": "country",
        "references_entity": "countries",
        "references_property": "id",     # expected points at 'id'
    }]

    diff = _diff_constraints(left_constraints, right_constraints)
    # The two FKs must NOT be considered equal — one is missing on each side
    assert len(diff.fk_missing) == 1, (
        f"expected 1 missing FK (on right side), got {diff.fk_missing}")
    assert len(diff.fk_extra) == 1, (
        f"expected 1 extra FK (on left side), got {diff.fk_extra}")
    # missing/extra entries are tuples (column, references_entity, references_property)
    assert diff.fk_missing[0] == ("country", "countries", "id")
    assert diff.fk_extra[0] == ("country", "countries", "code")


def test_fk_diff_identical_fks_are_equal():
    """Same (column, references_entity, references_property) tuple
    must be reported as no-diff."""
    fk = {
        "type": "FOREIGN_KEY",
        "column": "customer_id",
        "references_entity": "customers",
        "references_property": "customer_id",
    }
    diff = _diff_constraints([fk], [fk])
    assert not diff.fk_missing
    assert not diff.fk_extra


# -----------------------------------------------------------------------------
# #56 CHECK constraint diff test
# -----------------------------------------------------------------------------

def test_check_constraint_diff_reports_missing_and_extra():
    """Two CHECK constraints on the same anchor property but with
    different expressions must be reported as missing+extra."""
    left_constraints = [{
        "type": "CHECK",
        "target": "price",
        "expression": {"kind": "cmp", "field": "price", "op": ">", "literal": 0},
    }]
    right_constraints = [{
        "type": "CHECK",
        "target": "price",
        "expression": {"kind": "cmp", "field": "price", "op": ">=", "literal": 0},
    }]

    diff = _diff_constraints(left_constraints, right_constraints)
    assert len(diff.check_missing) == 1, (
        f"expected 1 missing CHECK, got {diff.check_missing}")
    assert len(diff.check_extra) == 1, (
        f"expected 1 extra CHECK, got {diff.check_extra}")
    # The missing one is from right (expected); extra one is from left (actual)
    assert diff.check_missing[0]["expression"]["op"] == ">="
    assert diff.check_extra[0]["expression"]["op"] == ">"


def test_check_constraint_diff_identical_are_equal():
    """Same CHECK expression on same target must be no-diff."""
    check = {
        "type": "CHECK",
        "target": "price",
        "expression": {"kind": "cmp", "field": "price", "op": ">", "literal": 0},
    }
    diff = _diff_constraints([check], [check])
    assert not diff.check_missing
    assert not diff.check_extra
