# test_routes_tags.py

**Path:** tests/unit/test_routes_tags.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
tests.unit.test_routes_tags - Unit tests for tag routes.

Tests cover route logic only — no database.
Repository methods patched with AsyncMock per test.

Covers:
  - GET  /tags/              — list all tags
  - GET  /tags/new           — form renders
  - POST /tags/new           — create redirects
  - GET  /tags/{id}/edit     — edit form found and not found
  - POST /tags/{id}/edit     — update redirects
  - POST /tags/{id}/delete   — delete redirects
"""

from unittest.mock import AsyncMock, patch

import pytest

from curator.exceptions import RecordNotFoundError


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _tag(**kwargs):
    base = {"id": 1, "name": "python", "category": "technology", "category_id": 2}
    return {**base, **kwargs}


def _category(**kwargs):
    base = {"id": 1, "name": "component", "sort_order": 1}
    return {**base, **kwargs}


# ---------------------------------------------------------------------------
# GET /tags/
# ---------------------------------------------------------------------------

class TestListTags:

    def test_returns_200(self, client):
        with patch("curator.web.routes.tags.TagRepository") as MockRepo:
            MockRepo.return_value.get_all = AsyncMock(return_value=[_tag()])
            response = client.get("/tags/")
        assert response.status_code == 200

    def test_empty_list_returns_200(self, client):
        with patch("curator.web.routes.tags.TagRepository") as MockRepo:
            MockRepo.return_value.get_all = AsyncMock(return_value=[])
            response = client.get("/tags/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /tags/new
# ---------------------------------------------------------------------------

class TestNewTagForm:

    def test_returns_200(self, client):
        with patch("curator.web.routes.tags.TagRepository") as MockRepo:
            MockRepo.return_value.get_category_options = AsyncMock(
                return_value=[_category()]
            )
            response = client.get("/tags/new")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /tags/new
# ---------------------------------------------------------------------------

class TestCreateTag:

    def test_redirects_to_list_on_success(self, client):
        with patch("curator.web.routes.tags.TagRepository") as MockRepo:
            MockRepo.return_value.create = AsyncMock(return_value=1)
            response = client.post(
                "/tags/new",
                data={"name": "python", "category_id": "2"},
                follow_redirects=False,
            )
        assert response.status_code == 303


# ---------------------------------------------------------------------------
# GET /tags/{id}/edit
# ---------------------------------------------------------------------------

class TestEditTagForm:

    def test_returns_200_when_found(self, client):
        with patch("curator.web.routes.tags.TagRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_by_id = AsyncMock(return_value=_tag())
            instance.get_category_options = AsyncMock(return_value=[_category()])
            response = client.get("/tags/1/edit")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client):
        with patch("curator.web.routes.tags.TagRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(
                side_effect=RecordNotFoundError("not found")
            )
            response = client.get("/tags/999/edit")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /tags/{id}/edit
# ---------------------------------------------------------------------------

class TestUpdateTag:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.tags.TagRepository") as MockRepo:
            MockRepo.return_value.update = AsyncMock(return_value=None)
            response = client.post(
                "/tags/1/edit",
                data={"name": "python", "category_id": "2"},
                follow_redirects=False,
            )
        assert response.status_code == 303


# ---------------------------------------------------------------------------
# POST /tags/{id}/delete
# ---------------------------------------------------------------------------

class TestDeleteTag:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.tags.TagRepository") as MockRepo:
            MockRepo.return_value.delete = AsyncMock(return_value=None)
            response = client.post("/tags/1/delete", follow_redirects=False)
        assert response.status_code == 303

```
