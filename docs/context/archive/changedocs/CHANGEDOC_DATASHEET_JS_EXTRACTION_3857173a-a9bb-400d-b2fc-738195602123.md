# Changedoc: datasheet.js Extraction + parent_field Fix

**Date:** 2026-07-08
**Depends on:** `_datasheet.html`, `_datasheet_with_header.html`, `base.html`
(all as uploaded this session)

**Scope:** Two related fixes in one unit:
1. Extract `_datasheet.html`'s inline `<script>` to a real
   `static/js/datasheet.js` ES module — same pattern as
   `bidirectional-filter.js` and `detail-panel.js`.
2. Replace the `paramKey` string-guessing heuristic with an explicit
   `parent_field` config parameter — fixes a real bug that would produce
   `task_id` instead of `project_id` for the Tasks child datasheet.

No SQL. No new routes. No `base.html` change — `datasheet.js` is imported
on demand by `_datasheet.html`'s `<script type="module">` block, not loaded
on every page the way `detail-panel.js` is (same lazy-import pattern
`_tab_identities.html` already uses for `bidirectional-filter.js`).

**Known gaps NOT fixed in this changedoc (logged separately):**
- `_datasheet.html`'s save/delete calls hit `/api/{entity}/save` and
  `/api/{entity}/{id}` — routes that don't exist; real routes are under
  `/crew/{entity}/...`. Fix deferred to next session.
- `_datasheet_with_header.html`'s `+ Add` button does nothing — its
  `<script type="module">` block is explicitly empty. Fix deferred to
  next session.

---

## The `paramKey` bug, precisely

```js
// BEFORE — in _datasheet.html's inline <script>
const paramKey = '{{ entity }}'.replace(/s$/, '_id')
    .replace('contact_email', 'contact')
    .replace('contact_phone', 'contact');
```

For `entity='tasks'`, this produces `task_id` — but the actual foreign key
column for a task's parent project is `project_id`. The result: every new
task row created through a child datasheet would send `{"task_id": 12}`
instead of `{"project_id": 12}`, silently saving the wrong field (or, more
likely, the proc ignoring it and creating an orphaned record).

The fix: `parent_field` is passed explicitly by whoever includes the
datasheet, the same way `entity`/`query_name`/`columns` already are. No
guessing from string patterns, no hardcoded special cases.

---

## Apply order

Three file changes, no pgAdmin steps:
1. Create `static/js/datasheet.js` (new file)
2. Replace `_datasheet.html`
3. Replace `_datasheet_with_header.html`

Then restart uvicorn and verify (see bottom of doc).

---

## `static/js/datasheet.js` (new file)

