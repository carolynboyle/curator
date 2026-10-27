# Changedoc: extract duplicated route patterns into `deps.py`

**Date:** 2026-07-04
**Reason:** `contacts.py`/`organizations.py`/`projects.py` each repeat four
identical or near-identical patterns — caught by inspection, not by
`pylint`'s `R0801` (the two smallest ones are almost certainly below its
minimum matching-lines threshold; the two larger ones may or may not
trip it today, but definitely will once Tasks adds a fourth copy of
each). Fixing this now, before Tasks exists, means Tasks's routes get
written against the shared helpers from day one instead of adding a
fourth copy that then needs its own cleanup pass.

**Source verified:** all three route files viewed directly from your
latest uploads; `deps.py` matches the version already confirmed working
this session (`_fetch_json_scalar`, `call_proc`, `call_proc_and_refetch`
all present and unchanged).

**Scope check against `project_rules.md`:** direct application of
"DRY — if the same logic appears in two places, it belongs in one place."
No new exceptions.

---

## What's being extracted

1. **`get_user_id(request)`** — replaces
   `request.state.user["user_id"] if request.state.user else None`,
   identical in all 9 save/delete routes across the three files.
2. **`require_name(name)`** — replaces
   `if not name: return JSONResponse({"success": False, "message": "Name is required.", "data": None})`,
   identical in both save routes (new + edit) across all three files.
3. **`get_detail_or_404(db, fetch_fn, record_id, not_found_detail)`** —
   replaces the fetch-or-404 body of `get_contact`/`get_organization`/
   `get_project`, identical except which fetch function and message
   string each uses.
4. **`delete_via_proc(db, proc_sql, proc_params)`** — replaces the
   call-proc-or-return-failure body of `delete_contact`/
   `delete_organization`/`delete_project`, identical except the proc SQL
   string.

`call_proc_and_refetch` (already extracted 2026-07-04) is untouched —
this is four *more* small pieces of the same kind of duplication it
already addressed, just smaller and previously missed.

---

## 1. `src/curator/web/deps.py` (edit — complete file)

### BEFORE (complete file, as uploaded)

```python
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
```

### AFTER (complete file — replace the whole thing with this)

```python
"""
curator.web.deps - FastAPI dependency injection.

Provides database connection and config manager as FastAPI
dependencies for use in route handlers. Also provides shared helpers
for the patterns repeated across every entity's routes
(projects.py, contacts.py, organizations.py):

    call_proc                - unwrap an api.* proc's JSONB envelope
    call_proc_and_refetch    - save, then re-fetch and return the record
    get_user_id              - pull user_id off request.state.user
    require_name             - reject a blank "name" field
    get_detail_or_404        - fetch-for-display, or raise 404
    delete_via_proc          - call a delete proc, 204 or failure envelope

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
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

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


# ---------------------------------------------------------------------------
# Route-pattern helpers
# Extracted from contacts.py/organizations.py/projects.py (2026-07-04) —
# each of these four patterns was identical or near-identical across all
# three entities' routes. Missed by the earlier R0801-driven cleanup
# pass since these are smaller than that pass's target, but the same
# "one canonical implementation" reasoning applies.
# ---------------------------------------------------------------------------

def get_user_id(request: Request) -> Optional[int]:
    """Return request.state.user["user_id"], or None if unauthenticated.

    Identical one-liner previously repeated in every save/delete route
    across contacts.py/organizations.py/projects.py (9 call sites).
    """
    return request.state.user["user_id"] if request.state.user else None


def require_name(name: str) -> Optional[JSONResponse]:
    """Return a rejection response if name is blank, else None.

    Usage:
        rejection = require_name(name)
        if rejection:
            return rejection

    Identical guard previously repeated in every save-new/save-edit
    route across contacts.py/organizations.py/projects.py (6 call sites).
    """
    if not name:
        return JSONResponse({
            "success": False,
            "message": "Name is required.",
            "data": None,
        })
    return None


async def get_detail_or_404(
    db: AsyncDBConnection,
    fetch_fn: Callable,
    record_id: int,
    not_found_detail: str,
) -> JSONResponse:
    """Fetch a single record for the detail panel, or raise 404.

    Extracted from get_contact/get_organization/get_project — identical
    shape in all three, differing only in which fetch_fn and 404 message
    to use.

    Args:
        db:               Open connection.
        fetch_fn:         The entity's _fetch_x_for_display function,
                           called as fetch_fn(db, record_id).
        record_id:        ID to fetch.
        not_found_detail: HTTPException detail message if not found.

    Returns:
        JSONResponse wrapping the record.

    Raises:
        HTTPException(404): if fetch_fn returns a falsy value.
    """
    record = await fetch_fn(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return JSONResponse(dict(record))


async def delete_via_proc(
    db: AsyncDBConnection,
    proc_sql: str,
    proc_params: tuple,
) -> Response:
    """Call a delete proc and return 204, or the failure envelope.

    Extracted from delete_contact/delete_organization/delete_project —
    identical shape in all three, differing only in the proc SQL string
    and params.

    Args:
        db:          Open connection.
        proc_sql:    The "SELECT api.delete_x(%s, %s)" string.
        proc_params: Params for that call (typically entity_id, user_id).

    Returns:
        Response(204) on success, or a JSONResponse with the failure
        envelope ({"success": false, "message": ...}) on failure.
    """
    envelope = await call_proc(db, proc_sql, proc_params)
    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})
    return Response(status_code=204)
```

