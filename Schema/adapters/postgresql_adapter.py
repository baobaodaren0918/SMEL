"""
PostgreSQL Adapter - Parse SQL DDL to Unified Meta Schema.
Converts CREATE TABLE statements to Database/EntityType/Attribute objects.

This adapter provides bidirectional conversion:
  - parse(): PostgreSQL DDL (CREATE TABLE) -> Unified Meta Schema
  - export_to_sql(): Unified Meta Schema -> PostgreSQL DDL

Data Flow:
  PostgreSQL DDL                         Unified Meta Schema
  ─────────────────────────────────────────────────────────────
  VARCHAR(255)                    ->     PrimitiveType.STRING
  INTEGER / SERIAL                ->     PrimitiveType.INTEGER
  REFERENCES table(col)           ->     Reference relationship
  PRIMARY KEY                     ->     UniqueConstraint (is_primary_key=True)

Design: from André Conrad
"""
import re
from typing import Dict, List, Optional, Tuple
from ..unified_meta_schema import (
    Database, DatabaseType, EntityType, Attribute,
    UniqueConstraint, UniqueProperty, PKTypeEnum,
    Reference, Cardinality, PrimitiveDataType, PrimitiveType,
    TypeMappings
)


class PostgreSQLAdapter:
    """
    Adapter to parse PostgreSQL DDL and create Unified Meta Schema.

    This class acts as a translator between PostgreSQL's DDL format
    and the internal Unified Meta Schema used by SMEL.

    Example:
        adapter = PostgreSQLAdapter()
        database = adapter.parse(ddl_content, db_name="mydb")
    """

    # =========================================================================
    # TYPE MAPPING (from centralized TypeMappings)
    # =========================================================================
    # Use centralized mappings from unified_meta_schema.py
    TYPE_MAP = TypeMappings.POSTGRESQL_TO_PRIMITIVE

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    def __init__(self):
        """Initialize adapter with empty state."""
        self.database: Optional[Database] = None
        # Pending references: (source_entity, fk_column, target_entity)
        # Stored during parsing, resolved after all tables are created
        self._pending_references: List[Tuple[str, str, str]] = []

    # =========================================================================
    # PARSE METHODS (DDL -> Unified Meta Schema)
    # =========================================================================

    def parse(self, ddl_content: str, db_name: str = "database") -> Database:
        """
        Parse SQL DDL content and return Database object.

        Example Input (PostgreSQL DDL):
            CREATE TABLE person (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255)
            );

            CREATE TABLE address (
                id SERIAL PRIMARY KEY,
                street VARCHAR(200),
                person_id INTEGER REFERENCES person(id)
            );

        Example Output (Unified Meta Schema):
            Database(
                db_name="mydb",
                db_type=DatabaseType.RELATIONAL,
                entity_types={
                    "person": EntityType(
                        object_name=["person"],
                        attributes=[
                            Attribute("id", INTEGER, is_key=True),
                            Attribute("name", STRING(100)),
                            Attribute("email", STRING(255))
                        ]
                    ),
                    "address": EntityType(
                        object_name=["address"],
                        attributes=[...],
                        relationships=[Reference("person_id" -> "person")]
                    )
                }
            )

        Processing Flow:
            1. Remove SQL comments (-- and /* */)
            2. Extract CREATE TABLE statements
            3. Parse each table -> EntityType
            4. Resolve REFERENCES -> Reference relationships
        """
        self.database = Database(db_name=db_name, db_type=DatabaseType.RELATIONAL)
        self._pending_references = []

        # Step 1: Remove comments
        ddl = self._remove_comments(ddl_content)

        # Step 2: Extract CREATE TABLE statements
        tables = self._extract_create_tables(ddl)

        # Step 3: Parse each table
        for table_name, table_body in tables:
            entity = self._parse_table(table_name, table_body)
            self.database.add_entity_type(entity)

        # Step 4: Resolve references after all entities are created
        # (FK references need target table to exist)
        self._resolve_references()

        return self.database

    def _remove_comments(self, ddl: str) -> str:
        """
        Remove SQL comments from DDL.

        Handles:
          - Single-line comments: -- comment
          - Multi-line comments: /* comment */
        """
        # Remove single-line comments (-- ...)
        ddl = re.sub(r'--.*$', '', ddl, flags=re.MULTILINE)
        # Remove multi-line comments (/* ... */)
        ddl = re.sub(r'/\*.*?\*/', '', ddl, flags=re.DOTALL)
        return ddl

    def _extract_create_tables(self, ddl: str) -> List[Tuple[str, str]]:
        """
        Extract CREATE TABLE statements from DDL.

        Returns:
            List of (table_name, table_body) tuples

        Example:
            "CREATE TABLE person (id INT, name VARCHAR);"
            -> [("person", "id INT, name VARCHAR")]
        """
        pattern = r'CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);'
        matches = re.findall(pattern, ddl, re.IGNORECASE | re.DOTALL)
        return matches

    def _parse_table(self, table_name: str, table_body: str) -> EntityType:
        """
        Parse a single CREATE TABLE body into EntityType.

        Example:
            table_name = "person"
            table_body = "id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL"

            -> EntityType(
                 object_name=["person"],
                 attributes=[
                     Attribute("id", INTEGER, is_key=True),
                     Attribute("name", STRING(100), is_optional=False)
                 ],
                 constraints=[UniqueConstraint(is_primary_key=True, ...)]
               )
        """
        entity = EntityType(object_name=[table_name.lower()])

        # Split by comma, but handle parentheses in type definitions
        # e.g., DECIMAL(15,2) should not be split
        columns = self._split_columns(table_body)

        for col_def in columns:
            col_def = col_def.strip()
            if not col_def:
                continue

            # Skip table-level constraint definitions (parsed separately)
            upper = col_def.upper()
            if any(upper.startswith(kw) for kw in ['PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK', 'CONSTRAINT']):
                continue

            # Parse column definition
            attr, ref_info = self._parse_column(col_def)
            if attr:
                entity.add_attribute(attr)

                # Handle inline PRIMARY KEY constraint
                # e.g., "id SERIAL PRIMARY KEY"
                if 'PRIMARY KEY' in col_def.upper():
                    constraint = UniqueConstraint(
                        is_primary_key=True,
                        is_managed=True,
                        unique_properties=[UniqueProperty(primary_key_type=PKTypeEnum.SIMPLE, property_id=attr.meta_id)]
                    )
                    entity.add_constraint(constraint)

                # Store REFERENCES for later resolution
                # e.g., "person_id INTEGER REFERENCES person(id)"
                if ref_info:
                    self._pending_references.append((entity.name, ref_info[0], ref_info[1]))

        # Auto-create primary key constraint for SERIAL columns
        # (SERIAL implies PRIMARY KEY even without explicit declaration)
        if not entity.get_primary_key():
            for attr in entity.attributes:
                if attr.is_key:
                    constraint = UniqueConstraint(
                        is_primary_key=True,
                        is_managed=True,
                        unique_properties=[UniqueProperty(primary_key_type=PKTypeEnum.SIMPLE, property_id=attr.meta_id)]
                    )
                    entity.add_constraint(constraint)
                    break

        return entity

    def _split_columns(self, body: str) -> List[str]:
        """
        Split column definitions, handling nested parentheses.

        Problem: Simple split by ',' fails for types like DECIMAL(15,2)
        Solution: Track parenthesis depth, only split at depth 0

        Example:
            "id INT, price DECIMAL(15,2), name VARCHAR(100)"
            -> ["id INT", "price DECIMAL(15,2)", "name VARCHAR(100)"]
        """
        result = []
        current = ""
        depth = 0

        for char in body:
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                # Only split when not inside parentheses
                result.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            result.append(current.strip())

        return result

    def _parse_column(self, col_def: str) -> Tuple[Optional[Attribute], Optional[Tuple[str, str]]]:
        """
        Parse a single column definition.

        Example Input:
            "person_id INTEGER NOT NULL REFERENCES person(id)"

        Example Output:
            Attribute("person_id", INTEGER, is_key=False, is_optional=False)
            ref_info = ("person_id", "person")

        Returns:
            (Attribute, ref_info) where ref_info is (fk_column, target_table) or None
        """
        # Normalize whitespace (handle multi-line definitions)
        col_def = ' '.join(col_def.split())

        # Pattern: column_name TYPE [constraints] [REFERENCES table(col)]
        # Handles: "id SERIAL", "name VARCHAR(100)", "price DOUBLE PRECISION"
        pattern = r'^(\w+)\s+(\w+(?:\s+PRECISION)?)\s*(?:\(([^)]+)\))?\s*(.*)?$'
        match = re.match(pattern, col_def.strip(), re.IGNORECASE)

        if not match:
            return None, None

        col_name = match.group(1).lower()          # "person_id"
        col_type = match.group(2).upper()          # "INTEGER"
        type_params = match.group(3)               # "100" for VARCHAR(100)
        constraints = match.group(4) or ""         # "NOT NULL REFERENCES person(id)"

        # Determine data type
        data_type = self._parse_data_type(col_type, type_params)

        # Check constraints
        # is_key: PRIMARY KEY explicitly declared OR SERIAL type (auto-increment implies PK)
        is_key = 'PRIMARY KEY' in constraints.upper() or col_type in ('SERIAL', 'BIGSERIAL')
        # is_optional: NOT NULL not present AND not a primary key
        is_optional = 'NOT NULL' not in constraints.upper() and not is_key

        attr = Attribute(
            attr_name=col_name,
            data_type=data_type,
            is_key=is_key,
            is_optional=is_optional
        )

        # Check for REFERENCES clause (foreign key)
        # Pattern: REFERENCES target_table(target_column)
        ref_info = None
        ref_match = re.search(r'REFERENCES\s+(\w+)\s*\((\w+)\)', constraints, re.IGNORECASE)
        if ref_match:
            ref_info = (col_name, ref_match.group(1).lower())

        return attr, ref_info

    def _parse_data_type(self, type_name: str, params: Optional[str]) -> PrimitiveDataType:
        """
        Parse SQL type to PrimitiveDataType.

        Examples:
            ("VARCHAR", "100")     -> PrimitiveDataType(STRING, max_length=100)
            ("DECIMAL", "15,2")    -> PrimitiveDataType(DECIMAL, precision=15, scale=2)
            ("INTEGER", None)      -> PrimitiveDataType(INTEGER)
        """
        primitive = self.TYPE_MAP.get(type_name, PrimitiveType.STRING)

        max_length = None
        precision = None
        scale = None

        if params:
            parts = [p.strip() for p in params.split(',')]
            if primitive in (PrimitiveType.STRING, PrimitiveType.TEXT):
                # VARCHAR(100) -> max_length=100
                max_length = int(parts[0]) if parts else None
            elif primitive == PrimitiveType.DECIMAL:
                # DECIMAL(15,2) -> precision=15, scale=2
                precision = int(parts[0]) if parts else None
                scale = int(parts[1]) if len(parts) > 1 else 0

        return PrimitiveDataType(
            primitive_type=primitive,
            max_length=max_length,
            precision=precision,
            scale=scale
        )

    def _resolve_references(self):
        """
        Resolve foreign key references after all entities are created.

        Why delayed resolution?
            REFERENCES clauses may refer to tables defined later in DDL.
            By collecting all references during parsing and resolving after,
            we ensure the target table exists.

        Example:
            _pending_references = [("address", "person_id", "person")]
            -> address entity gets Reference("person_id" -> "person")
        """
        for entity_name, ref_name, target_name in self._pending_references:
            entity = self.database.get_entity_type(entity_name)
            target = self.database.get_entity_type(target_name)

            if entity and target:
                # Get FK column's is_optional from attribute
                attr = entity.get_attribute(ref_name)
                is_optional = attr.is_optional if attr else True

                reference = Reference(
                    ref_name=ref_name,
                    refs_to=target_name,
                    cardinality=Cardinality.ONE_TO_ONE,
                    is_optional=is_optional
                )
                entity.add_relationship(reference)

    @staticmethod
    def load_from_file(file_path: str, db_name: str = None) -> Database:
        """
        Load SQL DDL from file and parse to Database.

        Example:
            database = PostgreSQLAdapter.load_from_file("schema.sql", db_name="mydb")
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if db_name is None:
            from pathlib import Path
            db_name = Path(file_path).stem

        adapter = PostgreSQLAdapter()
        return adapter.parse(content, db_name)

    # =========================================================================
    # EXPORT METHODS (Unified Meta Schema -> DDL)
    # =========================================================================

    # Reverse mapping (from centralized TypeMappings)
    # Used when exporting back to PostgreSQL format
    REVERSE_TYPE_MAP = TypeMappings.PRIMITIVE_TO_POSTGRESQL

    @classmethod
    def export_to_sql(cls, database: Database) -> str:
        """
        Export Unified Meta Schema to PostgreSQL DDL format.

        Example Output:
            TABLE person (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL
            );

            TABLE address (
                id SERIAL PRIMARY KEY,
                street VARCHAR(200),
                person_id INTEGER NOT NULL REFERENCES person(id)
            );

        Note: Tables are sorted by dependency order (referenced tables first)
        """
        lines = []

        # Sort entities by dependency order (entities with no FK first)
        # This ensures REFERENCES clauses point to existing tables
        sorted_entities = cls._sort_entities_by_dependency(database)

        for entity in sorted_entities:
            ddl = cls._export_entity_to_ddl(entity, database)
            lines.append(ddl)
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def _sort_entities_by_dependency(cls, database: Database) -> list:
        """
        Sort entities so that referenced tables come before referencing tables.

        Uses topological sort to handle FK dependencies.

        Example:
            address -> person (address has FK to person)
            Result: [person, address] (person first)
        """
        entities = list(database.entity_types.values())

        # Build dependency graph: entity -> set of entities it depends on
        dependencies = {}
        for entity in entities:
            deps = set()
            for rel in entity.relationships:
                if isinstance(rel, Reference):
                    target = rel.get_target_entity_name()
                    if target != entity.name:  # Avoid self-reference
                        deps.add(target)
            dependencies[entity.name] = deps

        # Topological sort (DFS)
        sorted_names = []
        visited = set()

        def visit(name):
            if name in visited:
                return
            visited.add(name)
            # Visit dependencies first
            for dep in dependencies.get(name, []):
                if dep in dependencies:  # Only visit if entity exists
                    visit(dep)
            sorted_names.append(name)

        for name in dependencies:
            visit(name)

        return [database.get_entity_type(name) for name in sorted_names if database.get_entity_type(name)]

    @classmethod
    def _export_entity_to_ddl(cls, entity: EntityType, database: Database) -> str:
        """
        Export a single entity to CREATE TABLE DDL format.

        Example Output:
            TABLE person (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255)
            );

        Handles:
            - Single-column PRIMARY KEY (inline)
            - Composite PRIMARY KEY (separate constraint)
            - REFERENCES clauses for FK columns
        """
        lines = []
        lines.append(f"TABLE {entity.name} (")

        columns = []
        constraints = []

        # Build FK lookup: column_name -> Reference relationship
        fk_refs = {}
        for rel in entity.relationships:
            if isinstance(rel, Reference):
                fk_refs[rel.ref_name] = rel

        # Check for composite primary key (e.g., M:N join tables)
        pk_constraint = entity.get_primary_key()
        pk_columns = []
        if pk_constraint and pk_constraint.unique_properties:
            for up in pk_constraint.unique_properties:
                pk_attr = entity.get_attribute_by_id(up.property_id)
                if pk_attr:
                    pk_columns.append(pk_attr.attr_name)

        is_composite_pk = len(pk_columns) > 1

        # Process attributes -> columns
        for attr in entity.attributes:
            col_def = cls._export_attribute_to_column(attr, fk_refs.get(attr.attr_name), database, is_composite_pk)
            columns.append(f"    {col_def}")

        # Add composite PRIMARY KEY constraint if needed
        # e.g., PRIMARY KEY (person_id, knows_person_id)
        if is_composite_pk:
            pk_constraint_str = f"    PRIMARY KEY ({', '.join(pk_columns)})"
            columns.append(pk_constraint_str)

        lines.append(",\n".join(columns))
        lines.append(");")

        return "\n".join(lines)

    @classmethod
    def _export_attribute_to_column(cls, attr: Attribute, fk_ref: Reference = None, database: Database = None, is_composite_pk: bool = False) -> str:
        """
        Export an attribute to column definition.

        Examples:
            Single PK:    "id SERIAL PRIMARY KEY"
            Required:     "name VARCHAR(100) NOT NULL"
            Optional:     "email VARCHAR(255)"
            FK:           "person_id INTEGER NOT NULL REFERENCES person(id)"
            Composite PK: "person_id VARCHAR(255) NOT NULL" (PK constraint is separate)
        """
        parts = [attr.attr_name]

        # Data type (VARCHAR, INTEGER, SERIAL, etc.)
        sql_type = cls._get_sql_type(attr)
        parts.append(sql_type)

        # Constraint: PRIMARY KEY (only inline for single-column PK)
        if attr.is_key and not is_composite_pk:
            parts.append("PRIMARY KEY")
        # Constraint: NOT NULL
        # - Required if not optional
        # - Required for composite PK columns (PK constraint is separate)
        elif not attr.is_optional or (attr.is_key and is_composite_pk):
            parts.append("NOT NULL")

        # Constraint: REFERENCES (foreign key)
        if fk_ref:
            target_entity_name = fk_ref.get_target_entity_name()
            # Find target PK column from database metadata
            target_pk_name = cls._get_target_pk_name(target_entity_name, database)
            parts.append(f"REFERENCES {target_entity_name}({target_pk_name})")

        return " ".join(parts)

    @classmethod
    def _get_sql_type(cls, attr: Attribute) -> str:
        """
        Get SQL type string from attribute.

        Examples:
            STRING with max_length=100  -> "VARCHAR(100)"
            STRING without max_length   -> "VARCHAR(255)" (default)
            DECIMAL(15,2)              -> "DECIMAL(15,2)"
            INTEGER with is_key=True   -> "SERIAL" (auto-increment)
            INTEGER with is_key=False  -> "INTEGER"
        """
        primitive = attr.data_type.primitive_type
        base_type = cls.REVERSE_TYPE_MAP.get(primitive, 'VARCHAR')

        # Handle VARCHAR with length
        if base_type == 'VARCHAR':
            max_len = attr.data_type.max_length or 255
            return f"VARCHAR({max_len})"

        # Handle DECIMAL with precision/scale
        if base_type == 'DECIMAL':
            precision = attr.data_type.precision or 13
            scale = attr.data_type.scale or 2
            return f"DECIMAL({precision},{scale})"

        # Use SERIAL for integer PKs (auto-increment)
        if base_type == 'INTEGER' and attr.is_key:
            return 'SERIAL'

        return base_type

    @classmethod
    def _get_target_pk_name(cls, entity_name: str, database: Database = None) -> str:
        """
        Get the PK column name for a target entity.

        Used for REFERENCES clause: REFERENCES target_entity(pk_column)

        Example:
            entity_name = "person"
            -> Looks up person's PK -> "_id" or "id"
            -> Returns "_id"
        """
        # Try to get PK from database metadata
        if database:
            target_entity = database.get_entity_type(entity_name)
            if target_entity:
                pk = target_entity.get_primary_key()
                if pk and pk.unique_properties:
                    # Use property_id to look up the attribute
                    pk_attr = target_entity.get_attribute_by_id(pk.unique_properties[0].property_id)
                    if pk_attr:
                        return pk_attr.attr_name

        # Fallback: default naming convention
        return f"{entity_name}_id"

    @classmethod
    def export_to_sql_file(cls, database: Database, file_path: str) -> None:
        """
        Export to SQL file.

        Example:
            PostgreSQLAdapter.export_to_sql_file(database, "output.sql")
        """
        sql = cls.export_to_sql(database)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sql)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
#
# Example 1: Parse PostgreSQL DDL to Unified Meta Schema
# -------------------------------------------------------
#
# ddl_content = '''
# CREATE TABLE person (
#     id SERIAL PRIMARY KEY,
#     name VARCHAR(100) NOT NULL,
#     email VARCHAR(255)
# );
#
# CREATE TABLE address (
#     id SERIAL PRIMARY KEY,
#     street VARCHAR(200),
#     city VARCHAR(100),
#     person_id INTEGER NOT NULL REFERENCES person(id)
# );
# '''
#
# adapter = PostgreSQLAdapter()
# database = adapter.parse(ddl_content, db_name="mydb")
#
# Result:
#   database.db_name = "mydb"
#   database.db_type = DatabaseType.RELATIONAL
#   database.entity_types = {
#       "person": EntityType(
#           object_name=["person"],
#           attributes=[
#               Attribute("id", INTEGER, is_key=True),
#               Attribute("name", STRING(100), is_optional=False),
#               Attribute("email", STRING(255), is_optional=True)
#           ],
#           constraints=[UniqueConstraint(is_primary_key=True, ...)]
#       ),
#       "address": EntityType(
#           object_name=["address"],
#           attributes=[
#               Attribute("id", INTEGER, is_key=True),
#               Attribute("street", STRING(200)),
#               Attribute("city", STRING(100)),
#               Attribute("person_id", INTEGER, is_optional=False)
#           ],
#           relationships=[Reference("person_id" -> "person")]
#       )
#   }
#
#
# Example 2: Load from file
# -------------------------
#
# database = PostgreSQLAdapter.load_from_file("schema.sql", db_name="mydb")
#
#
# Example 3: Export back to PostgreSQL DDL
# ----------------------------------------
#
# sql_ddl = PostgreSQLAdapter.export_to_sql(database)
# print(sql_ddl)
#
# Output:
#   TABLE person (
#       id SERIAL PRIMARY KEY,
#       name VARCHAR(100) NOT NULL,
#       email VARCHAR(255)
#   );
#
#   TABLE address (
#       id SERIAL PRIMARY KEY,
#       street VARCHAR(200),
#       city VARCHAR(100),
#       person_id INTEGER NOT NULL REFERENCES person(id)
#   );
#
#
# Example 4: Export to file
# -------------------------
#
# PostgreSQLAdapter.export_to_sql_file(database, "output.sql")
#
#
# Example 5: Composite Primary Key (M:N join table from FLATTEN without GENERATE KEY)
# ------------------------------------------------------------------------------------
#
# After FLATTEN person.knows[] AS person_knows (no GENERATE KEY -> composite PK):
#
# person_knows = EntityType(
#     object_name=["person_knows"],
#     attributes=[
#         Attribute("person_id", STRING, is_key=True),
#         Attribute("knows_person_id", STRING, is_key=True)
#     ],
#     constraints=[UniqueConstraint(
#         is_primary_key=True,
#         unique_properties=[person_id, knows_person_id]  # Composite!
#     )]
# )
#
# Export result:
#   TABLE person_knows (
#       person_id VARCHAR(255) NOT NULL REFERENCES person(_id),
#       knows_person_id VARCHAR(255) NOT NULL REFERENCES person(_id),
#       PRIMARY KEY (person_id, knows_person_id)
#   );
#