```javascript
/**
 * datasheet.js
 *
 * Generic Tabulator child-datasheet engine for Curator.
 * Called by _datasheet.html's <script type="module"> block on every
 * panel tab that includes a child datasheet (Tasks, Emails, Phones,
 * URLs, Contacts, etc.).
 *
 * Usage (from _datasheet.html's generated module script):
 *
 *   import { initDatasheet } from '/static/js/datasheet.js';
 *
 *   initDatasheet({
 *     containerId:  'tasks-datasheet',
 *     entity:       'tasks',
 *     queryName:    'for_project',
 *     queryParams:  '12',
 *     columns:      [...],
 *     parentField:  'project_id',   // explicit FK — never guessed
 *   });
 *
 * Known gaps (see CHANGEDOC_DATASHEET_JS_EXTRACTION.md):
 *   - save/delete URLs are /api/{entity}/... — routes that don't exist yet.
 *     Real routes live under /crew/{entity}/... Fix in next changedoc.
 *   - + Add button wiring is deferred — same next changedoc.
 */

export function initDatasheet(config) {
    const {
        containerId,
        entity,
        queryName,
        queryParams,
        columns,
        parentField,  // explicit parent FK field name — required for INSERT
                      // to include the correct parent id in the payload.
                      // Pass '' or omit if this datasheet has no parent FK.
    } = config;

    const container = document.getElementById(containerId);
    if (!container) return;

    const ajaxUrl = `/api/query/${entity}/${queryName}?params=${queryParams}`;

    // -------------------------------------------------------------------------
    // Save a row to the server
    // NOTE: URLs below (/api/{entity}/...) do not exist in the current app —
    // real routes are /crew/{entity}/... This is a known gap, not addressed
    // in this changedoc. Saving will 404 until the URL fix lands.
    // -------------------------------------------------------------------------
    async function saveRow(row) {
        const data = row.getData();
        const isNew = !data.id;

        // Don't save a new row with no content — just delete it
        const firstEditable = columns.find(c => c.editor);
        if (isNew && firstEditable && !data[firstEditable.field]) {
            row.delete();
            return true;
        }

        const url = isNew
            ? `/api/${entity}/save`
            : `/api/${entity}/${data.id}/save`;

        // Only send editable columns
        const editableFields = columns
            .filter(c => c.editor && c.field !== 'id')
            .map(c => c.field);

        const payload = {};
        editableFields.forEach(f => { payload[f] = data[f] ?? null; });

        // For new rows, include the parent FK with its explicit field name.
        // parentField replaces the old string-guessing heuristic that produced
        // task_id instead of project_id for the Tasks entity.
        if (isNew && parentField && queryParams) {
            payload[parentField] = queryParams;
        }

        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            alert(err.detail || 'Save failed');
            return false;
        }

        const saved = await resp.json();
        row.update(saved);
        return true;
    }

    // -------------------------------------------------------------------------
    // Delete a row from the server
    // NOTE: Same URL gap as saveRow above.
    // -------------------------------------------------------------------------
    async function deleteRow(row) {
        const id = row.getData().id;
        if (!id) { row.delete(); return; }

        if (!confirm('Delete this row?')) return;

        const resp = await fetch(`/api/${entity}/${id}`, { method: 'DELETE' });
        if (resp.ok) {
            row.delete();
        } else {
            alert('Delete failed');
        }
    }

    // -------------------------------------------------------------------------
    // Tabulator init — uses global Tabulator loaded by base.html via CDN
    // -------------------------------------------------------------------------
    const table = new Tabulator(container, {  // eslint-disable-line no-undef
        height: '100%',
        layout: 'fitColumns',
        ajaxURL: ajaxUrl,
        ajaxConfig: { headers: { 'Accept': 'application/json' } },
        ajaxResponse: (url, params, response) => response.records || [],
        editTriggerEvent: 'dblclick',
        columns: columns,

        cellEdited: async function(cell) {
            await saveRow(cell.getRow());
        },

        rowContextMenu: [
            {
                label: 'Delete row',
                action: (e, row) => deleteRow(row),
            }
        ],

        dataLoadError: (error) => {
            console.error(`Failed to load ${entity}/${queryName}:`, error);
        },
    });

    // Escape — delete empty new row, or cancel edit
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const newRow = table.getRows().find(r => !r.getData().id);
            if (newRow) newRow.delete();
        }
    });

    // Store reference on window for parent access (e.g. refresh after save)
    window[`tabulator_${containerId}`] = table;
    window[`refresh_${containerId}`]   = () => table.setData(ajaxUrl);
}
```

---

## `_datasheet.html`

### BEFORE

