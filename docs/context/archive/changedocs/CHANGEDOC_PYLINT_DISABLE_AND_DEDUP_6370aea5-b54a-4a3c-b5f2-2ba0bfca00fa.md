# Changedoc: Fix misplaced pylint disable + extract duplicated save/refetch pattern

**Date:** 2026-07-04
**Reason:** Two remaining `pylint src/` findings, addressed together since
both are cleanup on code this session already touched. Final-newline and
missing-docstring findings are explicitly out of scope per your request.

**No test changes expected or included.** The extraction in part 2 is a
pure internal refactor — same `db.fetch_one()` call sequence, same
response shapes, same error paths. Verify with `pytest tests/unit/` after
applying; expect 24/24, unchanged from before this changedoc.

---

## 1. `src/curator/web/routes/crew.py` — misplaced disable comment

**Why:** `_render_crew_dashboard_html` takes 6 parameters and is the one
that actually needs the pylint exception. The explanation for that was
sitting as a comment above `crew_dashboard` instead (which only takes 5
and never triggered the warning), and it was prose, not a real
`# pylint: disable=...` directive — so it never suppressed anything to
begin with. This also folds in the two fixes already applied and
confirmed working this session (`.sql()` instead of `.build()`, and the
`jsonable_encoder` wrap on `run_query()`), so this is the complete
current file with just the comment relocated.

### BEFORE (complete file)

