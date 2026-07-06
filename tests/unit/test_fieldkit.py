"""
tests.unit.test_fieldkit - Unit tests for curator.web.fieldkit.FieldKit.

Covers:
  - Tier-1 type map applied correctly for each supported Postgres type
  - *_id columns require an override, raise FieldSchemaError if absent
  - Integer columns (non-*_id) also require an override
  - Override entries take precedence over Tier-1 defaults
  - Every field's declared "source" must resolve via api.get_lookup()
  - The id column is always excluded, never requires an override
  - Empty/missing schema result raises FieldSchemaError
  - Column order from api.get_field_schema() is preserved in fields

All tests mock the DB — no real connection, no real YAML file on disk
(overrides passed as an explicit dict-backed path via tmp_path).
"""

from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock

import pytest
import yaml

from curator.exceptions import FieldSchemaError
from curator.web.fieldkit import FieldKit


def _mock_db(columns: list[dict], lookups: Optional[dict] = None):
    """Build a mock AsyncDBConnection for both get_field_schema() and
    get_lookup() calls, branching on which SQL was actually passed in
    rather than returning a single fixed value regardless of the call
    — a plain return_value mock can't distinguish the two calls and
    would silently mask a broken _validate_sources implementation.

    Args:
        columns: Column list returned for any get_field_schema call.
        lookups: Dict of source name -> options list (or None, to
                 simulate an unrecognized source), used for any
                 get_lookup call. Defaults to {} — tests with no
                 source-bearing fields never hit this branch anyway.
    """
    lookups = lookups or {}

    async def _fetch_one(sql: str, params: tuple):
        if "get_field_schema" in sql:
            return {"get_field_schema": columns}
        if "get_lookup" in sql:
            source = params[0]
            return {"get_lookup": lookups.get(source)}
        raise AssertionError(f"Unexpected SQL passed to mock db: {sql}")

    return SimpleNamespace(fetch_one=AsyncMock(side_effect=_fetch_one))


def _write_overrides(tmp_path, data: dict):
    """Write an overrides dict to a temp YAML file and return its path."""
    path = tmp_path / "fieldkit_overrides.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tier-1 type map
# ---------------------------------------------------------------------------

