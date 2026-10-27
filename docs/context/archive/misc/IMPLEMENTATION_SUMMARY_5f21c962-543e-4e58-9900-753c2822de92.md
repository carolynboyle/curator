# Detail Panel Implementation — Summary & Checklist

**Date:** 2026-06-27  
**Status:** Ready for implementation  
**Scope:** Complete detail panel system with QueryLoader integration

---

## Files to Create

### HTML Partials

1. **`templates/partials/_datasheet.html`** — Tabulator grid component (child of `_datasheet_with_header.html`)
   - Location: `/mnt/user-data/outputs/_datasheet.html`
   - Copy to: `templates/partials/_datasheet.html`

2. **`templates/partials/_datasheet_with_header.html`** — Datasheet with header bar (+ button, search)
   - Location: `/mnt/user-data/outputs/_datasheet_with_header.html`
   - Copy to: `templates/partials/_datasheet_with_header.html`

3. **`templates/partials/_detail_panel.html`** — Tabbed detail form with child datasheets
   - Location: `/mnt/user-data/outputs/_detail_panel.html`
   - Copy to: `templates/partials/_detail_panel.html`

### CSS

4. **`static/css/components/detail-panel.css`** — Detail panel styling
   - Location: `/mnt/user-data/outputs/detail-panel.css`
   - Copy to: `static/css/components/detail-panel.css`
   - **Must be imported** in `base.html` or main CSS file

### JavaScript

5. **`static/js/detail-panel.js`** — Detail panel interaction logic
   - Location: `/mnt/user-data/outputs/detail-panel.js`
   - Copy to: `static/js/detail-panel.js`
   - **Must be imported** in `base.html` as ES module

### CSS Theme Updates

6. **Update `static/css/themes/light.css`** — Add form/button color variables
   - See: `/mnt/user-data/outputs/CHANGEDOC_CSS_VARIABLES.md`
   - Add the form input and button color variables to `:root`

7. **Update `static/css/themes/dark.css`** — Add form/button color variables
   - See: `/mnt/user-data/outputs/CHANGEDOC_CSS_VARIABLES.md`
   - Add the form input and button color variables to `:root`

---

## Files to Modify

### queries.yaml

8. **Update `queries.yaml`** — Add child datasheet queries
   - See: `/mnt/user-data/outputs/CHANGEDOC_QUERIES.md`
   - Add query groups for:
     - `tasks.for_project`
     - `contact_emails.for_contact`
     - `contact_phones.for_contact`
     - `contact_urls.for_contact`
     - `organization_contacts.for_organization`
     - `organization_contacts.for_contact`

### crew.py

9. **Update `curator/web/routes/crew.py`** — Add QueryLoader initialization and `/api/query` endpoint
   - See: `/mnt/user-data/outputs/CHANGEDOC_API_QUERY_ENDPOINT.md`
   - Add imports for `QueryBuilder`, `QueryLoader`
   - Initialize `query_builder` and `query_loader` at module level
   - Add `@router.get("/api/query/{entity}/{query_name}")` route

### captain.html (or relevant crew page)

10. **Update `templates/captain.html`** — Add detail panel container
    - See: `/mnt/user-data/outputs/CHANGEDOC_CAPTAIN_HTML_INTEGRATION.md`
    - Add `<div id="detail-panel-container"></div>` after `.crew-hero`
    - Update `_projects_table.html` to wire ⋯ button to `openDetailPanel()`

### base.html

11. **Update `templates/base.html`** — Import CSS and JS
    - Add: `<link rel="stylesheet" href="/static/css/components/detail-panel.css">`
    - Add: `<script type="module" src="/static/js/detail-panel.js"></script>`

---

## Implementation Order

### Phase 1: Infrastructure
1. Update `light.css` and `dark.css` with new color variables
2. Create `_datasheet.html` and `_datasheet_with_header.html` partials
3. Create `detail-panel.css`
4. Update `queries.yaml` with new queries
5. Update `crew.py` with QueryLoader init and `/api/query` endpoint

### Phase 2: Templates & JavaScript
6. Create `_detail_panel.html` partial
7. Create `detail-panel.js`
8. Update `base.html` to import CSS and JS
9. Update `captain.html` to add detail panel container
10. Wire ⋯ button in `_projects_table.html` to call `openDetailPanel()`

### Phase 3: Testing
- Test opening/closing detail panel
- Test tab switching
- Test form save on Details tab
- Test child datasheet loading (Tasks, Emails, Phones, URLs)
- Test search and clear functionality (deferred but structure ready)

