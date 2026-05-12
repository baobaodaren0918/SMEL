"""Emit a SMILE script header (the user writes the operations themselves)."""
from __future__ import annotations


def render_header_only(
    source_db_type: str,
    target_db_type: str,
    kind: str = "auto",         # "migration" | "evolution" | "auto"
    migration_name: str = "generated",
    schema_name: str = "generated_schema",
    version: str = "1.0",
    schema_version_to: str = "2.0",
    syntax: str = "specific",
) -> str:
    """Emit just the SMILE header — the user writes the operations themselves."""
    src = (source_db_type or "").upper()
    tgt = (target_db_type or "").upper()
    if kind == "auto":
        is_evolution = src == tgt
    else:
        is_evolution = (kind == "evolution")
    keyword = "EVOLUTION" if is_evolution else "MIGRATION"
    name = (migration_name or "generated") + ("_evolution" if is_evolution else "_migration")
    using = f"USING {schema_name} VERSION {version}"
    if is_evolution:
        using += f" TO {schema_version_to}"
    lines = [
        f"{keyword} {name}:{version}",
        f"FROM {src} TO {tgt}",
        using,
        "",
        "-- TODO: write your operations below.",
        "",
    ]
    return "\n".join(lines) + "\n"
