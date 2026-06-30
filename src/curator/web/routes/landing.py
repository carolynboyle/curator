"""Landing page route."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from curator.config import ConfigManager
from curator.web.deps import get_config

router = APIRouter()

# Initialize Jinja2 for landing
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request, config: ConfigManager = Depends(get_config)):
    """Landing page with crew role cards.

    Cards are filtered by the logged-in user's crew_role.
    Captain sees all cards. All other roles see only their own card(s).
    """
    template = env.get_template("landing.html")

    all_roles = config.get("crew", "roles") or []

    # Get logged-in user's crew role from middleware-injected state
    user = getattr(request.state, "user", None)
    user_crew_role = user.get("crew_role") if user else None

    # Captain sees all cards; all others see only their matching card
    if user_crew_role == "captain" or user_crew_role is None:
        visible_roles = all_roles
    else:
        visible_roles = [r for r in all_roles if r.get("name") == user_crew_role]

    context = {
        "site_title": config.get("branding", "site_title"),
        "site_subtitle": config.get("branding", "site_subtitle"),
        "site_icon": config.get("branding", "site_icon"),
        "theme": config.get("ui", "theme"),
        "crew_roles": visible_roles,
    }

    return template.render(**context)