```python
"""Crew role dashboard routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.formkit import FormActions
from curator.web.deps import get_config, get_db
from curator.web.routes.contacts import _fetch_contacts
from curator.web.routes.organizations import _fetch_organizations
from curator.web.routes.projects import _fetch_records

# Initialize QueryLoader for /api/query endpoint
_QUERIES_PATH = Path(__file__).parent.parent.parent / "data" / "queries.yaml"
_FORMS_PATH   = Path(__file__).parent.parent.parent / "data" / "forms.yaml"
_query_builder = QueryBuilder(_QUERIES_PATH)
_query_loader  = QueryLoader(_query_builder)

router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Tab definitions per role — static, read-only, shared across all requests.
# Each tab references a partial in templates/partials/.
# Future: load from database (identity.landing_card).
_ROLE_TABS = {
    "captain": [
        {"id": "projects",      "label": "Projects",      "template": "_tab_projects.html"},
        {"id": "identities",    "label": "Identities",    "template": "_tab_identities.html"},
        {
            "id": "configuration",
            "label": "Configuration",
            "template": "_tab_configuration.html",
        },
    ],
    "scribe": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
    "mechanic": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
    "envoy": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
}
_DEFAULT_TABS = [
    {"id": "projects", "label": "Projects", "template": "_tab_projects.html"}
]


async def _fetch_lookups(db: AsyncDBConnection) -> dict:
    """Fetch project type and status lookup tables.

    Returns dict with 'types' and 'statuses' lists of dicts.
    Each dict has 'id' and 'name' keys.
    """
    types_sql = "SELECT id, name::text FROM projects.project_type ORDER BY name"
    statuses_sql = "SELECT id, name::text FROM projects.project_status ORDER BY name"

    types = await db.fetch_all(types_sql)
    statuses = await db.fetch_all(statuses_sql)

    return {
        "types": [dict(r) for r in types],
        "statuses": [dict(r) for r in statuses],
    }


@router.get("/api/query/{entity}/{query_name}")
async def run_query(
    entity: str,
    query_name: str,
    params: str = Query(""),
    db: AsyncDBConnection = Depends(get_db),
):
    """Generic query endpoint driven by queries.yaml.

    Used by _datasheet_with_header.html's Tabulator instances for child
    datasheets (Tasks, Emails, Phones, URLs, Organizations tabs).

    Query parameters:
        params: comma-separated string of positional SQL params

    Response is passed through jsonable_encoder() rather than returned
    as a plain dict — this endpoint serves whatever queries.yaml defines,
    present and future, and jsonable_encoder() handles types plain
    json.dumps() can't (datetime, Decimal, UUID) without every query
    author needing to remember an explicit ::text cast. queries.yaml
    should still cast consistently (see its own convention) — this is a
    backstop, not a replacement for that.
    """
    params_list = params.split(",") if params else []
    try:
        sql = _query_loader.sql(entity, query_name)
        rows = await db.fetch_all(sql, params_list)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(jsonable_encoder({"records": [dict(r) for r in rows]}))


# -- Dashboard ----------------------------------------------------------------

async def _render_crew_dashboard_html(
    role: str,
    role_meta: dict,
    config: ConfigManager,
    db: AsyncDBConnection,
    records: list,
    search: str,
):
    """Render the full crew dashboard HTML page.

    Separated from crew_dashboard() so that route handles routing/param
    fetching, and the JSON-request short-circuit for Tabulator's Ajax
    calls. The two were previously one function; separated because they
    are genuinely different jobs (serve JSON vs. render a full page) that
    happened to share a route.
    """
    lookups = await _fetch_lookups(db)

    # Fetch captain-only data
    if role == "captain":
        contacts = await _fetch_contacts(db)
        organizations = await _fetch_organizations(db)
    else:
        contacts = []
        organizations = []

    template = env.get_template("crew.html")
    detail_panel_actions = FormActions.from_yaml(_FORMS_PATH, "detail_panel")

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
        "contacts": contacts,
        "organizations": organizations,
        "tabs": _ROLE_TABS.get(role, _DEFAULT_TABS),
        "actions": detail_panel_actions["actions"],
        "container_class": detail_panel_actions["container_class"],
    }

    return HTMLResponse(template.render(**data))


@router.get("/crew")
# _render_crew_dashboard_html takes 6 parameters (one over pylint's default
# threshold of 5). All 6 are genuinely needed — role/role_meta/search
# describe the current request context, config/db/records are runtime
# dependencies. Restructuring into a context object would add indirection
# without improving clarity. Left as-is by design
async def crew_dashboard(
    request: Request,
    role: str = Query("captain"),
    search: str = Query(""),
    config: ConfigManager = Depends(get_config),
    db: AsyncDBConnection = Depends(get_db),
):
    """Crew dashboard — displays projects filtered by crew role.

    Query parameters:
        role:   One of the roles defined in curator.yaml
        search: Optional name filter (ILIKE match)

    JSON requests (Accept: application/json) return records for Tabulator.
    HTML requests return the full page template (see
    _render_crew_dashboard_html).
    """
    crew_roles = config.get("crew", "roles")
    valid_roles = [r["name"] for r in crew_roles]

    if role not in valid_roles:
        role = "captain"  # Safe fallback

    role_meta = next((r for r in crew_roles if r["name"] == role), None)

    records = await _fetch_records(db, role, search)

    # Tabulator Ajax requests — return JSON
    accept = request.headers.get("Accept", "")
    if "application/json" in accept:
        return JSONResponse({"records": records})

    return await _render_crew_dashboard_html(
        role, role_meta, config, db, records, search
    )
```

### AFTER (complete file)

