# Curator v2 Handoff — 2026-06-25 (Full Session)

## Session Summary

Very long session covering inline row editing, add new record, schema
cleanup, and database rebuild from scratch. The crew dashboard now has
full CRUD for projects (add, inline edit, cancel) with HTMX, role
filtering, and a clean modular schema.

---

## What Was Accomplished This Session

### Inline Row Editing

Full inline edit working on all crew dashboards:

- **Pencil icon** in reserved icon column (leftmost), hidden by default,
  visible on row hover (desktop) or always visible on touch devices
  via `@media (hover: none)`
- **`⋯` detail icon** next to pencil — visible, `disabled` for now,
  placeholder for future project details page
- **Click pencil** → HTMX GET `/crew/projects/{id}/edit-form` → row
  expands to editable fields (name, type dropdown, status dropdown)
  in-column, aligned under Name/Type/Status headers
- **Controls row** appears below form row with Save and Cancel buttons
- **Save** → HTMX POST `/crew/projects/{id}/save` → writes to DB →
  `_collapse_edit_row()` returns display row + OOB delete of controls row
- **Cancel** → HTMX POST `/crew/projects/{id}/cancel` → same collapse,
  no DB write
- **OOB delete pattern**: response returns display row HTML +
  `<tr id="edit-controls-{id}" hx-swap-oob="delete"></tr>`
- Rows identified by stable IDs: `edit-row-{id}` and `edit-controls-{id}`
- Dropdowns pre-loaded at page load (lookup tables are short)

### Add New Record

Add form working on all crew dashboards:

- **`+` button** in Name column header, neutral styling
- **Click `+`** → HTMX GET `/crew/projects/new?role={role}` → empty
  form row appears at top of list via `hx-swap="afterbegin"`
- **Types filtered by role** — queries `project_type_role_mapping`
  joined to `identity.crew_role`
- **Save** → POST `/crew/projects/new/save?role={role}` → generates slug,
  inserts record, collapses to display row
- **Cancel** → POST `/crew/projects/new/cancel` → OOB deletes both add
  rows, no DB write
- **Duplicate slug** → 409 response with inline error, form stays open
- Slug generation: `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')`
- Add row IDs: `add-row-new` and `add-controls-new`

### Routing Fix

Add routes declared **before** edit routes in `crew.py` to avoid FastAPI
matching `"new"` as an integer `{project_id}`. Order:
`/crew/projects/new` → `/crew/projects/new/save` →
`/crew/projects/new/cancel` → `/crew/projects/{project_id}/edit-form`

### Python Fixes

- **`Query` → `Form`** in `save_project` — HTMX sends form-encoded body,
  not query string. FastAPI's `Form(...)` reads it correctly.
- **`fetch_val` → `fetch_scalar`** — dbkit has no `fetch_val`; correct
  method is `fetch_scalar`
- **`import re`** added to `crew.py` for slug generation

### CSS — forms.css

Moved to `static/css/components/forms.css` and linked in `base.html`.
Contains all edit/add form styles:
- Icon column, pencil/detail icon hover behavior
- `@media (hover: none)` for touch devices
- Add icon in header
- Edit/add input and select field styles
- Save/Cancel button styles including `color: #111 !important` to
  override Pico CSS button color

### Schema Rebuild — Clean Slate

The live `wcyj` database was rebuilt from scratch with six modular SQL
files. Previous issues fixed:
- Infrastructure lookup tables were in `projects` schema — moved to
  `infrastructure`
- `contacts` schema renamed to `identity` (already done in live DB,
  now correct in SQL files)
- `project_type_status_mapping` added (new — see below)
- All types and statuses correctly seeded
- All GRANTs included in schema files, not separate

**Run order in pgAdmin as PG_Super on wcyj:**
1. `00_drop.sql` — drops all schemas CASCADE
2. `01_audit.sql` — audit schema + `public.set_updated_at()`
3. `02_identity.sql` — identity schema (contacts, orgs, crew_role, app_user)
4. `03_projects.sql` — projects schema + views + mapping tables
5. `04_infrastructure.sql` — infrastructure schema, lookups in correct schema
6. `05_seed.sql` — all seed data

Files live in `steward` repo at `sql/wcyj/`.

### project_type_status_mapping

