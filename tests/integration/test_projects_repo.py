"""
tests.integration.test_projects_repo - Integration tests for ProjectRepository.

All tests run against test_curator on steward via the floater account.
Each test is wrapped in a transaction that rolls back on completion.

Covers every method in curator.db.projects.ProjectRepository.
"""

import pytest
import pytest_asyncio

from curator.db.projects import ProjectRepository
from curator.exceptions import RecordNotFoundError

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixture: repo backed by the rollback transaction connection
# ---------------------------------------------------------------------------

@pytest.fixture()
def repo(fake_db):
    """ProjectRepository backed by the per-test rollback connection."""
    return ProjectRepository(fake_db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_project(repo, lookup, **kwargs) -> str:
    """Insert a minimal project and return its slug."""
    data = {
        "name": kwargs.get("name", "Test Project"),
        "description": kwargs.get("description", None),
        "status_id": await lookup("project_status", kwargs.get("status", "active")),
        "type_id": await lookup("project_type", kwargs.get("type", "coding")),
        "parent_id": kwargs.get("parent_id", None),
        "target_date": kwargs.get("target_date", None),
    }
    return await repo.create(data)


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------

class TestGetAll:

    async def test_returns_list(self, repo):
        result = await repo.get_all()
        assert isinstance(result, list)

    async def test_status_filter_returns_only_matching(self, repo, lookup):
        await _create_project(repo, lookup, name="Active One", status="active")
        await _create_project(repo, lookup, name="Paused One", status="paused")
        active = await repo.get_all(status="active")
        assert all(p["status"] == "active" for p in active)

    async def test_no_filter_returns_all_statuses(self, repo, lookup):
        await _create_project(repo, lookup, name="Active Two", status="active")
        await _create_project(repo, lookup, name="Paused Two", status="paused")
        all_projects = await repo.get_all()
        statuses = {p["status"] for p in all_projects}
        assert len(statuses) > 1


# ---------------------------------------------------------------------------
# get_by_slug
# ---------------------------------------------------------------------------

class TestGetBySlug:

    async def test_returns_project_dict(self, repo, lookup):
        slug = await _create_project(repo, lookup, name="Slug Test")
        project = await repo.get_by_slug(slug)
        assert project["slug"] == slug
        assert project["name"] == "Slug Test"

    async def test_raises_when_not_found(self, repo):
        with pytest.raises(RecordNotFoundError):
            await repo.get_by_slug("no-such-slug")


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

class TestCreate:

    async def test_returns_slug_string(self, repo, lookup):
        slug = await _create_project(repo, lookup, name="Create Test")
        assert isinstance(slug, str)
        assert len(slug) > 0

    async def test_created_project_is_retrievable(self, repo, lookup):
        slug = await _create_project(repo, lookup, name="Retrievable Project")
        project = await repo.get_by_slug(slug)
        assert project["name"] == "Retrievable Project"

    async def test_slug_generated_from_name(self, repo, lookup):
        slug = await _create_project(repo, lookup, name="My New Project")
        assert "my-new-project" in slug


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:

    async def test_update_changes_name(self, repo, lookup):
        slug = await _create_project(repo, lookup, name="Before Update")
        await repo.update(slug, {
            "name": "After Update",
            "description": None,
            "status_id": await lookup("project_status", "active"),
            "type_id": await lookup("project_type", "coding"),
            "parent_id": None,
            "target_date": None,
        })
        project = await repo.get_by_slug(slug)
        assert project["name"] == "After Update"

    async def test_update_nonexistent_raises(self, repo, lookup):
        with pytest.raises(RecordNotFoundError):
            await repo.update("no-such-slug", {
                "name": "Ghost",
                "description": None,
                "status_id": await lookup("project_status", "active"),
                "type_id": None,
                "parent_id": None,
                "target_date": None,
            })


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:

    async def test_delete_removes_project(self, repo, lookup):
        slug = await _create_project(repo, lookup, name="To Be Deleted")
        await repo.delete(slug)
        with pytest.raises(RecordNotFoundError):
            await repo.get_by_slug(slug)

    async def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(RecordNotFoundError):
            await repo.delete("never-existed")


# ---------------------------------------------------------------------------
# get_status_options / get_type_options / get_parent_options
# ---------------------------------------------------------------------------

class TestSelectOptions:

    async def test_status_options_returns_list(self, repo):
        options = await repo.get_status_options()
        assert isinstance(options, list)
        assert len(options) > 0

    async def test_type_options_returns_list(self, repo):
        options = await repo.get_type_options()
        assert isinstance(options, list)
        assert len(options) > 0

    async def test_parent_options_returns_list(self, repo):
        options = await repo.get_parent_options()
        assert isinstance(options, list)

    async def test_subprojects_returns_children_only(self, repo, lookup):
        parent_slug = await _create_project(repo, lookup, name="Parent Project")
        parent = await repo.get_by_slug(parent_slug)
        await _create_project(
            repo, lookup, name="Child Project", parent_id=parent["id"]
        )
        subprojects = await repo.get_subprojects(parent["id"])
        assert len(subprojects) >= 1
        assert all(p["parent_id"] == parent["id"] for p in subprojects)
