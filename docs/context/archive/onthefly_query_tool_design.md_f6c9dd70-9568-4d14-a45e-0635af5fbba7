# On-the-Fly Query Tool Design

## Overview

The **on-the-fly query tool** (OTF) is a command-line utility for running ad-hoc SQL queries against PostgreSQL databases using `viewkit`'s YAML query registry and `dbkit`'s connection management. It outputs results to stdout (ASCII table), JSON, or CSV files.

**Scope:** Generic query runner leveraging existing Project Crew infrastructure (dbkit, viewkit). Not an interactive REPL or a Curator plugin — a thin wrapper around dbkit's sync or async connection and viewkit's QueryLoader.

---

## Architecture

### Core Dependencies

- **dbkit** — Database connection management, exception wrapping (`ConfigError`, `DBConnectionError`, `QueryError`)
- **viewkit** — YAML query loading and parsing (`QueryBuilder`, `QueryLoader`, `QueryDef`)
- **psycopg** — PostgreSQL driver (via dbkit; OTF does not import it directly)
- **Standard library** — argparse, json, csv, pathlib, logging

### Data Flow

```
CLI args → Parse YAML config path & database name → Load queries.yaml via QueryBuilder
   ↓
Build QueryLoader from QueryBuilder
   ↓
Accept entity.query_name from CLI → Resolve to QueryDef via QueryLoader
   ↓
Open DBConnection (sync) via dbkit → Auto-load config from env vars or YAML
   ↓
Dispatch on QueryDef.query_type → Call matching db method (fetch_all, fetch_one, fetch_scalar, execute)
   ↓
Format result (ASCII table / JSON / CSV) → Write to stdout or file
   ↓
Close connection, exit with appropriate code
```

---

## Configuration

### Connection Parameters

OTF inherits dbkit's config loading precedence:

1. **Environment variables** (all-or-nothing):
   - `DBKIT_HOST`, `DBKIT_PORT`, `DBKIT_DBNAME`, `DBKIT_USER`
   - If all four are present, YAML config file is ignored entirely
   - If any are missing, falls back to step 2

2. **YAML config file** (default: `~/.config/dev-utils/config.yaml`):
   ```yaml
   dbkit:
     host: 192.168.x.x
     port: 5432
     dbname: projects
     user: carolyn
   ```
   - Password is always handled by `~/.pgpass` (PostgreSQL standard)
   - No credentials in code or config files

3. **Password** (`~/.pgpass`):
   - Format: `host:port:dbname:user:password`
   - Sourced by psycopg; OTF does not handle it explicitly

### Query File

OTF loads queries from a `queries.yaml` file. By default, it uses viewkit's standard config hierarchy (user override in `~/.config/viewkit/` takes precedence over shipped defaults in `viewkit/data/`). Alternatively, pass `--queries-file PATH` to override.

Each query has the standard viewkit shape:

```yaml
entity_name:
  query_name:
    type: select_all | select_one | select_scalar | execute
    sql: "SELECT ... FROM ... WHERE ... = %s"
```

---

## Multi-Database Design Decision

**Status:** Deferred — design for single-database-per-invocation initially.

**Rationale:**
- dbkit's env-var config is all-or-nothing per process (all four `DBKIT_*` vars or none)
- OTF runs as a CLI, not a long-lived server; opening multiple connections per invocation is unusual
- Precedent: psql also binds to a single database per invocation

**Future option:** If multi-database queries become common, either:
1. Shell out one OTF process per database (each with its own env-var context)
2. Accept multiple `--config-file` arguments and run the same query across all of them in sequence
3. Refactor dbkit's `_load_config` to support per-database env-var keys like `QUERY_{DBNAME}_HOST` (breaking change)

For now, keep it simple: **one connection per OTF invocation**.

---

## CLI Interface

### Basic Usage

