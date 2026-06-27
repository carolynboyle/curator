# Detail Panel Architecture — QueryLoader Integration

**Status:** Design skeleton (for approval before implementation)  
**Date:** 2026-06-27

---

## Overview

The detail panel opens when a user clicks `⋯` on a datasheet row. It displays a tabbed form where child datasheets (Tasks, Emails, Phones, etc.) are rendered using a reusable `_datasheet.html` partial. All child datasheets fetch data via a generic `/api/query/{entity}/{query_name}` endpoint powered by `QueryLoader`.

---

## 1. New Queries in `queries.yaml`

Add these query groups to support child datasheets across all entities:

```yaml
# Existing queries remain unchanged above

tasks:
  # Existing task queries...
  get_by_id:
    type: select_one
    sql: "SELECT * FROM v_tasks WHERE id = %s"
  # ... etc
  
  # NEW: Fetch all tasks for a project (for detail panel Tasks tab)
  for_project:
    type: select_all
    sql: |
      SELECT
          id,
          name::text,
          status_id,
          assignee_id,
          due_date
      FROM projects.task
      WHERE project_id = %s
      ORDER BY created_at DESC

contact_emails:
  # NEW: Fetch all emails for a contact (for detail panel Emails tab)
  for_contact:
    type: select_all
    sql: |
      SELECT
          id,
          label::text,
          address::text
      FROM identity.contact_emails
      WHERE contact_id = %s
      ORDER BY id

contact_phones:
  # NEW: Fetch all phones for a contact (for detail panel Phones tab)
  for_contact:
    type: select_all
    sql: |
      SELECT
          id,
          label::text,
          number::text
      FROM identity.contact_phones
      WHERE contact_id = %s
      ORDER BY id

contact_urls:
  # NEW: Fetch all URLs for a contact (for detail panel URLs tab)
  for_contact:
    type: select_all
    sql: |
      SELECT
          id,
          type::text,
          value::text
      FROM identity.contact_urls
      WHERE contact_id = %s
      ORDER BY id

organization_contacts:
  # NEW: Fetch all contacts in an organization (for detail panel Contacts tab)
  for_organization:
    type: select_all
    sql: |
      SELECT
          c.id,
          c.name::text,
          c.title::text,
          oc.role::text
      FROM identity.contacts c
      JOIN identity.organization_contacts oc
          ON oc.contact_id = c.id
      WHERE oc.organization_id = %s
      ORDER BY c.name
```

---

## 2. Generic `/api/query/{entity}/{query_name}` Endpoint

Add this route to `crew.py`:

```python
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader

# At module level (after router initialization):
queries_path = Path(__file__).parent.parent.parent / "queries.yaml"
query_builder = QueryBuilder(queries_path)
query_loader = QueryLoader(query_builder)

@router.get("/api/query/{entity}/{query_name}")
async def run_query(
    entity: str,
    query_name: str,
    params: list = Query(None),
    db: AsyncDBConnection = Depends(get_db),
):
    """
    Generic query endpoint for fetching data via QueryLoader.
    
    Path parameters:
        entity:     Entity key (e.g., "tasks", "contact_emails")
        query_name: Query name within entity (e.g., "for_project")
    
    Query parameters:
        params: Comma-separated list of bind parameters
                (e.g., ?params=123,456)
    
    Returns:
        JSON with { "records": [...] } for Tabulator
    """
    try:
        sql = query_loader.sql(entity, query_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    params_list = []
    if params:
        params_list = params.split(",")
    
    rows = await db.fetch_all(sql, tuple(params_list))
    return JSONResponse({
        "records": [dict(r) for r in rows]
    })
```

---

## 3. Reusable `_datasheet.html` Partial

Location: `templates/_datasheet.html`

This partial accepts parameters from Jinja2 `include`:

