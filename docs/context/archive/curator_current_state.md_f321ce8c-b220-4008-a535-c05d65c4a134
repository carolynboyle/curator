# Curator — Current State

*What exists, what works, and where to find it.*
*Last updated: April 2026*

---

## What Is Curator

Curator is a FastAPI web application for managing project information stored in PostgreSQL. It is part of Project Crew, a personal infrastructure toolset with a nautical naming theme. The Curator surfaces data from the Steward database (a PostgreSQL LXC container) through a browser UI built with Jinja2 templates, HTMX for partial-page updates, and PicoCSS for styling.

Curator is self-referential: it tracks its own development as a project in the database it manages.

The primary UI is a **kanban-style board** at `/projects/board`. A project tree is displayed in the left panel; clicking a project loads its detail panel on the right via HTMX. Everything else — forms, lists, CRUD operations — feeds back to the board.

---

## Running Instance

| Node | Address | Role |
|---|---|---|
| wcyjvs2 | `100.64.0.3` | Curator web server (Alma Linux 9) |
| Steward LXC | `100.64.0.10` | PostgreSQL 15 only — single-purpose database appliance |
| wcyjvs1 | `100.64.0.9` | Adminer and pgAdmin 4 (containerized), Directus |

Curator runs under uvicorn. In development, use `--reload`. The startup script `go.sh` is machine-specific and gitignored; it is generated per-machine during setup.

Adminer (on wcyjvs1) is the go-to tool for direct database inspection when no UI route exists yet.

---

## Database

### Core Schema

The schema lives in the `steward` repo at `data/projects/schema.sql`. The `projects` database is the canonical store. A `test_curator` database (owned by the `floater` role) is used for the integration test suite.

**Lookup tables** (small, stable, seeded from `seed.sql`):

| Table | Purpose |
|---|---|
| `task_status` | Open, in-progress, blocked, complete, etc. |
| `project_status` | Active, on-hold, complete, etc. |
| `project_type` | Category labels for projects |
| `tag_category` | Groups tags by kind |
| `location_type` | Classifies file references: local, url, git, s3 |
| `file_type` | Classifies file content: markdown, config, script, etc. |
| `priority` | Task priority levels: low, normal, high, blocking |

**Core tables**:

| Table | Notes |
|---|---|
| `projects` | Self-referencing (`parent_id`) for unlimited subproject depth. `slug` is the stable external handle. |
| `tasks` | Self-referencing (`parent_id`) for subtasks. `project_id` stored on every row for query simplicity. Cascade-deleted with project. Children block parent deletion — double-confirm required. |
| `tags` | Flat tag list, optionally categorized. |
| `project_tags` | Many-to-many junction: projects ↔ tags |
| `task_tags` | Many-to-many junction: tasks ↔ tags |
| `project_files` | File/URL attachments. Belongs to a project or task (CHECK enforces at least one). |

