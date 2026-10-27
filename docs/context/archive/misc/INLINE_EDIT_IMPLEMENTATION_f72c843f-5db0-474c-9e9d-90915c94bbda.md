# Inline Row Editing — Implementation

## Overview

Add pencil-icon editing to crew dashboard. Clicking the pencil expands the row with editable fields (name, type, status) plus Save/Cancel buttons. Uses HTMX for zero-page-reload editing with lookup table dropdowns pre-loaded. Two-row edit pattern (form row + controls row) with 4-column layout to reserve left column for future icon actions.

---

## File Changes

### 1. `curator/web/routes/crew.py`

**BEFORE:**
```python
"""Crew role dashboard routes."""

from fastapi import APIRouter, Query, Depends, Request
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
                pt.name::text  AS type
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
                pt.name::text  AS type
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

    template = env.get_template("crew.html")

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
    }

    return HTMLResponse(template.render(**data))
```

**AFTER:**
```python
"""Crew role dashboard routes."""

from fastapi import APIRouter, Query, Depends, Request, HTTPException
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
        FROM projects.project
        WHERE id = %s
    """
    result = await db.fetch_one(sql, (project_id,))
    
    if not result:
        return None
    
    return result


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
    name: str = Query(...),
    type_id: int = Query(...),
    status_id: int = Query(...),
    db: AsyncDBConnection = Depends(get_db),
):
    """Save project changes and return display row + OOB delete controls row.
    
    Query parameters:
        name:      Project name
        type_id:   Project type ID
        status_id: Project status ID
    """
    # Update project in database
    update_sql = """
        UPDATE projects.project
        SET name = %s, type_id = %s, status_id = %s
        WHERE id = %s
    """
    
    await db.execute(update_sql, (name, type_id, status_id, project_id))
    
    # Fetch updated project for display
    project = await _fetch_project_by_id(db, project_id)
    
    if not project:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")
    
    # Fetch type and status names for display
    type_sql = "SELECT name::text FROM projects.project_type WHERE id = %s"
    status_sql = "SELECT name::text FROM projects.project_status WHERE id = %s"
    
    type_name = await db.fetch_val(type_sql, (type_id,))
    status_name = await db.fetch_val(status_sql, (status_id,))
    
    # Add display names to project dict
    project["type"] = type_name
    project["status"] = status_name
    
    template = env.get_template("_crew_row_display.html")
    
    return HTMLResponse(template.render(record=project))


@router.post("/crew/projects/{project_id}/cancel", response_class=HTMLResponse)
async def cancel_edit(
    project_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Cancel edit and return display row + OOB delete controls row."""
    # Fetch project for display
    sql = """
        SELECT
            p.id,
            p.name::text,
            p.slug::text,
            p.description::text,
            ps.name::text  AS status,
            pt.name::text  AS type
        FROM projects.project p
        LEFT JOIN projects.project_status ps ON ps.id = p.status_id
        LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
        WHERE p.id = %s
    """
    
    record = await db.fetch_one(sql, (project_id,))
    
    if not record:
        raise HTTPException(status_code=404, detail="Project not found")
    
    template = env.get_template("_crew_row_display.html")
    
    return HTMLResponse(template.render(record=record))
```

**Explanation:**

- Added `_fetch_lookups()` helper to query project_type and project_status lookup tables once at page load
- Added `_fetch_project_by_id()` helper to fetch a single project for edit/cancel operations
- Modified main `crew_dashboard()` to fetch lookups and pass to template; added `type_id` and `status_id` to SELECT
- Added `GET /crew/projects/{project_id}/edit-form` route that returns the edit form partial with two rows
- Added `POST /crew/projects/{project_id}/save` route that updates the project in the database and returns display row + OOB delete instruction for controls row
- Added `POST /crew/projects/{project_id}/cancel` route that returns display row + OOB delete instruction without saving

---

### 2. `templates/crew.html`

**BEFORE:**
```jinja2
{% extends "base.html" %}

{% block title %}{{ role_title }} — Curator{% endblock %}

{% block content %}
<section class="crew-section {{ role }}">

    <div class="crew-header crew-card {{ role }}">
        <h1>{{ role_title }}</h1>
        <a href="/" class="btn-back">← Back to Crew</a>
    </div>

    <div class="crew-content">
        <input
            type="search"
            name="search"
            placeholder="Search projects..."
            value="{{ search }}"
            hx-get="/crew"
            hx-trigger="keyup changed delay:300ms"
            hx-target="#crew-rows"
            hx-include="[name='search']"
            hx-vals='{"role": "{{ role }}"}'
        >

        <table class="crew-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="crew-rows">
                {% include "_crew_rows.html" %}
            </tbody>
        </table>
    </div>

</section>
{% endblock %}
```