```html
{# Reusable Tabulator datasheet partial #}
{# 
  Parameters:
    - container_id (str): DOM id for Tabulator to mount to
    - query_name (str): Queryloader query name (e.g., "for_project")
    - entity (str): QueryLoader entity name (e.g., "tasks")
    - query_params (str): Comma-separated bind parameters (e.g., "123")
    - columns (list): Column definitions for Tabulator
    - save_url (str): POST endpoint for saving rows
    - add_url (str, optional): POST endpoint for adding new rows
#}

<div id="{{ container_id }}" style="height: 100%; overflow-y: auto;"></div>

<script type="module">
  import Tabulator from '/static/lib/tabulator/tabulator.esm.js';

  const container = document.getElementById('{{ container_id }}');
  const queryName = '{{ query_name }}';
  const entity = '{{ entity }}';
  const queryParams = '{{ query_params }}';
  const ajaxUrl = `/api/query/${entity}/${queryName}?params=${queryParams}`;
  
  const columns = {{ columns | tojson }};
  const saveUrl = '{{ save_url }}';
  const addUrl = '{{ add_url }}';

  const table = new Tabulator(container, {
    height: '100%',
    layout: 'fitColumns',
    selectable: true,
    clipboard: true,
    ajax: {
      url: ajaxUrl,
      headers: { 'Accept': 'application/json' },
    },
    ajaxResponse: (url, params, response) => {
      return response.records || [];
    },
    columns: columns,
    dataLoaded: (data) => {
      // Datasheet loaded successfully
    },
    dataLoadError: (error) => {
      console.error(`Failed to load ${entity}/${queryName}:`, error);
    },
  });

  // Save on Ctrl+S or blur (deferred — implement after structure approved)
  // Add new row on + button (deferred — implement after structure approved)
</script>
```

---

## 4. Detail Panel Structure

### HTML Skeleton

Location: `templates/_detail_panel.html`