New table defining which statuses are valid for each project type:
- All types get: `active`, `archived`, `complete`, `on hold`, `queued`
- Writing additionally gets: `published`, `ready to write`, `in progress`
- Managed by Captain's Command Center UI (not hardcoded)
- Enables status dropdown on add/edit forms to filter by selected type
  (app code for dynamic filtering not yet written — table is ready)

### Database Fixes During Session

- Table name: `projects.project` → `projects.projects` (plural)
- Column names in `project_type_role_mapping`: `type_id` →
  `project_type_id`, `role_id` → `crew_role_id`
- Missing GRANTs discovered and added (now all in schema files):
  `identity.crew_role`, `project_type_role_mapping`,
  `project_type_status_mapping`, INSERT on `projects.projects`,
  SEQUENCE usage

### pylint

- E0401 import errors for fastapi/jinja2 are false positives — pylint
  configuration issue not a code problem. `python -c "import fastapi"`
  confirms packages installed correctly.
- Fix: create `.pylintrc` at project root, add `import-error` and
  `no-name-in-module` to `disable=` line.
- dbkit E0001 was missing blank line between `__init__` and `__enter__`
  in installed copy. Fixed directly in venv file.
- Remaining real issues: trailing whitespace and missing final newlines
  in various files, unnecessary `pass` in exceptions.py.

---

## Files Changed This Session

| File | Change |
|------|--------|
| `src/curator/web/routes/crew.py` | Major rewrite: add/edit/cancel routes, Form params, fetch_scalar, slug generation, role-filtered types, `_collapse_edit_row()`, `_fetch_project_for_display()` |
| `templates/crew.html` | Icon `<th>`, `+` button in Name header, JS lookup embed |
| `templates/_crew_rows.html` | Delegates to `_crew_row_display.html` partial |
| `templates/_crew_row_display.html` | NEW — display row with pencil + detail icons |
| `templates/_crew_row_edit.html` | NEW — two-row edit form with stable IDs |
| `templates/_crew_row_add.html` | NEW — two-row add form, role-filtered types, error span |
| `static/css/components/forms.css` | NEW — all edit/add form styles, icons, responsive |
| `base.html` | Added `<link>` for `forms.css` |
| `steward/sql/wcyj/00_drop.sql` | NEW — drop all schemas in reverse dependency order |
| `steward/sql/wcyj/01_audit.sql` | NEW — replaces old wcyj_schema.sql audit section |
| `steward/sql/wcyj/02_identity.sql` | NEW — identity schema (was contacts, now correct) |
| `steward/sql/wcyj/03_projects.sql` | NEW — projects schema + mapping tables + views |
| `steward/sql/wcyj/04_infrastructure.sql` | NEW — infrastructure schema, lookups in correct home |
| `steward/sql/wcyj/05_seed.sql` | NEW — all seed data, name-based lookups, no hardcoded IDs |

---

## Current State

### Working
- Landing page with four crew cards ✅
- Role-filtered project lists (Captain/Scribe/Mechanic/Envoy) ✅
- HTMX search filtering within role views ✅
- Inline row editing (pencil → expand → save/cancel) ✅
- Add new project (+ → form → save/cancel) ✅
- Role-filtered type dropdowns on add form ✅
- Duplicate slug detection with inline error ✅
- Pencil and ⋯ icons (⋯ disabled, pencil active) ✅
- Touch device support for icon visibility ✅
- Button labels visible (Pico CSS override in forms.css) ✅
- Clean modular schema in steward repo ✅
- Infrastructure lookup tables in correct schema ✅
- `project_type_status_mapping` table seeded ✅

### Known Issues / Deferred
- Status dropdown on add/edit not yet filtered by selected type —
  `project_type_status_mapping` table exists and is seeded but app
  code for dynamic filtering not yet written (needs JS on type change)
- `⋯` detail icon is `disabled` — no route or page behind it yet
- Envoy mapped to `refurb` in seed — review whether correct or should
  be Mechanic only; adjust via Captain's Command Center once built
- After add, new record appears at top of list (not sorted) — page
  reload restores alphabetical sort; acceptable for now
- pylint false positives need `.pylintrc` at project root
- Responsive design on edit/add form needs review at narrow widths

---

## Next Steps (in order)

