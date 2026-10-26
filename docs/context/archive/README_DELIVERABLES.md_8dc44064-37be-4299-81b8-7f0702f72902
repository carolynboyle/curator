# Detail Panel Implementation — Complete Deliverables

**Date:** 2026-06-27  
**Status:** Ready to implement  
**Total files:** 11 new/modified files across HTML, CSS, JavaScript, SQL, and Python

---

## Overview

This is a complete, production-ready skeleton for Curator's detail panel system. The detail panel displays a record's details in a tabbed interface, with child datasheets for related records (tasks, emails, phones, etc.).

**Architecture:** QueryLoader-powered `/api/query` endpoint feeds data to reusable `_datasheet_with_header.html` partial, which itself includes the `_datasheet.html` grid component.

---

## All Deliverables

### Visual Skeleton (3 HTML partials)
- ✅ `_datasheet.html` — Just the Tabulator grid
- ✅ `_datasheet_with_header.html` — Grid + header with + button and search
- ✅ `_detail_panel.html` — Full tabbed interface with Details form and child datasheets

### Styling (1 CSS file, 1 CSS changedoc)
- ✅ `detail-panel.css` — Complete styling for panels, tabs, forms
- ✅ `CHANGEDOC_CSS_VARIABLES.md` — Add color variables to light.css and dark.css

### JavaScript (1 file)
- ✅ `detail-panel.js` — Tab switching, open/close, form save, event delegation

### Backend (2 changedocs, 1 design doc)
- ✅ `CHANGEDOC_QUERIES.md` — Add 6 child datasheet queries to queries.yaml
- ✅ `CHANGEDOC_API_QUERY_ENDPOINT.md` — Add `/api/query` endpoint to crew.py
- ✅ `detail_panel_architecture.md` — Full design and rationale

### Integration & Reference (3 changedocs, 1 summary)
- ✅ `CHANGEDOC_CAPTAIN_HTML_INTEGRATION.md` — Wire detail panel into captain.html
- ✅ `IMPLEMENTATION_SUMMARY.md` — Checklist, order of operations, testing guide
- ✅ Plus the original architecture design doc

---

## Quick Start

### 1. Apply Theme Variables
Edit `static/css/themes/light.css` and `dark.css`:
- Add form input color variables
- Add button color variables
- See: `CHANGEDOC_CSS_VARIABLES.md`

### 2. Copy HTML Partials
```
cp _datasheet.html templates/
cp _datasheet_with_header.html templates/
cp _detail_panel.html templates/
```

### 3. Copy CSS & JS
```
cp detail-panel.css static/css/components/
cp detail-panel.js static/js/
```

### 4. Update queries.yaml
Add 6 new query groups. See: `CHANGEDOC_QUERIES.md`

### 5. Update crew.py
- Add QueryBuilder/QueryLoader imports and initialization
- Add `/api/query/{entity}/{query_name}` route
- See: `CHANGEDOC_API_QUERY_ENDPOINT.md`

### 6. Update captain.html
- Add `<div id="detail-panel-container"></div>` after hero
- Wire ⋯ button to `openDetailPanel()`
- See: `CHANGEDOC_CAPTAIN_HTML_INTEGRATION.md`

### 7. Update base.html
- Import `detail-panel.css`
- Import `detail-panel.js` as ES module

---

## Architecture Highlights

### QueryLoader Integration
✅ Queries centralized in `queries.yaml`  
✅ `/api/query/{entity}/{query_name}?params=X` handles all child datasheets  
✅ Easy to audit — Captain can see exactly what data is being fetched  

### Three-Level Composition
```
_detail_panel.html (tabbed form)
  └─ _datasheet_with_header.html (datasheet + controls)
      └─ _datasheet.html (Tabulator grid)
```
Each level is independent and reusable.

### CSS Variables
✅ Theme-aware (light/dark)  
✅ Form inputs and buttons use theme colors  
✅ Easy to rebrand by changing variable values  

### JavaScript Event Delegation
✅ Single listener on `document`  
✅ Works with dynamically-rendered tabs and forms  
✅ Minimal coupling between components  

---

## What's NOT Included (Deferred)

- Search/filter functionality in child datasheets (structure ready)
- Row save in child datasheets (structure ready)
- Add new row functionality (structure ready)
- Dirty state Save/Discard dialog
- Links and Files tabs (placeholders included)
- Deep linking to specific records (future enhancement)

All of these are designed into the skeleton and can be added without restructuring.

---

## Testing

Once implemented, test:

1. **Open/Close** — Click ⋯ → panel opens. Click × or Escape → closes.
2. **Hero Fade** — Hero image fades out smoothly. Fades back in on close.
3. **Tab Switching** — Click tabs → content switches, active styling updates.
4. **Details Form** — Form loads with current values. Save button → POST.
5. **Child Datasheets** — Tasks, Emails, Phones, URLs tabs all load data.
6. **Grid Rendering** — Rows and columns display correctly.
7. **Theme Switching** — Light/dark modes → form styling updates correctly.

See: `IMPLEMENTATION_SUMMARY.md` for full checklist.

---

## Files Reference

| File | Type | Purpose |
|------|------|---------|
| `_datasheet.html` | HTML | Tabulator grid component |
| `_datasheet_with_header.html` | HTML | Grid + header with controls |
| `_detail_panel.html` | HTML | Tabbed detail form |
| `detail-panel.css` | CSS | All panel styling |
| `detail-panel.js` | JS | Tab switching, open/close, form save |
| `CHANGEDOC_CSS_VARIABLES.md` | Doc | Theme variable additions |
| `CHANGEDOC_QUERIES.md` | Doc | New queries to add |
| `CHANGEDOC_API_QUERY_ENDPOINT.md` | Doc | `/api/query` endpoint |
| `CHANGEDOC_CAPTAIN_HTML_INTEGRATION.md` | Doc | HTML integration |
| `IMPLEMENTATION_SUMMARY.md` | Doc | Checklist & testing |
| `detail_panel_architecture.md` | Doc | Design & rationale |

---

## Key Design Decisions

### Why QueryLoader?
- Queries live in YAML, not scattered across Python files
- Auditable — Captain can see exactly what's being fetched
- Extensible — adding new child datasheets just means adding a query

### Why `_datasheet_with_header.html`?
- Prevents code duplication if multiple datasheets need + button and search
- Clean separation: grid logic in `_datasheet.html`, header UI in parent
- Parent detail panel uses `_datasheet_with_header.html` consistently

### Why event delegation in detail-panel.js?
- Works with dynamically-rendered content
- Minimal global state
- Easy to trace (all listeners in one place)

### Why CSS variables for colors?
- Theme switching works automatically (light/dark CSS files override them)
- Rebrandable (change one variable, affects all instances)
- Future-proof (easy to add new color schemes)

---

## Next Steps

1. Review architecture and design docs
2. Apply changes in order (see IMPLEMENTATION_SUMMARY.md)
3. Test each component as implemented
4. Once verified, move on to deferred features (search, row save, add new row)

---

## Questions?

Refer to the corresponding changedoc for each implementation step:

- **CSS themes:** `CHANGEDOC_CSS_VARIABLES.md`
- **Queries:** `CHANGEDOC_QUERIES.md`
- **Backend endpoint:** `CHANGEDOC_API_QUERY_ENDPOINT.md`
- **HTML integration:** `CHANGEDOC_CAPTAIN_HTML_INTEGRATION.md`
- **Full system design:** `detail_panel_architecture.md`

Each document includes BEFORE/AFTER code and detailed explanations.