```jinja
{#
  _datasheet.html
  
  Reusable Tabulator datasheet grid.
  
  This partial renders just the Tabulator instance. It is always used as
  a child of _datasheet_with_header.html (which provides the + button,
  search, and controls).
  
  Parameters:
    - container_id (str): DOM id for Tabulator to mount to (required)
    - entity (str): QueryLoader entity name (e.g., "tasks", "contact_emails")
    - query_name (str): QueryLoader query name (e.g., "for_project")
    - query_params (str): Comma-separated bind parameters (e.g., "123")
    - columns (list): Column definitions for Tabulator
    - save_url (str): POST endpoint for saving row edits
    - add_url (str, optional): POST endpoint for adding new rows
  
  Example usage (from _datasheet_with_header.html):
    
    {% include '_datasheet.html' with
        container_id='tasks-datasheet',
        entity='tasks',
        query_name='for_project',
        query_params=record.id,
        columns=[
          { "title": "Name", "field": "name", "width": 200, "editor": "input" },
          { "title": "Status", "field": "status_id", "width": 100 }
        ],
        save_url='/crew/tasks/save'
    %}
#}

<div id="{{ container_id }}" style="height: 100%;"></div>

<script>
window.addEventListener('load', function () {

  const container = document.getElementById('{{ container_id }}');
  const entity = '{{ entity }}';
  const queryName = '{{ query_name }}';
  const queryParams = '{{ query_params }}';
  const ajaxUrl = `/api/query/${entity}/${queryName}?params=${queryParams}`;

  const columns = {{ columns | tojson }};

  // -------------------------------------------------------------------------
  // Save a row to the server via generic entity endpoint
  // -------------------------------------------------------------------------
  async function saveRow(row) {
    const data = row.getData();
    const isNew = !data.id;

    // Don't save a new row with no content — just delete it
    const firstEditable = columns.find(c => c.editor);
    if (isNew && firstEditable && !data[firstEditable.field]) {
      row.delete();
      return true;
    }

    const url = isNew
      ? `/api/${entity}/save`
      : `/api/${entity}/${data.id}/save`;

    // Only send editable columns
    const editableFields = columns
      .filter(c => c.editor && c.field !== 'id')
      .map(c => c.field);

    const payload = {};
    editableFields.forEach(f => { payload[f] = data[f] ?? null; });

    // For new rows, also include the parent foreign key if present
    // (e.g. contact_id, project_id — passed in via query_params)
    {% if query_params %}
    if (isNew) {
      const paramKey = '{{ entity }}'.replace(/s$/, '_id').replace('contact_email', 'contact').replace('contact_phone', 'contact');
      if (paramKey && !payload[paramKey]) {
        payload[paramKey] = {{ query_params }};
      }
    }
    {% endif %}

    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      alert(err.detail || 'Save failed');
      return false;
    }

    const saved = await resp.json();
    row.update(saved);
    return true;
  }

  // -------------------------------------------------------------------------
  // Delete a row from the server
  // -------------------------------------------------------------------------
  async function deleteRow(row) {
    const id = row.getData().id;
    if (!id) { row.delete(); return; }

    if (!confirm('Delete this row?')) return;

    const resp = await fetch(`/api/${entity}/${id}`, { method: 'DELETE' });
    if (resp.ok) {
      row.delete();
    } else {
      alert('Delete failed');
    }
  }

  // -------------------------------------------------------------------------
  // Tabulator init — uses global Tabulator loaded by base.html via CDN
  // -------------------------------------------------------------------------
  const table = new Tabulator(container, {
    height: '100%',
    layout: 'fitColumns',
    ajaxURL: ajaxUrl,
    ajaxConfig: { headers: { 'Accept': 'application/json' } },
    ajaxResponse: (url, params, response) => response.records || [],
    editTriggerEvent: 'dblclick',
    columns: columns,

    // Auto-save when a cell edit is confirmed (Enter or click away)
    cellEdited: async function(cell) {
      await saveRow(cell.getRow());
    },

    rowContextMenu: [
      {
        label: 'Delete row',
        action: (e, row) => deleteRow(row),
      }
    ],

    dataLoadError: (error) => {
      console.error(`Failed to load ${entity}/${queryName}:`, error);
    },
  });

  // Esc — delete empty new row, or cancel
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      // Find any unsaved new row and remove it
      const newRow = table.getRows().find(r => !r.getData().id);
      if (newRow) {
        newRow.delete();
      }
    }
  });

  // Store reference on window for parent access (e.g. refresh after external save)
  window[`tabulator_${container.id}`] = table;
  window[`refresh_${container.id}`] = () => table.setData(ajaxUrl);

});
</script>
```

### AFTER

```jinja
{#
  _datasheet.html

  Reusable Tabulator child-datasheet grid.

  Always used as a child of _datasheet_with_header.html (which provides
  the + Add button, search, and controls). Renders a mount point div and
  a small module script that imports initDatasheet() from datasheet.js —
  same pattern as _tab_identities.html → bidirectional-filter.js.

  The full Tabulator init, save, delete, and Escape-key logic lives in
  datasheet.js, not here. This file's only job is passing Jinja-rendered
  config values (which only exist at template-render time) into a call
  to that module.

  Parameters:
    - container_id  (str)  — DOM id for Tabulator to mount to (required)
    - entity        (str)  — QueryLoader entity name (e.g. "tasks")
    - query_name    (str)  — QueryLoader query name (e.g. "for_project")
    - query_params  (str)  — Comma-separated bind parameters (e.g. "123")
    - columns       (list) — Tabulator column definitions
    - parent_field  (str)  — Explicit FK column name for new-row inserts
                             (e.g. "project_id" for tasks, "contact_id"
                             for contact_emails). Never guessed from entity
                             name. Pass '' if this datasheet has no parent.
#}

<div id="{{ container_id }}" style="height: 100%;"></div>

<script type="module">
import { initDatasheet } from '/static/js/datasheet.js';

initDatasheet({
    containerId:  '{{ container_id }}',
    entity:       '{{ entity }}',
    queryName:    '{{ query_name }}',
    queryParams:  '{{ query_params }}',
    columns:      {{ columns | tojson }},
    parentField:  '{{ parent_field | default("") }}',
});
</script>
```

