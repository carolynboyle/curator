# Handoff — Seanchaí Register migration (written 2026-10-22, end of session)

Start the next conversation by attaching (or `add_repo`-ing) **steward**, **curator** and **seanchai**, and reading this note.

## Goal for the next session

Move the **Seanchaí Register** artifact (people + places) into Postgres **without losing its design**.

- Artifact: https://claude.ai/artifact/U6ubhT3cx4TXqg58bik4dR (title "Seanchaí Register")
- Agreed approach (Carolyn approved, "option 2"): data moves to the database; the Register's own HTML/CSS/JS is ported almost unchanged into a **Register tab on the Seanchaí crew dashboard**, loading from the database instead of the hard-coded `PEOPLE` / `PLACES` arrays. Its own Add Person / Edit forms save through `api.*` — ending the "copy this block and paste it to Claude" loop.
- **Do not touch the artifact** until the Curator version matches it.

### Three steps, each usable on its own
1. **Schema + import** (do this first). New steward SQL file (next free number: `10j_…`), additive. Extract the arrays from the artifact HTML (Artifact tool, `action: read`), generate an import SQL like the ledger import, test on a scratch Postgres 16 build, verify counts. Import SQL + raw extracted JSON go in the **seanchai** repo `data/` (project data, not schema).
2. **Read-only Register tab** — port the page into a Curator partial; data from a JSON route.
3. **Editing** — wire the Register's forms to `api.save_person` / `api.save_place` (+ delete).

### What's in the artifact (counted 2026-10-22)
- **25 people** in 5 groups: Boyle — Donegal Line; Beall Line; Connell's Children; Captain Felix's Family; Felix Michael's Family
- **21 places** in 5 groups: Ireland; Washington County; Monongahela River Sites; Pittsburgh & Allegheny County; Beyond Pennsylvania — 16 place types
- ~**175 timeline events** (99 people, 76 places)
- Person fields: `id` (text slug, e.g. `felix-sr-boyle`), `name`, `altName`, `group`, `tags[]`, `associatedPlaces[]`, `born{year,place}`, `died{year,place}`, `parents[]`, `spouse[]`, `children[]`, `siblings[]`, `events[{year,text}]`, `notes`
- Place fields: `id`, `name`, `altName`, `group`, `type`, `tags[]`, `location{area,county,state,country}`, `established{year,note}`, `status{year,note}`, `currentStatus`, `associatedPeople[]`, `relatedPlaces[]`, `events[]`, `notes`
- Years are **text** ("c. 1748", "1773 or 1777", "Dec 15, 1837") — keep them text.

### Proposed schema (seanchai schema)
- `people` and `places`, each keeping the text slug as a unique key so links stay readable
- `events` — one table for both timelines (person_id or place_id), year text, text, sort order
- `person_relationships` (person, related person, kind: parent / spouse / sibling — children are the reverse of parent; the artifact stores siblings explicitly, keep them)
- `person_places`, `place_relations`, `tags` + `person_tags` / `place_tags`
- `api.*` read + save functions, SECURITY DEFINER, `{success, data, message}` envelope
- Later (not now): link timeline events to ledger records (notes already cite PR-033 etc.)

## Where things stand (all deployed on wcyj-meet unless noted)

**Repos** — everything on `main`; all three cloned on the server at `~/projects/<repo>`, remotes over SSH.
- **steward** (private) — schema SQL, `databases/wcyj/sql/`
- **curator** (public — Carolyn's choice) — the app
- **seanchai** (private) — research data: `data/ledger_export_2026-10-22.json`, `data/10d_seanchai_import.sql`

**SQL applied on the live DB today:** `10d_seanchai_todos.sql`, ledger import (102 records, 12 searches, 23 todos, 53 links), `10f_seanchai_autonumber.sql`, `10g_seanchai_other_type.sql` (OTH), `10h_crew_role_seanchai.sql`. Also by hand: `seanchai.searches.year_filter` / `county_scope` widened to TEXT (views rebuilt to the 07b whitelist).
**Not yet confirmed applied:** `10i_seanchai_todos_to_tasks.sql` — run it if not done (expect report 23, 23, 53, 53).

**What exists now**
- **The Seanchaí is a crew role** (plum theme; Curator image as stand-in — the Seanchaí illustration from Bob Boyle's wine-glass photo is a later, "ready to share with the siblings" task). Dashboard tabs: Projects, Records, Searches. `/seanchai/` redirects to `/crew?role=seanchai`.
- **Projects belong to one crew role** (`projects.crew_role_id`); role views filter by owner; project types are shared. Captain sees all. Refurb went to the Mechanic.
- **Research todos are now tasks** in the Seanchaí project **"FamilySearch Research"** (after 10i); links kept in `seanchai.task_records`. Old `seanchai.todos*` tables still exist, unused — drop in a later cleanup. 10e (todo API) is cancelled.
- Ledger forms: Record/Search IDs auto-assigned (`<CODE>-NNN`, `SRCH-NNN`); Alt+A adds a record; Option+S/N/X now work on Mac.
- Landing page: two columns, "Curator: Navigate the Project Crew" title.

## How to work (conventions that held up today)
- Discuss approach before coding; Carolyn approves, then build.
- **Test SQL on a scratch Postgres 16** built from the full steward chain before she runs anything. Build order: every file in name order **except** skip `05b_migration_app_user.sql`, and run `07_detail_views.sql` **before** `07_detail_api.sql`.
- Render templates/pages with Jinja + headless Chromium (Playwright at `/opt/pw-browsers/chromium`) and send screenshots before she deploys UI changes. Curator's Python deps can't be pip-installed in the cloud session (no PyPI access), so the full app can't be run there.
- Commit and push to `main` (Carolyn prefers few branches). The session can't delete GitHub branches.
- Curator startup validates every `v_*_detail` view against `fieldkit_overrides.yaml` — a view change and its YAML must deploy together (SQL first, then rebuild immediately).
- Server commands, from `~/projects/curator`:
  - SQL: `docker compose exec -T db psql -U steward -d wcyj -v ON_ERROR_STOP=1 < ~/projects/steward/databases/wcyj/sql/<file>.sql`
  - Deploy: `git pull && docker compose up -d --build`; logs: `docker compose logs app --tail 60`

## Loose ends (none block the Register work)
- Delete merged branches on GitHub: steward `recovered-core-sql`; curator `seanchai-fieldkit-overrides`, `seanchai-form-fixes`. Review then delete curator `part_1` (June 2026).
- Delete test record if created: `DELETE FROM seanchai.records WHERE record_id = 'OTH-001';`
- Curator: remove `cookies.txt` (expired local login cookie) and add it to `.gitignore`.
- Steward `docs/roadmap/TODO_STEWARD_TIDY_UP.md`: tick off done items (branches merged, Dockerfile fixed in curator); add cookies.txt and part_1.
- Later: Project dropdown on the task form (move tasks between projects — DB already supports it); BIO-003 = Creigh's History of Washington County (cited, never logged; links to TODO-019 / its task); least-privilege DB user before business data returns; drop old `seanchai.todos*` tables.
