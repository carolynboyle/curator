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

    template = env.get_template("crew.html")

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
    }

    return template.render(**data)
