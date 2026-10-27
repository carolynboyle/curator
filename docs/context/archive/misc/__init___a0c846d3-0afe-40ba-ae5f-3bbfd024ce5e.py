"""
viewkit - YAML-driven view and query definition library.

Loads views.yaml and queries.yaml, returning framework-agnostic
definitions for use by any rendering or data access layer.

Public API:
    ViewBuilder       — loads views.yaml, returns ViewDef objects
    ViewDef           — a named view (title, columns, fields)
    ColumnDef         — a list/table column definition
    FieldDef          — a form field definition
    QueryBuilder      — loads queries.yaml, returns QueryDef objects
    QueryLoader       — runtime query lookup for repositories
    QueryDef          — a named SQL query definition
    ViewKitError      — base exception
    ViewNotFoundError — requested view not in views.yaml
    ViewConfigError   — file missing, unreadable, or malformed
    QueryNotFoundError — requested query not in queries.yaml
    QueryConfigError   — file missing, unreadable, or malformed
"""

from viewkit.view_builder import ViewBuilder
from viewkit.models import ColumnDef, FieldDef, ViewDef
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader
from viewkit.query_models import QueryDef
from viewkit.exceptions import (
    QueryConfigError,
    QueryNotFoundError,
    ViewConfigError,
    ViewKitError,
    ViewNotFoundError,
)

__all__ = [
    "ViewBuilder",
    "ViewDef",
    "ColumnDef",
    "FieldDef",
    "QueryBuilder",
    "QueryLoader",
    "QueryDef",
    "ViewKitError",
    "ViewNotFoundError",
    "ViewConfigError",
    "QueryNotFoundError",
    "QueryConfigError",
]
