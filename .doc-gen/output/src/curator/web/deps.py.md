# deps.py

**Path:** src/curator/web/deps.py
**Syntax:** python
**Generated:** 2026-04-13 04:51:40

```python
"""
curator.web.deps - FastAPI dependency injection.

Provides database connection and config manager as FastAPI
dependencies for use in route handlers.

Usage:
    from curator.web.deps import get_db, get_config

    @router.get("/")
    async def my_route(
        db: AsyncDBConnection = Depends(get_db),
        config: ConfigManager = Depends(get_config),
    ):
        ...
"""

from typing import AsyncGenerator

from dbkit.connection import AsyncDBConnection
from fastapi import Depends

from curator.config import ConfigManager


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def get_config() -> ConfigManager:
    """
    Return a ConfigManager instance.

    A new instance is created per request. ConfigManager is lightweight
    — it reads from disk once at construction and caches in memory.
    """
    return ConfigManager()


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

async def get_db(
    config: ConfigManager = Depends(get_config),
) -> AsyncGenerator[AsyncDBConnection, None]:
    """
    Yield an open AsyncDBConnection for the duration of a request.

    Opens a connection on entry, yields it to the route handler,
    then closes it on exit regardless of whether an exception occurred.

    Args:
        config: ConfigManager instance from get_config().

    Yields:
        An open AsyncDBConnection.
    """
    db = AsyncDBConnection(config.get_section("database"))
    try:
        await db.open()
        yield db
    finally:
        await db.close()
```
