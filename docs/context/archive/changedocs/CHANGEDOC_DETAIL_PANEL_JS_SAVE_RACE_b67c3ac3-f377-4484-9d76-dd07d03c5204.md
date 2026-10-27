# Changedoc: detail-panel.js — Fix Save button racing native form submission

**File:** `static/js/detail-panel.js`
**Date:** 2026-06-29
**Source verified:** Uploaded directly by Carolyn.

## Root cause

`forms.yaml` defines the Save button as:

```yaml
save:
  type: submit
  form_id: detail-form
```

Rendered to HTML, that's `<button type="submit" form="detail-form">`. A
`type="submit"` button explicitly associated with a form via the `form`
attribute does two things on click, simultaneously: (1) it's a normal DOM
element, so any click-delegation listener on it fires normally, and (2) it
triggers the browser's **native form submission** for `#detail-form`,
independent of any JS.

`initDetailPanel()`'s click listener does call `handleSave()` when
`btn-save` is clicked — that part works. But nothing ever calls
`e.preventDefault()` on that click, and `#detail-form` has no `submit`
listener either. So native submission fires unopposed, racing the
`fetch()`-based `handleSave()`. Since `#detail-form` has no `action` or
`method` attribute, native submission falls back to browser default: **GET
to the current page URL**, with every form field serialized as a query
string parameter.

That's the exact symptom observed: clicking Save produced
`GET /crew?name=API+TEST&type_id=1&status_id=1&description=test` in the
server log instead of `POST /crew/projects/save` with a JSON body.
`crew_dashboard` doesn't read those query params for anything, so the page
just silently re-renders with no save having occurred — no error, no
console output, nothing — which is exactly why this was hard to spot from
symptoms alone.

