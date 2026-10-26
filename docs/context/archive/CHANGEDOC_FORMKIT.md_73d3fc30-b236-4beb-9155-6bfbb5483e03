# Formkit Implementation — Changedoc

**Date:** 2026-06-28  
**Status:** Ready to apply  
**Scope:** Wire formkit into detail panel; fix detail-panel.css conflicts

---

## Overview

Four changes, no new files, no route changes, no base.html changes.

- `formkit.py` — already exists and is correct. No changes.
- `_form_actions.html` — already exists. Fix the comment block only (remove
  invalid `{% include ... with %}` example that could confuse future editors).
- `_detail_panel.html` — replace with the FIXED version + wire in `_form_actions.html`.
- `detail-panel.css` — remove duplicate button styles and fade transitions
  that conflict with `buttons.css` and the display:none rule.

---

## File locations in the repo

```
src/curator/formkit.py                              ← no change
src/curator/templates/partials/_form_actions.html   ← fix comment only
src/curator/templates/partials/_detail_panel.html   ← replace entirely
static/css/components/detail-panel.css              ← remove two sections
```

---

## Change 1: `_form_actions.html` — fix comment block

The partial body is correct. The docstring example uses invalid Jinja2 syntax
(`{% include ... with key=value %}`) which would mislead future editors.
Replace only the comment block.

**BEFORE** (lines 1–47, the entire `{# ... #}` comment):
```
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
  
  Example usage (from Python):
    
    from formkit import FormActions
    
    actions = FormActions.detail_panel_actions(form_id='detail-form')
    actions_dicts = FormActions.to_dicts(actions)
    
    # In template:
    {% include '_form_actions.html' with
        actions=actions_dicts,
        container_class='detail-panel-actions'
    %}
  
  Example usage (from template):
    
    {% include '_form_actions.html' with
        actions=[
            {'label': 'Save', 'type': 'submit', 'class': 'btn-save', 'form_id': 'form'},
            {'label': 'Cancel', 'type': 'button', 'class': 'btn-cancel'},
        ],
        container_class='form-actions'
    %}
#}
```

**AFTER** (replacement comment block):
```
{#
  _form_actions.html

  Reusable form action button bar. Can be used in any form context:
  detail panels, add/edit forms, dialogs, etc.

  Parameters:
    - actions (list): List of action dicts. Build with formkit.FormActions:

        from curator.formkit import FormActions
        actions = FormActions.to_dicts(FormActions.detail_panel_actions())

      Each dict has keys:
        label      (str)  — Button text
        type       (str)  — HTML button type: "submit", "button", "reset"
        class      (str)  — CSS class(es), e.g. "btn-save"
        id         (str, optional) — HTML id attribute
        title      (str, optional) — Tooltip text
        form_id    (str, optional) — Associates button with a form by id
        data_attrs (dict, optional) — data-* attributes, e.g. {"action": "new"}

    - container_class (str, optional): Extra CSS class on the container div
    - container_id    (str, optional): HTML id on the container div

  Usage in a template — set variables first, then include:

    {% set actions = [
        {'label': 'Save',    'type': 'submit', 'class': 'btn-save',    'form_id': 'detail-form', 'title': 'Save (Alt+S)'},
        {'label': 'New',     'type': 'button', 'class': 'btn-new',     'data_attrs': {'action': 'new'},     'title': 'New (Alt+N)'},
        {'label': 'Discard', 'type': 'button', 'class': 'btn-discard', 'data_attrs': {'action': 'discard'}, 'title': 'Discard (Alt+X)'},
    ] %}
    {% set container_class = 'detail-panel-actions' %}
    {% include 'partials/_form_actions.html' %}

  NOTE: Jinja2 does not support {% include ... with key=value %} syntax.
  Always set variables before the include.
#}
```

**Why:** The old comment showed `{% include ... with %}` which is not valid Jinja2
and would cause a TemplateSyntaxError if copied into a calling template.

---

## Change 2: `_detail_panel.html` — replace entirely

Use `_detail_panel_FIXED.html` as the base (all child tabs are "coming soon"
placeholders, buttons are in a sticky footer outside the form). Wire the
sticky footer to use `_form_actions.html` instead of hardcoded buttons.