```python
"""Crew role dashboard routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.formkit import FormActions
from curator.web.deps import get_config, get_db
from curator.web.routes.contacts import _fetch_contacts
from curator.web.routes.organizations import _fetch_organizations
from curator.web.routes.projects import _fetch_records

# Initialize QueryLoader for /api/query endpoint
_QUERIES_PATH = Path(__file__).parent.parent.parent / "data" / "queries.yaml"
_FORMS_PATH   = Path(__file__).parent.parent.parent / "data" / "forms.yaml"
_query_builder = QueryBuilder(_QUERIES_PATH)
_query_loader  = QueryLoader(_query_builder)

router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Tab definitions per role — static, read-only, shared across all requests.
# Each tab references a partial in templates/partials/.
# Future: load from database (identity.landing_card).
_ROLE_TABS = {
    "captain": [
        {"id": "projects",      "label": "Projects",      "template": "_tab_projects.html"},
        {"id": "identities",    "label": "Identities",    "template": "_tab_identities.html"},
        {
            "id": "configuration",
            "label": "Configuration",
            "template": "_tab_configuration.html",
        },
    ],
    "scribe": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
    "mechanic": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
    "envoy": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
}
_DEFAULT_TABS = [
    {"id": "projects", "label": "Projects", "template": "_tab_projects.html"}
]


async def _fetch_lookups(db: AsyncDBConnection) -> dict:
    """Fetch project type and status lookup tables.

    Returns dict with 'types' and 'statuses' lists of dicts.
    Each dict has 'id' and 'name' keys.
    """
    types_sql = "SELECT id, name::text FROM projects.project_type ORDER BY name"
    statuses_sql = "SELECT id, name::text FROM projects.project_status ORDER BY name"

    types = await db.fetch_all(types_sql)
    statuses = await db.fetch_all(statuses_sql)

    return {
        "types": [dict(r) for r in types],
        "statuses": [dict(r) for r in statuses],
    }


@router.get("/api/query/{entity}/{query_name}")
async def run_query(
    entity: str,
    query_name: str,
    params: str = Query(""),
    db: AsyncDBConnection = Depends(get_db),
):
    """Generic query endpoint driven by queries.yaml.

    Used by _datasheet_with_header.html's Tabulator instances for child
    datasheets (Tasks, Emails, Phones, URLs, Organizations tabs).

    Query parameters:
        params: comma-separated string of positional SQL params

    Response is passed through jsonable_encoder() rather than returned
    as a plain dict — this endpoint serves whatever queries.yaml defines,
    present and future, and jsonable_encoder() handles types plain
    json.dumps() can't (datetime, Decimal, UUID) without every query
    author needing to remember an explicit ::text cast. queries.yaml
    should still cast consistently (see its own convention) — this is a
    backstop, not a replacement for that.
    """
    params_list = params.split(",") if params else []
    try:
        sql = _query_loader.sql(entity, query_name)
        rows = await db.fetch_all(sql, params_list)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(jsonable_encoder({"records": [dict(r) for r in rows]}))


# -- Dashboard ----------------------------------------------------------------

async def _render_crew_dashboard_html(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    role: str,
    role_meta: dict,
    config: ConfigManager,
    db: AsyncDBConnection,
    records: list,
    search: str,
):
    """Render the full crew dashboard HTML page.

    Separated from crew_dashboard() so that route handles routing/param
    fetching, and the JSON-request short-circuit for Tabulator's Ajax
    calls. The two were previously one function; separated because they
    are genuinely different jobs (serve JSON vs. render a full page) that
    happened to share a route.

    Takes 6 parameters (one over pylint's default threshold of 5). All 6
    are genuinely needed — role/role_meta/search describe the current
    request context, config/db/records are runtime dependencies.
    Restructuring into a context object would add indirection without
    improving clarity. Left as-is by design, with the disable directive
    on the function that actually has 6 parameters — it used to sit as a
    prose-only comment above crew_dashboard (5 parameters, never needed
    it) and never suppressed anything, since pylint only responds to the
    real disable-comment syntax, not an explanation that reads like one.
    """
    lookups = await _fetch_lookups(db)

    # Fetch captain-only data
    if role == "captain":
        contacts = await _fetch_contacts(db)
        organizations = await _fetch_organizations(db)
    else:
        contacts = []
        organizations = []

    template = env.get_template("crew.html")
    detail_panel_actions = FormActions.from_yaml(_FORMS_PATH, "detail_panel")

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
        "contacts": contacts,
        "organizations": organizations,
        "tabs": _ROLE_TABS.get(role, _DEFAULT_TABS),
        "actions": detail_panel_actions["actions"],
        "container_class": detail_panel_actions["container_class"],
    }

    return HTMLResponse(template.render(**data))


@router.get("/crew")
async def crew_dashboard(
    request: Request,
    role: str = Query("captain"),
    search: str = Query(""),
    config: ConfigManager = Depends(get_config),
    db: AsyncDBConnection = Depends(get_db),
):
    """Crew dashboard — displays projects filtered by crew role.

    Query parameters:
        role:   One of the roles defined in curator.yaml
        search: Optional name filter (ILIKE match)

    JSON requests (Accept: application/json) return records for Tabulator.
    HTML requests return the full page template (see
    _render_crew_dashboard_html).
    """
    crew_roles = config.get("crew", "roles")
    valid_roles = [r["name"] for r in crew_roles]

    if role not in valid_roles:
        role = "captain"  # Safe fallback

    role_meta = next((r for r in crew_roles if r["name"] == role), None)

    records = await _fetch_records(db, role, search)

    # Tabulator Ajax requests — return JSON
    accept = request.headers.get("Accept", "")
    if "application/json" in accept:
        return JSONResponse({"records": records})

    return await _render_crew_dashboard_html(
        role, role_meta, config, db, records, search
    )
```

