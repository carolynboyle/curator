# Curator v2 Handoff — 2026-06-25

## Session Summary

Long session covering database migration planning, schema evolution, and
Phase 2 implementation. Role-filtered crew dashboards with HTMX search
are now live and working.

---

## What Was Accomplished This Session

### Database (wcyj on steward)

- **`contacts` schema renamed to `identity`** — one-line DDL, PostgreSQL
  handled all FK references automatically. Changedoc:
  `rename_schema_contacts_to_identity.md`

- **`identity.crew_role` table created and seeded** — captain, envoy,
  mechanic, scribe. Replaces hardcoded VARCHAR CHECK constraints so
  Captain can define new roles (e.g. Bosun) via UI without schema changes.

- **`projects.project_type_role_mapping` table created** — maps project
  types to crew roles. Seeded with:
  - Captain: all types
  - Scribe: writing
  - Mechanic: homelab
  - Envoy: refurb (needs review — refurb is arguably Mechanic territory)

- **`projects.project_status_role_mapping` table created** — maps project
  statuses to crew roles. Seeded but not yet wired into views.

- **Writing-specific statuses added** to `projects.project_status`:
  `published` (6), `ready to write` (7), `in progress` (8)

- **Three project types added** to `projects.project_type`:
  `coding` (4), `game-dev` (5), `personal` (6)

- **Four role-filtered views created**:
  - `projects.captain_view` — all projects
  - `projects.scribe_view` — writing only
  - `projects.mechanic_view` — homelab only
  - `projects.envoy_view` — refurb only

- **5 test project records inserted** directly via pgAdmin:
  - Accidental Mystic Substack (writing)
  - Curator v2 (homelab)
  - Homelab Infrastructure (homelab)
  - WCYJ Refurb Customer Records (refurb)
  - WCYJ Store Website (refurb)

- **GRANT SELECT on all four views to `steward`** (the Curator db user)

### dbkit Fix

- **psycopg 3.3.4 bytes regression fixed** — added `client_encoding="utf-8"`
  to both `DBConnection.__enter__` and `AsyncDBConnection.__aenter__` in
  `python/dbkit/dbkit/connection.py` in the dev-utils repo.
- Root cause: psycopg 3.3.4 changed behavior for `SQL_ASCII` databases,
  returning text as `bytes` instead of `str` when no client encoding is set.
  psycopg 3.3.3 (used by Curator v1) decoded automatically.
- Fix committed and pushed to dev-utils GitHub. Reinstalled in curator venv:
  `.venv/bin/pip install --force-reinstall ~/projects/dev-utils/python/dbkit`
- Changedoc: `dbkit_client_encoding_fix.md`

### App Code

- **`crew.py`** — updated to query role-specific PostgreSQL views, added
  HTMX-powered server-side search (`ILIKE`), detects `HX-Request` header
  and returns `_crew_rows.html` partial for HTMX requests.

- **`crew.html`** — updated with HTMX search input targeting `#crew-rows`,
  300ms debounce, passes role and search params.

- **`_crew_rows.html`** — new partial containing just the `<tr>` rows,
  shared between full page render and HTMX partial response.

- **`base.html`** — HTMX CDN script tag added before `</body>`.

### Documents Generated This Session

All in `docs/` or project knowledge:
- `rename_schema_contacts_to_identity.md` — schema rename changedoc +
  full updated `wcyj_schema.sql`
- `dbkit_client_encoding_fix.md` — dbkit bytes regression fix changedoc
- `phase2_migration.md` — data migration SQL (not yet run; old projects
  data migration deferred — test records sufficient for Phase 2 dev)

---

## Current State

### Working
- Landing page with four crew cards ✅
- Role-filtered project lists (Captain/Scribe/Mechanic/Envoy) ✅
- HTMX search filtering within role views ✅
- Clean text rendering (bytes regression fixed) ✅
- Role identity colors (Captain blue, Scribe slate, Mechanic green,
  Envoy crimson) ✅

### Known Issues / Deferred
- Envoy mapped to `refurb` — probably wrong, should be Mechanic.
  Fix via pgAdmin: update `project_type_role_mapping` directly, or
  wait for Captain's Command Center UI.
- Old projects data migration (`phase2_migration.md`) deferred — not
  needed until role filtering is proven with real data volume.
- `project_status_role_mapping` seeded but not yet wired into views.

---

## Next Steps (in order)

### 1. Inline row editing (next session priority)

**Flow:**
- Pencil icon hidden on each row, visible on `tr:hover` via CSS
- Clicking pencil triggers HTMX swap — row becomes editable in place
- Editable fields: name (text input), type (dropdown), status (dropdown)
- Dropdowns populated from `projects.project_type` and
  `projects.project_status` lookup tables
- Save / Cancel buttons appear just below the editing row
- Save: POST to update route → database write → row returns to display
  mode with updated values, role + search state preserved
- Cancel: row returns to display mode, no write

**Files to create/modify:**
- `crew.py` — add GET route for edit row partial, POST route for save
- `crew.html` — add `...` button at row end for future full edit
- `_crew_row_edit.html` — new partial: editable row form
- `_crew_rows.html` — add pencil icon, hover CSS class, HTMX trigger

**Prove before adding:**
- New record form (add project)
- Full edit page (`...` → `/projects/{slug}/edit`)

### 2. Full edit page (after inline edit proven)

- `...` at end of each row → `/projects/{slug}/edit`
- Fields TBD — at minimum: name, type, status, description, notes
- Eventually: tasks list, file attachments, parent project

### 3. Captain's Command Center

- Role ↔ project type assignment (dual listbox UI)
- Role ↔ project status assignment
- Eventually: define new roles, manage contacts, manage users

### 4. Task management

- Tasks per project record
- Accessible from full edit page or project detail page

### 5. Authentication (Phase 3)

- Login form per crew card
- Role validation
- Session management

---

## Key Facts to Remember

- **Database**: `wcyj` on steward (100.64.0.7), `steward` PostgreSQL role
  is the Curator app user
- **Schemas**: `audit`, `identity`, `projects`, `infrastructure`, `public`
  (empty default)
- **Views**: `projects.{role}_view` — captain, scribe, mechanic, envoy
- **Role IDs**: captain=1, envoy=2, mechanic=3, scribe=4
  (in `identity.crew_role`)
- **Project type IDs**: homelab=1, refurb=2, writing=3, coding=4,
  game-dev=5, personal=6
- **Project status IDs**: active=1, archived=2, complete=3, on hold=4,
  queued=5, published=6, ready to write=7, in progress=8
- **Curator runs on**: wcyjv20 (LMDE), `localhost:8080`
- **pgAdmin runs on**: wcyjvs2 (100.64.0.6:5050)
- **dbkit regression**: psycopg 3.3.4 returns bytes for SQL_ASCII text —
  fixed by `client_encoding="utf-8"` in dbkit connection.py
- **HTMX pattern**: search sends `HX-Request: true` header; crew.py
  returns `_crew_rows.html` partial when detected
- **Pencil hover CSS**: `tr .edit-icon { visibility: hidden; }`
  `tr:hover .edit-icon { visibility: visible; }`
- **Nautical commit vocab**: `launch`, `trim`, `patch`, `refit`,
  `provision`, `stow`, `chart`
