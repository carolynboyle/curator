# Captain's Command Center — Implementation Guide

## Overview

This document contains all code changes needed to build the Captain's tabbed page. The Captain gets a special-case route that shows three tabs: Projects, Identities, and Configuration. The Identities tab has sub-selectors for Contacts, Organizations, and Users.

**Key design decisions:**
- Captain's page defaults to Projects tab (your primary workflow)
- Projects tab has same inline edit/add as other roles
- Identities tab is a two-level interface: main sub-selector buttons + three sub-forms
- Configuration tab is a placeholder for Phase 2+
- All routing happens within `/crew?role=captain` — no new URLs

---

## File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/curator/web/routes/crew.py` | Modify | Add captain detection, select captain.html template |
| `src/curator/templates/base.html` | Modify | Link tabs.css |
| `src/curator/templates/captain.html` | Create | Main tabbed layout with Projects/Identities/Configuration |
| `src/curator/templates/_identities_contacts.html` | Create | Contacts sub-form placeholder |
| `src/curator/templates/_identities_organizations.html` | Create | Organizations sub-form placeholder |
| `src/curator/templates/_identities_users.html` | Create | Users sub-form placeholder |
| `static/css/components/tabs.css` | Create | Tab styling and animations |

---

## 1. Modify `src/curator/web/routes/crew.py`

### Location

In the `crew_dashboard()` function, around line 160-190, after the HTMX handling block.

### BEFORE
at line 198:
```python
template = env.get_template("crew.html")
```

### AFTER
replace line 198 with:
```python
# Captain gets a tabbed interface; other roles get the standard datasheet
if role == "captain":
    template = env.get_template("captain.html")
else:
    template = env.get_template("crew.html")
    
    
```

### What Changed

- **Added 3 lines** to detect `role == "captain"` and select appropriate template
- **Everything else stays the same** — data dict, queries, lookups all unchanged
- **Other roles unchanged** — scribe, mechanic, envoy still render crew.html

---

## 2. Modify `src/curator/templates/base.html`

### Location

In the `<head>` section, within the "Component styles" block.

### BEFORE

```html
    <!-- Component styles -->
    <link rel="stylesheet" href="/static/css/components/navbar.css">
    <link rel="stylesheet" href="/static/css/components/card.css">
    <link rel="stylesheet" href="/static/css/components/table.css">
    <link rel="stylesheet" href="/static/css/components/empty-state.css">
    <link rel="stylesheet" href="/static/css/components/forms.css">

    <!-- Theme -->
```

### AFTER

```html
    <!-- Component styles -->
    <link rel="stylesheet" href="/static/css/components/navbar.css">
    <link rel="stylesheet" href="/static/css/components/card.css">
    <link rel="stylesheet" href="/static/css/components/table.css">
    <link rel="stylesheet" href="/static/css/components/empty-state.css">
    <link rel="stylesheet" href="/static/css/components/forms.css">
    <link rel="stylesheet" href="/static/css/components/tabs.css">

    <!-- Theme -->
```

### What Changed

- **Added 1 line** to link the new tabs.css file
- Placed after forms.css to follow the component loading pattern

---

## 3. Create `src/curator/templates/captain.html`

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

- **Projects tab active by default** — first button and panel have `.active` class on load
- **Two-level tab system** — main tabs (Projects, Identities, Configuration) and sub-tabs within Identities
- **Projects table ready for inline edit/add** — same structure as crew.html, will work with existing edit/add routes
- **Sub-panels are includes** — each sub-form is a separate template file for clarity
- **Vanilla JS** — no external dependencies, minimal bundle size

---

## 4. Create `src/curator/templates/_identities_contacts.html`

```html
<h2>Contacts</h2>
<div class="sub-form-placeholder">
    <p>Contacts form coming soon.</p>
    <p class="hint">Searchable list of people with names, titles, phone numbers, and email addresses.</p>
</div>
```

---

## 5. Create `src/curator/templates/_identities_organizations.html`

```html
<h2>Organizations</h2>
<div class="sub-form-placeholder">
    <p>Organizations form coming soon.</p>
    <p class="hint">Searchable list of companies and groups with contact information and notes.</p>
</div>
```

---

## 6. Create `src/curator/templates/_identities_users.html`

```html
<h2>Users (DB Auth)</h2>
<div class="sub-form-placeholder">
    <p>Users form coming soon.</p>
    <p class="hint">Manage app authentication: link contacts to usernames, roles, and login status.</p>
</div>
```

---

