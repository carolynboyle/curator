"""
viewkit.exceptions - Exception hierarchy for viewkit.

All viewkit exceptions inherit from ViewKitError, allowing callers
to catch broadly or narrowly as needed.
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