**Why:** The entire `<script>` block (save/delete logic, Tabulator init,
Escape handler, window references — ~80 lines) is now in one shared
`datasheet.js` that every child datasheet imports, instead of being
re-emitted verbatim into the page's HTML once per included datasheet.
`save_url`/`add_url` are removed — `save_url` was documented but never
actually used in the script (the URL was always hardcoded from `entity`),
and `add_url` belongs to `_datasheet_with_header.html`'s + Add button,
not the grid itself.

---

## `_datasheet_with_header.html`

### BEFORE

```jinja
{#
  _datasheet_with_header.html
  
  Reusable datasheet component with header controls.
  
  Includes:
    - Header bar with [+ Add] button, search input, clear button
    - Calls _datasheet.html for the actual grid
  
  This is the standard way to use Tabulator in Curator. Always use this
  instead of _datasheet.html directly.
  
  Parameters (passed via {% with %} block):
    - add_button_label (str): Label for the + button (e.g., "+ Task")
    - add_url (str, optional): POST endpoint for adding new rows
    - container_id (str): DOM id for Tabulator to mount to (required)
    - entity (str): QueryLoader entity name (e.g., "tasks")
    - query_name (str): QueryLoader query name (e.g., "for_project")
    - query_params (str): Comma-separated bind parameters
    - columns (list): Column definitions for Tabulator
    - save_url (str): POST endpoint for saving row edits
#}

<div class="datasheet-container">
  
  <!-- Header with controls -->
  <div class="datasheet-header">
    {% if add_url %}
      <button class="datasheet-add-button" data-add-url="{{ add_url }}">
        {{ add_button_label }}
      </button>
    {% endif %}
    <input
      type="text"
      class="datasheet-search"
      placeholder="Search..."
      aria-label="Search datasheet"
    />
    <button class="datasheet-clear-button" aria-label="Clear search">
      ×
    </button>
  </div>

  <!-- Tabulator grid -->
  <div class="datasheet-body">
    {% with
        container_id=container_id,
        entity=entity,
        query_name=query_name,
        query_params=query_params,
        columns=columns,
        save_url=save_url
    %}
        {% include 'partials/_datasheet.html' %}
    {% endwith %}
  </div>

</div>

<script type="module">
  {# Search and clear button handlers (deferred — implement with full detail panel JS) #}
</script>

<style>
  .datasheet-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    gap: 0;
  }

  .datasheet-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface);
    flex-shrink: 0;
  }

  .datasheet-add-button {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-button-primary-text);
    background: var(--color-button-primary-bg);
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .datasheet-add-button:hover {
    opacity: 0.9;
  }

  .datasheet-search {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid var(--color-border);
    border-radius: 0.25rem;
    background: var(--color-input-bg);
    color: var(--color-input-text);
    font-size: 0.875rem;
  }

  .datasheet-search::placeholder {
    color: var(--color-text-light);
  }

  .datasheet-clear-button {
    padding: 0.25rem 0.5rem;
    font-size: 1.25rem;
    line-height: 1;
    color: var(--color-text-light);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: color 0.2s ease;
  }

  .datasheet-clear-button:hover {
    color: var(--color-text);
  }

  .datasheet-body {
    flex: 1;
    overflow: hidden;
    min-height: 0;  /* Important: allows flex child to shrink below content size */
  }
</style>
```

### AFTER

