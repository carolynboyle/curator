# Fix: crew.py — Add Search & Lookup Tables

**Goal**: Add search filtering, fetch project type/status lookups for inline edit forms, and include status_id/type_id in the SELECT.

**File**: `src/curator/web/routes/crew.py`

---

## BEFORE (line 19-68)

```python
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
```

---

## AFTER (line 19-82)

```python
@router.get("/crew", response_class=HTMLResponse)
async def crew_dashboard(
    role: str = Query("captain"),
    search: str = Query(""),
    config: ConfigManager = Depends(get_config),
    db: AsyncDBConnection = Depends(get_db),
):
    """Crew dashboard — displays projects filtered by crew role and search term.

    Query parameters:
        role: One of the roles defined in curator.yaml
        search: Optional search term to filter projects by name

    Queries the role-specific PostgreSQL view, filters by search,
    and passes lookup tables for inline edit forms.
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
            p.status_id,
            ps.name  AS status,
            p.type_id,
            pt.name  AS type
        FROM {view_name} p
        LEFT JOIN projects.project_status ps ON ps.id = p.status_id
        LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
    """
    
    params = {}
    if search:
        sql += " WHERE LOWER(p.name) LIKE LOWER(:search)"
        params["search"] = f"%{search}%"
    
    sql += " ORDER BY p.name"
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

1. **Added `search` parameter** (line 21) to accept search term from the search box in _projects_table.html
2. **Added `p.status_id` and `p.type_id`** to the SELECT (lines 45-46) — needed for the edit form to pre-select the current values
3. **Added search filtering** (lines 54-56) — if search term provided, filter by name (case-insensitive)
4. **Fetch lookup tables** (lines 59-63) — queries to get all project_types and project_statuses
5. **Convert rows to dicts** (lines 73) — Jinja2 expects dicts, not asyncpg Row objects
6. **Pass lookups and search to template** (lines 74-76) — so inline edit forms can access them via `window.projectTypes` and `window.projectStatuses`

---

## Testing Checklist

- [ ] `/crew?role=captain` loads, shows project list
- [ ] `/crew?role=scribe` loads, shows filtered list (only scribe projects)
- [ ] Type in search box, results filter by project name
- [ ] Click pencil icon on a project, edit form opens
- [ ] In edit form, Status and Type dropdowns show all options (not blank)
- [ ] Edit form shows current status/type pre-selected
- [ ] Save changes successfully
- [ ] Cancel reverts to display
