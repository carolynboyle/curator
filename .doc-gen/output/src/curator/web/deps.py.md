# deps.py

**Path:** src/curator/web/deps.py
**Syntax:** python
**Generated:** 2026-06-23 12:09:21

```python
"""Dependency injection for Curator routes."""

from typing import AsyncGenerator

from dbkit.connection import AsyncDBConnection

from curator.config import ConfigManager


async def get_db() -> AsyncGenerator[AsyncDBConnection, None]:
    """Yield a database connection per request.

    Closes on exit regardless of outcome.
    """
    db = AsyncDBConnection()
    try:
        await db.__aenter__()
        yield db
    finally:
        await db.__aexit__(None, None, None)


def get_config() -> ConfigManager:
    """Get the ConfigManager instance."""
    return ConfigManager()
```