```jinja
{#
  _datasheet_with_header.html

  Reusable datasheet component with header controls.

  Includes:
    - Header bar with [+ Add] button, search input, clear button
    - Calls _datasheet.html for the actual Tabulator grid

  This is the standard way to use Tabulator child datasheets in Curator.
  Always use this instead of _datasheet.html directly.

  Parameters (passed via {% with %} block):
    - add_button_label (str)  — Label for the + button (e.g. "+ Task")
    - add_url          (str, optional) — URL for the + Add button; if
                         absent the button is not rendered. Wiring the
                         button's click handler is deferred — see
                         CHANGEDOC_DATASHEET_JS_EXTRACTION.md.
    - container_id     (str)  — DOM id for Tabulator to mount to (required)
    - entity           (str)  — QueryLoader entity name (e.g. "tasks")
    - query_name       (str)  — QueryLoader query name (e.g. "for_project")
    - query_params     (str)  — Comma-separated bind parameters
    - columns          (list) — Tabulator column definitions
    - parent_field     (str)  — Explicit FK column name for new-row inserts
                         (e.g. "project_id" for tasks). Never guessed.
                         Pass '' if this datasheet has no parent FK.
#}

<div class="datasheet-container">

  <!-- Header with controls -->
  <div class="datasheet-header">
    {% if add_url %}
      <button class="datasheet-add-button" data-add-url="{{ add_url }}">
        {{ add_button_label }}
      </button>
    {% endif %}
    <input
      type="text"
      class="datasheet-search"
      placeholder="Search..."
      aria-label="Search datasheet"
    />
    <button class="datasheet-clear-button" aria-label="Clear search">
      ×
    </button>
  </div>

  <!-- Tabulator grid -->
  <div class="datasheet-body">
    {% with
        container_id=container_id,
        entity=entity,
        query_name=query_name,
        query_params=query_params,
        columns=columns,
        parent_field=parent_field|default('')
    %}
        {% include 'partials/_datasheet.html' %}
    {% endwith %}
  </div>

</div>

<style>
  .datasheet-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    gap: 0;
  }

  .datasheet-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface);
    flex-shrink: 0;
  }

  .datasheet-add-button {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-button-primary-text);
    background: var(--color-button-primary-bg);
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .datasheet-add-button:hover {
    opacity: 0.9;
  }

  .datasheet-search {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid var(--color-border);
    border-radius: 0.25rem;
    background: var(--color-input-bg);
    color: var(--color-input-text);
    font-size: 0.875rem;
  }

  .datasheet-search::placeholder {
    color: var(--color-text-light);
  }

  .datasheet-clear-button {
    padding: 0.25rem 0.5rem;
    font-size: 1.25rem;
    line-height: 1;
    color: var(--color-text-light);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: color 0.2s ease;
  }

  .datasheet-clear-button:hover {
    color: var(--color-text);
  }

  .datasheet-body {
    flex: 1;
    overflow: hidden;
    min-height: 0;  /* Important: allows flex child to shrink below content size */
  }
</style>
```

**Why:** `save_url` removed from the `{% with %}` passthrough — it was
documented as a parameter and passed through to `_datasheet.html`, but
`_datasheet.html`'s script never actually used it (the URL was always
hardcoded from `entity`). Removing it cleans up the misleading API.
`parent_field` added to passthrough, with `|default('')` so existing callers
that don't supply it don't error. The empty `<script type="module">` block
(search/clear handlers, explicitly "deferred") removed entirely — an empty
script tag is worse than nothing, since it implies something is wired when
it isn't.

---

## `base.html`

No change. `datasheet.js` is an ES module imported on demand by
`_datasheet.html`'s `<script type="module">` — the browser fetches it
only when a panel tab containing a child datasheet is actually rendered.
It doesn't need a `<script src>` tag in `base.html` the way
`detail-panel.js` does (which is loaded on every page because any page
may open a detail panel).

---

## Verify after applying

1. Restart uvicorn, hard-refresh the browser.
2. Open a project's detail panel — the Tasks tab should show "Tasks —
   coming soon" placeholder (no JS errors in the console from the new
   import, since the tab panel exists in the DOM even if empty).
3. Open DevTools → Network → filter by `datasheet.js` — confirm it's
   NOT fetched on initial page load (lazy import, only fetched when a
   tab including `_datasheet.html` is actually rendered).
4. `pylint src/` — no Python changes, should still be 10.00/10.
5. `pytest` — no changes affecting test coverage.

**Note:** Because the save/delete URL bug is deferred, you cannot yet
verify that row edits actually save — they'll 404. That's expected and
documented. The extraction itself (module loads, Tabulator inits, no
console errors) is what this changedoc verifies.
