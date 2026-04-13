# files.py

**Path:** src/curator/db/files.py
**Syntax:** python
**Generated:** 2026-04-12 14:34:39

```python
"""
curator.db.files - File attachment repository.

Handles project_files entries. Each file is attached to either a
project or a task (schema enforces at least one via CHECK constraint).
"""

from dbkit.connection import AsyncDBConnection

from curator.db.base import BaseRepository
from curator.exceptions import RecordNotFoundError


class FileRepository(BaseRepository):
    """
    CRUD operations for the project_files table.
    """

    def __init__(self, db: AsyncDBConnection):
        super().__init__(db)

    # -- Reads ----------------------------------------------------------------

    async def get_all(self) -> list[dict]:
        """Return all file attachments across all projects and tasks."""
        return await self.fetch_all(
            """
            SELECT pf.id, pf.label, pf.location, pf.notes,
                   ft.name AS file_type, lt.name AS location_type,
                   p.name AS project_name, p.slug AS project_slug
            FROM project_files pf
            JOIN file_type ft      ON ft.id = pf.file_type_id
            JOIN location_type lt  ON lt.id = pf.location_type_id
            LEFT JOIN projects p   ON p.id  = pf.project_id
            ORDER BY p.name, pf.label
            """
        )

    async def get_for_project(self, project_id: int) -> list[dict]:
        """Return all files attached to a project."""
        return await self.fetch_all(
            """
            SELECT pf.id, pf.label, pf.location, pf.notes,
                   ft.name AS file_type, lt.name AS location_type
            FROM project_files pf
            JOIN file_type ft     ON ft.id = pf.file_type_id
            JOIN location_type lt ON lt.id = pf.location_type_id
            WHERE pf.project_id = %s
            ORDER BY pf.label
            """,
            (project_id,),
        )

    async def get_for_task(self, task_id: int) -> list[dict]:
        """Return all files attached to a task."""
        return await self.fetch_all(
            """
            SELECT pf.id, pf.label, pf.location, pf.notes,
                   ft.name AS file_type, lt.name AS location_type
            FROM project_files pf
            JOIN file_type ft     ON ft.id = pf.file_type_id
            JOIN location_type lt ON lt.id = pf.location_type_id
            WHERE pf.task_id = %s
            ORDER BY pf.label
            """,
            (task_id,),
        )

    async def get_by_id(self, file_id: int) -> dict:
        """
        Return a single file record by ID.

        Raises:
            RecordNotFoundError: If no file with that ID exists.
        """
        row = await self.fetch_one(
            """
            SELECT pf.*, ft.name AS file_type, lt.name AS location_type
            FROM project_files pf
            JOIN file_type ft     ON ft.id = pf.file_type_id
            JOIN location_type lt ON lt.id = pf.location_type_id
            WHERE pf.id = %s
            """,
            (file_id,),
        )
        if row is None:
            raise RecordNotFoundError(f"File not found: {file_id}")
        return row

    # -- Writes ---------------------------------------------------------------

    async def create(self, data: dict) -> int:
        """
        Insert a new file attachment and return its ID.

        Either project_id or task_id must be provided (schema enforces
        this via CHECK constraint — the DB will reject rows with neither).

        Args:
            data: Dict with keys: label, file_type_id, location,
                  location_type_id. Optional: project_id, task_id, notes.

        Returns:
            ID of the newly created record.
        """
        result = await self.fetch_scalar(
            """
            INSERT INTO project_files
                (project_id, task_id, label, file_type_id,
                 location, location_type_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data.get("project_id"),
                data.get("task_id"),
                data["label"],
                data["file_type_id"],
                data["location"],
                data["location_type_id"],
                data.get("notes"),
            ),
        )
        return int(result)

    async def update(self, file_id: int, data: dict) -> None:
        """
        Update a file attachment's mutable fields.

        Raises:
            RecordNotFoundError: If no file with that ID exists.
        """
        await self.get_by_id(file_id)  # raises if not found
        await self.execute(
            """
            UPDATE project_files SET
                label            = %s,
                file_type_id     = %s,
                location         = %s,
                location_type_id = %s,
                notes            = %s
            WHERE id = %s
            """,
            (
                data["label"],
                data["file_type_id"],
                data["location"],
                data["location_type_id"],
                data.get("notes"),
                file_id,
            ),
        )

    async def delete(self, file_id: int) -> None:
        """
        Delete a file attachment.

        Raises:
            RecordNotFoundError: If no file with that ID exists.
        """
        await self.get_by_id(file_id)  # raises if not found
        await self.execute(
            "DELETE FROM project_files WHERE id = %s", (file_id,)
        )

    # -- Select options -------------------------------------------------------

    async def get_file_type_options(self) -> list[dict]:
        """Return all file types for select fields."""
        return await self.fetch_all(
            "SELECT * FROM file_type ORDER BY sort_order"
        )

    async def get_location_type_options(self) -> list[dict]:
        """Return all location types for select fields."""
        return await self.fetch_all(
            "SELECT * FROM location_type ORDER BY sort_order"
        )
    
```