**AFTER:**
```jinja2
{% extends "base.html" %}

{% block title %}{{ role_title }} — Curator{% endblock %}

{% block content %}
<section class="crew-section {{ role }}">

    <div class="crew-header crew-card {{ role }}">
        <h1>{{ role_title }}</h1>
        <a href="/" class="btn-back">← Back to Crew</a>
    </div>

    <div class="crew-content">
        <input
            type="search"
            name="search"
            placeholder="Search projects..."
            value="{{ search }}"
            hx-get="/crew"
            hx-trigger="keyup changed delay:300ms"
            hx-target="#crew-rows"
            hx-include="[name='search']"
            hx-vals='{"role": "{{ role }}"}'
        >

        <table class="crew-table">
            <thead>
                <tr>
                    <th></th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="crew-rows">
                {% include "_crew_rows.html" %}
            </tbody>
        </table>
    </div>

</section>

<!-- Embed lookups as data attributes for access in partials -->
<script>
    window.projectTypes = {{ project_types | tojson }};
    window.projectStatuses = {{ project_statuses | tojson }};
</script>
{% endblock %}
```

**Explanation:**

- Added empty `<th></th>` header for icon column (4 columns total)
- Added script block that embeds lookup tables as global JavaScript objects (useful if we add client-side validation later)

---

### 3. `templates/_crew_rows.html` (Modified)

**BEFORE:**
```jinja2
{% for record in records %}
<tr>
    <td>{{ record["name"] }}</td>
    <td>{{ record["type"] or "—" }}</td>
    <td>{{ record["status"] }}</td>
</tr>
{% else %}
<tr>
    <td colspan="3">No projects found.</td>
</tr>
{% endfor %}
```

**AFTER:**
```jinja2
{% for record in records %}
    {% include "_crew_row_display.html" %}
{% else %}
<tr>
    <td colspan="4">No projects found.</td>
</tr>
{% endfor %}
```

**Explanation:**

- Changed to include the display partial for each record (cleaner separation of concerns)
- Updated colspan from 3 to 4 for the empty state message (matches new 4-column layout)

---

### 4. `templates/_crew_row_display.html` (NEW)

```jinja2
<tr class="crew-row-display" data-project-id="{{ record.id }}">
    <td class="icon-col">
        <button
            class="edit-icon"
            hx-get="/crew/projects/{{ record.id }}/edit-form"
            hx-target="closest tr"
            hx-swap="outerHTML"
            title="Edit project"
        >✏</button>
    </td>
    <td>{{ record["name"] }}</td>
    <td>{{ record["type"] or "—" }}</td>
    <td>{{ record["status"] }}</td>
</tr>
```

**Explanation:**

- New partial extracted from `_crew_rows.html` for DRY principle
- Pencil icon in first column, hidden by default (CSS handles visibility)
- Icon button has HTMX trigger: GET `/crew/projects/{id}/edit-form` → targets closest `<tr>` → replaces with outerHTML
- When pencil is clicked, HTMX fetches the edit form (two rows) and replaces the display row with both edit rows

---

### 5. `templates/_crew_row_edit.html` (NEW)

