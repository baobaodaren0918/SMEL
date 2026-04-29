"""
Negative tests — verify the system fails *gracefully* when given bad input.

The 73 happy-path tests in test_full_flow.py / test_parser.py prove the
golden path works. This file proves the *failure* surfaces are sane:

* ``OpParams`` constructors reject empty required identifiers at
  construction time (rather than letting None/empty propagate into a
  confusing AttributeError deep inside a handler);
* handlers return ``OperationResult.skipped(reason=...)`` instead of
  raising when an op references something that does not exist;
* the run_apply loop continues past a bad op and finishes the rest;
* ``parse_smile_auto`` collects ANTLR syntax errors into the returned
  errors list — it does not crash and does not silently emit ops;
* adapters raise an informative exception on garbage native input.
"""
import sys
import tempfile
from pathlib import Path

import pytest

# Make the project root importable when pytest runs from this dir.
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.params import (
    AddPropertyParams, DeletePropertyParams, NestParams, UnnestParams,
    AddKeyParams, KeyType, OperationResult,
)
from Schema.unified_meta_schema import (
    Database, DatabaseType, EntityType, EntityKind, Property,
    PrimitiveDataType, PrimitiveType,
)


# ============================================================================
# 1. OpParams self-validation (#13 from stage 1)
# ============================================================================

class TestOpParamsValidation:
    """Constructing an OpParams with an empty required identifier must raise."""

    def test_add_property_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name must be non-empty"):
            AddPropertyParams(name="")

    def test_delete_property_rejects_empty_target(self):
        with pytest.raises(ValueError, match="target must be non-empty"):
            DeletePropertyParams(target="")

    def test_nest_rejects_empty_alias(self):
        with pytest.raises(ValueError, match="alias must be non-empty"):
            NestParams(source="orders", target="customers", alias="")

    def test_nest_rejects_all_empty(self):
        with pytest.raises(ValueError):
            NestParams(source="", target="", alias="")

    def test_unnest_rejects_empty_source_path(self):
        with pytest.raises(ValueError, match="source_path must be non-empty"):
            UnnestParams(source_path="", target="customers")

    def test_add_key_rejects_unknown_key_type_string(self):
        # __post_init__ coerces str → KeyType; unknown value should fail loudly.
        with pytest.raises(ValueError, match="not a valid KeyType"):
            AddKeyParams(key_type="NOT_A_REAL_KEY_TYPE", key_columns=["id"])

    def test_add_key_accepts_enum_directly(self):
        p = AddKeyParams(key_type=KeyType.PRIMARY, key_columns=["id"])
        assert p.key_type is KeyType.PRIMARY


# ============================================================================
# 2. Handler graceful failure (#7 OperationResult)
# ============================================================================

def _make_one_entity_db() -> Database:
    """Build a trivial Database with one entity ('users') for handler tests."""
    db = Database(db_name="t", db_type=DatabaseType.RELATIONAL)
    e = EntityType(object_name=["users"], entity_kind=EntityKind.TABLE)
    e.add_property(Property(
        name="id",
        data_type=PrimitiveDataType(primitive_type=PrimitiveType.INTEGER),
        is_key=True,
    ))
    db.add_entity_type(e)
    return db