---

## 2. `src/curator/web/routes/contacts.py` (edit — complete file)

### BEFORE

*(as uploaded — full file already in your last message, not repeated
here to keep this changedoc from ballooning further; the AFTER block
below is the complete replacement, diffed against exactly that upload.)*

### AFTER (complete file — replace the whole thing with this)

```python
"""Contact routes — CRUD for identity.contacts via api.save_contact /
api.delete_contact.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    get_db,
    call_proc_and_refetch,
    delete_via_proc,
    get_detail_or_404,
    get_user_id,
    require_name,
    _fetch_json_scalar,
)

router = APIRouter()


async def _fetch_contacts(db: AsyncDBConnection) -> list:
    """Fetch all contacts with their first email address.

    Returns list of dicts: id, name, title, email, org_ids.
    org_ids is a list of organization IDs this contact belongs to.
    email is the first address from contact_emails, or None.
    """
    sql = """
        SELECT
            c.id,
            c.name::text,
            c.title::text,
            (
                SELECT ce.address::text
                FROM identity.contact_emails ce
                WHERE ce.contact_id = c.id
                ORDER BY ce.id
                LIMIT 1
            ) AS email,
            COALESCE(
                ARRAY_AGG(oc.organization_id) FILTER (WHERE oc.organization_id IS NOT NULL),
                '{}'
            ) AS org_ids
        FROM identity.contacts c
        LEFT JOIN identity.organization_contacts oc ON oc.contact_id = c.id
        GROUP BY c.id, c.name, c.title
        ORDER BY c.name
    """
    rows = await db.fetch_all(sql)
    result = []
    for r in rows:
        d = dict(r)
        # org_ids comes back as a PostgreSQL array — ensure it's a plain list
        d["org_ids"] = list(d["org_ids"]) if d["org_ids"] else []
        result.append(d)
    return result


async def _fetch_contact_for_display(db: AsyncDBConnection, contact_id: int) -> dict:
    """Fetch a contact via api.get_contact_detail() for the detail panel.

    Returns dict with id, name, title, notes keys — matches the old
    direct query's shape exactly, since identity.v_contact_detail has no
    extra joined columns to lose — or None if not found.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_contact_detail(%s)", (contact_id,)
    )


# -- Single contact fetch (for detail panel) -----------------------------------

@router.get("/crew/contacts/{contact_id}")
async def get_contact(
    contact_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single contact as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_contact_for_display, contact_id, "Contact not found"
    )


# -- Contact save routes --------------------------------------------------------
# /crew/contacts/save must be declared before /crew/contacts/{contact_id}/save
# to prevent "save" matching as a contact_id integer.

@router.post("/crew/contacts/save")
async def save_new_contact(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new contact via api.save_contact().

    Accepts JSON body: {name, title, notes}
    Returns the new contact record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    title = body.get("title") or None
    notes = body.get("notes") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {"name": name, "title": title, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_contact(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_contact_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/crew/contacts/{contact_id}/save")
async def save_contact(
    contact_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing contact via api.save_contact().

    Accepts JSON body: {name, title, notes}
    Returns the updated contact record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, contact not found.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    title = body.get("title") or None
    notes = body.get("notes") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {"id": contact_id, "name": name, "title": title, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_contact(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_contact_for_display,
        contact_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/crew/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete a contact by id via api.delete_contact().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. not found, or blocked by dependent records (foreign key violation).
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_contact(%s, %s)", (contact_id, user_id)
    )
```

---

## 3. `src/curator/web/routes/organizations.py` (edit — complete file)

### AFTER (complete file — replace the whole thing with this)

