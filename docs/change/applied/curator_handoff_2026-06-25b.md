# Curator v2 Handoff — 2026-06-25 (Session B)

## Session Summary

Long session implementing inline row editing and record add on the crew
dashboard. Both features are working end-to-end with HTMX, PostgreSQL,
and responsive CSS. Several infrastructure issues were debugged along
the way (table name, column names, missing grants, Pico CSS overrides).

---

## What Was Accomplished This Session

### Inline Row Editing

Full inline edit is working on all crew dashboards:

- **Pencil icon** in reserved icon column (leftmost), hidden by default,
  visible on row hover (desktop) or always visible on touch devices
- **`⋯` detail icon** next to pencil — visible but `disabled` for now,
  placeholder for future project details page
- **Click pencil** → HTMX GET `/crew/projects/{id}/edit-form` → row
  expands to editable fields (name, type dropdown, status dropdown)
- **Controls row** appears below form row with Save and Cancel buttons
- **Save** → HTMX POST `/crew/projects/{id}/save` → writes to DB →
  collapses both rows back to display row via `_collapse_edit_row()`
- **Cancel** → HTMX POST `/crew/projects/{id}/cancel` → collapses both
  rows, no DB write
- **OOB delete** pattern: save/cancel response returns display row +
  `<tr id="edit-controls-{id}" hx-swap-oob="delete"></tr>` to remove
  controls row cleanly
- Dropdowns pre-loaded at page load (lookup tables not long, no delay)
- Fields align under Name/Type/Status column headers

### Add New Record

Add form is working on all crew dashboards:

- **`+` button** in Name column header, neutral styling blending with
  header colors
- **Click `+`** → HTMX GET `/crew/projects/new?role={role}` → empty
  form row appears at top of list via `hx-swap="afterbegin"`
- **Types filtered by role** — queries `project_type_role_mapping` joined
  to `identity.crew_role`, so Mechanic only sees mechanic-appropriate
  types, etc.
- **Save** → HTMX POST `/crew/projects/new/save?role={role}` → generates
  slug from name, inserts record, collapses to display row
- **Cancel** → HTMX POST `/crew/projects/new/cancel` → OOB deletes both
  add rows, no DB write
- **Duplicate slug handling** → 409 response with inline error message,
  form stays open for correction
- Slug generation: `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')`

### Routing Fix

Add routes declared **before** edit routes in `crew.py` to avoid FastAPI
matching `"new"` as an integer `{project_id}` path parameter.
Routes: `/crew/projects/new` (GET), `/crew/projects/new/save` (POST),
`/crew/projects/new/cancel` (POST) all come before
`/crew/projects/{project_id}/edit-form` etc.

### Database Fixes

- **Table name**: `projects.project` → `projects.projects` (plural)
- **Column names in `project_type_role_mapping`**: `type_id` →
  `project_type_id`, `role_id` → `crew_role_id`
- **Missing GRANTs** to `steward` role:
  ```sql
  GRANT SELECT ON identity.crew_role TO steward;
  GRANT SELECT ON projects.project_type_role_mapping TO steward;
  GRANT SELECT ON projects.project_status_role_mapping TO steward;
  GRANT INSERT ON projects.projects TO steward;
  GRANT USAGE ON SEQUENCE projects.projects_id_seq TO steward;
  ```

### Python Fix

- **`Query` → `Form`** in `save_project` route — HTMX sends form-encoded
  body data, not query string parameters. FastAPI's `Form(...)` is
  required to read it correctly.
- **`fetch_val` → `fetch_scalar`** — dbkit has no `fetch_val` method;
  the correct method is `fetch_scalar`.
- **`import re`** added to `crew.py` for slug generation.

### CSS

- `forms.css` moved to `static/css/components/forms.css` (component, not
  site-wide)
- Linked in `base.html` under component styles section
- Contains: icon column styles, pencil/detail icon hover behavior,
  `@media (hover: none)` rule for touch devices, add icon styles,
  edit/add field styles, Save/Cancel button styles including
  `color: #111 !important` to override Pico CSS button color behavior
- No color declarations in `forms.css` — role colors stay in crew files

### pylint

- `fastapi`, `jinja2` import errors are false positives — pylint
  configuration issue, not real errors. `python -c "import fastapi"`
  confirms packages are correctly installed.
- dbkit E0001 was caused by missing blank line between `__init__` and
  `__enter__` in the installed copy of `connection.py`. Fixed directly
  in the venv file. Source file at `~/projects/dev-utils/python/dbkit/`
  also has the fix but pip was using a cached wheel — fixed with
  `pip install --no-cache-dir --force-reinstall`.
- Remaining real issues to clean up: trailing whitespace and missing
  final newlines in various files, unnecessary `pass` in exceptions.py,
  wrong import order in landing.py.
- `.pylintrc` should be created at project root with `import-error` and
  `no-name-in-module` suppressed (false positives due to venv detection).

---

## Files Changed This Session

