# CHANGEDOC — Tasks UI Wiring: Backend Pieces

**Status:** Ready to apply. Requires the viewkit `hidden` field_type
change (CHANGEDOC_VIEWKIT_HIDDEN_FIELD_TYPE.md) already applied and
reinstalled — confirmed done 2026-07-10.

**Payload shape verified 2026-07-10** against `api.save_task()`'s live
`prosrc` in `wcyj` (pulled via pgAdmin — the on-disk copy of
`06b_api_projects.sql` is stale and doesn't contain the Tasks functions
at all; a doc-sync gap, flagged separately). `tasks.py`'s payload keys
and the `_require_description` guard are accurate against what the
database actually enforces, not just the 2026-07-08 handoff's prose
summary.

**Not included here:** the nested master-detail Tasks tab layout
itself (Tabulator list + nested form in `_detail_panel_content.html`)
and the `detail-panel.js` multi-panel refactor it depends on. Those are
separate, larger pieces — this changedoc only gets Tasks to the point
where `/panel/tasks/{id}`, `/panel/tasks/new`, and `/crew/tasks/...`
all work correctly on their own, testable independently of any UI that
calls them yet.

## Summary of changes

1. `fieldkit_overrides.yaml` — new `projects.v_task_detail` entry
2. `_detail_form_fields.html` — new `hidden` field_type render branch
3. `panel.py` — `panel_new()` now forwards query params into the
   (empty) record dict, so a hidden field can be pre-filled on a new
   record via e.g. `/panel/tasks/new?project_id=12`; `tasks` added to
   `_FETCH_FUNCTIONS`
4. `tasks.py` — new route file, mirrors `contacts.py`/`organizations.py`
   exactly
5. `queries.yaml` — `tasks.for_project`/`tasks.for_task`: drop stale
   `ORDER BY t.sort_order` (column no longer exists)
6. `app.py` — `tasks` added to `_FIELDKIT_VIEWS`, `tasks` router
   registered

---

## File 1 — `fieldkit_overrides.yaml`

### BEFORE

```yaml
projects.v_project_detail:
  type_id:
    control: select
    label: Type
    source: project_types
  status_id:
    control: select
    label: Status
    source: project_statuses
```

### AFTER

```yaml
projects.v_project_detail:
  type_id:
    control: select
    label: Type
    source: project_types
  status_id:
    control: select
    label: Status
    source: project_statuses

projects.v_task_detail:
  project_id:
    control: hidden
    # Pre-filled from context (the parent Project) via the query param
    # panel_new() forwards into the record dict — e.g.
    # /panel/tasks/new?project_id=12. Never user-editable; a subtask's
    # panel always opens from its parent task/project, never a bare
    # form the person fills in project_id on themselves.
  parent_id:
    control: hidden
    # Same reasoning as project_id. Empty ('') for a top-level task.
    # Subtask creation (pre-filling parent_id from the parent task) is
    # part of the Subtasks feature — deferred, see
    # nested_master_detail_design.md's "Deferred" section.
  status_id:
    control: select
    label: Status
    source: task_statuses
  priority_id:
    control: select
    label: Priority
    source: priorities
```

### Why

- `project_id`/`parent_id` are `*_id` columns on `v_task_detail`, so
  fieldkit requires an override entry for both regardless — this
  satisfies that requirement while also declaring them `hidden`, per
  the nested master-detail design's hidden-field-plus-context-line
  approach.
- `status_id`/`priority_id` use the `task_statuses`/`priorities`
  lookup sources — both already added to `api.get_lookup()` in the
  2026-07-08 Tasks SQL layer changedoc, so no SQL work needed here.

---

## File 2 — `_detail_form_fields.html`

### BEFORE

