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
"""
from abc import ABC, abstractmethod
from typing import Optional

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