```html
{#
  Detail panel — replaces hero image when ⋯ is clicked on a datasheet row.
  
  Parameters:
    - entity (str): Entity type ("projects", "contacts", "organizations")
    - record_id (int): ID of the record being displayed
    - record (dict): Full record data for form fields
#}

<div class="detail-panel" data-entity="{{ entity }}" data-id="{{ record_id }}">
  <!-- Tab navigation -->
  <div class="detail-tabs">
    <button class="detail-tab-button active" data-tab="details">Details</button>
    {% if entity == "projects" %}
      <button class="detail-tab-button" data-tab="tasks">Tasks</button>
      <button class="detail-tab-button" data-tab="links">Links</button>
      <button class="detail-tab-button" data-tab="contacts">Contacts</button>
    {% elif entity == "contacts" %}
      <button class="detail-tab-button" data-tab="emails">Emails</button>
      <button class="detail-tab-button" data-tab="phones">Phones</button>
      <button class="detail-tab-button" data-tab="urls">URLs</button>
      <button class="detail-tab-button" data-tab="organizations">Organizations</button>
    {% elif entity == "organizations" %}
      <button class="detail-tab-button" data-tab="contacts">Contacts</button>
    {% endif %}
    <button class="detail-close-button" aria-label="Close detail panel">×</button>
  </div>

  <!-- Tab content container -->
  <div class="detail-tab-panels">
    
    <!-- Details Tab (always first) -->
    <div class="detail-tab-panel active" data-tab="details">
      <form class="detail-form" data-entity="{{ entity }}" data-id="{{ record_id }}">
        {% if entity == "projects" %}
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>
          <div class="form-group">
            <label for="detail-type">Type</label>
            <select id="detail-type" name="type_id">
              <option value="">—</option>
              {% for type in project_types %}
                <option value="{{ type.id }}" {% if record.type_id == type.id %}selected{% endif %}>
                  {{ type.name }}
                </option>
              {% endfor %}
            </select>
          </div>
          <div class="form-group">
            <label for="detail-status">Status</label>
            <select id="detail-status" name="status_id">
              <option value="">—</option>
              {% for status in project_statuses %}
                <option value="{{ status.id }}" {% if record.status_id == status.id %}selected{% endif %}>
                  {{ status.name }}
                </option>
              {% endfor %}
            </select>
          </div>
          <div class="form-group">
            <label for="detail-description">Description</label>
            <textarea id="detail-description" name="description">{{ record.description or '' }}</textarea>
          </div>
        
        {% elif entity == "contacts" %}
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>
          <div class="form-group">
            <label for="detail-title">Title</label>
            <input type="text" id="detail-title" name="title" value="{{ record.title or '' }}" />
          </div>
        
        {% elif entity == "organizations" %}
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>
        {% endif %}
        
        <div class="form-actions">
          <button type="submit" class="btn-save">Save</button>
          <button type="reset" class="btn-discard">Discard</button>
        </div>
      </form>
    </div>

    <!-- Child Datasheets (project tasks, contact emails, etc.) -->
    {% if entity == "projects" %}
      <!-- Tasks Tab -->
      <div class="detail-tab-panel" data-tab="tasks">
        {% include '_datasheet.html' with
            container_id='tasks-datasheet',
            entity='tasks',
            query_name='for_project',
            query_params=record.id,
            columns=[
              { "title": "Name", "field": "name", "width": 200, "editor": "input" },
              { "title": "Status", "field": "status_id", "width": 100, "editor": "select", "editorParams": { "values": status_map } },
              { "title": "Assignee", "field": "assignee_id", "width": 100, "editor": "select", "editorParams": { "values": contact_map } },
              { "title": "Due", "field": "due_date", "width": 100, "editor": "input", "inputType": "date" }
            ],
            save_url='/crew/tasks/save',
            add_url='/crew/tasks/add'
        %}
      </div>

      <!-- Links Tab (deferred) -->
      <div class="detail-tab-panel" data-tab="links">
        <p>Links tab — deferred</p>
      </div>

      <!-- Contacts Tab (deferred) -->
      <div class="detail-tab-panel" data-tab="contacts">
        <p>Contacts tab — deferred</p>
      </div>

    {% elif entity == "contacts" %}
      <!-- Emails Tab -->
      <div class="detail-tab-panel" data-tab="emails">
        {% include '_datasheet.html' with
            container_id='emails-datasheet',
            entity='contact_emails',
            query_name='for_contact',
            query_params=record.id,
            columns=[
              { "title": "Label", "field": "label", "width": 100, "editor": "input" },
              { "title": "Address", "field": "address", "width": 200, "editor": "input" }
            ],
            save_url='/crew/contacts/emails/save',
            add_url='/crew/contacts/emails/add'
        %}
      </div>

      <!-- Phones Tab -->
      <div class="detail-tab-panel" data-tab="phones">
        {% include '_datasheet.html' with
            container_id='phones-datasheet',
            entity='contact_phones',
            query_name='for_contact',
            query_params=record.id,
            columns=[
              { "title": "Label", "field": "label", "width": 100, "editor": "input" },
              { "title": "Number", "field": "number", "width": 200, "editor": "input" }
            ],
            save_url='/crew/contacts/phones/save',
            add_url='/crew/contacts/phones/add'
        %}
      </div>

      <!-- URLs Tab -->
      <div class="detail-tab-panel" data-tab="urls">
        {% include '_datasheet.html' with
            container_id='urls-datasheet',
            entity='contact_urls',
            query_name='for_contact',
            query_params=record.id,
            columns=[
              { "title": "Type", "field": "type", "width": 100, "editor": "input" },
              { "title": "Value", "field": "value", "width": 200, "editor": "input" }
            ],
            save_url='/crew/contacts/urls/save',
            add_url='/crew/contacts/urls/add'
        %}
      </div>

      <!-- Organizations Tab -->
      <div class="detail-tab-panel" data-tab="organizations">
        {% include '_datasheet.html' with
            container_id='orgs-datasheet',
            entity='organization_contacts',
            query_name='for_contact',
            query_params=record.id,
            columns=[
              { "title": "Organization", "field": "name", "width": 200 },
              { "title": "Role", "field": "role", "width": 100, "editor": "input" }
            ],
            save_url='/crew/organizations/contacts/save'
        %}
      </div>

    {% elif entity == "organizations" %}
      <!-- Contacts Tab -->
      <div class="detail-tab-panel" data-tab="contacts">
        {% include '_datasheet.html' with
            container_id='contacts-datasheet',
            entity='organization_contacts',
            query_name='for_organization',
            query_params=record.id,
            columns=[
              { "title": "Name", "field": "name", "width": 200 },
              { "title": "Title", "field": "title", "width": 150 },
              { "title": "Role", "field": "role", "width": 100, "editor": "input" }
            ],
            save_url='/crew/organizations/contacts/save'
        %}
      </div>
    {% endif %}

  </div>
</div>
```

