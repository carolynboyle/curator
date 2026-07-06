"""Curator exceptions."""


class CuratorError(Exception):
    """Base exception for Curator."""


class ConfigError(CuratorError):
    """Configuration error."""


class DatabaseError(CuratorError):
    """Database connection or query error."""


class FieldSchemaError(CuratorError):
    """
    Raised when fieldkit cannot build a valid field list for a view.

    Two cases:
      - api.get_field_schema(view_name) returned no columns (bad or
        misspelled view name).
      - A *_id or integer column has no matching entry in the fieldkit
        override YAML file. These columns are never defaulted to a
        plain control — see sql_conventions.md's *_id / bare-integer
        rule. Raised at app startup (fieldkit's cache is built during
        FastAPI's lifespan), by design: a misconfigured form should
        crash the app immediately, not render a broken control later.
    """
