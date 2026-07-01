# Detail Panel UX Fixes — Sticky Action Buttons & Enter Key Handling

**Date:** 2026-06-28  
**Status:** Ready to apply  
**Affected files:** `_detail_panel.html`, `detail-panel.js`, `detail-panel.css`

---

## Problem Statement

### Issue #1: Action buttons disappear when scrolling
When a detail panel form has enough content to scroll (or when viewing child datasheets), the Save/New/Discard buttons at the bottom of the form scroll out of view. This breaks the rapid-entry workflow where users type data, hit Alt+N to save and create a new record.

### Issue #2: Enter key discards changes
Pressing Enter in a form field (Name, Type, Status, Description) was submitting the form unintentionally, causing data loss. User expectation: Enter should move to the next field (like Tab) without triggering a save.

---

## Solutions Implemented

### Solution #1: Sticky Footer Action Bar
**Change:** Move `.form-actions` outside the scrollable `.detail-tab-panels` container and position it as a sticky footer.

**Why:** The `.detail-tab-panels` container has `overflow-y: auto` for scrolling form content. Elements inside scroll out of view. By moving the action buttons to a sibling container below the tab panels, they become part of the detail panel's flex layout and stay fixed at the bottom.

**CSS approach:** The `.detail-panel-actions` is a `flex-shrink: 0` sibling to `.detail-tab-panels`, so it never scrolls away.

### Solution #2: Enter Key → Move to Next Field
**Change:** Add a `keydown` listener in `detail-panel.js` that intercepts Enter on form inputs/textareas and moves focus to the next focusable element.

**Why:** Default form submission behavior (Ctrl+Enter or Enter on last field) was being triggered. By preventing Enter's default and manually managing focus, we preserve the user's data and enable rapid field navigation.

**Behavior:**
- Enter on any form field (except last): moves focus to next input/select/textarea
- Enter on last field: blurs the field (deselects it)
- Alt+S still saves (explicit keyboard shortcut)
- Alt+N still saves & creates new record
- Alt+X still discards & closes panel

---

## File Changes

### File 1: `src/curator/templates/partials/_detail_panel.html`

**Line 112-115 (BEFORE):**
```html
        <div class="form-actions">
          <button type="submit" class="btn-save">Save</button>
          <button type="reset" class="btn-discard">Discard</button>
        </div>
      </form>
    </div>
```

**Line 112-115 (AFTER):**
```html
      </form>
    </div>
```

**Line 240-247 (NEW, at end of detail-panel, after all tab panels):**
```html
  <!-- Action buttons: sticky footer at bottom of panel -->
  <!-- Only visible on Details tab (where the form is) -->
  <div class="detail-panel-actions">
    <button type="submit" form="detail-form" class="btn-save" title="Save (Alt+S)">Save</button>
    <button type="button" class="btn-new" title="New (Alt+N)">New</button>
    <button type="button" class="btn-discard" title="Discard (Alt+X)">Discard (Alt+X)</button>
  </div>
```

**Explanation:**
- Removed `.form-actions` from inside the scrollable `.detail-tab-panel`
- Added `.detail-panel-actions` as a sibling to `.detail-tab-panels` at the same flex level
- Added `form="detail-form"` attribute to Save button so it can submit the form without being inside it
- Updated button text to show keyboard shortcuts in tooltip + text

---

### File 2: `static/css/components/detail-panel.css`

**Lines 148-182 (REPLACED):**

**BEFORE:**
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

**AFTER:**
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

**Explanation:**
- Changed `.form-actions` to `.detail-panel-actions` (scoped to the new footer container)
- Added `flex-shrink: 0` to prevent the footer from shrinking
- Added `border-top` and `background` to visually separate the footer from the scrollable content
- Scoped all button styles to `.detail-panel-actions .btn-*` for specificity
- Added `.btn-new` styles (same as secondary style)

---

### File 3: `static/js/detail-panel.js`

**Lines 46-83 (REPLACED):**

**BEFORE:**
```javascript
  // Escape key to close detail panel
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && detailPanelContainer?.querySelector('.detail-panel.active')) {
      closeDetailPanel();
    }
  });

  // Form save
  document.addEventListener('submit', async (e) => {
    if (!e.target.classList.contains('detail-form')) return;
    e.preventDefault();

    const form = e.target;
    const entity = form.dataset.entity;
    const recordId = form.dataset.id;

    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    const saveUrl = `/crew/${entity}/${recordId}/save`;

    try {
      const res = await fetch(saveUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (res.ok) {
        // Update successful — could refresh datasheet or show toast
        console.log(`${entity} ${recordId} saved`);
      } else {
        const errorText = await res.text();
        console.error(`Save failed: ${errorText}`);
      }
    } catch (err) {
      console.error('Save error:', err);
    }
  });
```

