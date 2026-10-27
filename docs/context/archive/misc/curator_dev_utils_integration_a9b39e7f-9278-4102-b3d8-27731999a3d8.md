# Curator — dev-utils Integration

*How the shared kit infrastructure is used by the Curator web application.*

---

## Overview

The `dev-utils` repository is the shared equipment locker for Project Crew. It provides reusable tools — the "kits" — that any crew member can draw from without duplicating infrastructure code. Curator currently uses three kits directly, with a fourth planned:

| Kit | Status in Curator | Role |
|---|---|---|
| `dbkit` | Active | Async PostgreSQL connections and connection config |
| `viewkit` (ViewBuilder) | Active | YAML-driven view definitions for templates |
| `viewkit` (QueryLoader) | Partially active | YAML-driven SQL query externalization |
| `setupkit` | Planned | Plugin registration and version management |
| `contactkit` | Planned (standalone) | Contact import; inserts into Curator's schema |
| `viewkit` (OTF Query Tool) | Possible future | Ad-hoc query execution for admin/debug routes |

All kits are installed via editable pip install (`pip install -e`). Curator imports them as normal packages and does not vendor or copy their code.

---

## dbkit

**Responsibility:** Manages PostgreSQL connections and reads database configuration. Curator never handles connection strings, credentials, or pooling directly.

**Entry points used by Curator:**
- `dbkit.connection.AsyncDBConnection` — async context manager wrapping a psycopg connection
- `dbkit.config.ConfigManager` — reads connection parameters from `~/.config/dev-utils/config.yaml`

**How Curator uses it:**

Curator's FastAPI dependency injection layer (`curator.web.deps`) wraps `AsyncDBConnection` in a generator that opens a connection per request and closes it on exit regardless of outcome:

```python
async def get_db() -> AsyncGenerator[AsyncDBConnection, None]:
    db = AsyncDBConnection()
    try:
        await db.__aenter__()
        yield db
    finally:
        await db.__aexit__(None, None, None)
```

Route handlers declare `db: AsyncDBConnection = Depends(get_db)` and pass the connection to a repository class. The repository executes all queries through that connection. Routes never touch SQL; repositories never touch HTTP.

**Config location:** `~/.config/dev-utils/config.yaml` under the `dbkit:` key (host, port, dbname, user). Passwords are handled by `~/.pgpass` — no credentials appear in code or config files. This is dbkit's responsibility entirely; Curator does not manage it.

**Design decision:** Curator treats the database connection as an injected dependency, not a global resource. This keeps routes testable — tests can inject a mock or transaction-rolled-back connection without touching the real database.

---

## viewkit — ViewBuilder

**Responsibility:** Loads `views.yaml` and returns `ViewDef` objects describing the columns and form fields for each named view. Templates use these to render lists and forms without hardcoded column names or labels.

**Entry points used by Curator:**
- `viewkit.ViewBuilder` — loaded with the resolved path to `views.yaml`
- `ViewDef`, `ColumnDef`, `FieldDef` — passed directly into Jinja2 templates as context variables

**How Curator uses it:**

`curator.config.ConfigManager` resolves the path to `views.yaml` using the standard shipped-default / user-override hierarchy:

```
curator/data/views.yaml          ← shipped defaults
~/.config/curator/views.yaml     ← user override (merged on top if present)
```

Routes call `ViewBuilder(config.views_path).get_view("projects")` to get the view definition, then pass the result into the template response:

```python
view = ViewBuilder(config.views_path).get_view("projects")
return templates.TemplateResponse("projects/list.html", {"view": view, ...})
```

Templates loop over `view.columns` to render table headers and `view.fields` to render form inputs. The template never decides what columns exist or what labels to show — that lives in YAML.

**Design decision:** ViewBuilder knows nothing about FastAPI, Jinja2, or Curator's domain model. It is a pure config loader. This means views can be tested independently, changed without touching Python, and overridden per-installation without patching the package.

---

## viewkit — QueryLoader

**Responsibility:** Loads `queries.yaml` and provides named SQL queries to repository classes at runtime. The goal is to move all SQL out of Python source files and into a single inspectable YAML file.

**Entry points used by Curator:**
- `viewkit.query_builder.QueryBuilder` — parses `queries.yaml` into `QueryDef` objects
- `viewkit.query_loader.QueryLoader` — runtime lookup interface used by repositories (`loader.sql("projects", "get_all")`)

**How Curator uses it:**

`queries.yaml` stores all 46 Curator SQL queries as literal strings, organized by entity:

```yaml
projects:
  get_all:
    sql: "SELECT * FROM v_projects ORDER BY name"
    query_type: select_all
  get_by_slug:
    sql: "SELECT * FROM v_projects WHERE slug = %(slug)s"
    query_type: select_one
```

Queries are stored as literal SQL — no ORM shorthand, no query builder abstraction. This means any query can be copied directly into Adminer for debugging without translation.

`projects_routes.py` is the reference implementation showing the full wiring. The remaining route files (`tasks_routes.py`, `files_routes.py`, `tags_routes.py`) still have inline SQL and are being backfilled.

**Design decision:** Externalizing SQL follows the same principle as externalizing views — configuration belongs in YAML, not in Python. It also makes queries auditable in one place and simplifies the path to adding query-level caching or logging later.

