# Formkit — YAML-Driven Buttons with Accelerator Keys (v2)

**Date:** 2026-06-28  
**Status:** Ready to apply  
**Scope:** Button labels and styles driven by config; all three buttons uniform

---

## Overview

Six changes:

1. **`src/curator/data/forms.yaml`** — new file; separates button definitions
   from preset compositions
2. **`src/curator/formkit.py`** — add `from_yaml()` classmethod
3. **`src/curator/web/routes/crew.py`** — load form actions preset and pass to template
4. **`src/curator/templates/partials/_detail_panel.html`** — remove hardcoded
   `{% set actions %}` block; use `actions` variable from route
5. **`src/curator/templates/partials/_form_actions.html`** — add `| safe` to label
6. **`static/css/components/buttons.css`** — move `.btn-save` to secondary group

---

## Change 1: `src/curator/data/forms.yaml` — NEW FILE

```yaml
# forms.yaml
# Formkit configuration — button definitions and form presets.
#
# Structure:
#   buttons:   Named button definitions. Each button is defined once here
#              and referenced by name in presets. This is the only place
#              you need to edit to change a button's label, class, or tooltip.
#
#   presets:   Named collections of buttons for a specific form context.
#              Presets reference buttons by name and can add context-specific
#              overrides (e.g. form_id differs per form).
#
# Button fields:
#   label      — Button text. Supports HTML: use <u> to mark accelerator letter.
#   type       — HTML button type: submit | button | reset
#   class      — CSS class from buttons.css (e.g. btn-secondary)
#   title      — Tooltip text (shown on hover)
#   data_attrs — Optional dict of data-* attributes
#
# Preset fields:
#   container_class — CSS class applied to the wrapping <div>
#   actions         — Ordered list of buttons to include
#     button        — Name of a button defined in buttons: above
#     form_id       — Optional; associates a submit button with a <form id="...">
#                     Lives in the preset (not the button) because the same
#                     Save button wires to different forms in different contexts.

buttons:
  save:
    label:   "<u>S</u>ave"
    type:    submit
    class:   btn-secondary
    title:   "Save (Alt+S)"

  new:
    label:   "<u>N</u>ew"
    type:    button
    class:   btn-secondary
    title:   "New (Alt+N)"
    data_attrs:
      action: new

  discard:
    label:   "<u>D</u>iscard"
    type:    button
    class:   btn-secondary
    title:   "Discard (Alt+X)"
    data_attrs:
      action: discard

presets:
  detail_panel:
    container_class: detail-panel-actions
    actions:
      - button:  save
        form_id: detail-form
      - button:  new
      - button:  discard

  create_form:
    container_class: form-actions
    actions:
      - button:  save
        form_id: create-form
      - button:  discard
```

**Why:** Button definitions live in one place (`buttons:`). Presets compose
them into context-specific bars (`presets:`). Adding a new button type
(e.g. `delete`, `publish`) means one addition to `buttons:` and a reference
in any presets that need it. `form_id` stays in the preset because the same
Save button wires to different form elements in different contexts.

---

## Change 2: `src/curator/formkit.py` — add `from_yaml()` classmethod

**BEFORE** — imports at top of file:
```python
from typing import List, Dict, Any, Optional
```

**AFTER**:
```python
from pathlib import Path
from typing import Any, Dict, List, Optional
```

**BEFORE** — `FormActions` class ends with `to_dicts()`:
```python
    @staticmethod
    def to_dicts(actions: List[FormAction]) -> List[Dict[str, Any]]:
        """Convert list of FormAction objects to list of dicts for Jinja2."""
        return [action.to_dict() for action in actions]
```

**AFTER** — add `from_yaml()` after `to_dicts()`:
```python
    @staticmethod
    def to_dicts(actions: List[FormAction]) -> List[Dict[str, Any]]:
        """Convert list of FormAction objects to list of dicts for Jinja2."""
        return [action.to_dict() for action in actions]

    @staticmethod
    def from_yaml(forms_path: Path, preset: str) -> Dict[str, Any]:
        """Load a button preset from forms.yaml.

        Looks up each action's button definition from the buttons: section,
        then merges any preset-level overrides (e.g. form_id).

        Returns dict with keys:
            container_class (str):  CSS class for the button container div
            actions         (list): Action dicts ready for _form_actions.html

        Each action dict has keys:
            label, type, class, id, title, form_id, data_attrs

        Args:
            forms_path: Path to forms.yaml
            preset:     Name of the preset to load (e.g. 'detail_panel')

        Raises:
            KeyError:          If preset or a referenced button is not found
            FileNotFoundError: If forms.yaml does not exist
        """
        import yaml

        with open(forms_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        button_defs = config.get("buttons", {})
        preset_cfg  = config.get("presets", {}).get(preset)

        if preset_cfg is None:
            raise KeyError(f"Preset '{preset}' not found in {forms_path}")

        container_class = preset_cfg.get("container_class", "form-actions")

        actions = []
        for action_cfg in preset_cfg.get("actions", []):
            btn_name = action_cfg.get("button")
            if btn_name not in button_defs:
                raise KeyError(
                    f"Button '{btn_name}' referenced in preset '{preset}' "
                    f"is not defined in buttons: section of {forms_path}"
                )

            # Start from the button definition, then apply preset overrides
            btn = dict(button_defs[btn_name])
            if "form_id" in action_cfg:
                btn["form_id"] = action_cfg["form_id"]

            actions.append({
                "label":      btn.get("label", ""),
                "type":       btn.get("type", "button"),
                "class":      btn.get("class", ""),
                "id":         btn.get("id", ""),
                "title":      btn.get("title", ""),
                "form_id":    btn.get("form_id", ""),
                "data_attrs": btn.get("data_attrs", {}),
            })

        return {
            "container_class": container_class,
            "actions":         actions,
        }
```

