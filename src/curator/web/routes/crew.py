"""Crew role dashboard routes."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.web.deps import get_config, get_db
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader

# Initialize QueryLoader for /api/query endpoint
_QUERIES_PATH = Path(__file__).parent.parent.parent / "data" / "queries.yaml"
_query_builder = QueryBuilder(_QUERIES_PATH)
_query_loader = QueryLoader(_query_builder)

router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


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


def _make_slug(name: str) -> str:
    """Generate a URL-safe slug from a project name.

    Lowercases, replaces non-alphanumeric runs with hyphens,
    strips leading/trailing hyphens.

    Example: "WCYJ Store Website" -> "wcyj-store-website"
    """
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


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


# -- Dashboard ----------------------------------------------------------------
@router.get("/api/query/{entity}/{query_name}")
async def run_query(
    entity: str,
    query_name: str,
    params: str = Query(""),
    db: AsyncDBConnection = Depends(get_db),
):
    """Generic query endpoint for child datasheets in detail panels."""
    try:
        sql = _query_loader.sql(entity, query_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Query not found: {entity}.{query_name}"
        )
    params_list = tuple(p.strip() for p in params.split(",")) if params else ()
    try:
        rows = await db.fetch_all(sql, params_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse({"records": [dict(r) for r in rows]})

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
    HTML requests return the full page template.
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

    # Full page HTML request
    lookups = await _fetch_lookups(db)

    if role == "captain":
        template = env.get_template("captain.html")
    else:
        template = env.get_template("crew.html")

    if role == "captain":
        contacts = await _fetch_contacts(db)
        organizations = await _fetch_organizations(db)
    else:
        contacts = []
        organizations = []

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
    }

    return HTMLResponse(template.render(**data))



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

@router.post("/crew/projects/save", response_class=HTMLResponse)
async def save_new_project(
    request: Request,
    role: str = Query("captain"),
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project from Tabulator add row.

    Accepts JSON body: {name, type_id, status_id}
    Returns display row HTML on success.
    Returns 409 text on duplicate name, 422 text on missing name.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None

    if not name:
        return HTMLResponse("Name is required", status_code=422)

    slug = _make_slug(name)

    existing = await db.fetch_one(
        "SELECT id FROM projects.projects WHERE slug = %s",
        (slug,)
    )
    if existing:
        return HTMLResponse(
            f'A project named "{name}" already exists.',
            status_code=409
        )

    result = await db.fetch_one(
        """
        INSERT INTO projects.projects (name, slug, type_id, status_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (name, slug, type_id, status_id)
    )
    new_id = result["id"]

    record = await _fetch_project_for_display(db, new_id)
    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    template = env.get_template("_crew_row_display.html")
    return HTMLResponse(template.render(record=record))


@router.post("/crew/projects/{project_id}/save", response_class=HTMLResponse)
async def save_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing project from Tabulator.

    Accepts JSON body: {name, type_id, status_id}
    Returns updated display row HTML on success.
    Returns 422 text on missing name.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None

    if not name:
        return HTMLResponse("Name is required", status_code=422)

    await db.execute(
        """
        UPDATE projects.projects
        SET name = %s, type_id = %s, status_id = %s
        WHERE id = %s
        """,
        (name, type_id, status_id, project_id)
    )

    record = await _fetch_project_for_display(db, project_id)
    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    template = env.get_template("_crew_row_display.html")
    return HTMLResponse(template.render(record=record))
