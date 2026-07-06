# Changedoc: `fieldkit.py` — pylint R0903 disable on `FieldKit`

**Date:** 2026-07-04
**Reason:** `pylint` flags `FieldKit` at 1/2 public methods — it only
counts `create()`, since every other method (`_fetch_schema`,
`_load_overrides`, `_read_yaml`, `_build_field`, `_default_label`) is
intentionally `_`-prefixed as internal helpers. Same shape as
`FormAction`/`FormActions` in `formkit.py`, which you already handled
with a documented disable rather than restructuring — same fix here,
not a new pattern.

**Source verified:** `pylint` output confirms this is the only remaining
finding (9.98/10, one line). No other file affected.

---

## `src/curator/web/fieldkit.py`

### BEFORE

```python
class FieldKit:
    """
    A built list of FieldDef objects for one entity's detail view.

    Construction requires a DB call (api.get_field_schema()), so this
    class is built via the async FieldKit.create() factory rather than
    a synchronous __init__.
    """
```

### AFTER

```python
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
```

---

## Apply and verify

1. Replace the class declaration + docstring as shown — nothing else in
   the file changes.
2. `pylint src/` — should now show 10.00/10.
3. `pytest` — no behavior changed, all 33 should still pass.

---

## Still outstanding before this piece is fully verified

- `v_contact_detail` and `v_organization_detail` haven't been checked yet
  the same way `v_project_detail` just was. Same query, swapping schema/
  table:
  ```sql
  SELECT column_name, data_type, ordinal_position
  FROM information_schema.columns
  WHERE table_schema = 'identity' AND table_name = 'v_contact_detail'
  ORDER BY ordinal_position;
  ```
  (and `v_organization_detail`). If either has a `*_id` column, add a
  matching entry to `fieldkit_overrides.yaml` before restarting uvicorn
  — right now the shipped file only has entries under
  `projects.v_project_detail`.
