"""Crew role dashboard routes."""

from fastapi import APIRouter, Query, Depends
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.web.deps import get_config, get_db

router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


@router.get("/crew", response_class=HTMLResponse)
async def crew_dashboard(
    role: str = Query("captain"),
    config: ConfigManager = Depends(get_config),
    db: AsyncDBConnection = Depends(get_db),
):
    """Crew dashboard — displays projects filtered by crew role.

    Query parameters:
        role: One of the roles defined in curator.yaml

    Queries the role-specific PostgreSQL view (e.g. projects.scribe_view)
    and passes results to the crew.html template.
    """
    crew_roles = config.get("crew", "roles")
    valid_roles = [r["name"] for r in crew_roles]

    if role not in valid_roles:
        role = "captain"  # Safe fallback

    # Find the role's metadata
    role_meta = next((r for r in crew_roles if r["name"] == role), None)

    # Query the role-specific view — role is validated above, safe to interpolate
    view_name = f"projects.{role}_view"
    sql = f"""
        SELECT
            p.id,
            p.name,
            p.slug,
            p.description,
            ps.name  AS status,
            pt.name  AS type
        FROM {view_name} p
        LEFT JOIN projects.project_status ps ON ps.id = p.status_id
        LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
        ORDER BY p.name
    """
    records = await db.fetch_all(sql)

    # Fetch project types (lookup table for dropdowns)
    project_types = await db.fetch_all("""
        SELECT id, name FROM projects.project_type ORDER BY name
    """)

    # Fetch project statuses (lookup table for dropdowns)
    project_statuses = await db.fetch_all("""
        SELECT id, name FROM projects.project_status ORDER BY name
    """)

    # Fetch organizations and contacts for Identities tab (Captain only)
    organizations = []
    contacts = []
    if role == "captain":
        organizations = await db.fetch_all("""
            SELECT
                o.id,
                o.name,
                COALESCE(STRING_AGG(oc.contact_id::text, ','), '') AS contact_ids
            FROM identity.organizations o
            LEFT JOIN identity.organization_contacts oc ON oc.organization_id = o.id
            GROUP BY o.id, o.name
            ORDER BY o.name
        """)

        contacts = await db.fetch_all("""
            SELECT
                c.id,
                c.name,
                ce.address AS email,
                COALESCE(STRING_AGG(oc.organization_id::text, ','), '') AS org_ids
            FROM identity.contacts c
            LEFT JOIN identity.contact_emails ce ON ce.contact_id = c.id AND ce.label = 'primary'
            LEFT JOIN identity.organization_contacts oc ON oc.contact_id = c.id
            GROUP BY c.id, c.name, ce.address
            ORDER BY c.name
        """)

    # Tab configuration
    tabs = [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ]
    
    if role == "captain":
        tabs.append({"id": "identities", "label": "Identities", "template": "_tab_identities.html"})
        tabs.append({"id": "configuration", "label": "Configuration", "template": "_tab_configuration.html"})

    template = env.get_template("crew.html")

    # Embed lookups for Tabulator and identity panels
    data['project_types'] = [dict(row) for row in project_types]
    data['project_statuses'] = [dict(row) for row in project_statuses]
    data['organizations'] = [dict(row) for row in organizations]
    data['contacts'] = [dict(row) for row in contacts]
    data['tabs'] = tabs

    return template.render(**data)