```bash
# Run a SELECT query, print results as ASCII table to stdout
otf projects get_all

# Run a SELECT query that returns one column, print the scalar value
otf tasks get_by_id 42

# Run an INSERT or UPDATE, no output
otf projects create "My Project" "my-project" "Description here" 1 2 null

# Write results to JSON file
otf projects get_all --json results.json

# Write results to CSV file
otf projects get_all --csv results.csv

# Dry-run mode (don't execute INSERT/UPDATE/DELETE)
otf projects create ... --dry-run
```

### Argument Structure

```
otf ENTITY QUERY [PARAM1 PARAM2 ...] [OPTIONS]
```

- `ENTITY` — Entity name from queries.yaml (e.g. `projects`, `tasks`)
- `QUERY` — Query name within the entity (e.g. `get_all`, `create`)
- `PARAM1 PARAM2 ...` — SQL parameters, passed positionally in order to %s placeholders
- `OPTIONS` — Named arguments (see below)

### Named Options

- `--queries-file PATH` — Override default queries.yaml location
- `--config-file PATH` — Override default dbkit config.yaml location
- `--json FILE` — Write results to JSON file instead of stdout
- `--csv FILE` — Write results to CSV file instead of stdout
- `--dry-run` — Parse and log the query, but don't execute (for `execute` type only)
- `--log-level {DEBUG,INFO,WARNING,ERROR}` — Control logging verbosity (default: INFO)
- `--help` — Show usage

### Parameters and NULL Values

Parameters are always positional, matching SQL's `%s` placeholders in order:

```bash
# Query: SELECT * FROM projects WHERE id = %s AND status = %s
otf projects get_by_id_and_status 5 "active"

# NULL value: pass the literal string "null"
otf projects create "Name" "slug" "desc" 1 2 null
```

The CLI parser treats all arguments as strings; dbkit/psycopg handles type coercion based on the database schema. If a parameter should be NULL, the caller passes the string `"null"` and the CLI converts it to Python `None` before passing to psycopg.

---

## Query Execution

### Type Dispatch

OTF switches on `QueryDef.query_type` to determine which dbkit method to call:

| `query_type` | dbkit method | Returns | Use case |
|---|---|---|---|
| `select_all` | `fetch_all()` | `list[dict]` | Multiple rows (projects list) |
| `select_one` | `fetch_one()` | `dict \| None` | Single row (one project detail) |
| `select_scalar` | `fetch_scalar()` | single value or None | Aggregates (COUNT, MAX), existence checks |
| `execute` | `execute()` | None | INSERT, UPDATE, DELETE |

