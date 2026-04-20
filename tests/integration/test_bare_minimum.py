import pytest

pytestmark = pytest.mark.integration


async def test_db_only(test_db):
    """Does the session fixture even complete?"""
    assert test_db


async def test_db_conn(db_conn):
    """Does the per-test connection work in isolation?"""
    async with db_conn.cursor() as cur:
        await cur.execute("SELECT 1")
        row = await cur.fetchone()
    assert row is not None


async def test_lookup(lookup):
    """Does the lookup fixture work in isolation?"""
    result = await lookup("task_status", "open")
    assert isinstance(result, int)


async def test_both_fixtures(db_conn, lookup):
    """Does using both fixtures in the same test hang?"""
    result = await lookup("task_status", "open")
    assert isinstance(result, int)
    async with db_conn.cursor() as cur:
        await cur.execute("SELECT 1")
        row = await cur.fetchone()
    assert row is not None
async def test_fake_db(fake_db):
    """Does fake_db work in isolation?"""
    result = await fake_db.fetch_scalar("SELECT 1")
    assert result == 1


async def test_fake_db_with_lookup(fake_db, lookup):
    """Does fake_db + lookup together work?"""
    result = await lookup("task_status", "open")
    assert isinstance(result, int)
