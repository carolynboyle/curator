# Curator Handoff — 2026-06-29

## Session Summary

Full day session. Built the PostgreSQL api schema with stored procedures,
implemented session-based authentication, wired the login dialog, and
proved the full auth flow end to end in the browser with two different
users landing on their correct crew views.

---

## What Was Accomplished This Session

### Schema Changes (steward repo — wcyj database)

**`02_identity.sql`** — updated canonical version:
- Added `crew_role_id` (nullable BIGINT FK → `identity.crew_role`) to
  `identity.app_user`
- Added `identity.app_user_sessions` table (server-side session store)
- Updated GRANTs: sessions gets SELECT, INSERT, UPDATE, DELETE for steward

**`06_migration_app_user.sql`** — one-time migration (already run on live DB):
- `ALTER TABLE identity.app_user ADD COLUMN crew_role_id`
- `CREATE TABLE identity.app_user_sessions`
- GRANTs for steward on sessions table

**`06_api.sql`** — new file, new schema:
- `CREATE SCHEMA api`
- `CREATE ROLE web_app_user` (EXECUTE on api.* only, no direct table access)
- `api.create_session(user_id, remember_me, ip, user_agent)` → session token
- `api.login(username, password, remember_me, ip, user_agent)` → JSONB
  - bcrypt verify via pgcrypto (hash never leaves DB)
  - creates session, updates last_login, returns user context
- `api.validate_session(token, ip)` → JSONB user context; slides last_seen_at
- `api.invalidate_session(token)` → JSONB; idempotent logout
- `api.purge_expired_sessions()` → JSONB; housekeeping
- `api.save_project(payload JSONB, user_id BIGINT)` → JSONB; insert/update
- `api.delete_project(id BIGINT, user_id BIGINT)` → JSONB

**GRANTs note:** `GRANT USAGE ON SCHEMA api` was missing from the initial
file — added after hitting `permission denied for schema api` on first
login attempt. The corrected `06_api.sql` has both USAGE and EXECUTE
grants for both `steward` and `web_app_user`.

**pgcrypto:** Enabled on wcyj database (`CREATE EXTENSION pgcrypto`).
Used for bcrypt hashing in `api.login()`. Decision: bcrypt via pgcrypto
over Argon2id because the hash never leaves PostgreSQL — cleaner threat
model, no Python crypto dependency.

### Role Model Decision

Two FK columns on `identity.app_user`:
- `role_id → identity.user_role` — permission tier (admin, staff, customer)
  Required for all users including external/portal users.
- `crew_role_id → identity.crew_role` — application persona (captain,
  mechanic, etc). Nullable — NULL = customer portal user, no crew UI.

Seed data already correct: `user_role` has admin/staff/customer,
`crew_role` has captain/envoy/mechanic/scribe.

### Test Users Created (live DB)

