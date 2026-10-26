# ViewKit Query Tester Design Summary

## Purpose
A CLI tool that reads SQL queries from YAML and executes them against PostgreSQL (or other SQL databases eventually), with comprehensive logging to understand what's happening at each step.

## Core Concept
- **Generic YAML-driven query runner** — not tied to any specific tool
- **Universal SQL execution** — can query any PostgreSQL database
- **Credentials cascade:** env vars → YAML → ~/.pgpass
- **Comprehensive logging** — essential to see what happens

---

## YAML Structure

### Database Configuration
```yaml
databases:
  curator:
    host: localhost
    port: 5432
    dbname: curator
    user: curator
    # password from ~/.pgpass or env QUERY_CURATOR_PASSWORD

  test_curator:
    host: localhost
    port: 5432
    dbname: test_curator
    user: floater
```

### Query Definition
```yaml
queries:
  contacts:
    get_all:
      db: curator
      type: select_all
      sql: "SELECT * FROM contacts ORDER BY name"
    
    get_by_id:
      db: curator
      type: select_one
      sql: "SELECT * FROM contacts WHERE id = %s"
  
  projects:
    list_active:
      db: curator
      type: select_all
      sql: "SELECT id, name, slug FROM projects WHERE status_id = 1"
```

**Query types (from QueryBuilder):**
- `select_all` — fetch all rows
- `select_one` — fetch single row
- `select_scalar` — fetch single value
- `execute` — INSERT/UPDATE/DELETE, return row count

---

## CLI Usage

### Basic execution
```bash
python -m viewkit.query_tester --query contacts.get_all
python -m viewkit.query_tester --query contacts.get_by_id --params '{"id": 5}'
```

### Output formats
```bash
# Default: pretty ASCII table to stdout
python -m viewkit.query_tester --query contacts.get_all

# Write to JSON file (no stdout)
python -m viewkit.query_tester --query contacts.get_all --json results.json

# Write to CSV file (no stdout)
python -m viewkit.query_tester --query contacts.get_all --csv results.csv

# Both files (no stdout)
python -m viewkit.query_tester --query contacts.get_all --json results.json --csv results.csv

# Suppress stdout but still write files
python -m viewkit.query_tester --query contacts.get_all --json results.json --silent
```

### Requirements
- `--silent` flag **requires** either `--json FILE` or `--csv FILE`
  - Error if used alone: "ERROR: --silent requires --json or --csv output"
- If neither `--json` nor `--csv` specified, always output to stdout (unless `--silent` + file output)

### Interactive mode
```bash
# List available queries and prompt user to select
python -m viewkit.query_tester --list
python -m viewkit.query_tester  # if no --query, list queries interactively
```

---

## Credentials Resolution

**Order of precedence (first match wins):**
1. Environment variables: `QUERY_{DBNAME}_{KEY}`
   - `QUERY_CURATOR_HOST`
   - `QUERY_CURATOR_PORT`
   - `QUERY_CURATOR_DBNAME`
   - `QUERY_CURATOR_USER`
   - `QUERY_CURATOR_PASSWORD`

2. YAML config (in `viewkit/queries.yaml`)
   - `databases.curator.host`, etc.

3. `~/.pgpass` (PostgreSQL standard)
   - Format: `host:port:dbname:user:password`
   - Only checked if YAML has host/port/dbname/user but no password

4. Fail with clear error message if any required field is missing

---

## Logging

### Log Output
- **All logging to file** (location TBD, probably `~/.local/share/viewkit/query_tester.log`)
- **Human-readable format** (timestamp, level, message)
- **Machine-readable format** (JSON) optional for parsing

### What gets logged
- Database connection details (host, port, dbname, user — NOT password)
- Query name and SQL executed
- Parameters passed
- Row count returned
- Execution time
- Any errors or warnings
- Final result summary (success/failure)

### Behavior on error
- Log full error details
- If absolute failure (can't connect, syntax error, etc.):
  - Print log to stderr
  - Exit with code 1
- Partial failures (e.g., 1 of 5 rows failed):
  - Log, but continue execution
  - Report in output

### Example log entry
```
[2025-04-22 14:23:45.123] INFO  : Connecting to curator (localhost:5432)
[2025-04-22 14:23:45.234] INFO  : Auth: user=curator
[2025-04-22 14:23:45.345] INFO  : Query: contacts.get_all
[2025-04-22 14:23:45.346] DEBUG : SQL: SELECT * FROM contacts ORDER BY name
[2025-04-22 14:23:45.456] INFO  : Result: 127 rows in 110ms
[2025-04-22 14:23:45.457] INFO  : Output: ASCII table to stdout
```

---

## Output Formats

### ASCII Table (default stdout)
```
id | name          | email              | title
---|---------------|--------------------|--------
1  | Alice Smith   | alice@example.com  | Manager
2  | Bob Johnson   | bob@example.com    | Lead
3  | Carol White   | carol@example.com  | Engineer
```

**Details to nail down:**
- Column alignment: text left, numbers right?
- NULL representation: empty or `<null>`?
- Column width calculation?
- Truncate long values or wrap?

### JSON File (`--json FILE`)
```json
[
  {
    "id": 1,
    "name": "Alice Smith",
    "email": "alice@example.com",
    "title": "Manager"
  },
  {
    "id": 2,
    "name": "Bob Johnson",
    "email": "bob@example.com",
    "title": "Lead"
  }
]
```

### CSV File (`--csv FILE`)
```
id,name,email,title
1,Alice Smith,alice@example.com,Manager
2,Bob Johnson,bob@example.com,Lead
3,Carol White,carol@example.com,Engineer
```

**Details to nail down:**
- Quote all strings or only if needed?
- Escape quotes as `""` or `\"`?
- Include header row? (yes, assumed)

---

## Still to Decide

### Query Parameters
- Format: `--params '{"id": 5}'` (single JSON string)?
- Or: `--param id=5 --param name=test` (multiple flags)?
- Or: both options supported?
- How to pass NULL values? `--param id=null`?

### NULL Representation
- ASCII table: empty cell or `<null>`?
- CSV: empty or `NULL` or `\N`?
- JSON: `null` (JavaScript convention)?

### Output Formatting
- ASCII table: column widths, alignment, borders?
- Truncate very long rows or wrap?
- Max rows before warning?

### Interactive Mode
- If no `--query`, list all available queries and let user pick?
- Then prompt for params?
- Then confirm before executing?

### File Output
- Overwrite existing files or error?
- Create parent directories or error?
- Atomic writes (temp file + rename)?

### Log Location
- `~/.local/share/viewkit/query_tester.log`?
- Or configurable via env var?
- Rotate logs?

---

## Next Steps

1. **Finalize this design** in next conversation
2. **Implement YAML structure** and validation
3. **Build database connection layer** (using dbkit)
4. **Build query executor** (SELECT, INSERT, UPDATE, DELETE handling)
5. **Build output formatters** (ASCII, JSON, CSV)
6. **Build logging system**
7. **Build CLI argument parser**
8. **Write tests**
9. **Create sample queries.yaml** with test data

---

## Implementation Notes

- Use `dbkit.connection.AsyncDBConnection` for consistency with Curator
- Use `tabulate` library for ASCII table formatting (or custom if preferred)
- Use Python's `json` module for JSON output
- Use Python's `csv` module for CSV output
- Use Python's `logging` module for logging
- Make it a module: `python -m viewkit.query_tester`
- No external dependencies beyond what viewkit already has
