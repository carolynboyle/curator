"""
tests.unit.conftest - Shared fixtures for unit tests.

Provides a FastAPI TestClient with get_db and get_query_loader overridden
so route tests never touch the database. Repository methods are patched
individually per test using unittest.mock.AsyncMock.

Fixtures:
    client      — TestClient with DB and loader dependencies neutralised.
    mock_config — A ConfigManager pointed at the shipped defaults, for
                  routes that call config.views_path or config.queries_path.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from curator.web.app import app
from curator.web.deps import get_config, get_db, get_query_loader


# ---------------------------------------------------------------------------
# Stub dependencies
# ---------------------------------------------------------------------------

async def _no_db():
    """Yield a mock DB connection — never touches Postgres."""
    yield AsyncMock()


def _no_loader():
    """Return a mock QueryLoader — never reads queries.yaml."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    TestClient with database and query loader dependencies overridden.

    Route handlers receive AsyncMock objects for db and loader.
    Patch repository methods on a per-test basis with AsyncMock.
    """
    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_query_loader] = _no_loader
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_config():
    """
    ConfigManager backed by shipped defaults.

    Useful for tests that need a real views_path or queries_path
    without caring about user overrides.
    """
    from curator.config import ConfigManager
    return ConfigManager()