**AFTER:**
```javascript
  // Escape key to close detail panel
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && detailPanelContainer?.querySelector('.detail-panel.active')) {
      closeDetailPanel();
    }

    // Alt+S to save
    if (e.altKey && e.key === 's') {
      e.preventDefault();
      const detailPanel = detailPanelContainer?.querySelector('.detail-panel.active');
      if (detailPanel) {
        const form = detailPanel.querySelector('form.detail-form');
        if (form) form.dispatchEvent(new Event('submit'));
      }
    }

    // Alt+N to new
    if (e.altKey && e.key === 'n') {
      e.preventDefault();
      const detailPanel = detailPanelContainer?.querySelector('.detail-panel.active');
      if (detailPanel) {
        handleNewRecord(e);
      }
    }

    // Alt+X to discard
    if (e.altKey && e.key === 'x') {
      e.preventDefault();
      closeDetailPanel();
    }
  });

  // Enter key in form inputs: move to next field instead of submitting
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const form = e.target.closest('form.detail-form');
      if (!form) return;

      // Only handle Enter in input and textarea elements
      if (!['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      e.preventDefault();

      // Get all focusable form elements (inputs, selects, textareas)
      const focusableElements = Array.from(form.querySelectorAll(
        'input:not([type="hidden"]), select, textarea'
      ));

      const currentIndex = focusableElements.indexOf(e.target);
      if (currentIndex !== -1 && currentIndex < focusableElements.length - 1) {
        // Move to next element
        focusableElements[currentIndex + 1].focus();
      } else if (currentIndex === focusableElements.length - 1) {
        // If at last field, blur to deselect
        e.target.blur();
      }
    }
  });

  // Form save
  document.addEventListener('submit', async (e) => {
    if (!e.target.classList.contains('detail-form')) return;
    e.preventDefault();

    const form = e.target;
    const entity = form.dataset.entity;
    const recordId = form.dataset.id;

    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    const saveUrl = `/crew/${entity}/${recordId}/save`;

    try {
      const res = await fetch(saveUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (res.ok) {
        // Update successful — close panel and refresh datasheet
        console.log(`${entity} ${recordId} saved`);
        closeDetailPanel();
        // TODO: Refresh datasheet grid
      } else {
        const errorText = await res.text();
        console.error(`Save failed: ${errorText}`);
      }
    } catch (err) {
      console.error('Save error:', err);
    }
  });
```

**Changes in click handler (lines 39-50):**

**BEFORE:**
```javascript
    // Close button
    if (e.target.classList.contains('detail-close-button')) {
      closeDetailPanel();
    }
```

**AFTER:**
```javascript
    // Close button
    if (e.target.classList.contains('detail-close-button')) {
      closeDetailPanel();
    }

    // New button (Alt+N)
    if (e.target.classList.contains('btn-new')) {
      handleNewRecord(e);
    }

    // Discard button (Alt+X / Escape)
    if (e.target.classList.contains('btn-discard')) {
      closeDetailPanel();
    }
```

**Explanation:**
- Added Alt+S, Alt+N, Alt+X keyboard handlers in the keydown listener (moved from outside the Escape check)
- Added Enter key handler that prevents default and moves focus to next field
- Added click handlers for `.btn-new` and `.btn-discard` buttons
- Updated form save handler to call `closeDetailPanel()` on success (was missing before)
- Added new `handleNewRecord()` function to save and reset form for rapid entry

**New function (after initDetailPanel):**

```javascript
/**
 * Handle "New" button: save current record and reset form for next entry.
 */
function handleNewRecord(e) {
  const detailPanel = e.target?.closest('.detail-panel') || document.querySelector('.detail-panel.active');
  if (!detailPanel) return;

  const form = detailPanel.querySelector('form.detail-form');
  if (!form) return;

  // Save current record first
  form.dispatchEvent(new Event('submit'));

  // Reset form and focus Name field
  form.reset();
  const nameField = form.querySelector('input[name="name"]');
  if (nameField) {
    nameField.focus();
  }
}
```

---

## Testing Checklist

- [ ] Open detail panel for existing project
- [ ] Type in Name field, press Enter → should move to Type dropdown (not submit)
- [ ] Type in Type field, press Enter → should move to Status dropdown
- [ ] Scroll down in form (if it scrolls) → Save/New/Discard buttons remain visible at bottom
- [ ] Press Alt+S → form saves and panel closes
- [ ] Click `+ Add Project` → open new project form
- [ ] Type Name, press Enter → focus moves to Type
- [ ] Type Type, press Enter → focus moves to Status
- [ ] Press Alt+N → saves record, clears form, focuses Name field
- [ ] Type new Name, press Alt+S → saves second record
- [ ] Close detail panel (Escape or × button) → hero image reappears

---

## Notes

- The `form="detail-form"` attribute on the Save button allows it to submit the form even though it's outside the `<form>` tag. This is standard HTML5 and well-supported.
- Enter key handling only applies to `<input>` and `<textarea>` elements, not `<select>` (selects have their own dropdown interaction).
- The `handleNewRecord()` function uses `form.reset()` which clears all fields. If you need to preserve certain fields (like project Type or Status), modify this function to selectively reset.
- Focus is automatically moved to the Name field when opening a panel or after New is triggered (see `openDetailPanel()` function updates).

---

## Deployment Notes

1. Replace `src/curator/templates/partials/_detail_panel.html`
2. Replace `static/css/components/detail-panel.css`
3. Replace `static/js/detail-panel.js`
4. Clear browser cache (hard refresh or Ctrl+Shift+R)
5. Test in all browsers (Enter key behavior is consistent across modern browsers)

---

## Future Improvements

- Keyboard shortcut help modal (show on `?` key or from menu)
- Dirty state detection (show warning if unsaved changes when closing panel)
- Auto-save on blur (save current field when focus leaves it)
- Tabbed navigation to move between tabs with Ctrl+Tab / Ctrl+Shift+Tab
