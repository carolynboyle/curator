# Changedoc: Crew Pages — Integrate Detail Panel Container

**Date:** 2026-06-27  
**Files:** `templates/captain.html`, `templates/crew.html`  
**Reason:** Add detail panel container placeholder to crew pages (identical on all pages)

---

## The Key Insight

**There is no role-specific branching needed.**

- Role filtering happens at the **database level** (projects.captain_view, projects.mechanic_view, etc.)
- Captain and all other roles see the **exact same detail panel HTML and CSS**
- When mechanic clicks ⋯, they see the same tabs as captain — but they only got there because the database view filtered records to just the ones mechanic is allowed to see

So `captain.html` and `crew.html` (used for all non-captain roles) can use **identical detail panel code**.

---

## Conceptual Change

The detail panel needs to live in the page DOM alongside the hero image. When a user clicks ⋯ on a datasheet row, JavaScript fetches the full record and activates the detail panel (fading out the hero image).

---

## BEFORE (all crew role pages — identical)

```html
<!-- captain.html OR crew.html (or any role-specific page) -->
<!-- These can be the same template or use the same structure -->

<main>
  <!-- Hero image area -->
  <div class="crew-hero">
    {# Hero content #}
  </div>

  <!-- Projects datasheet grid -->
  <div class="tab-content">
    {% include '_projects_table.html' %}
  </div>
</main>
```

---

## AFTER (all crew role pages — identical)

```html
<!-- captain.html OR crew.html (or any role-specific page) -->
<!-- Apply this change identically to all crew pages -->

<main>
  <!-- Hero image area — fades out when detail panel opens -->
  <div class="crew-hero">
    {# Hero content #}
  </div>

  <!-- Detail panel container — rendered via JavaScript -->
  <!-- Initially empty. When user clicks ⋯ on a row, JS fetches the record
       and renders _detail_panel.html into this container. -->
  <div id="detail-panel-container"></div>

  <!-- Projects datasheet grid -->
  <div class="tab-content">
    {% include '_projects_table.html' %}
  </div>
</main>
```

---

## That's It

Just add `<div id="detail-panel-container"></div>` after the hero on **every crew page**. No branching. No role-specific logic. The database views already filtered the records, so mechanic only sees mechanic projects in the grid. When they click ⋯ on one, the detail panel opens with that project — same code everywhere.

---

## Changes to `_projects_table.html` (or Any Role-Specific Datasheet)

The `⋯` column must wire up to `openDetailPanel()`. This change applies to **every datasheet** that should open a detail panel (projects, contacts, organizations).

### BEFORE (hypothetical current state)

```html
<!-- _projects_table.html -->
<div id="projects-datasheet"></div>

<script type="module">
  import Tabulator from '/static/lib/tabulator/tabulator.esm.js';

  const columns = [
    { title: "Name", field: "name", width: 200 },
    { title: "Type", field: "type", width: 100 },
    { title: "Status", field: "status", width: 100 },
    {
      title: "⋯",
      field: "id",
      width: 40,
      hozAlign: "center",
      formatter: (cell) => {
        const id = cell.getValue();
        return `<button class="detail-button" data-id="${id}">⋯</button>`;
      }
    }
  ];

  const table = new Tabulator('#projects-datasheet', {
    columns: columns,
    // ... other config
  });
</script>
```

### AFTER

```html
<!-- _projects_table.html -->
<div id="projects-datasheet"></div>

<script type="module">
  import Tabulator from '/static/lib/tabulator/tabulator.esm.js';
  import { openDetailPanel } from '/static/js/detail-panel.js';

  const columns = [
    { title: "Name", field: "name", width: 200 },
    { title: "Type", field: "type", width: 100 },
    { title: "Status", field: "status", width: 100 },
    {
      title: "⋯",
      field: "id",
      width: 40,
      hozAlign: "center",
      formatter: (cell) => {
        const id = cell.getValue();
        return `<button class="detail-button" data-id="${id}">⋯</button>`;
      }
    }
  ];

  const table = new Tabulator('#projects-datasheet', {
    columns: columns,
    // ... other config
  });

  // Wire up ⋯ button clicks to open detail panel
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('detail-button')) {
      const projectId = e.target.dataset.id;
      openDetailPanel('projects', projectId);
    }
  });
</script>
```

---

## New Endpoint Required: `GET /crew/{entity}/{id}`

The `openDetailPanel()` function expects a GET endpoint to fetch the full record:

```
GET /crew/projects/123
GET /crew/contacts/456
GET /crew/organizations/789
```

Response should be JSON with the full record data (name, type_id, status_id, description, etc.).

This endpoint should already exist or be trivial to add from existing `_fetch_project_for_display()` function in crew.py.

---

## JavaScript Import

Add this to `base.html` in the `<head>` or before closing `</body>`:

```html
<!-- Detail panel initialization -->
<script type="module" src="/static/js/detail-panel.js"></script>
```

This imports and runs `initDetailPanel()` automatically on page load, setting up:
- Tab switching via click handlers
- Close button (×) functionality
- Escape key to close
- Form save on Details tab submit

---

## Why These Changes

1. **Detail panel container** — JavaScript needs a place to render the panel into. The container is initially empty; JS populates it when a user clicks ⋯.

2. **⋯ button wiring** — When user clicks ⋯, we call `openDetailPanel(entity, recordId)`, which:
   - Fetches full record via `GET /crew/{entity}/{id}`
   - Renders `_detail_panel.html` into the container
   - Fades out hero, fades in detail panel
   - Resets to first tab (Details)

3. **detail-panel.js import** — Initializes all the event listeners (tab switching, close button, form save, Escape key).

The detail panel itself is stateless — it gets rendered/destroyed as needed, and all styling is in `detail-panel.css`. Role access control is entirely handled by the database views that feed the datasheet.
