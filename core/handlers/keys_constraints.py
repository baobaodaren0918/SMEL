"""Handlers for constraint-aware ops — keys, FKs, labels, cardinality, vertex/edge transforms.

The most internally-coupled handler group. Every method here reads or
writes a UniqueConstraint, ForeignKeyConstraint, edge cardinality, or
graph label, and they share a thick band of private helpers
(``_upsert_key_properties``, ``_remove_key_constraint``,
``_get_target_unique_property_id``, ``_sync_edge_cardinality``). Splitting
this group further would force those helpers into a separate util module
and add cross-imports for marginal benefit.
"""

import logging
from typing import List

from Schema.unified_meta_schema import (
    EntityType, EntityKind, Property,
    UniqueConstraint, ForeignKeyConstraint, UniqueProperty, ForeignKeyProperty, PKTypeEnum,
    CheckConstraint, ExistenceConstraint,
    Reference, Edge, Cardinality,
    PrimitiveDataType, PrimitiveType,
    CARDINALITY_MAP, KEY_TYPE_MAP, TYPE_STR_MAP,
)
from parser.params import (
    OperationResult,
    AddKeyParams, DeleteKeyParams,
    AddForeignKeyParams, DeleteForeignKeyParams, CastConstraintParams,
    AddConstraintParams, DeleteConstraintParams, ConstraintBodyKind,
    AddLabelParams, DeleteLabelParams,
    RecardParams, TransformParams,
)
from parser.listeners import OpType
from core.transformer import register_handler

logger = logging.getLogger(__name__)