```jinja2
<!-- Edit form row -->
<tr class="crew-row-edit" data-project-id="{{ project.id }}">
    <td class="icon-col"></td>
    <td colspan="3">
        <form class="edit-form" id="edit-form-{{ project.id }}" hx-post="/crew/projects/{{ project.id }}/save" hx-target="closest tr.crew-row-edit" hx-swap="outerHTML">
            <fieldset class="edit-fields">
                <input
                    type="text"
                    name="name"
                    class="edit-input"
                    value="{{ project.name }}"
                    placeholder="Project name"
                    required
                >
                <select
                    name="type_id"
                    class="edit-select"
                    required
                >
                    <option value="">— Type —</option>
                    {% for t in project_types %}
                    <option value="{{ t.id }}" {% if t.id == project.type_id %}selected{% endif %}>{{ t.name }}</option>
                    {% endfor %}
                </select>
                <select
                    name="status_id"
                    class="edit-select"
                    required
                >
                    <option value="">— Status —</option>
                    {% for s in project_statuses %}
                    <option value="{{ s.id }}" {% if s.id == project.status_id %}selected{% endif %}>{{ s.name }}</option>
                    {% endfor %}
                </select>
            </fieldset>
        </form>
    </td>
</tr>

<!-- Edit controls row (Save/Cancel buttons) — marked for OOB delete on response -->
<tr class="crew-row-edit-controls" data-project-id="{{ project.id }}" hx-swap-oob="delete">
    <td class="icon-col"></td>
    <td colspan="3">
        <div class="edit-controls">
            <button
                type="submit"
                form="edit-form-{{ project.id }}"
                class="btn-save"
            >Save</button>
            <button
                type="button"
                class="btn-cancel"
                hx-post="/crew/projects/{{ project.id }}/cancel"
                hx-target="closest tr.crew-row-edit"
                hx-swap="outerHTML"
            >Cancel</button>
        </div>
    </td>
</tr>
```

**Explanation:**

- Two `<tr>` elements: form row + controls row, both marked with `data-project-id`
- Form has `id="edit-form-{{ project.id }}"` so the Save button (in a different row) can reference it with `form` attribute
- All three fields in one `<fieldset class="edit-fields">` → CSS will make them inline with flex wrapping
- Form uses `hx-post="/crew/projects/{id}/save"` and targets the form row with `outerHTML` swap
- Controls row is marked `hx-swap-oob="delete"` — when the response comes back, HTMX will delete this row automatically (out-of-band)
- Cancel button posts to `/crew/projects/{id}/cancel`, targets the form row, and also triggers OOB delete on the controls row in the response

---

### 6. `static/css/curator.css` or role-specific CSS

Add to the stylesheet:

```css
/* Edit mode styles */
table.crew-table .icon-col {
    width: 2.5rem;
    text-align: center;
}

table.crew-table .edit-icon {
    visibility: hidden;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    font-size: 1rem;
    color: currentColor;
}

table.crew-table tr:hover .edit-icon {
    visibility: visible;
}

/* Edit form styling */
tr.crew-row-edit fieldset.edit-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
    margin: 0.5rem 0;
    border: none;
    padding: 0;
}

tr.crew-row-edit .edit-input,
tr.crew-row-edit .edit-select {
    padding: 0.5rem;
    border: 1px solid var(--border-color, #ccc);
    border-radius: 0.25rem;
    font-size: 0.95rem;
    font-family: inherit;
}

tr.crew-row-edit .edit-input {
    flex: 1 1 auto;
    min-width: 12rem;
}

tr.crew-row-edit .edit-select {
    flex: 0 1 auto;
    min-width: 8rem;
}

/* Controls row */
tr.crew-row-edit-controls .edit-controls {
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem 0;
}

.btn-save,
.btn-cancel {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color, #ccc);
    border-radius: 0.25rem;
    background: white;
    cursor: pointer;
    font-size: 0.95rem;
    transition: all 200ms ease;
}

.btn-save:hover {
    background: #e6f2ff;
    border-color: #0066cc;
}

.btn-cancel:hover {
    background: #f5f5f5;
    border-color: #666;
}

/* Responsive: on small screens, stack fields vertically */
@media (max-width: 640px) {
    tr.crew-row-edit fieldset.edit-fields {
        flex-direction: column;
    }

    tr.crew-row-edit .edit-input,
    tr.crew-row-edit .edit-select {
        width: 100%;
        min-width: auto;
    }

    tr.crew-row-edit-controls .edit-controls {
        flex-direction: row;
    }

    .btn-save,
    .btn-cancel {
        flex: 1;
        text-align: center;
    }
}
```

**Explanation:**

- Icon column: fixed width, centered
- Pencil icon: hidden by default, visible on row hover
- Edit fields: flex container, wraps on mobile, inline on desktop
- Input fields: min-width 12rem, expand to fill available space
- Selects: min-width 8rem, stay compact
- Buttons: flex layout with gap, responsive behavior (stack on mobile if needed)
- Color scheme uses CSS variables for theme compatibility (can be overridden in role CSS files)

---

## Testing Checklist