### 1. Dynamic status filtering on add/edit form

When user selects a type in the add or edit form, the status dropdown
should repopulate with only statuses valid for that type, from
`project_type_status_mapping`. Requires a small JavaScript `change`
event handler on the type dropdown, or an HTMX `hx-get` to a new
endpoint that returns filtered status options.

### 2. Captain's Command Center

Sub-card on Captain's dashboard page (not a 5th crew card on landing).
Two dual-listbox UIs:
- **Role → Project Types**: which types does each role see?
  Manages `project_type_role_mapping`
- **Project Type → Statuses**: which statuses are valid per type?
  Manages `project_type_status_mapping`

### 3. Project details page (`⋯` → `/projects/{slug}`)

- Full edit: name, type, status, description, notes
- Eventually: tasks list, file attachments, parent project
- Activates the `⋯` detail icon on every row

### 4. Task management

- Tasks per project record
- Accessible from project details page

### 5. Authentication (Phase 3)

- Login form per crew card
- Role validation, session management
- `identity.app_user` table is ready

### 6. contactkit web form

- CLI tool started but never finished end-to-end
- Web form takes priority over CLI completion
- `identity.contacts` and `identity.organizations` tables are ready

### 7. `curator_init.py`

High priority for new machine setup. Writes `~/.config/dev-utils/config.yaml`,
`~/.pgpass` (chmod 0600), and `.env` in one pass with live DB connection
verification. Recurring pain point after mesh migrations.

---

## Roadmap Items

- **Shipwright** — new crew role for coding/package projects. Coding
  doesn't belong under Mechanic (refurb territory). Shipwright handles
  code, packages, dev tooling. Needs: new crew_role seed row, new
  project_type_role_mapping rows, new role view, new CSS color.
- **Captain sub-cards** — Captain's page eventually gets its own card
  grid instead of a flat project list:
  - **Command Center** — role/type/status assignment settings
  - **The Shipwright** — coding projects
  - **Bursar's Room** — git operations (future Bosun tool)
- **Duplicate project name UX** — when duplicate slug detected on add,
  offer: accept name with `(1)` appended, enter new name, or open the
  existing project's detail page
- **`⋯` icon column** — reserved for future per-row actions: drag
  handles, checkboxes, etc. in addition to the detail link
- **HTMX flow diagram** from inline edit changedoc belongs in site
  documentation ("how the crew dashboard works")
- **PostgreSQL streaming replication**: wcyj-meet as primary, steward
  as standby
- **Scoped Felipe access**: herald node, `refurb` PostgreSQL role
  limiting access to refurb records only

---

## Key Facts

- **Database**: `wcyj` on steward (100.64.0.7)
- **App user**: `steward` PostgreSQL role
- **Schemas**: `audit`, `identity`, `projects`, `infrastructure`
- **Base table**: `projects.projects` (plural)
- **Views**: `projects.{role}_view` — captain, scribe, mechanic, envoy
- **Crew role names**: captain, envoy, mechanic, scribe
- **Project types**: coding, game-dev, homelab, personal, refurb, writing
- **Common statuses**: active, archived, complete, on hold, queued
- **Writing-only statuses**: published, ready to write, in progress
- **Mapping tables**:
  - `project_type_role_mapping` (columns: `project_type_id`, `crew_role_id`)
  - `project_type_status_mapping` (columns: `project_type_id`, `status_id`)
- **HTMX OOB pattern**: response returns display row +
  `<tr id="edit-controls-{id}" hx-swap-oob="delete"></tr>`
- **Add row IDs**: `add-row-new`, `add-controls-new`
- **Edit row IDs**: `edit-row-{project_id}`, `edit-controls-{project_id}`
- **Slug generation**: `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')`
- **Pico CSS override**: `color: #111 !important` in forms.css
- **Route order**: `/crew/projects/new` must be declared before
  `/crew/projects/{project_id}/edit-form` in crew.py
- **Schema file location**: `steward` repo, `sql/wcyj/` directory
- **Curator runs on**: wcyjv20 (LMDE), `localhost:8080`
- **pgAdmin runs on**: wcyjvs2 (100.64.0.6:5050)
- **Nautical commit vocab**: `launch`, `trim`, `patch`, `refit`,
  `provision`, `stow`, `chart`