---

## 5. Detail Panel CSS

Location: `static/css/components/detail-panel.css`

```css
/* Detail panel container */
.detail-panel {
  display: none;
  flex-direction: column;
  height: 420px;  /* Match hero image height */
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  background: var(--bg-secondary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.detail-panel.active {
  display: flex;
}

/* Tab navigation */
.detail-tabs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.detail-tab-button {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.detail-tab-button:hover {
  color: var(--text-primary);
}

.detail-tab-button.active {
  color: var(--text-primary);
  border-bottom-color: var(--primary-color);
}

.detail-close-button {
  margin-left: auto;
  padding: 0.25rem 0.5rem;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
}

.detail-close-button:hover {
  color: var(--text-primary);
}

/* Tab panels container */
.detail-tab-panels {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.detail-tab-panel {
  display: none;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  padding: 0.75rem;
  overflow-y: auto;
}

.detail-tab-panel.active {
  display: block;
}

/* Details form */
.detail-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 0.25rem;
  font-family: inherit;
  font-size: inherit;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.form-group textarea {
  resize: vertical;
  min-height: 4rem;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-save,
.btn-discard {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-save {
  background: var(--primary-color);
  color: white;
}

.btn-save:hover {
  opacity: 0.9;
}

.btn-discard {
  background: var(--border-color);
  color: var(--text-primary);
}

.btn-discard:hover {
  background: var(--bg-secondary);
}

/* Child datasheets inherit light theme from tabulator-overrides.css */
.detail-tab-panel [id$='-datasheet'] {
  height: 100%;
}
```

---

## 6. Hero ↔ Panel Transition

Add to relevant CSS file (or `captain.css`):

```css
.crew-hero {
  transition: opacity 0.2s ease, visibility 0.2s ease;
}

.crew-hero.hidden {
  opacity: 0;
  visibility: hidden;
}

.detail-panel {
  transition: opacity 0.2s ease, visibility 0.2s ease;
}

.detail-panel.active {
  opacity: 1;
  visibility: visible;
}
```

---

## 7. Integration Points

### In `captain.html` (or wherever projects grid lives)

When rendering the projects table, wrap it with hero + detail panel:

```html
<div class="crew-hero" id="hero-image">
  {# Existing hero image markup #}
</div>

{# Detail panel placeholder — will be populated via JS #}
<div id="detail-panel-container"></div>

{# Projects datasheet #}
{% include '_projects_table.html' %}
```

When user clicks `⋯` on a row:
1. JS fetches full record data
2. Renders `_detail_panel.html` into `#detail-panel-container`
3. Fades out hero, fades in detail panel
4. Attaches event listeners for tab switching, form save, etc.

---

## 8. Implementation Order

1. **Add queries to `queries.yaml`** — list above
2. **Add `/api/query/{entity}/{query_name}` endpoint to `crew.py`**
3. **Create `_datasheet.html` partial** — reusable Tabulator instance
4. **Create `_detail_panel.html` partial** — tab structure + Details form
5. **Create `detail-panel.css`** — all styling
6. **Wire detail panel opening** in JavaScript (click `⋯` → fetch record → render panel → attach listeners)
7. **Wire tab switching** in JavaScript (click tab button → show/hide panels)
8. **Implement form save** for Details tab (blur or Save button click)
9. **Implement child datasheet row save** (deferred until after structure approval)

---

## 9. Questions for Approval

1. **Does the `/api/query` endpoint design feel right?** (Generic, powered by `QueryLoader`, easy to add new queries)

2. **For the Details form, should we persist changes on blur, or only on Save button click?** (Design doc says "on save", but worth confirming)

3. **Should the `_datasheet.html` partial also include a `+` button for adding new rows, or should that live in the detail panel tab header?** (Currently deferred)

4. **For project Tasks tab — do we need to fetch the full contact list for the Assignee dropdown, or should we fetch it on-demand?** (May affect query design)

5. **Is the CSS variable approach (`var(--primary-color)`, etc.) correct, or should we use specific colors?** (Want to match existing theme setup)

