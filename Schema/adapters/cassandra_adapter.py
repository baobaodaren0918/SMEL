"""
Cassandra Adapter - Parse CQL DDL to Unified Meta Schema.
Converts CREATE TABLE statements to Database/EntityType/Attribute objects.

This adapter provides bidirectional conversion:
  - parse(): Cassandra CQL DDL (CREATE TABLE) -> Unified Meta Schema
  - export_to_cql(): Unified Meta Schema -> Cassandra CQL DDL

Data Flow:
  Cassandra CQL DDL                        Unified Meta Schema
  ─────────────────────────────────────────────────────────────
  TEXT / VARCHAR / ASCII             ->     PrimitiveType.STRING
  INT                                ->     PrimitiveType.INTEGER
  BIGINT / COUNTER                   ->     PrimitiveType.LONG
  DOUBLE / FLOAT                     ->     PrimitiveType.DOUBLE
  DECIMAL                            ->     PrimitiveType.DECIMAL
  BOOLEAN                            ->     PrimitiveType.BOOLEAN
  DATE                               ->     PrimitiveType.DATE
  TIMESTAMP                          ->     PrimitiveType.TIMESTAMP
  UUID / TIMEUUID                    ->     PrimitiveType.UUID
  BLOB                               ->     PrimitiveType.BINARY
  PRIMARY KEY ((part), clust)        ->     UniqueConstraint (PARTITION + CLUSTERING)

Design: from Andre Conrad
"""
import re
from typing import Dict, List, Optional, Tuple
from ..unified_meta_schema import (
    Database, DatabaseType, EntityType, EntityKind, Attribute,
    UniqueConstraint, UniqueProperty, PKTypeEnum,
    PrimitiveDataType, PrimitiveType, Cardinality, TypeMappings
)


