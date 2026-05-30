"""
Unit tests for the relationship trace mechanism on the SchemaTransformer
base class. These are deliberately small and bypass the full parse/migrate
pipeline so the trace's edge cases can be exercised in isolation.

The key invariant under test: when multiple trace entries match the same
Edge endpoint pair, ``_consume_deleted_fk_for_edge`` must NOT silently
pick one — it must log a warning and return (None, None), leaving the
caller to fall back to the default. This protects against the multi-FK
footgun (e.g. an entity with both ``billing_customer_id`` and
``shipping_customer_id`` pointing at the same target).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import SchemaTransformer
from Schema.unified_meta_schema import (
    Cardinality,
    Database,
    DatabaseType,
    RelationshipTrace,
    TraceOrigin,
)


def _new_transformer():
    return SchemaTransformer(Database(db_name="t", db_type=DatabaseType.RELATIONAL))


def test_single_trace_opp_dir_returns_swapped_values():
    """One trace entry, opposite-direction lookup: source/target swap per Path C convention."""
    t = _new_transformer()
    t._relationship_trace.append(RelationshipTrace(
        holder="orders", ref_name="customer_id", target="customers",
        target_end_cardinality=Cardinality.ONE_TO_ONE,
        source_end_cardinality=Cardinality.ZERO_TO_MANY,
        origin=TraceOrigin.DELETED_REFERENCE,
    ))
    # ADD_ENTITY PURCHASED FROM customers TO orders → opp_dir match
    target_end_card, source_end_card = t._consume_deleted_fk_for_edge("customers", "orders")
    assert target_end_card == Cardinality.ZERO_TO_MANY  # was trace.source_end_cardinality
    assert source_end_card == Cardinality.ONE_TO_ONE    # was trace.target_end_cardinality
    assert t._relationship_trace == []              # consumed


def test_single_trace_same_dir_returns_direct_values():
    """One trace entry, same-direction lookup: no swap."""
    t = _new_transformer()
    t._relationship_trace.append(RelationshipTrace(
        holder="products", ref_name="category_id", target="categories",
        target_end_cardinality=Cardinality.ONE_TO_ONE,
        source_end_cardinality=Cardinality.ZERO_TO_MANY,
        origin=TraceOrigin.DELETED_REFERENCE,
    ))
    # ADD_ENTITY PART_OF FROM products TO categories → same_dir match
    target_end_card, source_end_card = t._consume_deleted_fk_for_edge("products", "categories")
    assert target_end_card == Cardinality.ONE_TO_ONE
    assert source_end_card == Cardinality.ZERO_TO_MANY
    assert t._relationship_trace == []


def test_multi_fk_same_endpoint_pair_refuses_to_guess():
    """Multi-FK footgun: two References from orders to customers
    (billing_customer_id + shipping_customer_id) produce two trace entries
    on the same (orders, customers) endpoint pair. ADD_ENTITY must NOT
    silently pick one; it must log a warning and return (None, None) so
    the caller falls back to the default target_end_cardinality."""
    t = _new_transformer()
    t._relationship_trace.append(RelationshipTrace(
        holder="orders", ref_name="billing_customer_id", target="customers",
        target_end_cardinality=Cardinality.ONE_TO_ONE,
        source_end_cardinality=Cardinality.ZERO_TO_MANY,
        origin=TraceOrigin.DELETED_REFERENCE,
    ))
    t._relationship_trace.append(RelationshipTrace(
        holder="orders", ref_name="shipping_customer_id", target="customers",
        target_end_cardinality=Cardinality.ZERO_TO_ONE,
        source_end_cardinality=Cardinality.ZERO_TO_MANY,
        origin=TraceOrigin.DELETED_REFERENCE,
    ))
    # ADD_ENTITY CUSTOMER_LINK FROM customers TO orders → opp_dir would
    # find 2 candidates → refuse to guess.
    target_end_card, source_end_card = t._consume_deleted_fk_for_edge("customers", "orders")
    assert target_end_card is None
    assert source_end_card is None
    # Both traces remain — neither was silently consumed.
    assert len(t._relationship_trace) == 2


def test_self_ref_multi_trace_also_refuses_to_guess():
    """Self-reference variant: multiple traces with holder == target.
    Same protection applies."""
    t = _new_transformer()
    t._relationship_trace.append(RelationshipTrace(
        holder="employees", ref_name="manager_id", target="employees",
        target_end_cardinality=Cardinality.ZERO_TO_ONE,
        origin=TraceOrigin.DELETED_REFERENCE,
    ))
    t._relationship_trace.append(RelationshipTrace(
        holder="employees", ref_name="mentor_id", target="employees",
        target_end_cardinality=Cardinality.ZERO_TO_ONE,
        origin=TraceOrigin.DELETED_REFERENCE,
    ))
    # ADD_ENTITY REPORTS_TO FROM employees TO employees — self-ref edge.
    target_end_card, source_end_card = t._consume_deleted_fk_for_edge("employees", "employees")
    assert target_end_card is None
    assert source_end_card is None
    assert len(t._relationship_trace) == 2


def test_fallback_default_applied_after_ambiguous_lookup():
    """After ambiguous lookup returns None, _default_source_end_cardinality
    fills 0..n. The handler thus emits an explicit default rather than
    silently propagating a guessed value."""
    t = _new_transformer()
    t._relationship_trace.append(RelationshipTrace(
        holder="orders", ref_name="billing_customer_id", target="customers",
        target_end_cardinality=Cardinality.ONE_TO_ONE,
        origin=TraceOrigin.DELETED_REFERENCE,
    ))
    t._relationship_trace.append(RelationshipTrace(
        holder="orders", ref_name="shipping_customer_id", target="customers",
        target_end_cardinality=Cardinality.ONE_TO_ONE,
        origin=TraceOrigin.DELETED_REFERENCE,
    ))
    _, source_end_card = t._consume_deleted_fk_for_edge("customers", "orders")
    # default_source_end_cardinality returns ZERO_TO_MANY when given None
    assert t._default_source_end_cardinality(source_end_card) == Cardinality.ZERO_TO_MANY