Each query in `queries.yaml` must declare its type. Invalid types raise a validation error at load time (courtesy of viewkit's `QueryDef.__post_init__`).

### Return Values

**`select_all`:** List of dicts, one per row. Empty list if no rows matched.

**`select_one`:** Single dict (column name → value) or None if no row matched.

**`select_scalar`:** Single value (int, str, bool, etc.) or None. Uses psycopg's `scalar_row` row factory for direct value extraction.

**`execute`:** No return value. OTF logs success or failure.

### Transactions

dbkit's context managers auto-commit on clean exit, auto-rollback on exception. For `execute` queries:
- Normal flow: statement is committed automatically
- `--dry-run` flag: statement is parsed and logged, but not executed (OTF explicitly doesn't call the method)
- Exception: dbkit rolls back, OTF logs and exits with code 1

---

## Output Formats

### ASCII Table (default to stdout)

```
id | name          | email
---|---------------|---------
1  | Alice Smith   | alice@example.com
2  | Bob Johnson   | bob@example.com
```

**Details:**
- Columnar format with pipe separators
- Text columns left-aligned, numeric columns right-aligned
- NULL values displayed as empty cells (or `<null>`, TBD)
- Column widths auto-calculated from header and data
- Long values: truncate with ellipsis or wrap (TBD)

**Use case:** Human inspection at the terminal.

### JSON Output (`--json FILE`)

```json
[
  {
    "id": 1,
    "name": "Alice Smith",
    "email": "alice@example.com"
  },
  {
    "id": 2,
    "name": "Bob Johnson",
    "email": "bob@example.com"
  }
]
```

**Details:**
- Standard JSON array of objects
- Directly deserializable (no extra metadata wrapper)
- NULL database values become JSON `null`
- Dates/times: returned as ISO 8601 strings (psycopg default)

**Use case:** Piping to other tools, programmatic processing.

### CSV Output (`--csv FILE`)

```
id,name,email
1,Alice Smith,alice@example.com
2,Bob Johnson,bob@example.com
```

**Details:**
- Standard CSV with header row
- Quote strings only if needed (CSV dialect: `excel`)
- Escape quotes as `""` (CSV standard)
- NULL values become empty cells
- Use Python's `csv` module; no manual escaping

**Use case:** Import into Excel, spreadsheet processing.

### `select_scalar` Output

For scalar queries, OTF outputs just the value:
- **ASCII table:** Single cell with the value
- **JSON:** Single bare value (not wrapped in an object or array)
- **CSV:** Single cell with the value

Example: `otf tasks get_by_id 1` → `7` (the count, or the ID, etc.)

### `execute` Output

For INSERT/UPDATE/DELETE queries, OTF outputs status only:
- **stdout:** "Query executed successfully" or similar log message
- **JSON:** `{"status": "ok", "rows_affected": N}` (if psycopg provides this)
- **CSV:** Not applicable; ignored

---

## Error Handling

### Exception Handling

OTF catches three dbkit exceptions at the CLI boundary, each with distinct exit codes:

| Exception | Exit code | Log level | Message template |
|---|---|---|---|
| `ConfigError` | 2 | ERROR | "Configuration error: {details}. Check ~/.config/dev-utils/config.yaml or DBKIT_* env vars." |
| `DBConnectionError` | 3 | ERROR | "Database connection failed: {details}. Check host, port, user, and ~/.pgpass." |
| `QueryError` | 1 | ERROR | "Query failed: {details}. SQL: {sql}" |

Exit codes:
- `0` — Success
- `1` — Query execution failure (syntax error, constraint violation, etc.)
- `2` — Configuration error (missing or invalid config)
- `3` — Database connection failure (unreachable, auth failure)

### Logging

All logging goes to a file (location TBD, probably `~/.local/share/viewkit/otf.log`) in two formats:

**Human-readable (main log):**
```
[2025-04-22 14:23:45.123] INFO  : Loaded 46 queries from /home/carolyn/.config/viewkit/queries.yaml
[2025-04-22 14:23:45.234] DEBUG : Resolved projects.get_all to SELECT statement
[2025-04-22 14:23:45.345] INFO  : Connecting to projects (localhost:5432)
[2025-04-22 14:23:45.456] INFO  : Query projects.get_all executed
[2025-04-22 14:23:45.467] INFO  : Result: 7 rows in 122ms
[2025-04-22 14:23:45.468] INFO  : Formatted as ASCII table to stdout
```

**Machine-readable (JSON log, optional):**
```json
{"timestamp": "2025-04-22T14:23:45.123Z", "level": "INFO", "event": "query_executed", "entity": "projects", "query": "get_all", "rows": 7, "duration_ms": 122}
```

**Log what:**
- Config source (env vars or file path)
- Connection details (host, port, dbname, user — NOT password)
- Query resolved (entity, name, type, SQL statement)
- Parameters passed (with non-sensitive values; redact passwords)
- Execution time (milliseconds)
- Result row count (for `fetch_all`, `fetch_one`)
- Output format (ASCII, JSON, CSV)
- Any warnings or errors

**On error:**
- Log full traceback at DEBUG level
- Log human-readable summary at ERROR level
- Print error summary to stderr
- Exit with appropriate code

---

## Architectural Notes

### Why Sync, Not Async?

OTF defaults to `DBConnection` (sync) rather than `AsyncDBConnection`:

1. **Simpler CLI model** — No event loop setup, no `asyncio.run()`, no top-level async entrypoint
2. **Clearer error traces** — No asyncio machinery hiding the actual error
3. **Precedent** — psql, mysql, and other CLI tools are sync
4. **psycopg supports both equally** — No performance difference for single queries

If future use cases demand streaming results or parallel queries across databases, async can be reconsidered.

### No Driver Coupling

OTF never imports `psycopg` directly. All database access goes through dbkit, which wraps psycopg and provides exception translation. This keeps the OTF tool decoupled from the driver implementation.

### SQL as Source of Truth

SQL strings in `queries.yaml` are literal — no translation layer, no macro expansion, no string templating. This ensures:
- Copy-paste-into-Adminer debugging works
- SQL is portable (can be used in other tools without translation)
- No hidden complexity in parameter substitution

### No Lookup Table Coupling

Unlike Curator's `SlugResolver` and `get_lookup_options`, OTF does not provide helper methods for FK dropdowns or enum lookups. Those are application-level concerns; OTF is data-agnostic.

### Connection Lifecycle

One connection per OTF invocation:
1. `__enter__` opens the connection
2. Query executes (with auto-commit on success, auto-rollback on exception)
3. `__exit__` closes the connection
4. Process exits

No connection pooling, no reuse across queries, no background tasks.

---

## Implementation Checklist

- [ ] Create `viewkit/cli.py` or `viewkit/onthefly.py` with argument parser
- [ ] Implement query dispatch on `QueryDef.query_type`
- [ ] Implement ASCII table formatter
- [ ] Implement JSON output writer
- [ ] Implement CSV output writer
- [ ] Implement logging (human + JSON formats)
- [ ] Implement exception handling and exit codes
- [ ] Add `--dry-run` support (parse but don't execute)
- [ ] Add `--log-level` support
- [ ] Write unit tests for formatting, dispatch, error cases
- [ ] Write integration tests against a test database (use floater + test_curator)
- [ ] Document in viewkit README
- [ ] Consider adding console script entry point in `viewkit/pyproject.toml`

---

## Open Questions

1. **NULL display in ASCII table:** Empty cell or `<null>` literal? Currently undefined.
2. **Long value wrapping in ASCII table:** Truncate with `…` or line wrap? Currently undefined.
3. **JSON scalars:** Should `select_scalar` return a bare JSON value (e.g., `7`) or wrapped (`{"value": 7}`)? Bare is simpler; wrapped is more explicit.
4. **Rows affected count for execute:** Does psycopg provide this? If so, include in JSON output?
5. **Log file location:** Default to `~/.local/share/viewkit/otf.log`, or elsewhere?
6. **Future: multi-database support:** Deferred; revisit if needed (see Multi-Database Design Decision section above).

---

## Future Enhancements

- **Dry-run for SELECT:** Log the query and parameter count without fetching
- **Streaming results:** For large result sets, write to CSV/JSON incrementally instead of loading all rows into memory
- **Named parameters:** Extend `queries.yaml` to support `%(name)s` placeholders alongside `%s`
- **Interactive mode:** Let users select query from menu, enter params interactively, preview before executing
- **Query templating:** Minimal Jinja2 templating in SQL (e.g., `{% if filter %}WHERE status = %s{% endif %}`)
- **Result pagination:** For large ASCII tables, paginate output
- **Export formats:** YAML, XML, SQLite, Parquet
- **Audit logging:** Track who ran what query when (requires auth context)

---

## Related Documentation

- **dbkit:** `dbkit/connection.py` — Sync and async connection management, exception types
- **viewkit:** `QueryBuilder`, `QueryLoader`, `QueryDef` — YAML query loading and resolution
- **Curator:** `curator/db/base.py` — Example repository pattern (reference for dispatch logic)
- **Project Crew:** `project_crew_roster.md` — Infrastructure and role descriptions
