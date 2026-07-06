# Changedoc: `/panel/{entity}/{id}` route + `_detail_panel.html`/`detail-panel.js` fetch-and-swap

**Date:** 2026-07-04
**Reason:** Completes fetch-and-swap. Builds the route that serves
`_detail_form_fields.html` (previous changedoc), wires it into `app.py`,
and changes `_detail_panel.html`/`detail-panel.js` to actually use it —
replacing the old approach (one static per-entity form baked into the
page at load, JS populating a hardcoded list of field names) with a real
fetch-and-swap on every panel open.

**Source verified:** `crew.py` viewed directly — confirms raw
`jinja2.Environment(loader=FileSystemLoader(TEMPLATES_DIR))`, not
FastAPI's `Jinja2Templates`. The new route mirrors that exact pattern
rather than introducing a second templating convention into the
codebase.

---

## 1. `src/curator/web/routes/panel.py` (new file)

```python
"""Detail panel field-fragment routes.

Serves a single entity's field-input fragment, rendered via fieldkit,
for detail-panel.js to fetch-and-swap into the form container on every
panel open (new record or existing). Replaces the old approach of one
static per-entity form baked into _detail_panel.html at page load.

Mirrors crew.py's raw jinja2.Environment setup rather than introducing
FastAPI's Jinja2Templates as a second templating convention.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db
from curator.web.routes.contacts import _fetch_contact_for_display
from curator.web.routes.organizations import _fetch_organization_for_display
from curator.web.routes.projects import _fetch_project_for_display

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

router = APIRouter()

# Entity name -> its _fetch_*_for_display function. Small, fixed set of
# wiring decisions, same reasoning as app.py's _FIELDKIT_VIEWS: adding
# an entity means adding routes/templates alongside it regardless, so
# there's no scenario where this changes without a code change too.
_FETCH_FUNCTIONS = {
    "projects": _fetch_project_for_display,
    "contacts": _fetch_contact_for_display,
    "organizations": _fetch_organization_for_display,
}


def _render_fields(request: Request, entity: str, record: dict) -> HTMLResponse:
    """Render the field-fragment template for one entity + record.

    Args:
        request: Current request — used to reach app.state.fieldkit,
                 the FieldKit cache built once at FastAPI startup.
        entity:  One of "projects", "contacts", "organizations".
        record:  Field values dict, or {} for a new record.

    Returns:
        HTMLResponse — the rendered fragment, ready to be swapped into
        #detail-form-fields by detail-panel.js.
    """
    kit = request.app.state.fieldkit[entity]
    template = env.get_template("partials/_detail_form_fields.html")
    return HTMLResponse(
        template.render(fields=kit.fields, record=record, options=kit.options)
    )


# /panel/{entity}/new must be declared before /panel/{entity}/{record_id}
# — same route-ordering rule as the save routes (literal before
# parameterized), otherwise FastAPI tries to parse "new" as an int and
# 422s instead of matching this route.

@router.get("/panel/{entity}/new")
async def panel_new(entity: str, request: Request):
    """Render the field fragment for a new, empty record."""
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")
    return _render_fields(request, entity, {})


@router.get("/panel/{entity}/{record_id}")
async def panel_existing(
    entity: str,
    record_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Render the field fragment for an existing record."""
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")

    fetch_fn = _FETCH_FUNCTIONS[entity]
    record = await fetch_fn(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"{entity.title()} not found")

    return _render_fields(request, entity, record)
```

---

## 2. `src/curator/web/app.py` (edit — complete file)

### BEFORE