- `carolyn` — admin / captain — contact_id 1, app_user_id 1
- `felipe` — staff / mechanic — contact_id 2, app_user_id 2
  (Felipe's app_user.id is 2 not 42 — 42 was attempted but GENERATED
  ALWAYS AS IDENTITY doesn't allow explicit IDs without OVERRIDING
  SYSTEM VALUE, and we didn't pursue it)

Both users tested successfully end to end.

### Curator Repo Changes

**New files:**
- `src/curator/web/middleware.py` — `SessionMiddleware` validates
  `curator_session` cookie on every request via `api.validate_session()`.
  Injects user context into `request.state.user`. Public paths bypass:
  `/auth/login`, `/auth/logout`, `/static/`, `/health`.
- `src/curator/web/routes/auth.py` — auth routes:
  - `GET /auth/login` → renders login dialog page
  - `POST /auth/login` → calls `api.login()`, sets cookie, redirects
  - `GET /auth/logout` → calls `api.invalidate_session()`, clears cookie
- `src/curator/templates/auth/login.html` — standalone login page with
  native `<dialog>` element. Opens automatically via `showModal()`.
  ESC key blocked. Backdrop blur. Teal Sign In button. Error display.

**Updated files:**
- `src/curator/web/app.py` — adds `SessionMiddleware` and auth router
- `src/curator/web/deps.py` — adds `get_db_direct()` for use in
  middleware and auth routes where FastAPI `Depends()` is unavailable.
  Uses `await db.__aexit__(None, None, None)` to close (no `close()`
  method on `AsyncDBConnection`).
- `src/curator/web/routes/landing.py` — filters crew cards by
  `request.state.user["crew_role"]`. Captain sees all cards. All other
  roles see only their matching card(s). Unauthenticated falls back to
  all cards (middleware should have redirected, safety net only).

### Cookie Settings
- Name: `curator_session`
- `httponly=True` — JS cannot read
- `samesite="strict"` — CSRF protection
- `secure=False` — set to True when behind HTTPS in production
- remember_me=True → 30 days; False → 8 hours

---

## Deferred Items (do not forget)

### 1. dbkit `client_encoding` fix
**Repo:** dev-utils  
**File:** `python/dbkit/dbkit/connection.py`  
**Fix:** Add `client_encoding="utf-8"` to both `psycopg.connect()` and
`psycopg.AsyncConnection.connect()` calls.  
**Why deferred:** The encoding bug (psycopg 3.3.4 returning bytes for
SQL_ASCII databases) was fixed locally in the venv at the time but never
committed to the repo. The current auth flow works because `json.loads()`
handles bytes in Python 3. Will surface elsewhere.  
**Action:** Fix in dev-utils, commit, reinstall in Curator venv:
```bash
pip install --force-reinstall -e ~/projects/dev-utils/python/dbkit
```

### 2. Username lowercase constraint
**Fix:** `ALTER TABLE identity.app_user ADD CONSTRAINT chk_username_lowercase CHECK (username = LOWER(username));`  
**Also:** Update `02_identity.sql` to include the constraint.

### 3. Column rename: `contact_emails.address` → `contact_emails.email`
**Why:** `address` is ambiguous — implies street/mailing address.
The table is called `contact_emails` so the column should be `email`.  
**Fix:** Migration + update `02_identity.sql`.

### 4. Column rename: `contact_phones.number` → `contact_phones.phone_number`
**Why:** `queries.yaml` already references `phone_number` — schema and
queries are out of sync.  
**Fix:** Migration + update `02_identity.sql`.

### 5. `queries.yaml` fixes (contact_emails and contact_phones)
`contact_emails.for_contact` references `email` and `email_type` —
actual columns are `address` and `label`.  
`contact_phones.for_contact` references `phone_number` and `description`
— actual columns are `number` and `label`.  
**Fix:** After column renames above, update queries to match.  
**Note:** `contact_urls`, `tasks`, and `organization_contacts` queries
look correct.

---

## Next Session — PostgreSQL-Native CRUD

### Goal
Replace Python save/update/delete logic in `crew.py` with thin routes
that call `api` schema procs. Python becomes a messenger — receives JSON
from the browser, calls the proc, returns the result.

### Pattern
```python
async with AsyncDBConnection() as db:
    await db.execute(
        "SET LOCAL app.current_user_id = %s", (user_id,)
    )
    result = await db.fetch_one(
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id)
    )
return JSONResponse(result)
```

### Procs already written
- `api.save_project(payload JSONB, user_id BIGINT)` → handles INSERT and UPDATE
- `api.delete_project(id BIGINT, user_id BIGINT)` → hard delete

### What needs to happen
1. Identify existing Python save/update/delete routes in `crew.py`
2. Replace with thin generic route(s) calling api procs
3. Verify projects still save/update/delete correctly
4. Write `api.save_contact()` and `api.delete_contact()` procs
5. Eventually: one generic `api.save_record(entity, payload)` dispatcher

### Auth context in DB
When going public, wrap api calls in a transaction and set:
```sql
SET LOCAL app.current_user_id = '{id}'
```
Procs read via `current_setting('app.current_user_id', true)`.
Not yet implemented — user_id passed as explicit parameter for now.

---

## Known Issues / Deferred UI

- Mobile: Identities tab two-panel layout needs toggle for small screens
- Dark theme: some text color issues on Captain page (black on dark)
- `baseline.css` 404 in some browser sessions — confirm deleted from static
- Clipboard copy button above grid (when rows selected)
- Child datasheets (Tasks, Emails, Phones, URLs, Orgs) — all "coming soon"
- Logout should be accessible from nav (currently must navigate to
  `/auth/logout` directly — no logout button in UI yet)

---

## Commit
`trim: filter landing page crew cards by logged-in user role`

## Repo State
- `curator` repo: main branch, up to date
- `steward` repo: main branch, up to date
- `dev-utils` repo: dbkit fix NOT yet committed (see deferred items)
