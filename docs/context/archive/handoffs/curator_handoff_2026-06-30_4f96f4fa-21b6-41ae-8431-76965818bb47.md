# Curator Handoff — 2026-06-30

## Session Summary

Full day session. Migrated all project CRUD from Python-generated SQL into
PostgreSQL stored procedures, fixed a JS form-submission race condition that
was silently swallowing saves, completed a full pylint cleanup pass across
the entire `src/` tree, established the unit test infrastructure, and
resolved a multi-step pytest environment configuration problem. Score at
end of session: 9.87/10 (only known, deliberate exception documented in
code).

---

## What Was Accomplished This Session

### 1. Project CRUD → PostgreSQL stored procedures (`crew.py`)

All save/delete logic moved out of Python into `api` schema procs. Python
routes are now thin messengers: unwrap JSON from the browser, translate
`type_id`/`status_id` integers to name strings (the procs take names, not
ids — keeps the browser from exposing internal ids), call the proc, check
`success`, return either the flat record (success) or
`{success: false, message, data}` (failure).

Two new private helpers established as the reusable pattern for all future
entities (Contacts, Tasks):

- `_call_proc(db, sql, params)` — calls any `api.*` proc and unwraps its
  JSONB envelope, handling both the already-decoded-dict and raw-JSON-string
  cases from dbkit (encoding-dependent, see prior handoff notes).
- `_resolve_type_status_names(db, type_id, status_id)` — translates FK
  integers to name strings before the proc call.

**Response contract (decided this session, must not change):**
- Success: flat record JSON, no `success` key. HTTP 200.
- Failure: `{"success": false, "message": "...", "data": ...}`. HTTP 200.
- The JS `saveForm()` in `detail-panel.js` checks `body.success === false`
  to distinguish these — NOT `res.ok` (which is always true for 200s).
  Changing either side of this contract without updating the other will
  cause silent failures.

**`data` field on failure responses:** When `api.save_project` rejects a
duplicate name, it now returns `{"conflicting_id": N}` in the `data` field.
Python routes forward this through unchanged. The JS currently only reads
`message` for the alert — `data.conflicting_id` is available for a future
"open existing record / rename this one" dialog but that dialog hasn't been
built yet.

**`_make_slug()` removed** — slug generation now happens inside
`api.save_project`. `re` import removed as a consequence.

