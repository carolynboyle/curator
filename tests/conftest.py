"""Pytest configuration for Curator tests."""

import pytest


@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from curator.web.app import app
    
    return TestClient(app)