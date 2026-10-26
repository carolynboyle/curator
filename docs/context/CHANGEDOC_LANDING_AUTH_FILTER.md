# Changedoc — landing.py: Filter crew cards by logged-in user's crew role

**File:** `src/curator/web/routes/landing.py`
**Repo:** `curator`
**Date:** 2026-06-29

---

## Problem

The landing page shows all four crew cards regardless of who is logged in.
Felipe (Mechanic) sees Captain, Mechanic, Envoy, and Scribe cards.
He should only see the Mechanic card (and any future roles assigned to him).

The Captain sees all cards — Captain has visibility across all crew roles.

---

## Approach

- Add `Request` to the route signature so middleware-injected
  `request.state.user` is accessible
- Read `crew_role` from the session user context
- Filter `crew_roles` from config:
  - Captain → show all cards
  - Any other role → show only cards matching their crew_role
- The landing page remains accessible after login — it's the crew
  selector, not just a pre-login splash page

---

## Change

**File:** `src/curator/web/routes/landing.py`

**BEFORE:**
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

**AFTER:**
```python
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
```

---

## Why

`request.state.user` is injected by `SessionMiddleware` on every
authenticated request. It contains `crew_role` (the user's application
persona). Filtering here keeps the template dumb — it just iterates
whatever `crew_roles` it receives.

Captain is the special case that sees everything. `user_crew_role is None`
is a safety fallback for the unauthenticated case (middleware should have
redirected, but if it didn't, show all cards rather than crashing).

---

## After Applying

Restart uvicorn and verify:
- Logged in as Carolyn (captain) → all four cards visible
- Logged in as Felipe (mechanic) → only Mechanic card visible
- Future store role added → store user sees only Store card
