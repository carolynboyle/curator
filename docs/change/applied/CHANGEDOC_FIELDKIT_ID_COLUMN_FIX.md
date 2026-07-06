# Changedoc: `fieldkit.py` — skip the `id` column instead of requiring an override for it

**Date:** 2026-07-04
**Reason:** Real bug, caught by the startup-crash design working exactly
as intended. `_build_field`'s override-required check was
`name.endswith("_id") or data_type in _INTEGER_TYPES` — the second half
of that `or` catches *any* bigint/integer/smallint column, which
includes the bare `id` column itself (always `bigint`, never named with
an `_id` suffix). Per `sql_conventions.md`: **`id` is excluded from
anything downstream the same way `*_by` is — it's identity, not a field
a user fills in.** It's kept in the `v_*_detail` views (needed to know
which record you're looking at), but it was never supposed to become a
form field, let alone require an override to become one.

**Source verified:** confirmed by the actual traceback — `View
'projects.v_project_detail', column 'id' (bigint): no override
declared` — not reconstructed from memory.

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

        return cls(view_name, fields)
```

**Why here, not inside `_build_field`:** `id` isn't a "column that
happens to need an override" — it's a column that should never become a
`FieldDef` at all. Filtering it out of the list comprehension before
`_build_field` ever sees it makes that explicit: `_build_field`'s job
stays "decide the control for a field-shaped column," not "also know
which columns aren't fields." Matches how `*_by` columns are already
handled — excluded at the view layer (`sql_conventions.md`), not
special-cased in application code. `id` gets the same treatment one
layer later, in `fieldkit` instead of SQL, since the view still needs
to select `id` (to identify the record) even though the form never
renders it.

---

## Apply and verify

1. Add the `if column["name"] != "id"` filter to the list comprehension
   in `FieldKit.create()` — the only change.
2. Add a test confirming this — `tests/unit/test_fieldkit.py`, new test
   in `TestColumnOrder` or a new small class:

```python
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
```

3. `pytest tests/unit/test_fieldkit.py -v` — should now include this new
   test, all passing.
4. `pylint src/` — should stay at 10.00/10, no new findings from a
   single added filter condition.
5. Restart `uvicorn` again — this is the real check. Should start clean
   this time, for all three entities (`projects`, `contacts`,
   `organizations`), since none of their views have any other
   undeclared `*_id`/integer columns per the pgAdmin checks already run.
6. If it starts clean: hit `/health` to confirm the app is actually
   serving requests, not just that `lifespan` didn't throw.