---

## contactkit

**Responsibility:** Multi-format contact import with a CLI interface. Parses CSV and VCF export files from Gmail, Proton, Outlook, and Apple Contacts, then inserts records into Curator's contacts schema via a dbkit async connection. Logs each import run to the `contact_imports` audit table.

**Entry points (once implemented):**
- `contactkit.plugins.imports.gmail.GmailImporter` — and equivalent classes for other formats
- `contactkit.cli` — command-line entry point (`contactkit import --format gmail --file contacts.csv`)

**How it relates to Curator:**

contactkit is a standalone tool, not a Curator plugin. It uses dbkit for its database connection the same way Curator does — via `dbkit.config.ConfigManager` and `AsyncDBConnection`. It writes directly into Curator's contacts schema (`organizations`, `contacts`, `contact_emails`, `contact_phones`, `contact_urls`, `contact_imports`).

The planned refactor sequence is:
1. Implement and validate the Gmail importer with hardcoded SQL (MVP)
2. Replace hardcoded SQL with `viewkit.QueryLoader` — this simultaneously proves the QueryLoader pattern in a new non-Curator context and becomes a real-world integration test for viewkit
3. Implement remaining importers (Proton, Outlook, Apple) using the same pattern

**Design decision:** Prove the domain logic first (does the import work correctly?), then prove viewkit can handle it. The refactor is a deliberate sequencing choice, not an oversight.

---

## setupkit (Planned)

**Responsibility:** Plugin installer and version manager for Project Crew. Each crew member registers itself as a plugin; setupkit handles discovery, version checking, and coordinated installs.

**How Curator will use it:**

Curator exposes a `plugin.yaml` (not yet written) that registers it as a Project Crew crew member with name, version, description, and type. setupkit reads this at install time. `curator/setup.py` will import dbkit's setup logic and wire the Quartermaster orchestration layer.

`go.sh` (the per-machine startup script) is generated by `setup.py` and is gitignored, as it contains machine-specific paths.

**Status:** Planned. The plugin manifest format is defined; `setup.py` and `plugin.yaml` are not yet written.

---

## OTF Query Tool — viewkit.onthefly (Possible Future Integration)

**Responsibility:** YAML-driven ad-hoc SQL query execution with formatted output. Executes a named query from a YAML registry and returns results as an ASCII table, JSON, or CSV.

**Entry points:**
- `viewkit.onthefly.runner.run_query()` — executes a named query, returns an `OTFResult`
- `viewkit.onthefly.formatter.format_result()` — renders the result in the requested format

**How Curator could use it:**

- Admin or debug routes could execute named queries from the query registry and display results without writing bespoke repository code
- A `/query` panel in the board dashboard could expose the query registry as a read-only inspection tool — select a query, see results formatted as a table
- Doc-gen manifest diffs and file explorer queries are natural candidates for the registry

**Caveat — sync vs. async:** OTF uses a sync dbkit connection (one per invocation). It is database-agnostic and knows nothing about Curator's models, repositories, or async connection pool. If integrated into a Curator route, it should run in a thread executor to avoid blocking the event loop:

```python
import asyncio
from viewkit.onthefly.runner import run_query

result = await asyncio.get_event_loop().run_in_executor(
    None, run_query, query_name, params
)
```

**Status:** CLI tool complete; `cli.py` entry point in progress. Available as `viewkit.onthefly` once viewkit is installed. Integration into Curator is not planned for current development cycle — this is a note for future consideration.

---

## Config Hierarchy Summary

| Config file | Managed by | Purpose |
|---|---|---|
| `~/.config/dev-utils/config.yaml` | dbkit | DB host, port, dbname, user |
| `~/.pgpass` | System / user | DB passwords (never in code) |
| `curator/data/curator.yaml` | Curator (shipped) | App defaults (server, UI, plugin manifest) |
| `~/.config/curator/curator.yaml` | User (optional) | Per-installation overrides |
| `curator/data/views.yaml` | Curator (shipped) | Column and field definitions for all views |
| `~/.config/curator/views.yaml` | User (optional) | View overrides |
| `curator/data/queries.yaml` | Curator (shipped) | All SQL queries, organized by entity |

Curator's own config is its responsibility. Database connection config is dbkit's responsibility. Curator does not read or write `~/.config/dev-utils/`.

---

## Dependency Relationship

```
Curator routes
    └── Depends(get_db)       → dbkit.AsyncDBConnection → PostgreSQL
    └── Depends(get_config)   → curator.ConfigManager
                                    └── views_path → viewkit.ViewBuilder → views.yaml
                                                                            (templates)
    └── Repository classes
            └── viewkit.QueryLoader → queries.yaml → SQL strings
            └── dbkit.AsyncDBConnection (executes queries)

contactkit (standalone CLI)
    └── dbkit.AsyncDBConnection → PostgreSQL (Curator's contacts schema)
    └── viewkit.QueryLoader     → contactkit's queries.yaml (planned)

viewkit.onthefly (possible future)
    └── dbkit.SyncDBConnection  → PostgreSQL (own connection per call)
    └── asyncio.run_in_executor (if called from async Curator route)
```
