"""
tests.integration.conftest - Fixtures for integration tests.

All integration tests are marked @pytest.mark.integration and skipped
by default. Run them with: pytest -m integration

DB lifecycle:
  - session scope: creates test_curator if it doesn't exist, runs
    schema.sql and seed.sql to establish a clean schema with lookup data.
    The floater Postgres role owns test_curator (CREATEDB privilege).
  - function scope: each test runs inside a transaction that is rolled
    back after the test completes. No teardown scripts needed.

Environment variables (loaded from tests/.env.test via top-level conftest):
    DBKIT_HOST, DBKIT_PORT, DBKIT_DBNAME, DBKIT_USER, DBKIT_PASSWORD

SQL scripts are loaded from the local steward repo clone at
~/projects/steward/data/projects/ with a fallback to raw GitHub URLs.
They are executed via psql (not psycopg) because pg_dump output contains
psql meta-commands that psycopg cannot handle.

All async fixtures use explicit loop_scope="session" to ensure every
psycopg connection runs on the same event loop, avoiding the classic
pytest-asyncio loop-mismatch deadlock.

Connection uses psycopg (same driver as dbkit) — no asyncpg dependency.
"""

import os
import subprocess
import urllib.request
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
import pytest_asyncio

# SQL scripts — local clone preferred, GitHub fallback
_STEWARD_LOCAL = Path.home() / "projects" / "steward" / "data" / "projects"
_STEWARD_RAW = "https://raw.githubusercontent.com/carolynboyle/steward/main/data/projects"


def _get_sql(filename: str) -> str:
    """
    Return SQL file contents.

    Uses the local steward repo clone if present at
    ~/projects/steward/data/projects/, otherwise fetches from GitHub.

    Args:
        filename: SQL filename, e.g. "schema.sql" or "seed.sql".

    Returns:
        SQL file contents as a string.
    """
    local = _STEWARD_LOCAL / filename
    if local.exists():
        return local.read_text(encoding="utf-8")
    with urllib.request.urlopen(f"{_STEWARD_RAW}/{filename}") as r:
        return r.read().decode("utf-8")


def _dsn(dbname: str | None = None) -> str:
    """Build a psycopg DSN string from environment variables."""
    host = os.environ["DBKIT_HOST"]
    port = os.environ.get("DBKIT_PORT", "5432")
    db = dbname or os.environ["DBKIT_DBNAME"]
    user = os.environ["DBKIT_USER"]
    password = os.environ["DBKIT_PASSWORD"]
    return f"host={host} port={port} dbname={db} user={user} password={password}"


# ---------------------------------------------------------------------------
# Session-scoped: create and bootstrap test_curator once per pytest run
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_db():
    """
    Create test_curator if it doesn't exist, then run schema.sql and seed.sql.

    schema.sql is a pg_dump output containing psql meta-commands, so it
    is executed via psql rather than psycopg. PGPASSWORD covers auth.

    schema.sql has full DROP ... IF EXISTS CASCADE preamble, so re-running
    it against an existing test_curator is a safe reset — no need to drop
    and recreate the database on every run.

    Yields the database name string.
    """
    dbname = os.environ["DBKIT_DBNAME"]
    host = os.environ["DBKIT_HOST"]
    port = os.environ.get("DBKIT_PORT", "5432")
    user = os.environ["DBKIT_USER"]

    # CREATE DATABASE cannot run inside a transaction — use autocommit
    async with await psycopg.AsyncConnection.connect(
        _dsn(dbname="postgres"), autocommit=True
    ) as conn:
        cur = await conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        )
        row = await cur.fetchone()
        if not row:
            await conn.execute(f'CREATE DATABASE "{dbname}"')

    # Pass password explicitly — more reliable than .pgpass in subprocess
    env = os.environ.copy()
    env["PGPASSWORD"] = os.environ["DBKIT_PASSWORD"]

    # Run schema and seed via psql — pg_dump output requires psql client
    # to handle \restrict and other meta-commands.
    for filename in ("schema.sql", "seed.sql"):
        sql = _get_sql(filename)
        subprocess.run(
            ["psql", "-h", host, "-p", port, "-U", user, "-d", dbname],
            input=sql.encode("utf-8"),
            check=True,
            capture_output=True,
            env=env,
        )

    yield dbname