```html
{% for field in fields %}
  <div class="form-group">
    <label for="detail-{{ field.name }}">{{ field.label }}</label>

    {% if field.field_type == "text" %}
      <input
        type="text"
        id="detail-{{ field.name }}"
        name="{{ field.name }}"
        value="{{ record.get(field.name) or '' }}"
        {% if field.placeholder %}placeholder="{{ field.placeholder }}"{% endif %}
      />

    {% elif field.field_type == "textarea" %}
      <textarea
        id="detail-{{ field.name }}"
        name="{{ field.name }}"
        {% if field.placeholder %}placeholder="{{ field.placeholder }}"{% endif %}
      >{{ record.get(field.name) or '' }}</textarea>

    {% elif field.field_type == "select" %}
      <select id="detail-{{ field.name }}" name="{{ field.name }}">
        <option value="">—</option>
        {% for opt in options.get(field.source, []) %}
          <option
            value="{{ opt.value }}"
            {% if record.get(field.name) == opt.value %}selected{% endif %}
          >
            {{ opt.label }}
          </option>
        {% endfor %}
      </select>

    {% elif field.field_type == "date" %}
      <input
        type="date"
        id="detail-{{ field.name }}"
        name="{{ field.name }}"
        value="{{ record.get(field.name) or '' }}"
      />

    {% elif field.field_type == "checkbox" %}
      <input
        type="checkbox"
        id="detail-{{ field.name }}"
        name="{{ field.name }}"
        {% if record.get(field.name) %}checked{% endif %}
      />
    {% endif %}

    {% if field.help_text %}
      <small class="form-help">{{ field.help_text }}</small>
    {% endif %}
  </div>
{% endfor %}
```

### AFTER

```html
{% for field in fields %}
  {% if field.field_type == "hidden" %}
    {# No wrapping .form-group / label / help_text — a hidden field has
       nothing to display. Rendering the bare <input type="hidden">
       still submits it as part of the form's FormData, which is all
       it needs to do. #}
    <input
      type="hidden"
      id="detail-{{ field.name }}"
      name="{{ field.name }}"
      value="{{ record.get(field.name) or '' }}"
    />

  {% else %}
    <div class="form-group">
      <label for="detail-{{ field.name }}">{{ field.label }}</label>

      {% if field.field_type == "text" %}
        <input
          type="text"
          id="detail-{{ field.name }}"
          name="{{ field.name }}"
          value="{{ record.get(field.name) or '' }}"
          {% if field.placeholder %}placeholder="{{ field.placeholder }}"{% endif %}
        />

      {% elif field.field_type == "textarea" %}
        <textarea
          id="detail-{{ field.name }}"
          name="{{ field.name }}"
          {% if field.placeholder %}placeholder="{{ field.placeholder }}"{% endif %}
        >{{ record.get(field.name) or '' }}</textarea>

      {% elif field.field_type == "select" %}
        <select id="detail-{{ field.name }}" name="{{ field.name }}">
          <option value="">—</option>
          {% for opt in options.get(field.source, []) %}
            <option
              value="{{ opt.value }}"
              {% if record.get(field.name) == opt.value %}selected{% endif %}
            >
              {{ opt.label }}
            </option>
          {% endfor %}
        </select>

      {% elif field.field_type == "date" %}
        <input
          type="date"
          id="detail-{{ field.name }}"
          name="{{ field.name }}"
          value="{{ record.get(field.name) or '' }}"
        />

      {% elif field.field_type == "checkbox" %}
        <input
          type="checkbox"
          id="detail-{{ field.name }}"
          name="{{ field.name }}"
          {% if record.get(field.name) %}checked{% endif %}
        />
      {% endif %}

      {% if field.help_text %}
        <small class="form-help">{{ field.help_text }}</small>
      {% endif %}
    </div>
  {% endif %}
{% endfor %}
```

### Why

- Every existing field type keeps its exact current markup — the
  `{% else %}` branch is a verbatim copy of the original loop body,
  just re-indented one level deeper.
