# Formkit Component Architecture — Form Actions Refactor

**Date:** 2026-06-28  
**Status:** Ready to apply  
**Scope:** Extract reusable form action button bar component  

---

## Overview

The detail panel's action buttons (Save, New, Discard) are now a **reusable formkit component** that can be used in any form context: add/edit forms, dialogs, confirmation prompts, etc.

This refactor follows the **Curator philosophy**: declarative configuration over code duplication, single source of truth for UI patterns.

---

## Architecture

### Files Added

1. **`src/curator/formkit.py`** — Python builder module
   - `FormAction` class: represents a single button
   - `FormActions` class: factory methods for common buttons + presets
   - Methods: `save()`, `new()`, `discard()`, `cancel()`, `delete()`, `custom()`
   - Presets: `detail_panel_actions()`, `crud_create_actions()`, `crud_edit_actions()`

2. **`src/curator/templates/partials/_form_actions.html`** — Jinja2 template
   - Accepts list of action dicts
   - Renders a button bar with flexible styling
   - Handles `form=` attributes, tooltips, data attributes

3. **`config/forms.yaml`** — Action specifications
   - Presets for common form types (detail_panel, create, edit, dialog)
   - YAML-driven for easy configuration without code changes
   - Each action spec includes: label, type, class, title, data attributes

4. **`static/css/components/form-actions.css`** — Component styles
   - Generic `.form-actions` container styles
   - Variants: `.detail-panel-actions`, `.dialog-actions`, `.inline`, `.stacked`
   - Delegates button styling to `buttons.css`

### Files Modified

1. **`src/curator/templates/partials/_detail_panel.html`**
   - Replaced hardcoded button markup with `{% include '_form_actions.html' %}`
   - Passes `form_actions` variable (built in Python route)

2. **`static/css/components/detail-panel.css`**
   - Removed `.detail-panel-actions` button styling (moved to `form-actions.css`)
   - Removed `.btn-save`, `.btn-new`, `.btn-discard` scoped styles
   - Kept form layout and field styling

---

## Usage

### Python (in routes)

```python
from curator.formkit import FormActions

# Use a preset
actions = FormActions.detail_panel_actions(form_id='detail-form')
actions_dicts = FormActions.to_dicts(actions)

# Pass to template
return templates.TemplateResponse(
    "captain.html",
    {
        "form_actions": actions_dicts,
        ...
    }
)

# Or customize with YAML + custom logic
from curator.config import load_yaml

forms_config = load_yaml('config/forms.yaml')
actions = [
    # ... custom actions
]
actions_dicts = FormActions.to_dicts(actions)
```

### Jinja2 (in template)

```jinja2
{% include 'partials/_form_actions.html' with
    actions=form_actions,
    container_class='detail-panel-actions'
%}

<!-- Or inline with dicts: -->
{% include 'partials/_form_actions.html' with
    actions=[
        {'label': 'Save', 'type': 'submit', 'class': 'btn-save'},
        {'label': 'Cancel', 'type': 'button', 'class': 'btn-cancel'},
    ]
%}
```

### YAML (config-driven)

```yaml
# config/forms.yaml
detail_panel:
  container_class: detail-panel-actions
  actions:
    - label: "Save"
      type: "submit"
      class: "btn-save"
      form_id: "detail-form"
      title: "Save (Alt+S)"
    
    - label: "New"
      type: "button"
      class: "btn-new"
      title: "New (Alt+N)"
      data_attrs:
        action: "new"
```

---

## Implementation in Detail Panel

### Change 1: `_detail_panel.html`

**BEFORE (lines 240-247):**
```html
  <!-- Action buttons: sticky footer at bottom of panel -->
  <!-- Only visible on Details tab (where the form is) -->
  <div class="detail-panel-actions">
    <button type="submit" form="detail-form" class="btn-save" title="Save (Alt+S)">Save</button>
    <button type="button" class="btn-new" title="New (Alt+N)">New</button>
    <button type="button" class="btn-discard" title="Discard (Alt+X)">Discard (Alt+X)</button>
  </div>
```

**AFTER (lines 240-244):**
```html
  <!-- Action buttons: sticky footer at bottom of panel -->
  <!-- Rendered by reusable _form_actions.html partial -->
  {% include 'partials/_form_actions.html' with
      actions=form_actions,
      container_class='detail-panel-actions'
  %}
```

**Explanation:**
- Template no longer knows about button structure
- Passes `form_actions` (built in Python) to reusable partial
- Same visual result, but now reusable elsewhere

---

### Change 2: `_form_actions.html` (NEW)

