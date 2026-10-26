"""Crew role dashboard routes."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.formkit import FormActions
from curator.web.deps import get_config, get_db

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


async def _call_proc(db: AsyncDBConnection, sql: str, params: tuple) -> dict:
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

    envelope = await _call_proc(
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

    envelope = await _call_proc(
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

    envelope = await _call_proc(
        db,
        "SELECT api.delete_project(%s, %s)",
        (project_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)


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

    envelope = await _call_proc(
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

    envelope = await _call_proc(
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

    envelope = await _call_proc(
        db,
        "SELECT api.delete_contact(%s, %s)",
        (contact_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)


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

    envelope = await _call_proc(
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

    envelope = await _call_proc(
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

    envelope = await _call_proc(
        db,
        "SELECT api.delete_organization(%s, %s)",
        (organization_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
