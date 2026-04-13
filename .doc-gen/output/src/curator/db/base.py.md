# base.py

**Path:** src/curator/db/base.py
**Syntax:** python
**Generated:** 2026-04-13 04:51:40

```python
"""
curator.db.base - Generic async base repository.

Provides shared query helpers for all repository classes. Each
repository receives an AsyncDBConnection from the FastAPI dependency
layer — BaseRepository does not open or close connections.

All query methods delegate directly to the connection's methods,
providing a consistent interface and a single place to add
cross-cutting concerns (logging, metrics) in future.

Usage:
    class ProjectRepository(BaseRepository):
        async def get_all(self) -> list[dict]:
            return await self.fetch_all("SELECT * FROM v_projects")
"""

from dbkit.connection import AsyncDBConnection


class BaseRepository:
    """
    Base class for all Curator repositories.

    Wraps an AsyncDBConnection and exposes query helpers.
    Instantiate with an open connection from the FastAPI
    dependency layer.

    Args:
        db: An open AsyncDBConnection instance.
    """

    def __init__(self, db: AsyncDBConnection):
        self._db = db

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
        return await self.fetch_all(
            f"SELECT * FROM {table} ORDER BY {order_by}"
        )
    
```
