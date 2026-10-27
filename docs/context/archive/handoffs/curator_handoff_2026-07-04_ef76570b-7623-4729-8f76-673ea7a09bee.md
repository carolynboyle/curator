# Curator Handoff — 2026-07-04

## Session summary

Picked up from the 2026-07-01 session's `crew.py` split. This session:
(1) applied and verified that split, (2) built and verified the
fetch-and-swap detail panel's read path (views + `api.get_*_detail()`
functions), (3) found and fixed three real bugs surfaced by that work,
and (4) did a full `pylint` cleanup pass, ending at a clean 10.00/10 with
24/24 tests passing.

---

## Completed and verified this session

**`crew.py` split — confirmed applied and working**
- Split into `crew.py` (dashboard shell + `/api/query` endpoint),
  `projects.py`, `contacts.py`, `organizations.py` route files, per the
  2026-07-01 changedoc.
- Verified via `pytest` (22/22 at the time) and a full browser smoke
  test — dashboard loads for all roles, existing Save/New/Exit still
  work by click and Alt-key for all three entities.

**Detail-view read path — SQL, applied and verified in pgAdmin**
- `07_detail_views.sql`: `projects.v_project_detail`,
  `identity.v_contact_detail`, `identity.v_organization_detail` — each a
  deliberate whitelist of exactly the form-editable columns for that
  entity (no `id`, no `*_by`, no server-generated fields like
  `projects.projects.slug`).
- `07_detail_api.sql`: `api.get_project_detail(id)`,
  `api.get_contact_detail(id)`, `api.get_organization_detail(id)` —
  `LANGUAGE sql`, return `JSONB` via `row_to_json`, `NULL` on no match.
  Grants re-run (`06d_api_grants.sql`'s wildcard is a snapshot, doesn't
  retroactively cover new functions).
- Verified directly in pgAdmin: `SELECT api.get_project_detail(23)`
  returns real data, `SELECT api.get_project_detail(999999)` returns
  `NULL`, both without error. Grants confirmed via
  `information_schema.routine_privileges`.

**Detail-fetch functions wired to the new read path**
- `deps.py` gained `_fetch_json_scalar()` (generic single-JSON(B)-column
  unwrap, handles `NULL`/string/dict cases) with `call_proc()` refactored
  as a thin wrapper over it.
- `projects.py`/`contacts.py`/`organizations.py`'s
  `_fetch_*_for_display()` functions now call `api.get_*_detail()`
  instead of querying tables directly — closes the `web_app_user`/
  api-only inconsistency that existed since the original `crew.py`.
- **Response shape change, deliberate:** `_fetch_project_for_display()`
  no longer returns joined `type`/`status` name strings or `slug` —
  `v_project_detail` is editable-fields-only. Confirmed nothing
  downstream reads those (checked `detail-panel.js`'s `populateForm()`
  directly). Contacts/organizations unaffected — their views match the
  old query shape exactly.
- Five existing tests updated to match the new `fetch_one()` mock shape
  (wrapped in `{"get_x_detail": ...}` instead of bare values); one new
  test class (`TestFetchJsonScalar`) added to `test_deps.py`.

**Three real bugs found and fixed** (all pre-existing, none introduced by
this session's work — surfaced because this was the first time anyone
exercised these code paths):
1. `run_query()` called `_query_loader.build()`, which doesn't exist on
   `viewkit.QueryLoader` — correct method is `.sql()`. This broke every
   child-datasheet tab (Tasks, Emails, Phones, URLs, Organizations) from
   the moment the endpoint was written; nothing caught it because those
   tabs are all still static "coming soon" placeholders in
   `_detail_panel.html`, so nothing had ever called the endpoint.
2. `queries.yaml`'s `tasks.for_project`/`tasks.for_task` selected
   `t.created_at` without the `::text` cast every other column in those
   queries already had — caused `TypeError: Object of type datetime is
   not JSON serializable`. Fixed the cast in both queries, and
   additionally wrapped `run_query()`'s response in `jsonable_encoder()`
   as a backstop for any future query that misses the casting
   convention.
3. `crew.py`'s pylint-exception comment for `_render_crew_dashboard_html`
   (6 parameters) was sitting above the wrong function (`crew_dashboard`,
   5 parameters) and was prose, not a real `# pylint: disable=...`
   directive — never actually suppressed anything. Fixed by moving a real
   disable directive onto the function that needed it.