class CassandraAdapter:
    """
    Adapter to parse Cassandra CQL DDL and create Unified Meta Schema.

    This class acts as a translator between Cassandra's CQL DDL format
    and the internal Unified Meta Schema used by SMEL.

    Example:
        adapter = CassandraAdapter()
        database = adapter.parse(cql_content, db_name="mydb")
    """

    # =========================================================================
    # TYPE MAPPING (from centralized TypeMappings)
    # =========================================================================
    TYPE_MAP = TypeMappings.CASSANDRA_TO_PRIMITIVE
    REVERSE_TYPE_MAP = TypeMappings.PRIMITIVE_TO_CASSANDRA

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    def __init__(self):
        """Initialize adapter with empty state."""
        self.database: Optional[Database] = None

    # =========================================================================
    # PARSE METHODS (CQL DDL -> Unified Meta Schema)
    # =========================================================================

    def parse(self, cql_content: str, db_name: str = "database") -> Database:
        """
        Parse CQL DDL content and return Database object.

        Example Input (Cassandra CQL DDL):
            CREATE TABLE users (
                user_id UUID,
                name TEXT,
                email TEXT,
                PRIMARY KEY (user_id)
            );

            CREATE TABLE user_activity (
                user_id UUID,
                activity_time TIMESTAMP,
                action TEXT,
                details TEXT,
                PRIMARY KEY ((user_id), activity_time)
            );

        Example Output (Unified Meta Schema):
            Database(
                db_name="mydb",
                db_type=DatabaseType.COLUMNAR,
                entity_types={
                    "users": EntityType(
                        object_name=["users"],
                        entity_kind=EntityKind.WIDE_COLUMN_TABLE,
                        attributes=[
                            Attribute("user_id", UUID, is_key=True),
                            Attribute("name", STRING),
                            Attribute("email", STRING)
                        ],
                        constraints=[UniqueConstraint(
                            is_primary_key=True,
                            unique_properties=[
                                UniqueProperty(PKTypeEnum.PARTITION, user_id.meta_id)
                            ]
                        )]
                    ),
                    "user_activity": EntityType(
                        object_name=["user_activity"],
                        entity_kind=EntityKind.WIDE_COLUMN_TABLE,
                        attributes=[...],
                        constraints=[UniqueConstraint(
                            is_primary_key=True,
                            unique_properties=[
                                UniqueProperty(PKTypeEnum.PARTITION, user_id.meta_id),
                                UniqueProperty(PKTypeEnum.CLUSTERING, activity_time.meta_id)
                            ]
                        )]
                    )
                }
            )

        Processing Flow:
            1. Remove CQL comments (-- and /* */)
            2. Extract CREATE TABLE statements
            3. Parse each table -> EntityType with WIDE_COLUMN_TABLE kind
            4. Parse PRIMARY KEY with PARTITION / CLUSTERING distinction
        """
        self.database = Database(db_name=db_name, db_type=DatabaseType.COLUMNAR)

        # Step 1: Remove comments
        cql = self._remove_comments(cql_content)

        # Step 2: Extract CREATE TABLE statements
        tables = self._extract_create_tables(cql)

        # Step 3: Parse each table
        for table_name, table_body in tables:
            entity = self._parse_table(table_name, table_body)
            self.database.add_entity_type(entity)

        return self.database

    def _remove_comments(self, cql: str) -> str:
        """
        Remove CQL comments from DDL.

        Handles:
          - Single-line comments: -- comment
          - Multi-line comments: /* comment */
        """
        # Remove single-line comments (-- ...)
        cql = re.sub(r'--.*$', '', cql, flags=re.MULTILINE)
        # Remove multi-line comments (/* ... */)
        cql = re.sub(r'/\*.*?\*/', '', cql, flags=re.DOTALL)
        return cql

    def _extract_create_tables(self, cql: str) -> List[Tuple[str, str]]:
        """
        Extract CREATE TABLE statements from CQL DDL.

        Handles optional IF NOT EXISTS and WITH clauses.

        Returns:
            List of (table_name, table_body) tuples

        Example:
            "CREATE TABLE users (user_id UUID, PRIMARY KEY (user_id));"
            -> [("users", "user_id UUID, PRIMARY KEY (user_id)")]
        """
        # Match CREATE TABLE with optional IF NOT EXISTS
        # Capture table body inside outermost parentheses, stop before WITH or ;
        pattern = re.compile(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?(\w+)\s*\((.*?)\)\s*(?:WITH\s+.*?)?;',
            re.DOTALL | re.IGNORECASE
        )
        matches = pattern.findall(cql)
        return matches

    def _parse_table(self, table_name: str, table_body: str) -> EntityType:
        """
        Parse a single CREATE TABLE body into EntityType.

        Example:
            table_name = "users"
            table_body = "user_id UUID, name TEXT, email TEXT, PRIMARY KEY (user_id)"

            -> EntityType(
                 object_name=["users"],
                 entity_kind=EntityKind.WIDE_COLUMN_TABLE,
                 attributes=[
                     Attribute("user_id", UUID, is_key=True),
                     Attribute("name", STRING),
                     Attribute("email", STRING)
                 ],
                 constraints=[UniqueConstraint(is_primary_key=True, ...)]
               )
        """
        entity = EntityType(
            object_name=[table_name.lower()],
            entity_kind=EntityKind.WIDE_COLUMN_TABLE
        )

        # Split by comma, but handle parentheses in type definitions and PK clauses
        columns = self._split_columns(table_body)

        # Track inline PRIMARY KEY (single column with "PRIMARY KEY" suffix)
        inline_pk_col: Optional[str] = None
        # Track table-level PRIMARY KEY clause
        table_pk_clause: Optional[str] = None

        for col_def in columns:
            col_def = col_def.strip()
            if not col_def:
                continue

            upper = col_def.upper().strip()

            # Detect table-level PRIMARY KEY clause
            # e.g., "PRIMARY KEY (user_id)" or "PRIMARY KEY ((user_id), activity_time)"
            if upper.startswith('PRIMARY KEY'):
                table_pk_clause = col_def
                continue

            # Parse column definition
            attr, is_inline_pk = self._parse_column(col_def)
            if attr:
                entity.add_attribute(attr)
                if is_inline_pk:
                    inline_pk_col = attr.attr_name

        # Build primary key constraint
        if table_pk_clause:
            # Table-level PRIMARY KEY clause
            # Parse partition and clustering columns
            partition_cols, clustering_cols = self._parse_primary_key_clause(table_pk_clause)
            self._build_pk_constraint(entity, partition_cols, clustering_cols)
        elif inline_pk_col:
            # Inline PRIMARY KEY (single column)
            # e.g., "user_id UUID PRIMARY KEY"
            attr = entity.get_attribute(inline_pk_col)
            if attr:
                attr.is_key = True
                constraint = UniqueConstraint(
                    is_primary_key=True,
                    is_managed=True,
                    unique_properties=[UniqueProperty(
                        primary_key_type=PKTypeEnum.PARTITION,
                        property_id=attr.meta_id
                    )]
                )
                entity.add_constraint(constraint)

        return entity

    def _split_columns(self, body: str) -> List[str]:
        """
        Split column definitions, handling nested parentheses.

        Problem: Simple split by ',' fails for PRIMARY KEY ((part_col), clust_col)
        Solution: Track parenthesis depth, only split at depth 0

        Example:
            "user_id UUID, name TEXT, PRIMARY KEY ((user_id), activity_time)"
            -> ["user_id UUID", "name TEXT", "PRIMARY KEY ((user_id), activity_time)"]
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

    def _parse_column(self, col_def: str) -> Tuple[Optional[Attribute], bool]:
        """
        Parse a single column definition.

        Example Input:
            "user_id UUID PRIMARY KEY"

        Example Output:
            Attribute("user_id", UUID, is_key=True)
            is_inline_pk = True

        Returns:
            (Attribute, is_inline_pk) where is_inline_pk indicates inline PRIMARY KEY
        """
        # Normalize whitespace (handle multi-line definitions)
        col_def = ' '.join(col_def.split())

        # Check for inline PRIMARY KEY
        # e.g., "user_id UUID PRIMARY KEY"
        is_inline_pk = bool(re.search(r'PRIMARY\s+KEY', col_def, re.IGNORECASE))

        # Remove PRIMARY KEY from the definition for cleaner parsing
        clean_def = re.sub(r'\s*PRIMARY\s+KEY\s*', ' ', col_def, flags=re.IGNORECASE).strip()

        # Pattern: column_name TYPE
        # Handles: "user_id UUID", "name TEXT", "value DOUBLE"
        match = re.match(r'^(\w+)\s+(\w+)', clean_def.strip(), re.IGNORECASE)

        if not match:
            return None, False

        col_name = match.group(1).lower()
        col_type = match.group(2).upper()

        # Determine data type
        data_type = self._parse_data_type(col_type)

        # is_key will be set later when building the PK constraint
        attr = Attribute(
            attr_name=col_name,
            data_type=data_type,
            is_key=is_inline_pk,
            is_optional=not is_inline_pk
        )

        return attr, is_inline_pk

    def _parse_data_type(self, type_name: str) -> PrimitiveDataType:
        """
        Parse CQL type to PrimitiveDataType.

        Examples:
            "UUID"        -> PrimitiveDataType(UUID)
            "TEXT"        -> PrimitiveDataType(STRING)
            "TIMESTAMP"   -> PrimitiveDataType(TIMESTAMP)
            "DOUBLE"      -> PrimitiveDataType(DOUBLE)
        """
        primitive = self.TYPE_MAP.get(type_name, PrimitiveType.STRING)
        return PrimitiveDataType(primitive_type=primitive)

    def _parse_primary_key_clause(self, pk_clause: str) -> Tuple[List[str], List[str]]:
        """
        Parse PRIMARY KEY clause into partition and clustering columns.

        Handles both forms:
          - Simple: PRIMARY KEY (col)
          - Composite partition: PRIMARY KEY ((part1, part2), clust1, clust2)

        Example 1 - Simple PK:
            "PRIMARY KEY (user_id)"
            -> partition_cols=["user_id"], clustering_cols=[]

        Example 2 - Composite PK with partition and clustering:
            "PRIMARY KEY ((user_id), activity_time)"
            -> partition_cols=["user_id"], clustering_cols=["activity_time"]

        Example 3 - Multi-column partition key:
            "PRIMARY KEY ((tenant_id, user_id), created_at)"
            -> partition_cols=["tenant_id", "user_id"], clustering_cols=["created_at"]

        Returns:
            (partition_cols, clustering_cols)
        """
        # Extract everything inside PRIMARY KEY (...)
        pk_match = re.search(r'PRIMARY\s+KEY\s*\((.+)\)', pk_clause, re.IGNORECASE)
        if not pk_match:
            return [], []

        pk_content = pk_match.group(1).strip()

        # Check for composite partition key: ((part_cols), clust_cols)
        composite_match = re.match(r'\(\((.+?)\)\s*(?:,\s*(.+))?\)', '(' + pk_content + ')')
        # Try a direct pattern on pk_content
        inner_match = re.match(r'\((.+?)\)\s*(?:,\s*(.+))?$', pk_content)

        if inner_match:
            # Composite partition key: ((part1, part2), clust1, clust2)
            partition_str = inner_match.group(1)
            clustering_str = inner_match.group(2)

            partition_cols = [c.strip().lower() for c in partition_str.split(',')]
            clustering_cols = []
            if clustering_str:
                clustering_cols = [c.strip().lower() for c in clustering_str.split(',')]

            return partition_cols, clustering_cols
        else:
            # Simple primary key: (col1) or (col1, col2)
            # All columns are partition keys when there are no inner parentheses
            cols = [c.strip().lower() for c in pk_content.split(',')]
            return cols, []

    def _build_pk_constraint(self, entity: EntityType, partition_cols: List[str], clustering_cols: List[str]):
        """
        Build UniqueConstraint with PARTITION and CLUSTERING key types.

        Example:
            partition_cols = ["user_id"]
            clustering_cols = ["activity_time"]

            -> UniqueConstraint(
                 is_primary_key=True,
                 unique_properties=[
                     UniqueProperty(PKTypeEnum.PARTITION, user_id.meta_id),
                     UniqueProperty(PKTypeEnum.CLUSTERING, activity_time.meta_id)
                 ]
               )
        """
        unique_props = []

        # Add partition key columns
        for col_name in partition_cols:
            attr = entity.get_attribute(col_name)
            if attr:
                attr.is_key = True
                attr.is_optional = False
                unique_props.append(UniqueProperty(
                    primary_key_type=PKTypeEnum.PARTITION,
                    property_id=attr.meta_id
                ))

        # Add clustering key columns
        for col_name in clustering_cols:
            attr = entity.get_attribute(col_name)
            if attr:
                attr.is_key = True
                attr.is_optional = False
                unique_props.append(UniqueProperty(
                    primary_key_type=PKTypeEnum.CLUSTERING,
                    property_id=attr.meta_id
                ))

        if unique_props:
            constraint = UniqueConstraint(
                is_primary_key=True,
                is_managed=True,
                unique_properties=unique_props
            )
            entity.add_constraint(constraint)

    @staticmethod
    def load_from_file(file_path: str, db_name: str = None) -> Database:
        """
        Load CQL DDL from file and parse to Database.

        Example:
            database = CassandraAdapter.load_from_file("schema.cql", db_name="mydb")
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if db_name is None:
            from pathlib import Path
            db_name = Path(file_path).stem

        adapter = CassandraAdapter()
        return adapter.parse(content, db_name)

    # =========================================================================
    # EXPORT METHODS (Unified Meta Schema -> CQL DDL)
    # =========================================================================

    @classmethod
    def export_to_cql(cls, database: Database) -> str:
        """
        Export Unified Meta Schema to Cassandra CQL DDL format.

        Example Output:
            -- Cassandra Schema
            -- Generated by SMEL

            CREATE TABLE users (
                user_id UUID,
                name TEXT,
                email TEXT,
                PRIMARY KEY (user_id)
            );

            CREATE TABLE user_activity (
                user_id UUID,
                activity_time TIMESTAMP,
                action TEXT,
                details TEXT,
                PRIMARY KEY ((user_id), activity_time)
            );
        """
        lines = []
        lines.append("-- Cassandra Schema")
        lines.append("-- Generated by SMEL")
        lines.append("")

        for entity in database.entity_types.values():
            ddl = cls._export_entity_to_cql(entity)
            lines.append(ddl)
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def _export_entity_to_cql(cls, entity: EntityType) -> str:
        """
        Export a single entity to CREATE TABLE CQL format.

        Example Output (simple PK):
            CREATE TABLE users (
                user_id UUID,
                name TEXT,
                email TEXT,
                PRIMARY KEY (user_id)
            );

        Example Output (composite PK with partition + clustering):
            CREATE TABLE user_activity (
                user_id UUID,
                activity_time TIMESTAMP,
                action TEXT,
                details TEXT,
                PRIMARY KEY ((user_id), activity_time)
            );

        Handles:
            - PARTITION keys -> ((part_col1, part_col2))
            - CLUSTERING keys -> appended after partition keys
            - Single partition key without clustering -> PRIMARY KEY (col)
        """
        lines = []
        lines.append(f"CREATE TABLE {entity.name} (")

        columns = []

        # Process attributes -> column definitions
        for attr in entity.attributes:
            col_def = cls._export_attribute_to_column(attr)
            columns.append(f"    {col_def}")

        # Build PRIMARY KEY clause
        pk_clause = cls._build_primary_key_clause(entity)
        if pk_clause:
            columns.append(f"    {pk_clause}")

        lines.append(",\n".join(columns))
        lines.append(");")

        return "\n".join(lines)

    @classmethod
    def _export_attribute_to_column(cls, attr: Attribute) -> str:
        """
        Export an attribute to CQL column definition.

        Examples:
            "user_id UUID"
            "name TEXT"
            "value DOUBLE"
        """
        cql_type = cls._get_cql_type(attr)
        return f"{attr.attr_name} {cql_type}"

    @classmethod
    def _get_cql_type(cls, attr: Attribute) -> str:
        """
        Get CQL type string from attribute.

        Examples:
            PrimitiveType.STRING    -> "TEXT"
            PrimitiveType.UUID      -> "UUID"
            PrimitiveType.TIMESTAMP -> "TIMESTAMP"
            PrimitiveType.DOUBLE    -> "DOUBLE"
        """
        if not isinstance(attr.data_type, PrimitiveDataType):
            return 'TEXT'

        primitive = attr.data_type.primitive_type
        return cls.REVERSE_TYPE_MAP.get(primitive, 'TEXT')

    @classmethod
    def _build_primary_key_clause(cls, entity: EntityType) -> Optional[str]:
        """
        Build PRIMARY KEY clause from entity constraints.

        Logic:
            1. Find PARTITION key attributes (UniqueProperty with PKTypeEnum.PARTITION)
            2. Find CLUSTERING key attributes (UniqueProperty with PKTypeEnum.CLUSTERING)
            3. Build PRIMARY KEY clause:
               - Only partition keys: PRIMARY KEY (col1, col2)
               - Partition + clustering: PRIMARY KEY ((partition_cols), clustering_cols)

        Example 1 - Single partition key:
            -> "PRIMARY KEY (user_id)"

        Example 2 - Partition + clustering:
            -> "PRIMARY KEY ((user_id), activity_time)"

        Example 3 - Multi-column partition + clustering:
            -> "PRIMARY KEY ((tenant_id, user_id), created_at, event_id)"
        """
        pk_constraint = entity.get_primary_key()
        if not pk_constraint or not pk_constraint.unique_properties:
            return None

        partition_cols = []
        clustering_cols = []

        for up in pk_constraint.unique_properties:
            attr = entity.get_attribute_by_id(up.property_id)
            if not attr:
                continue

            if up.primary_key_type == PKTypeEnum.PARTITION:
                partition_cols.append(attr.attr_name)
            elif up.primary_key_type == PKTypeEnum.CLUSTERING:
                clustering_cols.append(attr.attr_name)
            else:
                # SIMPLE or unknown -> treat as partition key
                partition_cols.append(attr.attr_name)

        if not partition_cols:
            return None

        if clustering_cols:
            # Composite: PRIMARY KEY ((part1, part2), clust1, clust2)
            partition_str = ", ".join(partition_cols)
            clustering_str = ", ".join(clustering_cols)
            return f"PRIMARY KEY (({partition_str}), {clustering_str})"
        else:
            # Partition only: PRIMARY KEY (col1, col2)
            partition_str = ", ".join(partition_cols)
            return f"PRIMARY KEY ({partition_str})"

    @classmethod
    def export_to_cql_file(cls, database: Database, file_path: str) -> None:
        """
        Export to CQL file.

        Example:
            CassandraAdapter.export_to_cql_file(database, "output.cql")
        """
        cql = cls.export_to_cql(database)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cql)

    @classmethod
    def export(cls, database: Database) -> str:
        """
        Convenience method that calls export_to_cql(db).

        Example:
            cql_ddl = CassandraAdapter.export(database)
        """
        return cls.export_to_cql(database)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
