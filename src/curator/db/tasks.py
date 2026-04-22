"""
curator.db.tasks - Task repository.

Reads use v_tasks and v_task_tree views. Writes target the tasks
table directly.

Deletion of tasks with children requires the caller to confirm —
the schema uses ON DELETE NO ACTION for task parent_id. This
repository raises DeleteBlockedError when children exist, allowing
the route layer to present a confirmation UI before calling
force_delete().
"""

from datetime import datetime, timezone

from dbkit.connection import AsyncDBConnection

from curator.db.base import BaseRepository
from curator.exceptions import DeleteBlockedError, RecordNotFoundError


class TaskRepository(BaseRepository):
    """
    CRUD operations for the tasks table.

    Reads use v_tasks and v_task_tree for resolved lookup names.
    Writes target the tasks table directly.
    """

    def __init__(self, db: AsyncDBConnection, loader=None):
        super().__init__(db, loader)

    # -- Reads ----------------------------------------------------------------

    async def get_all_for_project(self, project_id: int) -> list[dict]:
        """
        Return all top-level tasks for a project, ordered for display.

        Args:
            project_id: Project ID to filter by.

        Returns:
            List of task dicts from v_tasks.
        """
        return await self.fetch_all(
            """
            SELECT * FROM v_tasks
            WHERE project_id = %s AND parent_id IS NULL
            ORDER BY sort_order, id
            """,
            (project_id,),
        )

    async def get_by_id(self, task_id: int) -> dict:
        """
        Return a single task by ID.

        Args:
            task_id: Task ID.

        Returns:
            Task dict from v_tasks.

        Raises:
            RecordNotFoundError: If no task with that ID exists.
        """
        row = await self.fetch_one(
            "SELECT * FROM v_tasks WHERE id = %s", (task_id,)
        )
        if row is None:
            raise RecordNotFoundError(f"Task not found: {task_id}")
        return row

    async def get_subtasks(self, parent_id: int) -> list[dict]:
        """
        Return direct subtasks of a task.

        Args:
            parent_id: ID of the parent task.

        Returns:
            List of task dicts ordered by sort_order.
        """
        return await self.fetch_all(
            """
            SELECT * FROM v_tasks
            WHERE parent_id = %s
            ORDER BY sort_order, id
            """,
            (parent_id,),
        )

    async def get_tree_for_project(self, project_id: int) -> list[dict]:
        """
        Return the full task tree for a project from v_task_tree.

        Args:
            project_id: Project ID to filter by.

        Returns:
            List of task tree dicts ordered by path.
        """
        return await self.fetch_all(
            """
            SELECT * FROM v_task_tree
            WHERE project_id = %s
            ORDER BY path
            """,
            (project_id,),
        )

    async def get_child_count(self, task_id: int) -> int:
        """
        Return the number of direct children of a task.

        Args:
            task_id: Task ID.

        Returns:
            Count of direct child tasks.
        """
        result = await self.fetch_scalar(
            "SELECT COUNT(*) FROM tasks WHERE parent_id = %s", (task_id,)
        )
        return int(result or 0)

    # -- Writes ---------------------------------------------------------------

    async def create(self, data: dict) -> int:
        result = await self.fetch_scalar(
            """
            INSERT INTO tasks
                (project_id, parent_id, description, status_id, priority_id,
                 notes, links, source_file, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data["project_id"],
                data.get("parent_id"),
                data["description"],
                data["status_id"],
                data["priority_id"],
                data.get("notes", ""),
                data.get("links", ""),
                data.get("source_file", ""),
                data.get("sort_order", 0),
            ),
        )
        return int(result)

    async def update(self, task_id: int, data: dict) -> None:
        """
        Update a task's mutable fields.

        Marks completed_at when status becomes terminal, clears it
        when status returns to non-terminal.

        Args:
            task_id: ID of the task to update.
            data:    Dict with any of: description, status_id,
                     priority_id, parent_id, links, sort_order.
                     Must include is_terminal to manage completed_at.

        Raises:
            RecordNotFoundError: If no task with that ID exists.
        """
        await self.get_by_id(task_id)  # raises if not found

        is_terminal = bool(data.get("is_terminal", False))
        completed_at = datetime.now(timezone.utc) if is_terminal else None
        
        await self.execute(
            """
            UPDATE tasks SET
                description  = %s,
                status_id    = %s,
                priority_id  = %s,
                parent_id    = %s,
                notes        = %s,
                links        = %s,
                sort_order   = %s,
                completed_at = %s
            WHERE id = %s
            """,
            (
                data["description"],
                data["status_id"],
                data["priority_id"],
                data.get("parent_id"),
                data.get("notes", ""),
                data.get("links", ""),
                data.get("sort_order", 0),
                completed_at,
                task_id,
            ),
        )

    async def delete(self, task_id: int) -> None:
        """
        Delete a task, raising if it has children.

        The schema uses ON DELETE NO ACTION for task parent_id.
        Callers must detect children and present confirmation before
        calling force_delete().

        Args:
            task_id: ID of the task to delete.

        Raises:
            RecordNotFoundError: If the task does not exist.
            DeleteBlockedError:  If the task has child tasks.
        """
        await self.get_by_id(task_id)  # raises if not found

        count = await self.get_child_count(task_id)
        if count > 0:
            raise DeleteBlockedError(
                f"Task {task_id} has {count} subtask(s). "
                "Delete subtasks first or use force_delete().",
                count=count,
            )

        await self.execute("DELETE FROM tasks WHERE id = %s", (task_id,))

    async def force_delete(self, task_id: int) -> None:
        """
        Delete a task and all its descendants.

        Use only after explicit user confirmation. Recursively deletes
        all subtasks before deleting the parent to satisfy the
        ON DELETE NO ACTION constraint.

        Args:
            task_id: ID of the task to delete.

        Raises:
            RecordNotFoundError: If the task does not exist.
        """
        await self.get_by_id(task_id)  # raises if not found

        # Delete all descendants via recursive CTE, deepest first
        await self.execute(
            """
            WITH RECURSIVE descendants AS (
                SELECT id FROM tasks WHERE parent_id = %s
                UNION ALL
                SELECT t.id FROM tasks t
                JOIN descendants d ON d.id = t.parent_id
            )
            DELETE FROM tasks WHERE id IN (SELECT id FROM descendants)
            """,
            (task_id,),
        )
        await self.execute("DELETE FROM tasks WHERE id = %s", (task_id,))

    # -- Select options -------------------------------------------------------

    async def get_status_options(self) -> list[dict]:
        """Return all task statuses for select fields."""
        return await self.fetch_all(
            "SELECT * FROM task_status ORDER BY sort_order"
        )

    async def get_priority_options(self) -> list[dict]:
        """Return all priorities for select fields."""
        return await self.fetch_all(
            "SELECT * FROM priority ORDER BY sort_order"
        )

    async def get_parent_options(self, project_id: int) -> list[dict]:
        """
        Return tasks in a project as parent options for select fields.

        Args:
            project_id: Restrict options to this project.

        Returns:
            List of dicts with id and description.
        """
        return await self.fetch_all(
            """
            SELECT id, description FROM tasks
            WHERE project_id = %s AND parent_id IS NULL
            ORDER BY sort_order, id
            """,
            (project_id,),
        )
    