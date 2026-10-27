# Changedoc: `FieldKit` caches select options + new field-fragment template

**Date:** 2026-07-04
**Reason:** First two pieces of fetch-and-swap. `FieldKit` already
validates every declared `source:` resolves via `api.get_lookup()`
(previous changedoc) — this reuses that same call to cache the actual
*options*, so the render step never needs its own `get_lookup()` call
per request. The new template is the actual field-rendering logic that
replaces `_detail_panel.html`'s hardcoded per-entity blocks.

**Not yet included in this changedoc:** the `/panel/{entity}/{id}` route
and the `_detail_panel.html`/`detail-panel.js` wiring — those need
`crew.py`'s existing `Jinja2Templates` setup verified first (see note
at the end).

---

## 1. `src/curator/web/fieldkit.py` (edit)

**Design note:** `_validate_sources` already confirmed every source
resolves to something non-empty. `_load_options` reuses that same
`get_lookup()` call to actually cache the result — kept as a separate
method rather than merged into `_validate_sources` to avoid touching
that method's already-tested contract (its existing tests assert only
on raising behavior, not on any return value). The tradeoff: a source
used by more than one field only gets queried once here (deduplicated
by source name), but the *same* source does get queried twice overall
across `_validate_sources` + `_load_options` — a small, deliberate
redundancy at startup only, not per-request, traded for not disturbing
already-verified code.

### BEFORE

```python
    def __init__(self, view_name: str, fields: list[FieldDef]):
        self.view_name = view_name
        self.fields = fields

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
            Populated FieldKit, fields in view column order.

        Raises:
            FieldSchemaError: If the view has no columns (bad or
                              misspelled view name), or any *_id /
                              integer column has no matching override.
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

        return cls(view_name, fields)
```

### AFTER

```python
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
```

**New method, added after `_validate_sources`:**

```python
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
```

---

## 2. `src/curator/templates/partials/_detail_form_fields.html` (new file)

**Design note on `record[field.name]` vs. `record.get(field.name)`:**
using `.get()` explicitly rather than `[]` subscript, since `record` is
`{}` for a new record and every field must resolve to `None` cleanly
rather than risk a Jinja `Undefined` on a missing key.

```html
{#
  _detail_form_fields.html

  Renders the field inputs for a single entity's detail form — driven
  entirely by fieldkit's FieldDef list, no per-entity Jinja branching.
  Fetched by GET /panel/{entity}/{id} (or /panel/{entity}/new) and
  swapped into #detail-form-fields by detail-panel.js on every panel
  open. Replaces the old approach of one static per-entity form baked
  into _detail_panel.html at page load.

  Parameters:
    - fields  (list[FieldDef]) — from FieldKit.fields, in view column order
    - record  (dict) — current field values, or {} for a new record
    - options (dict) — source name -> list of {"value", "label"} dicts,
                        from FieldKit.options; only consulted for
                        field_type == "select"
#}
{% for field in fields %}
  <div class="form-group">
    <label for="detail-{{ field.name }}">{{ field.label }}</label>

    {% if field.field_type == "text" %}
      <input
        type="text"
        id="detail-{{ field.name }}"
        name="{{ field.name }}"
        value="{{ record.get(field.name) or '' }}"
        {% if field.placeholder %}placeholder="{{ field.placeholder }}"{% endif %}
      />

    {% elif field.field_type == "textarea" %}
      <textarea
        id="detail-{{ field.name }}"
        name="{{ field.name }}"
        {% if field.placeholder %}placeholder="{{ field.placeholder }}"{% endif %}
      >{{ record.get(field.name) or '' }}</textarea>

    {% elif field.field_type == "select" %}
      <select id="detail-{{ field.name }}" name="{{ field.name }}">
        <option value="">—</option>
        {% for opt in options.get(field.source, []) %}
          <option
            value="{{ opt.value }}"
            {% if record.get(field.name) == opt.value %}selected{% endif %}
          >
            {{ opt.label }}
          </option>
        {% endfor %}
      </select>

    {% elif field.field_type == "date" %}
      <input
        type="date"
        id="detail-{{ field.name }}"
        name="{{ field.name }}"
        value="{{ record.get(field.name) or '' }}"
      />

    {% elif field.field_type == "checkbox" %}
      <input
        type="checkbox"
        id="detail-{{ field.name }}"
        name="{{ field.name }}"
        {% if record.get(field.name) %}checked{% endif %}
      />
    {% endif %}

    {% if field.help_text %}
      <small class="form-help">{{ field.help_text }}</small>
    {% endif %}
  </div>
{% endfor %}
```

---

## 3. `tests/unit/test_fieldkit.py` — new tests for `_load_options`

Added after `TestSourceValidation`:

```python
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
```

---

## Apply and verify (this piece only)

1. Update `fieldkit.py`'s `__init__`/`create` and add `_load_options`.
2. Create the new template file at
   `src/curator/templates/partials/_detail_form_fields.html` — **verify
   this path against your actual templates directory structure first**;
   I'm inferring `partials/` from `_detail_panel.html`'s existing
   `{% include 'partials/_form_actions.html' %}` reference, but haven't
   directly confirmed the directory layout.
3. Add the three new tests to `test_fieldkit.py`.
4. `pytest tests/unit/test_fieldkit.py -v` — should all pass.
5. `pylint src/` — should stay at 10.00/10.
6. Restart `uvicorn` — same check as always, should still start clean.

This piece is self-contained and safe to apply now — nothing in the
existing app reads `FieldKit.options` yet, and the new template file
isn't referenced by anything yet either, so there's no risk of breaking
what's currently working.

---

## What I need from you before the next piece

Please upload your current `crew.py`. I need to see how it currently
sets up `Jinja2Templates` (import path, directory argument, variable
name) before I can write the `/panel/{entity}/{id}` route correctly —
every route file I've verified this session either returns JSON or
doesn't touch templates at all, so I don't want to guess at this and
risk an import that doesn't match your actual setup.