**Why:** `from_yaml()` resolves button names to their definitions, merges
preset-level overrides, and returns a flat list of dicts the template can
iterate directly. The route calls it once; the template just renders.

---

## Change 3: `src/curator/web/routes/crew.py`

Three additions — import, path constant, and data dict entry.

**BEFORE** — imports:
```python
from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.web.deps import get_config, get_db
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader
```

**AFTER**:
```python
from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.formkit import FormActions
from curator.web.deps import get_config, get_db
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader
```

**BEFORE** — path constants:
```python
_QUERIES_PATH = Path(__file__).parent.parent.parent / "data" / "queries.yaml"
_query_builder = QueryBuilder(_QUERIES_PATH)
_query_loader = QueryLoader(_query_builder)
```

**AFTER**:
```python
_QUERIES_PATH = Path(__file__).parent.parent.parent / "data" / "queries.yaml"
_FORMS_PATH   = Path(__file__).parent.parent.parent / "data" / "forms.yaml"
_query_builder = QueryBuilder(_QUERIES_PATH)
_query_loader  = QueryLoader(_query_builder)
```

**BEFORE** — `data` dict in `crew_dashboard()`:
```python
    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
        "contacts": contacts,
        "organizations": organizations,
        "tabs": role_tabs.get(
            role,
            [{"id": "projects", "label": "Projects", "template": "_tab_projects.html"}]
        ),
    }
```

**AFTER**:
```python
    detail_panel_actions = FormActions.from_yaml(_FORMS_PATH, "detail_panel")

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
        "contacts": contacts,
        "organizations": organizations,
        "tabs": role_tabs.get(
            role,
            [{"id": "projects", "label": "Projects", "template": "_tab_projects.html"}]
        ),
        "actions":         detail_panel_actions["actions"],
        "container_class": detail_panel_actions["container_class"],
    }
```

---

## Change 4: `src/curator/templates/partials/_detail_panel.html`

Remove the hardcoded `{% set actions %}` block from the sticky footer.

**BEFORE** — sticky footer at bottom of file:
```html
  <!-- Action buttons: sticky footer, outside the form, wired via form="detail-form" -->
  {% set actions = [
      {'label': 'Save',    'type': 'submit', 'class': 'btn-save',    'form_id': 'detail-form', 'title': 'Save (Alt+S)'},
      {'label': 'New',     'type': 'button', 'class': 'btn-new',     'data_attrs': {'action': 'new'},     'title': 'New (Alt+N)'},
      {'label': 'Discard', 'type': 'button', 'class': 'btn-discard', 'data_attrs': {'action': 'discard'}, 'title': 'Discard (Alt+X)'},
  ] %}
  {% set container_class = 'detail-panel-actions' %}
  {% include 'partials/_form_actions.html' %}

</div>
```

**AFTER**:
```html
  <!-- Action buttons: sticky footer — actions and container_class from route -->
  {% include 'partials/_form_actions.html' %}

</div>
```

---

## Change 5: `src/curator/templates/partials/_form_actions.html`

Add `| safe` to label output.

**BEFORE**:
```html
    >
      {{ action.label }}
    </button>
```

**AFTER**:
```html
    >
      {{ action.label | safe }}
    </button>
```

**Why:** Jinja2 auto-escapes by default. Without `| safe`, `<u>S</u>ave`
renders as literal text on screen. Safe to use here because labels come
from `forms.yaml`, a controlled config file, never from user input.

---

## Change 6: `static/css/components/buttons.css`

Move `.btn-save` from primary to secondary group.

**BEFORE**:
```css
.btn-primary,
.btn-save {
  background: var(--color-accent);
  color: #ffffff;
  border-color: var(--color-accent);
}

.btn-primary:hover,
.btn-save:hover {
  opacity: 0.88;
}

.btn-secondary,
.btn-new,
.btn-discard,
.btn-cancel {
  background: transparent;
  color: var(--color-text);
  border-color: var(--color-border);
}

.btn-secondary:hover,
.btn-new:hover,
.btn-discard:hover,
.btn-cancel:hover {
  background: var(--color-border);
}
```

**AFTER**:
```css
.btn-primary {
  background: var(--color-accent);
  color: #ffffff;
  border-color: var(--color-accent);
}

.btn-primary:hover {
  opacity: 0.88;
}

.btn-secondary,
.btn-save,
.btn-new,
.btn-discard,
.btn-cancel {
  background: transparent;
  color: var(--color-text);
  border-color: var(--color-border);
}

.btn-secondary:hover,
.btn-save:hover,
.btn-new:hover,
.btn-discard:hover,
.btn-cancel:hover {
  background: var(--color-border);
}
```

---

## Summary

| File | Action |
|------|--------|
| `src/curator/data/forms.yaml` | Create new |
| `src/curator/formkit.py` | Add `Path` import; add `from_yaml()` |
| `src/curator/web/routes/crew.py` | Add `FormActions` import, `_FORMS_PATH`, load preset, pass to template |
| `src/curator/templates/partials/_detail_panel.html` | Remove hardcoded `{% set actions %}` block |
| `src/curator/templates/partials/_form_actions.html` | Add `| safe` to label |
| `static/css/components/buttons.css` | Move `.btn-save` to secondary group |

---

## Verification

1. Start server — no import errors.
2. Open Captain view — panel hidden on load.
3. Click ⋯ on a row — panel opens, three buttons in footer.
4. All three buttons look identical (outlined).
5. Button labels show underlined accelerator letters: Save, New, Discard.
6. Alt+S saves and closes. Alt+N saves and clears. Alt+X / Escape discards.
7. Edit a label in `forms.yaml`, restart server — change appears without
   touching any Python or HTML.