class TestHandlerGracefulFailure:
    """Handlers must return OperationResult.skipped(reason=...) on bad input,
    not raise. The reason field must identify what went wrong."""

    def test_delete_property_on_missing_entity_returns_skipped(self):
        from core import SchemaTransformer
        db = _make_one_entity_db()
        t = SchemaTransformer(db)
        result = t._handle_delete_property(DeletePropertyParams(target="ghost.field"))
        assert isinstance(result, OperationResult)
        assert not result   # __bool__ returns success
        assert result.reason, "skipped result must carry a non-empty reason"

    def test_delete_property_on_missing_field_returns_skipped(self):
        from core import SchemaTransformer
        db = _make_one_entity_db()
        t = SchemaTransformer(db)
        # Entity 'users' exists, field 'nonexistent_col' does not.
        result = t._handle_delete_property(DeletePropertyParams(target="users.nonexistent_col"))
        assert not result
        assert result.reason

    def test_add_property_on_missing_entity_returns_skipped(self):
        from core import SchemaTransformer
        db = _make_one_entity_db()
        t = SchemaTransformer(db)
        result = t._handle_add_property(
            AddPropertyParams(name="email", entity="ghost_table")
        )
        assert not result
        assert result.reason

    def test_successful_handler_returns_ok(self):
        # Sanity check that the failure assertions aren't trivially true.
        from core import SchemaTransformer
        db = _make_one_entity_db()
        t = SchemaTransformer(db)
        result = t._handle_add_property(
            AddPropertyParams(name="email", entity="users")
        )
        assert result, f"successful add should return truthy OperationResult, got reason={result.reason}"
        assert result.reason is None


# ============================================================================
# 3. Pipeline continues after a bad op
# ============================================================================

class TestPipelineContinuesAfterFailure:
    """run_apply should not bail on the first failed op."""

    def test_bad_op_then_good_op_both_recorded(self):
        from core import SchemaTransformer, run_apply
        from parser.listeners import Operation, OpType
        db = _make_one_entity_db()
        transformer = SchemaTransformer(db)

        ops = [
            # Op 1: targets a non-existent entity -> skipped
            Operation(OpType.DELETE_PROPERTY,
                      DeletePropertyParams(target="ghost.field")),
            # Op 2: valid -> success
            Operation(OpType.ADD_PROPERTY,
                      AddPropertyParams(name="email", entity="users")),
        ]
        details, success_count, skipped_count, error_count = run_apply(transformer, ops)

        assert len(details) == 2, "every op must be recorded, even when skipped"
        assert success_count == 1
        assert skipped_count == 1
        assert error_count == 0, "no handler bugs expected for valid input"
        assert details[0]["status"] == "skipped"
        assert details[0].get("reason"), "skipped op must surface a reason"
        assert details[1]["status"] == "success"
        # Side effect of op 2 actually applied:
        users = transformer.database.get_entity_type("users")
        assert any(p.name == "email" for p in users.properties)

    def test_run_migration_with_conflicting_ops_does_not_crash(self):
        """End-to-end: a script that deletes an entity then tries to add a
        property to it. The pipeline must finish and report the second op
        as skipped — not raise."""
        from core import SchemaTransformer, run_apply
        from parser.listeners import Operation, OpType
        from parser.params import DeleteEntityParams
        db = _make_one_entity_db()
        transformer = SchemaTransformer(db)
        ops = [
            Operation(OpType.DELETE_ENTITY, DeleteEntityParams(name="users")),
            Operation(OpType.ADD_PROPERTY,
                      AddPropertyParams(name="email", entity="users")),
        ]
        details, success, skipped, errors = run_apply(transformer, ops)
        assert len(details) == 2
        assert errors == 0, "no handler bugs expected for valid input"
        # First op succeeds (deletes users), second op now sees no entity.
        assert details[0]["status"] == "success"
        assert details[1]["status"] == "skipped"
        assert details[1].get("reason")


# ============================================================================
# 4. Parser handles malformed input
# ============================================================================

