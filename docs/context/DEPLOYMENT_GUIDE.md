# Detail Panel Fixes — Deployment Guide

**Date:** 2026-06-28  
**Status:** Ready to apply  
**Fixes:** Jinja2 template syntax errors + Enter key behavior + sticky buttons

---

## What's Fixed

### Issue: Jinja2 TemplateSyntaxError
**Error:** `expected token 'end of statement block', got 'with'`

**Cause:** Invalid Jinja2 `include` syntax on child datasheet tabs (Tasks, Emails, Phones, URLs, Organizations)

**Fix:** Replaced broken includes with placeholder "coming soon" tabs. Child datasheets will be implemented later using the proper approach.

### Issue: Enter key discards changes
**Behavior:** Pressing Enter in a form field was submitting the form unintentionally

**Fix:** Added `keydown` listener that moves focus to the next field instead. Preserves Alt+S, Alt+N, Alt+X keyboard shortcuts.

### Issue: Action buttons disappear on scroll
**Behavior:** Save/New/Discard buttons scrolled out of view when form had many fields

**Fix:** Moved buttons outside scrollable container as sticky footer. `.detail-panel-actions` with `flex-shrink: 0` ensures buttons always visible.

---

## Files to Replace

### 1. `src/curator/templates/partials/_detail_panel.html`
**Replace with:** `_detail_panel_FIXED.html`

**Changes:**
- Removed invalid Jinja2 includes on child datasheets (Tasks, Emails, Phones, URLs, Organizations)
- Replaced with placeholder tabs showing "coming soon" message
- Kept form fields (Name, Type, Status, Description) with valid syntax
- Action buttons remain hardcoded (not using formkit yet)

### 2. `static/css/components/detail-panel.css`
**Replace with:** `detail-panel_FIXED.css`

**Changes:**
- Restored button styles for `.detail-panel-actions` section
- All styles present and complete
- Ready to use with the fixed template

### 3. `static/js/detail-panel.js`
**Replace with:** `detail-panel_FIXED.js`

**Changes:**
- Added `keydown` listener for Enter key field navigation
- Added Alt+S, Alt+N, Alt+X keyboard shortcuts
- Added click handlers for New/Discard buttons
- Improved form save handler to close detail panel on success

---

## Deployment Steps

1. **Stop the dev server:**
   ```bash
   # In the curator directory
   bash stop.sh
   ```

2. **Back up current files:**
   ```bash
   cd ~/projects/curator
   cp src/curator/templates/partials/_detail_panel.html src/curator/templates/partials/_detail_panel.html.bak
   cp static/css/components/detail-panel.css static/css/components/detail-panel.css.bak
   cp static/js/detail-panel.js static/js/detail-panel.js.bak
   ```

3. **Replace files:**
   ```bash
   # Copy the fixed files to your project
   cp _detail_panel_FIXED.html ~/projects/curator/src/curator/templates/partials/_detail_panel.html
   cp detail-panel_FIXED.css ~/projects/curator/static/css/components/detail-panel.css
   cp detail-panel_FIXED.js ~/projects/curator/static/js/detail-panel.js
   ```

4. **Start the dev server:**
   ```bash
   cd ~/projects/curator
   bash start.sh
   ```

5. **Test:**
   - Open http://localhost:8080/crew?role=captain
   - Should load without Jinja2 errors
   - Click on a project row to open detail panel
   - Test keyboard shortcuts:
     - Type in Name field, press Enter → moves to Type dropdown
     - Type in Type field, press Enter → moves to Status dropdown
     - Press Alt+S → saves and closes panel
     - Press Alt+N → saves, clears form, focuses Name field
     - Press Alt+X or Escape → closes panel without saving
   - Scroll down in form → Save/New/Discard buttons remain visible at bottom

---

## What's NOT Yet Implemented

The following tabs show placeholder "coming soon" messages:

- **Projects detail panel:**
  - Tasks tab
  - Links tab
  - Contacts tab

- **Contacts detail panel:**
  - Emails tab
  - Phones tab
  - URLs tab
  - Organizations tab

- **Organizations detail panel:**
  - Contacts tab

These will be implemented in Phase 2 when the formkit component is ready.

---

## Next Steps (Formkit Refactor)

Once this is working and committed, we can apply the formkit component refactor:

1. **Add new files:**
   - `src/curator/formkit.py` (Python button builder)
   - `src/curator/templates/partials/_form_actions.html` (Jinja2 partial)
   - `config/forms.yaml` (action specifications)
   - `static/css/components/form-actions.css` (component styles)

2. **Update routes:** Pass `form_actions` to templates from Python

3. **Update _detail_panel.html:** Use `{% include '_form_actions.html' %}`

This will make the action button bar reusable across all forms.

---

## Rollback

If anything goes wrong, restore the backups:

```bash
cd ~/projects/curator
cp src/curator/templates/partials/_detail_panel.html.bak src/curator/templates/partials/_detail_panel.html
cp static/css/components/detail-panel.css.bak static/css/components/detail-panel.css
cp static/js/detail-panel.js.bak static/js/detail-panel.js
bash stop.sh && bash start.sh
```

---

## Git Commit

After testing and verifying everything works:

```bash
cd ~/projects/curator
git add src/curator/templates/partials/_detail_panel.html
git add static/css/components/detail-panel.css
git add static/js/detail-panel.js
git commit -m "fix: resolve Jinja2 syntax errors and improve detail panel UX

- Fix invalid include syntax on child datasheet tabs
- Add Enter key field navigation (move to next field, not submit)
- Add keyboard shortcuts: Alt+S save, Alt+N new, Alt+X discard
- Sticky footer for action buttons (always visible on scroll)
- Child datasheets deferred to Phase 2"
```

---

## Questions?

Refer to:
- `CHANGEDOC_DETAIL_PANEL_FIXES.md` — detailed technical explanation
- `curator_handoff_2026-06-28.md` — session summary and next build sequence
