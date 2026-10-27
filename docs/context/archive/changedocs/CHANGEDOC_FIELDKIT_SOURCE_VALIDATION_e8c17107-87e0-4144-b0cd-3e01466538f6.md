# Changedoc: `fieldkit.py` — validate `source:` values at startup

**Date:** 2026-07-04
**Reason:** Closes the gap flagged in `CHANGEDOC_API_GET_LOOKUP.md`
point 3 — a typo'd `source:` value in `fieldkit_overrides.yaml` (e.g.
`project_type` instead of `project_types`) currently wouldn't be caught
until something actually tried to render that field and got an empty
dropdown. This makes it fail the same way a missing `*_id` override
does: loudly, at app startup, before `uvicorn` ever serves a request.

**Depends on:** `08b_api_lookup.sql` (`api.get_lookup()`) already applied
and verified in pgAdmin.

**One known limitation, flagged rather than hidden:** `jsonb_agg()` over
zero matching rows returns `NULL` in Postgres — identical to what
`api.get_lookup()` returns for a source name it doesn't recognize at
all. So a *real, correctly-spelled* lookup source whose table happens to
have zero rows would trigger this same startup crash, indistinguishable
from an actual typo. Not a concern in practice right now — both
`projects.project_type` and `projects.project_status` are seeded with
real rows — but worth knowing this validation can't tell "wrong name"
apart from "right name, empty table" if that ever changes.

---

## `src/curator/web/fieldkit.py`

### BEFORE

```python
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

        return cls(view_name, fields)
```

### AFTER

```python
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

        return cls(view_name, fields)
```

**New method, added after `_build_field`:**

```python
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
```

**Module docstring update** — add `_validate_sources` to the list of
what construction does, so the crash-at-startup guarantee is documented
in one place:

### BEFORE (module docstring, relevant excerpt)

```python
Fails loudly (FieldSchemaError) at construction time if any *_id column
or integer column has no matching override entry. This is deliberate:
fieldkit's cache is built once during FastAPI's lifespan startup (see
app.py), so a misconfigured view/override crashes uvicorn before it ever
serves a request, rather than rendering a broken control in front of
Felipe. See sql_conventions.md's *_id / bare-integer rule for why these
columns are never defaulted.
```

### AFTER

```python
Fails loudly (FieldSchemaError) at construction time in two cases:
  - Any *_id column or integer column has no matching override entry
    (see sql_conventions.md's *_id / bare-integer rule).
  - Any field's declared "source" (a select field's lookup name) isn't
    recognized by api.get_lookup() — almost always a typo in the
    override YAML.
Both are deliberate: fieldkit's cache is built once during FastAPI's
lifespan startup (see app.py), so a misconfigured view/override/source
crashes uvicorn before it ever serves a request, rather than rendering a
broken or empty control in front of Felipe.
```

---

## `tests/unit/test_fieldkit.py`

**New helper, replacing the plain `_mock_db`** — the old one always
returns the same fixed value regardless of which SQL was passed in
(`AsyncMock(return_value=...)` ignores call arguments), which happened
to not matter before this change, but would silently mask a broken
`_validate_sources` implementation now (it would "pass" a `get_lookup`
call by coincidentally handing back the column list instead of options,
since both are non-empty and the old mock can't tell the two calls
apart). Replaced with a `side_effect` function that actually branches on
the SQL text, so each test's mock only returns what its specific query
would really return.

### BEFORE

```python
def _mock_db(columns: list[dict]):
    """Build a mock AsyncDBConnection whose get_field_schema() call
    returns the given column list, matching _fetch_json_scalar's
    unwrap contract: fetch_one() returns {"get_field_schema": [...]}."""
    return SimpleNamespace(
        fetch_one=AsyncMock(return_value={"get_field_schema": columns})
    )
```

### AFTER

```python
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
```

*(Needs `from typing import Optional` added to the test file's imports —
not already present since the module under test does the async work,
not the test file itself.)*

**Existing test needing an update** — `TestRequiresOverride
.test_id_column_with_override_succeeds` declares a `source:
"project_types"` override, which now triggers a `get_lookup` call that
the old mock never modeled correctly. Update its `_mock_db` call to
supply a matching `lookups` dict:

### BEFORE

```python
    @pytest.mark.asyncio
    async def test_id_column_with_override_succeeds(self, tmp_path):
        db = _mock_db([
            {"name": "type_id", "data_type": "bigint", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {
            "projects.v_project_detail": {
                "type_id": {"control": "select", "label": "Type", "source": "project_types"}
            }
        })

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "select"
        assert kit.fields[0].label == "Type"
        assert kit.fields[0].source == "project_types"
```

### AFTER

```python
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
```

**New test class**, added after `TestRequiresOverride` (before
`TestIdColumnExcluded`):

```python
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
```

---

## Apply and verify

1. Add `_validate_sources` to `fieldkit.py`, call it from `create()` as
   shown, update the module docstring.
2. Replace `_mock_db` in `test_fieldkit.py`, add `Optional` to its
   imports, update `test_id_column_with_override_succeeds`'s call site,
   add the new `TestSourceValidation` class.
3. `pytest tests/unit/test_fieldkit.py -v` — all tests, old and new,
   should pass.
4. `pylint src/` — should stay at 10.00/10.
5. Restart `uvicorn` — this is the real test again. Should still start
   clean: both `type_id`'s `project_types` and `status_id`'s
   `project_statuses` sources are real, seeded lookup tables per the
   `08b_api_lookup.sql` verification already done in pgAdmin.
6. As a deliberate negative test (optional, but worth doing once): edit
   `fieldkit_overrides.yaml` locally to misspell one source (e.g.
   `project_type` instead of `project_types`), restart `uvicorn`, confirm
   it crashes with a legible message naming the field and bad source —
   then revert the typo. Seeing the failure mode actually work once, on
   purpose, is worth the thirty seconds.
