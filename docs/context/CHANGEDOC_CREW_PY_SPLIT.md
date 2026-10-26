# Changedoc: Split `crew.py` into dashboard / projects / contacts / organizations

**Date:** 2026-07-01
**Reason:** `crew.py` had grown to cover dashboard rendering, the generic
`/api/query` datasheet endpoint, and full CRUD for three unrelated entities
(projects, contacts, organizations) in one file — directly against
`project_rules.md`'s "small modules over monoliths" / "one cohesive set of
related functions per module" rule. Splitting now, before the
fetch-and-swap detail-panel work (views, `fieldkit`, new `/panel` route)
adds more code, so the new work lands directly in the right file instead
of being written into the monolith and untangled later.

**project_rules.md reviewed — no exceptions needed.** This is a pure
mechanical reorganization: no route paths change, no response shapes
change, no SQL changes. Tests move with the code they test, per "Tests
live in tests/ and mirror the structure of src/."

**Assumption made, since not explicitly confirmed:** the test-file split
follows the rule-consistent default discussed — four files
(`test_deps.py`, `test_routes_projects.py`, `test_routes_contacts.py`,
`test_routes_organizations.py`) rather than keeping contacts+organizations
together. Easy to consolidate back if you'd rather.

**Confirmed empty, so no BEFORE block for these three:**
`src/curator/web/routes/projects.py`, `contacts.py`, `organizations.py`
(each currently contains nothing beyond what `__init__.py` already has:
`"""Curator route modules."""`).

**One thing flagged, not silently changed:** the original
`test_routes_crew.py`'s `TestProcRejectionPassthrough` test had a leftover
`print("DIAGNOSTIC: db =", db, "type:", type(db))` line — clearly
debugging output, not an assertion. Dropped it in the moved version below.
Flagging in case it was left in deliberately for a reason I don't know
about.

---

## 1. `src/curator/web/deps.py`

**Why:** `_call_proc` is used by all three entity route modules and has no
project/contact/organization-specific logic — it belongs in shared
infrastructure, not any one route file. Renamed `_call_proc` → `call_proc`
on the move: the leading underscore meant "module-private," which stopped
being true the moment a second module needed to import it.

### BEFORE

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

### AFTER

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
# Stored-procedure envelope helper
# Moved here from crew.py (2026-07-01 changedoc) — shared by every route
# module that calls an api.* proc. Not entity-specific, so it belongs in
# shared infrastructure rather than any one route file. Renamed from
# _call_proc to call_proc on the move: the leading underscore signaled
# "module-private," which stopped being true the moment a second module
# needed to import it.
# ---------------------------------------------------------------------------

async def call_proc(db: AsyncDBConnection, sql: str, params: tuple) -> dict:
    """Call a stored proc that returns a single JSONB envelope and unwrap it.

    Every api.* proc returns {"success": bool, "data": ..., "message": str}.
    fetch_one() gives back a dict keyed by the proc's column name (e.g.
    {"save_project": {...}}); this pulls out that single value and parses
    it if dbkit returned it as a JSON string rather than an already-decoded
    dict (encoding-dependent — see dbkit client_encoding note in handoff).

    Returns the envelope dict: {"success": ..., "data": ..., "message": ...}
    """
    result = await db.fetch_one(sql, params)
    envelope = list(result.values())[0]
    if isinstance(envelope, str):
        envelope = json.loads(envelope)
    return envelope
```

---

## 2. `src/curator/web/routes/crew.py`

**Why:** Sheds everything project/contact/organization-specific, keeping
only what's genuinely about the dashboard shell: tab definitions, the
lookup-table fetch, the dashboard renderer/route, and the generic
`/api/query` child-datasheet endpoint (which isn't entity-specific either
— it's driven entirely by `queries.yaml`). Now imports `_fetch_records`
from `projects.py` and `_fetch_contacts`/`_fetch_organizations` from
`contacts.py`/`organizations.py` instead of defining them locally, so
"how to fetch a contact" has exactly one home regardless of whether it's
a single record or the dashboard's list view.

### BEFORE

The full 827-line file as it exists today (dashboard + `/api/query` +
full projects/contacts/organizations CRUD + `_call_proc`) — not repeated
here in full since every route/helper being removed is shown in its new
location in sections 3–5 below, verbatim except for import paths.

### AFTER (complete file)

```python
"""Crew role dashboard routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
    """
    params_list = params.split(",") if params else []
    try:
        sql = _query_loader.build(entity, query_name)
        rows = await db.fetch_all(sql, params_list)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"records": [dict(r) for r in rows]})


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

