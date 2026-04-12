"""
curator.db - Database repository layer.

One repository class per resource. All repositories inherit from
BaseRepository and receive an AsyncDBConnection from the FastAPI
dependency layer.

Public API:
    BaseRepository    — base class with shared query helpers
    ProjectRepository — CRUD for projects
    TaskRepository    — CRUD for tasks
    TagRepository     — CRUD for tags and junction tables
    FileRepository    — CRUD for project_files
"""

from curator.db.base import BaseRepository
from curator.db.projects import ProjectRepository
from curator.db.tasks import TaskRepository
from curator.db.tags import TagRepository
from curator.db.files import FileRepository

__all__ = [
    "BaseRepository",
    "ProjectRepository",
    "TaskRepository",
    "TagRepository",
    "FileRepository",
]