# Curator — Test Suite Guide

*Operational reference for running, extending, and understanding the test suite.*
*Last updated: April 2026*

---

## Overview

The Curator test suite has two independent tiers that serve different purposes and run independently. They share no fixtures and have no dependencies on each other.

**Unit tests** (~49 tests) test route logic only. All database calls are patched with `AsyncMock`. No database connection required. This is the default `pytest` run — fast, no infrastructure.

**Integration tests** (~70 tests) test repository classes against a real PostgreSQL database (`test_curator` on steward) via the `floater` role. Each test runs inside a transaction that is always rolled back on exit, leaving the database clean for the next test. These require steward to be reachable and credentials in `tests/.env.test`.

Neither tier tests templates directly. The unit tests verify that routes return the correct HTTP status codes and redirect targets. Whether a template renders correctly is a manual concern.

---

## Quick Reference

```bash
# Unit tests only — default, no DB required
pytest

# Integration tests only
pytest -m integration -v

# Both tiers together
pytest -m "integration or not integration" -v

# One integration test file
pytest tests/integration/test_tasks_repo.py -v -m integration
```

---

## Infrastructure Prerequisites (Integration Tests)

### `tests/.env.test`

Integration tests load credentials from `tests/.env.test`, which is gitignored. The file is not committed. The password is in Proton vault. Format:

```
DBKIT_HOST=100.64.0.10
DBKIT_PORT=5432
DBKIT_DBNAME=test_curator
DBKIT_USER=floater
DBKIT_PASSWORD=<from vault>
```

The top-level `conftest.py` loads this file at session start via `python-dotenv`. If the file is missing, integration tests will fail immediately with a `KeyError` on `DBKIT_HOST`.

### `floater` Postgres Role

`floater` is the dedicated test role on steward. It has `CREATEDB` privilege and no access to the production `projects` database. It owns `test_curator`. See `pgpass.md` and the crew roster for full details.

### `test_curator` Database

`test_curator` is created automatically by the session fixture if it does not exist. The schema and seed SQL are applied on every run via `psql` subprocess — `schema.sql` has a full `DROP ... IF EXISTS CASCADE` preamble, so re-running it against an existing database is a safe reset. No manual setup or teardown is required.

### Schema and Seed SQL Source

The session fixture looks for schema and seed files in this order:

1. Local clone at `~/projects/steward/data/projects/` (preferred — faster, works offline)
2. Raw GitHub URL fallback: `https://raw.githubusercontent.com/carolynboyle/steward/main/data/projects/`

If steward connectivity is available but the local clone is absent, the fallback works transparently.

### `asyncio_mode = "auto"`

Integration test classes use `async def test_*` methods with no `@pytest.mark.asyncio` decorator on each method. This works because Curator's `pyproject.toml` contains:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
```

If either setting is removed, async tests will fail with a confusing "coroutine was never awaited" error. The `loop_scope = "session"` setting is required to prevent the event loop mismatch deadlock described in the Known Issues section below.

---

## How Test Isolation Works

Every integration test runs inside a psycopg transaction that is unconditionally rolled back when the test exits:

```python
async with conn.transaction():
    yield conn
    raise psycopg.Rollback()   # always rolls back, pass or fail
```

This means:

- No teardown scripts are needed
- The database is always at the seeded baseline at the start of each test
- Tests can freely insert, update, and delete — nothing persists
- Tests are fully independent and can run in any order

The `lookup` fixture uses a **separate `autocommit=True` connection** outside the rollback transaction. This is intentional: lookup table reads (`task_status`, `priority`, etc.) should always see the seeded baseline regardless of what the test transaction has done, and should not appear as `idle in transaction` sessions on steward.

---

## Fixture Reference

All fixtures are defined in `tests/integration/conftest.py`.

### `test_db` (session scope)

Creates `test_curator` if it does not exist, then runs `schema.sql` and `seed.sql` via `psql` subprocess. Yields the database name string. Runs once per pytest session.

Yields: `str` (database name)

### `db_conn` (function scope)

Opens a psycopg `AsyncConnection` inside a rollback transaction. Yields the connection for use by `fake_db` and any test that needs raw SQL access.

Depends on: `test_db`
Yields: `psycopg.AsyncConnection`

### `lookup` (function scope)

Yields a coroutine that resolves a lookup table name to its integer ID. Uses a separate `autocommit=True` connection so it is not affected by the per-test rollback.

```python
status_id = await lookup("task_status", "open")
priority_id = await lookup("priority", "normal")
```

Depends on: `test_db`
Yields: `async callable(table: str, name: str) -> int`

### `fake_db` (function scope)

Returns a `_FakeAsyncDBConnection` wrapping the rollback transaction connection. Pass this to repository constructors instead of a real `AsyncDBConnection`.

```python
def test_something(fake_db):
    repo = ProjectRepository(fake_db)
