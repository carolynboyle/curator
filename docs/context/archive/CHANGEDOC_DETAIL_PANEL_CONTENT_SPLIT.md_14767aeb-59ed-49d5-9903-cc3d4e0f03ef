# Changedoc: Detail Panel Content Split (Bug Fix) — REVISED

**Date:** 2026-07-06 (continued session)
**Supersedes:** the earlier same-titled changedoc from this session — do
not apply that one, apply this one instead. Same bug, cleaner fix.
**Depends on:** `_detail_panel.html`, `panel.py`, `_form_actions.html`,
`crew.html` (all as uploaded this session)

**Scope:** Bug fix + a small cleanup the bug fix surfaced. No SQL, no new
routes.

---

## The bug, precisely

`crew.html` includes `_detail_panel.html` once at initial page load,
hardcoded to `entity='projects'`. But that render is **never visible** —
the panel sits hidden behind the hero image until someone clicks `⋯` or
`+ Add`, at which point `detail-panel.js`'s `fetchAndSwapPanel()` replaces
`.detail-panel`'s entire `innerHTML` with whatever `panel.py` returns from
`/panel/{entity}/{id}` (or `.../new`).

`panel.py` was only ever rendering `_detail_form_fields.html` — bare field
`<div>`s, no tab bar, no `<form>` wrapper, no close button — because
`_detail_panel_content.html`, the file it was seemingly written assuming
existed, was never actually created. So the correct tab bar from the
invisible initial render gets wiped out the moment anyone opens anything,
replaced by three bare `.form-group` divs. Confirmed via DOM inspection
after a full uvicorn restart and browser cache clear — not staleness, a
genuine mismatch between what `detail-panel.js` assumes `panel.py` returns
and what it actually returns.

## The cleanup this surfaced

Once `_detail_panel_content.html` exists and `panel.py` is the *only* thing
that renders real content into `.detail-panel`, `crew.html`'s initial-load
render of `_detail_panel.html` has no job left to do — it's invisible,
gets fully overwritten on first open regardless, and was hardcoding a fake
`entity='projects'` plus forwarding `project_types`/`project_statuses` that
`_detail_panel_content.html` doesn't even reference (fieldkit replaced that
raw-lookup approach already). Keeping it "just in case" would mean two
different code paths capable of rendering this panel's content — exactly
the duplication fieldkit's whole design was meant to eliminate, even if
one path is currently invisible. So it's removed outright, not defended
against with default-value fallbacks.

---

## The fix

1. **New `_detail_panel_content.html`** — the tab bar + form + child-tab
   placeholders + action buttons, extracted from `_detail_panel.html`.
   This is what `panel.py` renders on every real panel open.
2. **`_detail_panel.html` becomes a genuinely empty shell** — no
   entity/record data at all. Just the outer div, rendered once,
   invisible, immediately superseded on first open.
3. **`crew.html`'s include simplifies** — drops the `{% with entity=...,
   record_id=..., record={}, project_types=..., project_statuses=... %}`
   wrapper entirely; just includes the now-parameterless shell.
4. **`panel.py` renders `_detail_panel_content.html` instead of
   `_detail_form_fields.html`**, loading `actions`/`container_class` via
   `FormActions.from_yaml()` the same way `crew.py` already does — confirmed
   against the real `formkit.py` (`from_yaml()` returns exactly
   `{"container_class": ..., "actions": [...]}`, matching what
   `_form_actions.html` expects).

`_detail_panel_content.html` still defaults `fields`/`options`/`record`/
`actions` to empty values — not to support two callers gracefully anymore
(there's only one real caller, `panel.py`, which always supplies full
data), but because the shell's one harmless initial-load render passes
nothing at all, and Jinja raises on iterating an undefined variable
(`{% for field in fields %}`) even though it happily prints one as empty
text. The defaults are a two-line safety net for that one invisible
render, not a design accommodation.

---

## Apply order

No SQL, no pgAdmin steps. Four file changes below, then restart uvicorn
and hard-refresh the browser.

---

## `_detail_panel_content.html` (new file)

```jinja
{#
  _detail_panel_content.html

  The actual rendered content of a detail panel for one entity + record:
  tab navigation, the Details tab (fieldkit-driven form), the
  currently-placeholder child tabs, and the action button bar.

  panel.py is the ONLY renderer of this template with real data — every
  /panel/{entity}/{id} (or .../new) request re-renders this exact
  content, and detail-panel.js's fetchAndSwapPanel() replaces
  .detail-panel's entire innerHTML with the result. _detail_panel.html's
  own initial-page-load render includes this template with nothing —
  invisible, immediately overwritten on first open — which is why the
  defaults below exist.

  Parameters (all optional — panel.py always supplies them; only
  _detail_panel.html's invisible initial render omits them):
    - entity          (str)  — "projects", "contacts", or "organizations"
    - record_id       (int|str) — blank/'' for a new-record panel
    - record          (dict, optional) — current field values, defaults {}
    - fields          (list[FieldDef], optional) — from FieldKit.fields,
                      defaults []
    - options         (dict, optional) — FieldKit.options, source name ->
                      list of {"value","label"} dicts, defaults {}
    - actions         (list, optional) — from formkit.FormActions, for
                      _form_actions.html, defaults []
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

  Genuinely empty shell for the detail panel container — no entity,
  no record data. This is the ONE render of this file that happens via
  crew.html at initial page load, and it's invisible: the panel sits
  hidden behind the hero image until someone clicks ⋯ or + Add. From
  that point on, panel.py is the sole renderer of real content —
  /panel/{entity}/{id} (or .../new) returns _detail_panel_content.html
  fully populated, and detail-panel.js's fetchAndSwapPanel() replaces
  this div's entire innerHTML with it.

  Previously received entity='projects'/record_id=0/record={}/
  project_types/project_statuses from crew.html — all vestigial.
  project_types/project_statuses aren't referenced anywhere in
  _detail_panel_content.html (fieldkit replaced that raw-lookup
  approach), and entity/record_id were rendering a fake "projects"
  panel nobody ever saw before panel.py overwrote it on first open.
  Removed outright rather than defended against with fallback values —
  a second code path capable of rendering this content, even one that's
  invisible, is exactly the duplication fieldkit's design was meant to
  eliminate.
#}

<div class="detail-panel" data-entity="" data-id="">
  {% include "partials/_detail_panel_content.html" %}
</div>
```

---

## `crew.html`

### BEFORE

```jinja
{% extends "base.html" %}

{% block title %}{{ role_title }} — Curator{% endblock %}

{% block content %}
<section class="crew-section {{ role }}">

    <!-- Hero image and detail panel share the same spot; toggle visibility -->
    <div class="hero-detail-stack">
        {% with
            role=role,
            hero_image=role + ".png",
            title=role_title,
            show_back=true
        %}
            {% include "partials/_crew_header.html" %}
        {% endwith %}

        <div id="detail-panel-container">
            {% with entity='projects', record_id=0, record={}, project_types=project_types, project_statuses=project_statuses %}
                {% include "partials/_detail_panel.html" %}
            {% endwith %}
        </div>
    </div>

    <!-- Tab Navigation -->
    <div class="tabs">
        {% for tab in tabs %}
            <button
                class="tab-btn {% if loop.first %}active{% endif %}"
                data-tab="tab-{{ tab.id }}"
            >{{ tab.label }}</button>
        {% endfor %}
    </div>

    <!-- Tab Panels -->
    {% for tab in tabs %}
        <div id="tab-{{ tab.id }}" class="tab-panel {% if loop.first %}active{% endif %}">
            {% include "partials/" + tab.template %}
        </div>
    {% endfor %}

</section>

<!-- Embed lookups for Tabulator and identity panels -->
<script>
    window.projectTypes    = {{ project_types    | tojson }};
    window.projectStatuses = {{ project_statuses | tojson }};

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(this.dataset.tab).classList.add('active');
            this.classList.add('active');
        });
    });
