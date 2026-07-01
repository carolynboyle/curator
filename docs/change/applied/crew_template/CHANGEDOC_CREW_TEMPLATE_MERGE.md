# Changedoc: crew.py — Add Tab Configuration, Remove captain.html

**Date:** 2026-06-27  
**File:** `src/curator/web/routes/crew.py`  
**Reason:** Add role-based tab configuration to support unified crew.html template. Remove captain.html reference.

---

## BEFORE (template selection block in crew_dashboard)

```python
    if role == "captain":
        template = env.get_template("captain.html")
    else:
        template = env.get_template("crew.html")

    if role == "captain":
        contacts = await _fetch_contacts(db)
        organizations = await _fetch_organizations(db)
    else:
        contacts = []
        organizations = []

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
        "contacts": contacts,
        "organizations": organizations,
    }

    return HTMLResponse(template.render(**data))
```

---

## AFTER

```python
    # Tab definitions per role
    # Each tab references a partial in templates/partials/
    # Future: load from database (identity.landing_card)
    role_tabs = {
        "captain": [
            {"id": "projects",      "label": "Projects",      "template": "_tab_projects.html"},
            {"id": "identities",    "label": "Identities",    "template": "_tab_identities.html"},
            {"id": "configuration", "label": "Configuration", "template": "_tab_configuration.html"},
        ],
        "scribe": [
            {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
        ],
        "mechanic": [
            {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
        ],
        "envoy": [
            {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
        ],
    }

    # Fetch captain-only data
    if role == "captain":
        contacts = await _fetch_contacts(db)
        organizations = await _fetch_organizations(db)
    else:
        contacts = []
        organizations = []

    template = env.get_template("crew.html")

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
        "contacts": contacts,
        "organizations": organizations,
        "tabs": role_tabs.get(role, [{"id": "projects", "label": "Projects", "template": "_tab_projects.html"}]),
    }

    return HTMLResponse(template.render(**data))
```

---

## Why These Changes

- All roles now use a single `crew.html` template
- `captain.html` is deleted — no longer needed
- Tabs are defined in Python as a list of dicts passed to the template
- Adding a new tab to any role = add one entry to `role_tabs`
- Adding a new role = add one entry to `role_tabs`
- Future: `role_tabs` moves to database (`identity.landing_card` table per the roadmap design)

## After Making This Change

1. Delete `src/curator/templates/captain.html`
2. Copy new `crew.html` to `src/curator/templates/crew.html`
3. Copy new tab partials to `src/curator/templates/partials/`