```python
"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dbkit.connection import AsyncDBConnection
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from curator.web.fieldkit import FieldKit
from curator.web.middleware import SessionMiddleware
from curator.web.routes import auth, landing, crew, projects, contacts, organizations

# ---------------------------------------------------------------------------
# Fieldkit cache — entity name -> schema-qualified view name.
#
# Explicit here rather than in curator.yaml: this is a small, fixed set
# of wiring decisions (which view backs which entity's form), similar in
# spirit to the router registrations below, not user-facing deployment
# config. Adding an entity means adding routes/templates alongside it
# regardless, so there's no scenario where this list changes without a
# code change happening at the same time.
# ---------------------------------------------------------------------------

_FIELDKIT_VIEWS = {
    "projects": "projects.v_project_detail",
    "contacts": "identity.v_contact_detail",
    "organizations": "identity.v_organization_detail",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Build the fieldkit cache once at startup, before serving any request.

    Opens its own connection — this runs outside any request context, so
    the per-request get_db dependency isn't available here.

    Deliberately does NOT catch FieldSchemaError. A misconfigured view or
    a *_id/integer column with no override entry must crash uvicorn
    immediately, not surface later as a broken form in front of Felipe.
    See fieldkit.py and curator/exceptions.py's FieldSchemaError
    docstring for the full reasoning.
    """
    async with AsyncDBConnection() as db:
        _app.state.fieldkit = {
            entity: await FieldKit.create(db, view_name)
            for entity, view_name in _FIELDKIT_VIEWS.items()
        }
    yield
    # No teardown — app.state.fieldkit holds FieldDef data only, no open
    # resources to release.


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# Must be added before routers are registered.
# SessionMiddleware validates curator_session cookie on every request.
# ---------------------------------------------------------------------------

app.add_middleware(SessionMiddleware)

# ---------------------------------------------------------------------------
# Static files — resolved relative to this file: src/curator/web/ -> static/
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parents[3] / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Routers
# Auth must be registered first — /auth/login is the public entry point.
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)
app.include_router(projects.router)
app.include_router(contacts.router)
app.include_router(organizations.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

### AFTER (complete file — replace the whole thing with this)

```python
"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dbkit.connection import AsyncDBConnection
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from curator.web.fieldkit import FieldKit
from curator.web.middleware import SessionMiddleware
from curator.web.routes import auth, landing, crew, panel, projects, contacts, organizations

# ---------------------------------------------------------------------------
# Fieldkit cache — entity name -> schema-qualified view name.
#
# Explicit here rather than in curator.yaml: this is a small, fixed set
# of wiring decisions (which view backs which entity's form), similar in
# spirit to the router registrations below, not user-facing deployment
# config. Adding an entity means adding routes/templates alongside it
# regardless, so there's no scenario where this list changes without a
# code change happening at the same time.
# ---------------------------------------------------------------------------