---

## Key Architectural Points

### QueryLoader Integration
- Queries live in `queries.yaml`, not scattered across route files
- `/api/query/{entity}/{query_name}?params=X` is the single endpoint for all child datasheets
- QueryLoader is initialized at module startup for performance

### Three-Level Composition
```
_detail_panel.html                    (top-level tabbed form)
  └─ _datasheet_with_header.html      (child datasheet + controls)
      └─ _datasheet.html              (just the Tabulator grid)
```

### CSS & Theming
- Form/button colors defined as CSS variables in theme files
- `detail-panel.css` uses these variables, works in both light and dark themes
- Datasheet always renders in light theme (via `tabulator-overrides.css`)
- Hero ↔ Panel transitions are pure CSS (fade in/out with opacity + visibility)

### JavaScript Event Delegation
- `detail-panel.js` uses event delegation (single listener on `document`)
- Works for dynamic content (tabs, close button, form submit)
- Easy to add new features (search, row save, etc.)

---

## Deferred Features (Not Implemented Yet)

These features are designed into the skeleton but not wired up in this phase:

1. **Search functionality** — Input box exists, filter logic deferred
2. **Row save in child datasheets** — Save button and endpoint deferred
3. **Add new row** — `+ Task`, `+ Email`, etc. buttons exist, POST logic deferred
4. **Detail form dirty state** — Save/Discard dialog deferred
5. **Links & Files tabs** — Placeholders exist, queries/forms deferred

---

## Testing Checklist

Once implemented:

- [ ] Page loads without JavaScript errors
- [ ] Detail panel container renders correctly
- [ ] Click ⋯ on a project row → detail panel opens, hero fades out
- [ ] Click × or press Escape → detail panel closes, hero fades in
- [ ] Click a tab → tab switches, active button/panel highlight updates
- [ ] Details form loads with current values
- [ ] Save button on Details form → form submits to POST endpoint
- [ ] Tasks tab loads → `GET /api/query/tasks/for_project?params=X` is called
- [ ] Task grid renders with rows and columns
- [ ] Same for Emails, Phones, URLs, Organizations tabs
- [ ] Theme switching (light/dark) → form inputs and buttons theme correctly

---

## API Endpoints Summary

### New Endpoints

```
GET /api/query/{entity}/{query_name}?params=X,Y,Z
  Returns: { "records": [...] }
  Used by: Child datasheets in detail panel

GET /crew/{entity}/{id}
  Returns: Full record data as JSON
  Used by: openDetailPanel() to fetch record before opening
  NOTE: May already exist or need to be created from existing functions

POST /crew/{entity}/{id}/save
  Payload: { "field": "value", ... }
  Returns: Success/error response
  Used by: Details form save button
  NOTE: Likely exists already from datasheet inline edit
```

### Updated Routes

The following routes may need updates to support detail panel features (deferred):

- `POST /crew/tasks/add` — Create new task in project
- `POST /crew/tasks/{id}/save` — Save task edits
- `POST /crew/contacts/emails/add` — Add email to contact
- `POST /crew/contacts/emails/{id}/save` — Save email
- (and similar for phones, URLs, org contacts)

---

## Files with Detailed Implementation Notes

1. **CSS Variables:** `/mnt/user-data/outputs/CHANGEDOC_CSS_VARIABLES.md`
2. **Queries:** `/mnt/user-data/outputs/CHANGEDOC_QUERIES.md`
3. **API Endpoint:** `/mnt/user-data/outputs/CHANGEDOC_API_QUERY_ENDPOINT.md`
4. **HTML Integration:** `/mnt/user-data/outputs/CHANGEDOC_CAPTAIN_HTML_INTEGRATION.md`

---

## Quick Reference

| File | What | Where |
|------|------|-------|
| `_datasheet.html` | Grid only | templates/partials/ |
| `_datasheet_with_header.html` | Grid + controls | templates/partials/ |
| `_detail_panel.html` | Tabs + forms | templates/partials/ |
| `detail-panel.css` | All styling | static/css/components/ |
| `detail-panel.js` | Interactions | static/js/ |
| `light.css`, `dark.css` | Theme vars | static/css/themes/ |
| `queries.yaml` | Child queries | project root |
| `crew.py` | `/api/query` route | curator/web/routes/ |
| `captain.html` | Panel container | templates/ |
| `base.html` | CSS/JS imports | templates/ |

