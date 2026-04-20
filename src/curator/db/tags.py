"""
curator.db.tags - Tag repository.

Handles tags and their assignment to projects and tasks.
"""

from dbkit.connection import AsyncDBConnection

from curator.db.base import BaseRepository
from curator.exceptions import RecordNotFoundError


class TagRepository(BaseRepository):
    """
    CRUD operations for tags and junction tables.
    """

    def __init__(self, db: AsyncDBConnection, loader=None):
        super().__init__(db, loader)

    # -- Reads ----------------------------------------------------------------

    async def get_all(self) -> list[dict]:
        """Return all tags with their category names."""
        return await self.fetch_all(
            """
            SELECT t.id, t.name, tc.name AS category
            FROM tags t
            LEFT JOIN tag_category tc ON tc.id = t.category_id
            ORDER BY tc.sort_order, t.name
            """
        )

    async def get_by_id(self, tag_id: int) -> dict:
        """
        Return a single tag by ID.

        Raises:
            RecordNotFoundError: If no tag with that ID exists.
        """
        row = await self.fetch_one(
            """
            SELECT t.id, t.name, t.category_id, tc.name AS category
            FROM tags t
            LEFT JOIN tag_category tc ON tc.id = t.category_id
            WHERE t.id = %s
            """,
            (tag_id,),
        )
        if row is None:
            raise RecordNotFoundError(f"Tag not found: {tag_id}")
        return row

    async def get_for_project(self, project_id: int) -> list[dict]:
        """Return all tags assigned to a project."""
        return await self.fetch_all(
            """
            SELECT t.id, t.name, tc.name AS category
            FROM tags t
            JOIN project_tags pt ON pt.tag_id = t.id
            LEFT JOIN tag_category tc ON tc.id = t.category_id
            WHERE pt.project_id = %s
            ORDER BY tc.sort_order, t.name
            """,
            (project_id,),
        )

    async def get_for_task(self, task_id: int) -> list[dict]:
        """Return all tags assigned to a task."""
        return await self.fetch_all(
            """
            SELECT t.id, t.name, tc.name AS category
            FROM tags t
            JOIN task_tags tt ON tt.tag_id = t.id
            LEFT JOIN tag_category tc ON tc.id = t.category_id
            WHERE tt.task_id = %s
            ORDER BY tc.sort_order, t.name
            """,
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
            "INSERT INTO tags (name, category_id) VALUES (%s, %s) RETURNING id",
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
            "UPDATE tags SET name = %s, category_id = %s WHERE id = %s",
            (data["name"], data.get("category_id"), tag_id),
        )

    async def delete(self, tag_id: int) -> None:
        """
        Delete a tag. Junction table rows cascade automatically.

        Raises:
            RecordNotFoundError: If no tag with that ID exists.
        """
        await self.get_by_id(tag_id)  # raises if not found
        await self.execute("DELETE FROM tags WHERE id = %s", (tag_id,))

    async def assign_to_project(self, project_id: int, tag_id: int) -> None:
        """
        Assign a tag to a project. Silently ignores duplicates.

        Args:
            project_id: Project to tag.
            tag_id:     Tag to assign.
        """
        await self.execute(
            """
            INSERT INTO project_tags (project_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT (project_id, tag_id) DO NOTHING
            """,
            (project_id, tag_id),
        )

    async def remove_from_project(self, project_id: int, tag_id: int) -> None:
        """Remove a tag assignment from a project."""
        await self.execute(
            "DELETE FROM project_tags WHERE project_id = %s AND tag_id = %s",
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
            """
            INSERT INTO task_tags (task_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT (task_id, tag_id) DO NOTHING
            """,
            (task_id, tag_id),
        )

    async def remove_from_task(self, task_id: int, tag_id: int) -> None:
        """Remove a tag assignment from a task."""
        await self.execute(
            "DELETE FROM task_tags WHERE task_id = %s AND tag_id = %s",
            (task_id, tag_id),
        )

    # -- Select options -------------------------------------------------------

    async def get_category_options(self) -> list[dict]:
        """Return all tag categories for select fields."""
        return await self.fetch_all(
            "SELECT * FROM tag_category ORDER BY sort_order"
        )