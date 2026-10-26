"""
tests.integration.test_tags_repo - Integration tests for TagRepository.

All tests run against test_curator on steward via the floater account.
Each test is wrapped in a transaction that rolls back on completion.

Covers every method in curator.db.tags.TagRepository.
"""

import pytest

from curator.db.projects import ProjectRepository
from curator.db.tags import TagRepository
from curator.exceptions import RecordNotFoundError

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tag_repo(fake_db):
    return TagRepository(fake_db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_project(fake_db, lookup, name="Tag Test Project") -> int:
    """Create a minimal project and return its ID."""
    repo = ProjectRepository(fake_db)
    slug = await repo.create({
        "name": name,
        "description": None,
        "status_id": await lookup("project_status", "active"),
        "type_id": await lookup("project_type", "coding"),
        "parent_id": None,
        "target_date": None,
    })
    project = await repo.get_by_slug(slug)
    return project["id"]


async def _create_tag(repo, lookup, name="test-tag", category="technology") -> int:
    return await repo.create({
        "name": name,
        "category_id": await lookup("tag_category", category),
    })


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------

class TestGetAll:

    async def test_returns_list(self, tag_repo):
        result = await tag_repo.get_all()
        assert isinstance(result, list)

    async def test_created_tag_appears_in_list(self, tag_repo, lookup):
        await _create_tag(tag_repo, lookup, name="integration-tag")
        all_tags = await tag_repo.get_all()
        names = [t["name"] for t in all_tags]
        assert "integration-tag" in names


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

class TestGetById:

    async def test_returns_tag_dict(self, tag_repo, lookup):
        tag_id = await _create_tag(tag_repo, lookup)
        tag = await tag_repo.get_by_id(tag_id)
        assert tag["id"] == tag_id

    async def test_raises_when_not_found(self, tag_repo):
        with pytest.raises(RecordNotFoundError):
            await tag_repo.get_by_id(999999)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

class TestCreate:

    async def test_returns_integer_id(self, tag_repo, lookup):
        tag_id = await _create_tag(tag_repo, lookup)
        assert isinstance(tag_id, int)

    async def test_tag_retrievable_after_create(self, tag_repo, lookup):
        tag_id = await _create_tag(tag_repo, lookup, name="new-unique-tag")
        tag = await tag_repo.get_by_id(tag_id)
        assert tag["name"] == "new-unique-tag"


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:

    async def test_update_changes_name(self, tag_repo, lookup):
        tag_id = await _create_tag(tag_repo, lookup, name="before")
        await tag_repo.update(tag_id, {
            "name": "after",
            "category_id": await lookup("tag_category", "technology"),
        })
        tag = await tag_repo.get_by_id(tag_id)
        assert tag["name"] == "after"

    async def test_update_nonexistent_raises(self, tag_repo, lookup):
        with pytest.raises(RecordNotFoundError):
            await tag_repo.update(999999, {
                "name": "ghost",
                "category_id": await lookup("tag_category", "technology"),
            })


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:

    async def test_delete_removes_tag(self, tag_repo, lookup):
        tag_id = await _create_tag(tag_repo, lookup, name="to-delete")
        await tag_repo.delete(tag_id)
        with pytest.raises(RecordNotFoundError):
            await tag_repo.get_by_id(tag_id)

    async def test_delete_nonexistent_raises(self, tag_repo):
        with pytest.raises(RecordNotFoundError):
            await tag_repo.delete(999999)


# ---------------------------------------------------------------------------
# assign_to_project / remove_from_project
# ---------------------------------------------------------------------------

class TestProjectTagAssignment:

    async def test_assign_tag_to_project(self, tag_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        tag_id = await _create_tag(tag_repo, lookup, name="proj-tag")
        await tag_repo.assign_to_project(project_id, tag_id)
        tags = await tag_repo.get_for_project(project_id)
        assert any(t["id"] == tag_id for t in tags)

    async def test_assign_duplicate_is_silent(self, tag_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        tag_id = await _create_tag(tag_repo, lookup, name="dup-tag")
        await tag_repo.assign_to_project(project_id, tag_id)
        await tag_repo.assign_to_project(project_id, tag_id)
        tags = await tag_repo.get_for_project(project_id)
        assert sum(1 for t in tags if t["id"] == tag_id) == 1

    async def test_remove_tag_from_project(self, tag_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        tag_id = await _create_tag(tag_repo, lookup, name="removable-tag")
        await tag_repo.assign_to_project(project_id, tag_id)
        await tag_repo.remove_from_project(project_id, tag_id)
        tags = await tag_repo.get_for_project(project_id)
        assert not any(t["id"] == tag_id for t in tags)


# ---------------------------------------------------------------------------
# get_category_options
# ---------------------------------------------------------------------------

class TestSelectOptions:

    async def test_category_options_non_empty(self, tag_repo):
        options = await tag_repo.get_category_options()
        assert len(options) > 0