</script>
{% endblock %}
```

### AFTER

```jinja
{% extends "base.html" %}

{% block title %}{{ role_title }} — Curator{% endblock %}

{% block content %}
<section class="crew-section {{ role }}">

    <!-- Hero image and detail panel share the same spot; toggle visibility -->
    <div class="hero-detail-stack">
        {% with
            role=role,
            hero_image=role + ".png",
            title=role_title,
            show_back=true
        %}
            {% include "partials/_crew_header.html" %}
        {% endwith %}

        <div id="detail-panel-container">
            {% include "partials/_detail_panel.html" %}
        </div>
    </div>

    <!-- Tab Navigation -->
    <div class="tabs">
        {% for tab in tabs %}
            <button
                class="tab-btn {% if loop.first %}active{% endif %}"
                data-tab="tab-{{ tab.id }}"
            >{{ tab.label }}</button>
        {% endfor %}
    </div>

    <!-- Tab Panels -->
    {% for tab in tabs %}
        <div id="tab-{{ tab.id }}" class="tab-panel {% if loop.first %}active{% endif %}">
            {% include "partials/" + tab.template %}
        </div>
    {% endfor %}

</section>

<!-- Embed lookups for Tabulator and identity panels -->
<script>
    window.projectTypes    = {{ project_types    | tojson }};
    window.projectStatuses = {{ project_statuses | tojson }};

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(this.dataset.tab).classList.add('active');
            this.classList.add('active');
        });
    });
</script>
{% endblock %}
```

**Why:** `project_types`/`project_statuses` stay as top-level `crew.html`
variables — the `<script>` block at the bottom still uses them directly for
Tabulator, unrelated to the detail panel. Only the detail-panel include's
`{% with %}` wrapper is removed.

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
_detail_panel.html's (now-empty, invisible) initial render delegates
to. See CHANGEDOC_DETAIL_PANEL_CONTENT_SPLIT.md for the full diagnosis.

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
                   the <form> data attributes JS reads.

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
renders considerably more than fields. Confirmed against the real
`formkit.py` this time — `from_yaml()` returns
`{"container_class": str, "actions": [dict, ...]}`, each action dict having
`label`/`type`/`class`/`id`/`title`/`form_id`/`data_attrs`, an exact match
for `_form_actions.html`'s expectations.

---

## Verify after applying

1. Restart uvicorn, hard-refresh the browser.
2. DevTools → Elements → search for `detail-tabs` on initial page load —
   should find 1 match, tab buttons empty/inert (no entity set yet — this
   is expected and invisible, panel is hidden behind the hero image).
3. Click `⋯` on a project row. Search `detail-tabs` again — 1 match, tab
   buttons now read Tasks/Links/Contacts.
4. Click `⋯` on a contact row. Tab buttons now read
   Emails/Phones/URLs/Organizations — confirms the swap is genuinely
   entity-conditional per open.
5. Confirm Save/New/Exit buttons are present and functional after a swap.
6. `pylint src/` and `pytest` — no test currently covers `panel.py`
   (flagged in the 2026-07-06 handoff as a known gap) or `crew.html`'s
   Jinja, so this needs the manual browser check above.