**BEFORE** — the entire current file (`src/curator/templates/partials/_detail_panel.html`):

```html
{#
  _detail_panel.html
  
  Detail panel — displays a record's details in a tabbed interface.
  Replaces the hero image when a user clicks ⋯ on a datasheet row.
  
  Parameters:
    - entity (str): Entity type ("projects", "contacts", "organizations")
    - record_id (int): ID of the record being displayed
    - record (dict): Full record data for form fields
    - project_types (list, optional): Type lookup for projects
    - project_statuses (list, optional): Status lookup for projects
    - contact_map (dict, optional): Contact ID → name mapping for dropdowns
    - status_map (dict, optional): Status ID → name mapping for dropdowns
  
  Example usage (from captain.html):
    
    {% include '_detail_panel.html' with
        entity='projects',
        record_id=project.id,
        record=project,
        project_types=project_types,
        project_statuses=project_statuses
    %}
#}

<div class="detail-panel" data-entity="{{ entity }}" data-id="{{ record_id }}">
  
  <!-- Tab navigation -->
  <div class="detail-tabs">
    <button class="detail-tab-button active" data-tab="details">Details</button>
    
    {% if entity == "projects" %}
      <button class="detail-tab-button" data-tab="tasks">Tasks</button>
      <button class="detail-tab-button" data-tab="links">Links</button>
      <button class="detail-tab-button" data-tab="contacts">Contacts</button>
    {% elif entity == "contacts" %}
      <button class="detail-tab-button" data-tab="emails">Emails</button>
      <button class="detail-tab-button" data-tab="phones">Phones</button>
      <button class="detail-tab-button" data-tab="urls">URLs</button>
      <button class="detail-tab-button" data-tab="organizations">Organizations</button>
    {% elif entity == "organizations" %}
      <button class="detail-tab-button" data-tab="contacts">Contacts</button>
    {% endif %}
    
    <button class="detail-close-button" aria-label="Close detail panel">×</button>
  </div>

  <!-- Tab content container -->
  <div class="detail-tab-panels">
    
    <!-- ===== DETAILS TAB (always first) ===== -->
    <div class="detail-tab-panel active" data-tab="details">
      <form class="detail-form" data-entity="{{ entity }}" data-id="{{ record_id }}">
        
        {% if entity == "projects" %}
          <!-- Project details -->
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>
          
          <div class="form-group">
            <label for="detail-type">Type</label>
            <select id="detail-type" name="type_id">
              <option value="">—</option>
              {% for type in project_types %}
                <option value="{{ type.id }}" {% if record.type_id == type.id %}selected{% endif %}>
                  {{ type.name }}
                </option>
              {% endfor %}
            </select>
          </div>
          
          <div class="form-group">
            <label for="detail-status">Status</label>
            <select id="detail-status" name="status_id">
              <option value="">—</option>
              {% for status in project_statuses %}
                <option value="{{ status.id }}" {% if record.status_id == status.id %}selected{% endif %}>
                  {{ status.name }}
                </option>
              {% endfor %}
            </select>
          </div>
          
          <div class="form-group">
            <label for="detail-description">Description</label>
            <textarea id="detail-description" name="description">{{ record.description or '' }}</textarea>
          </div>

        {% elif entity == "contacts" %}
          <!-- Contact details -->
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>
          
          <div class="form-group">
            <label for="detail-title">Title</label>
            <input type="text" id="detail-title" name="title" value="{{ record.title or '' }}" />
          </div>

        {% elif entity == "organizations" %}
          <!-- Organization details -->
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>
        {% endif %}
        
        <div class="form-actions">
          <button type="submit" class="btn-save">Save</button>
          <button type="reset" class="btn-discard">Discard</button>
        </div>
      </form>
    </div>

    <!-- ===== PROJECT CHILD DATASHEETS ===== -->
    {% if entity == "projects" %}
      
      <!-- Tasks Tab -->
      <div class="detail-tab-panel" data-tab="tasks">
        {% include 'partials/_datasheet_with_header.html' with
            add_button_label='+ Task',
            ...
        %}
      </div>
      ... (all remaining child tabs with invalid include syntax)

    {% endif %}

  </div>
</div>
```