## 7. Create `static/css/components/tabs.css`

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
- **Two tab levels:** Main tabs (prominent, 1rem size), sub-tabs (smaller, 0.9rem, lighter gray)
- **Smooth fade-in** animation when switching panels (0.2s ease)
- **Responsive design:** Tab buttons shrink on mobile but remain readable
- **Placeholder styling:** Light gray background box with centered text, ready for future form content

---

## Implementation Checklist

### Step 1: Modify crew.py
- [ ] Open `src/curator/web/routes/crew.py`
- [ ] Find line `template = env.get_template("crew.html")` (around line 175)
- [ ] Replace with the 4-line captain detection block
- [ ] Save file

### Step 2: Modify base.html
- [ ] Open `src/curator/templates/base.html`
- [ ] Find the `<link rel="stylesheet" href="/static/css/components/forms.css">` line
- [ ] Add new line below it: `<link rel="stylesheet" href="/static/css/components/tabs.css">`
- [ ] Save file

### Step 3: Create captain.html
- [ ] Create new file: `src/curator/templates/captain.html`
- [ ] Copy the entire captain.html template from Section 3 above
- [ ] Save file

### Step 4: Create identity sub-form placeholders
- [ ] Create `src/curator/templates/_identities_contacts.html` (Section 4)
- [ ] Create `src/curator/templates/_identities_organizations.html` (Section 5)
- [ ] Create `src/curator/templates/_identities_users.html` (Section 6)
- [ ] Save all three files

### Step 5: Create tabs.css
- [ ] Create new file: `static/css/components/tabs.css`
- [ ] Copy the entire CSS from Section 7 above
- [ ] Save file

### Step 6: Test
- [ ] Start Curator app
- [ ] Navigate to `/crew?role=captain`
- [ ] Verify Projects tab loads first (active)
- [ ] Click Identities tab → see Contacts sub-form
- [ ] Click Organizations button → sub-form switches
- [ ] Click Users button → sub-form switches
- [ ] Click Configuration tab → see placeholder text
- [ ] Click back to Projects tab → should work
- [ ] Visit `/crew?role=scribe` → should still show crew.html (unchanged)
- [ ] Test search on Projects tab → should still work via HTMX

---

## Next Steps (Phase 2)

Once this is working and deployed:

1. **Build Contacts sub-form**
   - Searchable list of contacts (name, title)
   - Inline add (+ button)
   - Inline edit (pencil icon)
   - Sub-fields: phones, emails, URLs (repeating fields)

2. **Build Organizations sub-form**
   - Similar structure to Contacts
   - Fields: name, notes

3. **Build Users (DB Auth) sub-form**
   - Link existing contact to app_user
   - Set username, password, user_role, is_active

4. **Build Configuration tab**
   - Dual-listbox UIs for role/type/status mappings
   - Settings management interface

---

## Key Design Decisions

1. **Captain's template is `captain.html`** — separate from `crew.html`, makes future customization easier without breaking other roles
2. **Two-level tab system** — main tabs are prominent, sub-tabs within Identities are lighter weight
3. **Vanilla JS for tab switching** — no external dependencies, minimal bundle size, easy to maintain
4. **Placeholders for empty sub-forms** — ready to build Contacts, Orgs, Users in Phase 2 without structural changes
5. **Projects tab active by default** — aligns with your workflow (Captain uses projects first)
6. **Projects tab has same structure as crew.html** — reuses existing inline edit/add rows, no duplication
7. **Same data passed to all templates** — both `crew.html` and `captain.html` receive records, types, statuses

---

## Testing Notes

- **Desktop:** Tab switching should feel snappy with no page reload
- **Mobile:** Tab buttons should remain readable (responsive CSS in place)
- **Other roles:** Scribe/Mechanic/Envoy should see unchanged `crew.html` interface
- **Captain projects:** Should show all projects (unrestricted, unlike other roles)
- **HTMX search:** Should still work on Captain's Projects tab
- **Inline edit/add:** Should work exactly as before (same rows, same routes)

---

## File Paths Quick Reference

```
src/curator/
├── web/
│   └── routes/
│       └── crew.py ← Modify (line ~175)
├── templates/
│   ├── base.html ← Modify (add tabs.css link)
│   ├── captain.html ← Create (new)
│   ├── _identities_contacts.html ← Create (new)
│   ├── _identities_organizations.html ← Create (new)
│   └── _identities_users.html ← Create (new)

static/
└── css/
    └── components/
        └── tabs.css ← Create (new)
```