- `hidden` fields skip the `.form-group`/`<label>`/`help_text` wrapper
  entirely, since there's nothing to label or explain — they exist
  purely to carry a value through `FormData` on save.
- Reads `record.get(field.name)` exactly like every other field type —
  no special-casing needed for the pre-fill-from-query-param behavior;
  it works automatically because `panel_new()` (below) puts the query
  param value into the same `record` dict this template already reads
  from.

---

## File 3 — `panel.py`

### BEFORE

```python
_FETCH_FUNCTIONS = {
    "projects": _fetch_project_for_display,
    "contacts": _fetch_contact_for_display,
    "organizations": _fetch_organization_for_display,
}
```

```python
@router.get("/panel/{entity}/new")
async def panel_new(entity: str, request: Request):
    """Render the full panel content for a new, empty record."""
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")
    return _render_panel_content(request, entity, {}, "")
```

### AFTER

```python
_FETCH_FUNCTIONS = {
    "projects": _fetch_project_for_display,
    "contacts": _fetch_contact_for_display,
    "organizations": _fetch_organization_for_display,
    "tasks": _fetch_task_for_display,
}
```

```python
@router.get("/panel/{entity}/new")
async def panel_new(entity: str, request: Request):
    """Render the full panel content for a new, empty record.

    Any query parameters on the request are forwarded into the record
    dict verbatim — e.g. /panel/tasks/new?project_id=12 pre-fills the
    Tasks form's hidden project_id field with '12'. This is the only
    mechanism for prefilling a new-record panel; it stays entity-
    agnostic on purpose (panel.py never checks entity to decide which
    query params are meaningful — that's fieldkit_overrides.yaml's
    job, via which fields exist and are marked hidden). A query param
    with no matching field name is simply ignored by
    _detail_form_fields.html's record.get(field.name) lookups.
    """
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")
    record = dict(request.query_params)
    return _render_panel_content(request, entity, record, "")
```

Also add the import (alongside the three existing `_fetch_*_for_display`
imports near the top of the file):

### BEFORE

```python
from curator.web.routes.contacts import _fetch_contact_for_display
from curator.web.routes.organizations import _fetch_organization_for_display
from curator.web.routes.projects import _fetch_project_for_display
```

### AFTER

```python
from curator.web.routes.contacts import _fetch_contact_for_display
from curator.web.routes.organizations import _fetch_organization_for_display
from curator.web.routes.projects import _fetch_project_for_display
from curator.web.routes.tasks import _fetch_task_for_display
```

### Why

- `dict(request.query_params)` — FastAPI's `Request.query_params` is a
  `Starlette` `QueryParams` (multidict-like) object; converting to a
  plain `dict` keeps only the last value per key, which is fine here
  since every current use case (a single parent id) never repeats a key.
- Deliberately generic: no `if entity == "tasks": ...` branching. Any
  future entity needing a pre-filled hidden field on its new-record
  panel gets this for free, the same way fieldkit's schema
  introspection already works for any entity without per-entity code.

---

## File 4 — `tasks.py` (new file)

