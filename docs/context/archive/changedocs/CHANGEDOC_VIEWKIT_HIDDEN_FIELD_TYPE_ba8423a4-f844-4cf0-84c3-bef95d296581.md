# CHANGEDOC — viewkit: Add `hidden` field_type to FieldDef

**Repo:** `dev-utils` (`~/projects/dev-utils/python/viewkit/`)
**Status:** Ready to apply. Requires reinstall into Curator's venv —
viewkit is a regular (non-editable) install there, confirmed via
`pip show viewkit` / `pip list -e` (2026-07-10).

## Summary

Curator's Tasks UI wiring needs a `hidden` field type in fieldkit's
generic field-rendering system, for `project_id`/`parent_id` on tasks —
FK columns that must be submitted with the form but never shown as an
editable control (see `nested_master_detail_design.md`). `FieldDef`'s
own `__post_init__` validates `field_type` against a fixed set that
doesn't include `hidden`, so constructing one currently raises
`ValueError` before this can be used anywhere.

This is a one-line change to the validation set in `viewkit.models`,
not a Curator-side change — `viewkit` is Carolyn's own `dev-utils`
package (Curator is currently its only consumer, but it was designed
for reuse), so the fix belongs in the shared package, not worked around
locally in Curator.

---

## File — `python/viewkit/models.py`

### BEFORE

```python
    def __post_init__(self):
        valid_types = {"text", "textarea", "select", "date", "number", "checkbox"}
        if self.field_type not in valid_types:
            raise ValueError(
                f"FieldDef '{self.name}': invalid field_type '{self.field_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )
        if self.field_type == "select" and self.source is None:
            raise ValueError(
                f"FieldDef '{self.name}': field_type 'select' requires a 'source'."
            )
```

### AFTER

```python
    def __post_init__(self):
        valid_types = {
            "text", "textarea", "select", "date", "number", "checkbox", "hidden",
        }
        if self.field_type not in valid_types:
            raise ValueError(
                f"FieldDef '{self.name}': invalid field_type '{self.field_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )
        if self.field_type == "select" and self.source is None:
            raise ValueError(
                f"FieldDef '{self.name}': field_type 'select' requires a 'source'."
            )
```

### Why

- `hidden` needs to be a legal `field_type` for fieldkit's `_build_field()`
  to produce a `FieldDef` for `project_id`/`parent_id` on tasks without
  raising at startup.
- No other validation changes: a hidden field has no special
  requirement analogous to `select`'s `source` — `required`, `readonly`,
  `source`, `placeholder`, and `help_text` remain meaningful (or
  harmlessly unused) exactly as they are for every other type.
- Also update the module docstring's `FieldDef.field_type` doc comment
  (`"One of: text, textarea, select, date, number, checkbox."`) to
  include `hidden` in that list, since it's the field-level
  documentation of the same valid-types set:

```python
        field_type: Input type. One of: text, textarea, select, date,
                    number, checkbox, hidden. Defaults to 'text'.
```

---

## Apply and deploy — full sequence

Confirmed 2026-07-10: `viewkit` is installed as a **regular
(non-editable)** package in Curator's venv (copied into
`site-packages`, not linked to the `dev-utils` repo). Editing the repo
source alone does nothing until reinstalled.

1. Edit `~/projects/dev-utils/python/viewkit/models.py` per the diff above.
2. Commit and push to GitHub per normal `dev-utils` workflow.
3. Reinstall into Curator's venv (from `~/projects/curator`, `.venv` active):

   ```bash
   pip install --force-reinstall --no-deps /home/carolyn/projects/dev-utils/python/viewkit
   ```

   `--no-deps` avoids pip also touching `dbkit`/`pyyaml` unnecessarily.
   `--force-reinstall` is required because the version number
   (`0.1.0`) isn't changing — without it, pip sees the same version
   already installed and skips the reinstall silently.

4. Restart uvicorn to pick up the new code (already-imported modules in
   a running process won't see the change either way, editable install
   or not).

## Not in scope here

- Making `viewkit` an editable install (`pip install -e
  ~/projects/dev-utils/python/viewkit`) so future `viewkit` changes
  don't need step 3's reinstall dance. Worth doing at some point since
  `viewkit` is genuinely shared infrastructure, but it's a one-time
  convenience change, not required to unblock this work — noted here,
  not actioned.
- Any bump to `viewkit`'s version number (`0.1.0`). Left unchanged;
  revisit if/when `viewkit` gets a real versioning discipline.
- The Curator-side consumers of this new `hidden` type
  (`fieldkit_overrides.yaml`, `_detail_form_fields.html`, `panel.py`,
  `tasks.py`) — separate changedoc, Curator repo, depends on this one
  being applied and reinstalled first.