# ---------------------------------------------------------------------------
# Function-scoped: transaction per test, rolled back on exit
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(loop_scope="session")
async def db_conn(test_db):
    """
    Yield an open psycopg AsyncConnection inside a transaction.

    The transaction is rolled back after the test completes, leaving
    test_curator in a clean state for the next test.

    The connection uses dict-style row factory so results match
    what dbkit's fetch_all / fetch_one return.
    """
    async with await psycopg.AsyncConnection.connect(
        _dsn(), row_factory=psycopg.rows.dict_row
    ) as conn:
        async with conn.transaction():
            yield conn
            raise psycopg.Rollback()


# ---------------------------------------------------------------------------
# Convenience: lookup ID helper
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(loop_scope="session")
async def lookup(test_db):
    """
    Yield a coroutine that fetches a lookup table ID by name.

    Uses a separate autocommit connection outside the rollback transaction
    so lookup table reads are always against the seeded baseline and do
    not appear as idle-in-transaction sessions on steward.

    Usage:
        status_id = await lookup("task_status", "open")
        priority_id = await lookup("priority", "normal")
    """
    async with await psycopg.AsyncConnection.connect(
        _dsn(), row_factory=psycopg.rows.dict_row, autocommit=True
    ) as conn:
        async def _get(table: str, name: str) -> int:
            cur = await conn.execute(
                f"SELECT id FROM {table} WHERE name = %s", (name,)  # noqa: S608
            )
            row = await cur.fetchone()
            if row is None:
                raise KeyError(
                    f"{table}.name = {name!r} not found in test_curator"
                )
            return row["id"]

        yield _get


# ---------------------------------------------------------------------------
# Convenience: wrap a psycopg connection in a minimal AsyncDBConnection shell
# ---------------------------------------------------------------------------

class _FakeAsyncDBConnection:
    """
    Minimal stand-in for dbkit.AsyncDBConnection for integration tests.

    Wraps a psycopg AsyncConnection and delegates fetch_all / fetch_one /
    fetch_scalar / execute to it using the same calling convention as
    dbkit.

    Cursors are created explicitly per call with the correct row factory
    to ensure text columns are returned as str, not bytes.
    """

    def __init__(self, conn):
        self._conn = conn

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        cur = self._conn.cursor(row_factory=psycopg.rows.dict_row)
        await cur.execute(sql, params or None)
        rows = await cur.fetchall()
        return [
            {k: v.decode() if isinstance(v, bytes) else v for k, v in r.items()}
            for r in rows
        ]
    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        cur = self._conn.cursor(row_factory=psycopg.rows.dict_row)
        await cur.execute(sql, params or None)
        row = await cur.fetchone()
        if row is None:
            return None
        return {k: v.decode() if isinstance(v, bytes) else v for k, v in row.items()}

    async def fetch_scalar(self, sql: str, params: tuple = ()):
        async with self._conn.cursor() as cur:
            await cur.execute(sql, params or None)
            row = await cur.fetchone()
            if row is None:
                return None
            return next(iter(row.values()))

    async def execute(self, sql: str, params: tuple = ()) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, params or None)


@pytest.fixture()
def fake_db(db_conn):
    """
    Return a _FakeAsyncDBConnection wrapping the rollback transaction connection.

    Pass this to repository constructors in integration tests instead of
    a real AsyncDBConnection.

    Usage:
        async def test_something(fake_db):
            repo = ProjectRepository(fake_db)
            result = await repo.get_all()
    """
    return _FakeAsyncDBConnection(db_conn)