```python
"""Task routes — CRUD for projects.tasks via api.save_task /
api.delete_task.

Mirrors contacts.py/organizations.py's structure exactly — same
deps.py helpers, same route shapes, same save/delete error contract.
Tasks have no "name" field (they use "description" instead), so the
blank-field guard is a local check rather than deps.py's require_name()
— see _require_description() below.
"""

import json

from fastapi import APIRouter, Depends, Request
from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    get_db,
    call_proc_and_refetch,
    delete_via_proc,
    get_detail_or_404,
    get_user_id,
    _fetch_json_scalar,
)
from fastapi.responses import JSONResponse

router = APIRouter()


async def _fetch_task_for_display(db: AsyncDBConnection, task_id: int) -> dict:
    """Fetch a task via api.get_task_detail() for the detail panel.

    Returns dict with id, project_id, parent_id, description, notes,
    status_id, priority_id keys — matches projects.v_task_detail's
    whitelist — or None if not found.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_task_detail(%s)", (task_id,)
    )


def _require_description(description: str):
    """Return a rejection response if description is blank, else None.

    Tasks don't have a "name" field — deps.py's require_name() is
    name-specific in both the field it checks and its message text, so
    this is a small local equivalent rather than a forced reuse. If a
    third entity ever needs the same "required text field, different
    name" shape, that's the point to extract a generic version into
    deps.py — two occurrences doesn't yet justify it.

    NOTE — this is a cheap early-exit for the single most common blank
    submission, not a complete mirror of api.save_task()'s validation.
    Confirmed against the live function body (2026-07-10):
    api.save_task() itself also rejects a missing/null project_id
    ("A project is required.") and a missing/null status_id ("Task
    status is required."), each returning its own
    {"success": false, ...} envelope. Those two are deliberately NOT
    re-checked here — project_id always arrives via the hidden field
    (set from context, never user-typed, so effectively always
    present), and status_id's presence depends on the form having a
    sensible default value (see the default-status discussion —
    unresolved as of this changedoc). This function only exists to
    save a round trip on the one rejection a person can trivially
    cause themselves (leaving description blank); the proc remains the
    real authority for project_id/status_id, and call_proc_and_refetch
    already forwards its rejection message straight through to the UI
    if either is somehow missing.
    """
    if not description:
        return JSONResponse({
            "success": False,
            "message": "Description is required.",
            "data": None,
        })
    return None


# -- Single task fetch (for detail panel) -------------------------------------

@router.get("/crew/tasks/{task_id}")
async def get_task(
    task_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single task as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_task_for_display, task_id, "Task not found"
    )


# -- Task save routes ----------------------------------------------------------
# /crew/tasks/save must be declared before /crew/tasks/{task_id}/save to
# prevent "save" matching as a task_id integer.

@router.post("/crew/tasks/save")
async def save_new_task(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new task via api.save_task().

    Accepts JSON body: {description, notes, status_id, priority_id,
    project_id, parent_id}. project_id arrives from the form's hidden
    field (pre-filled by panel.py's panel_new() from the ?project_id=
    query param — see nested_master_detail_design.md). parent_id is
    '' for a top-level task.

    Returns the new task record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure. api.save_task() enforces, in order: description required,
    project_id required and must reference an existing project,
    status_id required and must reference an existing task_status,
    parent_id (if given) must belong to the same project and not equal
    the task's own id. Only the description check is duplicated in
    Python (see _require_description) — the rest are the proc's alone.
    """
    body = await request.json()
    description = (body.get("description") or "").strip()
    notes = body.get("notes") or None
    status_id = body.get("status_id") or None
    priority_id = body.get("priority_id") or None
    project_id = body.get("project_id") or None
    parent_id = body.get("parent_id") or None

    rejection = _require_description(description)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {
        "description": description,
        "notes": notes,
        "status_id": status_id,
        "priority_id": priority_id,
        "project_id": project_id,
        "parent_id": parent_id,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_task(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_task_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/crew/tasks/{task_id}/save")
async def save_task(
    task_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing task via api.save_task().

    Accepts JSON body: {description, notes, status_id, priority_id,
    project_id, parent_id}.

    Returns the updated task record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — task not found, plus the same description/project_id/
    status_id/parent_id validation api.save_task() enforces on insert
    (see save_new_task's docstring above for the full list).
    """
    body = await request.json()
    description = (body.get("description") or "").strip()
    notes = body.get("notes") or None
    status_id = body.get("status_id") or None
    priority_id = body.get("priority_id") or None
    project_id = body.get("project_id") or None
    parent_id = body.get("parent_id") or None

    rejection = _require_description(description)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {
        "id": task_id,
        "description": description,
        "notes": notes,
        "status_id": status_id,
        "priority_id": priority_id,
        "project_id": project_id,
        "parent_id": parent_id,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_task(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_task_for_display,
        task_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/crew/tasks/{task_id}")
async def delete_task(
    task_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete a task by id via api.delete_task().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. not found, or blocked by undeleted child tasks (per
    api.delete_task()'s explicit child-task detection,
    CHANGEDOC_TASKS_SQL_LAYER.md).
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_task(%s, %s)", (task_id, user_id)
    )
```

