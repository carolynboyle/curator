"""
curator.web.deps - FastAPI dependency injection.

Provides database connection and config manager as FastAPI
dependencies for use in route handlers. Also provides call_proc(),
a shared helper for unwrapping api.* stored-procedure JSONB envelopes,
and call_proc_and_refetch(), which wraps the common "save, then re-fetch
the record" pattern shared by every entity's save routes (projects.py,
contacts.py, organizations.py).

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

import json
from typing import AsyncGenerator, Callable, Optional

from dbkit.connection import AsyncDBConnection
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse

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


# ---------------------------------------------------------------------------
# Stored-procedure / detail-fetch envelope helpers
# Moved here from crew.py (2026-07-01 changedoc) — shared by every route
# module that calls an api.* function. Not entity-specific, so it belongs
# in shared infrastructure rather than any one route file.
# ---------------------------------------------------------------------------

async def _fetch_json_scalar(db: AsyncDBConnection, sql: str, params: tuple):
    """Call a function/proc returning a single JSON(B) column and unwrap it.

    fetch_one() gives back a dict keyed by the function's column name
    (e.g. {"get_project_detail": {...}} or {"save_project": {...}});
    this pulls out that single value and parses it if dbkit returned it
    as a JSON string rather than an already-decoded dict
    (encoding-dependent — see dbkit client_encoding note in handoff).

    Returns whatever that single value is: a dict (proc envelope or
    detail record), or None if the column itself is NULL — e.g.
    api.get_project_detail() finding no matching row. Callers that
    always expect a value (call_proc, below) never see None in practice;
    callers that might get a miss (the detail-fetch functions in
    projects.py/contacts.py/organizations.py) check for it themselves.
    """
    result = await db.fetch_one(sql, params)
    value = list(result.values())[0]
    if isinstance(value, str):
        value = json.loads(value)
    return value


async def call_proc(db: AsyncDBConnection, sql: str, params: tuple) -> dict:
    """Call a stored proc that returns a single JSONB envelope and unwrap it.

    Every api.* proc returns {"success": bool, "data": ..., "message": str}.
    Thin wrapper over _fetch_json_scalar — kept as its own name since
    "call a proc and get its envelope" reads more clearly at call sites
    than the more general _fetch_json_scalar would, even though the
    underlying mechanics are identical.

    Returns the envelope dict: {"success": ..., "data": ..., "message": ...}
    """
    return await _fetch_json_scalar(db, sql, params)


async def call_proc_and_refetch(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    db: AsyncDBConnection,
    proc_sql: str,
    proc_params: tuple,
    fetch_fn: Callable,
    entity_id: Optional[int],
    not_found_detail: str,
) -> JSONResponse:
    """Call a save proc, then re-fetch and return the saved record.

    Extracted from projects.py/contacts.py/organizations.py's save
    routes (2026-07-04 changedoc) — every one of them called a proc,
    checked its envelope, and either forwarded a rejection as-is or
    re-fetched the record and returned it flat. Same shape every time;
    this is the one canonical implementation instead of four near-copies.

    Args:
        db:               Open connection.
        proc_sql:         The "SELECT api.save_x(%s, %s)" string.
        proc_params:      Params for that call (typically the JSON
                           payload string and user_id).
        fetch_fn:         The entity's _fetch_x_for_display function —
                           called as fetch_fn(db, record_id).
        entity_id:        None for an insert (the new id is pulled from
                           the proc's own success envelope,
                           envelope["data"]["id"]); the already-known id
                           for an update (contact_id, project_id, etc.).
        not_found_detail: HTTPException detail message if the re-fetch
                           comes back empty (proc succeeded but the
                           record can't be found — shouldn't normally
                           happen, but distinguishes insert vs. update
                           failure messages, matching each route's
                           existing wording).

    Returns:
        JSONResponse — either the proc's rejection envelope
        ({"success": false, "message": ..., "data": ...}), or the flat
        saved record with no "success" key (the contract saveForm() in
        detail-panel.js relies on).

    Raises:
        HTTPException(500): if the proc succeeded but the re-fetch
        returns nothing.
    """
    envelope = await call_proc(db, proc_sql, proc_params)

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    record_id = entity_id if entity_id is not None else envelope["data"]["id"]
    record = await fetch_fn(db, record_id)
    if not record:
        raise HTTPException(status_code=500, detail=not_found_detail)

    return JSONResponse(dict(record))