```

Depends on: `db_conn`
Returns: `_FakeAsyncDBConnection`

### `_FakeAsyncDBConnection`

A minimal shim that wraps a psycopg `AsyncConnection` and exposes the same interface as `dbkit.AsyncDBConnection`: `fetch_all`, `fetch_one`, `fetch_scalar`, `execute`. Cursors are created explicitly per call with `row_factory=dict_row` to ensure text columns return as `str`, not `bytes`.

This class is not a fixture — it is instantiated by the `fake_db` fixture.

---

## Writing New Tests

### Unit Test Pattern

Unit tests live in `tests/unit/`. They use FastAPI's `TestClient` and patch repository classes with `AsyncMock`.

```python
class TestSomeRoute:

    def test_returns_200_when_found(self, client):
        """Route renders successfully when repository returns data."""
        with patch("curator.web.routes.things.ThingRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=_thing())
            response = client.get("/things/1")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client):
        """Route returns 404 when repository raises RecordNotFoundError."""
        with patch("curator.web.routes.things.ThingRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(
                side_effect=RecordNotFoundError("not found")
            )
            response = client.get("/things/999")
        assert response.status_code == 404
```

Key conventions:
- Always use `follow_redirects=False` on POST requests and assert `status_code == 303`
- Factory functions (`_thing(**kwargs)`) provide default fixture dicts; use `**kwargs` override pattern
- Patch the repository at the route module's import path, not the source module
- The `client` fixture overrides both `get_db` and `get_query_loader` with mocks — routes that use the query loader will receive a `MagicMock()` and won't exercise the actual YAML wiring

Individual test methods should have a one-line docstring explaining what condition is being tested and what the expected outcome is. See `test_setupkit.py` for the established pattern.

### Integration Test Pattern

Integration tests live in `tests/integration/`. One file per repository class.

```python
pytestmark = pytest.mark.integration


@pytest.fixture()
def thing_repo(fake_db):
    return ThingRepository(fake_db)


async def _create_thing(repo, lookup, **kwargs) -> int:
    """Insert a minimal thing and return its ID."""
    return await repo.create({
        "name": kwargs.get("name", "test thing"),
        "category_id": await lookup("thing_category", kwargs.get("category", "default")),
    })


class TestCreate:

    async def test_returns_integer_id(self, thing_repo, lookup):
        """create() returns an integer primary key."""
        thing_id = await _create_thing(thing_repo, lookup)
        assert isinstance(thing_id, int)
```

Key conventions:
- `pytestmark = pytest.mark.integration` at module level — no decorator per test
- One `*_repo` fixture per file; receives `fake_db` and constructs the repository
- `_create_*` helper function (not a fixture) for inserting test data — see the section below on why
- `999999` as the sentinel ID for "record that does not exist"
- Individual test methods should have a one-line docstring

### The `_create_*` Helper — Why It's a Function, Not a Fixture

**Do not make `project_id` (or any analogous setup value) an async fixture.** Use an inline async helper function called directly inside each test instead.

```python
# CORRECT — inline helper
async def _make_project(fake_db, lookup) -> int:
    repo = ProjectRepository(fake_db)
    slug = await repo.create({
        "name": "Test Project",
        "status_id": await lookup("project_status", "active"),
        "type_id": await lookup("project_type", "coding"),
        "description": None,
        "parent_id": None,
        "target_date": None,
    })
    project = await repo.get_by_slug(slug)
    return project["id"]

async def test_something(self, thing_repo, fake_db, lookup):
    """Test description here."""
    project_id = await _make_project(fake_db, lookup)
    # ... rest of test
```

```python
# WRONG — async fixture for a setup value
@pytest_asyncio.fixture()
async def project_id(fake_db, lookup):   # do not do this
    ...