### Why

- Structurally identical to `contacts.py`/`organizations.py` — same
  `deps.py` helpers (`call_proc_and_refetch`, `delete_via_proc`,
  `get_detail_or_404`, `get_user_id`), same route-ordering rule
  (literal `/save` before `/{id}/save}`), same error contract. This was
  explicitly verified in the datasheet URL-fix session (2026-07-10) —
  every entity's save/delete goes through the same shared helpers, so
  Tasks needed no special-casing to match.
- `_require_description()` is a small local function rather than
  forcing tasks to use `deps.py`'s `require_name()`, which is
  name-specific in both field and message wording. Flagged in its own
  docstring as a two-occurrences-isn't-a-pattern-yet judgment call —
  worth revisiting if a third entity needs the same shape.
- `status_id`/`priority_id`/`project_id`/`parent_id` are passed through
  as raw strings from the JSON body (or `None` if blank) without int
  casting — matches `projects.py`'s handling of `type_id`/`status_id`,
  which relies on psycopg/Postgres to compare a numeric-string against
  an integer column correctly.

---

## File 5 — `queries.yaml`

### BEFORE

```yaml
tasks:
  # Fetch all tasks for a project (detail panel Tasks tab)
  for_project:
    type: select_all
    sql: >
      SELECT
          t.id,
          t.description::text,
          t.notes::text,
          t.status_id,
          ts.name::text AS status,
          t.priority_id,
          p.name::text  AS priority,
          t.sort_order,
          t.created_at::text
      FROM projects.tasks t
      LEFT JOIN projects.task_status ts ON ts.id = t.status_id
      LEFT JOIN projects.priority    p  ON p.id  = t.priority_id
      WHERE t.project_id = %s
        AND t.parent_id IS NULL
      ORDER BY t.sort_order, t.created_at

  # Fetch sub-tasks for a parent task
  for_task:
    type: select_all
    sql: >
      SELECT
          t.id,
          t.description::text,
          t.notes::text,
          t.status_id,
          ts.name::text AS status,
          t.priority_id,
          p.name::text  AS priority,
          t.sort_order,
          t.created_at::text
      FROM projects.tasks t
      LEFT JOIN projects.task_status ts ON ts.id = t.status_id
      LEFT JOIN projects.priority    p  ON p.id  = t.priority_id
      WHERE t.parent_id = %s
      ORDER BY t.sort_order, t.created_at
```

### AFTER

```yaml
tasks:
  # Fetch all tasks for a project (detail panel Tasks tab)
  for_project:
    type: select_all
    sql: >
      SELECT
          t.id,
          t.description::text,
          t.notes::text,
          t.status_id,
          ts.name::text AS status,
          t.priority_id,
          p.name::text  AS priority,
          t.created_at::text
      FROM projects.tasks t
      LEFT JOIN projects.task_status ts ON ts.id = t.status_id
      LEFT JOIN projects.priority    p  ON p.id  = t.priority_id
      WHERE t.project_id = %s
        AND t.parent_id IS NULL
      ORDER BY t.created_at

  # Fetch sub-tasks for a parent task
  for_task:
    type: select_all
    sql: >
      SELECT
          t.id,
          t.description::text,
          t.notes::text,
          t.status_id,
          ts.name::text AS status,
          t.priority_id,
          p.name::text  AS priority,
          t.created_at::text
      FROM projects.tasks t
      LEFT JOIN projects.task_status ts ON ts.id = t.status_id
      LEFT JOIN projects.priority    p  ON p.id  = t.priority_id
      WHERE t.parent_id = %s
      ORDER BY t.created_at
```