**Views** (join lookup names in so repositories don't need to):

| View | Purpose |
|---|---|
| `v_projects` | Projects with resolved status/type names, parent name/slug, and task counts (total, open, completed) |
| `v_tasks` | Tasks with resolved status, priority, parent description, and project name/slug |
| `v_project_tree` | Recursive CTE — expands full project ancestry. `depth` 0 = top-level. |
| `v_task_tree` | Recursive CTE — expands full subtask ancestry. Carries `project_id` and `project_slug` for filtering. |

### Contacts Schema (migrated, no UI yet)

A second schema layer was added in April 2026 to support contact management. The tables exist in the database but no routes or UI have been built yet.

| Table | Purpose |
|---|---|
| `organizations` | Employer/org records, referenced by contacts |
| `contacts` | Person records (name, org, notes) |
| `contact_emails` | Normalized email addresses per contact |
| `contact_phones` | Normalized phone numbers per contact |
| `contact_urls` | URLs per contact (LinkedIn, GitHub, etc.) |
| `project_contacts` | Many-to-many: projects ↔ contacts, with `primary_email_id` and role (project-context-dependent) |
| `contact_imports` | Audit log of import runs |

---

## Routes

### Board (primary entry point)

| Method | Path | Status | Notes |
|---|---|---|---|
| GET | `/projects/board` | ✅ Working | Main UI. Project tree left panel, detail right panel. |
| GET | `/projects/{slug}/panel` | ✅ Working | HTMX fragment. Loads project detail into board right panel. |

### Projects

| Method | Path | Status | Notes |
|---|---|---|---|
| GET | `/projects/` | ✅ Working | Flat list view. Filterable by status. |
| GET | `/projects/new` | ✅ Working | Create form. |
| POST | `/projects/new` | ✅ Working | Creates project, redirects to board. |
| GET | `/projects/{slug}/edit` | ✅ Working | Edit form. |
| POST | `/projects/{slug}/edit` | ✅ Working | Updates project, redirects to board. |
| POST | `/projects/{slug}/delete` | ✅ Working | Deletes project (cascades to tasks). |
| GET | `/projects/{slug}` | ⚠️ Present, targeted for removal | Standalone detail page. Superseded by the board panel. Should be deleted. |

**Note:** Route registration order matters. `/projects/board` must be registered before `/{slug}` or FastAPI will try to match `board` as a slug. This is enforced in code but does not yet have a regression test.

### Tasks

| Method | Path | Status | Notes |
|---|---|---|---|
| GET | `/tasks/project/{slug}` | ✅ Working | Standalone task list for a project. |
| GET | `/tasks/new/{slug}` | ✅ Working | Create form. |
| POST | `/tasks/new/{slug}` | ✅ Working | Creates task, redirects to project. |
| GET | `/tasks/{id}/edit` | ✅ Working | Edit form. |
| POST | `/tasks/{id}/edit` | ⚠️ Bug | Status change in-progress → complete does not save correctly. |
| POST | `/tasks/{id}/delete` | ✅ Working | Blocked if task has children — returns `?delete_blocked=` query param. |
| POST | `/tasks/{id}/force-delete` | ✅ Working | Deletes task and all descendants. |

**Known bug:** Inline edit redirects to the standalone detail page instead of staying on the board. Related to the detail page not yet being removed.

### Files

| Method | Path | Status | Notes |
|---|---|---|---|
| GET | `/files/` | ✅ Working | All file attachments across all projects. |
| GET | `/files/new` | ✅ Working | Accepts `?project_id=` or `?task_id=` context. |
| POST | `/files/new` | ✅ Working | Creates attachment, redirects to project if slug available. |
| GET | `/files/{id}/edit` | ✅ Working | Edit form. |
| POST | `/files/{id}/edit` | ✅ Working | |
| POST | `/files/{id}/delete` | ✅ Working | |

### Tags

| Method | Path | Status | Notes |
|---|---|---|---|
| GET | `/tags/` | ✅ Working | All tags. |
| GET | `/tags/new` | ✅ Working | |
| POST | `/tags/new` | ✅ Working | Redirects to `/tags/`. |
| GET | `/tags/{id}/edit` | ✅ Working | |
| POST | `/tags/{id}/edit` | ✅ Working | |
| POST | `/tags/{id}/delete` | ✅ Working | |

### Contacts

No routes yet. Schema is in place; UI design is documented. See `SCHEMA_MIGRATION_CONTACTS.md`.

---

## Architecture Layers

**Request flow:**

```
Browser → FastAPI route → Repository → dbkit.AsyncDBConnection → PostgreSQL
                ↓
        Jinja2 template (+ HTMX for panel loads)
```

**Dependency injection** (via `curator.web.deps`):
- `get_db` — yields an `AsyncDBConnection` per request, closes on exit
- `get_config` — yields `ConfigManager` (resolves config and data file paths)
- `get_query_loader` — yields `QueryLoader` for externalized SQL (wired in `projects_routes.py`; other route files still use inline SQL)

**Repository classes** live in `curator.db`. One class per entity: `ProjectRepository`, `TaskRepository`, `FileRepository`, `TagRepository`. Routes never touch SQL; repositories never touch HTTP.

**YAML-driven configuration:**
- `curator/data/views.yaml` — column and field definitions for all views; read by `viewkit.ViewBuilder`
- `curator/data/queries.yaml` — all 46 SQL queries as literal strings, organized by entity; read by `viewkit.QueryLoader`

SQL is stored as literal strings so any query can be pasted directly into Adminer without translation.

---

## dev-utils Integration

Curator uses three tools from the `dev-utils` shared library, all installed as editable pip packages (`pip install -e`):

| Kit | Status | What it does for Curator |
|---|---|---|
| `dbkit` | Active | Async PostgreSQL connection management; reads `~/.config/dev-utils/config.yaml` for connection params |
| `viewkit` (ViewBuilder) | Active | Loads `views.yaml` → `ViewDef` objects passed to templates |
| `viewkit` (QueryLoader) | Partially wired | Loads `queries.yaml` → named SQL strings for repositories. Wired in `projects_routes.py`; remaining routes still use inline SQL. |

Passwords are handled exclusively by `~/.pgpass`. No credentials appear in code or config files.

---

## Test Suite

Two tiers, run independently:

**Unit tests** (~49 tests): FastAPI `TestClient` with `AsyncMock` for repository calls. No database required. Run with `pytest` (default marker).

**Integration tests** (~70 tests): psycopg direct against `test_curator` via the `floater` role. Each test runs inside a transaction that is rolled back on exit — no teardown scripts needed. Run with `pytest -m integration`.

Integration tests require environment variables (`DBKIT_HOST`, `DBKIT_PORT`, `DBKIT_DBNAME`, `DBKIT_USER`, `DBKIT_PASSWORD`) loaded from `tests/.env.test`. The test fixture loads `schema.sql` and `seed.sql` from either a local `steward` repo clone or raw GitHub URLs.

Schema and seed SQL are executed via `psql` subprocess (not psycopg) because `pg_dump` output contains psql meta-commands that psycopg cannot handle.

---

## Known Active Bugs

| Bug | Location | Notes |
|---|---|---|
| Task status in-progress → complete not saving | `tasks_routes.py` POST `/{id}/edit` | Status change silently fails |
| Inline task edit redirects to standalone detail page | `tasks_routes.py` | Should return to board; detail page is targeted for deletion |
| No regression test for route registration order | `projects_routes.py` | `/board` must precede `/{slug}` or board is treated as a slug |
