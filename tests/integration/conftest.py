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

Connection uses psycopg (same driver as dbkit) — no asyncpg dependency.
"""

import os
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
import pytest_asyncio

# SQL scripts are in the curator repo root
_REPO_ROOT = Path(__file__).parent.parent.parent
_SCHEMA_SQL = _REPO_ROOT / "schema.sql"
_SEED_SQL = _REPO_ROOT / "seed.sql"


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

@pytest_asyncio.fixture(scope="session")
async def test_db():
    """
    Create test_curator if it doesn't exist, then run schema.sql and seed.sql.

    schema.sql has full DROP ... IF EXISTS CASCADE preamble, so re-running
    it against an existing test_curator is a safe reset — no need to drop
    and recreate the database on every run.

    Yields the database name string.
    """
    dbname = os.environ["DBKIT_DBNAME"]

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

    # Bootstrap schema and seed — psycopg executes multi-statement SQL fine
    async with await psycopg.AsyncConnection.connect(_dsn()) as conn:
        schema_sql = _SCHEMA_SQL.read_text(encoding="utf-8")
        seed_sql = _SEED_SQL.read_text(encoding="utf-8")
        await conn.execute(schema_sql)
        await conn.execute(seed_sql)

    yield dbname


# ---------------------------------------------------------------------------
# Function-scoped: transaction per test, rolled back on exit
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
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

@pytest_asyncio.fixture()
async def lookup(test_db):
    """
    Yield a coroutine that fetches a lookup table ID by name.

    Uses a separate connection outside the rollback transaction so
    lookup table reads are always against the seeded baseline.

    Usage:
        status_id = await lookup("task_status", "open")
        priority_id = await lookup("priority", "normal")
    """
    async with await psycopg.AsyncConnection.connect(
        _dsn(), row_factory=psycopg.rows.dict_row
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
    dbkit. This avoids bypassing AsyncDBConnection's constructor with
    __new__ and keeps test internals independent of dbkit implementation
    details beyond the public method signatures.
    """

    def __init__(self, conn):
        self._conn = conn

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        cur = await self._conn.execute(sql, params or None)
        return await cur.fetchall()

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        cur = await self._conn.execute(sql, params or None)
        return await cur.fetchone()

    async def fetch_scalar(self, sql: str, params: tuple = ()):
        cur = await self._conn.execute(sql, params or None)
        row = await cur.fetchone()
        if row is None:
            return None
        return next(iter(row.values()))

    async def execute(self, sql: str, params: tuple = ()) -> None:
        await self._conn.execute(sql, params or None)


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