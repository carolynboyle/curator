# test_routes_projects.py

**Path:** tests/unit/test_routes_projects.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
tests.unit.test_routes_projects - Unit tests for project routes.

Tests cover route logic only — no database, no templates rendered to disk.
Repository methods are patched with AsyncMock per test.

Covers:
  - GET  /projects/           — list, with and without status filter
  - GET  /projects/new        — form renders
  - POST /projects/new        — create redirects to detail
  - GET  /projects/{slug}     — detail found and not found (404)
  - GET  /projects/{slug}/edit — edit form found and not found
  - POST /projects/{slug}/edit — update redirects
  - POST /projects/{slug}/delete — delete redirects to board
"""

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal project/task/tag/file dict factories
# ---------------------------------------------------------------------------

def _project(**kwargs):
    base = {
        "id": 1, "name": "Test Project", "slug": "test-project",
        "description": None, "status": "active", "type": "coding",
        "parent_id": None, "target_date": None,
        "open_task_count": 0, "created_at": None, "updated_at": None,
    }
    return {**base, **kwargs}


def _option(id: int, name: str):
    return {"id": id, "name": name, "sort_order": id}


# ---------------------------------------------------------------------------
# GET /projects/
# ---------------------------------------------------------------------------

class TestListProjects:

    def test_returns_200(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_all = AsyncMock(return_value=[_project()])
            instance.get_status_options = AsyncMock(return_value=[])
            response = client.get("/projects/")
        assert response.status_code == 200

    def test_status_filter_passed_to_repo(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_all = AsyncMock(return_value=[])
            instance.get_status_options = AsyncMock(return_value=[])
            client.get("/projects/?status=active")
            instance.get_all.assert_called_once_with(status="active")

    def test_empty_list_returns_200(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_all = AsyncMock(return_value=[])
            instance.get_status_options = AsyncMock(return_value=[])
            response = client.get("/projects/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /projects/new
# ---------------------------------------------------------------------------

class TestNewProjectForm:

    def test_returns_200(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_status_options = AsyncMock(return_value=[_option(1, "active")])
            instance.get_type_options = AsyncMock(return_value=[_option(1, "coding")])
            instance.get_parent_options = AsyncMock(return_value=[])
            response = client.get("/projects/new")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /projects/new
# ---------------------------------------------------------------------------

class TestCreateProject:

    def test_redirects_to_detail_on_success(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.create = AsyncMock(return_value="new-project")
            response = client.post(
                "/projects/new",
                data={"name": "New Project", "status_id": "1"},
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert response.headers["location"] == "/projects/new-project"


# ---------------------------------------------------------------------------
# GET /projects/{slug}
# ---------------------------------------------------------------------------

class TestProjectDetail:

    def test_returns_200_when_found(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockProjRepo, \
             patch("curator.web.routes.projects.TaskRepository") as MockTaskRepo, \
             patch("curator.web.routes.projects.TagRepository") as MockTagRepo, \
             patch("curator.web.routes.projects.FileRepository") as MockFileRepo:
            MockProjRepo.return_value.get_by_slug = AsyncMock(return_value=_project())
            MockProjRepo.return_value.get_subprojects = AsyncMock(return_value=[])
            MockTaskRepo.return_value.get_tree_for_project = AsyncMock(return_value=[])
            MockTagRepo.return_value.get_for_project = AsyncMock(return_value=[])
            MockFileRepo.return_value.get_for_project = AsyncMock(return_value=[])
            response = client.get("/projects/test-project")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client):
        from curator.exceptions import RecordNotFoundError
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            MockRepo.return_value.get_by_slug = AsyncMock(
                side_effect=RecordNotFoundError("not found")
            )
            response = client.get("/projects/no-such-slug")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{slug}/edit
# ---------------------------------------------------------------------------

class TestEditProjectForm:

    def test_returns_200_when_found(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_by_slug = AsyncMock(return_value=_project())
            instance.get_status_options = AsyncMock(return_value=[])
            instance.get_type_options = AsyncMock(return_value=[])
            instance.get_parent_options = AsyncMock(return_value=[])
            response = client.get("/projects/test-project/edit")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client):
        from curator.exceptions import RecordNotFoundError
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            MockRepo.return_value.get_by_slug = AsyncMock(
                side_effect=RecordNotFoundError("not found")
            )
            response = client.get("/projects/no-such-slug/edit")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /projects/{slug}/edit
# ---------------------------------------------------------------------------

class TestUpdateProject:

    def test_redirects_to_detail_on_success(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            MockRepo.return_value.update = AsyncMock(return_value=None)
            response = client.post(
                "/projects/test-project/edit",
                data={"name": "Updated", "status_id": "1"},
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert response.headers["location"] == "/projects/test-project"


# ---------------------------------------------------------------------------
# POST /projects/{slug}/delete
# ---------------------------------------------------------------------------

class TestDeleteProject:

    def test_redirects_to_board_on_success(self, client):
        with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
            MockRepo.return_value.delete = AsyncMock(return_value=None)
            response = client.post(
                "/projects/test-project/delete",
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "/projects/" in response.headers["location"]

```
