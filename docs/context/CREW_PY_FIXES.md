# Fix: crew.py — Pass Lookup Tables & Add Search

**Goal**: Make the Projects tab inline-edit forms work by passing `project_types` and `project_statuses` as JSON to the template, and wire up the search filtering.

**File**: `src/curator/web/routes/crew.py`

---

## BEFORE

```python
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
```

---

## AFTER

```python
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
    search: str = Query("", alias="search"),
    config: ConfigManager = Depends(get_config),
    db: AsyncDBConnection = Depends(get_db),
):
    """Crew dashboard — displays projects filtered by crew role and search term.

    Query parameters:
        role: One of the roles defined in curator.yaml
        search: Optional search term to filter projects by name

    Returns the projects.{role}_view filtered by search, plus lookup tables
    for inline edit forms (project types, project statuses).
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
            id,
            name,
            description,
            status_id,
            status,
            type_id,
            type
        FROM {view_name}
    """
    
    params = {}
    if search:
        sql += " WHERE LOWER(name) LIKE LOWER(:search)"
        params["search"] = f"%{search}%"
    
    sql += " ORDER BY name"
    records = await db.fetch_all(sql, params)
    
    # Fetch lookup tables for inline edit forms
    project_types = await db.fetch_all(
        "SELECT id, name FROM projects.project_type ORDER BY name"
    )
    project_statuses = await db.fetch_all(
        "SELECT id, name FROM projects.project_status ORDER BY name"
    )
    
    template = env.get_template("crew.html")
    
    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": [dict(r) for r in records],
        "project_types": [dict(pt) for pt in project_types],
        "project_statuses": [dict(ps) for ps in project_statuses],
        "search": search,
    }
    
    return template.render(**data)
```

---

## What Changed

1. **Added imports**: `AsyncDBConnection` from dbkit, `get_db` from deps
2. **Added `search` parameter** to handle filter input from _projects_table.html
3. **Query the role view** (`projects.{role}_view`) instead of returning empty records
4. **Filter by search term** if provided (case-insensitive LIKE on name)
5. **Fetch lookup tables** from `projects.project_type` and `projects.project_status`
6. **Convert rows to dicts** before passing to template (Jinja2 needs dicts, not Row objects)
7. **Pass all data** including `project_types`, `project_statuses`, and `search` value to template

---

## Why This Works

- The captain.html template expects `project_types` and `project_statuses` in the script block to be available as `window.projectTypes` and `window.projectStatuses` (see `| tojson` filter)
- The _crew_row_add.html and _crew_row_edit.html partials use these globals to populate the type/status dropdowns
- The search box in _projects_table.html makes an HTMX GET request to `/crew` with the search term, this route handles it

---

## Testing Checklist

- [ ] Landing page loads (not affected)
- [ ] `/crew?role=captain` loads, shows Projects tab with project list
- [ ] `/crew?role=scribe` loads, shows project list (filtered to scribe role)
- [ ] `/crew?role=mechanic` loads, shows project list (filtered to mechanic role)
- [ ] Type search box in _projects_table.html works, filters results
- [ ] Project type/status dropdowns in add form show values (no blank options)
- [ ] Pencil icon opens edit form, dropdowns populate with lookup values