_FIELDKIT_VIEWS = {
    "projects": "projects.v_project_detail",
    "contacts": "identity.v_contact_detail",
    "organizations": "identity.v_organization_detail",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Build the fieldkit cache once at startup, before serving any request.

    Opens its own connection — this runs outside any request context, so
    the per-request get_db dependency isn't available here.

    Deliberately does NOT catch FieldSchemaError. A misconfigured view or
    a *_id/integer column with no override entry must crash uvicorn
    immediately, not surface later as a broken form in front of Felipe.
    See fieldkit.py and curator/exceptions.py's FieldSchemaError
    docstring for the full reasoning.
    """
    async with AsyncDBConnection() as db:
        _app.state.fieldkit = {
            entity: await FieldKit.create(db, view_name)
            for entity, view_name in _FIELDKIT_VIEWS.items()
        }
    yield
    # No teardown — app.state.fieldkit holds FieldDef data only, no open
    # resources to release.


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# Must be added before routers are registered.
# SessionMiddleware validates curator_session cookie on every request.
# ---------------------------------------------------------------------------

app.add_middleware(SessionMiddleware)

# ---------------------------------------------------------------------------
# Static files — resolved relative to this file: src/curator/web/ -> static/
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parents[3] / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Routers
# Auth must be registered first — /auth/login is the public entry point.
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)
app.include_router(panel.router)
app.include_router(projects.router)
app.include_router(contacts.router)
app.include_router(organizations.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

**Only two changes:** `panel` added to the route-module import line, and
`app.include_router(panel.router)` added alongside the others.

---

## 3. `src/curator/templates/partials/_detail_panel.html` (edit — complete file)

**What's removed:** the entire hardcoded `{% if entity == "projects" %}...
{% elif %}...{% endif %}` block of form fields inside `<form
id="detail-form">`. **What's added:** an empty `<div
id="detail-form-fields">` — populated by `detail-panel.js` fetching
`/panel/{entity}/{id}` on every open. The panel is never visible at
initial page load (it's hidden behind the hero image until an open
action fires), so there's nothing lost by leaving this empty at render
time — the old per-entity blocks were already invisible until then too.

**Not touched:** the tab-button/tab-panel structure for child datasheets
(Tasks, Emails, Phones, etc.) — those are a separate, already-deferred
concern ("coming soon" placeholders), unrelated to the details-tab
field-rendering this changedoc addresses.

### BEFORE

```html
{#
  _detail_panel.html

  Detail panel — displays a record's details in a tabbed interface.
  Replaces the hero image when a user clicks ⋯ on a datasheet row.

  Parameters:
    - entity          (str)  — "projects", "contacts", or "organizations"
    - record_id       (int)  — ID of the record being displayed
    - record          (dict) — Full record data for form fields
    - project_types   (list, optional) — Type lookup for projects
    - project_statuses(list, optional) — Status lookup for projects

  Caller must set entity, record_id, and record before including.
  Child datasheets (Tasks, Emails, etc.) are deferred — coming soon.
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

    <!-- ===== DETAILS TAB (always first) ===== -->
    <div class="detail-tab-panel active" data-tab="details">
      <form id="detail-form" class="detail-form" data-entity="{{ entity }}" data-id="{{ record_id }}">

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

      </form>
    </div>

    <!-- ===== CHILD TABS (deferred) ===== -->
    {% if entity == "projects" %}
      <div class="detail-tab-panel" data-tab="tasks">
        <p class="tab-placeholder">Tasks — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="links">
        <p class="tab-placeholder">Links — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="contacts">
        <p class="tab-placeholder">Contacts — coming soon</p>
      </div>

    {% elif entity == "contacts" %}
      <div class="detail-tab-panel" data-tab="emails">
        <p class="tab-placeholder">Emails — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="phones">
        <p class="tab-placeholder">Phones — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="urls">
        <p class="tab-placeholder">URLs — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="organizations">
        <p class="tab-placeholder">Organizations — coming soon</p>
      </div>

    {% elif entity == "organizations" %}
      <div class="detail-tab-panel" data-tab="contacts">
        <p class="tab-placeholder">Contacts — coming soon</p>
      </div>
    {% endif %}

  </div>

  <!-- Action buttons: sticky footer — actions and container_class from route -->
  {% include 'partials/_form_actions.html' %}

</div>
```

### AFTER (complete file — replace the whole thing with this)

```html
{#
  _detail_panel.html

  Detail panel — displays a record's details in a tabbed interface.
  Replaces the hero image when a user clicks ⋯ on a datasheet row.

  Parameters:
    - entity    (str) — "projects", "contacts", or "organizations"
    - record_id (int) — ID of the record being displayed (blank/'' for
                        a new-record panel not yet opened)

  The details tab's field inputs are NOT rendered here anymore — see
  detail-form-fields below. detail-panel.js fetches them from
  /panel/{entity}/{id} (or /panel/{entity}/new) on every panel open,
  fetch-and-swap style, so this template only needs entity/record_id to
  set data attributes for JS to read. The panel is hidden behind the
  hero image until an open action fires, so there's nothing visible to
  lose by leaving detail-form-fields empty at initial page render.

  Child datasheets (Tasks, Emails, etc.) are deferred — coming soon —
  and unrelated to this fetch-and-swap change.
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

    <!-- ===== DETAILS TAB (always first) ===== -->
    <div class="detail-tab-panel active" data-tab="details">
      <form id="detail-form" class="detail-form" data-entity="{{ entity }}" data-id="{{ record_id }}">
        <div id="detail-form-fields">
          <!-- Populated by detail-panel.js fetching
               /panel/{entity}/{id} or /panel/{entity}/new on open. -->
        </div>
      </form>
    </div>

    <!-- ===== CHILD TABS (deferred) ===== -->
    {% if entity == "projects" %}
      <div class="detail-tab-panel" data-tab="tasks">
        <p class="tab-placeholder">Tasks — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="links">
        <p class="tab-placeholder">Links — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="contacts">
        <p class="tab-placeholder">Contacts — coming soon</p>
      </div>

    {% elif entity == "contacts" %}
      <div class="detail-tab-panel" data-tab="emails">
        <p class="tab-placeholder">Emails — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="phones">
        <p class="tab-placeholder">Phones — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="urls">
        <p class="tab-placeholder">URLs — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="organizations">
        <p class="tab-placeholder">Organizations — coming soon</p>
      </div>

    {% elif entity == "organizations" %}
      <div class="detail-tab-panel" data-tab="contacts">
        <p class="tab-placeholder">Contacts — coming soon</p>
      </div>
    {% endif %}

  </div>

  <!-- Action buttons: sticky footer — actions and container_class from route -->
  {% include 'partials/_form_actions.html' %}

</div>
```

---

## 4. `src/curator/static/js/detail-panel.js` (edit — complete file)

**What's removed:** `populateForm()` entirely — it was the hardcoded
field-name list (`type_id`/`status_id`/`description`/`title`) this whole
piece of work exists to eliminate. **What's added:** `getFieldsContainer()`
and `fetchAndSwapFields()`, and `openDetailPanel`/`openNewRecordPanel`
now fetch-and-swap instead of fetching JSON and manually populating.

**Not changed, verified still correct as-is:** `clearForm()` (already
generic — selects by tag name, not hardcoded field names, so it works
against whatever fields the fragment just rendered) and `focusName()`
(still finds `#detail-name`, which the new template still produces for
any entity's `name` field, since `id="detail-{{ field.name }}"` for a
column literally named `name` is `detail-name`).

### BEFORE

```javascript
/**
 * detail-panel.js
 *
 * Handles detail panel interactions:
 * - Opening detail panel for existing records (⋯ button)
 * - Opening detail panel for new records (+ Add button)
 * - Closing panel on × / Alt+X / Escape
 * - Tab switching
 * - Save (Alt+S) — save and close
 * - New  (Alt+N) — save current, clear form, focus Name
 * - Discard (Alt+X) — discard and close
 *
 * Hero image and detail panel occupy the same spot. Opening the panel
 * hides the hero (display:none) and shows the panel (display:flex).
 */

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function getPanel() {
  return document.querySelector('#detail-panel-container .detail-panel');
}

function getForm() {
  return document.getElementById('detail-form');
}

function getHero() {
  return document.querySelector('.crew-header');
}

function showPanel() {
  const panel = getPanel();
  const hero  = getHero();
  if (panel) panel.classList.add('active');
  if (hero)  hero.classList.add('hidden');
}

function hidePanel() {
  const panel = getPanel();
  const hero  = getHero();
  if (panel) panel.classList.remove('active');
  if (hero)  hero.classList.remove('hidden');
}

function resetToDetailsTab() {
  const panel = getPanel();
  if (!panel) return;
  panel.querySelectorAll('.detail-tab-button').forEach(b => b.classList.remove('active'));
  panel.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
  const firstBtn   = panel.querySelector('.detail-tab-button');
  const detailsTab = panel.querySelector('.detail-tab-panel[data-tab="details"]');
  if (firstBtn)   firstBtn.classList.add('active');
  if (detailsTab) detailsTab.classList.add('active');
}

function clearForm() {
  const form = getForm();
  if (!form) return;
  form.dataset.id = '';
  form.querySelectorAll('input, textarea').forEach(el => el.value = '');
  form.querySelectorAll('select').forEach(el => el.selectedIndex = 0);
}

function focusName() {
  const nameField = document.getElementById('detail-name');
  if (nameField) {
    nameField.focus();
    nameField.select();
  }
}

function populateForm(record) {
  const form = getForm();
  if (!form) return;
  form.dataset.id = record.id ?? '';

  const nameField   = form.querySelector('[name="name"]');
  const typeField   = form.querySelector('[name="type_id"]');
  const statusField = form.querySelector('[name="status_id"]');
  const descField   = form.querySelector('[name="description"]');
  const titleField  = form.querySelector('[name="title"]');

  if (nameField)   nameField.value   = record.name        ?? '';
  if (typeField)   typeField.value   = record.type_id     ?? '';
  if (statusField) statusField.value = record.status_id   ?? '';
  if (descField)   descField.value   = record.description ?? '';
  if (titleField)  titleField.value  = record.title       ?? '';
}

// ---------------------------------------------------------------------------
// Save to server
// Returns the saved record on success, null on failure.
// ---------------------------------------------------------------------------

// Guard against double-saves from rapid clicks or accesskey + click firing together
let _saving = false;

async function saveForm() {
  const form = getForm();
  if (!form) return null;

  const entity   = form.dataset.entity;
  const recordId = form.dataset.id;
  const isNew    = !recordId;

  const formData = new FormData(form);
  const data     = Object.fromEntries(formData);

  const url = isNew
    ? `/crew/${entity}/save`
    : `/crew/${entity}/${recordId}/save`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (res.ok) {
      const saved = await res.json();
      // Update form id to the newly saved record's id
      form.dataset.id = saved.id;
      const panel = getPanel();
      if (panel) panel.dataset.id = saved.id;
      return saved;
    } else {
      // crew.py returns {"success": false, "message": "..."} on proc
      // rejection (duplicate name, not found, etc.) — read message, not
      // detail, or this always falls back to the generic string below.
      const err = await res.json().catch(() => ({ message: res.statusText }));
      alert(err.message || 'Save failed');
      return null;
    }
  } catch (err) {
    console.error('Save error:', err);
    alert('Save error: ' + err.message);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Button handlers
// ---------------------------------------------------------------------------

async function handleSave() {
  if (_saving) return;
  _saving = true;
  try {
    const saved = await saveForm();
    if (saved) {
      if (window._refreshProjectsGrid) window._refreshProjectsGrid();
      hidePanel();
    }
  } finally {
    _saving = false;
  }
}

async function handleNew() {
  if (_saving) return;
  _saving = true;
  try {
    const saved = await saveForm();
    if (!saved) return;
    clearForm();
    resetToDetailsTab();
    focusName();
    if (window._refreshProjectsGrid) window._refreshProjectsGrid();
  } finally {
    _saving = false;
  }
}

function handleDiscard() {
  hidePanel();
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Open detail panel for an existing record.
 * Fetches record from server and populates the form.
 */
export async function openDetailPanel(entity, recordId) {
  let record;
  try {
    const res = await fetch(`/crew/${entity}/${recordId}`);
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    record = await res.json();
  } catch (err) {
    console.error('Could not fetch record:', err);
    return;
  }

  const panel = getPanel();
  const form  = getForm();
  if (!panel || !form) return;

  panel.dataset.entity = entity;
  panel.dataset.id     = recordId;
  form.dataset.entity  = entity;

  populateForm(record);
  resetToDetailsTab();
  showPanel();
}

/**
 * Open detail panel in new-record mode.
 * Form is empty, save will POST to /crew/{entity}/save.
 */
export function openNewRecordPanel(entity) {
  const panel = getPanel();
  const form  = getForm();
  if (!panel || !form) return;

  panel.dataset.entity = entity;
  panel.dataset.id     = '';
  form.dataset.entity  = entity;

  clearForm();
  resetToDetailsTab();
  showPanel();
  focusName();
}

/**
 * Close the detail panel and restore the hero image.
 */
export function closeDetailPanel() {
  hidePanel();
}

// ---------------------------------------------------------------------------
// Init — wire up all event listeners
// ---------------------------------------------------------------------------

export function initDetailPanel() {
  // Tab switching
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('detail-tab-button')) {
      const panel = e.target.closest('.detail-panel');
      if (!panel) return;
      const targetTab = e.target.dataset.tab;
      panel.querySelectorAll('.detail-tab-button').forEach(b => b.classList.remove('active'));
      panel.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
      e.target.classList.add('active');
      const tabPanel = panel.querySelector(`.detail-tab-panel[data-tab="${targetTab}"]`);
      if (tabPanel) tabPanel.classList.add('active');
    }

    if (e.target.classList.contains('detail-close-button')) handleDiscard();

    // btn-save is type="submit" with form="detail-form" (see forms.yaml) so
    // clicking it also triggers native form submission. Without preventDefault
    // here, the browser's native GET-to-current-URL submission races the
    // fetch() in handleSave() and wins, since nothing else stops it.
    if (e.target.classList.contains('btn-save')) {
      e.preventDefault();
      handleSave();
    }
    if (e.target.classList.contains('btn-new'))             handleNew();
    if (e.target.classList.contains('btn-discard'))         handleDiscard();
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const panel = getPanel();
    if (!panel?.classList.contains('active')) return;

    // Alt+S — Save and close
    if (e.altKey && e.key === 's') { e.preventDefault(); handleSave(); }
    // Alt+N — Save and new
    if (e.altKey && e.key === 'n') { e.preventDefault(); handleNew(); }
    // Alt+X or Escape — Discard and close
    if ((e.altKey && e.key === 'x') || e.key === 'Escape') { e.preventDefault(); handleDiscard(); }
  });

  // Safety net: catch any native form submission (e.g. pressing Enter in a
  // text input, which submits the nearest form by default browser behavior)
  // that isn't already intercepted by the btn-save click handler above.
  // Without this, Enter-to-submit falls back to a GET on the current URL
  // with form fields as query params, identical to the btn-save race bug.
  document.addEventListener('submit', (e) => {
    if (e.target.id === 'detail-form') {
      e.preventDefault();
      handleSave();
    }
  });
}

// ---------------------------------------------------------------------------
// Expose for non-module scripts (e.g. _projects_table.html)
// ---------------------------------------------------------------------------
window.openDetailPanel    = openDetailPanel;
window.openNewRecordPanel = openNewRecordPanel;
window.closeDetailPanel   = closeDetailPanel;

// Initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDetailPanel);
} else {
  initDetailPanel();
}
```

### AFTER (complete file — replace the whole thing with this)

```javascript
/**
 * detail-panel.js
 *
 * Handles detail panel interactions:
 * - Opening detail panel for existing records (⋯ button)
 * - Opening detail panel for new records (+ Add button)
 * - Closing panel on × / Alt+X / Escape
 * - Tab switching
 * - Save (Alt+S) — save and close
 * - New  (Alt+N) — save current, clear form, focus Name
 * - Discard (Alt+X) — discard and close
 *
 * Hero image and detail panel occupy the same spot. Opening the panel
 * hides the hero (display:none) and shows the panel (display:flex).
 *
 * Field rendering is fetch-and-swap: opening a record fetches a
 * server-rendered fragment from /panel/{entity}/{id} (or
 * /panel/{entity}/new) — built by fieldkit from the entity's actual
 * schema — and swaps it into #detail-form-fields. There is no
 * client-side knowledge of what fields any entity has; adding a new
 * entity (or a new field to an existing one) requires no JS change.
 */

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function getPanel() {
  return document.querySelector('#detail-panel-container .detail-panel');
}

function getForm() {
  return document.getElementById('detail-form');
}

function getFieldsContainer() {
  return document.getElementById('detail-form-fields');
}

function getHero() {
  return document.querySelector('.crew-header');
}

function showPanel() {
  const panel = getPanel();
  const hero  = getHero();
  if (panel) panel.classList.add('active');
  if (hero)  hero.classList.add('hidden');
}

function hidePanel() {
  const panel = getPanel();
  const hero  = getHero();
  if (panel) panel.classList.remove('active');
  if (hero)  hero.classList.remove('hidden');
}

function resetToDetailsTab() {
  const panel = getPanel();
  if (!panel) return;
  panel.querySelectorAll('.detail-tab-button').forEach(b => b.classList.remove('active'));
  panel.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
  const firstBtn   = panel.querySelector('.detail-tab-button');
  const detailsTab = panel.querySelector('.detail-tab-panel[data-tab="details"]');
  if (firstBtn)   firstBtn.classList.add('active');
  if (detailsTab) detailsTab.classList.add('active');
}

function clearForm() {
  const form = getForm();
  if (!form) return;
  form.dataset.id = '';
  form.querySelectorAll('input, textarea').forEach(el => el.value = '');
  form.querySelectorAll('select').forEach(el => el.selectedIndex = 0);
}

function focusName() {
  const nameField = document.getElementById('detail-name');
  if (nameField) {
    nameField.focus();
    nameField.select();
  }
}

/**
 * Fetch the field-fragment HTML for one entity + record (or 'new') and
 * swap it into #detail-form-fields.
 *
 * Returns true on success, false on failure (network error, 404 —
 * caller decides whether to proceed with showing the panel).
 */
async function fetchAndSwapFields(entity, recordIdOrNew) {
  const container = getFieldsContainer();
  if (!container) return false;

  try {
    const res = await fetch(`/panel/${entity}/${recordIdOrNew}`);
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    container.innerHTML = await res.text();
    return true;
  } catch (err) {
    console.error('Could not fetch field fragment:', err);
    return false;
  }
}

// ---------------------------------------------------------------------------
// Save to server
// Returns the saved record on success, null on failure.
// ---------------------------------------------------------------------------

// Guard against double-saves from rapid clicks or accesskey + click firing together
let _saving = false;

async function saveForm() {
  const form = getForm();
  if (!form) return null;

  const entity   = form.dataset.entity;
  const recordId = form.dataset.id;
  const isNew    = !recordId;

  const formData = new FormData(form);
  const data     = Object.fromEntries(formData);

  const url = isNew
    ? `/crew/${entity}/save`
    : `/crew/${entity}/${recordId}/save`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (res.ok) {
      const saved = await res.json();
      // Update form id to the newly saved record's id
      form.dataset.id = saved.id;
      const panel = getPanel();
      if (panel) panel.dataset.id = saved.id;
      return saved;
    } else {
      // crew.py returns {"success": false, "message": "..."} on proc
      // rejection (duplicate name, not found, etc.) — read message, not
      // detail, or this always falls back to the generic string below.
      const err = await res.json().catch(() => ({ message: res.statusText }));
      alert(err.message || 'Save failed');
      return null;
    }
  } catch (err) {
    console.error('Save error:', err);
    alert('Save error: ' + err.message);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Button handlers
// ---------------------------------------------------------------------------

async function handleSave() {
  if (_saving) return;
  _saving = true;
  try {
    const saved = await saveForm();
    if (saved) {
      if (window._refreshProjectsGrid) window._refreshProjectsGrid();
      hidePanel();
    }
  } finally {
    _saving = false;
  }
}

async function handleNew() {
  if (_saving) return;
  _saving = true;
  try {
    const saved = await saveForm();
    if (!saved) return;
    clearForm();
    resetToDetailsTab();
    focusName();
    if (window._refreshProjectsGrid) window._refreshProjectsGrid();
  } finally {
    _saving = false;
  }
}

function handleDiscard() {
  hidePanel();
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Open detail panel for an existing record.
 * Fetches the field fragment from /panel/{entity}/{id} and swaps it in,
 * rather than fetching JSON and manually populating known field names.
 */
export async function openDetailPanel(entity, recordId) {
  const panel = getPanel();
  const form  = getForm();
  if (!panel || !form) return;

  const ok = await fetchAndSwapFields(entity, recordId);
  if (!ok) return;

  panel.dataset.entity = entity;
  panel.dataset.id     = recordId;
  form.dataset.entity  = entity;
  form.dataset.id      = recordId;

  resetToDetailsTab();
  showPanel();
}

/**
 * Open detail panel in new-record mode.
 * Fetches the field fragment from /panel/{entity}/new (empty values)
 * and swaps it in. Save will POST to /crew/{entity}/save.
 */
export async function openNewRecordPanel(entity) {
  const panel = getPanel();
  const form  = getForm();
  if (!panel || !form) return;

  const ok = await fetchAndSwapFields(entity, 'new');
  if (!ok) return;

  panel.dataset.entity = entity;
  panel.dataset.id     = '';
  form.dataset.entity  = entity;
  form.dataset.id      = '';

  resetToDetailsTab();
  showPanel();
  focusName();
}

/**
 * Close the detail panel and restore the hero image.
 */
export function closeDetailPanel() {
  hidePanel();
}

// ---------------------------------------------------------------------------
// Init — wire up all event listeners
// ---------------------------------------------------------------------------

export function initDetailPanel() {
  // Tab switching
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('detail-tab-button')) {
      const panel = e.target.closest('.detail-panel');
      if (!panel) return;
      const targetTab = e.target.dataset.tab;
      panel.querySelectorAll('.detail-tab-button').forEach(b => b.classList.remove('active'));
      panel.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
      e.target.classList.add('active');
      const tabPanel = panel.querySelector(`.detail-tab-panel[data-tab="${targetTab}"]`);
      if (tabPanel) tabPanel.classList.add('active');
    }

    if (e.target.classList.contains('detail-close-button')) handleDiscard();

    // btn-save is type="submit" with form="detail-form" (see forms.yaml) so
    // clicking it also triggers native form submission. Without preventDefault
    // here, the browser's native GET-to-current-URL submission races the
    // fetch() in handleSave() and wins, since nothing else stops it.
    if (e.target.classList.contains('btn-save')) {
      e.preventDefault();
      handleSave();
    }
    if (e.target.classList.contains('btn-new'))             handleNew();
    if (e.target.classList.contains('btn-discard'))         handleDiscard();
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const panel = getPanel();
    if (!panel?.classList.contains('active')) return;

    // Alt+S — Save and close
    if (e.altKey && e.key === 's') { e.preventDefault(); handleSave(); }
    // Alt+N — Save and new
    if (e.altKey && e.key === 'n') { e.preventDefault(); handleNew(); }
    // Alt+X or Escape — Discard and close
    if ((e.altKey && e.key === 'x') || e.key === 'Escape') { e.preventDefault(); handleDiscard(); }
  });

  // Safety net: catch any native form submission (e.g. pressing Enter in a
  // text input, which submits the nearest form by default browser behavior)
  // that isn't already intercepted by the btn-save click handler above.
  // Without this, Enter-to-submit falls back to a GET on the current URL
  // with form fields as query params, identical to the btn-save race bug.
  document.addEventListener('submit', (e) => {
    if (e.target.id === 'detail-form') {
      e.preventDefault();
      handleSave();
    }
  });
}

// ---------------------------------------------------------------------------
// Expose for non-module scripts (e.g. _projects_table.html)
// ---------------------------------------------------------------------------
window.openDetailPanel    = openDetailPanel;
window.openNewRecordPanel = openNewRecordPanel;
window.closeDetailPanel   = closeDetailPanel;

// Initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDetailPanel);
} else {
  initDetailPanel();
}
```

---

## Apply and verify

1. Create `src/curator/web/routes/panel.py` as shown.
2. Replace `app.py` with the AFTER block (adds `panel` import + one
   `include_router` line).
3. Replace `_detail_panel.html` with the AFTER block.
4. Replace `detail-panel.js` with the AFTER block.
5. `pylint src/` — should stay at 10.00/10 (no Python test changes in
   this piece — `panel.py` has no dedicated unit tests yet; flagging
   that as a gap, see below).
6. Restart `uvicorn`.
7. **Manual browser test — this is the real check for this piece:**
   - Open the Captain dashboard, click ⋯ on an existing project. The
     detail panel should open with real fields: Name (text), Type
     (select, populated with real options), Status (select, populated),
     Description (textarea) — all rendered from the fetched fragment,
     not the old hardcoded markup.
   - Click + Add for a new project — same fields, all empty, Name
     focused.
   - Switch to Identities tab, open a contact — should show Name/Title
     fields only (no Type/Status — contacts has no such fields).
   - Open an organization — should show Name only.
   - Edit and Save a record of each type — confirm the save still works
     (this piece didn't touch the save path, but worth confirming
     nothing broke).

---

## Known gap, not addressed in this changedoc

`panel.py` has no unit tests. Every other new route file this session
got test coverage; this one doesn't yet, mainly because testing it
meaningfully requires mocking `request.app.state.fieldkit`, which is a
slightly different shape than the `db`-mocking pattern used everywhere
else. Worth its own small follow-up rather than rushing it into this
already-large changedoc — flagging it rather than skipping it silently.
