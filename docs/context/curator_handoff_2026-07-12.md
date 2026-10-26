# Curator Handoff — 2026-07-10/12

## Session summary

Started with the datasheet save/delete URL fix left over from the
2026-07-08 session, then moved into Tasks UI wiring: a `viewkit`
change to support hidden form fields, the Curator-side backend pieces
to make `/panel/tasks/...` and `/crew/tasks/...` work, and a design
doc for how the Tasks tab's UI will actually look. Several apply-time
bugs were caught and fixed along the way — recorded below since the
pattern (content added without removing/reconciling the old version)
recurred more than once and is worth watching for generally, not just
in this session.

---

## Completed and verified this session

**`datasheet.js` / `detail-panel.js` — URL and success-flag fixes**
(carried over from 2026-07-08, finished this session)
- `datasheet.js`'s `saveRow()`/`deleteRow()`: URLs changed from the
  nonexistent `/api/{entity}/...` to the real `/crew/{entity}/...`
  routes.
- Both now check `body.success === false` (not `resp.ok`/`res.ok`) to
  detect failure — confirmed against `projects.py`/`contacts.py`/
  `organizations.py` that every save route returns failures as HTTP
  200 with a `{"success": false, "message": ...}` envelope, not a
  non-2xx status. `resp.ok` was always `true` regardless of outcome.
- **Found and fixed a real latent bug in already-shipped code**:
  `detail-panel.js`'s `saveForm()` had the same `res.ok` mistake —
  meaning a rejected save (duplicate name, etc.) was previously being
  silently treated as successful.
- Delete's contract is different from save's: success is a bare HTTP
  204 (no body), failure is 200 with a `success: false` body — so
  delete's check is on status code, not on a parsed body.
- Confirmed via `contacts.py`/`organizations.py`/`deps.py` that this
  contract isn't just convention — every entity's save/delete goes
  through the same shared `deps.py` helpers
  (`call_proc_and_refetch`/`delete_via_proc`), so the fix generalizes
  correctly to Tasks (and any future entity) with no special-casing.
- Changedoc: `CHANGEDOC_DATASHEET_URL_AND_SUCCESS_FLAG_FIX.md`.
- Architecture decision confirmed and logged: the `/crew/{entity}/...`
  route prefix is permanent, even across future business verticals —
  "crew" names the role-based access layer (a DB concept), not
  anything UI-facing. Only *display* labels are in scope for the
  future crew-terminology/theming roadmap item.

**`viewkit` — `hidden` field_type added to `FieldDef`**
- `FieldDef.__post_init__()`'s `valid_types` set didn't include
  `"hidden"` — needed so `project_id`/`parent_id` on tasks can be
  submitted with the form but never shown as an editable control.
- This is a `dev-utils` package change (Curator is currently its only
  consumer), not a Curator-only fix — added `"hidden"` to the set,
  one line.
- **Took two attempts to actually land**: the changedoc originally
  gave the wrong repo path (`~/projects/dev-utils/python/viewkit/models.py`,
  missing the inner package folder). The real path is
  `~/projects/dev-utils/python/viewkit/viewkit/models.py`. First
  "reinstall" silently reinstalled the same old unpatched code because
  the edit had gone nowhere. Confirmed now genuinely fixed and
  reinstalled — verified live via
  `python -c "import viewkit.models, inspect; print(inspect.getsource(...))"`.
- Changedoc (path corrected): `CHANGEDOC_VIEWKIT_HIDDEN_FIELD_TYPE.md`.
- `viewkit` is installed as a **regular (non-editable)** package in
  Curator's venv — any future `viewkit` change needs the same
  edit-then-`pip install --force-reinstall --no-deps <path>` dance.
  Noted as a candidate for switching to an editable install someday,
  not done.

**Tasks UI wiring — backend pieces (confirmed working end-to-end via curl)**
- `fieldkit_overrides.yaml`: new `projects.v_task_detail` entry —
  `project_id`/`parent_id` → hidden, `status_id` → `task_statuses`,
  `priority_id` → `priorities`.
- `_detail_form_fields.html`: new `hidden` field_type branch (no
  wrapping `.form-group`/label — just a bare `<input type="hidden">`).