### Desktop
- [ ] Pencil icon appears on row hover only
- [ ] Click pencil → row expands to show form + buttons
- [ ] Dropdowns pre-populated with correct lookups
- [ ] Type and Status dropdowns show selected value
- [ ] Type in name field → text updates
- [ ] Click Save → POST fires, database updates, row returns to display mode with new values
- [ ] Click Cancel → row returns to display, no database change
- [ ] Search still works while editing another row
- [ ] After edit, search state is preserved

### Mobile (phone browser or Chrome dev tools)
- [ ] Pencil icon still accessible (visible on tap or in the icon column area)
- [ ] Edit form fields stack vertically for readability
- [ ] Buttons are large enough to tap easily (min 44px height)
- [ ] Form doesn't overflow screen width
- [ ] Save/Cancel buttons are clearly separated

### Edge Cases
- [ ] Edit project, change nothing, click Save → succeeds, no visual change
- [ ] Edit project, change name only → saves correctly, type/status unchanged
- [ ] Dropdown set to blank → form should reject (required attribute)
- [ ] Very long project name → text input handles gracefully, doesn't overflow
- [ ] Multiple rows edited simultaneously → each maintains its own state (HTMX handles this)

---

## Database Queries Used

The routes use these queries:

**Fetch project types:**
```sql
SELECT id, name::text FROM projects.project_type ORDER BY name
```

**Fetch project statuses:**
```sql
SELECT id, name::text FROM projects.project_status ORDER BY name
```

**Fetch single project by ID:**
```sql
SELECT id, name::text, type_id, status_id FROM projects.project WHERE id = %s
```

**Update project:**
```sql
UPDATE projects.project
SET name = %s, type_id = %s, status_id = %s
WHERE id = %s
```

All queries are parameterized to prevent SQL injection.

---

## HTMX Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│ Display Row (pencil icon in icon column)            │
└──────────┬──────────────────────────────────────────┘
           │ Click pencil
           ├─ hx-get="/crew/projects/{id}/edit-form"
           ├─ hx-target="closest tr"
           └─ hx-swap="outerHTML"
           │
           ▼
┌─────────────────────────────────────────────────────┐
│ Edit Form Row (name, type, status fields)           │
│ hx-post="/crew/projects/{id}/save"                  │
│ hx-target="closest tr.crew-row-edit"                │
│ hx-swap="outerHTML"                                 │
└─────────────────────────────────────────────────────┘
            │
            │ form visible
            │
┌─────────────────────────────────────────────────────┐
│ Edit Controls Row (Save, Cancel buttons)            │
│ [marked with hx-swap-oob="delete"]                  │
└──────────┬──────────────────────────────────────────┘
           │
           ├─────────────────┬──────────────────┐
           │                 │                  │
        Click Save        Click Cancel      Search runs
           │                 │                  │
    hx-post to save      hx-post to        hx-get to crew
      endpoint            cancel           (doesn't affect
           │              endpoint          edit mode)
           │                 │
           ▼                 ▼
    ┌────────────┐      ┌────────────┐
    │ POST       │      │ POST       │
    │ /save      │      │ /cancel    │
    └────────────┘      └────────────┘
           │                 │
           ▼                 ▼
    Returns:             Returns:
    Display Row +        Display Row +
    OOB delete          OOB delete
           │                 │
           └─────┬───────────┘
                 │
                 ▼
    HTMX replaces form row with display row
    HTMX deletes controls row (OOB)
                 │
                 ▼
    ┌─────────────────────────────────────┐
    │ Display Row (back to normal state)   │
    └─────────────────────────────────────┘
```

---

## Notes

- **OOB (Out-of-Band) swaps**: The `hx-swap-oob="delete"` attribute on the controls row tells HTMX to delete that row without requiring an explicit target. This is an HTMX 1.7+ feature.
- **Form ID linking**: The Save button in a different row from the form uses the `form` attribute to associate with the form ID.
- **Search preservation**: Search queries are handled by the main crew dashboard route; editing rows doesn't interfere because the HTMX requests are scoped to the row-level routes.
- **Responsive design**: Fields flex-wrap on desktop (3 fields in a row if space permits, fewer on smaller screens); on mobile (max-width 640px), they stack vertically for readability.
- **No role-specific colors in edit CSS**: Edit styling is neutral (white background, gray borders); role colors are applied at the `<tr>` level or inherited from the parent section.

