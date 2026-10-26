# Changedoc: Detail Panel Content Split (Bug Fix)

**Date:** 2026-07-06 (continued session)
**Depends on:** `_detail_panel.html`, `panel.py`, `_form_actions.html`,
`crew.html` (all as uploaded this session)

**Scope:** Fixes a real bug found while starting the Tasks work — not a
Tasks feature change. No SQL, no new routes.

---

## The bug, precisely

`crew.html` includes `_detail_panel.html` once at initial page load — full
tab bar, form wrapper, close button, everything. That render is correct.

But `detail-panel.js`'s `fetchAndSwapPanel()` replaces `.detail-panel`'s
entire `innerHTML` on every subsequent open (`⋯` on a row, or `+ Add`), using
whatever `panel.py` returns from `/panel/{entity}/{id}` (or `.../new`).
`panel.py` was only ever rendering `_detail_form_fields.html` — the bare
field `<div>`s — not the tab bar, not the `<form>` wrapper, not the close
button. So the first time anyone opens *any* record, the correct tab bar
from initial page load gets wiped out and replaced with three bare
`.form-group` divs and nothing else. Confirmed against two screenshots and
a DOM inspection after a full uvicorn restart and browser cache clear — not
a stale-file or caching issue, a genuine mismatch between what
`detail-panel.js` assumes `panel.py` returns and what it actually returns.

`_detail_panel_content.html` — the file `panel.py` was seemingly written
assuming already existed — was never actually created.

---

## The fix

1. **New `_detail_panel_content.html`** — the actual tab bar + form +
   child-tab-placeholder + action-button markup, extracted from
   `_detail_panel.html`. This is what gets re-rendered on every panel open.
2. **`_detail_panel.html` shrinks to a bare shell** — just the outer
   `<div class="detail-panel">` wrapping one include of
   `_detail_panel_content.html`. Used only by `crew.html`'s initial
   page-load render.
3. **`panel.py` renders `_detail_panel_content.html` instead of
   `_detail_form_fields.html`**, and now loads `actions`/`container_class`
   via `FormActions.from_yaml()` the same way `crew.py` already does, so the
   Save/New/Exit buttons survive the swap too.

One consequence worth calling out: since `panel.py` now renders the whole
content template — fields already included — the old `#detail-form-fields`
placeholder div (previously left empty for a second JS-driven fetch that
never actually happened) is now filled directly via
`{% include "partials/_detail_form_fields.html" %}` in the same render pass.
One fetch, fully rendered — matching what `detail-panel.js`'s own comments
already assumed was happening.

`crew.html`'s initial-page-load include only passes `entity`/`record_id`/
`record`/`project_types`/`project_statuses` — no `fields`/`options`/
`actions`. That's fine (the panel is hidden behind the hero image at that
point and gets fully replaced the first time it's opened), but
`_detail_panel_content.html` defaults all of those to safe empty values so
that initial render doesn't error.

---

## Apply order

No SQL, no pgAdmin steps. Just the three file changes below, then restart
uvicorn and hard-refresh the browser.

---

## `_detail_panel_content.html` (new file)

```jinja
{#
  _detail_panel_content.html

  The actual rendered content of a detail panel for one entity + record:
  tab navigation, the Details tab (fieldkit-driven form), the
  currently-placeholder child tabs, and the action button bar.

  Split out of _detail_panel.html so panel.py's fetch-and-swap route
  (/panel/{entity}/{id}, /panel/{entity}/new) can re-render this exact
  content on every panel open — see panel.py and detail-panel.js's
  fetchAndSwapPanel(), which replaces .detail-panel's entire innerHTML
  with whatever this template produces. Before this file existed,
  panel.py rendered only _detail_form_fields.html (bare field <div>s),
  which silently wiped out the tab bar/form wrapper/close button on
  every open. See CHANGEDOC_DETAIL_PANEL_CONTENT_SPLIT.md for the full
  diagnosis.

  Parameters:
    - entity          (str)  — "projects", "contacts", or "organizations"
    - record_id       (int|str) — blank/'' for a new-record panel
    - record          (dict, optional) — current field values, defaults {}
    - fields          (list[FieldDef], optional) — from FieldKit.fields;
                      empty at crew.html's initial page-load include
                      (fieldkit isn't threaded into that render context —
                      the panel is hidden behind the hero image at that
                      point anyway, and gets fully replaced by panel.py's
                      render the first time it's actually opened)
    - options         (dict, optional) — FieldKit.options, source name ->
                      list of {"value","label"} dicts
    - actions         (list, optional) — from formkit.FormActions, for
                      _form_actions.html
    - container_class (str, optional) — for _form_actions.html
#}
{% set fields = fields|default([]) %}
{% set options = options|default({}) %}
{% set record = record|default({}) %}
{% set actions = actions|default([]) %}

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
        {% include "partials/_detail_form_fields.html" %}
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

<!-- Action buttons: sticky footer -->
{% include 'partials/_form_actions.html' %}
```

---

## `_detail_panel.html`

### BEFORE

