"""
PostgreSQL Adapter - Parse SQL DDL to Unified Meta Schema.
Converts CREATE TABLE statements to Database/EntityType/Attribute objects.
"""
import re
from typing import Dict, List, Optional, Tuple
from ..unified_meta_schema import (
    Database, DatabaseType, EntityType, Attribute, Key, KeyType,
    Reference, Cardinality, PrimitiveDataType, PrimitiveType
)


class PostgreSQLAdapter:
    """Adapter to parse PostgreSQL DDL and create Unified Meta Schema."""

    # PostgreSQL type to PrimitiveType mapping
    TYPE_MAP = {
        'SERIAL': PrimitiveType.INTEGER,
        'BIGSERIAL': PrimitiveType.LONG,
        'INTEGER': PrimitiveType.INTEGER,
        'INT': PrimitiveType.INTEGER,
        'BIGINT': PrimitiveType.LONG,
        'SMALLINT': PrimitiveType.INTEGER,
        'DECIMAL': PrimitiveType.DECIMAL,
        'NUMERIC': PrimitiveType.DECIMAL,
        'REAL': PrimitiveType.FLOAT,
        'DOUBLE PRECISION': PrimitiveType.DOUBLE,
        'FLOAT': PrimitiveType.FLOAT,
        'VARCHAR': PrimitiveType.STRING,
        'CHAR': PrimitiveType.STRING,
        'TEXT': PrimitiveType.STRING,  # TEXT and VARCHAR both map to STRING for MongoDB compatibility
        'BOOLEAN': PrimitiveType.BOOLEAN,
        'BOOL': PrimitiveType.BOOLEAN,
        'DATE': PrimitiveType.DATE,
        'TIMESTAMP': PrimitiveType.TIMESTAMP,
        'TIME': PrimitiveType.TIMESTAMP,
        'UUID': PrimitiveType.UUID,
        'BYTEA': PrimitiveType.BINARY,
        'JSON': PrimitiveType.STRING,
        'JSONB': PrimitiveType.STRING,
    }

    def __init__(self):
        self.database: Optional[Database] = None
        self._pending_references: List[Tuple[str, str, str]] = []  # (entity, ref_name, target)

    def parse(self, ddl_content: str, db_name: str = "database") -> Database:
        """Parse SQL DDL content and return Database object."""
        self.database = Database(db_name=db_name, db_type=DatabaseType.RELATIONAL)
        self._pending_references = []

        # Remove comments
        ddl = self._remove_comments(ddl_content)

        # Parse CREATE TABLE statements
        tables = self._extract_create_tables(ddl)

        for table_name, table_body in tables:
            entity = self._parse_table(table_name, table_body)
            self.database.add_entity_type(entity)

        # Resolve references after all entities are created
        self._resolve_references()

        return self.database

    def _remove_comments(self, ddl: str) -> str:
        """Remove SQL comments."""
        # Remove single-line comments
        ddl = re.sub(r'--.*$', '', ddl, flags=re.MULTILINE)
        # Remove multi-line comments
        ddl = re.sub(r'/\*.*?\*/', '', ddl, flags=re.DOTALL)
        return ddl

    def _extract_create_tables(self, ddl: str) -> List[Tuple[str, str]]:
        """Extract CREATE TABLE statements."""
        pattern = r'CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);'
        matches = re.findall(pattern, ddl, re.IGNORECASE | re.DOTALL)
        return matches

    def _parse_table(self, table_name: str, table_body: str) -> EntityType:
        """Parse a single CREATE TABLE body."""
        entity = EntityType(en_name=table_name.lower())

        # Split by comma, but handle parentheses in type definitions
        columns = self._split_columns(table_body)

        for col_def in columns:
            col_def = col_def.strip()
            if not col_def:
                continue

            # Skip constraint definitions
            upper = col_def.upper()
            if any(upper.startswith(kw) for kw in ['PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK', 'CONSTRAINT']):
                continue

            # Parse column
            attr, ref_info = self._parse_column(col_def)
            if attr:
                entity.add_attribute(attr)

                # Handle PRIMARY KEY in column definition
                if 'PRIMARY KEY' in col_def.upper():
                    key = Key(key_type=KeyType.PRIMARY)
                    key.add_attribute(attr)
                    entity.add_key(key)

                # Store reference for later resolution
                if ref_info:
                    self._pending_references.append((entity.en_name, ref_info[0], ref_info[1]))

        # Create primary key if SERIAL is used
        if not entity.get_primary_key():
            for attr in entity.attributes:
                if attr.is_key:
                    key = Key(key_type=KeyType.PRIMARY)
                    key.add_attribute(attr)
                    entity.add_key(key)
                    break

        return entity

    def _split_columns(self, body: str) -> List[str]:
        """Split column definitions, handling nested parentheses."""
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
                result.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            result.append(current.strip())

        return result

    def _parse_column(self, col_def: str) -> Tuple[Optional[Attribute], Optional[Tuple[str, str]]]:
        """Parse a single column definition."""
        # Normalize whitespace (handle multi-line definitions)
        col_def = ' '.join(col_def.split())

        # Pattern: column_name TYPE [constraints] [REFERENCES table(col)]
        pattern = r'^(\w+)\s+(\w+(?:\s+PRECISION)?)\s*(?:\(([^)]+)\))?\s*(.*)?$'
        match = re.match(pattern, col_def.strip(), re.IGNORECASE)

        if not match:
            return None, None

        col_name = match.group(1).lower()
        col_type = match.group(2).upper()
        type_params = match.group(3)  # e.g., "35" for VARCHAR(35), "15,2" for DECIMAL(15,2)
        constraints = match.group(4) or ""

        # Determine data type
        data_type = self._parse_data_type(col_type, type_params)

        # Check constraints
        is_key = 'PRIMARY KEY' in constraints.upper() or col_type in ('SERIAL', 'BIGSERIAL')
        is_optional = 'NOT NULL' not in constraints.upper() and not is_key

        attr = Attribute(
            attr_name=col_name,
            data_type=data_type,
            is_key=is_key,
            is_optional=is_optional
        )

        # Check for REFERENCES
        ref_info = None
        ref_match = re.search(r'REFERENCES\s+(\w+)\s*\((\w+)\)', constraints, re.IGNORECASE)
        if ref_match:
            ref_info = (col_name, ref_match.group(1).lower())

        return attr, ref_info

    def _parse_data_type(self, type_name: str, params: Optional[str]) -> PrimitiveDataType:
        """Parse SQL type to PrimitiveDataType."""
        primitive = self.TYPE_MAP.get(type_name, PrimitiveType.STRING)

        max_length = None
        precision = None
        scale = None

        if params:
            parts = [p.strip() for p in params.split(',')]
            if primitive in (PrimitiveType.STRING, PrimitiveType.TEXT):
                max_length = int(parts[0]) if parts else None
            elif primitive == PrimitiveType.DECIMAL:
                precision = int(parts[0]) if parts else None
                scale = int(parts[1]) if len(parts) > 1 else 0

        return PrimitiveDataType(
            primitive_type=primitive,
            max_length=max_length,
            precision=precision,
            scale=scale
        )

    def _resolve_references(self):
        """Resolve foreign key references after all entities are created."""
        for entity_name, ref_name, target_name in self._pending_references:
            entity = self.database.get_entity_type(entity_name)
            target = self.database.get_entity_type(target_name)

            if entity and target:
                # Check if attribute exists (it might be the FK column)
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
        """Load SQL DDL from file and parse to Database."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if db_name is None:
            from pathlib import Path
            db_name = Path(file_path).stem

        adapter = PostgreSQLAdapter()
        return adapter.parse(content, db_name)

    # ========== Export Methods ==========

    # Reverse mapping: PrimitiveType -> SQL type
    REVERSE_TYPE_MAP = {
        PrimitiveType.INTEGER: 'INTEGER',
        PrimitiveType.LONG: 'BIGINT',
        PrimitiveType.STRING: 'VARCHAR',
        PrimitiveType.TEXT: 'TEXT',
        PrimitiveType.DECIMAL: 'DECIMAL',
        PrimitiveType.FLOAT: 'REAL',
        PrimitiveType.DOUBLE: 'DOUBLE PRECISION',
        PrimitiveType.BOOLEAN: 'BOOLEAN',
        PrimitiveType.DATE: 'DATE',
        PrimitiveType.TIMESTAMP: 'TIMESTAMP',
        PrimitiveType.UUID: 'UUID',
        PrimitiveType.BINARY: 'BYTEA',
    }

    @classmethod
    def export_to_sql(cls, database: Database) -> str:
        """
        Export Unified Meta Schema to PostgreSQL DDL format.

        Args:
            database: The Database object to export

        Returns:
            PostgreSQL DDL as a string
        """
        lines = []
        lines.append("-- PostgreSQL Schema (Generated by SMEL)")
        lines.append(f"-- Database: {database.db_name}")
        lines.append("")

        # Sort entities by dependency order (entities with no FK first)
        sorted_entities = cls._sort_entities_by_dependency(database)

        for entity in sorted_entities:
            ddl = cls._export_entity_to_ddl(entity, database)
            lines.append(ddl)
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def _sort_entities_by_dependency(cls, database: Database) -> list:
        """Sort entities so that referenced tables come before referencing tables."""
        entities = list(database.entity_types.values())

        # Build dependency graph
        dependencies = {}
        for entity in entities:
            deps = set()
            for rel in entity.relationships:
                if isinstance(rel, Reference):
                    target = rel.get_target_entity_name()
                    if target != entity.en_name:  # Avoid self-reference
                        deps.add(target)
            dependencies[entity.en_name] = deps

        # Topological sort
        sorted_names = []
        visited = set()

        def visit(name):
            if name in visited:
                return
            visited.add(name)
            for dep in dependencies.get(name, []):
                if dep in dependencies:  # Only visit if entity exists
                    visit(dep)
            sorted_names.append(name)

        for name in dependencies:
            visit(name)

        return [database.get_entity_type(name) for name in sorted_names if database.get_entity_type(name)]

    @classmethod
    def _export_entity_to_ddl(cls, entity: EntityType, database: Database) -> str:
        """Export a single entity to CREATE TABLE statement."""
        lines = []
        lines.append(f"CREATE TABLE {entity.en_name} (")

        columns = []
        constraints = []

        # Find FK relationships
        fk_refs = {}
        for rel in entity.relationships:
            if isinstance(rel, Reference):
                fk_refs[rel.ref_name] = rel

        # Process attributes
        for attr in entity.attributes:
            col_def = cls._export_attribute_to_column(attr, fk_refs.get(attr.attr_name), database)
            columns.append(f"    {col_def}")

        # Add FK constraints as inline REFERENCES
        # (already handled in _export_attribute_to_column)

        lines.append(",\n".join(columns))
        lines.append(");")

        return "\n".join(lines)

    @classmethod
    def _export_attribute_to_column(cls, attr: Attribute, fk_ref: Reference = None, database: Database = None) -> str:
        """Export an attribute to column definition."""
        parts = [attr.attr_name]

        # Data type
        sql_type = cls._get_sql_type(attr)
        parts.append(sql_type)

        # PRIMARY KEY
        if attr.is_key:
            parts.append("PRIMARY KEY")
        # NOT NULL (if not optional and not PK)
        elif not attr.is_optional:
            parts.append("NOT NULL")

        # REFERENCES (FK)
        if fk_ref:
            target_entity_name = fk_ref.get_target_entity_name()
            # Find target PK column from database metadata
            target_pk_name = cls._get_target_pk_name(target_entity_name, database)
            parts.append(f"REFERENCES {target_entity_name}({target_pk_name})")

        return " ".join(parts)

    @classmethod
    def _get_sql_type(cls, attr: Attribute) -> str:
        """Get SQL type from attribute."""
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

        # Use SERIAL for integer PKs
        if base_type == 'INTEGER' and attr.is_key:
            return 'SERIAL'

        return base_type

    @classmethod
    def _get_target_pk_name(cls, entity_name: str, database: Database = None) -> str:
        """Get the PK column name for an entity from database metadata."""
        # Try to get PK from database metadata
        if database:
            target_entity = database.get_entity_type(entity_name)
            if target_entity:
                pk = target_entity.get_primary_key()
                if pk and pk.key_attributes:
                    return pk.key_attributes[0].attr_name

        # Fallback: default naming convention
        return f"{entity_name}_id"

    @classmethod
    def export_to_sql_file(cls, database: Database, file_path: str) -> None:
        """Export to SQL file."""
        sql = cls.export_to_sql(database)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sql)
