"""
viewkit.view_builder - YAML-driven view definition loader.

Loads a views.yaml file and returns framework-agnostic ViewDef objects
describing the columns and fields for each named view.

ViewBuilder knows nothing about what calls it, how the path was found,
or how the returned objects will be rendered. That is the caller's concern.

Usage:
    from pathlib import Path
    from viewkit.view_builder import ViewBuilder

    builder = ViewBuilder(Path("/path/to/views.yaml"))

    view = builder.get_view("projects")
    # view.title   -> "Projects"
    # view.columns -> [ColumnDef(...), ...]
    # view.fields  -> [FieldDef(...), ...]

    all_views = builder.get_all_views()
    # {"projects": ViewDef(...), "tasks": ViewDef(...), ...}
"""

from pathlib import Path
from typing import Optional

import yaml

from viewkit.exceptions import ViewConfigError, ViewNotFoundError
from viewkit.models import ColumnDef, FieldDef, ViewDef


class ViewBuilder:
    """
    Loads views.yaml and builds ViewDef objects on request.

    The YAML file is loaded once at construction time. Call get_view()
    to retrieve a parsed ViewDef by name.

    Args:
        views_path: Path to the views.yaml file to load.

    Raises:
        ViewConfigError: If the file is missing, unreadable, or malformed.
    """

    def __init__(self, views_path: Path):
        self._path = views_path
        self._raw = self._load(views_path)

    # -- Public interface -----------------------------------------------------

    def get_view(self, name: str) -> ViewDef:
        """
        Return a parsed ViewDef for the named view.

        Args:
            name: Key in views.yaml (e.g. "projects", "tasks").

        Returns:
            ViewDef with title, columns, and fields populated.

        Raises:
            ViewNotFoundError: If name is not present in views.yaml.
            ViewConfigError:   If the view definition is malformed.
        """
        if name not in self._raw:
            raise ViewNotFoundError(
                f"View '{name}' not found in {self._path}. "
                f"Available views: {', '.join(self._raw.keys())}"
            )
        return self._parse_view(name, self._raw[name])

    def get_all_views(self) -> dict[str, ViewDef]:
        """
        Return all views defined in views.yaml as a dict keyed by name.

        Returns:
            Dict mapping view name → ViewDef.

        Raises:
            ViewConfigError: If any view definition is malformed.
        """
        return {name: self._parse_view(name, data) for name, data in self._raw.items()}

    def list_view_names(self) -> list[str]:
        """
        Return the names of all views defined in views.yaml.

        Returns:
            List of view name strings in definition order.
        """
        return list(self._raw.keys())

    # -- Parsing --------------------------------------------------------------

    def _parse_view(self, name: str, data: dict) -> ViewDef:
        """
        Parse a single view definition dict into a ViewDef.

        Args:
            name: The view key from views.yaml.
            data: The raw dict for this view.

        Returns:
            Populated ViewDef.

        Raises:
            ViewConfigError: If required keys are missing or values are invalid.
        """
        if not isinstance(data, dict):
            raise ViewConfigError(
                f"View '{name}' in {self._path} must be a mapping, "
                f"got {type(data).__name__}."
            )

        title = data.get("title")
        if not title:
            raise ViewConfigError(
                f"View '{name}' in {self._path} is missing required key 'title'."
            )

        columns = [
            self._parse_column(name, i, col)
            for i, col in enumerate(data.get("columns") or [])
        ]

        fields = [
            self._parse_field(name, i, fld)
            for i, fld in enumerate(data.get("fields") or [])
        ]

        return ViewDef(name=name, title=title, columns=columns, fields=fields)

    def _parse_column(self, view_name: str, index: int, data: dict) -> ColumnDef:
        """
        Parse a single column definition dict into a ColumnDef.

        Args:
            view_name: Parent view name, used in error messages.
            index:     Position in the columns list, used in error messages.
            data:      Raw column dict.

        Returns:
            Populated ColumnDef.

        Raises:
            ViewConfigError: If required keys are missing.
        """
        if not isinstance(data, dict):
            raise ViewConfigError(
                f"View '{view_name}', column {index}: expected a mapping, "
                f"got {type(data).__name__}."
            )

        name = data.get("name")
        label = data.get("label")

        if not name:
            raise ViewConfigError(
                f"View '{view_name}', column {index}: missing required key 'name'."
            )
        if not label:
            raise ViewConfigError(
                f"View '{view_name}', column {index} ('{name}'): "
                f"missing required key 'label'."
            )

        return ColumnDef(
            name=name,
            label=label,
            link=bool(data.get("link", False)),
            sortable=bool(data.get("sortable", False)),
            truncate=data.get("truncate"),
        )

    def _parse_field(self, view_name: str, index: int, data: dict) -> FieldDef:
        """
        Parse a single field definition dict into a FieldDef.

        Args:
            view_name: Parent view name, used in error messages.
            index:     Position in the fields list, used in error messages.
            data:      Raw field dict.

        Returns:
            Populated FieldDef.

        Raises:
            ViewConfigError: If required keys are missing or values are invalid.
        """
        if not isinstance(data, dict):
            raise ViewConfigError(
                f"View '{view_name}', field {index}: expected a mapping, "
                f"got {type(data).__name__}."
            )

        name = data.get("name")
        label = data.get("label")

        if not name:
            raise ViewConfigError(
                f"View '{view_name}', field {index}: missing required key 'name'."
            )
        if not label:
            raise ViewConfigError(
                f"View '{view_name}', field {index} ('{name}'): "
                f"missing required key 'label'."
            )

        try:
            return FieldDef(
                name=name,
                label=label,
                field_type=data.get("type", "text"),
                required=bool(data.get("required", False)),
                readonly=bool(data.get("readonly", False)),
                source=data.get("source"),
                placeholder=data.get("placeholder"),
                help_text=data.get("help_text"),
            )
        except ValueError as exc:
            raise ViewConfigError(
                f"View '{view_name}', field '{name}': {exc}"
            ) from exc

    # -- File loading ---------------------------------------------------------

    @staticmethod
    def _load(path: Path) -> dict:
        """
        Load and parse a views.yaml file.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed dict of view definitions.

        Raises:
            ViewConfigError: If the file is missing, unreadable, or invalid YAML.
        """
        if not path.exists():
            raise ViewConfigError(f"views.yaml not found: {path}")

        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise ViewConfigError(
                f"Could not read views.yaml at {path}: {exc}"
            ) from exc

        if not data or not isinstance(data, dict):
            raise ViewConfigError(
                f"views.yaml at {path} is empty or not a valid mapping."
            )

        return data