- `panel.py`: `panel_new()` now forwards any query params into the
  (empty) record dict — e.g. `/panel/tasks/new?project_id=12`
  pre-fills the hidden `project_id` field. Deliberately entity-agnostic
  — no `if entity == "tasks"` branching; works for any future entity's
  hidden-field-prefill needs the same way. `tasks` added to
  `_FETCH_FUNCTIONS`.
- `tasks.py` (new file): `_fetch_task_for_display`, `GET
  /crew/tasks/{id}`, `POST /crew/tasks/save`, `POST
  /crew/tasks/{id}/save`, `DELETE /crew/tasks/{id}`. Mirrors
  `contacts.py`/`organizations.py` exactly — same `deps.py` helpers,
  same route-ordering rule, same error contract.
  - `_require_description()` is a small local required-field guard
    (tasks have no `name` field — they use `description`). **Verified
    against the live `api.save_task()` function body** (pulled via
    pgAdmin, since the on-disk `06b_api_projects.sql` doesn't contain
    the Tasks functions at all — stale file, flagged separately below)
    — the proc itself also requires `project_id` and `status_id`,
    neither of which is re-checked in Python; the proc is treated as
    the real authority for those two, and `call_proc_and_refetch`
    forwards its rejection message straight through if either is ever
    missing.
- `queries.yaml`: `tasks.for_project`/`tasks.for_task` — removed the
  stale `ORDER BY t.sort_order` (column no longer exists; caught this
  session when it produced a `QueryConfigError`, see "apply-time bugs"
  below — actually a different bug, the sort_order removal itself was
  correct from the start).
- `app.py`: `tasks` added to `_FIELDKIT_VIEWS`, `tasks` router
  registered.
- Changedoc: `CHANGEDOC_TASKS_UI_WIRING_BACKEND.md` (corrected
  mid-session to accurately document what's enforced in Python vs. in
  the proc).
- **Verified via `curl`**: `GET /panel/tasks/new?project_id=1`
  (authenticated) returns 200 with correctly rendered panel HTML —
  hidden `project_id`/`parent_id` fields present and correctly valued,
  Description/Notes as textareas, Status/Priority as populated selects
  with real lookup data (`backlog`/`blocked`/`cancelled`/`complete`/
  `in progress`; `high`/`low`/`normal`/`urgent`), Save/New/Exit buttons
  present. This is the first working proof of the full chain: viewkit
  → fieldkit_overrides.yaml → fieldkit.py → panel.py → template.
  **Not yet tested**: fetching an existing task, and a full save/delete
  round-trip — deliberately deferred until there's a real UI to click
  through rather than hand-built curl payloads.

**Apply-time bugs caught this session (pattern: content added, not replacing old)**
Recurred enough times to be worth naming as a pattern to watch for,
not just a list of one-offs:
- `datasheet.js`: a second, old, broken `deleteRow()` was left in place
  below the corrected one — later declaration silently won, meaning
  the fix was inert until caught and the duplicate removed.
- `app.py`: old `from curator.web.routes import (...)` line left in
  place alongside the new one that includes `tasks` — caused
  `Reimport` pylint warnings; fixed by deleting the old line.
- `tasks.py`: old `from fastapi.responses import JSONResponse` left in
  place below the correctly-ordered new import block — also, the
  module docstring was missing entirely from what landed on disk (the
  changedoc had one). Both fixed; file now pylint-clean (10.00/10).
- `_detail_form_fields.html`: this one was **Claude's mistake**, not an
  apply-time issue — the changedoc's AFTER block for this file had a
  correct single `{% endfor %}`, but the version that landed on disk
  had two, and tracing it back the second one wasn't in the actual
  changedoc text either — most likely introduced when the file was
  hand-typed/copied. Caused a `TemplateSyntaxError` at startup. Fixed
  by deleting the duplicate trailing `{% endfor %}`.

**Nested master-detail design doc — Tasks tab layout**
- Design doc written and refined:
  `nested_master_detail_design.md`.