**Import note:** `json` and `Response` are no longer imported — nothing
left in `crew.py` uses them (both were only needed by the CRUD routes
that moved out).

---

## 3. `src/curator/web/routes/projects.py` (new — file confirmed empty)

**Why:** Full project CRUD, previously in `crew.py`, now self-contained.
`_fetch_records` stays exported (not renamed) since `crew.py`'s
`crew_dashboard()` still needs it for the role-filtered project list.

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
from curator.web.deps import get_db, call_proc

router = APIRouter()


async def _fetch_project_for_display(db: AsyncDBConnection, project_id: int) -> dict:
    """Fetch a project with joined type and status names for display.

    Returns dict with id, name, slug, description, type, status,
    type_id, status_id keys.
    """
    sql = """
        SELECT
            p.id,
            p.name::text,
            p.slug::text,
            p.description::text,
            p.type_id,
            p.status_id,
            ps.name::text  AS status,
            pt.name::text  AS type
        FROM projects.projects p
        LEFT JOIN projects.project_status ps ON ps.id = p.status_id
        LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
        WHERE p.id = %s
    """
    return await db.fetch_one(sql, (project_id,))


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

---

## 4. `src/curator/web/routes/contacts.py` (new — file confirmed empty)

**Why:** Full contact CRUD, previously in `crew.py`, now self-contained.
`_fetch_contacts` stays exported (not renamed) since `crew.py`'s dashboard
renderer needs it for the captain Identities tab.

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
from curator.web.deps import get_db, call_proc

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
    """Fetch a single contact for the detail panel.

    Returns dict with id, name, title, notes keys.
    """
    sql = """
        SELECT
            c.id,
            c.name::text,
            c.title::text,
            c.notes::text
        FROM identity.contacts c
        WHERE c.id = %s
    """
    return await db.fetch_one(sql, (contact_id,))


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

---

## 5. `src/curator/web/routes/organizations.py` (new — file confirmed empty)

**Why:** Full organization CRUD, previously in `crew.py`, now
self-contained. `_fetch_organizations` stays exported for the same reason
`_fetch_contacts` does.

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
from curator.web.deps import get_db, call_proc

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
    """Fetch a single organization for the detail panel.

    Returns dict with id, name, notes keys.
    """
    sql = """
        SELECT
            o.id,
            o.name::text,
            o.notes::text
        FROM identity.organizations o
        WHERE o.id = %s
    """
    return await db.fetch_one(sql, (organization_id,))


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

---

## 6. `src/curator/web/app.py`

**Why:** Three new routers need registering. Route paths inside each
module are unchanged (`/crew/projects/...` etc.), so nothing about
request handling changes — this is purely wiring the new modules in.

### BEFORE

```python
"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from curator.web.middleware import SessionMiddleware
from curator.web.routes import landing, crew
from curator.web.routes import auth

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
)

# ---------------------------------------------------------------------------
# Middleware
# Must be added before routers are registered.
# SessionMiddleware validates curator_session cookie on every request.
# ---------------------------------------------------------------------------

app.add_middleware(SessionMiddleware)

# ---------------------------------------------------------------------------
# Static files — resolved relative to this file: src/curator/web/ -> static/
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parents[3] / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Routers
# Auth must be registered first — /auth/login is the public entry point.
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

### AFTER

```python
"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from curator.web.middleware import SessionMiddleware
from curator.web.routes import auth, landing, crew, projects, contacts, organizations

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
)