**Pylint cleanup — `contacts.py`/`organizations.py` duplication**
- Extracted the repeated "call proc → check envelope → re-fetch →
  return" pattern (flagged by `R0801`) into `call_proc_and_refetch()` in
  `deps.py` — one canonical implementation instead of near-identical
  copies in `projects.py`, `contacts.py`, `organizations.py` (folded
  `projects.py` in too for full consistency, even though pylint's
  similarity threshold hadn't flagged it there).
- That extraction itself hit the same too-many-arguments threshold (6
  genuinely-necessary parameters) — given a proper disable directive
  with reasoning this time, not another misplaced comment.
- **`pylint src/` now at 10.00/10. `pytest` at 24/24.** Both confirmed
  clean as of the end of this session.

---

## Current architecture state

- `crew.py`: dashboard shell + `/api/query` generic endpoint only.
- `projects.py`/`contacts.py`/`organizations.py`: full CRUD per entity,
  reads via `api.get_*_detail()`, writes via `api.save_*()`/
  `api.delete_*()`, save routes using the shared
  `call_proc_and_refetch()` helper.
- `deps.py`: `get_db`/`get_config`/`get_db_direct` (dependency injection),
  `_fetch_json_scalar`/`call_proc`/`call_proc_and_refetch` (shared
  proc/read helpers).
- Detail panel itself (`_detail_panel.html`, `detail-panel.js`) is
  **unchanged** this session — still the single server-rendered
  projects-shaped form, still relabeled/repopulated in place by JS rather
  than fetched-and-swapped. That work hasn't started yet.
- Child datasheet tabs (Tasks, Emails, Phones, URLs, Organizations) are
  still static placeholders. The `/api/query` endpoint that will
  eventually feed them now actually works (bugs 1 and 2 above), but
  nothing in the UI calls it yet.

---

## Next session's stated priority: get Tasks working

Explicit steer from the user: **project tasks are the thing that
actually proves Curator is useful for project tracking**, more than the
in-progress fetch-and-swap/field-schema generalization work. Worth
sequencing next-session work around that rather than mechanically
continuing the fetch-and-swap plan in its original order.

**What Tasks needs, roughly, based on what's already confirmed working
and what isn't:**
- `api.*` save/delete functions for `projects.tasks` — **don't exist
  yet**. None of `06a`/`06b`/`06c_api_identity.sql` touch tasks at all.
  This is the biggest gap.
- `tasks.for_project`/`tasks.for_task` in `queries.yaml` — confirmed
  working now (this session's bug fixes), but only for reads via the
  generic `/api/query` endpoint. No write path exists yet.
- The Tasks tab in `_detail_panel.html` is a static placeholder — needs
  actual markup, presumably a datasheet (Tabulator, matching the
  existing pattern) wired to `/api/query/tasks/for_project`.
- `projects.tasks.sort_order` — confirmed dead/unused this session
  (zero live call sites), and confirmed unnecessary going forward per
  earlier discussion (`01_first task`/`02_second task` naming convention
  handles manual ordering without a dedicated column). Worth dropping
  before any task-save proc gets written that might otherwise start
  referencing it.
- Subtask support (`parent_id`) already exists in the schema and in
  `queries.yaml`'s `for_task` query — worth deciding whether v1 of task
  save/UI handles subtasks or defers them.

**Not yet started, still on the books from before, lower priority than
Tasks per this steer:** `api.get_field_schema()`, `api.get_lookup()`,
`fieldkit.py`, the YAML field-override file, the `/panel` route, and the
`_detail_panel.html`/`detail-panel.js` fetch-and-swap work itself. All of
this remains necessary eventually — contacts/organizations still show
the Projects form shape today — but Tasks is the more convincing
near-term win.

---

## Suggested commit for this session

Everything above is applied and verified (pylint 10.00/10, pytest
24/24). One commit, or split by logical chunk if preferred — up to you.
Nautical vocabulary per your convention:

```
patch: wire detail-panel reads through api.get_*_detail(), fix
QueryLoader.build()/datetime serialization bugs, extract
call_proc_and_refetch to eliminate route duplication

- 07_detail_views.sql / 07_detail_api.sql: v_*_detail views and
  api.get_*_detail() functions, closing the web_app_user/api-only gap
- deps.py: _fetch_json_scalar, call_proc refactored onto it,
  call_proc_and_refetch extracted from projects/contacts/organizations
- fix: QueryLoader.sql() not .build() in run_query()
- fix: cast created_at::text in queries.yaml tasks queries; wrap
  run_query() response in jsonable_encoder() as a backstop
- fix: misplaced pylint disable comment on _render_crew_dashboard_html
- pylint src/ clean at 10.00/10, pytest 24/24
```
