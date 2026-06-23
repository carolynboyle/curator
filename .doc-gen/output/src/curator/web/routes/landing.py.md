# landing.py

**Path:** src/curator/web/routes/landing.py
**Syntax:** python
**Generated:** 2026-06-23 12:09:21

```python
"""Landing page route."""

from fastapi import APIRouter, Depends
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
async def landing(config: ConfigManager = Depends(get_config)):
    """Landing page with crew role cards.
    
    All text, icons, crew definitions come from config — no hardcoding.
    """
    template = env.get_template("landing.html")
    
    context = {
        "site_title": config.get("branding", "site_title"),
        "site_subtitle": config.get("branding", "site_subtitle"),
        "site_icon": config.get("branding", "site_icon"),
        "theme": config.get("ui", "theme"),
        "crew_roles": config.get("crew", "roles"),
    }
    
    return template.render(**context)
```
