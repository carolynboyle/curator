# exceptions.py

**Path:** src/curator/exceptions.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
curator.exceptions - Exception hierarchy for the Curator.

All Curator exceptions inherit from CuratorError, allowing callers
to catch broadly or narrowly as needed.

DB-layer exceptions are re-raised from dbkit — callers that need
to distinguish DB errors should catch dbkit.exceptions directly.
"""


class CuratorError(Exception):
    """Base exception for all Curator errors."""


class ConfigError(CuratorError):
    """
    Raised when Curator configuration is missing or invalid.

    Examples: config file not found, required key absent, invalid value.
    """


class RepositoryError(CuratorError):
    """
    Raised when a repository operation fails for a domain reason.

    Not raised for raw DB errors — those come from dbkit.QueryError.
    Use this for higher-level failures: record not found, constraint
    violation the application should handle, etc.
    """


class RecordNotFoundError(RepositoryError):
    """
    Raised when a requested record does not exist.

    Example:
        repo.get_project("nonexistent-slug")  # raises RecordNotFoundError
    """


class DeleteBlockedError(RepositoryError):
    """
    Raised when a delete is blocked by existing children.

    The schema uses ON DELETE NO ACTION for task parent_id, requiring
    the application to detect children and present confirmation before
    deleting. This exception signals that condition.

    Attributes:
        count: Number of child records blocking the delete.
    """

    def __init__(self, message: str, count: int = 0):
        super().__init__(message)
        self.count = count
```
