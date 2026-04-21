"""
tests.unit.test_routes_files - Unit tests for file attachment routes.

Tests cover route logic only — no database.
Repository methods patched with AsyncMock per test.

Covers:
  - GET  /files/new                 — form renders (project or task scoped)
  - POST /files/new                 — create redirects
  - GET  /files/{id}/edit           — edit form found and not found
  - POST /files/{id}/edit           — update redirects
  - POST /files/{id}/delete         — delete redirects
"""

from unittest.mock import AsyncMock, patch

import pytest

from curator.exceptions import RecordNotFoundError


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _file(**kwargs):
    base = {
        "id": 1, "label": "source repo", "location": "https://github.com/example",
        "notes": None, "file_type": "other", "location_type": "git",
        "project_id": 1, "task_id": None,
        "file_type_id": 1, "location_type_id": 3,
    }
    return {**base, **kwargs}


def _option(opt_id: int, name: str):
    return {"id": opt_id, "name": name, "sort_order": opt_id}


# ---------------------------------------------------------------------------
# GET /files/new
# ---------------------------------------------------------------------------

class TestNewFileForm:

    def test_returns_200_project_scoped(self, client):
        with patch("curator.web.routes.files.FileRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_file_type_options = AsyncMock(return_value=[_option(1, "other")])
            instance.get_location_type_options = AsyncMock(return_value=[_option(1, "git")])
            response = client.get("/files/new?project_id=1")
        assert response.status_code == 200

    def test_returns_200_task_scoped(self, client):
        with patch("curator.web.routes.files.FileRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_file_type_options = AsyncMock(return_value=[_option(1, "other")])
            instance.get_location_type_options = AsyncMock(return_value=[_option(1, "git")])
            response = client.get("/files/new?task_id=1")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /files/new
# ---------------------------------------------------------------------------

class TestCreateFile:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.files.FileRepository") as MockRepo:
            MockRepo.return_value.create = AsyncMock(return_value=1)
            response = client.post(
                "/files/new",
                data={
                    "project_id": "1",
                    "label": "source repo",
                    "file_type_id": "1",
                    "location": "https://github.com/example",
                    "location_type_id": "3",
                },
                follow_redirects=False,
            )
        assert response.status_code == 303


# ---------------------------------------------------------------------------
# GET /files/{id}/edit
# ---------------------------------------------------------------------------

class TestEditFileForm:

    def test_returns_200_when_found(self, client):
        with patch("curator.web.routes.files.FileRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_by_id = AsyncMock(return_value=_file())
            instance.get_file_type_options = AsyncMock(return_value=[_option(1, "other")])
            instance.get_location_type_options = AsyncMock(return_value=[_option(1, "git")])
            response = client.get("/files/1/edit")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client):
        with patch("curator.web.routes.files.FileRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(
                side_effect=RecordNotFoundError("not found")
            )
            response = client.get("/files/999/edit")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /files/{id}/edit
# ---------------------------------------------------------------------------

class TestUpdateFile:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.files.FileRepository") as MockRepo:
            MockRepo.return_value.update = AsyncMock(return_value=None)
            response = client.post(
                "/files/1/edit",
                data={
                    "label": "updated label",
                    "file_type_id": "1",
                    "location": "https://github.com/example",
                    "location_type_id": "3",
                },
                follow_redirects=False,
            )
        assert response.status_code == 303


# ---------------------------------------------------------------------------
# POST /files/{id}/delete
# ---------------------------------------------------------------------------

class TestDeleteFile:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.files.FileRepository") as MockRepo:
            MockRepo.return_value.delete = AsyncMock(return_value=None)
            response = client.post("/files/1/delete", follow_redirects=False)
        assert response.status_code == 303