**AFTER** — complete replacement file:

```html
{#
  _detail_panel.html

  Detail panel — displays a record's details in a tabbed interface.
  Replaces the hero image when a user clicks ⋯ on a datasheet row.

  Parameters:
    - entity          (str)  — "projects", "contacts", or "organizations"
    - record_id       (int)  — ID of the record being displayed
    - record          (dict) — Full record data for form fields
    - project_types   (list, optional) — Type lookup for projects
    - project_statuses(list, optional) — Status lookup for projects

  Caller must set entity, record_id, and record before including.
  Child datasheets (Tasks, Emails, etc.) are deferred — coming soon.
#}

<div class="detail-panel" data-entity="{{ entity }}" data-id="{{ record_id }}">

  <!-- Tab navigation -->
  <div class="detail-tabs">
    <button class="detail-tab-button active" data-tab="details">Details</button>

    {% if entity == "projects" %}
      <button class="detail-tab-button" data-tab="tasks">Tasks</button>
      <button class="detail-tab-button" data-tab="links">Links</button>
      <button class="detail-tab-button" data-tab="contacts">Contacts</button>
    {% elif entity == "contacts" %}
      <button class="detail-tab-button" data-tab="emails">Emails</button>
      <button class="detail-tab-button" data-tab="phones">Phones</button>
      <button class="detail-tab-button" data-tab="urls">URLs</button>
      <button class="detail-tab-button" data-tab="organizations">Organizations</button>
    {% elif entity == "organizations" %}
      <button class="detail-tab-button" data-tab="contacts">Contacts</button>
    {% endif %}

    <button class="detail-close-button" aria-label="Close detail panel">×</button>
  </div>

  <!-- Tab content container -->
  <div class="detail-tab-panels">

    <!-- ===== DETAILS TAB (always first) ===== -->
    <div class="detail-tab-panel active" data-tab="details">
      <form id="detail-form" class="detail-form" data-entity="{{ entity }}" data-id="{{ record_id }}">

        {% if entity == "projects" %}
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>

          <div class="form-group">
            <label for="detail-type">Type</label>
            <select id="detail-type" name="type_id">
              <option value="">—</option>
              {% for type in project_types %}
                <option value="{{ type.id }}" {% if record.type_id == type.id %}selected{% endif %}>
                  {{ type.name }}
                </option>
              {% endfor %}
            </select>
          </div>

          <div class="form-group">
            <label for="detail-status">Status</label>
            <select id="detail-status" name="status_id">
              <option value="">—</option>
              {% for status in project_statuses %}
                <option value="{{ status.id }}" {% if record.status_id == status.id %}selected{% endif %}>
                  {{ status.name }}
                </option>
              {% endfor %}
            </select>
          </div>

          <div class="form-group">
            <label for="detail-description">Description</label>
            <textarea id="detail-description" name="description">{{ record.description or '' }}</textarea>
          </div>

        {% elif entity == "contacts" %}
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>

          <div class="form-group">
            <label for="detail-title">Title</label>
            <input type="text" id="detail-title" name="title" value="{{ record.title or '' }}" />
          </div>

        {% elif entity == "organizations" %}
          <div class="form-group">
            <label for="detail-name">Name</label>
            <input type="text" id="detail-name" name="name" value="{{ record.name or '' }}" />
          </div>
        {% endif %}

      </form>
    </div>

    <!-- ===== CHILD TABS (deferred) ===== -->
    {% if entity == "projects" %}
      <div class="detail-tab-panel" data-tab="tasks">
        <p class="tab-placeholder">Tasks — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="links">
        <p class="tab-placeholder">Links — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="contacts">
        <p class="tab-placeholder">Contacts — coming soon</p>
      </div>

    {% elif entity == "contacts" %}
      <div class="detail-tab-panel" data-tab="emails">
        <p class="tab-placeholder">Emails — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="phones">
        <p class="tab-placeholder">Phones — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="urls">
        <p class="tab-placeholder">URLs — coming soon</p>
      </div>
      <div class="detail-tab-panel" data-tab="organizations">
        <p class="tab-placeholder">Organizations — coming soon</p>
      </div>

    {% elif entity == "organizations" %}
      <div class="detail-tab-panel" data-tab="contacts">
        <p class="tab-placeholder">Contacts — coming soon</p>
      </div>
    {% endif %}

  </div>

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

**Why:**
- Removes all `{% include ... with %}` calls on child tabs (invalid Jinja2 syntax).
- Moves buttons out of the form into a sticky footer div, wired via `form="detail-form"`.
- Wires the footer through `_form_actions.html` so formkit is live in the codebase.
- Adds `id="detail-form"` to the `<form>` tag (required for the `form=` attribute on the Save button to work).
- Uses `{% set %}` before `{% include %}` — the correct Jinja2 pattern.

---

## Change 3: `detail-panel.css` — remove duplicate button styles

`buttons.css` is the sole authority for button styles. `detail-panel.css`
has conflicting definitions that must be removed.

**BEFORE** (lines 148–181):
```css
.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-save,
.btn-discard {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-save {
  background: var(--color-button-primary-bg);
  color: var(--color-button-primary-text);
}

.btn-save:hover {
  opacity: 0.9;
}

.btn-discard {
  background: var(--color-button-secondary-bg);
  color: var(--color-button-secondary-text);
}

.btn-discard:hover {
  opacity: 0.8;
}
```

**AFTER** — replace with `.detail-panel-actions` and `.tab-placeholder` only:
```css
/* Action button sticky footer */
.detail-panel-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  flex-shrink: 0;
}

