# Detail Panel & Route Fixes — Deployment Guide

**Date:** 2026-06-28  
**Status:** Ready to apply  
**Fixes:** 
- Jinja2 template syntax errors
- Missing data in crew.py route
- Missing window global functions in detail-panel.js
- Delete obsolete captain.html template

---

## What's Fixed

### Issue 1: Jinja2 TemplateSyntaxError
**Error:** `expected token 'end of statement block', got 'with'`

**Cause:** Invalid Jinja2 `include` syntax on child datasheet tabs

**Fix:** Replaced broken includes with placeholder "coming soon" tabs

### Issue 2: Click handlers not working (window is not a function)
**Error:** `Uncaught TypeError: window.openDetailPanel is not a function`

**Cause:** detail-panel.js exports functions but doesn't expose them to global scope

**Fix:** Added `window.openDetailPanel` and `window.closeDetailPanel` at module end

### Issue 3: Templates and JS don't have required data
**Error:** Nothing happens when clicking `+ Add Project` or `...`

**Cause:** crew.py route doesn't fetch/pass:
- `project_types` — type dropdown lookup
- `project_statuses` — status dropdown lookup
- `tabs` — tab configuration
- `organizations` & `contacts` — for Identities tab (Captain only)

**Fix:** Updated crew.py to fetch and pass all required data

### Issue 4: captain.html is dead code
**Status:** No longer used (crew.html replaced it)

**Fix:** Delete captain.html

---

## Files to Replace/Delete

### 1. Replace: `src/curator/web/routes/crew.py`
**Replace with:** `crew_FIXED.py`

**Changes:**
- Added queries for project_types and project_statuses
- Added queries for organizations and contacts (Captain role only)
- Build dynamic tabs array based on role
- Pass all data to template: `project_types`, `project_statuses`, `organizations`, `contacts`, `tabs`

### 2. Replace: `static/js/detail-panel.js`
**Replace with:** `detail-panel_FIXED.js` (updated version with window globals)

**Changes:**
- Added `window.openDetailPanel = openDetailPanel;`
- Added `window.closeDetailPanel = closeDetailPanel;`
- These expose the functions so HTML onclick handlers can call them

### 3. Replace: `src/curator/templates/partials/_detail_panel.html`
**Replace with:** `_detail_panel_FIXED.html`

**Changes:**
- Removed invalid Jinja2 includes on child datasheets
- Replaced with placeholder tabs showing "coming soon"
- Kept form fields and action buttons

### 4. Replace: `static/css/components/detail-panel.css`
**Replace with:** `detail-panel_FIXED.css`

**Changes:**
- Complete styling for detail panel and buttons

### 5. DELETE: `src/curator/templates/captain.html`

**Reason:** No longer used. crew.html is the single template for all roles.

---

## Deployment Steps

1. **Stop the dev server:**
   ```bash
   cd ~/projects/curator
   bash stop.sh
   ```

2. **Back up current files:**
   ```bash
   cp src/curator/web/routes/crew.py src/curator/web/routes/crew.py.bak
   cp static/js/detail-panel.js static/js/detail-panel.js.bak
   cp src/curator/templates/partials/_detail_panel.html src/curator/templates/partials/_detail_panel.html.bak
   cp static/css/components/detail-panel.css static/css/components/detail-panel.css.bak
   ```

3. **Replace files:**
   ```bash
   cp crew_FIXED.py ~/projects/curator/src/curator/web/routes/crew.py
   cp detail-panel_FIXED.js ~/projects/curator/static/js/detail-panel.js
   cp _detail_panel_FIXED.html ~/projects/curator/src/curator/templates/partials/_detail_panel.html
   cp detail-panel_FIXED.css ~/projects/curator/static/css/components/detail-panel.css
   ```

4. **Delete dead code:**
   ```bash
   rm ~/projects/curator/src/curator/templates/captain.html
   ```

5. **Start the dev server:**
   ```bash
   cd ~/projects/curator
   bash start.sh
   ```

6. **Test:**
   - Open http://localhost:8080/crew?role=captain
   - Should load without errors
   - **Click `+ Add Project`** — detail panel should open
   - **Click on a project row's `...`** — detail panel should open with data
   - Type in Name field, press Enter → moves to Type dropdown
   - Type in Type field, press Enter → moves to Status dropdown
   - Press Alt+S → saves and closes panel
   - Press Alt+N → saves, clears form, focuses Name field
   - Press Alt+X or Escape → closes panel without saving
   - Scroll down in form → Save/New/Discard buttons remain visible at bottom

---

## SQL Queries Added to crew.py

The updated route now queries:
- `projects.project_type` — for dropdown
- `projects.project_status` — for dropdown
- `identity.organizations` — with aggregated contact IDs
- `identity.contacts` — with email and aggregated org IDs

These assume your database schema has these tables. If table names differ, update the SQL in crew_FIXED.py.

---

## Git Commit

After testing and verifying everything works:

```bash
cd ~/projects/curator
git add src/curator/web/routes/crew.py
git add static/js/detail-panel.js
git add src/curator/templates/partials/_detail_panel.html
git add static/css/components/detail-panel.css
git rm src/curator/templates/captain.html
git commit -m "fix: detail panel integration and crew route data

- Fix Jinja2 syntax errors in _detail_panel.html
- Add global window functions to detail-panel.js
- Fetch and pass required data in crew.py route
- Delete obsolete captain.html (crew.html is universal)
- Detail panel now functional: + Add Project and ... (edit) work"
```

---

## Rollback

If anything goes wrong:

```bash
cd ~/projects/curator
cp src/curator/web/routes/crew.py.bak src/curator/web/routes/crew.py
cp static/js/detail-panel.js.bak static/js/detail-panel.js
cp src/curator/templates/partials/_detail_panel.html.bak src/curator/templates/partials/_detail_panel.html
cp static/css/components/detail-panel.css.bak static/css/components/detail-panel.css
git checkout src/curator/templates/captain.html  # Restore deleted file
bash stop.sh && bash start.sh
```

---

## What's Still Deferred

The following features are stubbed but not implemented:

- Child datasheets (Tasks, Emails, Phones, URLs, Organizations tabs show "coming soon")
- Contacts/Organizations detail forms
- Identities tab filtering (buttons wired but handlers not connected yet)

These will be implemented in Phase 2.

---

## Questions?

Refer to:
- `CHANGEDOC_DETAIL_PANEL_FIXES.md` — detailed technical explanation
- `curator_handoff_2026-06-28.md` — session summary