A second, not-yet-triggered instance of the same root cause: with no
`keydown`-based Enter-key interception in this version of the file (an
earlier version of `detail-panel.js` reviewed earlier in this project had
Enter-to-next-field navigation; this one doesn't), pressing Enter inside any
text input in `#detail-form` also triggers native form submission by
default browser behavior — same GET-to-current-URL fallback, different
trigger.

## Fix

Two changes, both inside `initDetailPanel()`:

1. **Guard the `btn-save` click branch** with `e.preventDefault()` before
   calling `handleSave()`.
2. **Add a `submit` listener on `document`**, scoped to `#detail-form`,
   that calls `e.preventDefault()` and `handleSave()`. This is the more
   robust fix — it catches *any* path to native submission (Enter key,
   future buttons, accessibility tools that trigger submit programmatically)
   rather than only the one button click. The click-handler guard stays in
   as well; it's redundant once the submit listener exists, but costs
   nothing and documents intent at the point of the click.

`btn-new` and `btn-discard` are `type: button` in `forms.yaml` (not
`submit`), so they were never part of this bug and needed no changes.

---

## Change 1 — Guard the Save click handler

### BEFORE

```javascript
    if (e.target.classList.contains('detail-close-button')) handleDiscard();
    if (e.target.classList.contains('btn-save'))            handleSave();
    if (e.target.classList.contains('btn-new'))             handleNew();
    if (e.target.classList.contains('btn-discard'))         handleDiscard();
```

### AFTER

```javascript
    if (e.target.classList.contains('detail-close-button')) handleDiscard();

    // btn-save is type="submit" with form="detail-form" (see forms.yaml) so
    // clicking it also triggers native form submission. Without preventDefault
    // here, the browser's native GET-to-current-URL submission races the
    // fetch() in handleSave() and wins, since nothing else stops it.
    if (e.target.classList.contains('btn-save')) {
      e.preventDefault();
      handleSave();
    }
    if (e.target.classList.contains('btn-new'))             handleNew();
    if (e.target.classList.contains('btn-discard'))         handleDiscard();
```

### Why

Stops the click itself from triggering native submission. On its own this
would have fixed the observed bug (clicking Save), but not the Enter-key
path, hence Change 2.

---

## Change 2 — Add a submit listener as the primary fix

### BEFORE

*(no submit listener exists anywhere in the file — confirmed via
`getEventListeners(document).submit` returning `undefined` in DevTools)*

```javascript
  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const panel = getPanel();
    if (!panel?.classList.contains('active')) return;

    // Alt+S — Save and close
    if (e.altKey && e.key === 's') { e.preventDefault(); handleSave(); }
    // Alt+N — Save and new
    if (e.altKey && e.key === 'n') { e.preventDefault(); handleNew(); }
    // Alt+X or Escape — Discard and close
    if ((e.altKey && e.key === 'x') || e.key === 'Escape') { e.preventDefault(); handleDiscard(); }
  });
```

### AFTER

```javascript
  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const panel = getPanel();
    if (!panel?.classList.contains('active')) return;

    // Alt+S — Save and close
    if (e.altKey && e.key === 's') { e.preventDefault(); handleSave(); }
    // Alt+N — Save and new
    if (e.altKey && e.key === 'n') { e.preventDefault(); handleNew(); }
    // Alt+X or Escape — Discard and close
    if ((e.altKey && e.key === 'x') || e.key === 'Escape') { e.preventDefault(); handleDiscard(); }
  });

  // Safety net: catch any native form submission (e.g. pressing Enter in a
  // text input, which submits the nearest form by default browser behavior)
  // that isn't already intercepted by the btn-save click handler above.
  // Without this, Enter-to-submit falls back to a GET on the current URL
  // with form fields as query params, identical to the btn-save race bug.
  document.addEventListener('submit', (e) => {
    if (e.target.id === 'detail-form') {
      e.preventDefault();
      handleSave();
    }
  });
```

### Why

This is the architecturally correct fix — intercepting at the `submit`
event level catches every path to native submission, not just one button.
Scoped to `e.target.id === 'detail-form'` so it doesn't interfere with any
other form that might exist on the page (e.g. a future contacts or tasks
form using a different id, or the login form on a different page — though
this script only loads where `#detail-panel-container` exists).

---

## Change 3 — Read `err.message` instead of `err.detail`

### BEFORE

```javascript
    } else {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      alert(err.detail || 'Save failed');
      return null;
    }
```

### AFTER

```javascript
    } else {
      // crew.py returns {"success": false, "message": "..."} on proc
      // rejection (duplicate name, not found, etc.) — read message, not
      // detail, or this always falls back to the generic string below.
      const err = await res.json().catch(() => ({ message: res.statusText }));
      alert(err.message || 'Save failed');
      return null;
    }
```

### Why

`crew.py`'s save/delete routes (prior session) return
`{"success": false, "message": "..."}` on proc-rejected saves — there is no
`detail` key. As originally written, `err.detail` would always be
`undefined`, so every proc rejection (duplicate name, not found, etc.)
surfaced as the generic `'Save failed'` fallback instead of the proc's
actual human-readable message. This directly satisfies the "Felipe should
see what went wrong without checking logs" requirement from the prior
session — now the real message reaches the alert.

Note: the `err.message` read inside the JS-level `catch` block further down
(network/parse failures, a standard JS `Error` object) is unrelated and was
already correct — only the proc-rejection branch needed this change.

## Verification steps

1. Reload `/crew?role=captain`.
2. Open DevTools Console, run `getEventListeners(document).submit` — should
   now show one listener (was `undefined` before this fix).
3. Click "+ Add Project", fill in Name/Type/Status, click Save.
4. **Confirm in the Network tab:** request should be
   `POST /crew/projects/save` with `Content-Type: application/json`, not a
   GET with query params on `/crew`.
5. **Confirm the URL bar does not change** — no `?name=...&type_id=...`
   appended to `/crew`.
6. Repeat using Enter key instead of clicking Save (focus a field, press
   Enter) — same expected behavior as step 4–5.
7. Confirm the new project appears in the grid and the panel closes
   (`handleSave()` calls `hidePanel()` on success).
8. Test a duplicate name to confirm the `{success: false, message}` path
   from the `crew.py` proc-call changes surfaces via the `alert()` in
   `saveForm()`'s failure branch — this was already wired correctly in this
   file (`alert(err.detail || 'Save failed')`), but it's worth confirming
   end-to-end now that both halves (backend proc call, frontend form
   submission) are fixed.

## Note on payload key mismatch (now fixed — see Change 3 above)

`saveForm()`'s failure branch originally read `err.detail`, but `crew.py`
returns `{"success": false, "message": "..."}` — no `detail` key. This was
caught while drafting this changedoc and fixed in the same pass (Change 3)
rather than left as a follow-up, since it was a one-line read with no open
design decision: `crew.py`'s response contract was already settled last
session.