```jinja
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

### AFTER

```jinja
{#
  _detail_panel.html

  Bare shell for the detail panel — just the outer container div with
  data-entity/data-id attributes for JS to read. Actual content (tab
  bar, form, child tabs, action buttons) lives in
  _detail_panel_content.html, included here for crew.html's initial
  page-load render, and re-rendered wholesale by panel.py on every
  subsequent panel open — see detail-panel.js's fetchAndSwapPanel(),
  which replaces .detail-panel's entire innerHTML with panel.py's
  response.

  Parameters — same as _detail_panel_content.html; passed through
  automatically via Jinja's context-sharing include behavior, not
  restated here.
#}

<div class="detail-panel" data-entity="{{ entity }}" data-id="{{ record_id }}">
  {% include "partials/_detail_panel_content.html" %}
</div>
```

**Why:** This file now only renders once, at initial page load via
`crew.html`. Every subsequent open goes through `panel.py`, which renders
`_detail_panel_content.html` directly (no outer wrapper div — the wrapper
already exists in the DOM and isn't replaced, only its `innerHTML` is).

---

## `panel.py`

### BEFORE

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

### AFTER

```python
"""Detail panel content routes.

Serves a single entity's full panel content (tab bar, fieldkit-driven
form, child-tab placeholders, action buttons), rendered via
_detail_panel_content.html, for detail-panel.js to fetch-and-swap into
.detail-panel on every panel open (new record or existing).

Previously rendered only _detail_form_fields.html — the bare field
<div>s, no tab bar or form wrapper — which silently wiped out the tab
bar on every open, since detail-panel.js replaces .detail-panel's
entire innerHTML. Fixed by rendering the same content template
_detail_panel.html now delegates to for its own initial-page-load
render. See CHANGEDOC_DETAIL_PANEL_CONTENT_SPLIT.md for the full
diagnosis.

Mirrors crew.py's raw jinja2.Environment setup rather than introducing
FastAPI's Jinja2Templates as a second templating convention.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from dbkit.connection import AsyncDBConnection
from curator.formkit import FormActions
from curator.web.deps import get_db
from curator.web.routes.contacts import _fetch_contact_for_display
from curator.web.routes.organizations import _fetch_organization_for_display
from curator.web.routes.projects import _fetch_project_for_display

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
_FORMS_PATH = Path(__file__).parent.parent.parent / "data" / "forms.yaml"
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


def _render_panel_content(
    request: Request, entity: str, record: dict, record_id
) -> HTMLResponse:
    """Render the full panel-content template for one entity + record.

    Args:
        request:   Current request — used to reach app.state.fieldkit,
                   the FieldKit cache built once at FastAPI startup.
        entity:    One of "projects", "contacts", "organizations".
        record:    Field values dict, or {} for a new record.
        record_id: The record's id, or '' for a new record — set on
                   the <form> and <div class="detail-panel"> data
                   attributes JS reads.

    Returns:
        HTMLResponse — the rendered content (tab bar, form, child-tab
        placeholders, action buttons), ready to be swapped into
        .detail-panel's innerHTML by detail-panel.js.
    """
    kit = request.app.state.fieldkit[entity]
    detail_panel_actions = FormActions.from_yaml(_FORMS_PATH, "detail_panel")
    template = env.get_template("partials/_detail_panel_content.html")
    return HTMLResponse(
        template.render(
            entity=entity,
            record_id=record_id,
            record=record,
            fields=kit.fields,
            options=kit.options,
            actions=detail_panel_actions["actions"],
            container_class=detail_panel_actions["container_class"],
        )
    )


# /panel/{entity}/new must be declared before /panel/{entity}/{record_id}
# — same route-ordering rule as the save routes (literal before
# parameterized), otherwise FastAPI tries to parse "new" as an int and
# 422s instead of matching this route.

@router.get("/panel/{entity}/new")
async def panel_new(entity: str, request: Request):
    """Render the full panel content for a new, empty record."""
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")
    return _render_panel_content(request, entity, {}, "")


@router.get("/panel/{entity}/{record_id}")
async def panel_existing(
    entity: str,
    record_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Render the full panel content for an existing record."""
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")

    fetch_fn = _FETCH_FUNCTIONS[entity]
    record = await fetch_fn(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"{entity.title()} not found")

    return _render_panel_content(request, entity, record, record_id)
```

**Why:** `_render_fields` is renamed `_render_panel_content` since it now
renders considerably more than fields — the old name would be misleading.
`record_id` is now threaded through explicitly (previously absent — the old
field-only fragment didn't need it, but the `<form>`/`<div class="detail-panel">`
data attributes inside the content template do).

---

## Verify after applying

1. Restart uvicorn, hard-refresh the browser.
2. Open DevTools → Elements → search for `detail-tabs` on the initial page
   load — should find 1 match (from `crew.html`'s render).
3. Click `⋯` on any project row. Search for `detail-tabs` again — should
   still find 1 match, and the tab buttons should read Tasks/Links/Contacts.
4. Click `⋯` on a contact row. Tab buttons should now read
   Emails/Phones/URLs/Organizations — confirming the swap is genuinely
   entity-conditional per open, not stuck from page load.
5. Confirm Save/New/Exit buttons are still present and functional after
   a swap (not just on the initial page load).
6. `pylint src/` and `pytest` — no test currently covers `panel.py`
   (flagged in the 2026-07-06 handoff as a known gap), so this needs the
   manual browser check above; not something the test suite will catch.
