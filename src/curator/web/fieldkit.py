"""
curator.web.fieldkit - Schema-driven form field generation.

Introspects a v_*_detail view via api.get_field_schema(), applies a
Tier-1 Postgres-type-to-control map, and merges a YAML override file for
anything Tier-1 can't decide alone. Produces viewkit.models.FieldDef
objects directly — fieldkit does not define its own field model, it
populates the one viewkit already has (single canonical implementation,
per project_rules.md).

Fails loudly (FieldSchemaError) at construction time if any *_id column
or integer column has no matching override entry. This is deliberate:
fieldkit's cache is built once during FastAPI's lifespan startup (see
app.py), so a misconfigured view/override crashes uvicorn before it ever
serves a request, rather than rendering a broken control in front of
Felipe. See sql_conventions.md's *_id / bare-integer rule for why these
columns are never defaulted.

Override file location follows the same shipped-default / user-override
pattern as curator.yaml (see config.py):
    Shipped default:  curator/data/fieldkit_overrides.yaml
    User override:    ~/.config/curator/fieldkit_overrides.yaml
Merged with ConfigManager._merge() — reused directly rather than
duplicating that merge logic a second time.

Usage:
    from curator.web.fieldkit import FieldKit

    kit = await FieldKit.create(db, "projects.v_project_detail")
    kit.fields  # list[FieldDef], in view column order
"""

from pathlib import Path
from typing import Optional

import yaml

from dbkit.connection import AsyncDBConnection
from viewkit.models import FieldDef

from curator.config import ConfigManager
from curator.exceptions import FieldSchemaError
from curator.web.deps import _fetch_json_scalar


# Tier-1 map: information_schema.columns "data_type" string -> viewkit
# FieldDef.field_type. Algorithmic constant, not user-facing config —
# exceptions to this default (every *_id column, any bare integer, any
# field where this default is wrong for that specific column) go in the
# override YAML file, not here.
_TIER1_TYPE_MAP = {
    "character varying": "text",
    "text": "textarea",
    "boolean": "checkbox",
    "date": "date",
}

# Postgres integer types always require an explicit override — see
# sql_conventions.md's *_id / bare-integer rule. Never defaulted, even
# if a future bare (non-FK) integer column shows up.
_INTEGER_TYPES = {"bigint", "integer", "smallint"}

# Shipped default lives in curator/data/ — same directory curator.yaml
# ships from. fieldkit.py is one level deeper (curator/web/) than
# config.py (curator/), hence parents[1] rather than parent.
_DATA_DIR = Path(__file__).parents[1] / "data"
_DEFAULT_OVERRIDES = _DATA_DIR / "fieldkit_overrides.yaml"

_USER_CONFIG_DIR = Path.home() / ".config" / "curator"
_USER_OVERRIDES = _USER_CONFIG_DIR / "fieldkit_overrides.yaml"