---

## 2. `src/curator/web/deps.py` — new shared helper

**Why:** `call_proc_and_refetch()` is the extracted shape of "call a save
proc, forward its rejection as-is on failure, or re-fetch and return the
flat record on success" — identical logic currently duplicated across
`projects.py`, `contacts.py`, and `organizations.py`'s four save routes.
`entity_id` distinguishes insert from update: `None` means pull the new
id from the proc's own success envelope (`envelope["data"]["id"]`);
anything else means use the already-known id (the update case).

### BEFORE (complete file)

```python
"""
curator.web.deps - FastAPI dependency injection.

Provides database connection and config manager as FastAPI
dependencies for use in route handlers. Also provides call_proc(),
a shared helper for unwrapping api.* stored-procedure JSONB envelopes —
used by every entity route module (projects.py, contacts.py,
organizations.py) that calls into the api schema.

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
```

### AFTER (complete file)

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


async def call_proc_and_refetch(
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

---

## 3. `src/curator/web/routes/projects.py`

**Why:** `save_new_project`/`save_project` now call the shared helper.
Everything else — `_fetch_project_for_display`, `_resolve_type_status_names`,
`_fetch_records`, `get_project`, `delete_project` — is unchanged.

### BEFORE (complete file)

```python
"""Project routes — CRUD for projects.projects via api.save_project /
api.delete_project.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db, call_proc, _fetch_json_scalar

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
    record = await _fetch_project_for_display(db, project_id)
    if not record:
        raise HTTPException(status_code=404, detail="Project not found")
    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {
        "name": name,
        "description": description,
        "type": type_name,
        "status": status_name,
    }

    envelope = await call_proc(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    new_id = envelope["data"]["id"]
    record = await _fetch_project_for_display(db, new_id)
    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {
        "id": project_id,
        "name": name,
        "description": description,
        "type": type_name,
        "status": status_name,
    }

    envelope = await call_proc(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    record = await _fetch_project_for_display(db, project_id)
    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    return JSONResponse(dict(record))


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
    user_id = request.state.user["user_id"] if request.state.user else None

    envelope = await call_proc(
        db,
        "SELECT api.delete_project(%s, %s)",
        (project_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
```

### AFTER (complete file)

```python
"""Project routes — CRUD for projects.projects via api.save_project /
api.delete_project.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db, call_proc, call_proc_and_refetch, _fetch_json_scalar

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
    record = await _fetch_project_for_display(db, project_id)
    if not record:
        raise HTTPException(status_code=404, detail="Project not found")
    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = request.state.user["user_id"] if request.state.user else None

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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = request.state.user["user_id"] if request.state.user else None

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
    user_id = request.state.user["user_id"] if request.state.user else None

    envelope = await call_proc(
        db,
        "SELECT api.delete_project(%s, %s)",
        (project_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
```

---

## 4. `src/curator/web/routes/contacts.py`

**Why:** `save_new_contact`/`save_contact` now call the shared helper.
`_fetch_contacts`, `_fetch_contact_for_display`, `get_contact`,
`delete_contact` are unchanged.

### BEFORE (complete file)

```python
"""Contact routes — CRUD for identity.contacts via api.save_contact /
api.delete_contact.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db, call_proc, _fetch_json_scalar

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
    record = await _fetch_contact_for_display(db, contact_id)
    if not record:
        raise HTTPException(status_code=404, detail="Contact not found")
    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {"name": name, "title": title, "notes": notes}

    envelope = await call_proc(
        db,
        "SELECT api.save_contact(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    new_id = envelope["data"]["id"]
    record = await _fetch_contact_for_display(db, new_id)
    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {"id": contact_id, "name": name, "title": title, "notes": notes}

    envelope = await call_proc(
        db,
        "SELECT api.save_contact(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    record = await _fetch_contact_for_display(db, contact_id)
    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    return JSONResponse(dict(record))


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
    user_id = request.state.user["user_id"] if request.state.user else None

    envelope = await call_proc(
        db,
        "SELECT api.delete_contact(%s, %s)",
        (contact_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
```

### AFTER (complete file)

```python
"""Contact routes — CRUD for identity.contacts via api.save_contact /
api.delete_contact.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db, call_proc, call_proc_and_refetch, _fetch_json_scalar

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
    record = await _fetch_contact_for_display(db, contact_id)
    if not record:
        raise HTTPException(status_code=404, detail="Contact not found")
    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

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
    user_id = request.state.user["user_id"] if request.state.user else None

    envelope = await call_proc(
        db,
        "SELECT api.delete_contact(%s, %s)",
        (contact_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
```

---

## 5. `src/curator/web/routes/organizations.py`

**Why:** `save_new_organization`/`save_organization` now call the shared
helper. `_fetch_organizations`, `_fetch_organization_for_display`,
`get_organization`, `delete_organization` are unchanged.

### BEFORE (complete file)

```python
"""Organization routes — CRUD for identity.organizations via
api.save_organization / api.delete_organization.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db, call_proc, _fetch_json_scalar

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
    record = await _fetch_organization_for_display(db, organization_id)
    if not record:
        raise HTTPException(status_code=404, detail="Organization not found")
    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {"name": name, "notes": notes}

    envelope = await call_proc(
        db,
        "SELECT api.save_organization(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    new_id = envelope["data"]["id"]
    record = await _fetch_organization_for_display(db, new_id)
    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {"id": organization_id, "name": name, "notes": notes}

    envelope = await call_proc(
        db,
        "SELECT api.save_organization(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    record = await _fetch_organization_for_display(db, organization_id)
    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    return JSONResponse(dict(record))


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
    user_id = request.state.user["user_id"] if request.state.user else None

    envelope = await call_proc(
        db,
        "SELECT api.delete_organization(%s, %s)",
        (organization_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
```

### AFTER (complete file)

```python
"""Organization routes — CRUD for identity.organizations via
api.save_organization / api.delete_organization.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db, call_proc, call_proc_and_refetch, _fetch_json_scalar

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
    record = await _fetch_organization_for_display(db, organization_id)
    if not record:
        raise HTTPException(status_code=404, detail="Organization not found")
    return JSONResponse(dict(record))


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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

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
    user_id = request.state.user["user_id"] if request.state.user else None

    envelope = await call_proc(
        db,
        "SELECT api.delete_organization(%s, %s)",
        (organization_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
```

---

## Apply and verify

1. `deps.py` — add `call_proc_and_refetch`, update imports
   (`HTTPException` from `fastapi`, `JSONResponse` from
   `fastapi.responses`, `Callable`/`Optional` from `typing`).
2. `crew.py` — relocate the disable comment (this is the only change;
   everything else in the file is already applied from the two prior
   changedocs).
3. `projects.py`, `contacts.py`, `organizations.py` — swap each save
   route's inline call-proc/check/refetch block for the
   `call_proc_and_refetch()` call.
4. `pytest tests/unit/` — expect 24/24, unchanged.
5. `pylint src/` — `R0913`/`R0917`/`R0801` should all be gone. Only the
   three `C0304` (missing final newline) findings should remain, which
   you're deliberately leaving for now.
6. Restart uvicorn, spot-check one save/edit through the browser for each
   entity (project, contact, organization) to confirm nothing broke in
   practice, not just in the mocked tests.