- Shape: within the Tasks tab, a Tabulator list on top (existing child
  datasheet engine) and a real detail form below it (the *same* generic
  `_detail_panel_content.html`/`panel.py`/`detail-panel.js` machinery
  already used for the top-level panel, mounted a second time in a
  nested container) — not a new Tasks-specific form, not inline
  Tabulator cell editing.
- **Inline Tabulator row editing for Add was explicitly ruled out** —
  found via conversation search that this exact approach was tried and
  abandoned for the top-level Projects grid on 2026-06-28:
  `cellEdited` doesn't fire reliably for programmatically-added rows
  under `dblclick` edit-trigger mode. This is why Add
  Project/Contact/Organization all open a full detail panel today, and
  why Tasks won't attempt inline-row-add either.
- The Tasks tab is a **subform of the Project** — needs a static
  project-context label ("Project: WCYJ Refurbs") at the top,
  separate from the hidden `project_id` field that actually powers the
  save. Link-back-to-project version deferred; plain label first.
- Save behavior: after saving in the nested form, the Tabulator list
  above must refresh (`refresh_{containerId}()`, already stubbed in
  `datasheet.js`) — a save that doesn't visibly update the list reads
  as "did that actually save?"
- Subtasks (recursive nesting) explicitly deferred — get the one-level
  Project→Tasks version fully working first.
- Reflects a broader point worth remembering: this pattern works for
  *any* future entity with a proper SQL layer (view + `api.get_*_detail`/
  `save_*`/`delete_*`), not just Tasks — reinforces the original
  cross-deployment reusability goal, and keeps different views of the
  same data visually consistent by construction rather than by
  discipline.

**Default field values — explicitly deferred to future Configuration section**
- No existing mechanism in `FieldDef`/fieldkit/`viewkit` for a select
  field to have a default value (e.g. default task status for new
  tasks). Two candidate approaches sketched (reuse the query-param
  prefill mechanism with a new `is_default`-style lookup flag, or a new
  `default` attribute on `FieldDef`) — deliberately not built.

**Function-export tooling — design doc parked, direction decided**
- `function_export_tool_design.md` — captures the idea (per-function
  `.sql` files for the `api` schema, to fix the stale numbered-file
  problem and make functions easier to browse/diff/reuse), review of a
  starter script (needed rework to use `dbkit` instead of hardcoded
  credentials, handle `prokind`, handle overloaded-function-name
  collisions), evaluation of `pgschema` (ruled out — it's a
  Terraform-style migration tool, wrong shape for a documentation
  need) and `pg_extractor` (right direction, PostgreSQL-licensed,
  5-years-stale — plan is to fork and fix for current Postgres
  compatibility, possibly upstream via PR), and a new idea to feed the
  fork's output into "Dr. Filewalker" (the existing repo-walking doc-gen
  tool) rather than building a second, disconnected presentation layer.
  Dr. Filewalker's own planned multi-repo YAML config refactor would
  make this integration clean — the function-export output becomes
  just one more entry in that config. Nothing built; this is all design
  captured for later.

---

## What's next — priority order

**1. `detail-panel.js` multi-panel refactor**
Currently every panel-related function (`getPanel()`, `getForm()`,
`showPanel()`, `saveForm()`, the module-level `_saving` guard, the
Alt+S/Alt+N/Alt+X keyboard shortcuts) hardcodes "there is exactly one
detail panel on the page" — correct when it was written, but the
nested master-detail design needs a second, independent instance
(outer Project panel + nested Task panel) alive simultaneously.
`id="detail-form"` in particular can't be duplicated in valid HTML at
all. This needs to become "there can be one or more, each independent"
— container/root parameter threaded through every function, rather
than fixed document-wide selectors. Treat as its own design pass before
touching code, same as the master-detail layout got its own doc.

**2. Nested master-detail Tasks tab — actual implementation**
Once #1 is done: replace `_detail_panel_content.html`'s "Tasks — coming
soon" placeholder with the real layout from
`nested_master_detail_design.md` — project-context label, Tabulator
list (`_datasheet_with_header.html` include, `parent_field='project_id'`,
top-level tasks only via `parent_id IS NULL`), nested detail form below
it using the (by-then-refactored) shared panel machinery.

