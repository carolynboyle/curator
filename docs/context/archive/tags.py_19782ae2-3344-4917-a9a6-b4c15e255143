"""
curator.db.tags - Tag repository.

Handles tags and their assignment to projects and tasks.
"""

from typing import Optional

from dbkit.connection import AsyncDBConnection

from curator.db.base import BaseRepository
from curator.exceptions import RecordNotFoundError
from viewkit import QueryLoader


class TagRepository(BaseRepository):
    """
    CRUD operations for tags and junction tables.
    """

    def __init__(self, db: AsyncDBConnection, loader: Optional[QueryLoader] = None):
        super().__init__(db, loader)

    # -- Reads ----------------------------------------------------------------

    async def get_all(self) -> list[dict]:
        """Return all tags with their category names."""
        return await self.fetch_all(
            self._q.sql("tags", "get_all")
        )

    async def get_by_id(self, tag_id: int) -> dict:
        """
        Return a single tag by ID.

        Raises:
            RecordNotFoundError: If no tag with that ID exists.
        """
        row = await self.fetch_one(
            self._q.sql("tags", "get_by_id"),
            (tag_id,),
        )
        if row is None:
            raise RecordNotFoundError(f"Tag not found: {tag_id}")
        return row

    async def get_for_project(self, project_id: int) -> list[dict]:
        """Return all tags assigned to a project."""
        return await self.fetch_all(
            self._q.sql("tags", "get_for_project"),
            (project_id,),
        )

    async def get_for_task(self, task_id: int) -> list[dict]:
        """Return all tags assigned to a task."""
        return await self.fetch_all(
            self._q.sql("tags", "get_for_task"),
            (task_id,),
        )

    # -- Writes ---------------------------------------------------------------

    async def create(self, data: dict) -> int:
        """
        Insert a new tag and return its ID.

        Args:
            data: Dict with keys: name, category_id (optional).

        Returns:
            ID of the newly created tag.
        """
        result = await self.fetch_scalar(
            self._q.sql("tags", "create"),
            (data["name"], data.get("category_id")),
        )
        return int(result)

    async def update(self, tag_id: int, data: dict) -> None:
        """
        Update a tag's name and/or category.

        Raises:
            RecordNotFoundError: If no tag with that ID exists.
        """
        await self.get_by_id(tag_id)  # raises if not found
        await self.execute(
            self._q.sql("tags", "update"),
            (data["name"], data.get("category_id"), tag_id),
        )

    async def delete(self, tag_id: int) -> None:
        """
        Delete a tag. Junction table rows cascade automatically.

        Raises:
            RecordNotFoundError: If no tag with that ID exists.
        """
        await self.get_by_id(tag_id)  # raises if not found
        await self.execute(
            self._q.sql("tags", "delete"), (tag_id,)
        )

    async def assign_to_project(self, project_id: int, tag_id: int) -> None:
        """
        Assign a tag to a project. Silently ignores duplicates.

        Args:
            project_id: Project to tag.
            tag_id:     Tag to assign.
        """
        await self.execute(
            self._q.sql("tags", "assign_to_project"),
            (project_id, tag_id),
        )

    async def remove_from_project(self, project_id: int, tag_id: int) -> None:
        """Remove a tag assignment from a project."""
        await self.execute(
            self._q.sql("tags", "remove_from_project"),
            (project_id, tag_id),
        )

    async def assign_to_task(self, task_id: int, tag_id: int) -> None:
        """
        Assign a tag to a task. Silently ignores duplicates.

        Args:
            task_id: Task to tag.
            tag_id:  Tag to assign.
        """
        await self.execute(
            self._q.sql("tags", "assign_to_task"),
            (task_id, tag_id),
        )

    async def remove_from_task(self, task_id: int, tag_id: int) -> None:
        """Remove a tag assignment from a task."""
        await self.execute(
            self._q.sql("tags", "remove_from_task"),
            (task_id, tag_id),
        )

    # -- Select options -------------------------------------------------------

    async def get_category_options(self) -> list[dict]:
        """Return all tag categories for select fields."""
        return await self.fetch_all(
            self._q.sql("tags", "category_options")
        )