**`_render_crew_dashboard_html` split out from `crew_dashboard`** — these
were genuinely different jobs (serve JSON for Tabulator vs. render a full
HTML page) sharing one function. Now separated. `_ROLE_TABS` and
`_DEFAULT_TABS` promoted to module-level constants (read-only, safe to
share across requests). `_render_crew_dashboard_html` takes 6 parameters
(one over pylint's default threshold of 5) — all 6 genuinely needed,
restructuring would add indirection without clarity. Decision documented in
a comment above the function definition in `crew.py`.

### 2. JS save-race condition fixed (`detail-panel.js`)

**Root cause:** The Save button is `type="submit"` with `form="detail-form"`
(per `forms.yaml`). Clicking it triggered both the JS click-delegation
handler (`handleSave()`) AND native browser form submission. Since
`#detail-form` has no `action` or `method`, native submission fell back to
`GET /crew?name=...&type_id=...` — identical URL to the current page but
with all form fields appended as query params. `crew_dashboard` silently
ignored those params and re-rendered the page unchanged. Symptom: "nothing
happens when I click Save."

**Fix (two layers, belt-and-suspenders):**
1. `e.preventDefault()` added to the `btn-save` click branch in the
   delegated click listener.
2. A `document.addEventListener('submit', ...)` handler added, scoped to
   `e.target.id === 'detail-form'`, calling `e.preventDefault()` and
   `handleSave()`. This is the more robust fix — catches Enter-key
   submission and any other native submit trigger, not just the one button
   click.

**`res.ok` vs `success` flag bug also fixed:** `saveForm()` previously
checked `if (res.ok)` to distinguish success from failure — but routes
return HTTP 200 for both. The failure branch (`alert(err.detail || 'Save
failed')`) was dead code. Fixed to parse the body first and check
`body.success === false`. Also fixed `err.detail` → `err.message` to match
the actual response envelope shape.

### 3. `api.save_project` — conflicting_id on duplicate name

The duplicate-name conflict check previously did `SELECT 1 ... EXISTS`,
discarding the conflicting record's id. Changed to `SELECT id INTO
v_conflict_id` (same query, zero extra cost) and included that id in the
proc's `data` field on rejection. New variable `v_conflict_id BIGINT`
declared in `DECLARE` block. Applied to both the INSERT and UPDATE conflict
check branches. Python routes forward `data` through on failure (was
previously discarded). Groundwork for a future "open existing record"
dialog — the id is now available in the browser even though the dialog
hasn't been built.

### 4. Pylint cleanup — full `src/` pass

All files in `src/` brought to 9.87/10 (only known deliberate exception
remaining). Changes by file:

- **`config.py`** — missing final newline
- **`formkit.py`** — trailing whitespace (16 lines), missing final newline,
  `import yaml` moved to module level, `FormAction.__init__` refactored from
  7 keyword args to single dict parameter (Option B: named instance
  attributes preserved internally, only constructor signature changes),
  `too-few-public-methods` disabled on both `FormAction` and `FormActions`
  with inline explanations
- **`exceptions.py`** — `pass` removed from all three exception classes
  (docstring alone is valid class body), missing final newline
- **`curator/__init__.py`** — missing final newline
- **`middleware.py`** — `import logging` moved to module level, `too-few-
  public-methods` disabled on `SessionMiddleware` with explanation
  (`BaseHTTPMiddleware` contract requires exactly one `dispatch()` method)
- **`deps.py`** — `get_db()` refactored from manual `__aenter__`/`__aexit__`
  calls to `async with AsyncDBConnection() as db: yield db`. `get_db_direct()`
  keeps manual `__aenter__()` with inline disable and explanation (entry/exit
  are deliberately split across caller and callee — `async with` can't express
  that)
- **`crew.py`** — import reorder (`viewkit` before `curator.*`), `raise ...
  from exc` on both exception branches in `run_query`, unused `role` param
  removed from `save_new_project`, `_render_crew_dashboard_html` split,
  `_ROLE_TABS` as module constant, line-too-long and trailing whitespace fixed
- **`auth.py`** — `unused-argument` disabled on `login_page`'s `request`
  param with explanation (FastAPI requires it in signature), `too-many-locals`
  disabled on `login_submit` with explanation (all 11 locals genuinely needed),
  `broad-except` disabled on both exception handlers with explanations
- **`landing.py`** — blank line added between stdlib and third-party imports
- **`web/__init__.py`**, **`web/routes/__init__.py`**, **`db/__init__.py`**
  — missing final newlines (fixed directly, no changedocs needed)

### 5. Unit test infrastructure established (`tests/unit/test_routes_crew.py`)

First real test file in the project. 9 tests, all passing. Pattern
established for all future route unit tests:

- Database is mocked via `SimpleNamespace(fetch_one=AsyncMock(...))` — no
  real PostgreSQL connection needed
- Route functions called directly with keyword arguments
  (`crew.save_new_project(request=request, db=db)`) — keyword args are
  mandatory to catch signature changes loudly rather than silently
- `make_mock_request(body, user_id)` and `make_mock_db_for_proc(envelope)`
  are the two reusable fixture builders

**Tests cover:**
- `_call_proc` envelope unwrapping — both the already-decoded-dict case and
  the raw-JSON-string case (the encoding-ambiguity that was flagged as
  unverified in the prior session)
- Empty/whitespace/missing name guard on `save_new_project` — confirms
  early return before any DB call
- Same guard on `save_project` (update route)
- Proc rejection forwarding — confirms `{success, message, data}` all pass
  through correctly, including `data.conflicting_id`
- Success response shape — confirms flat record with no `success` key,
  pinning down the exact contract `saveForm()` depends on

**Key lesson from this session:** Always use keyword arguments when calling
route functions directly in tests. Positional calls bind to wrong parameters
silently when signatures change — we spent significant time debugging this
exact failure mode when `save_new_project` still had a `role` parameter that
a previous changedoc had removed but hadn't been applied to the live file.

### 6. Pytest environment

- `pytest` was previously installed in `/opt/venvs/tools/` (shared tools
  venv) rather than the project's `.venv`. Removed from tools venv, added
  to `[dev]` extras in `pyproject.toml`.
- Install with: `pip install -e ".[dev]"` (not just `pip install -e .`)
- Run with: `pytest` (now resolves to `.venv/bin/pytest` correctly)
- `hash -r` may be needed after changing venv pytest location to clear
  bash's command path cache

### 7. Task tracking in PostgreSQL

44 task records inserted into `projects.tasks` for project_id=1 (Curator),
one per changedoc/handoff file in `docs/change/`. All marked complete
(`status_id=4`, `completed_at=NOW()`). Going forward: new changedocs get
a task record when created, marked complete when applied.

`docs/change/applied/` folder created — all previously applied changedocs
moved there. Anything not in `applied/` has not yet been applied.

### 8. `dbkit` `client_encoding` fix

Confirmed done and committed to dev-utils `main` branch. Both
`psycopg.connect()` and `psycopg.AsyncConnection.connect()` now pass
`client_encoding="utf-8"`. No action needed.

---

## Files Changed This Session

### Curator repo (`src/`)
- `src/curator/config.py` — newline
- `src/curator/exceptions.py` — pass removal, newline
- `src/curator/formkit.py` — full refactor (see pylint section)
- `src/curator/__init__.py` — newline
- `src/curator/web/middleware.py` — import, pylint disable
- `src/curator/web/deps.py` — async with refactor
- `src/curator/web/routes/crew.py` — full proc migration + pylint cleanup
- `src/curator/web/routes/auth.py` — pylint disables
- `src/curator/web/routes/landing.py` — import order

### Static
- `static/js/detail-panel.js` — submit-race fix, res.ok → success flag fix

### Tests
- `tests/unit/test_routes_crew.py` — new file, 9 unit tests
- `tests/test_routes_crew.py` — deleted (was a duplicate in wrong location)
- `tests/repro.py` — diagnostic script used during debugging, can be
  deleted or kept as an example of the standalone-reproduction pattern

### Database (steward repo — wcyj database)
- `06_api.sql` — `api.save_project` updated: `v_conflict_id BIGINT` variable
  added, both conflict-check branches now return `conflicting_id` in `data`

---

## Deferred Items

### Before Contacts/Tasks forms are wired (do these first)

**1. `queries.yaml` column name mismatches**
- `contact_emails.for_contact` selects `email` and `email_type` — actual
  columns are `address` and `label`
- `contact_phones.for_contact` selects `phone_number` and `description` —
  actual columns are `number` and `label`
- Fix: update `queries.yaml` to use actual column names. No schema change
  needed (decision made this session: the column names are fine as-is, the
  queries were just wrong)

**2. Lowercase constraint on `app_user.username`**
```sql
ALTER TABLE identity.app_user
    ADD CONSTRAINT chk_username_lowercase
    CHECK (username = LOWER(username));
```
Also update `02_identity.sql` canonical source.

### After Contacts/Tasks forms are working

**3. Project Templates**
Design doc at `docs/design/project_templates_design.md` (created this
session). Schema: two additive columns on `projects.projects`:
```sql
ALTER TABLE projects.projects ADD COLUMN is_template BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE projects.projects ADD COLUMN source_template_id BIGINT
    REFERENCES projects.projects(id) ON DELETE SET NULL;
```
Proc: `api.create_project_from_template` — copies task tree with
parent_id remapping and status reset to "not started". Open question:
whether role-filtered views need `WHERE is_template = false`.

**4. Row-Level Security**
Must be implemented before any public deployment. Pattern already
scaffolded: `SET LOCAL app.current_user_id` per transaction, RLS policies
read via `current_setting('app.current_user_id', true)`. Explicitly
deferred until after Felipe demo milestone.

**5. Contacts and Tasks forms**
Design the visual layout first (fields, child datasheets, tab structure),
then wire to PostgreSQL procs using the same pattern established for
projects this session. **Do not write backend code until form layout is
settled** — the form shape determines what the procs need to accept.

**6. UI gaps (not blocking Felipe demo)**
- Logout button in nav (currently must navigate to `/auth/logout` directly)
- `/crew?role=captain` accessible directly by any authenticated user
  regardless of their actual crew_role (landing page hides the card, but
  the URL is not protected — RLS will eventually close this properly)
- Dark theme text color issues on Captain page
- Clipboard copy button above grid (when rows selected)
- Child datasheets (Tasks, Emails, Phones, URLs, Orgs) — all "coming soon"
- Mobile: Identities tab two-panel layout needs toggle for small screens

**7. `project_files` and `task_files` tables not yet created**
The schema design docs reference these tables but they were never run on
`steward`. Before file metadata can be attached to projects or tasks, the
`CREATE TABLE` statements need to be written and executed, and the canonical
SQL files (`03_projects.sql`) updated to include them. No UI or proc work
until the tables exist.

### Infrastructure (longer term)
- Docker containerization on Hetzner VPS
- PostgreSQL streaming replication (homelab `steward` → VPS standby)
- Durin Observatory monitoring dashboard
- `curator_init.py` script for config file setup after mesh/IP changes

---

## Patterns Established This Session

### Proc-call pattern (reuse for Contacts, Tasks, everything)

```python
# In the route:
envelope = await _call_proc(
    db,
    "SELECT api.save_contact(%s, %s)",
    (json.dumps(payload), user_id),
)
if not envelope.get("success"):
    return JSONResponse({
        "success": False,
        "message": envelope.get("message"),
        "data": envelope.get("data"),
    })
# On success, re-fetch the full record and return it flat:
record = await _fetch_contact_for_display(db, envelope["data"]["id"])
return JSONResponse(dict(record))
```

### Response contract (must not change)
- **Success:** flat record, no `success` key, HTTP 200
- **Failure:** `{"success": false, "message": "...", "data": ...}`, HTTP 200
- **JS side:** `body.success === false` distinguishes these, never `res.ok`

### Unit test pattern (reuse for future route tests)
```python
# Always use keyword arguments:
response = await crew.save_new_project(request=request, db=db)

# Mock the DB:
db = SimpleNamespace(fetch_one=AsyncMock(return_value={
    "some_proc": {"success": True, "data": {"id": 1}, "message": None}
}))

# Mock the request:
request = SimpleNamespace(
    json=AsyncMock(return_value={"name": "Test"}),
    state=SimpleNamespace(user={"user_id": 1}),
)
```

---

## Next Session — Recommended Starting Point

1. Run `pytest` to confirm 9/9 still passing
2. Run `pylint src/` to confirm 9.87/10 (only the known `_render_crew_
   dashboard_html` too-many-arguments exception)
3. Commit everything from this session:
   ```
   git add -A
   git commit -m "refit: proc-based CRUD, JS save fix, pylint cleanup, unit tests"
   git push
   ```
4. Fix `queries.yaml` column mismatches (quick, no schema change)
5. Add lowercase constraint on `app_user.username`
6. Begin Contacts/Tasks form layout design (visual first, no backend yet)
