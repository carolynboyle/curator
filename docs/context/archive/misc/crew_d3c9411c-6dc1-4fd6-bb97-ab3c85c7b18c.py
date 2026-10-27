"""Crew role dashboard routes."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.web.deps import get_config, get_db

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
        "types": types,
        "statuses": statuses,
    }


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


# -- Dashboard ----------------------------------------------------------------

@router.get("/crew", response_class=HTMLResponse)
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

    Queries the role-specific PostgreSQL view (e.g. projects.scribe_view)
    and passes results to the crew.html template. HTMX requests return
    only the _crew_rows.html partial.
    """
    crew_roles = config.get("crew", "roles")
    valid_roles = [r["name"] for r in crew_roles]

    if role not in valid_roles:
        role = "captain"  # Safe fallback

    # Find the role's metadata
    role_meta = next((r for r in crew_roles if r["name"] == role), None)

    # Build query — role is validated above, safe to interpolate
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
        records = await db.fetch_all(sql, (f"%{search}%",))
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
        records = await db.fetch_all(sql)

    # HTMX requests return only the table rows partial
    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        template = env.get_template("_crew_rows.html")
        return HTMLResponse(template.render(records=records))

    # Fetch lookup tables for dropdowns
    lookups = await _fetch_lookups(db)

    # Captain gets a tabbed interface; other roles get the standard datasheet
    if role == "captain":
        template = env.get_template("captain.html")
    else:
        template = env.get_template("crew.html")

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
    }

    return HTMLResponse(template.render(**data))


# -- Project save routes ------------------------------------------------------
# Both accept JSON body from datasheet.js fetch() calls.
# Route /crew/projects/save must be declared before /crew/projects/{project_id}/save
# to avoid "save" being matched as a project_id integer (FastAPI rejects it
# gracefully but explicit ordering is cleaner).

@router.post("/crew/projects/save", response_class=HTMLResponse)
async def save_new_project(
    request: Request,
    role: str = Query("captain"),
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project from datasheet add row.

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
    """Save edits to an existing project from datasheet row.

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