```

**Why:** pytest-asyncio has known reliability issues with function-scoped async fixtures that depend on session-scoped async fixtures, even with explicit `loop_scope`. The symptom is a silent deadlock — the test suite hangs indefinitely with no output, and `pg_stat_activity` on steward shows connections in `idle in transaction / ClientRead`. The inline helper pattern avoids the async fixture dependency chain entirely.

All four existing integration test files (`test_projects_repo.py`, `test_tasks_repo.py`, `test_files_repo.py`, `test_tags_repo.py`) use the inline helper pattern consistently. Every test that needs a project calls `_make_project(fake_db, lookup)` directly. There are no async fixtures for setup values in the suite.

---

## `test_dbkit_connection.py` — Diagnostic Script, Not a Test

`python/dbkit/tests/test_dbkit_connection.py` in the dev-utils repo is a manual connectivity diagnostic, not a pytest file. It has no pytest imports, no assertions, and uses `print()` and `exit()`. It verifies that dbkit can connect to steward and query the `projects` table. It is run directly:

```bash
python test_dbkit_connection.py
```

It is not part of the pytest suite and will not be collected by pytest. It is useful when troubleshooting a new machine setup or a broken steward connection. It is not a model for writing tests.

---

## Known Issues and Gotchas

### 1. `pg_dump` Output Cannot Be Executed by psycopg

`schema.sql` is generated by `pg_dump` and contains psql meta-commands (`\restrict`, `\unrestrict`). Passing it to `conn.execute()` raises `SyntaxError`. It must be executed via `subprocess.run(["psql", ...])`. The session fixture does this correctly. Do not change it to use psycopg directly.

### 2. Event Loop Mismatch Deadlock

**Symptom:** Test suite hangs indefinitely. `pg_stat_activity` on steward shows connections in `idle in transaction / ClientRead` with `blocked_by = {}`.

**Cause:** A psycopg socket opened on event loop A cannot be awaited on loop B. Function-scoped async fixtures that depend on session-scoped async fixtures can silently create this situation.

**Fix:** `asyncio_default_fixture_loop_scope = "session"` in `pyproject.toml`, explicit `loop_scope="session"` on all `@pytest_asyncio.fixture` decorators, and — most importantly — no async fixtures for values that can be produced by inline helper functions.

### 3. psycopg Returns `bytes` for Text Columns

**Symptom:** `assert b'some-slug' == 'some-slug'` fails.

**Cause:** `row_factory=dict_row` on a connection is not automatically inherited by cursors created manually via `conn.cursor()`.

**Fix:** `_FakeAsyncDBConnection` passes `row_factory=psycopg.rows.dict_row` explicitly when creating every cursor. Do not create cursors from `db_conn` directly in tests — always go through `fake_db`.

### 4. Task Status In-Progress → Complete Bug

Changing a task from `in_progress` to `complete` via the edit form does not save correctly. The integration test `test_complete_status_sets_completed_at` passes (the repository is correct), which confirms the bug is in the route or form handling, not the repository. There is no failing test for this yet.

---

## File Structure

```
tests/
├── .env.test                        # gitignored — floater credentials (password in Proton vault)
├── __init__.py
├── conftest.py                      # loads .env.test, registers pytest.mark.integration
├── unit/
│   ├── __init__.py
│   ├── conftest.py                  # TestClient; overrides get_db and get_query_loader
│   ├── test_config.py               # ConfigManager (synchronous — no async)
│   ├── test_routes_files.py
│   ├── test_routes_projects.py
│   ├── test_routes_tags.py
│   └── test_routes_tasks.py
└── integration/
    ├── __init__.py
    ├── conftest.py                  # DB bootstrap, per-test rollback, _FakeAsyncDBConnection
    ├── test_bare_minimum.py         # fixture smoke tests — keep for infrastructure diagnostics
    ├── test_files_repo.py
    ├── test_projects_repo.py
    ├── test_tags_repo.py
    └── test_tasks_repo.py
```

The `test_config.py` file is worth noting as the pattern for testing non-async code: plain `def test_*` methods, no async fixtures, no `pytestmark`. If a module under test has no async code, the test file should have none either.

`test_bare_minimum.py` is fixture infrastructure smoke tests — it verifies that `test_db`, `db_conn`, `lookup`, `fake_db`, and combinations thereof all work in isolation. It is not testing application code. Keep it in place; it is the first thing to run when a new machine is being set up or the fixture infrastructure is suspected to be broken. It is not a model for writing application tests.

---

## Style Conventions Summary

| Convention | Rule |
|---|---|
| Module docstring | Required on every test file; include "Covers:" list |
| Test method docstring | One line per method explaining the condition and expected outcome |
| Section dividers | `# ---` with the class name as the comment |
| Class naming | `TestMethodName` — one class per public method or logical behaviour group |
| Parametrize | Not currently used; prefer explicit test methods with descriptive names |
| `match=` on `pytest.raises` | Required — always assert the exception message, not just the type |
| Sentinel ID | `999999` for "record does not exist" |
| `follow_redirects=False` | Required on all POST requests in unit tests |
| Async fixtures for setup values | Do not use — use inline async helpers instead |
| `@pytest.fixture()` | Always include parentheses for consistency |
