"""DatabaseAdapter — abstract base class for the four schema adapters.

Concrete subclasses (PostgreSQL / MongoDB / Neo4j / Cassandra) implement
the same three-method contract:

* ``load_from_file(path, db_name)``  — reverse-engineer a native file → Database
* ``parse(content, db_name)``        — reverse-engineer in-memory native text → Database
* ``export(database)``               — forward-engineer Database → native text

Adapters whose native format is JSON (MongoDB, optionally Neo4j) accept the
*string* form on ``parse``; they ``json.loads`` internally. Neo4j additionally
auto-detects JSON vs Cypher input. This unifies the call surface so callers
never need to ask "what format does this particular adapter want?".

Shared parsing helpers (``_remove_sql_comments``, ``_split_columns``) live on
this base class as static methods so the SQL-style adapters (PostgreSQL and
Cassandra) can reuse them without duplicating identical regex / state-machine
logic in each file.
"""
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from Schema.unified_meta_schema import Database


class DatabaseAdapter(ABC):
    """Common interface every database adapter must implement."""

    @classmethod
    @abstractmethod
    def load_from_file(cls, file_path: str, db_name: Optional[str] = None) -> Database:
        """Read a native schema file (DDL / JSON / Cypher / CQL) and return a Database."""
        ...

    @classmethod
    @abstractmethod
    def export(cls, database: Database) -> str:
        """Render a Database back to its native text form."""
        ...

    @abstractmethod
    def parse(self, content: str, db_name: str = "database") -> Database:
        """Parse in-memory native schema content into a Database.

        ``content`` is always a string. Adapters whose native format is JSON
        call ``json.loads`` internally before consuming it.
        """
        ...

    # ----------------------------------------------------------------------
    # Shared SQL-style helpers (used by PostgreSQL and Cassandra adapters).
    # MongoDB uses JSON parsing and Neo4j a custom comment-driven format,
    # so they don't need these.
    # ----------------------------------------------------------------------

    @staticmethod
    def _remove_sql_comments(ddl: str) -> str:
        """Strip SQL-style ``--`` line comments and ``/* ... */`` block comments.

        Used by both PostgreSQL DDL and Cassandra CQL because their comment
        syntax is identical. Neo4j's Cypher uses ``//`` line comments and is
        not handled here.
        """
        # Remove single-line comments (-- ...)
        ddl = re.sub(r'--.*$', '', ddl, flags=re.MULTILINE)
        # Remove multi-line comments (/* ... */)
        ddl = re.sub(r'/\*.*?\*/', '', ddl, flags=re.DOTALL)
        return ddl

    @staticmethod
    def _split_columns(body: str) -> List[str]:
        """Split a CREATE TABLE body on top-level commas, ignoring those
        inside parentheses.

        A naïve ``body.split(',')`` mis-splits on commas inside type or
        constraint expressions, e.g. ``DECIMAL(15,2)`` or
        ``PRIMARY KEY ((part_col), clust_col)``. This helper tracks paren
        depth and only splits when ``depth == 0``.

        Example:
            "id INT, price DECIMAL(15,2), PRIMARY KEY ((a), b)"
            -> ["id INT", "price DECIMAL(15,2)", "PRIMARY KEY ((a), b)"]
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
                result.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            result.append(current.strip())

        return result
