"""
viewkit.exceptions - Exception hierarchy for viewkit.

All viewkit exceptions inherit from ViewKitError, allowing callers
to catch broadly or narrowly as needed.

Hierarchy:
    ViewKitError
    ├── ViewNotFoundError   — requested view not in views.yaml
    ├── ViewConfigError     — views.yaml missing, unreadable, or malformed
    ├── QueryNotFoundError  — requested query not in queries.yaml
    └── QueryConfigError    — queries.yaml missing, unreadable, or malformed
"""


class ViewKitError(Exception):
    """Base exception for all viewkit errors."""


class ViewNotFoundError(ViewKitError):
    """
    Raised when a requested view name is not present in views.yaml.

    Example:
        builder.get_view("nonexistent")  # raises ViewNotFoundError
    """


class ViewConfigError(ViewKitError):
    """
    Raised when a views.yaml file is missing, unreadable, or malformed.

    Examples: file not found, invalid YAML, missing required keys.
    """


class QueryNotFoundError(ViewKitError):
    """
    Raised when a requested entity or query name is not present
    in queries.yaml.

    Examples:
        builder.get_query("nonexistent", "get_all")
        builder.get_query("projects", "nonexistent")
    """


class QueryConfigError(ViewKitError):
    """
    Raised when a queries.yaml file is missing, unreadable, or malformed.

    Examples: file not found, invalid YAML, missing required keys,
    invalid query type.
    """