class FieldKit:  # pylint: disable=too-few-public-methods
    # Pylint only counts create() as public — every other method is
    # an intentional _-prefixed internal helper (_fetch_schema,
    # _load_overrides, _read_yaml, _build_field, _default_label).
    # Same shape as FormAction/FormActions in formkit.py: a class with
    # one real public entry point and several private steps behind it
    # is correct here, not a gap to restructure around.
    """
    A built list of FieldDef objects for one entity's detail view.

    Construction requires a DB call (api.get_field_schema()), so this
    class is built via the async FieldKit.create() factory rather than
    a synchronous __init__.
    """
    def __init__(
        self,
        view_name: str,
        fields: list[FieldDef],
        options: Optional[dict] = None,
    ):
        self.view_name = view_name
        self.fields = fields
        self.options = options or {}

    @classmethod
    async def create(
        cls,
        db: AsyncDBConnection,
        view_name: str,
        overrides_path: Optional[Path] = None,
    ) -> "FieldKit":
        """
        Build a FieldKit for a single schema-qualified view.

        Args:
            db:             Open AsyncDBConnection.
            view_name:      Schema-qualified view name, e.g.
                            'projects.v_project_detail'.
            overrides_path: Explicit override file path — bypasses the
                            shipped-default/user-override resolution
                            entirely. Intended for tests; leave None in
                            application code.

        Returns:
            Populated FieldKit, fields in view column order, options
            cached per source name for select fields.

        Raises:
            FieldSchemaError: If the view has no columns (bad or
                              misspelled view name), any *_id /
                              integer column has no matching override,
                              or any declared source doesn't resolve.
        """
        columns = await cls._fetch_schema(db, view_name)
        if not columns:
            raise FieldSchemaError(
                f"api.get_field_schema('{view_name}') returned no "
                f"columns. Check the view name is correct and "
                f"schema-qualified, e.g. 'projects.v_project_detail'."
            )

        overrides = cls._load_overrides(overrides_path)
        entity_overrides = overrides.get(view_name, {})

        fields = [
            cls._build_field(view_name, column, entity_overrides)
            for column in columns
            if column["name"] != "id"
        ]

        await cls._validate_sources(db, view_name, fields)
        options = await cls._load_options(db, fields)

        return cls(view_name, fields, options)

    # -- Internal ---------------------------------------------------------

    @staticmethod
    async def _fetch_schema(db: AsyncDBConnection, view_name: str) -> list:
        """Call api.get_field_schema() and return the column list."""
        result = await _fetch_json_scalar(
            db, "SELECT api.get_field_schema(%s)", (view_name,)
        )
        return result or []

    @staticmethod
    def _load_overrides(overrides_path: Optional[Path]) -> dict:
        """
        Load and merge the fieldkit override YAML files.

        Args:
            overrides_path: Explicit path (tests), or None to use the
                            shipped-default/user-override resolution.

        Returns:
            Merged dict: {view_name: {column_name: {override attrs}}}.
        """
        if overrides_path is not None:
            return FieldKit._read_yaml(overrides_path)

        defaults = FieldKit._read_yaml(_DEFAULT_OVERRIDES)
        if _USER_OVERRIDES.exists():
            user = FieldKit._read_yaml(_USER_OVERRIDES)
            return ConfigManager._merge(  # pylint: disable=protected-access
                defaults, user
            )
        return defaults

    @staticmethod
    def _read_yaml(path: Path) -> dict:
        """Read a single override YAML file. Empty dict if absent."""
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}

    @classmethod
    def _build_field(
        cls, view_name: str, column: dict, entity_overrides: dict
    ) -> FieldDef:
        """
        Build one FieldDef from a column dict + any override entry.

        Args:
            view_name:        Parent view name, used in error messages.
            column:           One item from api.get_field_schema()'s
                              result: {"name", "data_type", "position"}.
            entity_overrides: This view's slice of the override file:
                              {column_name: {control, label, source, ...}}.

        Returns:
            Populated FieldDef.

        Raises:
            FieldSchemaError: If the column needs an override (*_id or
                              integer type) and none is declared.
        """
        name = column["name"]
        data_type = column["data_type"]
        override = entity_overrides.get(name)

        if override is not None:
            return FieldDef(
                name=name,
                label=override.get("label", cls._default_label(name)),
                field_type=override.get("control", "text"),
                required=bool(override.get("required", False)),
                readonly=bool(override.get("readonly", False)),
                source=override.get("source"),
                placeholder=override.get("placeholder"),
                help_text=override.get("help_text"),
            )

        if name.endswith("_id") or data_type in _INTEGER_TYPES:
            raise FieldSchemaError(
                f"View '{view_name}', column '{name}' ({data_type}): "
                f"no override declared. *_id and integer columns always "
                f"require an explicit control — add an entry under "
                f"'{view_name}:' / '{name}:' in "
                f"curator/data/fieldkit_overrides.yaml (or the user "
                f"override at ~/.config/curator/fieldkit_overrides.yaml)."
            )

        return FieldDef(
            name=name,
            label=cls._default_label(name),
            field_type=_TIER1_TYPE_MAP.get(data_type, "text"),
        )

    @staticmethod
    async def _validate_sources(
        db: AsyncDBConnection, view_name: str, fields: list[FieldDef]
    ) -> None:
        """
        Confirm every field's declared lookup source actually resolves.

        Calls api.get_lookup() once per field that has a source
        declared (select fields only — most fields have source=None
        and are skipped). A NULL result means the source name isn't
        recognized by any CASE branch in api.get_lookup() — almost
        always a typo in the override YAML.

        Args:
            db:        Open connection.
            view_name: Parent view name, used in the error message.
            fields:    The FieldDef list just built for this view.

        Raises:
            FieldSchemaError: If any field's source returns NULL from
                              api.get_lookup(). See this changedoc's
                              header for the one known false-positive
                              case (a real source name whose table
                              happens to have zero rows).
        """
        for field in fields:
            if field.source is None:
                continue

            options = await _fetch_json_scalar(
                db, "SELECT api.get_lookup(%s)", (field.source,)
            )
            if not options:
                raise FieldSchemaError(
                    f"View '{view_name}', field '{field.name}': source "
                    f"'{field.source}' returned no options from "
                    f"api.get_lookup(). Check the source name matches "
                    f"one of the CASE branches in api.get_lookup() "
                    f"(08b_api_lookup.sql) — or, if the source name is "
                    f"correct, confirm its backing table actually has "
                    f"rows (a real source with zero matching rows looks "
                    f"identical to an unrecognized one here)."
                )

    @staticmethod
    async def _load_options(
        db: AsyncDBConnection, fields: list[FieldDef]
    ) -> dict:
        """
        Fetch and cache select-field options, keyed by source name.

        Called after _validate_sources, which already confirmed every
        declared source resolves to something non-empty — this collects
        those results once at startup so the render step never needs
        its own get_lookup() call per request.

        Args:
            db:     Open connection.
            fields: The FieldDef list already built and validated.

        Returns:
            Dict of source name -> options list (each option a
            {"value": ..., "label": ...} dict, per api.get_lookup()'s
            return shape). Fields with no source contribute nothing;
            two fields sharing the same source only trigger one
            get_lookup() call here.
        """
        options = {}
        for field in fields:
            if field.source is None or field.source in options:
                continue
            options[field.source] = await _fetch_json_scalar(
                db, "SELECT api.get_lookup(%s)", (field.source,)
            )
        return options

    @staticmethod
    def _default_label(name: str) -> str:
        """'target_date' -> 'Target Date'. Used when no override supplies one."""
        return name.replace("_", " ").title()