#
# Example 1: Parse Cassandra CQL DDL to Unified Meta Schema
# ----------------------------------------------------------
#
# cql_content = '''
# CREATE TABLE users (
#     user_id UUID,
#     name TEXT,
#     email TEXT,
#     PRIMARY KEY (user_id)
# );
#
# CREATE TABLE user_activity (
#     user_id UUID,
#     activity_time TIMESTAMP,
#     action TEXT,
#     details TEXT,
#     PRIMARY KEY ((user_id), activity_time)
# );
# '''
#
# adapter = CassandraAdapter()
# database = adapter.parse(cql_content, db_name="mydb")
#
# Result:
#   database.db_name = "mydb"
#   database.db_type = DatabaseType.COLUMNAR
#   database.entity_types = {
#       "users": EntityType(
#           object_name=["users"],
#           entity_kind=EntityKind.WIDE_COLUMN_TABLE,
#           attributes=[
#               Attribute("user_id", UUID, is_key=True),
#               Attribute("name", STRING, is_optional=True),
#               Attribute("email", STRING, is_optional=True)
#           ],
#           constraints=[UniqueConstraint(
#               is_primary_key=True,
#               unique_properties=[
#                   UniqueProperty(PKTypeEnum.PARTITION, user_id.meta_id)
#               ]
#           )]
#       ),
#       "user_activity": EntityType(
#           object_name=["user_activity"],
#           entity_kind=EntityKind.WIDE_COLUMN_TABLE,
#           attributes=[
#               Attribute("user_id", UUID, is_key=True),
#               Attribute("activity_time", TIMESTAMP, is_key=True),
#               Attribute("action", STRING),
#               Attribute("details", STRING)
#           ],
#           constraints=[UniqueConstraint(
#               is_primary_key=True,
#               unique_properties=[
#                   UniqueProperty(PKTypeEnum.PARTITION, user_id.meta_id),
#                   UniqueProperty(PKTypeEnum.CLUSTERING, activity_time.meta_id)
#               ]
#           )]
#       )
#   }
#
#
# Example 2: Load from file
# -------------------------
#
# database = CassandraAdapter.load_from_file("schema.cql", db_name="mydb")
#
#
# Example 3: Export back to Cassandra CQL DDL
# --------------------------------------------
#
# cql_ddl = CassandraAdapter.export_to_cql(database)
# print(cql_ddl)
#
# Output:
#   -- Cassandra Schema
#   -- Generated by SMEL
#
#   CREATE TABLE users (
#       user_id UUID,
#       name TEXT,
#       email TEXT,
#       PRIMARY KEY (user_id)
#   );
#
#   CREATE TABLE user_activity (
#       user_id UUID,
#       activity_time TIMESTAMP,
#       action TEXT,
#       details TEXT,
#       PRIMARY KEY ((user_id), activity_time)
#   );
#
#
# Example 4: Export to file
# -------------------------
#
# CassandraAdapter.export_to_cql_file(database, "output.cql")
#
#
# Example 5: Convenience export method
# -------------------------------------
#
# cql_ddl = CassandraAdapter.export(database)
#
#
# Example 6: Composite partition key with clustering columns
# -----------------------------------------------------------
#
# cql_content = '''
# CREATE TABLE sensor_data (
#     sensor_id UUID,
#     reading_time TIMESTAMP,
#     value DOUBLE,
#     PRIMARY KEY ((sensor_id), reading_time)
# ) WITH CLUSTERING ORDER BY (reading_time DESC);
# '''
#
# adapter = CassandraAdapter()
# database = adapter.parse(cql_content, db_name="iot")
#
# sensor_data entity:
#   constraints=[UniqueConstraint(
#       is_primary_key=True,
#       unique_properties=[
#           UniqueProperty(PKTypeEnum.PARTITION, sensor_id.meta_id),
#           UniqueProperty(PKTypeEnum.CLUSTERING, reading_time.meta_id)
#       ]
#   )]
#
# Export result:
#   CREATE TABLE sensor_data (
#       sensor_id UUID,
#       reading_time TIMESTAMP,
#       value DOUBLE,
#       PRIMARY KEY ((sensor_id), reading_time)
#   );
#