# ---------------------------------------------------------------------------
# Middleware
# Must be added before routers are registered.
# SessionMiddleware validates curator_session cookie on every request.
# ---------------------------------------------------------------------------

app.add_middleware(SessionMiddleware)

# ---------------------------------------------------------------------------
# Static files — resolved relative to this file: src/curator/web/ -> static/
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parents[3] / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Routers
# Auth must be registered first — /auth/login is the public entry point.
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)
app.include_router(projects.router)
app.include_router(contacts.router)
app.include_router(organizations.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

---

## 7. Test files

**Why:** Tests move with the code they test. `TestCallProc` follows
`call_proc` to `deps.py`. The remaining `test_routes_crew.py` classes
(all project-specific) become `test_routes_projects.py`.
`test_routes_crew_identities.py` splits along its existing
contact/organization section boundary into two files. `make_mock_request`
stays duplicated across the three route-test files, matching the existing
documented tradeoff in `test_routes_crew_identities.py` (pytest doesn't
resolve cross-file bare imports under this project's `tests/unit/`
discovery setup).

**Action: delete** `tests/unit/test_routes_crew.py` and
`tests/unit/test_routes_crew_identities.py` after the four files below
are in place and passing — their content fully relocates, nothing is
left behind in either.

### 7a. `tests/unit/test_deps.py` (new)

```python
"""
Unit tests for curator.web.deps

Scope: call_proc()'s envelope unwrapping — moved here from
test_routes_crew.py's TestCallProc class as part of the crew.py route
split (2026-07-01). call_proc itself also moved, from crew.py to deps.py,
and was renamed from _call_proc (see deps.py changedoc entry for why).

These are unit tests, not integration tests: the database connection is
mocked throughout. Nothing here makes a real connection to PostgreSQL.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web import deps


def make_mock_db_for_proc(envelope) -> SimpleNamespace:
    """Build a fake db whose fetch_one() returns a single-key dict wrapping
    the given envelope — matching the real shape dbkit returns for
    `SELECT api.some_proc(...)` (e.g. {"save_project": {...}}).

    envelope may be a dict (simulating dbkit already having decoded JSONB
    to a Python dict) or a JSON string (simulating the case where it comes
    back as a raw string and call_proc must json.loads() it itself).
    """
    return SimpleNamespace(
        fetch_one=AsyncMock(return_value={"some_proc_name": envelope})
    )


class TestCallProc:
    """call_proc must correctly unwrap a proc's JSONB envelope regardless
    of whether dbkit hands it back as an already-decoded dict or as a raw
    JSON string — this ambiguity was flagged as unverified during the
    original crew.py -> api schema migration and is exactly the kind of
    thing that should be pinned down by a test rather than left as an
    assumption.
    """

    @pytest.mark.asyncio
    async def test_unwraps_dict_envelope(self):
        """When dbkit already returns a decoded dict, call_proc should
        pass it through unchanged, not double-parse it."""
        envelope = {"success": True, "data": {"id": 42}, "message": None}
        db = make_mock_db_for_proc(envelope)

        result = await deps.call_proc(db, "SELECT api.fake_proc(%s)", (1,))

        assert result == envelope
        assert result["success"] is True
        assert result["data"]["id"] == 42

    @pytest.mark.asyncio
    async def test_unwraps_json_string_envelope(self):
        """When dbkit returns the envelope as a raw JSON string (the
        encoding-dependent case noted in call_proc's docstring),
        call_proc must json.loads() it before returning."""
        envelope_dict = {"success": False, "data": None, "message": "Not found."}
        envelope_str = json.dumps(envelope_dict)
        db = make_mock_db_for_proc(envelope_str)

        result = await deps.call_proc(db, "SELECT api.fake_proc(%s)", (1,))

        assert result == envelope_dict
        assert result["success"] is False
        assert result["message"] == "Not found."

    @pytest.mark.asyncio
    async def test_passes_sql_and_params_through_unchanged(self):
        """call_proc shouldn't alter the SQL or params it was given —
        confirms it's a thin pass-through to fetch_one, not doing any
        SQL construction of its own."""
        db = make_mock_db_for_proc({"success": True, "data": None, "message": None})
        sql = "SELECT api.save_project(%s, %s)"
        params = ('{"name": "Test"}', 7)

        await deps.call_proc(db, sql, params)

        db.fetch_one.assert_awaited_once_with(sql, params)
```

### 7b. `tests/unit/test_routes_projects.py` (replaces `test_routes_crew.py`)

```python
"""
Unit tests for curator.web.routes.projects

Scope: the save routes' guard clauses (empty name) that return before
ever touching the database, and the proc-rejection passthrough contract.
Split out of test_routes_crew.py as part of the crew.py route split
(2026-07-01) — projects.save_new_project / save_project moved to their
own module, and _call_proc's envelope-unwrapping tests moved to
test_deps.py alongside call_proc itself.

These are unit tests, not integration tests: the database connection is
mocked throughout. Nothing here makes a real connection to PostgreSQL.
Integration tests against the real wcyj database are deferred until the
Contacts/Tasks forms are designed and their procs exist — see
tests/integration/ for where those will eventually live.

Note: importing curator.web.routes.projects triggers no module-level
YAML reads (unlike the old crew.py, which read queries.yaml/forms.yaml
at import time for the /api/query endpoint and dashboard rendering —
those stayed in crew.py). projects.py has no import-time filesystem
dependency.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import projects


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Build a minimal fake Request with just what the save routes read.

    The real save routes only touch request.json() and
    request.state.user["user_id"] — nothing else about the real Starlette
    Request object is needed for these tests, so a SimpleNamespace stands
    in rather than constructing or mocking the full Request class.
    """
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


class TestSaveNewProjectGuard:
    """The empty-name check in save_new_project is meant to short-circuit
    before any database call. These tests confirm that guard actually
    fires and that the database is never touched when it does — if a
    future edit accidentally moves the check after the proc call, or
    removes it, these should fail.
    """

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "type_id": None,
                                      "status_id": None, "description": None})
        db = SimpleNamespace(fetch_one=AsyncMock())  # should never be called

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_name_is_treated_as_empty(self):
        """The route does name.strip() before checking — a name of only
        spaces should be rejected the same as a truly empty string."""
        request = make_mock_request({"name": "   ", "type_id": None,
                                      "status_id": None, "description": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Name is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_name_key_entirely_is_treated_as_empty(self):
        """body.get("name") on a payload with no "name" key at all should
        behave the same as an explicit empty string, not raise a KeyError."""
        request = make_mock_request({"type_id": None, "status_id": None,
                                      "description": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


class TestSaveProjectGuard:
    """Same guard, same reasoning, applied to the update route — kept as
    a separate test class since save_project takes project_id as a
    parameter the new-project route doesn't have, so the call shape
    differs slightly even though the guard logic is identical.
    """

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "type_id": None,
                                      "status_id": None, "description": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await projects.save_project(project_id=22, request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


class TestProcRejectionPassthrough:
    """Confirms the route correctly forwards a proc's full rejection
    envelope (including the "data" field used for the conflicting_id
    feature) without dropping or reshaping any of it. This is the bug
    class that caused the silent duplicate-name failure in an earlier
    session (saveForm() couldn't tell success from failure because the
    route's response shape was inconsistent) — a regression here should
    fail loudly, not silently.
    """

    @pytest.mark.asyncio
    async def test_duplicate_name_rejection_forwards_data_and_message(self):
        request = make_mock_request({
            "name": "Existing Project", "type_id": None,
            "status_id": None, "description": None,
        })

        rejection_envelope = {
            "success": False,
            "data": {"conflicting_id": 99},
            "message": "A project with that name already exists.",
        }

        # First fetch_one call (inside call_proc) returns the rejection.
        # _resolve_type_status_names won't call fetch_one at all here since
        # both type_id and status_id are None in this payload.
        db = SimpleNamespace(fetch_one=AsyncMock(return_value={
            "save_project": rejection_envelope
        }))

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "A project with that name already exists."
        assert body["data"] == {"conflicting_id": 99}

    @pytest.mark.asyncio
    async def test_success_response_has_no_success_key(self):
        """On success, the route returns the flat project record with no
        "success" key at all — this is the exact distinction saveForm()
        in detail-panel.js relies on (body.success === False, not
        res.ok) to tell success from failure. A test pinning this down
        protects that contract from an accidental future change."""
        request = make_mock_request({
            "name": "New Project", "type_id": None,
            "status_id": None, "description": None,
        })

        save_envelope = {
            "success": True,
            "data": {"id": 123},
            "message": None,
        }
        display_record = {
            "id": 123, "name": "New Project", "slug": "new-project",
            "description": None, "type_id": None, "status_id": None,
            "status": None, "type": None,
        }

        # fetch_one is called twice in the success path:
        #   1. inside call_proc, for the SELECT api.save_project(...) call
        #   2. inside _fetch_project_for_display, for the re-fetch by id
        db = SimpleNamespace(fetch_one=AsyncMock(side_effect=[
            {"save_project": save_envelope},
            display_record,
        ]))

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 123
        assert body["name"] == "New Project"
```

### 7c. `tests/unit/test_routes_contacts.py` (new, split from `test_routes_crew_identities.py`)

```python
"""
Unit tests for curator.web.routes.contacts

Scope: mirrors test_routes_projects.py's guard/success-shape coverage,
applied to the contact save/delete routes. Split out of
test_routes_crew_identities.py as part of the crew.py route split
(2026-07-01) — contacts.py is now its own module.

Same conventions as test_routes_projects.py:
- Unit tests only, database connection mocked throughout.
- make_mock_request is duplicated here rather than imported (see note
  below the imports) — pytest does not resolve cross-file bare imports
  in tests/unit/ under this project's discovery setup.
- Keyword arguments used for every route call, per project convention.

api.save_contact has no duplicate-name check (contacts.name is not
UNIQUE), so there is no contact-side equivalent of
TestOrganizationDuplicateNameRejection in test_routes_organizations.py.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import contacts


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Build a minimal fake Request with just what the save routes read."""
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


class TestSaveNewContactGuard:
    """Same empty-name short-circuit as TestSaveNewProjectGuard, applied to
    contacts. Contacts have no type_id/status_id/description fields —
    payload shape is name/title/notes instead.
    """

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()  # should never be called

        response = await contacts.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_name_is_treated_as_empty(self):
        request = make_mock_request({"name": "   ", "title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await contacts.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Name is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_name_key_entirely_is_treated_as_empty(self):
        request = make_mock_request({"title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await contacts.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


class TestSaveContactGuard:
    """Same guard applied to the update route — save_contact takes
    contact_id as a parameter the new-contact route doesn't have."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await contacts.save_contact(contact_id=5, request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


class TestContactSuccessResponseShape:
    """Pins down that a successful save returns the flat contact record
    with no "success" key, which is what saveForm() in detail-panel.js
    relies on to tell success from failure.
    """

    @pytest.mark.asyncio
    async def test_success_response_has_no_success_key(self):
        request = make_mock_request({
            "name": "Andrea Flores", "title": "Purchasing Manager", "notes": None,
        })

        save_envelope = {
            "success": True,
            "data": {"id": 200},
            "message": "Contact created.",
        }
        display_record = {
            "id": 200, "name": "Andrea Flores",
            "title": "Purchasing Manager", "notes": None,
        }

        # fetch_one is called twice in the success path:
        #   1. inside call_proc, for the SELECT api.save_contact(...) call
        #   2. inside _fetch_contact_for_display, for the re-fetch by id
        db = AsyncMock()
        db.fetch_one = AsyncMock(side_effect=[
            {"save_contact": save_envelope},
            display_record,
        ])

        response = await contacts.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 200
        assert body["name"] == "Andrea Flores"
        assert body["title"] == "Purchasing Manager"


class TestGetContactNotFound:
    """_fetch_contact_for_display returning None (record doesn't exist)
    should raise a 404, matching get_project's existing behavior — not
    silently return an empty/null body."""

    @pytest.mark.asyncio
    async def test_missing_contact_raises_404(self):
        from fastapi import HTTPException

        db = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await contacts.get_contact(contact_id=9999, db=db)

        assert exc_info.value.status_code == 404
```

### 7d. `tests/unit/test_routes_organizations.py` (new, split from `test_routes_crew_identities.py`)

```python
"""
Unit tests for curator.web.routes.organizations

Scope: mirrors test_routes_projects.py's guard/success-shape/rejection
coverage, applied to the organization save/delete routes. Split out of
test_routes_crew_identities.py as part of the crew.py route split
(2026-07-01) — organizations.py is now its own module.

Same conventions as test_routes_contacts.py. organizations.name IS
UNIQUE (unlike contacts.name), so this file carries the duplicate-name
rejection coverage that contacts doesn't need.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import organizations


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Build a minimal fake Request with just what the save routes read."""
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


class TestSaveNewOrganizationGuard:
    """Same empty-name short-circuit, applied to organizations. Payload
    shape is name/notes only — no title field on organizations."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_name_is_treated_as_empty(self):
        request = make_mock_request({"name": "   ", "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Name is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_name_key_entirely_is_treated_as_empty(self):
        request = make_mock_request({"notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


class TestSaveOrganizationGuard:
    """Same guard applied to the update route."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await organizations.save_organization(
            organization_id=10, request=request, db=db
        )

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


class TestOrganizationDuplicateNameRejection:
    """organizations.name IS UNIQUE, unlike contacts.name — this is the
    one place contact and organization route coverage genuinely diverges,
    not just a mechanical copy.
    """

    @pytest.mark.asyncio
    async def test_duplicate_name_rejection_forwards_message(self):
        request = make_mock_request({"name": "Bailey Ltd", "notes": None})

        rejection_envelope = {
            "success": False,
            "data": None,
            "message": "An organization with that name already exists.",
        }

        db = AsyncMock()
        db.fetch_one = AsyncMock(return_value={
            "save_organization": rejection_envelope
        })

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "An organization with that name already exists."


class TestOrganizationSuccessResponseShape:
    """Success returns the flat record, no "success" key."""

    @pytest.mark.asyncio
    async def test_success_response_has_no_success_key(self):
        request = make_mock_request({"name": "New Vendor Co", "notes": None})

        save_envelope = {
            "success": True,
            "data": {"id": 301},
            "message": "Organization created.",
        }
        display_record = {"id": 301, "name": "New Vendor Co", "notes": None}

        db = AsyncMock()
        db.fetch_one = AsyncMock(side_effect=[
            {"save_organization": save_envelope},
            display_record,
        ])

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 301
        assert body["name"] == "New Vendor Co"


class TestGetOrganizationNotFound:
    @pytest.mark.asyncio
    async def test_missing_organization_raises_404(self):
        from fastapi import HTTPException

        db = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await organizations.get_organization(organization_id=9999, db=db)

        assert exc_info.value.status_code == 404
```

---

## Apply order

1. `deps.py` — add `call_proc`, `import json`.
2. `projects.py`, `contacts.py`, `organizations.py` — write complete files.
3. `crew.py` — replace with the shrunk version (imports the three
   `_fetch_*` helpers from their new homes).
4. `app.py` — add the three router registrations.
5. Add `test_deps.py`, `test_routes_projects.py`, `test_routes_contacts.py`,
   `test_routes_organizations.py`.
6. Run the full suite (`pytest tests/unit/`) — expect 22 passing, same
   count as before, just redistributed across four files instead of two.
7. Delete `tests/unit/test_routes_crew.py` and
   `tests/unit/test_routes_crew_identities.py`.
8. `git add .`, commit (`refit: split crew.py into dashboard/projects/contacts/organizations`),
   push.
9. Restart uvicorn, manually smoke-test: `/crew` dashboard loads for each
   role, existing project/contact/organization Save/New/Exit still work
   by click and by Alt-key (per your 2026-07-01 handoff note that these
   were just confirmed working before this split).

No SQL, no template, no JS changes — this step is Python-internal only.
