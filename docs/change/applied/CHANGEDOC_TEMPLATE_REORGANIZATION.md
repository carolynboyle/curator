# Changedoc: Reorganize Templates — Move Partials to Subdirectory

**Date:** 2026-06-27  
**Task:** Move all `_*.html` partial templates into `templates/partials/` subdirectory and update include paths

---

## Files to Move

Move these files from `templates/` to `templates/partials/`:

```
_datasheet.html
_datasheet_with_header.html
_detail_panel.html
_crew_header.html
_crew_row_display.html
_crew_row_edit.html
_crew_row_add.html
_crew_rows.html
_projects_table.html
(any other files starting with _)
```

**After:** All partials live in `templates/partials/`

---

## Files That Reference Partials

Update include paths in these files:

### 1. `templates/partials/_datasheet_with_header.html`

**BEFORE:**
```html
{% include '_datasheet.html' with
    container_id=container_id,
    ...
%}
```

**AFTER:**
```html
{% include 'partials/_datasheet.html' with
    container_id=container_id,
    ...
%}
```

---

### 2. `templates/partials/_detail_panel.html`

**BEFORE (appears multiple times in the file):**
```html
{% include '_datasheet_with_header.html' with
    add_button_label='+ Task',
    ...
%}
```

**AFTER:**
```html
{% include 'partials/_datasheet_with_header.html' with
    add_button_label='+ Task',
    ...
%}
```

This appears in:
- Projects → Tasks tab
- Projects → Links tab (deferred)
- Projects → Contacts tab (deferred)
- Contacts → Emails tab
- Contacts → Phones tab
- Contacts → URLs tab
- Contacts → Organizations tab
- Organizations → Contacts tab

Replace all instances.

---

### 3. Any Crew Pages That Include Partials

If `captain.html` or `crew.html` include partials, update those too:

**BEFORE:**
```html
{% include '_crew_header.html' %}
{% include '_projects_table.html' %}
```

**AFTER:**
```html
{% include 'partials/_crew_header.html' %}
{% include 'partials/_projects_table.html' %}
```

---

## Directory Structure After

```
src/templates/
├── base.html
├── captain.html
├── crew.html
├── landing.html
├── index.html
├── partials/
│   ├── _datasheet.html
│   ├── _datasheet_with_header.html
│   ├── _detail_panel.html
│   ├── _crew_header.html
│   ├── _crew_row_display.html
│   ├── _crew_row_edit.html
│   ├── _crew_row_add.html
│   ├── _crew_rows.html
│   ├── _projects_table.html
│   └── (other _ prefixed files)
├── projects/
├── contacts/
└── organizations/
```

---

## Why This Change

- **Cleaner root:** Full page templates in `templates/`, reusable components in `templates/partials/`
- **Obvious intent:** Anything with `_` prefix is a component, not a full page
- **Scalable:** As you add entity-specific pages (projects/detail.html, contacts/list.html, etc.), the structure is ready
- **Same behavior:** Jinja2 resolves `include 'partials/_x.html'` the same way it does `include '_x.html'`

---

## How to Do It

1. Create `templates/partials/` directory if it doesn't exist
2. Move all `_*.html` files into `partials/`
3. Search-replace in the 2-3 files that include them:
   - Find: `include '_`
   - Replace: `include 'partials/_`
4. Delete empty top-level directories (projects/, contacts/, organizations/) if you want, or leave them for future use

---

## Testing

After moving:
1. Run `python -m curator` or start the dev server
2. Load any crew page (captain, scribe, mechanic, envoy)
3. Verify the page loads and the datasheet renders
4. No 404 errors about missing templates

If there's a template error, it will tell you the path — just make sure the `include` path matches the new location.
