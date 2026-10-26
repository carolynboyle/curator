"""
tests.integration.test_files_repo - Integration tests for FileRepository.

All tests run against test_curator on steward via the floater account.
Each test is wrapped in a transaction that rolls back on completion.

Covers every method in curator.db.files.FileRepository.
"""

import pytest
import pytest_asyncio

from curator.db.files import FileRepository
from curator.db.projects import ProjectRepository
from curator.exceptions import RecordNotFoundError

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def file_repo(fake_db):
    return FileRepository(fake_db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_project(fake_db, lookup, name="File Test Project") -> int:
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


async def _create_file(repo, lookup, project_id, **kwargs) -> int:
    """Insert a minimal file attachment and return its ID."""
    return await repo.create({
        "project_id": project_id,
        "task_id": kwargs.get("task_id", None),
        "label": kwargs.get("label", "test file"),
        "file_type_id": await lookup("file_type", kwargs.get("file_type", "other")),
        "location": kwargs.get("location", "https://example.com"),
        "location_type_id": await lookup(
            "location_type", kwargs.get("location_type", "url")
        ),
        "notes": kwargs.get("notes", None),
    })


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

class TestGetById:

    async def test_returns_file_dict(self, file_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        file_id = await _create_file(file_repo, lookup, project_id)
        f = await file_repo.get_by_id(file_id)
        assert f["id"] == file_id

    async def test_raises_when_not_found(self, file_repo):
        with pytest.raises(RecordNotFoundError):
            await file_repo.get_by_id(999999)


# ---------------------------------------------------------------------------
# get_for_project
# ---------------------------------------------------------------------------

class TestGetForProject:

    async def test_returns_files_for_project(self, file_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        await _create_file(file_repo, lookup, project_id, label="repo link")
        files = await file_repo.get_for_project(project_id)
        assert any(f["label"] == "repo link" for f in files)

    async def test_empty_project_returns_empty_list(self, file_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        files = await file_repo.get_for_project(project_id)
        assert files == []

    async def test_does_not_include_other_project_files(
        self, file_repo, fake_db, lookup
    ):
        project_id = await _make_project(fake_db, lookup, name="Project A")
        other_id = await _make_project(fake_db, lookup, name="Project B")
        await _create_file(file_repo, lookup, other_id, label="other project file")
        files = await file_repo.get_for_project(project_id)
        assert not any(f["label"] == "other project file" for f in files)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

class TestCreate:

    async def test_returns_integer_id(self, file_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        file_id = await _create_file(file_repo, lookup, project_id)
        assert isinstance(file_id, int)

    async def test_file_retrievable_after_create(self, file_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        file_id = await _create_file(
            file_repo, lookup, project_id, label="unique label"
        )
        f = await file_repo.get_by_id(file_id)
        assert f["label"] == "unique label"

    async def test_file_type_and_location_type_resolved(
        self, file_repo, fake_db, lookup
    ):
        project_id = await _make_project(fake_db, lookup)
        file_id = await _create_file(
            file_repo, lookup, project_id,
            file_type="markdown", location_type="git",
        )
        f = await file_repo.get_by_id(file_id)
        assert f["file_type"] == "markdown"
        assert f["location_type"] == "git"


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:

    async def test_update_changes_label(self, file_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        file_id = await _create_file(file_repo, lookup, project_id, label="old label")
        await file_repo.update(file_id, {
            "label": "new label",
            "file_type_id": await lookup("file_type", "other"),
            "location": "https://example.com",
            "location_type_id": await lookup("location_type", "url"),
            "notes": None,
        })
        f = await file_repo.get_by_id(file_id)
        assert f["label"] == "new label"

    async def test_update_nonexistent_raises(self, file_repo, lookup):
        with pytest.raises(RecordNotFoundError):
            await file_repo.update(999999, {
                "label": "ghost",
                "file_type_id": await lookup("file_type", "other"),
                "location": "https://example.com",
                "location_type_id": await lookup("location_type", "url"),
                "notes": None,
            })


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:

    async def test_delete_removes_file(self, file_repo, fake_db, lookup):
        project_id = await _make_project(fake_db, lookup)
        file_id = await _create_file(file_repo, lookup, project_id)
        await file_repo.delete(file_id)
        with pytest.raises(RecordNotFoundError):
            await file_repo.get_by_id(file_id)

    async def test_delete_nonexistent_raises(self, file_repo):
        with pytest.raises(RecordNotFoundError):
            await file_repo.delete(999999)


# ---------------------------------------------------------------------------
# Select options
# ---------------------------------------------------------------------------

class TestSelectOptions:

    async def test_file_type_options_non_empty(self, file_repo):
        options = await file_repo.get_file_type_options()
        assert len(options) > 0

    async def test_location_type_options_non_empty(self, file_repo):
        options = await file_repo.get_location_type_options()
        assert len(options) > 0
