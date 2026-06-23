"""Curator exceptions."""


class CuratorError(Exception):
    """Base exception for Curator."""
    pass


class ConfigError(CuratorError):
    """Configuration error."""
    pass


class DatabaseError(CuratorError):
    """Database connection or query error."""
    pass