# Changedoc: deps.py — resolve unnecessary-dunder-call warnings

**File:** `src/curator/web/deps.py`
**Date:** 2026-06-29
**Source verified:** Viewed directly from Carolyn's upload before writing
this changedoc.

## Summary

Pylint flagged `C2801: Unnecessarily calls dunder method __aenter__` twice
— once in `get_db()`, once in `get_db_direct()`. These two functions look
similar but have genuinely different lifecycles, so they get different
treatment:

- **`get_db()`** — entry and exit happen within the same function (open,
  yield, close in a `finally`). This is exactly what `async with` is for,
  so it's refactored to use it.
- **`get_db_direct()`** — entry and exit are deliberately split across two
  separate call sites: this function opens the connection and *returns*
  it; the caller (e.g. `middleware.py`'s `dispatch()`) holds it open
  across its own logic, then calls `__aexit__()` itself, possibly much
  later and in a different function entirely. `async with` cannot express
  that — it ties entry and exit to one lexical block. So this one keeps
  the manual `__aenter__()` call, with an inline disable and a comment
  explaining why, rather than being forced into a shape that would break
  the calling pattern `middleware.py` already depends on.

No behavior change in either function — `async with AsyncDBConnection() as
db` calls the same `__aenter__`/`__aexit__` methods the original
`try`/`finally` did, just via the context manager protocol instead of by
hand. This relies on `AsyncDBConnection` correctly implementing that
protocol, which it already must, since it was already being used as an
async context manager before this change.

---

## BEFORE (complete file, as uploaded)

```python
"""
curator.web.deps - FastAPI dependency injection.

Provides database connection and config manager as FastAPI
dependencies for use in route handlers.

The database connection is managed by dbkit, which reads connection
parameters from ~/.config/dev-utils/config.yaml under the 'dbkit:' key.
Passwords are handled by ~/.pgpass — no credentials in code or config.

Usage in routes:
    from curator.web.deps import get_db, get_config

    @router.get("/")
    async def my_route(
        db: AsyncDBConnection = Depends(get_db),
        config: ConfigManager = Depends(get_config),
    ):
        ...

Usage in middleware / non-route contexts (no Depends available):
    from curator.web.deps import get_db_direct

    db = await get_db_direct()
    result = await db.fetch_one(...)
    await db.__aexit__(None, None, None)
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
# Database — FastAPI dependency (use in route handlers)
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


# ---------------------------------------------------------------------------
# Database — direct async factory (use in middleware and auth routes)
# Middleware cannot use FastAPI's Depends() system, so this opens a
# connection directly. Caller is responsible for calling await db.__aexit__(None, None, None).
# ---------------------------------------------------------------------------

async def get_db_direct() -> AsyncDBConnection:
    """
    Open and return an AsyncDBConnection without the FastAPI dependency system.

    Use this in middleware, background tasks, or any context where
    Depends() is not available. Always call await db.__aexit__(None, None, None) when done.

    Returns:
        An open AsyncDBConnection.
    """
    db = AsyncDBConnection()
    await db.__aenter__()
    return db
```

## AFTER (complete file — replace the whole thing with this)

```python
"""
curator.web.deps - FastAPI dependency injection.

Provides database connection and config manager as FastAPI
dependencies for use in route handlers.

The database connection is managed by dbkit, which reads connection
parameters from ~/.config/dev-utils/config.yaml under the 'dbkit:' key.
Passwords are handled by ~/.pgpass — no credentials in code or config.

Usage in routes:
    from curator.web.deps import get_db, get_config

    @router.get("/")
    async def my_route(
        db: AsyncDBConnection = Depends(get_db),
        config: ConfigManager = Depends(get_config),
    ):
        ...

Usage in middleware / non-route contexts (no Depends available):
    from curator.web.deps import get_db_direct

    db = await get_db_direct()
    result = await db.fetch_one(...)
    await db.__aexit__(None, None, None)
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
# Database — FastAPI dependency (use in route handlers)
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
    async with AsyncDBConnection() as db:
        yield db


# ---------------------------------------------------------------------------
# Database — direct async factory (use in middleware and auth routes)
# Middleware cannot use FastAPI's Depends() system, so this opens a
# connection directly. Caller is responsible for calling await db.__aexit__(None, None, None).
# ---------------------------------------------------------------------------

async def get_db_direct() -> AsyncDBConnection:
    """
    Open and return an AsyncDBConnection without the FastAPI dependency system.

    Use this in middleware, background tasks, or any context where
    Depends() is not available. Always call await db.__aexit__(None, None, None) when done.

    Returns:
        An open AsyncDBConnection.
    """
    db = AsyncDBConnection()
    await db.__aenter__()  # pylint: disable=unnecessary-dunder-call
    # Cannot use "async with" here — entry and exit are deliberately
    # decoupled by design. The caller (e.g. middleware.py) holds this
    # connection open across a wider scope than a single "with" block
    # could express, and is responsible for calling __aexit__() itself
    # once it's done. See module docstring's "Usage in middleware" section.
    return db
```

---

## What did NOT change

- `get_db_direct()`'s actual contract — still opens and returns a
  connection, still requires the caller to close it manually. This
  changedoc does not touch `middleware.py`'s call site, which already
  correctly does `await db.__aexit__(None, None, None)` after use (see
  the middleware changedoc from earlier this session) — that pattern
  continues to work exactly as before.
- `get_config()` — untouched, no warnings on it.
- Module docstring — untouched, its "Usage" examples are still accurate.

## Verification steps

1. Replace the file as shown above.
2. Run `pylint src/curator/web/deps.py` — `get_db_direct()`'s warning
   should now show as suppressed (not absent from pylint's awareness, just
   explicitly disabled with a reason); `get_db()`'s warning should be
   genuinely resolved.
3. This file can't be meaningfully tested without a live DB connection.
   Restart the app and confirm:
   - Any route using `Depends(get_db)` still works (e.g. `/crew`,
     `/crew/projects/save`) — connection opens, query runs, connection
     closes after the response.
   - `middleware.py`'s session validation (which uses `get_db_direct()`)
     still works — login, logout, and session redirect behavior unchanged.
   - No connection leaks under normal use — if you have a way to monitor
     active PostgreSQL connections (e.g. `SELECT * FROM
     pg_stat_activity`), a quick before/after glance after a few requests
     can confirm connections are still being closed properly.
