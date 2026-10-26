"""
curator.web.deps - FastAPI dependency injection.

Provides database connection, config manager, and query loader as
FastAPI dependencies for use in route handlers.

The database connection is managed by dbkit, which reads connection
parameters from ~/.config/dev-utils/config.yaml under the 'dbkit:' key.
Passwords are handled by ~/.pgpass — no credentials in code or config.

Usage:
    from curator.web.deps import get_db, get_config, get_query_loader

    @router.get("/")
    async def my_route(
        db: AsyncDBConnection = Depends(get_db),
        config: ConfigManager = Depends(get_config),
        loader: QueryLoader = Depends(get_query_loader),
    ):
        repo = ProjectRepository(db, loader)
        ...
"""

from typing import AsyncGenerator

from dbkit.connection import AsyncDBConnection
from fastapi import Depends

from curator.config import ConfigManager
from viewkit import QueryBuilder, QueryLoader


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
# Query Loader
# ---------------------------------------------------------------------------

def get_query_loader(
    config: ConfigManager = Depends(get_config),
) -> QueryLoader:
    """
    Return a QueryLoader instance backed by queries.yaml.

    The path to queries.yaml is resolved by ConfigManager using the
    standard config hierarchy: user override in ~/.config/curator/
    takes precedence over shipped defaults in curator/data/.

    Args:
        config: ConfigManager providing the queries.yaml path.

    Returns:
        A QueryLoader ready for use by repository classes.
    """
    builder = QueryBuilder(config.queries_path)
    return QueryLoader(builder)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

async def get_db(
    config: ConfigManager = Depends(get_config),  # pylint: disable=unused-argument
) -> AsyncGenerator[AsyncDBConnection, None]:
    """
    Yield an open AsyncDBConnection for the duration of a request.

    Opens a connection on entry, yields it to the route handler,
    then closes it on exit regardless of whether an exception occurred.

    dbkit reads connection parameters from:
        ~/.config/dev-utils/config.yaml  (host, port, dbname, user)
        ~/.pgpass                         (password)

    Yields:
        An open AsyncDBConnection.
    """
    db = AsyncDBConnection()
    try:
        await db.__aenter__()
        yield db
    finally:
        await db.__aexit__(None, None, None)
