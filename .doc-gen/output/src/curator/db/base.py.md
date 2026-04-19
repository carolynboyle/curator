# base.py

**Path:** src/curator/db/base.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
curator.db.base - Generic async base repository.

Provides shared query helpers for all repository classes. Each
repository receives an AsyncDBConnection and a QueryLoader from
the FastAPI dependency layer — BaseRepository does not open or
close connections, and does not load YAML.

All query methods delegate directly to the connection's methods,
providing a consistent interface and a single place to add
cross-cutting concerns (logging, metrics) in future.

Usage:
    class ProjectRepository(BaseRepository):
        async def get_all(self) -> list[dict]:
            return await self.fetch_all(self._q.sql("projects", "get_all"))
"""

from typing import Optional

from dbkit.connection import AsyncDBConnection
from dbkit.resolver import SlugResolver

from viewkit import QueryLoader


class BaseRepository:
    """
    Base class for all Curator repositories.

    Wraps an AsyncDBConnection and exposes query helpers.
    Optionally receives a QueryLoader for externalised SQL lookups.

    Args:
        db:     An open AsyncDBConnection instance.
        loader: Optional QueryLoader for YAML-driven SQL lookups.
    """

    def __init__(self, db: AsyncDBConnection, loader: Optional[QueryLoader] = None):
        self._db = db
        self._resolver = SlugResolver(db)
        self._q = loader

    # -- Query helpers --------------------------------------------------------

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """Fetch all matching rows as a list of dicts."""
        return await self._db.fetch_all(sql, params)

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Fetch a single row as a dict, or None."""
        return await self._db.fetch_one(sql, params)

    async def fetch_scalar(self, sql: str, params: tuple = ()):
        """Fetch a single value from the first column of the first row."""
        return await self._db.fetch_scalar(sql, params)

    async def execute(self, sql: str, params: tuple = ()) -> None:
        """Execute a statement with no return value."""
        return await self._db.execute(sql, params)

    # -- Lookup helpers -------------------------------------------------------

    async def get_lookup_options(
        self, table: str, order_by: str = "sort_order"
    ) -> list[dict]:
        """
        Return all rows from a lookup table for populating select fields.

        Args:
            table:    Lookup table name (e.g. "task_status", "priority").
            order_by: Column to sort by. Defaults to "sort_order".

        Returns:
            List of dicts, one per row.
        """
        return self._resolver.get_all(table, order_by)

```
