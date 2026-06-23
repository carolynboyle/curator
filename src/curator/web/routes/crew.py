"""Crew role dashboard routes."""

from fastapi import APIRouter, Query, Depends
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from curator.config import ConfigManager
from curator.web.deps import get_config

router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


@router.get("/crew", response_class=HTMLResponse)
async def crew_dashboard(
    role: str = Query("captain"),
    config: ConfigManager = Depends(get_config)
):
    """Crew dashboard — displays data for the requested role.

    Query parameters:
        role: One of the roles defined in curator.yaml

    Phase 1: Accepts role param, renders template.
    Phase 2: Will load role-specific views from database.
    Phase 3: Will query settings table for user's theme preference.
    """
    crew_roles = config.get("crew", "roles")
    valid_roles = [r["name"] for r in crew_roles]
    
    if role not in valid_roles:
        role = "captain"  # Safe fallback
    
    # Find the role's metadata
    role_meta = next((r for r in crew_roles if r["name"] == role), None)
    
    template = env.get_template("crew.html")
    
    # Phase 2: Replace this with database query for role's view
    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": [],  # Will be populated in Phase 2
        "message": f"Crew dashboard for {role.title()} (Phase 1 — no data yet)"
    }
    
    return template.render(**data)