**Complete file:**
```html
{#
  _form_actions.html
  
  Reusable form action button bar. Can be used in any form context:
  detail panels, add/edit forms, dialogs, etc.
  
  This partial renders nothing but the button container and buttons.
  All styling, keyboard handling, and state management is external.
  
  Parameters:
    - actions (list): List of action dicts with keys:
        - label (str): Button text
        - type (str): HTML button type ("submit", "button", "reset")
        - class (str): CSS classes (e.g., "btn-save btn-primary")
        - id (str, optional): HTML id attribute
        - title (str, optional): Tooltip text
        - form_id (str, optional): Form ID for submit buttons (form= attribute)
        - data_attrs (dict, optional): Additional data-* attributes
    
    - container_class (str, optional): CSS class for the container div
      Default: "form-actions"
    
    - container_id (str, optional): HTML id for the container div
#}

<div class="form-actions {% if container_class %}{{ container_class }}{% endif %}"
     {% if container_id %}id="{{ container_id }}"{% endif %}>
  
  {% for action in actions %}
    <button
        type="{{ action.type }}"
        class="form-action-button {{ action.class }}"
        {% if action.id %}id="{{ action.id }}"{% endif %}
        {% if action.title %}title="{{ action.title }}"{% endif %}
        {% if action.form_id %}form="{{ action.form_id }}"{% endif %}
        {% if action.data_attrs %}
          {% for key, value in action.data_attrs.items() %}
            data-{{ key }}="{{ value }}"
          {% endfor %}
        {% endif %}
    >
      {{ action.label }}
    </button>
  {% endfor %}

</div>
```

**Key features:**
- Renders a `<div class="form-actions">` container
- Loops through actions list and renders each as a button
- Supports all HTML button attributes
- Data attributes can be set via dict for JS hooks
- No hardcoded buttons or styling (delegated to caller + CSS)

---

### Change 3: `detail-panel.css`

**BEFORE (lines 148-197):**
```css
/* Action buttons: sticky footer bar */
.detail-panel-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  flex-shrink: 0;
}

.detail-panel-actions .btn-save,
.detail-panel-actions .btn-new,
.detail-panel-actions .btn-discard {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.detail-panel-actions .btn-save {
  background: var(--color-button-primary-bg);
  color: var(--color-button-primary-text);
}

.detail-panel-actions .btn-save:hover {
  opacity: 0.9;
}

.detail-panel-actions .btn-new {
  background: var(--color-button-secondary-bg);
  color: var(--color-button-secondary-text);
}

.detail-panel-actions .btn-new:hover {
  opacity: 0.8;
}

.detail-panel-actions .btn-discard {
  background: var(--color-button-secondary-bg);
  color: var(--color-button-secondary-text);
}

.detail-panel-actions .btn-discard:hover {
  opacity: 0.8;
}
```

**AFTER (lines 148-149):**
```css
/* Action buttons: rendered by reusable _form_actions.html partial
   Styling handled by form-actions.css and buttons.css */
```

**Explanation:**
- All button styling moved to `form-actions.css` (component-level)
- Button appearance (colors, hover) moved to `buttons.css` (design system)
- Detail panel CSS now only handles form layout, not button presentation
- Better separation of concerns

---

### Change 4: `form-actions.css` (NEW)

**Complete file:**
```css
/* =============================================================================
   Form Actions Component
   
   Reusable button bar for form actions. Can be used in any context:
   detail panels, add/edit forms, dialogs, etc.
   
   All buttons inherit from the button system (buttons.css). This file
   only handles the container layout and spacing.
   ============================================================================= */

/* Base form-actions container */
.form-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  flex-shrink: 0;
}

/* Individual action button (inherits from button.css) */
.form-action-button {
  /* All styling delegated to button classes (.btn-save, .btn-cancel, etc.)
     defined in buttons.css */
}

/* Variant: sticky footer (used in detail panels) */
.form-actions.detail-panel-actions {
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

/* Variant: dialog actions (centered, often at bottom of modal) */
.form-actions.dialog-actions {
  justify-content: flex-end;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  gap: 1rem;
}

/* Variant: inline actions (buttons on same line as content) */
.form-actions.inline {
  margin-top: 1rem;
  border: none;
  background: transparent;
  padding: 0;
}

/* Variant: stacked actions (buttons in column) */
.form-actions.stacked {
  flex-direction: column;
}

.form-actions.stacked .form-action-button {
  width: 100%;
  text-align: center;
}
```

**Design:**
- Generic `.form-actions` base styles (flex container, gap, padding)
- Variants for different contexts (detail panel, dialog, inline, stacked)
- All button styling delegated to `buttons.css` via class names
- No component-specific colors or sizing

---

### Change 5: `formkit.py` (NEW)

**Complete file (see above):**

Key classes:
- `FormAction` — represents a single button
- `FormActions` — factory with static methods

Factory methods:
- `save(form_id, label)` — Submit button
- `new(label)` — Secondary button with `data-action="new"`
- `discard(label)` — Secondary button with `data-action="discard"`
- `cancel(label)` — Alias for discard
- `delete(label, confirm)` — Danger button with optional confirmation
- `custom(label, button_type, css_class, **kwargs)` — Any custom button