### Why

- `t.sort_order` was dropped from `projects.tasks` in the Tasks SQL
  layer changedoc (2026-07-08) — both queries still selected and
  ordered by it, which would error the moment either query actually
  ran. Removed the column from the `SELECT` list and the `ORDER BY`
  clause in both.
- Ordering falls back to `t.created_at` — matches your stated
  intention ("ordering by naming convention or sort-by-name/date in
  the UI") until/unless a naming-convention-based sort is added at the
  UI layer later.

---

## File 6 — `app.py`

### BEFORE

```python
from curator.web.routes import auth, landing, crew, panel, projects, contacts, organizations

_FIELDKIT_VIEWS = {
    "projects": "projects.v_project_detail",
    "contacts": "identity.v_contact_detail",
    "organizations": "identity.v_organization_detail",
}
```

```python
app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)
app.include_router(panel.router)
app.include_router(projects.router)
app.include_router(contacts.router)
app.include_router(organizations.router)
```

### AFTER

```python
from curator.web.routes import (
    auth, landing, crew, panel, projects, contacts, organizations, tasks,
)

_FIELDKIT_VIEWS = {
    "projects": "projects.v_project_detail",
    "contacts": "identity.v_contact_detail",
    "organizations": "identity.v_organization_detail",
    "tasks": "projects.v_task_detail",
}
```

```python
app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)
app.include_router(panel.router)
app.include_router(projects.router)
app.include_router(contacts.router)
app.include_router(organizations.router)
app.include_router(tasks.router)
```

### Why

- `_FIELDKIT_VIEWS` entry lets `FieldKit.create()` build the Tasks
  cache at startup, same as every other entity — this is also where
  the `hidden`-type `FieldDef`s for `project_id`/`parent_id` actually
  get constructed and validated (via `fieldkit_overrides.yaml`'s new
  entries), so a mistake in that YAML (wrong source name, etc.) will
  crash uvicorn at startup exactly as designed, not surface as a broken
  form later.
- Router registration follows the same pattern as every other entity —
  no special treatment.

---

## Testing notes

- No existing test file covers `tasks.py` yet (`test_routes_tasks.py`
  doesn't exist in the current project files, unlike
  `test_routes_contacts.py`/`test_routes_organizations.py` for the
  other entities). Worth adding as a follow-up, mirroring those two
  files' structure — not included in this changedoc to keep scope to
  "make Tasks work," matching how the 2026-07-08 SQL layer changedoc
  also shipped without new tests and flagged it as a gap rather than
  blocking on it.
- Manual verification once applied:
  1. Restart uvicorn — confirm no `FieldSchemaError` at startup (this
     is the first real test of the `fieldkit_overrides.yaml` entries
     and the reinstalled `viewkit`).
  2. `curl http://localhost:8080/panel/tasks/new?project_id=1` — should
     return panel HTML with a hidden `project_id` input containing
     value `"1"`.
  3. `curl http://localhost:8080/panel/tasks/1` (assuming a task with
     id 1 exists) — should return the populated panel.
  4. A save/delete round-trip via `curl` or browser dev tools against
     `/crew/tasks/save`, `/crew/tasks/{id}/save`, `/crew/tasks/{id}` —
     confirms `tasks.py`'s routes work before any UI calls them.

## Not in scope for this changedoc

- The nested master-detail Tasks tab layout itself — replacing
  `_detail_panel_content.html`'s "Tasks — coming soon" placeholder with
  the real Tabulator-list-plus-nested-form UI. Depends on the
  `detail-panel.js` multi-panel refactor (flagged separately,
  2026-07-10) being done first.
- `test_routes_tasks.py` — flagged above as a gap, not written here.
- Subtask creation / `parent_id` prefill flow — deferred per
  `nested_master_detail_design.md`.