**3. Full round-trip verification of the Tasks backend**
Deferred from this session on purpose — once the UI exists, exercise
fetch-existing-task, save (both insert and update), and delete through
actual clicks rather than hand-built curl payloads. Also worth writing
`test_routes_tasks.py` at some point (flagged as a gap — no test file
exists for `tasks.py` yet, mirroring `test_routes_contacts.py`).

**4. `+ Add Task` wiring**
Depends on #1 and #2 being done — Add for Tasks was deliberately left
unspecified in the datasheet URL-fix changedoc, pending the nested
master-detail design (now settled): it opens the nested detail form in
new-record mode, not an inline Tabulator row (ruled out, see design doc
notes above).

**5. steward repo `.sql` files are more out of sync than previously known**
`06b_api_projects.sql` doesn't contain `api.save_task()`/
`api.delete_task()` at all, despite both existing and working live in
`wcyj` — confirmed by pulling the live function body directly via
pgAdmin this session. This was already a flagged gap from
2026-07-08, but it's now confirmed concretely for at least this one
function, not just suspected in general.

---

## Known bugs / flakiness (not fixed, deliberately parked)

**"New" button on project detail form — intermittent, not reproducible**
Clicking New (mouse) sometimes does nothing on the first click, works
on the second, or just works fine most of the time. No JS console
errors seen. Alt+N keyboard shortcut seems unaffected. Investigated
briefly (checked whether New is a submit-type button subject to the
same native-form-submission race Save needed guarding against — it's
not: `formkit.py` defines New as `type="button"` with no `form=`
attribute) but no root cause found, and Carolyn explicitly chose not to
keep chasing a non-reproducing flake. Revisit only if it becomes
reliably reproducible.

---

## Architectural decisions confirmed this session

- **`/crew/{entity}/...` route prefix is permanent**, even for future
  non-Curator business verticals built on this same codebase — it
  names the role-based DB access layer, not anything UI-facing.
- **Nested master-detail (list + form in the same tab, both using the
  same generic panel machinery)** is the pattern for any child entity
  with enough fields to warrant a real form — decided specifically
  against both inline-Tabulator-row-editing (known broken,
  2026-06-28) and pop-open-a-separate-panel (works, but visually
  disconnects the list from what's being edited).
- **`viewkit` changes require a manual edit + `pip install
  --force-reinstall --no-deps` + uvicorn restart** — not an editable
  install. Get the real path right: `~/projects/dev-utils/python/viewkit/`
  is the repo root; `viewkit/viewkit/models.py` is the actual package
  file, one level deeper than it looks.
- **`pg_extractor` (not `pgschema`) is the right base for the future
  function-documentation tool** — direction decided, nothing built.

## Suggested commit message

```
patch: tasks backend wiring, datasheet fixes, viewkit hidden field type

viewkit (dev-utils repo, separate commit):
- FieldDef.__post_init__: add "hidden" to valid_types set

Curator:
- datasheet.js: save/delete URLs /api/ -> /crew/; success checked via
  body.success !== false (not HTTP status) for save; status-code check
  (204 vs body) for delete; removed a stale duplicate deleteRow()
- detail-panel.js: found-and-fixed same success-flag bug in saveForm()
  (previously res.ok, which is true even on a proc-rejected save)
- fieldkit_overrides.yaml: projects.v_task_detail entry (project_id/
  parent_id hidden, status_id/priority_id select w/ lookup sources)
- _detail_form_fields.html: new hidden field_type render branch
- panel.py: panel_new() forwards query params into the record dict,
  entity-agnostically, so hidden fields can be pre-filled on a new
  record (e.g. ?project_id=12); tasks added to _FETCH_FUNCTIONS
- tasks.py: new route file — get/save/save-existing/delete, mirrors
  contacts.py/organizations.py exactly; payload verified against the
  live api.save_task() function body, not just handoff prose
- queries.yaml: tasks.for_project/for_task — drop stale
  ORDER BY t.sort_order
- app.py: tasks registered in _FIELDKIT_VIEWS and as a router

Verified via curl: GET /panel/tasks/new?project_id=1 returns correct
panel HTML end-to-end. Save/delete round-trip deferred until the UI
exists.

Design docs (no code): nested_master_detail_design.md,
function_export_tool_design.md
```
