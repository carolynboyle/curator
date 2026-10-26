# Changedoc: detail-panel.js — populateForm() missing title field

**File:** `static/js/detail-panel.js`
**Type:** Bug fix
**Reason:** `populateForm()` only maps `name`/`type_id`/`status_id`/
`description` from the fetched record onto the form. Contacts have a
`title` field (`_detail_panel.html`'s contacts branch: `<input name="title">`),
but nothing populates it. Effect: double-clicking any contact with a
title set (e.g. Andrea Flores) opens the detail panel with Title showing
blank, not what's actually stored. If Save is then clicked without
noticing, the blank overwrites the real value in the database — silent
data loss, not just a display glitch.

Found while verifying `_detail_panel.html`'s field names against the new
`/crew/contacts/*` routes (`CHANGEDOC_CREW_PY_CONTACTS_ORGANIZATIONS_ROUTES.md`)
— field names matched what the routes expect, but this populate gap is
independent of that work and would have surfaced the first time anyone
edited a contact with a title.

---

## BEFORE

```javascript
function populateForm(record) {
  const form = getForm();
  if (!form) return;
  form.dataset.id = record.id ?? '';

  const nameField   = form.querySelector('[name="name"]');
  const typeField   = form.querySelector('[name="type_id"]');
  const statusField = form.querySelector('[name="status_id"]');
  const descField   = form.querySelector('[name="description"]');

  if (nameField)   nameField.value   = record.name        ?? '';
  if (typeField)   typeField.value   = record.type_id     ?? '';
  if (statusField) statusField.value = record.status_id   ?? '';
  if (descField)   descField.value   = record.description ?? '';
}
```

## AFTER

```javascript
function populateForm(record) {
  const form = getForm();
  if (!form) return;
  form.dataset.id = record.id ?? '';

  const nameField   = form.querySelector('[name="name"]');
  const typeField   = form.querySelector('[name="type_id"]');
  const statusField = form.querySelector('[name="status_id"]');
  const descField   = form.querySelector('[name="description"]');
  const titleField  = form.querySelector('[name="title"]');

  if (nameField)   nameField.value   = record.name        ?? '';
  if (typeField)   typeField.value   = record.type_id     ?? '';
  if (statusField) statusField.value = record.status_id   ?? '';
  if (descField)   descField.value   = record.description ?? '';
  if (titleField)  titleField.value  = record.title       ?? '';
}
```

---

## Notes
- `form.querySelector('[name="..."]')` returning `null` on entities that
  don't have that field is already handled by the `if (fieldRef)` guards
  — this follows the exact same pattern already used for `type_id`/
  `status_id`/`description` not existing on the contacts/organizations
  forms. No entity-specific branching needed in the JS.
- `clearForm()` (used when opening a blank new-record form) already does
  a blanket `form.querySelectorAll('input, textarea').forEach(el => el.value = '')`,
  so the New-record path was never affected by this bug — only editing an
  *existing* record with a title hit it.
- Worth a quick manual check after applying: open an existing contact
  that has a title set, confirm it now shows, Save, reload, confirm it's
  still there (i.e. didn't get blanked by an earlier accidental save
  before this fix was applied).
