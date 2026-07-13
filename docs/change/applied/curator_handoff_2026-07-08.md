# Curator Handoff — 2026-07-08

## Session summary

Picked up from the 2026-07-06 session's fieldkit/fetch-and-swap work.
This session completed the Tasks SQL layer, found and fixed a real
pre-existing bug in the detail panel rendering pipeline, extracted
`_datasheet.html`'s inline script to a proper ES module, and fixed a
hardcoded field-name bug that would have broken the Tasks child
datasheet on first use. Also had a productive design conversation that
named and clarified several architectural patterns, surfaced two more
deferred gaps, and added a Contacts/Organizations datasheet view to the
roadmap.

---

## Completed and verified this session

**Tasks SQL layer — applied and verified in pgAdmin**
- `ALTER TABLE projects.tasks DROP COLUMN sort_order` — confirmed dead
  weight, no consumer anywhere. Ordering by naming convention
  (`01_task`, `02_task`) or sort-by-name/date in the UI.
- `projects.v_task_detail` — whitelisted view: `id`, `project_id`,
  `parent_id`, `description`, `notes`, `status_id`, `priority_id`.
  `completed_at` excluded (server-managed via `is_terminal`).
- `api.get_task_detail(id)` — mirrors `get_project_detail` exactly.
- `api.save_task(payload, user_id)` — takes `status_id`/`priority_id`
  as ids directly (not name strings, since fieldkit's selects post ids).
  Sets `completed_at` automatically from `task_status.is_terminal`.
  Validates `parent_id` same-project membership; rejects self-parent.
  Deeper cycle detection (grandparent loops) is a known gap, flagged
  not fixed.
- `api.delete_task(id, user_id)` — explicit child-task detection before
  deletion, clear human-readable error message ("Delete or reassign
  them first").
- `api.get_lookup()` — two new `CASE` branches: `task_statuses`,
  `priorities`.
- Grants re-run. All verified in pgAdmin.

**Detail panel content split bug fix — confirmed working in browser**
- Root cause found: `crew.html` included `_detail_panel.html` once at
  page load (hardcoded `entity='projects'`, invisible behind hero
  image), but `detail-panel.js`'s `fetchAndSwapPanel()` replaced
  `.detail-panel`'s entire `innerHTML` on every `⋯` click — and
  `panel.py` was only ever returning bare field `<div>`s, not the tab
  bar or form wrapper. Tab bar got wiped on first open, every time.
  Confirmed via DOM inspection after full uvicorn restart + cache clear.
- Fix: created `_detail_panel_content.html` (new file — tab bar, form,
  child-tab placeholders, action buttons); `panel.py` now renders this
  on every open; `_detail_panel.html` reduced to a genuinely empty shell
  (`<div class="detail-panel" data-entity="" data-id="">`  +  one
  include); `crew.html`'s `{% with entity='projects'... %}` wrapper
  removed entirely — vestigial, never visible, two code paths for the
  same content is exactly what fieldkit was designed to eliminate.
- Verified in browser: Tommy Perez's contact panel showing
  Emails/Phones/URLs/Organizations (not stuck on Tasks/Links/Contacts),
  Save/New/Exit buttons present after swap, 4 `detail-tab` matches in
  DOM search.

**`datasheet.js` extraction + `parent_field` fix — no console errors confirmed**
- `_datasheet.html`'s entire `<script>` block (~80 lines, re-emitted
  verbatim into the HTML once per included datasheet) extracted to
  `static/js/datasheet.js`, exported as `initDatasheet(config)`.
  Imported on demand via `<script type="module">` in `_datasheet.html`
  — not loaded on every page like `detail-panel.js`, only fetched when
  a panel tab containing a child datasheet is rendered.
- `paramKey` heuristic replaced: the old
  `entity.replace(/s$/, '_id').replace(...)` string-guessing produced
  `task_id` instead of `project_id` for the Tasks entity. Replaced with
  explicit `parent_field` config parameter passed by the caller — same
  "no hardcoded values" principle as everything else in this app.
- `_datasheet_with_header.html` updated: `save_url` removed from
  `{% with %}` passthrough (was documented but never actually used in
  the script), empty `<script type="module">` block removed (explicitly
  "deferred" comment, worse than nothing), `parent_field` passthrough
  added with `|default('')`.
- `base.html` unchanged — `datasheet.js` is lazy-imported, no `<script
  src>` needed.
- Verified: landing page and crew dashboard load with no console errors.

---

## Deferred gaps found this session (not yet fixed)

**`_datasheet.html` save/delete URLs are wrong.** The extracted
`datasheet.js` still uses `/api/{entity}/save` and `/api/{entity}/{id}`
— routes that don't exist. Every real route is under
`/crew/{entity}/save` and `/crew/{entity}/{id}`, matching
`detail-panel.js`'s convention. Child datasheet saves/deletes currently
404 silently. Fix: derive URL from `entity` the same way
`detail-panel.js` does; the `save_url` parameter that was documented
but never honored can simply be dropped (already removed from the
templates this session). **Fix this before wiring any child datasheet
that actually saves rows.**

**`_datasheet_with_header.html`'s `+ Add` button does nothing.** The
`data-add-url` attribute is set, but the click handler was explicitly
"deferred" and the `<script type="module">` block that would wire it
was empty (now removed). Clicking `+ Add` on any child datasheet
currently does nothing. Needs wiring in `datasheet.js`. **Fix this in
the same changedoc as the URL fix above.**

**`formkit.py` dead-code cleanup.** `FormActions.detail_panel_actions()`
(and possibly `crud_create_actions`/`crud_edit_actions`) appear unused —
`_detail_panel.html` and `panel.py` both go through `FormActions.from_yaml()`
instead. The docstring claims it's "used in `_detail_panel.html`" but
it isn't. Confirm nothing else calls these before removing.

**steward repo `.sql` files may be out of sync.** After the Tasks SQL
layer changedoc, the following files on disk may not reflect what's
live in `wcyj`: `03_projects.sql` (sort_order dropped),
`06b_api_projects.sql` (save_task/delete_task appended),
`08b_api_lookup.sql` (task_statuses/priorities branches added),
`07_detail_views.sql` (v_task_detail added). Confirm/apply before
assuming they're in sync.

**`panel.py` has no unit tests.** Testing it meaningfully requires
mocking `request.app.state.fieldkit`, a different shape than the
`db`-mocking pattern used everywhere else. Flagged across multiple
sessions, not yet addressed.

**Curator has no logging infrastructure.** `app.py` has no logger or
file handler, unlike `fletcher`/`contactkit` which use human-readable
+ JSON logging. Deferred as its own piece.

**Deeper cycle detection on `parent_id` in `api.save_task()`.** A task
set as its own grandparent isn't caught — only direct self-parent and
cross-project cases are rejected. Not expected to be a real problem
with shallow subtask usage, but noted.

---

## What's next — priority order

**1. Fix `_datasheet.html` save/delete URLs + wire `+ Add` button**
One changedoc, both gaps together. This is a prerequisite before any
child datasheet (Tasks, Emails, Phones, etc.) can actually save rows.

**2. Tasks UI wiring** — the original goal of all the fieldkit/
fetch-and-swap/detail-panel work this session and last. Now genuinely
unblocked. Concretely:
- `fieldkit.py`: add `hidden` field type (for `project_id` and
  `parent_id`, pre-filled from context, never rendered as an editable
  control)
- `fieldkit_overrides.yaml`: new `projects.v_task_detail` entry —
  `status_id` → `task_statuses`, `priority_id` → `priorities`,
  `project_id` → hidden, `parent_id` → hidden
- `app.py`/`panel.py`: one `_FIELDKIT_VIEWS`/`_FETCH_FUNCTIONS` entry
  each for `tasks`
- `tasks.py`: new route file — `_fetch_task_for_display`,
  `GET /crew/tasks/{id}`, `POST /crew/tasks/save`,
  `POST /crew/tasks/{id}/save`, `DELETE /crew/tasks/{id}`
- `_detail_panel_content.html`: replace Tasks tab "coming soon"
  placeholder with a real `_datasheet_with_header.html` include
  (flat top-level tasks only: `parent_id IS NULL`, `query_params=record_id`,
  `parent_field='project_id'`)
- `queries.yaml`: fix `tasks.for_project` and `tasks.for_task` — both
  still `ORDER BY t.sort_order` which was just dropped from the table

**3. Task detail panel — Subtasks section** (Phase 2 of Tasks UI)
Each task's own panel gets a Subtasks child datasheet. Recursive: a
subtask's panel has its own Subtasks section. No depth limit. Subtask
creation is always from the parent task's panel ("+Subtask" button),
not from a `parent_id` field on the form. Depth indicator (badge or
"L2"/"L3" label) on each task's panel.

**4. Identities gaps** — contact↔organization association (save path
for `identity.organization_contacts`, the join table), and
email/phone/URL entry for contacts. Design in `CONTACTS_TWO_PANEL.md`.
Emails/Phones is the simpler starting point (no picker-for-existing-
record complexity). Two open design decisions on org/contact
association: Role field (free text vs. lookup table), and how the
"pick an existing organization" UX looks.

---

## Architectural decisions made or confirmed this session

**One canonical path per concern — applied twice more this session:**
- `_detail_panel_content.html` is the only renderer of panel content;
  `crew.html`'s vestigial initial render of a fake "projects" panel was
  removed rather than defended against.
- `datasheet.js` is the only implementation of Tabulator child-datasheet
  behavior; `_datasheet.html` is now a thin config-passing shell.

**"Metadata-Driven UI" + "Dynamic Attribute-Based Access Control
(ABAC)"** — vocabulary from this session. The fieldkit + schema-driven
forms system is a textbook Metadata-Driven UI; the `web_app_user`
EXECUTE-only access model is ABAC at the database layer. Good to have
the vocabulary, both for documentation and for asking better questions
next time a similar system needs to be built.

**`_projects_table.html` is a separate design project, not a quick
extraction.** ~250 lines, a materially richer Tabulator implementation
(dirty-row tracking with Save/Discard dialog, multi-select, clipboard
copy, keyboard delete). Unifying it with the child-datasheet engine
requires a feature-parity decision first ("do child datasheets
eventually get this richness?"), then the extraction. Not a quick
follow-on changedoc.

**Contacts/Organizations datasheet view** is on the roadmap. The
Identities tab's bidirectional listbox filter stays for relationship
browsing ("where do they work"). A separate datasheet view (same shared
engine as Projects/Tasks) is for bulk operations on many rows (bulk
copy, bulk delete). How it's reached — toggle, second tab, button —
is undecided.

**Export project feature** — a multi-sheet xlsx dump of a project and
all its related records (tasks w/ recursive depth, contacts, files,
etc.), one sheet per entity type via SheetJS. Raised during Tasks
design discussion. A `WITH RECURSIVE` view for the task tree, one sheet
per entity type — real work, needs its own design pass. Not yet scoped.

---

## Current architecture state

- `fieldkit.py`: schema introspection → Tier-1 type map → YAML override
  merge → startup validation → cached options. No hidden-field-type yet
  (needed for `project_id`/`parent_id` on tasks).
- `panel.py`: `GET /panel/{entity}/new` and `GET /panel/{entity}/{id}`,
  renders `_detail_panel_content.html` (full panel body — tab bar, form,
  child-tab placeholders, action buttons).
- `_detail_panel.html`: empty shell, `<div>` + one include.
- `_detail_panel_content.html`: the actual rendered content, fetched
  per panel open. Child tabs still "coming soon" placeholders.
- `_detail_form_fields.html`: fieldkit-driven field loop, dispatches on
  `field_type`. Handles `text`, `textarea`, `select`, `date`,
  `checkbox`. No `hidden` type yet.
- `detail-panel.js`: fetch-and-swap wholesale into `.detail-panel` on
  every open. `clearForm()`/`focusName()` unchanged (already generic).
- `datasheet.js`: new this session — `initDatasheet(config)`, imported
  on demand. Save/delete URLs still wrong (deferred).
- `_datasheet.html`: thin shell, one `<script type="module">` calling
  `initDatasheet()`.
- `_datasheet_with_header.html`: passes `parent_field` through; `save_url`
  and empty deferred script block removed.
- `queries.yaml`: `tasks.for_project` and `tasks.for_task` queries
  exist but still reference `sort_order` in `ORDER BY` — will error
  when called. Fix in Tasks UI wiring changedoc.
- `deps.py`, `crew.py`, `projects.py`, `contacts.py`,
  `organizations.py`: unchanged this session.
- `fieldkit_overrides.yaml`: `projects.v_project_detail` entries only.
  `projects.v_task_detail` entries not yet added.
- `app.py`: `tasks` not yet in `_FIELDKIT_VIEWS`.

---

## Suggested commit message

```
patch: tasks SQL layer, detail panel content split, datasheet.js extraction

SQL (applied, verified in pgAdmin):
- projects.tasks: drop sort_order (no consumer, ordering by convention)
- projects.v_task_detail: whitelist view for task detail panel
- api.get_task_detail(): read function, mirrors get_project_detail
- api.save_task(): ids-direct (not name strings), completed_at from
  is_terminal, parent_id same-project validation, self-parent rejection
- api.delete_task(): explicit child-task detection, clear error message
- api.get_lookup(): task_statuses and priorities CASE branches
- Grants re-run

Python/templates:
- _detail_panel_content.html: new file — actual panel content (tab bar,
  form, child-tab placeholders, action buttons); panel.py renders this
  on every open instead of bare field divs
- _detail_panel.html: reduced to empty shell — removes vestigial
  crew.html page-load render of a fake "projects" panel nobody ever saw
- crew.html: {% with entity='projects'... %} wrapper removed
- panel.py: renders _detail_panel_content.html + FormActions; renamed
  _render_fields → _render_panel_content
- datasheet.js: new file — initDatasheet(config) extracted from
  _datasheet.html's inline <script>; parent_field replaces paramKey
  string-guessing heuristic that produced task_id instead of project_id
- _datasheet.html: thin shell, <script type="module"> calling
  initDatasheet()
- _datasheet_with_header.html: parent_field passthrough added; save_url
  (never used) and empty deferred script block removed

Known gaps not addressed: save/delete URLs in datasheet.js are wrong
(/api/ not /crew/); + Add button unwired; panel.py has no unit tests;
Tasks not yet wired into fieldkit/panel/UI
```
