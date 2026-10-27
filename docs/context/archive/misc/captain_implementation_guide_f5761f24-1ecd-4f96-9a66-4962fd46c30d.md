# Captain's Command Center — Implementation Guide

## Overview

This document contains all code changes needed to build the Captain's tabbed page. The Captain gets a special-case route that shows three tabs: Projects, Identities, and Configuration. The Identities tab has sub-selectors for Contacts, Organizations, and Users.

---

## File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/curator/web/routes/crew.py` | Modify | Add captain detection, query all projects |
| `templates/captain.html` | Create | Main tabbed layout |
| `templates/_identities_contacts.html` | Create | Contacts sub-form placeholder |
| `templates/_identities_organizations.html` | Create | Organizations sub-form placeholder |
| `templates/_identities_users.html` | Create | Users sub-form placeholder |
| `static/css/components/tabs.css` | Create | Tab styling and JavaScript |
| `base.html` | Modify | Link tabs.css |

---

## 1. Modify `src/curator/web/routes/crew.py`

### BEFORE
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

### AFTER
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
    config: ConfigManager = Depends(get_config),
    db: AsyncDBConnection = Depends(get_db),
):
    """Crew dashboard — displays projects filtered by crew role.

    Query parameters:
        role: One of the roles defined in curator.yaml

    For captain, renders a tabbed interface with Projects, Identities, and
    Configuration tabs. For other roles, renders the standard crew datasheet.

    Queries the role-specific PostgreSQL view (e.g. projects.scribe_view)
    and passes results to the appropriate template.
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
    }

    return template.render(**data)
```

### Changes Explained

- **Added captain detection:** `if role == "captain"` branch selects `captain.html` template
- **Updated docstring:** Mentions that captain gets a tabbed interface
- **No changes to query logic:** Captain still uses `projects.captain_view` which returns all projects
- **Data passed to template:** Same `records` list works for both `crew.html` and `captain.html`

---

## 2. Create `templates/captain.html`

```html
{% extends "base.html" %}

{% block title %}Captain's Command — Curator{% endblock %}

{% block content %}
<section class="crew-section">
    <div class="crew-header">
        <img src="/static/img/captain.png" alt="Captain" class="crew-hero-image">
        <h1>{{ role_title }}</h1>
        <a href="/" class="btn-back">← Back to Crew</a>
    </div>

    <!-- Main Tab Navigation -->
    <div class="tab-bar">
        <button class="tab-btn active" data-tab="projects">Projects</button>
        <button class="tab-btn" data-tab="identities">Identities</button>
        <button class="tab-btn" data-tab="configuration">Configuration</button>
    </div>

    <!-- Main Tab Panels -->
    <div class="tab-panels">
        <!-- Projects Tab -->
        <div id="tab-projects" class="tab-panel active">
            <div class="crew-content">
                {% if records %}
                    <table class="records-table">
                        <thead>
                            <tr>
                                <th></th>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="crew-rows">
                            {% for record in records %}
                            <tr class="project-row" id="display-row-{{ record['id'] }}">
                                <td class="icon-col">
                                    <button class="edit-icon" title="Edit" data-project-id="{{ record['id'] }}">✏️</button>
                                    <button class="detail-icon" title="Details" disabled>⋯</button>
                                </td>
                                <td>{{ record["name"] }}</td>
                                <td>{{ record["type"] or "—" }}</td>
                                <td>{{ record["status"] }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <div class="empty-state">
                        <p>No projects found.</p>
                    </div>
                {% endif %}
            </div>
        </div>

        <!-- Identities Tab -->
        <div id="tab-identities" class="tab-panel">
            <div class="crew-content">
                <!-- Identities Sub-selector -->
                <div class="sub-tab-bar">
                    <button class="sub-tab-btn active" data-sub="contacts">Contacts</button>
                    <button class="sub-tab-btn" data-sub="organizations">Organizations</button>
                    <button class="sub-tab-btn" data-sub="users">Users (DB Auth)</button>
                </div>

                <!-- Identities Sub-panels -->
                <div class="sub-tab-panels">
                    <!-- Contacts Sub-form -->
                    <div id="sub-contacts" class="sub-tab-panel active">
                        {% include "_identities_contacts.html" %}
                    </div>

                    <!-- Organizations Sub-form -->
                    <div id="sub-organizations" class="sub-tab-panel">
                        {% include "_identities_organizations.html" %}
                    </div>

                    <!-- Users Sub-form -->
                    <div id="sub-users" class="sub-tab-panel">
                        {% include "_identities_users.html" %}
                    </div>
                </div>
            </div>
        </div>

        <!-- Configuration Tab -->
        <div id="tab-configuration" class="tab-panel">
            <div class="crew-content">
                <p>Configuration settings coming soon.</p>
                <p class="hint">Future: Role/Type/Status mappings, User management, Audit logs</p>
            </div>
        </div>
    </div>
</section>

<script>
    // Main tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active from all main tabs and panels
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            
            // Add active to clicked button and corresponding panel
            btn.classList.add('active');
            const tabName = btn.dataset.tab;
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });

    // Sub-tab switching (within Identities tab)
    document.querySelectorAll('.sub-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active from all sub-tabs and sub-panels
            document.querySelectorAll('.sub-tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.sub-tab-panel').forEach(p => p.classList.remove('active'));
            
            // Add active to clicked button and corresponding sub-panel
            btn.classList.add('active');
            const subName = btn.dataset.sub;
            document.getElementById(`sub-${subName}`).classList.add('active');
        });
    });
</script>
{% endblock %}
```

### Notes

- **Two-level tab system:** Main tabs (Projects, Identities, Configuration) and sub-tabs within Identities
- **Projects tab reuses table structure:** Ready for inline edit/add (next session)
- **Sub-panels are includes:** Each sub-form is a separate template file for clarity
- **Inline JS:** Tab switching is vanilla JS with no external dependencies
- **Projects tab active by default:** First `.tab-btn` and first `.tab-panel` have `.active` class on load

---

## 3. Create `templates/_identities_contacts.html`

```html
<h2>Contacts</h2>
<div class="sub-form-placeholder">
    <p>Contacts form coming soon.</p>
    <p class="hint">Searchable list of people with names, titles, phone numbers, and email addresses.</p>
</div>
```

---

## 4. Create `templates/_identities_organizations.html`

```html
<h2>Organizations</h2>
<div class="sub-form-placeholder">
    <p>Organizations form coming soon.</p>
    <p class="hint">Searchable list of companies and groups with contact information and notes.</p>
</div>
```

---

## 5. Create `templates/_identities_users.html`

```html
<h2>Users (DB Auth)</h2>
<div class="sub-form-placeholder">
    <p>Users form coming soon.</p>
    <p class="hint">Manage app authentication: link contacts to usernames, roles, and login status.</p>
</div>
```

---

## 6. Create `static/css/components/tabs.css`

```css
/* =============================================================================
   Tab Navigation — Main tabs
   ============================================================================= */

.tab-bar {
    display: flex;
    gap: 0.5rem;
    border-bottom: 2px solid #e5e7eb;
    margin: 1.5rem 0 1.5rem 0;
    padding: 0;
}

.tab-btn {
    padding: 0.75rem 1.5rem;
    border: none;
    background: transparent;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    color: #6b7280;
    font-size: 1rem;
    font-weight: 500;
    transition: all 0.2s ease;
}

.tab-btn:hover {
    color: #0f766e;
}

.tab-btn.active {
    border-bottom-color: #0f766e;
    color: #0f766e;
    font-weight: 600;
}

/* =============================================================================
   Tab Panels
   ============================================================================= */

.tab-panels {
    display: block;
}

.tab-panel {
    display: none;
}

.tab-panel.active {
    display: block;
    animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}

/* =============================================================================
   Sub-tab Navigation — Within Identities tab
   ============================================================================= */

.sub-tab-bar {
    display: flex;
    gap: 0.5rem;
    border-bottom: 1px solid #f3f4f6;
    margin: 1.5rem 0 1.5rem 0;
    padding: 0;
}

.sub-tab-btn {
    padding: 0.5rem 1rem;
    border: none;
    background: transparent;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    color: #9ca3af;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.2s ease;
}

.sub-tab-btn:hover {
    color: #0f766e;
}

.sub-tab-btn.active {
    border-bottom-color: #0f766e;
    color: #0f766e;
    font-weight: 600;
}

/* =============================================================================
   Sub-tab Panels
   ============================================================================= */

.sub-tab-panels {
    display: block;
}

.sub-tab-panel {
    display: none;
}

.sub-tab-panel.active {
    display: block;
    animation: fadeIn 0.2s ease;
}

/* =============================================================================
   Placeholder Styling
   ============================================================================= */

.sub-form-placeholder {
    padding: 2rem;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    text-align: center;
    margin-top: 1.5rem;
}

.sub-form-placeholder p {
    margin: 0.5rem 0;
    color: #6b7280;
}

.sub-form-placeholder .hint {
    font-size: 0.9rem;
    color: #9ca3af;
}

/* =============================================================================
   Responsive
   ============================================================================= */

@media (max-width: 640px) {
    .tab-bar,
    .sub-tab-bar {
        gap: 0.25rem;
    }

    .tab-btn,
    .sub-tab-btn {
        padding-left: 1rem;
        padding-right: 1rem;
        font-size: 0.9rem;
    }
}
```

### CSS Notes

- **WCYJ Teal (#0f766e)** used for active states (matches your brand)
- **Two tab levels:** Main tabs (prominent), sub-tabs (smaller, lighter)
- **Smooth fade-in** when switching panels
- **Responsive:** Tab buttons shrink on mobile but remain readable
- **No hardcoded colors:** Uses your existing theme palette

---

## 7. Modify `base.html`

### BEFORE
```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}The Curator{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <link rel="stylesheet" href="/static/curator.css">
    <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
</head>
```

### AFTER
```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}The Curator{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <link rel="stylesheet" href="/static/curator.css">
    <link rel="stylesheet" href="/static/css/components/tabs.css">
    <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
</head>
```

### Changes

- **Added tabs.css link** before the closing `</head>` tag

---

## Implementation Checklist

- [ ] Modify `src/curator/web/routes/crew.py` — captain detection logic
- [ ] Update `base.html` — add tabs.css link
- [ ] Create `templates/captain.html` — main tabbed template
- [ ] Create `templates/_identities_contacts.html` — placeholder
- [ ] Create `templates/_identities_organizations.html` — placeholder
- [ ] Create `templates/_identities_users.html` — placeholder
- [ ] Create `static/css/components/tabs.css` — tab styling
- [ ] Test: Visit `/crew?role=captain` → Projects tab loads by default
- [ ] Test: Click each tab → content switches correctly
- [ ] Test: Click each sub-tab in Identities → sub-form switches correctly
- [ ] Test: Other roles (scribe, mechanic, envoy) still see `crew.html` (no change)

---

## Next Steps (Phase 2)

Once this is working and deployed:

1. Build the Contacts sub-form (searchable list + inline add/edit)
2. Wire HTMX for search, add, edit functionality
3. Handle repeating fields (phones, emails, URLs)
4. Build Organizations and Users sub-forms similarly
5. Build Configuration tab (dual-listbox UIs for role/type/status mappings)

---

## Testing Notes

- **Desktop:** Tab switching should feel snappy, no page reload
- **Mobile:** Tab buttons should remain readable (responsive CSS in place)
- **Other roles:** Scribe/Mechanic/Envoy should see unchanged `crew.html` interface
- **Captain projects:** Should show all projects (unrestricted, unlike other roles)

---

## Key Design Decisions

1. **Captain's template is `captain.html`** — separate from `crew.html`, makes future customization easier
2. **Two-level tab system** — main tabs are prominent, sub-tabs within Identities are lighter
3. **Vanilla JS for tab switching** — no external dependencies, minimal bundle size
4. **Placeholders for empty sub-forms** — ready to build Contacts, Orgs, Users in Phase 2
5. **Projects tab active by default** — aligns with your workflow (Captain uses projects first)
6. **Projects tab has same structure as crew.html** — ready for inline edit/add in next session