| File | Change |
|------|--------|
| `src/curator/web/routes/crew.py` | Major: add/edit/cancel routes, Form params, fetch_scalar, slug, role-filtered types |
| `templates/crew.html` | Added icon `<th>`, `+` button in Name header, JS lookup embed |
| `templates/_crew_rows.html` | Delegates to `_crew_row_display.html` partial |
| `templates/_crew_row_display.html` | NEW — display row with pencil + detail icons |
| `templates/_crew_row_edit.html` | NEW — two-row edit form with IDs for HTMX targeting |
| `templates/_crew_row_add.html` | NEW — two-row add form, role-filtered types, error span |
| `static/css/components/forms.css` | NEW — all edit/add form styles, icon visibility, responsive |
| `base.html` | Added `<link>` for `forms.css` |

---

## Current State

### Working
- Landing page with four crew cards ✅
- Role-filtered project lists (Captain/Scribe/Mechanic/Envoy) ✅
- HTMX search filtering within role views ✅
- Inline row editing (pencil → edit → save/cancel) ✅
- Add new project (+ → form → save/cancel) ✅
- Role-filtered type dropdowns on add form ✅
- Duplicate slug detection with inline error ✅
- Pencil and ⋯ icons (⋯ disabled, pencil active) ✅
- Touch device support for icon visibility ✅
- Button labels visible (Pico CSS override) ✅

### Known Issues / Deferred
- `⋯` detail icon is `disabled` — links to nothing yet
- Envoy mapped to `refurb` in `project_type_role_mapping` — should
  probably be Mechanic; fix via pgAdmin or Captain's Command Center
- `project_status_role_mapping` seeded but not yet wired into views
- Old projects data migration (`phase2_migration.md`) still deferred
- pylint false positives (import-error) — needs `.pylintrc`
- Responsive design on edit/add form needs review at narrow widths
- After add, new record appears at top of list (not sorted) — page
  reload restores sort order; acceptable for now

---

## Next Steps (in order)

### 1. Captain's Command Center (Phase 2 completion)

- Role ↔ project type assignment UI (dual listbox)
- Role ↔ project status assignment UI
- Eventually: define new roles, manage contacts, manage users
- Lives as a sub-card on Captain's dashboard page (not a 5th crew card)

### 2. Project details page (`⋯` → `/projects/{slug}`)

- Full edit: name, type, status, description, notes
- Eventually: tasks list, file attachments, parent project
- Activates the `⋯` detail icon on every row

### 3. Task management

- Tasks per project record
- Accessible from project details page

### 4. Authentication (Phase 3)

- Login form per crew card
- Role validation, session management

### 5. contactkit web form

- CLI tool was started but never finished end-to-end
- Web form takes priority over CLI completion

---

## Roadmap Items Noted This Session

- **Shipwright** — new crew role for coding/package projects. Coding
  projects don't belong under Mechanic (refurb territory). Shipwright
  handles code, packages being built, dev tooling.
- **Captain sub-cards** — Captain's page eventually has its own card
  grid instead of a flat project list:
  - **Command Center** — role/type/status assignment settings
  - **The Shipwright** — coding projects
  - **Bursar's Room** — git operations (future Bosun tool)
- **Duplicate project name UX** (roadmap, not implemented) — when a
  duplicate slug is detected on add, offer: accept name with `(1)`
  appended, enter a new name, or open the existing project's detail page
- **`⋯` icon** — reserved column will eventually hold drag handles,
  checkboxes, or other per-row actions in addition to the detail link
- **HTMX flow diagram** from inline edit changedoc belongs in site
  documentation ("how the crew dashboard works" section)
- **`curator_init.py`** — still high priority for new machine setup;
  writes config.yaml, .pgpass, .env in one pass with live DB verify

---

## Key Facts

- **Database**: `wcyj` on steward (100.64.0.7), `steward` PostgreSQL
  role is the Curator app user
- **Schemas**: `audit`, `identity`, `projects`, `infrastructure`
- **Base table**: `projects.projects` (plural)
- **Views**: `projects.{role}_view` — captain, scribe, mechanic, envoy
- **Role IDs**: captain=1, envoy=2, mechanic=3, scribe=4
- **Mapping tables**: `project_type_role_mapping` (columns:
  `project_type_id`, `crew_role_id`), `project_status_role_mapping`
- **HTMX OOB pattern**: save/cancel returns display row HTML +
  `<tr id="edit-controls-{id}" hx-swap-oob="delete"></tr>`
- **Add row IDs**: `id="add-row-new"` and `id="add-controls-new"`
- **Edit row IDs**: `id="edit-row-{project_id}"` and
  `id="edit-controls-{project_id}"`
- **Slug generation**: `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')`
- **Pico CSS button override**: `color: #111 !important` in forms.css
- **Route order matters**: `/crew/projects/new` must be declared before
  `/crew/projects/{project_id}/edit-form` in crew.py
- **Nautical commit vocab**: `launch`, `trim`, `patch`, `refit`,
  `provision`, `stow`, `chart`
