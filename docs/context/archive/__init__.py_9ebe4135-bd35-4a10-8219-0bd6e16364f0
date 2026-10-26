"""
viewkit - YAML-driven view definition library.

Loads views.yaml and returns framework-agnostic view definitions
for use by any rendering layer.

Public API:
    ViewBuilder   — loads views.yaml, returns ViewDef objects
    ViewDef       — a named view (title, columns, fields)
    ColumnDef     — a list/table column definition
    FieldDef      — a form field definition
    ViewKitError  — base exception
    ViewNotFoundError — requested view not in views.yaml
    ViewConfigError   — file missing, unreadable, or malformed
"""

from viewkit.view_builder import ViewBuilder
from viewkit.models import ColumnDef, FieldDef, ViewDef
from viewkit.exceptions import ViewConfigError, ViewKitError, ViewNotFoundError

__all__ = [
    "ViewBuilder",
    "ViewDef",
    "ColumnDef",
    "FieldDef",
    "ViewKitError",
    "ViewNotFoundError",
    "ViewConfigError",
]