class KeysConstraintsHandlersMixin:
    """Mixin contributing one focused subset of `_handle_*` methods to ``SchemaTransformer``."""

    @register_handler(OpType.DELETE_FOREIGN_KEY)
    def _handle_delete_foreign_key(self, params: DeleteForeignKeyParams) -> OperationResult:
        entity_name, ref_name = self._split_path(params.reference)
        entity = self._get_entity(entity_name) if entity_name else None
        if entity:
            # Remove the Reference relationship
            entity.remove_relationship(ref_name)
            # Also remove the matching ForeignKeyConstraint from entity.constraints
            # (matches SQL semantics: DROP CONSTRAINT removes FK but keeps the column)
            fk_attr = entity.get_property(ref_name)
            if fk_attr:
                entity.constraints = [
                    c for c in entity.constraints
                    if not (c.kind == "foreign_key" and
                            any(fkp.property_id == fk_attr.meta_id for fkp in c.foreign_key_properties))
                ]
            self._touch(entity_name)
            self.changes.append(f"DELETE_FOREIGN_KEY:{entity_name}.{ref_name}")
            return OperationResult.ok()
        return OperationResult.skipped("delete_foreign_key: precondition not met")

    @register_handler(OpType.ADD_FOREIGN_KEY)
    def _handle_add_foreign_key(self, params: AddForeignKeyParams) -> OperationResult:
        """ADD_FOREIGN_KEY <columns> [TO entity] REFERENCES target(<columns>).

        Single-column FKs (length-1 lists) keep their long-standing layout —
        one ``Reference`` relationship plus one ``ForeignKeyConstraint``
        carrying one ``ForeignKeyProperty``. Composite FKs (length>1) emit
        one ``Reference`` *per* source column (each column individually points
        at the same target entity) but bundle every column into a *single*
        ``ForeignKeyConstraint``: that single constraint with N matched
        ``ForeignKeyProperty`` entries is what makes it "composite" (vs N
        independent FKs that would have N separate constraints).
        """
        field_names = params.field_names
        target_table = params.target_table
        target_columns = params.target_columns
        entity_name = params.entity

        if not entity_name or not field_names or not target_table or not target_columns:
            return OperationResult.skipped("add_foreign_key: precondition not met")

        entity = self._get_entity(entity_name, "ADD_FOREIGN_KEY")
        if not entity:
            return OperationResult.skipped("add_foreign_key: precondition not met")

        target_entity = self._get_entity(target_table)

        # Cardinality applies to the FK as a whole, not to individual columns.
        cardinality = Cardinality.ONE_TO_ONE
        clauses = params.clauses
        if 'cardinality' in clauses:
            cardinality = CARDINALITY_MAP.get(clauses['cardinality'], Cardinality.ONE_TO_ONE)

        fk_props: List[ForeignKeyProperty] = []
        for src_col, tgt_col in zip(field_names, target_columns):
            # Resolve the FK property's data type from the target column when
            # available; default to INTEGER otherwise (matches the original
            # behaviour for unknown targets).
            fk_type = PrimitiveDataType(PrimitiveType.INTEGER)
            if target_entity:
                tgt_attr = target_entity.get_property(tgt_col)
                if tgt_attr is not None:
                    fk_type = tgt_attr.data_type
                else:
                    target_pk = target_entity.get_primary_key()
                    if target_pk and target_pk.unique_properties:
                        pk_attr = target_entity.get_property_by_id(target_pk.unique_properties[0].property_id)
                        if pk_attr:
                            fk_type = pk_attr.data_type

            if not entity.get_property(src_col):
                entity.add_property(Property(src_col, fk_type, False, True))

            existing_ref = next(
                (r for r in entity.relationships
                 if isinstance(r, Reference) and r.ref_name == src_col),
                None,
            )
            if existing_ref:
                existing_ref.refs_to = target_table
                existing_ref.cardinality = cardinality
                # ADD_FOREIGN_KEY always produces an *enforced* reference. If
                # the existing Reference came from a previous logical-only
                # declaration (e.g. parsed from a Mongo cross-collection
                # description, or set by ADD_CONSTRAINT REFERENCE LOGICAL),
                # this op upgrades it. Without this flip the FKConstraint
                # below would be created on top of a Reference still flagged
                # as logical, leaving the meta model in an inconsistent
                # "FK enforcement enabled but Reference still labelled
                # logical" state.
                existing_ref.is_enforced = True
            else:
                entity.add_relationship(Reference(
                    ref_name=src_col, refs_to=target_table,
                    cardinality=cardinality, is_optional=not cardinality.is_required(),
                ))

            fk_attr = entity.get_property(src_col)
            if fk_attr and cardinality.is_required():
                fk_attr.is_optional = False

            if fk_attr:
                target_up_id = self._get_target_unique_property_id(target_table, tgt_col)
                fk_props.append(ForeignKeyProperty(
                    property_id=fk_attr.meta_id,
                    points_to_unique_property_id=target_up_id,
                ))

        # One ForeignKeyConstraint per ADD_FOREIGN_KEY call — collects every
        # (src_col, tgt_col) pair as a ForeignKeyProperty entry. Skip if a
        # constraint covering exactly these source columns already exists,
        # to keep the operation idempotent.
        existing_property_id_sets = [
            {fkp.property_id for fkp in c.foreign_key_properties}
            for c in entity.constraints if c.kind == "foreign_key"
        ]
        new_property_ids = {fp.property_id for fp in fk_props}
        if fk_props and new_property_ids not in existing_property_id_sets:
            entity.add_constraint(ForeignKeyConstraint(
                is_managed=True, foreign_key_properties=fk_props,
            ))

        self._touch(entity_name)
        # Change description: name the columns for diff readability.
        cols_str = ",".join(field_names) if len(field_names) > 1 else field_names[0]
        self.changes.append(f"ADD_REF:{entity_name}.{cols_str}")
        return OperationResult.ok()

    # ------------------------------------------------------------------
    # ADD_CONSTRAINT / DELETE_CONSTRAINT
    # ------------------------------------------------------------------
    # ADD_CONSTRAINT covers the constraint kinds NOT addressed by the narrow
    # operators (PK / UNIQUE / FK / PARTITION / CLUSTERING / LABEL):
    #   * REFERENCE LOGICAL  -> Reference(is_enforced=False) — non-enforced
    #     cross-entity reference (Mongo cross-collection, Cass denormalised
    #     columns, self-references). The enforced FK case is intentionally
    #     not covered here: ``ADD_FOREIGN_KEY`` is the SQL-traditional path
    #     and the only one that supports composite multi-column FKs.
    #   * CHECK <expr>       -> CheckConstraint(expression=<AST>, target_property_id=<id>)
    #   * EXISTENCE          -> Property.is_optional=False (+ ExistenceConstraint marker)
    # DELETE_CONSTRAINT inspects the entity at ``entity.field`` and removes
    # whichever logical Reference / CheckConstraint / ExistenceConstraint
    # is currently anchored there.

    @register_handler(OpType.ADD_CONSTRAINT)
    def _handle_add_constraint(self, params: AddConstraintParams) -> OperationResult:
        """Dispatcher for ADD_CONSTRAINT. Delegates to a body-kind-specific
        sub-handler depending on whether the user wrote AS REFERENCE / CHECK
        / EXISTENCE."""
        if params.body_kind == ConstraintBodyKind.REFERENCE:
            return self._handle_add_constraint_reference(params)
        if params.body_kind == ConstraintBodyKind.CHECK:
            return self._handle_add_constraint_check(params)
        if params.body_kind == ConstraintBodyKind.EXISTENCE:
            return self._handle_add_constraint_existence(params)
        return OperationResult.skipped(
            f"add_constraint: unknown body kind {params.body_kind!r}")

    def _handle_add_constraint_reference(self, params: AddConstraintParams) -> OperationResult:
        """ADD_CONSTRAINT entity.field AS REFERENCE LOGICAL TO target(col).

        Creates a single ``Reference(is_enforced=False)`` on the source entity
        — a logical (non-enforced) cross-entity reference. No
        ``ForeignKeyConstraint`` is created (that path belongs to
        ``ADD_FOREIGN_KEY``, which is also the only operator that supports
        composite multi-column FKs).

        If an existing Reference is already present for this column, this op
        upserts it: refs_to and cardinality are updated and ``is_enforced``
        is forced back to ``False``. This makes ``ADD_CONSTRAINT REFERENCE
        LOGICAL`` a clean "downgrade enforced -> logical" path; any FK
        constraint covering the same column is also dropped to keep the
        meta-model state consistent with the new logical-only intent.
        """
        entity_name, field_name = self._split_path(params.target)
        if not entity_name or not field_name:
            return OperationResult.skipped(
                "add_constraint: target must be entity.field")
        entity = self._get_entity(entity_name, "ADD_CONSTRAINT")
        if not entity:
            return OperationResult.skipped(
                "add_constraint: precondition not met")
        target_table = params.ref_target_table
        target_columns = params.ref_target_columns
        if not target_table or not target_columns:
            return OperationResult.skipped(
                "add_constraint: REFERENCE body needs target table and columns")
        target_entity = self._get_entity(target_table)

        # Resolve the source-property data type. Carry the target property's
        # type if available so the meta model is consistent with the
        # equivalent ADD_FOREIGN_KEY behaviour.
        fk_type = PrimitiveDataType(PrimitiveType.INTEGER)
        if target_entity:
            tgt_attr = target_entity.get_property(target_columns[0])
            if tgt_attr is not None:
                fk_type = tgt_attr.data_type
            else:
                target_pk = target_entity.get_primary_key()
                if target_pk and target_pk.unique_properties:
                    pk_attr = target_entity.get_property_by_id(
                        target_pk.unique_properties[0].property_id)
                    if pk_attr:
                        fk_type = pk_attr.data_type

        cardinality = Cardinality.ONE_TO_ONE
        if params.ref_cardinality:
            cardinality = CARDINALITY_MAP.get(
                params.ref_cardinality, Cardinality.ONE_TO_ONE)

        # Ensure the source property exists.
        if not entity.get_property(field_name):
            entity.add_property(Property(field_name, fk_type, False, True))

        # Mirror the cardinality's required-ness onto the source property's
        # ``is_optional``. The Reference itself records cardinality, but the
        # Mongo / PG adapters read ``Property.is_optional`` to decide whether
        # the column appears in ``required[]`` / carries ``NOT NULL``. Without
        # this propagation, an ADD_CONSTRAINT REFERENCE WITH CARDINALITY
        # ONE_TO_* would silently leave the property nullable.
        src_attr = entity.get_property(field_name)
        if src_attr is not None:
            src_attr.is_optional = not cardinality.is_required()

        # Upsert the Reference. If one already exists for this column,
        # update its target / cardinality and force ``is_enforced=False``
        # so this op cleanly downgrades a previously-enforced reference.
        existing_ref = next(
            (r for r in entity.relationships
             if isinstance(r, Reference) and r.ref_name == field_name),
            None,
        )
        if existing_ref:
            existing_ref.refs_to = target_table
            existing_ref.cardinality = cardinality
            existing_ref.is_enforced = False
        else:
            entity.add_relationship(Reference(
                ref_name=field_name,
                refs_to=target_table,
                cardinality=cardinality,
                is_optional=not cardinality.is_required(),
                is_enforced=False,
            ))

        # Drop any FK constraint covering this column — logical-only state.
        fk_attr = entity.get_property(field_name)
        if fk_attr is not None:
            entity.constraints = [
                c for c in entity.constraints
                if not (c.kind == "foreign_key"
                        and any(fkp.property_id == fk_attr.meta_id
                                for fkp in c.foreign_key_properties))
            ]

        self._touch(entity_name)
        self.changes.append(
            f"ADD_CONSTRAINT:{entity_name}.{field_name}=REFERENCE_LOGICAL->"
            f"{target_table}({target_columns[0]})")
        return OperationResult.ok()

    def _handle_add_constraint_check(self, params: AddConstraintParams) -> OperationResult:
        """ADD_CONSTRAINT entity.field AS CHECK <expr>.

        Anchors the CheckConstraint to the named property's meta_id so
        DELETE_CONSTRAINT can locate it later by qualified name. The CHECK
        expression itself may reference multiple properties of the entity;
        the anchor only controls which property the constraint is *attached
        to* in the meta model."""
        entity, field_name = self._resolve_entity_attr(
            params.target, "ADD_CONSTRAINT")
        if not entity or not field_name:
            return OperationResult.skipped(
                "add_constraint: precondition not met")
        anchor_attr = entity.get_property(field_name)
        if anchor_attr is None:
            return OperationResult.skipped(
                f"add_constraint: anchor property {params.target!r} not found")

        entity.add_constraint(CheckConstraint(
            expression=params.check_expression,
            target_property_id=anchor_attr.meta_id,
        ))
        self._touch(entity.full_path)
        self.changes.append(
            f"ADD_CONSTRAINT:{params.target}=CHECK")
        return OperationResult.ok()

    def _handle_add_constraint_existence(self, params: AddConstraintParams) -> OperationResult:
        """ADD_CONSTRAINT entity.field AS EXISTENCE.

        Sets the property's ``is_optional`` flag to ``False`` (the in-memory
        equivalent of NOT NULL) and records an ExistenceConstraint marker so
        the meta model can express "constraint added post-hoc" distinctly
        from "property declared NOT NULL on creation"."""
        entity, field_name = self._resolve_entity_attr(
            params.target, "ADD_CONSTRAINT")
        if not entity or not field_name:
            return OperationResult.skipped(
                "add_constraint: precondition not met")
        attr = entity.get_property(field_name)
        if attr is None:
            return OperationResult.skipped(
                f"add_constraint: property {params.target!r} not found")
        attr.is_optional = False

        already = any(
            c.kind == "existence" and c.target_property_id == attr.meta_id
            for c in entity.constraints
        )
        if not already:
            entity.add_constraint(ExistenceConstraint(
                target_property_id=attr.meta_id,
            ))
        self._touch(entity.full_path)
        self.changes.append(f"ADD_CONSTRAINT:{params.target}=EXISTENCE")
        return OperationResult.ok()

    @register_handler(OpType.DELETE_CONSTRAINT)
    def _handle_delete_constraint(self, params: DeleteConstraintParams) -> OperationResult:
        """DELETE_CONSTRAINT entity.field.

        Removes whichever ADD_CONSTRAINT-produced object is currently anchored
        at the named property — in priority order: a logical Reference (the
        Reference.ref_name == field_name and is_enforced=False), a
        CheckConstraint with target_property_id == property.meta_id, or an
        ExistenceConstraint (which also restores ``is_optional=True``).

        Constraints from the narrow operators (PK / FK / UNIQUE / PARTITION
        / CLUSTERING / LABEL) are NOT deleted by this handler; use
        DELETE_PRIMARY_KEY / DELETE_FOREIGN_KEY / etc. for those.
        """
        entity, field_name = self._resolve_entity_attr(
            params.target, "DELETE_CONSTRAINT")
        if not entity or not field_name:
            return OperationResult.skipped(
                "delete_constraint: precondition not met")

        removed_kinds = []

        # 1. Logical references (Reference.is_enforced == False).
        new_relationships = []
        for rel in entity.relationships:
            if (isinstance(rel, Reference)
                    and rel.ref_name == field_name
                    and rel.is_enforced is False):
                removed_kinds.append("REFERENCE_LOGICAL")
                continue
            new_relationships.append(rel)
        entity.relationships = new_relationships

        # 2. CheckConstraint and ExistenceConstraint anchored to this property.
        attr = entity.get_property(field_name)
        if attr is not None:
            anchor_id = attr.meta_id
            kept = []
            for c in entity.constraints:
                if c.kind == "check" and c.target_property_id == anchor_id:
                    removed_kinds.append("CHECK")
                    continue
                if c.kind == "existence" and c.target_property_id == anchor_id:
                    removed_kinds.append("EXISTENCE")
                    # Restore is_optional default — symmetric with how the
                    # EXISTENCE handler set it to False.
                    attr.is_optional = True
                    continue
                kept.append(c)
            entity.constraints = kept

        if not removed_kinds:
            return OperationResult.skipped(
                f"delete_constraint: no ADD_CONSTRAINT object anchored at "
                f"{params.target!r}")

        self._touch(entity.full_path)
        self.changes.append(
            f"DELETE_CONSTRAINT:{params.target}={'+'.join(removed_kinds)}")
        return OperationResult.ok()

    @register_handler(OpType.DELETE_KEY)
    def _handle_delete_key(self, params: DeleteKeyParams) -> OperationResult:
        """DELETE PRIMARY/FOREIGN/UNIQUE KEY - destructive removal"""
        return self._remove_key_constraint(params, operation="DELETE")

    @register_handler(OpType.ADD_KEY)
    def _handle_add_key(self, params: AddKeyParams) -> OperationResult:
        """ADD KEY id AS String — or ADD PRIMARY KEY (id1, id2) TO Customer (composite)."""
        entity_name = params.entity
        key_columns = params.key_columns
        if not key_columns:
            return OperationResult.skipped("add_key: precondition not met")

        key_data_type = (
            PrimitiveDataType(TYPE_STR_MAP.get(params.data_type.upper(), PrimitiveType.STRING))
            if params.data_type
            else PrimitiveDataType(PrimitiveType.INTEGER)
        )

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity:
            logger.info(f"ADD_KEY: entity '{entity_name}' not found, auto-creating")
            entity = EntityType(object_name=[entity_name] if entity_name else ["unnamed"])
            self.database.add_entity_type(entity)

        key_attrs, reject_reason = self._upsert_key_properties(
            entity, key_columns, key_data_type, bool(params.data_type)
        )
        # Strict explicit-type rule — ``_upsert_key_properties`` returns a
        # non-None ``reject_reason`` when the script tries to (a) name a
        # property that does not exist *without* declaring its type via
        # AS, or (b) re-declare an existing property's type with a
        # different value. Both cases used to silently mutate the meta
        # model (silent INTEGER fallback / silent type rewrite); we now
        # surface them as user-facing ``OperationResult.skipped`` so
        # Layer 0 reports them with an actionable next step.
        if reject_reason:
            return OperationResult.skipped(reject_reason)
        key_type_str, pk_type_enum = self._resolve_pk_type(params.key_type)
        constraint = self._build_key_constraint(
            key_attrs, key_type_str, pk_type_enum, params.clauses
        )

        # For PK constraints, Cassandra PARTITION/CLUSTERING may append to an
        # existing PK (and short-circuit this handler), while a regular PK
        # replaces any existing one. FK / UNIQUE just get added at the end.
        if constraint.kind == "unique" and constraint.is_primary_key:
            if self._append_to_existing_pk(entity, constraint, pk_type_enum):
                self._touch(entity_name)
                self.changes.append(f"ADD_KEY:{entity_name}.({', '.join(key_columns)})")
                return OperationResult.ok()
            if pk_type_enum == PKTypeEnum.SIMPLE:
                self._clear_existing_pk(entity, key_columns)

        entity.add_constraint(constraint)
        self._touch(entity_name)
        self.changes.append(f"ADD_KEY:{entity_name}.({', '.join(key_columns)})")
        return OperationResult.ok()

    def _upsert_key_properties(self, entity, key_columns, key_data_type, data_type_explicit):
        """Look up or create a Property for each member of a (possibly
        composite) key, enforcing the strict explicit-type rule.

        Decision matrix on ``(property exists?, AS provided?)``:

        * **(exists, no AS)** — case ①: promote to key, keep existing type.
        * **(exists, AS matches)** — case ②a: AS is redundant; keep existing
          type unchanged. The AS is silently accepted because re-declaring
          the same type is harmless.
        * **(exists, AS differs)** — case ②b: REJECT. Silent rewrite of an
          existing property's type is the worst-possible outcome (it
          changes meta-model semantics without the user seeing it). Return
          a non-None reason; the caller surfaces it as a Layer 0 skip.
        * **(absent, AS provided)** — case ③: create the property with the
          declared type.
        * **(absent, no AS)** — case ④: REJECT. The previous default-INTEGER
          fallback caused cross-paradigm divergence (the contact_id incident
          documented in N5-1: Cassandra evolution silently created INTEGER
          while the relational counterpart used VARCHAR). Forcing an
          explicit declaration eliminates that whole class of silent bug.

        Returns ``(key_attrs, None)`` on success, or ``([], reason)`` on
        rejection — the caller decides how to surface the rejection.
        Wording in the reasons is paradigm-neutral ("property" rather than
        "column") so the same handler serves all four database paradigms.
        """
        key_attrs = []
        for col_name in key_columns:
            attr = entity.get_property(col_name)
            if not attr:
                # Property does not exist — case ③ or case ④.
                if not data_type_explicit:
                    # Case ④: silent INTEGER fallback would invent a type.
                    # Refuse rather than guess; tell the user the two
                    # explicit paths that resolve the situation.
                    return [], (
                        f"property '{col_name}' does not exist on "
                        f"'{entity.name}'; ADD_KEY requires either an "
                        f"explicit type via 'AS <Type>' or a preceding "
                        f"'ADD_PROPERTY {col_name} TO {entity.name} "
                        f"WITH TYPE <Type>'"
                    )
                # Case ③: create with the explicitly declared type.
                attr = Property(col_name, key_data_type, True, False)
                entity.add_property(attr)
            else:
                # Property exists — case ① (no AS) or case ② (AS provided).
                if data_type_explicit:
                    # Case ②: AS clause given on a property that already
                    # has a type. Compare to detect silent rewrite.
                    old_primitive = (
                        attr.data_type.primitive_type.value
                        if hasattr(attr.data_type, 'primitive_type')
                        else 'unknown'
                    )
                    new_primitive = (
                        key_data_type.primitive_type.value
                        if hasattr(key_data_type, 'primitive_type')
                        else 'unknown'
                    )
                    if old_primitive != new_primitive:
                        # Case ②b: types differ. Refuse the silent rewrite
                        # and point the user at CAST_PROPERTY — the only
                        # operator whose job is to change a property's type.
                        # The error message includes the literal command
                        # they need so they can copy-paste the fix.
                        return [], (
                            f"property '{entity.name}.{col_name}' already "
                            f"exists with type '{old_primitive}'; the AS "
                            f"clause requested '{new_primitive}'. ADD_KEY "
                            f"does not change property types — use "
                            f"'CAST_PROPERTY {entity.name}.{col_name} TO "
                            f"<Type>' first if you intended to change the "
                            f"type."
                        )
                    # Case ②a: types match. AS is redundant but harmless;
                    # do not rewrite ``attr.data_type`` (no-op preserves
                    # any extra type metadata like max_length / precision
                    # that the AS form would lose).
                # Case ① / ②a: promote to key without touching data_type.
                attr.is_key = True
                attr.is_optional = False
            key_attrs.append(attr)
        return key_attrs, None

    def _resolve_pk_type(self, key_type_param):
        """Translate the SMILE key_type string into (sql_kind, PKTypeEnum).

        PARTITION/CLUSTERING are Cassandra-specific variants of PRIMARY, so
        their sql_kind folds to "primary" and the distinction survives only
        in PKTypeEnum. Every other key_type yields PKTypeEnum.SIMPLE.
        """
        mapped = KEY_TYPE_MAP.get(key_type_param, "primary")
        if isinstance(mapped, PKTypeEnum):
            return "primary", mapped
        return mapped, PKTypeEnum.SIMPLE

    def _build_key_constraint(self, key_attrs, key_type_str, pk_type_enum, clauses):
        """Construct a ForeignKeyConstraint or UniqueConstraint from resolved
        key info. `clauses` is the dict produced by `_parse_key_clauses`
        and may carry a REFERENCES sub-dict for FK definitions.
        """
        if key_type_str == "foreign":
            references = (clauses or {}).get("references", {})
            ref_entity_name = references.get("table")
            ref_attrs = references.get("columns", [])
            fk_props = []
            for i, attr in enumerate(key_attrs):
                target_attr = ref_attrs[i] if i < len(ref_attrs) else (ref_attrs[0] if ref_attrs else "")
                target_up_id = self._get_target_unique_property_id(ref_entity_name, target_attr)
                fk_props.append(ForeignKeyProperty(
                    property_id=attr.meta_id,
                    points_to_unique_property_id=target_up_id,
                ))
            return ForeignKeyConstraint(is_managed=True, foreign_key_properties=fk_props)

        unique_props = [
            UniqueProperty(primary_key_type=pk_type_enum, property_id=attr.meta_id)
            for attr in key_attrs
        ]
        return UniqueConstraint(
            is_primary_key=(key_type_str == "primary"),
            is_managed=True,
            unique_properties=unique_props,
        )

    def _append_to_existing_pk(self, entity, constraint, pk_type_enum):
        """If the new key is a Cassandra PARTITION/CLUSTERING column and the
        entity already has a primary-key constraint, append the new columns
        to it (skipping duplicates) and return True so the caller skips the
        usual `entity.add_constraint` step. Otherwise return False.
        """
        if pk_type_enum not in (PKTypeEnum.PARTITION, PKTypeEnum.CLUSTERING):
            return OperationResult.skipped("add_key: precondition not met")
        existing_pk = next(
            (c for c in entity.constraints
             if c.kind == "unique" and c.is_primary_key),
            None,
        )
        if not existing_pk:
            return OperationResult.skipped("add_key: precondition not met")
        existing_ids = {up.property_id for up in existing_pk.unique_properties}
        for up in constraint.unique_properties:
            if up.property_id not in existing_ids:
                existing_pk.unique_properties.append(up)
        return OperationResult.ok()

    def _clear_existing_pk(self, entity, incoming_key_columns):
        """Drop any existing primary-key constraint and strip `is_key` from
        every old PK property that is NOT in the new key column set.

        ``is_optional`` is intentionally left untouched. Auto-restoring it
        to True would silently turn a previously-NOT-NULL property into
        nullable on PK demotion — a hidden semantic decision that loses
        the explicit constraint a PG / Mongo source may have carried (and
        that has no SMILE op to revert). Users who genuinely want the
        post-demotion property to be nullable should declare that
        explicitly via ``ADD_CONSTRAINT field AS EXISTENCE`` followed by
        ``DELETE_CONSTRAINT field``; Layer 1 NOTICEs flag the cases where
        such an explicit decision was not made so the user can act on
        them rather than have the handler decide on their behalf.
        """
        for old_c in entity.constraints:
            if old_c.kind == "unique" and old_c.is_primary_key:
                for up in old_c.unique_properties:
                    old_attr = entity.get_property_by_id(up.property_id)
                    if old_attr and old_attr.name not in incoming_key_columns:
                        old_attr.is_key = False
        entity.constraints = [
            c for c in entity.constraints
            if not (c.kind == "unique" and c.is_primary_key)
        ]

    def _get_target_unique_property_id(self, target_entity_name: str, target_attr_name: str) -> str:
        """Get the UniqueProperty meta_id for a target entity's property (for FK references)."""
        if not target_entity_name:
            return ""
        target_entity = self.database.get_entity_type(target_entity_name)
        if not target_entity:
            return ""
        target_pk = target_entity.get_primary_key()
        if not target_pk or not target_pk.unique_properties:
            return ""
        # If target_attr_name is specified, find matching UniqueProperty
        if target_attr_name:
            for up in target_pk.unique_properties:
                attr = target_entity.get_property_by_id(up.property_id)
                if attr and attr.name == target_attr_name:
                    return up.meta_id
        # Default to first UniqueProperty
        return target_pk.unique_properties[0].meta_id

    def _remove_key_constraint(self, params: DeleteKeyParams, operation: str = "DELETE") -> bool:
        """Helper method for DELETE_KEY operations"""
        entity_name = params.entity
        key_columns = params.key_columns  # List of column names
        key_type_str = KEY_TYPE_MAP.get(params.key_type, "primary")

        entity = self.database.get_entity_type(entity_name) if entity_name else None
        if not entity or not key_columns:
            return OperationResult.skipped("add_key: precondition not met")

        key_columns_set = set(key_columns)

        for constraint in list(entity.constraints):
            if key_type_str == "foreign" and constraint.kind == "foreign_key":
                # Check if all FK columns match
                fk_attr_names = set()
                for fk_prop in constraint.foreign_key_properties:
                    fk_attr = entity.get_property_by_id(fk_prop.property_id)
                    if fk_attr:
                        fk_attr_names.add(fk_attr.name)
                if fk_attr_names == key_columns_set:
                    entity.constraints.remove(constraint)
                    for fk_prop in constraint.foreign_key_properties:
                        fk_attr = entity.get_property_by_id(fk_prop.property_id)
                        if fk_attr:
                            fk_attr.is_key = False
                    key_names_str = ", ".join(key_columns)
                    self.changes.append(f"{operation}_KEY:{entity_name}.({key_names_str})")
                    return OperationResult.ok()

            elif key_type_str in ("primary", "unique") and constraint.kind == "unique":
                is_primary = (key_type_str == "primary")
                if constraint.is_primary_key == is_primary:
                    # Check if all constraint columns match
                    constraint_attr_names = set()
                    for up in constraint.unique_properties:
                        up_attr = entity.get_property_by_id(up.property_id)
                        if up_attr:
                            constraint_attr_names.add(up_attr.name)
                    if constraint_attr_names == key_columns_set:
                        entity.constraints.remove(constraint)
                        for up in constraint.unique_properties:
                            up_attr = entity.get_property_by_id(up.property_id)
                            if up_attr:
                                up_attr.is_key = False
                        key_names_str = ", ".join(key_columns)
                        self.changes.append(f"{operation}_KEY:{entity_name}.({key_names_str})")
                        return OperationResult.ok()

            elif isinstance(key_type_str, PKTypeEnum) and constraint.kind == "unique":
                # Cassandra PARTITION/CLUSTERING keys: remove matching properties
                removed_any = False
                for up in list(constraint.unique_properties):
                    if up.primary_key_type == key_type_str:
                        up_attr = entity.get_property_by_id(up.property_id)
                        if up_attr and up_attr.name in key_columns_set:
                            constraint.unique_properties.remove(up)
                            up_attr.is_key = False
                            # In Cassandra, the only way for a column to be
                            # non-null is to be part of the partition or
                            # clustering key. Removing it from the key must
                            # therefore restore is_optional=True, mirroring
                            # ADD_KEY's symmetric is_optional=False on
                            # promotion. A subsequent SMILE op (ADD_KEY,
                            # ADD_FOREIGN_KEY, ADD_CONSTRAINT REFERENCE with
                            # required cardinality) is responsible for
                            # re-asserting non-null if intended.
                            up_attr.is_optional = True
                            removed_any = True
                if removed_any:
                    key_names_str = ", ".join(key_columns)
                    self.changes.append(f"{operation}_KEY:{entity_name}.({key_names_str})")
                    if not constraint.unique_properties:
                        entity.constraints.remove(constraint)
                    self._touch(entity_name)
                    return OperationResult.ok()
        return OperationResult.skipped("add_key: precondition not met")

    @register_handler(OpType.DELETE_LABEL)
    def _handle_delete_label(self, params: DeleteLabelParams) -> OperationResult:
        """DELETE LABEL Vendor FROM suppliers (graph database)"""
        label = params.label
        entity_name = params.entity

        entity = self._get_entity(entity_name, "DELETE_LABEL") if entity_name else None
        if not entity:
            return OperationResult.skipped("delete_label: precondition not met")

        if label in entity.labels:
            entity.labels.remove(label)
        self._touch(entity_name)
        self.changes.append(f"DELETE_LABEL:{entity_name}.{label}")
        return OperationResult.ok()

    @register_handler(OpType.ADD_LABEL)
    def _handle_add_label(self, params: AddLabelParams) -> OperationResult:
        """ADD LABEL Vendor TO suppliers (graph database)"""
        label = params.label
        entity_name = params.entity

        entity = self._get_entity(entity_name, "ADD_LABEL") if entity_name else None
        if not entity or not label:
            return OperationResult.skipped("add_label: precondition not met")

        if label not in entity.labels:
            entity.labels.append(label)
        self._touch(entity_name)
        self.changes.append(f"ADD_LABEL:{entity_name}.{label}")
        return OperationResult.ok()

    @register_handler(OpType.CAST_CONSTRAINT)
    def _handle_cast_constraint(self, params: CastConstraintParams) -> OperationResult:
        """CAST_CONSTRAINT: Change the type of a constraint.

        Reference: Orion "Cast Reference" - change the type of a constraint.
        Example: CAST_CONSTRAINT customers.email TO UNIQUE KEY
        Example: CAST_CONSTRAINT customers.city TO PARTITION KEY
        """
        target = params.target
        new_type = params.constraint_type  # PRIMARY_KEY, UNIQUE_KEY, PARTITION_KEY, CLUSTERING_KEY, NODE_KEY, DOCUMENT_ID

        entity, attr_name = self._resolve_entity_attr(target)
        if not entity:
            return OperationResult.skipped("cast_constraint: precondition not met")

        # Find the property
        attr = entity.get_property(attr_name)
        if not attr:
            return OperationResult.skipped("cast_constraint: precondition not met")

        # Find constraint containing this property and modify its type
        for constraint in entity.constraints:
            if constraint.kind == "unique":
                for up in constraint.unique_properties:
                    if up.property_id == attr.meta_id:
                        if new_type == "PRIMARY_KEY":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.SIMPLE
                        elif new_type == "UNIQUE_KEY":
                            constraint.is_primary_key = False
                        elif new_type == "PARTITION_KEY":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.PARTITION
                        elif new_type == "CLUSTERING_KEY":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.CLUSTERING
                        elif new_type == "NODE_KEY":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.NODE_KEY
                        elif new_type == "DOCUMENT_ID":
                            constraint.is_primary_key = True
                            up.primary_key_type = PKTypeEnum.DOCUMENT_ID
                        self._touch(entity.name)
                        self.changes.append(f"CAST_CONSTRAINT:{target}->{new_type}")
                        return OperationResult.ok()
        return OperationResult.skipped("cast_constraint: precondition not met")

    @register_handler(OpType.RECARD)
    def _handle_recard(self, params: RecardParams) -> OperationResult:
        """RECARD: Change the multiplicity/cardinality of a reference.

        Reference: Orion "Mult Reference" - change the multiplicity of a reference.
        Example: RECARD orders.customer_id TO ONE_TO_MANY
        """
        target = params.target
        new_cardinality_str = params.cardinality

        entity, ref_name = self._resolve_entity_attr(target)
        if not entity:
            return OperationResult.skipped("recard: precondition not met")

        new_cardinality = CARDINALITY_MAP.get(new_cardinality_str, None)
        if not new_cardinality:
            return OperationResult.skipped("recard: precondition not met")

        # Find the reference relationship and update its cardinality
        for rel in entity.relationships:
            if isinstance(rel, Reference) and rel.ref_name == ref_name:
                rel.cardinality = new_cardinality
                self._touch(entity.name)
                self.changes.append(f"RECARD:{target}->{new_cardinality_str}")
                return OperationResult.ok()
            elif isinstance(rel, Edge) and rel.rel_type_name == ref_name:
                # Edge cardinality is duplicated on the EDGE entity and on the
                # Edge relationship object; sync both via helper so they
                # cannot drift apart.
                self._sync_edge_cardinality(ref_name, new_cardinality)
                self._touch(entity.name, ref_name)
                self.changes.append(f"RECARD:{target}->{new_cardinality_str}")
                return OperationResult.ok()
        return OperationResult.skipped("recard: precondition not met")

    def _sync_edge_cardinality(self, edge_name: str, new_cardinality: Cardinality) -> None:
        """Keep the cardinality of an EDGE consistent across its two storage sites.

        An edge's cardinality is duplicated in the data model: once on the
        EDGE entity itself (`entity.edge_cardinality`) and once on the `Edge`
        relationship object sitting in the source entity's `relationships`
        list. This helper writes both so the two never drift apart.
        """
        edge_entity = self.database.get_entity_type(edge_name)
        if not edge_entity or edge_entity.entity_kind != EntityKind.EDGE:
            return
        edge_entity.edge_cardinality = new_cardinality
        if edge_entity.source_entity:
            source_ent = self.database.get_entity_type(edge_entity.source_entity)
            if source_ent:
                for rel in source_ent.relationships:
                    if isinstance(rel, Edge) and rel.rel_type_name == edge_name:
                        rel.cardinality = new_cardinality
                        break

    @register_handler(OpType.TRANSFORM)
    def _handle_transform(self, params: TransformParams) -> OperationResult:
        """TRANSFORM: Convert between entity (node) and relationship type (edge).

        Based on Hausler et al. - nodeToRel / relToNode graph evolution operations.

        TO RELATIONSHIP: EntityType (VERTEX) -> EntityType (EDGE)
          - Changes entity_kind to EDGE, sets source/target
          - Adds Edge to source entity's relationships

        TO ENTITY: EntityType (EDGE) -> EntityType (VERTEX)
          - Changes entity_kind to VERTEX, clears source/target
          - Removes Edge from source entity's relationships
        """
        name = params.name
        target_type = params.target_type

        if target_type == "RELATIONSHIP":
            source_entity_name = params.source_entity
            target_entity_name = params.target_entity

            entity = self._get_entity(name, "TRANSFORM")
            if not entity:
                return OperationResult.skipped("transform: precondition not met")

            # Resolve cardinality (default: ZERO_TO_MANY)
            cardinality = Cardinality.ZERO_TO_MANY
            if params.cardinality:
                cardinality = CARDINALITY_MAP.get(params.cardinality, Cardinality.ZERO_TO_MANY)

            # Convert VERTEX -> EDGE
            entity.entity_kind = EntityKind.EDGE
            entity.source_entity = source_entity_name
            entity.target_entity = target_entity_name
            entity.edge_cardinality = cardinality

            # Add Edge to source entity's relationships (avoid duplicates)
            source_ent = self.database.get_entity_type(source_entity_name)
            if source_ent:
                existing_edge = any(
                    isinstance(r, Edge) and r.rel_type_name == name
                    for r in source_ent.relationships
                )
                if not existing_edge:
                    edge = Edge(
                        rel_type_name=name,
                        source_entity=source_entity_name,
                        target_entity=target_entity_name,
                        cardinality=cardinality
                    )
                    source_ent.add_relationship(edge)

            self.changes.append(f"TRANSFORM:{name}->RELATIONSHIP({source_entity_name},{target_entity_name})")
            return OperationResult.ok()

        elif target_type == "ENTITY":
            edge_entity = self._get_entity(name, "TRANSFORM")
            if not edge_entity or edge_entity.entity_kind != EntityKind.EDGE:
                return OperationResult.skipped("transform: precondition not met")

            # Remove Edge from source entity's relationships
            if edge_entity.source_entity:
                source_ent = self.database.get_entity_type(edge_entity.source_entity)
                if source_ent:
                    source_ent.remove_relationship(name)

            # Convert EDGE -> VERTEX
            edge_entity.entity_kind = EntityKind.VERTEX
            edge_entity.source_entity = None
            edge_entity.target_entity = None
            edge_entity.edge_cardinality = None

            self.changes.append(f"TRANSFORM:{name}->ENTITY")
            return OperationResult.ok()
        return OperationResult.skipped("transform: precondition not met")
