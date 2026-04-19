# test_tasks_repo.py

**Path:** tests/integration/test_tasks_repo.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
tests.integration.test_tasks_repo - Integration tests for TaskRepository.

All tests run against test_curator on steward via the floater account.
Each test is wrapped in a transaction that rolls back on completion.

Covers every method in curator.db.tasks.TaskRepository.
"""

import pytest
import pytest_asyncio

from curator.db.projects import ProjectRepository
from curator.db.tasks import TaskRepository
from curator.exceptions import DeleteBlockedError, RecordNotFoundError

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def task_repo(fake_db):
    return TaskRepository(fake_db)


@pytest_asyncio.fixture()
async def project_id(fake_db, lookup):
    """Create a minimal project and return its ID for task tests."""
    repo = ProjectRepository(fake_db)
    slug = await repo.create({
        "name": "Task Test Project",
        "description": None,
        "status_id": await lookup("project_status", "active"),
        "type_id": await lookup("project_type", "coding"),
        "parent_id": None,
        "target_date": None,
    })
    project = await repo.get_by_slug(slug)
    return project["id"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_task(repo, project_id, lookup, **kwargs) -> int:
    """Insert a minimal task and return its ID."""
    return await repo.create({
        "project_id": project_id,
        "description": kwargs.get("description", "Test task"),
        "status_id": await lookup("task_status", kwargs.get("status", "open")),
        "priority_id": await lookup("priority", kwargs.get("priority", "normal")),
        "parent_id": kwargs.get("parent_id", None),
        "links": kwargs.get("links", ""),
        "source_file": kwargs.get("source_file", ""),
        "sort_order": kwargs.get("sort_order", 0),
    })


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

class TestGetById:

    async def test_returns_task_dict(self, task_repo, project_id, lookup):
        task_id = await _create_task(task_repo, project_id, lookup)
        task = await task_repo.get_by_id(task_id)
        assert task["id"] == task_id

    async def test_raises_when_not_found(self, task_repo):
        with pytest.raises(RecordNotFoundError):
            await task_repo.get_by_id(999999)


# ---------------------------------------------------------------------------
# get_all_for_project
# ---------------------------------------------------------------------------

class TestGetAllForProject:

    async def test_returns_top_level_tasks_only(self, task_repo, project_id, lookup):
        parent_id = await _create_task(task_repo, project_id, lookup, description="Parent")
        await _create_task(
            task_repo, project_id, lookup,
            description="Child", parent_id=parent_id
        )
        top_level = await task_repo.get_all_for_project(project_id)
        assert all(t["parent_id"] is None for t in top_level)

    async def test_empty_project_returns_empty_list(self, task_repo, project_id):
        result = await task_repo.get_all_for_project(project_id)
        assert result == []


# ---------------------------------------------------------------------------
# get_tree_for_project
# ---------------------------------------------------------------------------

class TestGetTreeForProject:

    async def test_returns_all_tasks_including_subtasks(
        self, task_repo, project_id, lookup
    ):
        parent_id = await _create_task(task_repo, project_id, lookup, description="Root")
        await _create_task(
            task_repo, project_id, lookup,
            description="Leaf", parent_id=parent_id
        )
        tree = await task_repo.get_tree_for_project(project_id)
        assert len(tree) == 2


# ---------------------------------------------------------------------------
# get_subtasks
# ---------------------------------------------------------------------------

class TestGetSubtasks:

    async def test_returns_direct_children_only(self, task_repo, project_id, lookup):
        parent_id = await _create_task(task_repo, project_id, lookup, description="Parent")
        child_id = await _create_task(
            task_repo, project_id, lookup,
            description="Child", parent_id=parent_id
        )
        await _create_task(
            task_repo, project_id, lookup,
            description="Grandchild", parent_id=child_id
        )
        children = await task_repo.get_subtasks(parent_id)
        assert len(children) == 1
        assert children[0]["id"] == child_id


# ---------------------------------------------------------------------------
# get_child_count
# ---------------------------------------------------------------------------

class TestGetChildCount:

    async def test_zero_for_leaf_task(self, task_repo, project_id, lookup):
        task_id = await _create_task(task_repo, project_id, lookup)
        count = await task_repo.get_child_count(task_id)
        assert count == 0

    async def test_correct_count_for_parent(self, task_repo, project_id, lookup):
        parent_id = await _create_task(task_repo, project_id, lookup, description="P")
        await _create_task(task_repo, project_id, lookup, parent_id=parent_id)
        await _create_task(task_repo, project_id, lookup, parent_id=parent_id)
        count = await task_repo.get_child_count(parent_id)
        assert count == 2


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

class TestCreate:

    async def test_returns_integer_id(self, task_repo, project_id, lookup):
        task_id = await _create_task(task_repo, project_id, lookup)
        assert isinstance(task_id, int)

    async def test_created_task_is_retrievable(self, task_repo, project_id, lookup):
        task_id = await _create_task(
            task_repo, project_id, lookup, description="Unique description"
        )
        task = await task_repo.get_by_id(task_id)
        assert task["description"] == "Unique description"


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:

    async def test_update_changes_description(self, task_repo, project_id, lookup):
        task_id = await _create_task(task_repo, project_id, lookup, description="Before")
        await task_repo.update(task_id, {
            "description": "After",
            "status_id": await lookup("task_status", "open"),
            "priority_id": await lookup("priority", "normal"),
            "parent_id": None,
            "links": "",
            "sort_order": 0,
            "is_terminal": False,
        })
        task = await task_repo.get_by_id(task_id)
        assert task["description"] == "After"

    async def test_complete_status_sets_completed_at(self, task_repo, project_id, lookup):
        task_id = await _create_task(task_repo, project_id, lookup)
        await task_repo.update(task_id, {
            "description": "Done",
            "status_id": await lookup("task_status", "complete"),
            "priority_id": await lookup("priority", "normal"),
            "parent_id": None,
            "links": "",
            "sort_order": 0,
            "is_terminal": True,
        })
        task = await task_repo.get_by_id(task_id)
        assert task["completed_at"] is not None

    async def test_update_nonexistent_raises(self, task_repo, lookup):
        with pytest.raises(RecordNotFoundError):
            await task_repo.update(999999, {
                "description": "Ghost",
                "status_id": await lookup("task_status", "open"),
                "priority_id": await lookup("priority", "normal"),
                "parent_id": None,
                "links": "",
                "sort_order": 0,
                "is_terminal": False,
            })


# ---------------------------------------------------------------------------
# delete / force_delete
# ---------------------------------------------------------------------------

class TestDelete:

    async def test_delete_leaf_task(self, task_repo, project_id, lookup):
        task_id = await _create_task(task_repo, project_id, lookup)
        await task_repo.delete(task_id)
        with pytest.raises(RecordNotFoundError):
            await task_repo.get_by_id(task_id)

    async def test_delete_with_children_raises(self, task_repo, project_id, lookup):
        parent_id = await _create_task(task_repo, project_id, lookup, description="Parent")
        await _create_task(task_repo, project_id, lookup, parent_id=parent_id)
        with pytest.raises(DeleteBlockedError) as exc_info:
            await task_repo.delete(parent_id)
        assert exc_info.value.count == 1

    async def test_force_delete_removes_parent_and_children(
        self, task_repo, project_id, lookup
    ):
        parent_id = await _create_task(task_repo, project_id, lookup, description="Root")
        child_id = await _create_task(
            task_repo, project_id, lookup, parent_id=parent_id
        )
        await task_repo.force_delete(parent_id)
        with pytest.raises(RecordNotFoundError):
            await task_repo.get_by_id(parent_id)
        with pytest.raises(RecordNotFoundError):
            await task_repo.get_by_id(child_id)

    async def test_delete_nonexistent_raises(self, task_repo):
        with pytest.raises(RecordNotFoundError):
            await task_repo.delete(999999)


# ---------------------------------------------------------------------------
# Select options
# ---------------------------------------------------------------------------

class TestSelectOptions:

    async def test_status_options_non_empty(self, task_repo):
        options = await task_repo.get_status_options()
        assert len(options) > 0

    async def test_priority_options_non_empty(self, task_repo):
        options = await task_repo.get_priority_options()
        assert len(options) > 0

    async def test_parent_options_for_project(self, task_repo, project_id, lookup):
        await _create_task(task_repo, project_id, lookup, description="Top level")
        options = await task_repo.get_parent_options(project_id)
        assert len(options) >= 1

```