/* Placeholder text for deferred child tabs */
.tab-placeholder {
  padding: 1rem;
  color: var(--color-text-light);
  font-size: 0.875rem;
}
```

**Why:** `.btn-save` and `.btn-discard` are defined in `buttons.css`. Having
them here too causes specificity conflicts. `.form-actions` was the old
in-form button wrapper — it's gone. `.detail-panel-actions` is the new
sticky footer — it needs a rule. `.tab-placeholder` replaces the inline
`style=` on placeholder paragraphs.

---

## Change 4: `detail-panel.css` — remove fade transitions

Project rule: visibility toggles use `display:none` ↔ `display:flex/block`
only. No opacity, no visibility, no transitions on show/hide.

**BEFORE** (lines 188–207):
```css
/* Hero ↔ Panel transitions */
.crew-hero {
  transition: opacity 0.2s ease, visibility 0.2s ease;
}

.crew-hero.hidden {
  opacity: 0;
  visibility: hidden;
}

.detail-panel {
  transition: opacity 0.2s ease, visibility 0.2s ease;
  opacity: 0;
  visibility: hidden;
}

.detail-panel.active {
  opacity: 1;
  visibility: visible;
}
```

**AFTER** — delete these rules entirely.

The existing rules earlier in the file already handle show/hide correctly:
```css
/* (line 10) */
.detail-panel        { display: none; ... }
.detail-panel.active { display: flex; }
```
The fade block contradicts and overrides those. Removing it restores
correct display:none behavior.

**Why:** The fade uses `opacity` + `visibility`, which leaves the element
in the layout and intercepts clicks even when "hidden". `display:none`
removes it entirely. These two approaches conflict; the fade block wins
due to cascade order and breaks the hide behavior.

---

## Summary — files to change

| File | Action |
|------|--------|
| `src/curator/formkit.py` | No change |
| `src/curator/templates/partials/_form_actions.html` | Replace comment block only (Change 1) |
| `src/curator/templates/partials/_detail_panel.html` | Replace entirely (Change 2) |
| `static/css/components/detail-panel.css` | Remove button styles + fade block; add `.detail-panel-actions` + `.tab-placeholder` (Changes 3 & 4) |

No changes to: `crew.py`, `base.html`, `buttons.css`, or any other file.

---

## Verification

After applying:
1. Start the server. No startup errors = template syntax is clean.
2. Open Captain view, click ⋯ on a project row — detail panel opens.
3. Verify three buttons render (Save, New, Discard) in sticky footer below tabs.
4. Click Save — panel closes, grid refreshes.
5. Click New — form clears, Name field focused.
6. Click Discard or × — panel closes, no save.
7. Click Tasks/Links/Contacts tabs — "coming soon" placeholder appears.
8. Toggle dark theme — buttons style correctly (from buttons.css variables).
