"""
Operation parameter types for SMILE operations.

Each OpType has a dedicated dataclass defining the contract between the
listener (which constructs operations while walking the ANTLR parse tree)
and the transformer handlers (which consume them). Replacing the previous
Dict[str, Any] payload with typed dataclasses turns parser/transformer
contract mismatches into static errors instead of silent runtime skips.

The `clauses` field in a few OpTypes remains a Dict[str, Any]: its nested
structure is itself recursive (AST-like) and a second layer of typed
wrappers would be over-engineering at this stage.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


# ============================================================================
# Structural operations
# ============================================================================

@dataclass
class NestParams:
    source: str
    target: str
    alias: str
    properties: List[str] = field(default_factory=list)
    nested: List[Dict[str, Any]] = field(default_factory=list)
    source_fk: str = ""
    # Currently unused by _handle_nest: listener collects multi-condition
    # JOIN state (NEST ... WHERE a AND b AND c) but the handler consumes
    # only the first condition via source_fk. Kept for future extension.
    join_conditions: List[Dict[str, Any]] = field(default_factory=list)
    target_pk: str = ""


@dataclass
class UnnestParams:
    source_path: str
    target: str
    properties: List[str] = field(default_factory=list)
    nested: List[Dict[str, Any]] = field(default_factory=list)
    carry_fields: List[Dict[str, Any]] = field(default_factory=list)
    # Unused by _handle_unnest; listener-side residue from an older syntax.
    name: Optional[str] = None


@dataclass
class FlattenParams:
    source: str


@dataclass
class UnflattenParams:
    entity: str
    fields: List[str]
    nested_name: str


@dataclass
class WindParams:
    source: str


@dataclass
class UnwindParams:
    mode: str  # "create_table" or "expand_in_place"
    source: str
    target: Optional[str] = None


# ============================================================================
# Entity operations
# ============================================================================

@dataclass
class AddEntityParams:
    name: str
    # list of clause dicts (see _parse_entity_clauses); dict/list shape varies by op
    clauses: List[Dict[str, Any]] = field(default_factory=list)
    source_entity: Optional[str] = None
    target_entity: Optional[str] = None
    cardinality: Optional[str] = None


@dataclass
class DeleteEntityParams:
    name: str


@dataclass
class RenameEntityParams:
    old_name: str
    new_name: Optional[str] = None


@dataclass
class CopyEntityParams:
    source: str
    target: str
    source_entity: Optional[str] = None
    target_entity: Optional[str] = None


# ============================================================================
# Property operations
# ============================================================================

@dataclass
class AddPropertyParams:
    name: str
    entity: Optional[str] = None
    # list of clause dicts (see _parse_property_clauses)
    clauses: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DeletePropertyParams:
    target: str


@dataclass
class RenamePropertyParams:
    old_name: str
    new_name: Optional[str] = None
    entity: Optional[str] = None


@dataclass
class CopyPropertyParams:
    source: str
    target: str


@dataclass
class MovePropertyParams:
    source: str
    target: str


# ============================================================================
# Key / Constraint operations
# ============================================================================

@dataclass
class AddKeyParams:
    key_type: str  # "PRIMARY" | "FOREIGN" | "UNIQUE" | "PARTITION" | "CLUSTERING"
    key_columns: List[str] = field(default_factory=list)
    entity: Optional[str] = None
    data_type: Optional[str] = None
    clauses: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeleteKeyParams:
    key_type: str
    key_columns: List[str] = field(default_factory=list)
    entity: Optional[str] = None


@dataclass
class AddForeignKeyParams:
    field_name: str
    target_table: str
    target_column: str
    entity: Optional[str] = None
    clauses: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeleteForeignKeyParams:
    reference: str


@dataclass
class CastConstraintParams:
    target: str
    constraint_type: str


@dataclass
class CastEntityParams:
    target: str
    entity_kind: str


# ============================================================================
# Embedded operations
# ============================================================================

@dataclass
class AddEmbeddedParams:
    name: str
    entity: Optional[str] = None
    # list of clause dicts (see _parse_embedded_clauses)
    clauses: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DeleteEmbeddedParams:
    embedded: str


# ============================================================================
# Label operations (Graph)
# ============================================================================

@dataclass
class AddLabelParams:
    label: str
    entity: Optional[str] = None


@dataclass
class DeleteLabelParams:
    label: str
    entity: Optional[str] = None


# ============================================================================
# Transformation / cast / cardinality operations
# ============================================================================

@dataclass
class CastPropertyParams:
    target: str
    type: str
    # Unused: listener never produces this, but the handler historically
    # reads params.get("data_type", params.get("type", ...)) as a fallback.
    data_type: Optional[str] = None


@dataclass
class MergeParams:
    source1: str
    source2: str
    target: str
    # Unused by _handle_merge: grammar accepts MERGE a b INTO c AS alias
    # but the alias is currently not applied to the resulting entity.
    alias: Optional[str] = None


@dataclass
class SplitParams:
    source: str
    parts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RecardParams:
    target: str
    cardinality: str


@dataclass
class TransformParams:
    name: str
    target_type: str  # "ENTITY" or "RELATIONSHIP"
    source_entity: Optional[str] = None
    target_entity: Optional[str] = None
    cardinality: Optional[str] = None


# ============================================================================
# Union type alias for Operation.params annotation
# ============================================================================

OpParams = Union[
    NestParams, UnnestParams, FlattenParams, UnflattenParams,
    WindParams, UnwindParams,
    AddEntityParams, DeleteEntityParams, RenameEntityParams, CopyEntityParams,
    AddPropertyParams, DeletePropertyParams, RenamePropertyParams,
    CopyPropertyParams, MovePropertyParams,
    AddKeyParams, DeleteKeyParams,
    AddForeignKeyParams, DeleteForeignKeyParams, CastConstraintParams,
    CastEntityParams,
    AddEmbeddedParams, DeleteEmbeddedParams,
    AddLabelParams, DeleteLabelParams,
    CastPropertyParams, MergeParams, SplitParams,
    RecardParams, TransformParams,
]