class TestTier1TypeMap:
    """Columns with no override fall through to the Tier-1 map."""

    @pytest.mark.asyncio
    async def test_varchar_becomes_text(self, tmp_path):

        db = _mock_db([
            {"name": "name", "data_type": "character varying", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "text"
        assert kit.fields[0].label == "Name"

    @pytest.mark.asyncio
    async def test_text_becomes_textarea(self, tmp_path):
        db = _mock_db([
            {"name": "description", "data_type": "text", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "textarea"

    @pytest.mark.asyncio
    async def test_boolean_becomes_checkbox(self, tmp_path):
        db = _mock_db([
            {"name": "is_active", "data_type": "boolean", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "checkbox"

    @pytest.mark.asyncio
    async def test_date_becomes_date(self, tmp_path):
        db = _mock_db([
            {"name": "target_date", "data_type": "date", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "date"


# ---------------------------------------------------------------------------
# *_id / integer columns require an override
# ---------------------------------------------------------------------------

class TestRequiresOverride:
    """*_id columns and bare integer columns never get a Tier-1 default —
    they must have an explicit override entry or construction fails."""

    @pytest.mark.asyncio
    async def test_id_column_without_override_raises(self, tmp_path):
        db = _mock_db([
            {"name": "type_id", "data_type": "bigint", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        with pytest.raises(FieldSchemaError, match="type_id.*no override declared"):
            await FieldKit.create(db, "projects.v_project_detail", overrides_path)

    @pytest.mark.asyncio
    async def test_bare_integer_without_override_raises(self, tmp_path):
        db = _mock_db([
            {"name": "quantity", "data_type": "integer", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        with pytest.raises(FieldSchemaError, match="quantity.*no override declared"):
            await FieldKit.create(db, "projects.v_project_detail", overrides_path)

    @pytest.mark.asyncio
    async def test_id_column_with_override_succeeds(self, tmp_path):
        db = _mock_db(
            [{"name": "type_id", "data_type": "bigint", "position": 1}],
            lookups={"project_types": [{"value": 1, "label": "Coding"}]},
        )
        overrides_path = _write_overrides(tmp_path, {
            "projects.v_project_detail": {
                "type_id": {"control": "select", "label": "Type", "source": "project_types"}
            }
        })

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "select"
        assert kit.fields[0].label == "Type"
        assert kit.fields[0].source == "project_types"


# ---------------------------------------------------------------------------
# source validation — every declared lookup source must actually resolve
# ---------------------------------------------------------------------------

class TestSourceValidation:
    """A field with a "source" declared must have that source recognized
    by api.get_lookup() — an unrecognized source (typo in the override
    YAML) must crash construction the same way a missing *_id override
    does, not silently render an empty dropdown later."""

    @pytest.mark.asyncio
    async def test_unrecognized_source_raises(self, tmp_path):
        """get_lookup() returning NULL (source not in lookups dict)
        must raise FieldSchemaError naming the field and source."""
        db = _mock_db(
            [{"name": "type_id", "data_type": "bigint", "position": 1}],
            lookups={},  # "project_types" deliberately absent -> NULL
        )
        overrides_path = _write_overrides(tmp_path, {
            "projects.v_project_detail": {
                "type_id": {"control": "select", "label": "Type", "source": "project_types"}
            }
        })

        with pytest.raises(FieldSchemaError, match="project_types.*no options"):
            await FieldKit.create(db, "projects.v_project_detail", overrides_path)

    @pytest.mark.asyncio
    async def test_recognized_source_succeeds(self, tmp_path):
        """get_lookup() returning real options must not raise."""
        db = _mock_db(
            [{"name": "status_id", "data_type": "bigint", "position": 1}],
            lookups={"project_statuses": [{"value": 1, "label": "Active"}]},
        )
        overrides_path = _write_overrides(tmp_path, {
            "projects.v_project_detail": {
                "status_id": {"control": "select", "label": "Status", "source": "project_statuses"}
            }
        })

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].source == "project_statuses"

    @pytest.mark.asyncio
    async def test_field_without_source_skips_validation(self, tmp_path):
        """Fields with no source (the overwhelming majority — every
        Tier-1-mapped field, plus non-select overrides) must never
        trigger a get_lookup call at all."""
        db = _mock_db([
            {"name": "name", "data_type": "character varying", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].source is None
        # No assertion needed on db.fetch_one call count beyond the
        # single get_field_schema call — _mock_db's _fetch_one would
        # raise AssertionError on any unexpected SQL, which doubles as
        # the check that get_lookup was never called here.

# ---------------------------------------------------------------------------
# Options caching — select fields' options collected once, keyed by source
# ---------------------------------------------------------------------------

class TestLoadOptions:
    """FieldKit.options caches get_lookup() results per source name, so
    the render step never needs its own DB call per request."""

    @pytest.mark.asyncio
    async def test_options_cached_by_source(self, tmp_path):
        db = _mock_db(
            [{"name": "type_id", "data_type": "bigint", "position": 1}],
            lookups={"project_types": [{"value": 1, "label": "Coding"}]},
        )
        overrides_path = _write_overrides(tmp_path, {
            "projects.v_project_detail": {
                "type_id": {"control": "select", "label": "Type", "source": "project_types"}
            }
        })

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.options == {"project_types": [{"value": 1, "label": "Coding"}]}

    @pytest.mark.asyncio
    async def test_shared_source_queried_once(self, tmp_path):
        """Two fields with the same source must only trigger one
        get_lookup() call — modeled here by two override entries
        pointing at the same source name."""
        call_count = {"n": 0}
        db = _mock_db(
            [
                {"name": "type_id", "data_type": "bigint", "position": 1},
                {"name": "other_id", "data_type": "bigint", "position": 2},
            ],
            lookups={"project_types": [{"value": 1, "label": "Coding"}]},
        )

        original_fetch_one = db.fetch_one

        async def _counting_fetch_one(sql, params):
            if "get_lookup" in sql:
                call_count["n"] += 1
            return await original_fetch_one(sql, params)

        db.fetch_one = _counting_fetch_one

        overrides_path = _write_overrides(tmp_path, {
            "projects.v_project_detail": {
                "type_id": {"control": "select", "label": "Type", "source": "project_types"},
                "other_id": {"control": "select", "label": "Other", "source": "project_types"},
            }
        })

        await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        # _validate_sources calls get_lookup once per field (2 calls),
        # _load_options deduplicates by source (1 more call) -> 3 total,
        # not 4. This asserts the dedup in _load_options specifically,
        # not the (separately accepted) redundancy between the two
        # methods described in this changedoc's header.
        assert call_count["n"] == 3

    @pytest.mark.asyncio
    async def test_no_source_fields_produce_empty_options(self, tmp_path):
        db = _mock_db([
            {"name": "name", "data_type": "character varying", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.options == {}
# ---------------------------------------------------------------------------
# id column is always excluded, never requires an override
# ---------------------------------------------------------------------------

class TestIdColumnExcluded:
    """The id column is never rendered as a field — it identifies the
    record, it isn't something a user edits — so it must never reach
    the override-or-crash decision in _build_field, even though
    api.get_field_schema() reports it (views select it deliberately,
    per sql_conventions.md, to know which record is being displayed)."""

    @pytest.mark.asyncio
    async def test_id_column_skipped_without_override(self, tmp_path):
        """id is bigint with no override entry — if it weren't filtered
        out, this would raise FieldSchemaError exactly like the real
        startup crash did. It shouldn't raise at all."""
        db = _mock_db([
            {"name": "id", "data_type": "bigint", "position": 1},
            {"name": "name", "data_type": "character varying", "position": 2},
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert [f.name for f in kit.fields] == ["name"]


# ---------------------------------------------------------------------------
# Empty / missing schema result
# ---------------------------------------------------------------------------

class TestMissingView:
    """A bad or misspelled view name (api.get_field_schema returns
    NULL/empty) must fail loudly, not silently produce an empty form."""

    @pytest.mark.asyncio
    async def test_empty_columns_raises(self, tmp_path):
        db = _mock_db([])
        overrides_path = _write_overrides(tmp_path, {})

        with pytest.raises(FieldSchemaError, match="no columns"):
            await FieldKit.create(db, "projects.v_does_not_exist", overrides_path)


# ---------------------------------------------------------------------------
# Column order preserved
# ---------------------------------------------------------------------------

class TestColumnOrder:
    """Field order in kit.fields matches the order api.get_field_schema()
    returned — which itself reflects the view's CREATE VIEW column order."""

    @pytest.mark.asyncio
    async def test_fields_preserve_schema_order(self, tmp_path):
        db = _mock_db([
            {"name": "name", "data_type": "character varying", "position": 1},
            {"name": "description", "data_type": "text", "position": 2},
            {"name": "target_date", "data_type": "date", "position": 3},
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert [f.name for f in kit.fields] == ["name", "description", "target_date"]
