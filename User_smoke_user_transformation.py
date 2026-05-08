"""
User_smoke_user_transformation.py — manual smoke + functional test for the
**User Transformation** tab in the SMILE web UI.

Run this script while the web server (``python web_server.py``) is up on
http://localhost:5601. It mirrors exactly what the browser does when a
user pastes a SMILE script in the Compose tab and clicks Run, by hitting
the same endpoints over HTTP:

  1. POST /api/validate_script  — parse-only check (script syntax)
  2. POST /api/run_script       — full pipeline (parse → apply → export
                                  → 3-layer validation)

The five test cases cover:
  * TEST 1 — a trivial valid script (happy path, validate-only)
  * TEST 2 — a deliberate syntax error (negative, parser error reporting)
  * TEST 3 — a small PG→PG end-to-end migration (happy path, full pipeline)
  * TEST 4 — strict ADD_KEY rule case ④ (no AS + property absent →
             must be rejected and surfaced via Layer 0 + script_failed)
  * TEST 5 — strict ADD_KEY rule case ②b (AS type mismatches existing →
             must reject and point at CAST_PROPERTY in the reason text)

This file is **not** part of the pytest suite — it is a one-off manual
smoke tool kept in the repo so future runs can re-verify the live
end-to-end behaviour of the User Transformation flow without having to
rewrite the request bodies. To run:

    python User_smoke_user_transformation.py
"""
import json
import sys
import urllib.request
import urllib.error


BASE = "http://localhost:5601"


def post(path: str, payload: dict) -> dict:
    """Tiny urllib wrapper — avoids the requests dependency."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"status": resp.status, "json": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "json": {"error": e.read().decode("utf-8")}}
    except Exception as e:
        return {"status": 0, "json": {"error": str(e)}}


def banner(title):
    print()
    print("=" * 70)
    print(" " + title)
    print("=" * 70)


# ── Test 1: validate a trivial script ─────────────────────────────────
banner("TEST 1 — /api/validate_script with the simplest possible script")

simplest = (
    "MIGRATION smoke:1.0\n"
    "FROM RELATIONAL TO RELATIONAL\n"
    "USING smoke_schema VERSION 1\n"
    "ADD_PROPERTY foo TO orders WITH TYPE String\n"
)

r = post("/api/validate_script", {"text": simplest, "syntax": "specific"})
print(f"  HTTP: {r['status']}")
print(f"  ok={r['json'].get('ok')}, errors={r['json'].get('errors')}")


# ── Test 2: validate a deliberately broken script ─────────────────────
banner("TEST 2 — /api/validate_script with a syntax error (negative test)")

broken = "MIGRATION smoke:1.0\nFROM RELATIONAL\nNOT_A_VALID_KEYWORD foo\n"
r = post("/api/validate_script", {"text": broken, "syntax": "specific"})
print(f"  HTTP: {r['status']}")
print(f"  ok={r['json'].get('ok')}")
errs = r["json"].get("errors") or []
print(f"  errors ({len(errs)}):")
for e in errs[:3]:
    print(f"    - {e}")


# ── Test 3: run a tiny end-to-end script (PG → PG) ────────────────────
banner("TEST 3 — /api/run_script with a tiny PG→PG schema (full pipeline)")

# Minimal source: just orders + customers.
mini_pg_source = (
    "CREATE TABLE customers (\n"
    "  customer_id SERIAL PRIMARY KEY,\n"
    "  name VARCHAR(100) NOT NULL\n"
    ");\n"
    "\n"
    "CREATE TABLE orders (\n"
    "  order_id SERIAL PRIMARY KEY,\n"
    "  customer_id INTEGER REFERENCES customers(customer_id),\n"
    "  amount DECIMAL(10,2)\n"
    ");\n"
)

mini_smile = (
    "EVOLUTION smoke:1.0\n"
    "FROM RELATIONAL TO RELATIONAL\n"
    "USING smoke_schema VERSION 1 TO 2\n"
    "ADD_PROPERTY status TO orders WITH TYPE String\n"
    "RENAME_PROPERTY name TO full_name IN customers\n"
)

r = post("/api/run_script", {
    "script": mini_smile,
    "source_text": mini_pg_source,
    "source_db_type": "RELATIONAL",
    "target_db_type": "RELATIONAL",
    "syntax": "specific",
})
print(f"  HTTP: {r['status']}")
j = r["json"]
print(f"  ok={j.get('ok')}, stage={j.get('stage')}")
print(f"  operations_total={j.get('operations_total')} "
      f"applied={j.get('operations_applied')} "
      f"skipped={len(j.get('operations_skipped') or [])} "
      f"errors={len(j.get('operations_errors') or [])}")
print(f"  source_entity_count={j.get('source_entity_count')} "
      f"result_entity_count={j.get('result_entity_count')}")
print(f"  validation_blame={j.get('validation_blame')}")
print(f"  validation_summary={j.get('validation_summary')}")
v0 = j.get("validation_layer0") or {}
print(f"  Layer 0: passed={v0.get('passed')}, summary={v0.get('summary')}")
exp = j.get("exported_target") or ""
if exp:
    print()
    print("  Exported target (first 400 chars):")
    for line in exp[:400].splitlines():
        print(f"    {line}")


# ── Test 4: run a script that triggers our new ADD_KEY rejection ──────
banner("TEST 4 — /api/run_script triggering the new strict ADD_KEY rule (case ④)")

# 'foo' does not exist on customers AND no AS clause → must be rejected
strict_smile = (
    "EVOLUTION smoke:1.0\n"
    "FROM RELATIONAL TO RELATIONAL\n"
    "USING smoke_schema VERSION 1 TO 2\n"
    "ADD_PRIMARY_KEY customers.foo\n"  # ← the offending op
)

r = post("/api/run_script", {
    "script": strict_smile,
    "source_text": mini_pg_source,
    "source_db_type": "RELATIONAL",
    "target_db_type": "RELATIONAL",
    "syntax": "specific",
})
print(f"  HTTP: {r['status']}")
j = r["json"]
print(f"  ok={j.get('ok')}, blame={j.get('validation_blame')}")
v0 = j.get("validation_layer0") or {}
print(f"  Layer 0 passed={v0.get('passed')}")
print(f"  Layer 0 summary: {v0.get('summary')}")
for s in (v0.get("details") or {}).get("failed_steps", []):
    print(f"    Step {s.get('step')} [{s.get('status')}] "
          f"{s.get('original_keyword')}: {s.get('reason')}")


# ── Test 5: run a script that triggers the case ②b rejection ──────────
banner("TEST 5 — /api/run_script triggering case ②b (existing + AS mismatch)")

# customer_id is INTEGER from SERIAL; the script tries AS String → reject
mismatch_smile = (
    "EVOLUTION smoke:1.0\n"
    "FROM RELATIONAL TO RELATIONAL\n"
    "USING smoke_schema VERSION 1 TO 2\n"
    "ADD_PRIMARY_KEY customers.customer_id AS String\n"
)

r = post("/api/run_script", {
    "script": mismatch_smile,
    "source_text": mini_pg_source,
    "source_db_type": "RELATIONAL",
    "target_db_type": "RELATIONAL",
    "syntax": "specific",
})
print(f"  HTTP: {r['status']}")
j = r["json"]
print(f"  blame={j.get('validation_blame')}")
v0 = j.get("validation_layer0") or {}
print(f"  Layer 0 passed={v0.get('passed')}")
for s in (v0.get("details") or {}).get("failed_steps", []):
    print(f"    Step {s.get('step')} [{s.get('status')}] "
          f"{s.get('original_keyword')}: {s.get('reason')}")