```python
"""Organization routes — CRUD for identity.organizations via
api.save_organization / api.delete_organization.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    get_db,
    call_proc_and_refetch,
    delete_via_proc,
    get_detail_or_404,
    get_user_id,
    require_name,
    _fetch_json_scalar,
)

router = APIRouter()


async def _fetch_organizations(db: AsyncDBConnection) -> list:
    """Fetch all organizations with their contact IDs.

    Returns list of dicts: id, name, contact_ids.
    contact_ids is a list of contact IDs belonging to this org.
    """
    sql = """
        SELECT
            o.id,
            o.name::text,
            COALESCE(
                ARRAY_AGG(oc.contact_id) FILTER (WHERE oc.contact_id IS NOT NULL),
                '{}'
            ) AS contact_ids
        FROM identity.organizations o
        LEFT JOIN identity.organization_contacts oc ON oc.organization_id = o.id
        GROUP BY o.id, o.name
        ORDER BY o.name
    """
    rows = await db.fetch_all(sql)
    result = []
    for r in rows:
        d = dict(r)
        d["contact_ids"] = list(d["contact_ids"]) if d["contact_ids"] else []
        result.append(d)
    return result


async def _fetch_organization_for_display(db: AsyncDBConnection, organization_id: int) -> dict:
    """Fetch an organization via api.get_organization_detail() for the
    detail panel.

    Returns dict with id, name, notes keys — matches the old direct
    query's shape exactly — or None if not found.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_organization_detail(%s)", (organization_id,)
    )


# -- Single organization fetch (for detail panel) ------------------------------

@router.get("/crew/organizations/{organization_id}")
async def get_organization(
    organization_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single organization as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_organization_for_display, organization_id, "Organization not found"
    )


# -- Organization save routes ---------------------------------------------------
# /crew/organizations/save must be declared before
# /crew/organizations/{organization_id}/save to prevent "save" matching as
# an organization_id integer.

@router.post("/crew/organizations/save")
async def save_new_organization(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new organization via api.save_organization().

    Accepts JSON body: {name, notes}
    Returns the new organization record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, duplicate name.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    notes = body.get("notes") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {"name": name, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_organization(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_organization_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/crew/organizations/{organization_id}/save")
async def save_organization(
    organization_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing organization via api.save_organization().

    Accepts JSON body: {name, notes}
    Returns the updated organization record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, duplicate name, organization not found.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    notes = body.get("notes") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {"id": organization_id, "name": name, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_organization(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_organization_for_display,
        organization_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/crew/organizations/{organization_id}")
async def delete_organization(
    organization_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete an organization by id via api.delete_organization().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. not found, or blocked by dependent records (foreign key violation).
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_organization(%s, %s)", (organization_id, user_id)
    )
```

---

## 4. `src/curator/web/routes/projects.py` (edit — complete file)

**Note:** `_resolve_type_status_names` and `_fetch_records` are untouched
— they're projects-specific (type/status name lookup, role-filtered
listing) with no equivalent in contacts/organizations, so there's nothing
to extract there. Only the four cross-entity patterns change.

### AFTER (complete file — replace the whole thing with this)