Presets:
- `detail_panel_actions(form_id)` — [Save, New, Discard]
- `crud_create_actions(form_id)` — [Save, Cancel]
- `crud_edit_actions(form_id)` — [Save, Delete, Cancel]

Helper:
- `to_dicts(actions)` — Convert FormAction list to dicts for Jinja2

**Usage:**
```python
# Use preset
actions = FormActions.detail_panel_actions()
actions_dicts = FormActions.to_dicts(actions)

# Mix preset + custom
actions = [
    FormActions.save(form_id='form'),
    FormActions.custom('Archive', css_class='btn-secondary', data_attrs={'action': 'archive'}),
    FormActions.cancel(),
]
```

---

### Change 6: `forms.yaml` (NEW)

**Structure:**
```yaml
<preset_name>:
  container_class: <optional CSS class for container>
  actions:
    - label: <button text>
      type: <submit|button|reset>
      class: <CSS classes>
      form_id: <optional form ID>
      title: <optional tooltip>
      data_attrs: <optional dict of data-* attributes>
```

**Presets included:**
- `detail_panel` — Save, New, Discard (for detail panels)
- `create` — Save, Cancel (for add forms)
- `edit` — Save, Delete, Cancel (for edit forms)
- `dialog` — OK, Cancel (for modal dialogs)
- `close` — Close (for read-only displays)

**Future presets:**
- `publish` — Save & Publish, Save Draft, Discard
- `bulk_actions` — Apply, Select All, Deselect All
- etc.

---

## How to Use in Routes

### Example: Captain projects view

**In `crew.py`:**
```python
from curator.formkit import FormActions

@app.get("/crew/projects")
async def captain_projects_view(request: Request, ...):
    # Build action specs
    form_actions_dicts = FormActions.to_dicts(
        FormActions.detail_panel_actions(form_id='detail-form')
    )
    
    return templates.TemplateResponse(
        "crew.html",
        {
            "role": "captain",
            "form_actions": form_actions_dicts,
            "projects": projects,
            ...
        }
    )
```

**In template (captain.html):**
```html
{% include '_detail_panel.html' with
    entity='projects',
    record=project,
    form_actions=form_actions
%}
```

---

## Migration Checklist

- [ ] Add `src/curator/formkit.py`
- [ ] Add `src/curator/templates/partials/_form_actions.html`
- [ ] Add `config/forms.yaml`
- [ ] Add `static/css/components/form-actions.css`
- [ ] Link `form-actions.css` in `base.html` (after `buttons.css`)
- [ ] Update `_detail_panel.html` to use `_form_actions.html`
- [ ] Update `detail-panel.css` (remove button styles)
- [ ] Update crew.py route(s) to pass `form_actions`:
  ```python
  form_actions = FormActions.to_dicts(FormActions.detail_panel_actions(form_id='detail-form'))
  ```
- [ ] Test detail panel (Save, New, Discard all work)
- [ ] Test with keyboard shortcuts (Alt+S, Alt+N, Alt+X)
- [ ] Clear browser cache

---

## Future Extensions

### Phase 2: Config-driven routes
Load action specs from `forms.yaml` directly in routes:
```python
from curator.config import load_yaml

forms_config = load_yaml('config/forms.yaml')
form_actions = FormActions.from_yaml(forms_config['detail_panel'])
```

### Phase 3: Formkit in dev-utils
Move `formkit.py` to dev-utils package as a shared library:
- `dev-utils/src/formkit/__init__.py`
- Used by curator, Qt app, and other projects

### Phase 4: Advanced features
- Conditional button display (e.g., hide Delete if user lacks permission)
- Button state management (disabled, loading, etc.)
- Keyboard shortcut help modal
- Analytics/tracking hooks

---

## CSS Architecture After This Change

```
buttons.css           — Button design system (.btn-save, .btn-cancel, etc.)
  └─ Applied to buttons in form-actions.css

form-actions.css      — Action button bar component
  ├─ .form-actions (base)
  ├─ .form-actions.detail-panel-actions
  ├─ .form-actions.dialog-actions
  ├─ .form-actions.inline
  └─ .form-actions.stacked

detail-panel.css      — Detail panel layout
  ├─ .detail-panel (flex layout)
  ├─ .detail-tabs (tab navigation)
  ├─ .detail-tab-panels (scrollable content)
  ├─ .detail-form (form fields)
  └─ (no button styling)
```

---

## Benefits

1. **Reusability**: Button bars are no longer locked to detail panels
2. **Maintainability**: Button specs live in one place (Python or YAML)
3. **Extensibility**: New button types don't require template changes
4. **Flexibility**: Data attributes allow JS hooks without hardcoding
5. **Configuration**: YAML-driven means non-programmers can add new presets
6. **Consistency**: All forms use the same patterns and classes