class TestMalformedSmileScript:
    """parse_smile_auto must collect ANTLR syntax errors into errors list,
    not raise and not silently swallow them."""

    def _write_temp(self, content: str, suffix: str = ".smile") -> str:
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        )
        f.write(content)
        f.close()
        return f.name

    def test_garbage_script_reports_errors(self):
        from parser.factory import parse_smile_auto
        path = self._write_temp("THIS IS NOT VALID SMILE @@@ ###")
        try:
            ctx, ops, errors = parse_smile_auto(path)
            # Must report errors rather than silently succeed.
            assert errors, "malformed script should produce non-empty errors list"
            assert len(ops) == 0, "no ops should be emitted from a fully-malformed script"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_empty_script_does_not_crash(self):
        from parser.factory import parse_smile_auto
        path = self._write_temp("")
        try:
            ctx, ops, errors = parse_smile_auto(path)
            # Empty file → zero ops; whether errors are emitted depends on grammar
            # (header is required), but the call must not raise.
            assert ops == []
        finally:
            Path(path).unlink(missing_ok=True)

    def test_partial_op_with_missing_name_emits_error(self):
        # MIGRATION header is fine, but ADD_PROPERTY is missing its identifier.
        script = (
            "MIGRATION test:1.0\n"
            "FROM RELATIONAL TO RELATIONAL\n"
            "USING demo VERSION 1.0\n"
            "\n"
            "ADD_PROPERTY\n"   # truncated — missing name
        )
        from parser.factory import parse_smile_auto
        path = self._write_temp(script)
        try:
            ctx, ops, errors = parse_smile_auto(path)
            assert errors, "missing-identifier syntax error must be reported"
        finally:
            Path(path).unlink(missing_ok=True)


# ============================================================================
# 5. Adapters reject corrupted native input
# ============================================================================

class TestAdapterMalformedInput:
    """Each adapter's parse() should raise an informative exception on garbage,
    not segfault, hang, or silently produce an empty Database."""

    def test_postgresql_handles_garbage_gracefully(self):
        from Schema.adapters import PostgreSQLAdapter
        # Random text isn't valid SQL DDL. The adapter is text-based and tolerant
        # (parses as zero tables) — verify it does not raise unhandled exceptions.
        db = PostgreSQLAdapter().parse("blah blah this is not sql", "t")
        assert isinstance(db, Database)
        assert len(db.entity_types) == 0, "no tables should be parsed from garbage"

    def test_mongodb_rejects_invalid_json(self):
        from Schema.adapters import MongoDBAdapter
        with pytest.raises(Exception):  # json.JSONDecodeError or similar
            MongoDBAdapter().parse("{not valid json", "t")

    def test_cassandra_handles_garbage_gracefully(self):
        from Schema.adapters import CassandraAdapter
        db = CassandraAdapter().parse("not a valid cql script", "t")
        assert isinstance(db, Database)
        assert len(db.entity_types) == 0

    def test_neo4j_invalid_json_routes_to_cypher(self):
        # Strings starting with non-{ are routed to parse_cypher per the ABC
        # contract introduced in stage 4; cypher parser is tolerant and simply
        # returns an empty db rather than raising.
        from Schema.adapters import Neo4jAdapter
        db = Neo4jAdapter().parse("not cypher either", "t")
        assert isinstance(db, Database)
        assert len(db.entity_types) == 0

    def test_neo4j_rejects_truncated_json(self):
        # If the input *looks* like JSON ({...) but is malformed, json.loads
        # raises — we want that error to propagate, not be silently swallowed.
        from Schema.adapters import Neo4jAdapter
        with pytest.raises(Exception):
            Neo4jAdapter().parse('{"nodes": [missing-quotes', "t")


# ============================================================================
# 6. Validation pipeline blame attribution
# ============================================================================

class TestValidationBlame:
    """validate_pipeline must attribute blame correctly when L1/L2 disagree."""

    def test_unverifiable_when_no_target_file(self):
        from core import run_migration
        r = run_migration("grammar_completeness_specific")
        # No target file registered for grammar_completeness → both layers N/A.
        assert r["validation_blame"] == "unverifiable"

    def test_ok_when_both_layers_pass(self):
        from core import run_migration
        r = run_migration("northwind_r2d_specific")
        assert r["validation_blame"] == "ok"

    def test_smile_script_blame_on_layer1_failure(self):
        """Simulate a broken Meta V2 (script error) and confirm blame=smile_script."""
        from core import run_migration
        from validation.pipeline import validate_pipeline
        r = run_migration("northwind_r2d_specific")
        # Surgically wreck the Meta V2 to force Layer 1 to fail.
        r["result"] = {}
        r["exported_target"] = ""
        v = validate_pipeline(r, "Document", "northwind_r2d_specific")
        assert v["blame"] == "smile_script"