```python
"""Project routes — CRUD for projects.projects via api.save_project /
api.delete_project.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    get_db,
    call_proc_and_refetch,
    delete_via_proc,
    get_detail_or_404,
    get_user_id,
    require_name,
    _fetch_json_scalar,
)

router = APIRouter()


async def _fetch_project_for_display(db: AsyncDBConnection, project_id: int) -> dict:
    """Fetch a project via api.get_project_detail() for the detail panel.

    Returns dict with id, name, description, type_id, status_id keys —
    the columns in projects.v_project_detail — or None if not found.

    No longer returns joined type/status *name* strings (the old direct
    query's `type`/`status` columns) or `slug`: v_project_detail is a
    whitelist of editable fields only. Nothing downstream reads those —
    detail-panel.js's populateForm() only maps name/type_id/status_id/
    description/title.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_project_detail(%s)", (project_id,)
    )


async def _resolve_type_status_names(
    db: AsyncDBConnection, type_id, status_id
) -> tuple:
    """Look up type and status name strings from their ids.

    api.save_project() takes name strings, not ids, so the browser's
    type_id/status_id selections are translated here before the proc call.
    Either id may be None; returns (type_name, status_name), each possibly
    None if not found or not provided.
    """
    type_name = None
    if type_id:
        row = await db.fetch_one(
            "SELECT name FROM projects.project_type WHERE id = %s", (type_id,)
        )
        type_name = row["name"] if row else None

    status_name = None
    if status_id:
        row = await db.fetch_one(
            "SELECT name FROM projects.project_status WHERE id = %s", (status_id,)
        )
        status_name = row["name"] if row else None

    return type_name, status_name


async def _fetch_records(db: AsyncDBConnection, role: str, search: str) -> list:
    """Fetch role-filtered projects, optionally filtered by search term.

    Returns list of dicts with id, name, type, type_id, status, status_id.
    """
    view_name = f"projects.{role}_view"

    if search:
        sql = f"""
            SELECT
                p.id,
                p.name::text,
                p.slug::text,
                p.description::text,
                ps.name::text  AS status,
                pt.name::text  AS type,
                p.type_id,
                p.status_id
            FROM {view_name} p
            LEFT JOIN projects.project_status ps ON ps.id = p.status_id
            LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
            WHERE p.name ILIKE %s
            ORDER BY p.name
        """
        rows = await db.fetch_all(sql, (f"%{search}%",))
    else:
        sql = f"""
            SELECT
                p.id,
                p.name::text,
                p.slug::text,
                p.description::text,
                ps.name::text  AS status,
                pt.name::text  AS type,
                p.type_id,
                p.status_id
            FROM {view_name} p
            LEFT JOIN projects.project_status ps ON ps.id = p.status_id
            LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
            ORDER BY p.name
        """
        rows = await db.fetch_all(sql)

    return [dict(r) for r in rows]


# -- Single project fetch (for detail panel) ----------------------------------

@router.get("/crew/projects/{project_id}")
async def get_project(
    project_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single project as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_project_for_display, project_id, "Project not found"
    )


# -- Project save routes ------------------------------------------------------
# /crew/projects/save must be declared before /crew/projects/{project_id}/save
# to prevent "save" matching as a project_id integer.

@router.post("/crew/projects/save")
async def save_new_project(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project via api.save_project().

    Accepts JSON body: {name, type_id, status_id, description}
    Returns the new project record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, duplicate name. The message is
    proc-supplied and safe to display directly in the UI. data is None
    for most failures but may carry extra context (e.g. conflicting_id
    on a duplicate-name rejection) for future UI features to consume.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None
    description = body.get("description") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = get_user_id(request)

    payload = {
        "name": name,
        "description": description,
        "type": type_name,
        "status": status_name,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_project_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/crew/projects/{project_id}/save")
async def save_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing project via api.save_project().

    Accepts JSON body: {name, type_id, status_id, description}
    Returns the updated project record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, duplicate name, project not found. data
    is None for most failures but may carry extra context (e.g.
    conflicting_id on a duplicate-name rejection) for future UI features
    to consume.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None
    description = body.get("description") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = get_user_id(request)

    payload = {
        "id": project_id,
        "name": name,
        "description": description,
        "type": type_name,
        "status": status_name,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_project_for_display,
        project_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/crew/projects/{project_id}")
async def delete_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete a project by id via api.delete_project().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. not found, or blocked by dependent records (foreign key violation).
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_project(%s, %s)", (project_id, user_id)
    )
```

---

## Apply and verify

1. Replace `deps.py` with the AFTER block — adds `Request` and
   `Response` imports, adds the four new functions, nothing existing
   changes shape.
2. Replace `contacts.py`, `organizations.py`, `projects.py` with their
   AFTER blocks. Note `HTTPException` is no longer imported directly in
   any of the three — `get_detail_or_404` raises it internally now, and
   nothing else in these files used it.
3. **Existing unit tests will need updating** — `test_routes_contacts.py`,
   `test_routes_organizations.py`, `test_routes_projects.py` currently
   assert against the old inline shapes. The 404/delete tests in
   particular may need their mocks adjusted since the logic moved into
   `deps.get_detail_or_404`/`deps.delete_via_proc` — worth a quick look
   at whether any test patches something at the wrong location (e.g.
   patching `contacts.HTTPException` that no longer exists there).
4. `pytest` — expect all existing tests to still pass once step 3's
   adjustments are made; flag anything that breaks rather than silently
   loosening an assertion to make it pass.
5. `pylint src/` — should stay at 10.00/10.
6. Restart `uvicorn`, spot-check one save/edit/delete through the
   browser for each entity to confirm nothing broke in practice.

---

## Not touched, flagged for later

`_fetch_records`'s two nearly-identical SQL blocks (search vs. no-search)
within `projects.py` are a *separate*, smaller duplication — within one
file, not across files — and weren't part of what you asked about here.
Worth a look eventually (a single query with `WHERE (%s = '' OR p.name
ILIKE %s)`-style conditional would collapse it to one block), but not
bundled into this changedoc since it's an unrelated concern.
