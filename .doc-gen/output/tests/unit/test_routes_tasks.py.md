# test_routes_tasks.py

**Path:** tests/unit/test_routes_tasks.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
tests.unit.test_routes_tasks - Unit tests for task routes.

Tests cover route logic only — no database.
Repository methods patched with AsyncMock per test.

Covers:
  - GET  /tasks/project/{slug}      — list tasks, project not found
  - GET  /tasks/new/{slug}          — form renders, project not found
  - POST /tasks/new/{slug}          — create redirects
  - GET  /tasks/{id}/edit           — edit form found and not found
  - POST /tasks/{id}/edit           — update redirects
  - POST /tasks/{id}/delete         — delete redirects; DeleteBlockedError redirects with query params
  - POST /tasks/{id}/force-delete   — force delete redirects
"""

from unittest.mock import AsyncMock, patch

import pytest

from curator.exceptions import DeleteBlockedError, RecordNotFoundError


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _project(**kwargs):
    base = {"id": 1, "name": "Test Project", "slug": "test-project"}
    return {**base, **kwargs}


def _task(**kwargs):
    base = {
        "id": 1, "project_id": 1, "project_slug": "test-project",
        "description": "Do something", "status": "open",
        "status_display": "[ ]", "is_terminal": False,
        "priority": "normal", "parent_id": None,
        "parent_description": None, "sort_order": 1,
        "depth": 0,  # required by tasks/list.html template
        "path": "0001",
        "links": "", "source_file": "",
        "created_at": None, "updated_at": None, "completed_at": None,
    }
    return {**base, **kwargs}


# ---------------------------------------------------------------------------
# GET /tasks/project/{slug}
# ---------------------------------------------------------------------------

class TestListTasks:

    def test_returns_200_when_project_found(self, client):
        with patch("curator.web.routes.tasks.ProjectRepository") as MockProj, \
             patch("curator.web.routes.tasks.TaskRepository") as MockTask:
            MockProj.return_value.get_by_slug = AsyncMock(return_value=_project())
            MockTask.return_value.get_tree_for_project = AsyncMock(return_value=[_task()])
            response = client.get("/tasks/project/test-project")
        assert response.status_code == 200

    def test_returns_404_when_project_not_found(self, client):
        with patch("curator.web.routes.tasks.ProjectRepository") as MockProj:
            MockProj.return_value.get_by_slug = AsyncMock(
                side_effect=RecordNotFoundError("not found")
            )
            response = client.get("/tasks/project/no-such-slug")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /tasks/new/{slug}
# ---------------------------------------------------------------------------

class TestNewTaskForm:

    def test_returns_200_when_project_found(self, client):
        with patch("curator.web.routes.tasks.ProjectRepository") as MockProj, \
             patch("curator.web.routes.tasks.TaskRepository") as MockTask:
            MockProj.return_value.get_by_slug = AsyncMock(return_value=_project())
            MockTask.return_value.get_status_options = AsyncMock(return_value=[])
            MockTask.return_value.get_priority_options = AsyncMock(return_value=[])
            MockTask.return_value.get_parent_options = AsyncMock(return_value=[])
            response = client.get("/tasks/new/test-project")
        assert response.status_code == 200

    def test_returns_404_when_project_not_found(self, client):
        with patch("curator.web.routes.tasks.ProjectRepository") as MockProj:
            MockProj.return_value.get_by_slug = AsyncMock(
                side_effect=RecordNotFoundError("not found")
            )
            response = client.get("/tasks/new/no-such-slug")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /tasks/new/{slug}
# ---------------------------------------------------------------------------

class TestCreateTask:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.tasks.ProjectRepository") as MockProj, \
             patch("curator.web.routes.tasks.TaskRepository") as MockTask:
            MockProj.return_value.get_by_slug = AsyncMock(return_value=_project())
            MockTask.return_value.create = AsyncMock(return_value=42)
            response = client.post(
                "/tasks/new/test-project",
                data={
                    "description": "New task",
                    "status_id": "1",
                    "priority_id": "2",
                },
                follow_redirects=False,
            )
        assert response.status_code == 303


# ---------------------------------------------------------------------------
# GET /tasks/{id}/edit
# ---------------------------------------------------------------------------

class TestEditTaskForm:

    def test_returns_200_when_found(self, client):
        with patch("curator.web.routes.tasks.TaskRepository") as MockTask, \
             patch("curator.web.routes.tasks.ProjectRepository") as MockProj:
            MockTask.return_value.get_by_id = AsyncMock(return_value=_task())
            MockTask.return_value.get_status_options = AsyncMock(return_value=[])
            MockTask.return_value.get_priority_options = AsyncMock(return_value=[])
            MockTask.return_value.get_parent_options = AsyncMock(return_value=[])
            MockProj.return_value.get_by_id = AsyncMock(return_value=_project())
            response = client.get("/tasks/1/edit")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client):
        with patch("curator.web.routes.tasks.TaskRepository") as MockTask:
            MockTask.return_value.get_by_id = AsyncMock(
                side_effect=RecordNotFoundError("not found")
            )
            response = client.get("/tasks/999/edit")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /tasks/{id}/edit
# ---------------------------------------------------------------------------

class TestUpdateTask:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.tasks.TaskRepository") as MockTask:
            MockTask.return_value.update = AsyncMock(return_value=None)
            response = client.post(
                "/tasks/1/edit",
                data={
                    "description": "Updated",
                    "status_id": "1",
                    "priority_id": "2",
                    "is_terminal": "false",
                    "project_slug": "test-project",  # required Form field
                },
                follow_redirects=False,
            )
        assert response.status_code == 303


# ---------------------------------------------------------------------------
# POST /tasks/{id}/delete
# ---------------------------------------------------------------------------

class TestDeleteTask:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.tasks.TaskRepository") as MockTask:
            MockTask.return_value.delete = AsyncMock(return_value=None)
            response = client.post(
                "/tasks/1/delete",
                data={"project_slug": "test-project"},  # required Form field
                follow_redirects=False,
            )
        assert response.status_code == 303

    def test_delete_blocked_redirects_with_params(self, client):
        with patch("curator.web.routes.tasks.TaskRepository") as MockTask:
            MockTask.return_value.delete = AsyncMock(
                side_effect=DeleteBlockedError("has children", count=3)
            )
            response = client.post(
                "/tasks/1/delete",
                data={"project_slug": "test-project"},
                follow_redirects=False,
            )
        # Route redirects with delete_blocked query params rather than
        # rendering a confirm page directly
        assert response.status_code == 303
        assert "delete_blocked" in response.headers["location"]


# ---------------------------------------------------------------------------
# POST /tasks/{id}/force-delete
# ---------------------------------------------------------------------------

class TestForceDeleteTask:

    def test_redirects_on_success(self, client):
        with patch("curator.web.routes.tasks.TaskRepository") as MockTask:
            MockTask.return_value.force_delete = AsyncMock(return_value=None)
            response = client.post(
                "/tasks/1/force-delete",
                data={"project_slug": "test-project"},  # required Form field
                follow_redirects=False,
            )
        assert response.status_code == 303

```
