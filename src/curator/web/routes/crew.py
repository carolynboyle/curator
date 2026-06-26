"""Crew role dashboard routes."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
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


async def _fetch_role_types(db: AsyncDBConnection, role: str) -> list:
    """Fetch project types available to a specific crew role.

    Queries project_type_role_mapping joined to crew_role and project_type.
    Returns list of dicts with 'id' and 'name' keys.
    """
    sql = """
        SELECT pt.id, pt.name::text
        FROM projects.project_type pt
        JOIN projects.project_type_role_mapping ptrm ON ptrm.project_type_id = pt.id
        JOIN identity.crew_role cr ON cr.id = ptrm.crew_role_id
        WHERE cr.name = %s
        ORDER BY pt.name
    """
    return await db.fetch_all(sql, (role,))


async def _fetch_project_by_id(db: AsyncDBConnection, project_id: int) -> dict:
    """Fetch a single project by ID.

    Returns dict with id, name, type_id, status_id keys.
    """
    sql = """
        SELECT
            id,
            name::text,
            type_id,
            status_id
        FROM projects.projects
        WHERE id = %s
    """
    result = await db.fetch_one(sql, (project_id,))

    if not result:
        return None

    return result


async def _fetch_project_for_display(db: AsyncDBConnection, project_id: int) -> dict:
    """Fetch a project with joined type and status names for display.

    Returns dict with id, name, slug, description, type, status keys.
    """
    sql = """
        SELECT
            p.id,
            p.name::text,
            p.slug::text,
            p.description::text,
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


def _collapse_edit_row(project_id: int, record: dict) -> HTMLResponse:
    """Render display row + OOB delete of controls row.

    Used by both save and cancel to collapse the edit state back to
    a single display row. The controls row is removed via HTMX OOB swap.
    """
    display_template = env.get_template("_crew_row_display.html")
    display_html = display_template.render(record=record)
    oob_delete = f'<tr id="edit-controls-{project_id}" hx-swap-oob="delete"></tr>'
    return HTMLResponse(display_html + oob_delete)


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


# -- Add routes (declared before edit to avoid {project_id} collision) --------

@router.get("/crew/projects/new", response_class=HTMLResponse)
async def add_project_form(
    role: str = Query("captain"),
    db: AsyncDBConnection = Depends(get_db),
):
    """Return empty add form partial, filtered to role-appropriate types.

    Inserts two rows at the top of #crew-rows via hx-swap afterbegin.
    """
    project_types = await _fetch_role_types(db, role)
    lookups = await _fetch_lookups(db)

    template = env.get_template("_crew_row_add.html")

    data = {
        "role": role,
        "project_types": project_types,
        "project_statuses": lookups["statuses"],
    }

    return HTMLResponse(template.render(**data))


@router.post("/crew/projects/new/save", response_class=HTMLResponse)
async def save_new_project(
    role: str = Query("captain"),
    name: str = Form(...),
    type_id: int = Form(...),
    status_id: int = Form(...),
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project and collapse add rows to display row.

    Generates slug from name. Returns 409 with inline error on duplicate slug.
    """
    slug = _make_slug(name)

    # Check for duplicate slug
    existing = await db.fetch_one(
        "SELECT id FROM projects.projects WHERE slug = %s",
        (slug,)
    )

    if existing:
        # Return error message in place, keep add row open
        project_types = await _fetch_role_types(db, role)
        lookups = await _fetch_lookups(db)
        template = env.get_template("_crew_row_add.html")
        html = template.render(
            role=role,
            project_types=project_types,
            project_statuses=lookups["statuses"],
            error=f'A project named "{name}" already exists.',
            name=name,
            type_id=type_id,
            status_id=status_id,
        )
        return HTMLResponse(html, status_code=409)

    # Insert new project
    insert_sql = """
        INSERT INTO projects.projects (name, slug, type_id, status_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    result = await db.fetch_one(insert_sql, (name, slug, type_id, status_id))
    new_id = result["id"]

    # Fetch for display
    record = await _fetch_project_for_display(db, new_id)

    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    # Return display row + OOB delete of controls row
    display_template = env.get_template("_crew_row_display.html")
    display_html = display_template.render(record=record)
    oob_delete = '<tr id="add-controls-new" hx-swap-oob="delete"></tr>'
    return HTMLResponse(display_html + oob_delete)


@router.post("/crew/projects/new/cancel", response_class=HTMLResponse)
async def cancel_new_project():
    """Cancel add — remove both add rows with no database write."""
    oob_delete = '<tr id="add-controls-new" hx-swap-oob="delete"></tr>'
    return HTMLResponse(
        '<tr id="add-row-new" hx-swap-oob="delete"></tr>' + oob_delete
    )


# -- Edit routes --------------------------------------------------------------

@router.get("/crew/projects/{project_id}/edit-form", response_class=HTMLResponse)
async def edit_project_form(
    project_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Return editable form partial for a project.

    Returns two rows: form row and controls row.
    """
    project = await _fetch_project_by_id(db, project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    lookups = await _fetch_lookups(db)

    template = env.get_template("_crew_row_edit.html")

    data = {
        "project": project,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
    }

    return HTMLResponse(template.render(**data))


@router.post("/crew/projects/{project_id}/save", response_class=HTMLResponse)
async def save_project(
    project_id: int,
    name: str = Form(...),
    type_id: int = Form(...),
    status_id: int = Form(...),
    db: AsyncDBConnection = Depends(get_db),
):
    """Save project changes and collapse edit rows back to display row.

    Writes changes to the database, then returns the updated display row
    plus an OOB delete of the controls row.
    """
    update_sql = """
        UPDATE projects.projects
        SET name = %s, type_id = %s, status_id = %s
        WHERE id = %s
    """

    await db.execute(update_sql, (name, type_id, status_id, project_id))

    record = await _fetch_project_for_display(db, project_id)

    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    return _collapse_edit_row(project_id, record)


@router.post("/crew/projects/{project_id}/cancel", response_class=HTMLResponse)
async def cancel_edit(
    project_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Cancel edit and collapse edit rows back to original display row.

    Makes no database changes. Returns the current display row plus
    an OOB delete of the controls row.
    """
    record = await _fetch_project_for_display(db, project_id)

    if not record:
        raise HTTPException(status_code=404, detail="Project not found")

    return _collapse_edit_row(project_id, record)
