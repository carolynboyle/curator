"""
curator.db.projects - Project repository.

All project reads go through v_projects (flat) or v_project_tree
(recursive). Writes go directly to the projects table.

Slug generation: slugs are derived from the project name by the
application on create, then treated as immutable. The repository
does not generate slugs — the route layer does.
"""

import re

from dbkit.connection import AsyncDBConnection

from curator.db.base import BaseRepository
from curator.exceptions import RecordNotFoundError


def _slugify(name: str) -> str:
    """
    Convert a project name to a URL-safe slug.

    Lowercases, replaces spaces and underscores with hyphens,
    strips non-alphanumeric characters, collapses multiple hyphens.

    Args:
        name: Raw project name string.

    Returns:
        URL-safe slug string.
    """
    slug = name.lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class ProjectRepository(BaseRepository):
    """
    CRUD operations for the projects table.

    Reads use v_projects and v_project_tree views for resolved
    lookup names and task counts. Writes target the projects table
    directly.
    """

    def __init__(self, db: AsyncDBConnection):
        super().__init__(db)

    # -- Reads ----------------------------------------------------------------

    async def get_all(self, status: str | None = None) -> list[dict]:
        """
        Return all projects, optionally filtered by status name.

        Args:
            status: Optional status name to filter by (e.g. "active").

        Returns:
            List of project dicts from v_projects, ordered by name.
        """
        if status:
            return await self.fetch_all(
                "SELECT * FROM v_projects WHERE status = %s ORDER BY name",
                (status,),
            )
        return await self.fetch_all(
            "SELECT * FROM v_projects ORDER BY name"
        )

    async def get_by_id(self, project_id: int) -> dict:
        """
        Return a single project by ID.

        Args:
            project_id: Project ID.

        Returns:
            Project dict from v_projects.

        Raises:
            RecordNotFoundError: If no project with that ID exists.
        """
        row = await self.fetch_one(
            "SELECT * FROM v_projects WHERE id = %s", (project_id,)
        )
        if row is None:
            raise RecordNotFoundError(f"Project not found: {project_id}")
        return row

    async def get_by_slug(self, slug: str) -> dict:
        """
        Return a single project by slug.

        Args:
            slug: Project slug.

        Returns:
            Project dict from v_projects.

        Raises:
            RecordNotFoundError: If no project with that slug exists.
        """
        row = await self.fetch_one(
            "SELECT * FROM v_projects WHERE slug = %s", (slug,)
        )
        if row is None:
            raise RecordNotFoundError(f"Project not found: {slug!r}")
        return row

    async def get_tree(self) -> list[dict]:
        """
        Return all projects with full ancestry from v_project_tree.

        Returns:
            List of project tree dicts ordered by depth then name.
        """
        return await self.fetch_all(
            "SELECT * FROM v_project_tree ORDER BY path"
        )

    async def get_subprojects(self, parent_id: int) -> list[dict]:
        """
        Return direct children of a project.

        Args:
            parent_id: ID of the parent project.

        Returns:
            List of project dicts.
        """
        return await self.fetch_all(
            "SELECT * FROM v_projects WHERE parent_id = %s ORDER BY name",
            (parent_id,),
        )

    async def slug_exists(self, slug: str) -> bool:
        """
        Return True if a project with this slug already exists.

        Args:
            slug: Slug to check.

        Returns:
            True if the slug is taken.
        """
        result = await self.fetch_scalar(
            "SELECT EXISTS (SELECT 1 FROM projects WHERE slug = %s)",
            (slug,),
        )
        return bool(result)

    # -- Writes ---------------------------------------------------------------

    async def create(self, data: dict) -> str:
        """
        Insert a new project and return its slug.

        Generates a slug from the name. If the slug is already taken,
        appends a numeric suffix until unique.

        Args:
            data: Dict with keys: name, description, status_id, type_id,
                  parent_id. All optional except name and status_id.

        Returns:
            The slug of the newly created project.
        """
        base_slug = _slugify(data["name"])
        slug = base_slug
        suffix = 1
        while await self.slug_exists(slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        await self.execute(
            """
            INSERT INTO projects (name, slug, description, status_id, type_id, parent_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                data["name"],
                slug,
                data.get("description"),
                data["status_id"],
                data.get("type_id"),
                data.get("parent_id"),
            ),
        )
        return slug

    async def update(self, slug: str, data: dict) -> None:
        """
        Update a project's mutable fields.

        Slug and created_at are immutable and ignored if present in data.

        Args:
            slug: Slug identifying the project to update.
            data: Dict with any of: name, description, status_id,
                  type_id, parent_id, target_date.

        Raises:
            RecordNotFoundError: If no project with that slug exists.
        """
        await self.get_by_slug(slug)  # raises if not found

        await self.execute(
            """
            UPDATE projects SET
                name        = %s,
                description = %s,
                status_id   = %s,
                type_id     = %s,
                parent_id   = %s,
                target_date = %s
            WHERE slug = %s
            """,
            (
                data["name"],
                data.get("description"),
                data["status_id"],
                data.get("type_id"),
                data.get("parent_id"),
                data.get("target_date"),
                slug,
            ),
        )

    async def delete(self, slug: str) -> None:
        """
        Delete a project by slug.

        All tasks belonging to the project are deleted by CASCADE.
        Subprojects have their parent_id set to NULL by SET NULL.

        Args:
            slug: Slug identifying the project to delete.

        Raises:
            RecordNotFoundError: If no project with that slug exists.
        """
        await self.get_by_slug(slug)  # raises if not found
        await self.execute(
            "DELETE FROM projects WHERE slug = %s", (slug,)
        )

    # -- Select options -------------------------------------------------------

    async def get_status_options(self) -> list[dict]:
        """Return all project statuses for select fields."""
        return await self.fetch_all(
            "SELECT * FROM project_status ORDER BY sort_order"
        )

    async def get_type_options(self) -> list[dict]:
        """Return all project types for select fields."""
        return await self.fetch_all(
            "SELECT * FROM project_type ORDER BY sort_order"
        )

    async def get_parent_options(self) -> list[dict]:
        """
        Return all projects as parent options for select fields.

        Returns id, name, slug for use in a dropdown.
        """
        return await self.fetch_all(
            "SELECT id, name, slug FROM projects ORDER BY name"
        )
    