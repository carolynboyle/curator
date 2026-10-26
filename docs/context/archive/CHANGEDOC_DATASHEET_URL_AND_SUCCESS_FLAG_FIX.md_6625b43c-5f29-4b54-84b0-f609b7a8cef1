# CHANGEDOC — Datasheet Save/Delete URLs + Success-Flag Bug Fix

**Status:** Ready to apply — Python/JS only, no SQL, no pgAdmin step.

## Summary

Three fixes, one changedoc, because they share a root cause (wrong
assumption about how failure is signaled by the API):

1. `datasheet.js` — save/delete URLs point at `/api/{entity}/...`,
   which doesn't exist. Real routes are `/crew/{entity}/...`.
2. `datasheet.js` — `saveRow()` checks `resp.ok` (HTTP status) to decide
   success/failure. The actual API contract returns failures as HTTP
   200 with `{"success": false, "message": "...", "data": ...}` in the
   body (confirmed in `projects.py`'s `save_new_project`/`save_project`
   routes). `resp.ok` is always `true` for these responses, so a
   rejected save (duplicate name, validation failure, etc.) would be
   silently treated as successful.
3. `detail-panel.js` — same bug, already shipped. `saveForm()` checks
   `res.ok` instead of `body.success`. This is a **found latent bug in
   already-shipped code**, not a new gap — flagging per project rules
   rather than fixing without a paper trail.

Delete is different: `delete_project` returns bare HTTP 204 (no body)
on success, and `{"success": false, "message": "..."}` at HTTP 200 on
failure. So delete's fix is a status-code check (204 vs. everything
else), not a body-parsing check — `resp.ok` alone would incorrectly
treat a 200-with-failure delete response as success.

---

## File 1 — `static/js/datasheet.js`

### BEFORE

```javascript
    // -------------------------------------------------------------------------
    // Save a row to the server
    // NOTE: URLs below (/api/{entity}/...) do not exist in the current app —
    // real routes are /crew/{entity}/... This is a known gap, not addressed
    // in this changedoc. Saving will 404 until the URL fix lands.
    // -------------------------------------------------------------------------
    async function saveRow(row) {
        const data = row.getData();
        const isNew = !data.id;

        // Don't save a new row with no content — just delete it
        const firstEditable = columns.find(c => c.editor);
        if (isNew && firstEditable && !data[firstEditable.field]) {
            row.delete();
            return true;
        }

        const url = isNew
            ? `/api/${entity}/save`
            : `/api/${entity}/${data.id}/save`;

        // Only send editable columns
        const editableFields = columns
            .filter(c => c.editor && c.field !== 'id')
            .map(c => c.field);

        const payload = {};
        editableFields.forEach(f => { payload[f] = data[f] ?? null; });

        // For new rows, include the parent FK with its explicit field name.
        // parentField replaces the old string-guessing heuristic that produced
        // task_id instead of project_id for the Tasks entity.
        if (isNew && parentField && queryParams) {
            payload[parentField] = queryParams;
        }

        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            alert(err.detail || 'Save failed');
            return false;
        }

        const saved = await resp.json();
        row.update(saved);
        return true;
    }

    // -------------------------------------------------------------------------
    // Delete a row from the server
    // NOTE: Same URL gap as saveRow above.
    // -------------------------------------------------------------------------
    async function deleteRow(row) {
        const id = row.getData().id;
        if (!id) { row.delete(); return; }

        if (!confirm('Delete this row?')) return;

        const resp = await fetch(`/api/${entity}/${id}`, { method: 'DELETE' });
        if (resp.ok) {
            row.delete();
        } else {
            alert('Delete failed');
        }
    }
```

### AFTER

```javascript
    // -------------------------------------------------------------------------
    // Save a row to the server
    //
    // Error response contract (see projects.py save_new_project /
    // save_project): success = flat record at HTTP 200; failure =
    // {"success": false, "message": "...", "data": ...} ALSO at HTTP 200.
    // This means resp.ok is true in both cases — the only reliable success
    // check is body.success !== false. Matches detail-panel.js's corrected
    // saveForm() below; keep both in sync if this contract ever changes.
    // -------------------------------------------------------------------------
    async function saveRow(row) {
        const data = row.getData();
        const isNew = !data.id;

        // Don't save a new row with no content — just delete it
        const firstEditable = columns.find(c => c.editor);
        if (isNew && firstEditable && !data[firstEditable.field]) {
            row.delete();
            return true;
        }

        const url = isNew
            ? `/crew/${entity}/save`
            : `/crew/${entity}/${data.id}/save`;

        // Only send editable columns
        const editableFields = columns
            .filter(c => c.editor && c.field !== 'id')
            .map(c => c.field);

        const payload = {};
        editableFields.forEach(f => { payload[f] = data[f] ?? null; });

        // For new rows, include the parent FK with its explicit field name.
        // parentField replaces the old string-guessing heuristic that produced
        // task_id instead of project_id for the Tasks entity.
        if (isNew && parentField && queryParams) {
            payload[parentField] = queryParams;
        }

        let body;
        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            body = await resp.json();
        } catch (err) {
            alert('Save error: ' + err.message);
            return false;
        }

        if (body.success === false) {
            alert(body.message || 'Save failed');
            return false;
        }

        row.update(body);
        return true;
    }

    // -------------------------------------------------------------------------
    // Delete a row from the server
    //
    // Error response contract (see projects.py delete_project): success =
    // bare HTTP 204, no body; failure = {"success": false, "message": "..."}
    // at HTTP 200. Unlike save, there's no body to check on success (204
    // has none) — so delete's check is on status code, not body.success.
    // -------------------------------------------------------------------------
    async function deleteRow(row) {
        const id = row.getData().id;
        if (!id) { row.delete(); return; }

        if (!confirm('Delete this row?')) return;

        let resp;
        try {
            resp = await fetch(`/crew/${entity}/${id}`, { method: 'DELETE' });
        } catch (err) {
            alert('Delete error: ' + err.message);
            return;
        }

        if (resp.status === 204) {
            row.delete();
            return;
        }

        const body = await resp.json().catch(() => ({ message: resp.statusText }));
        alert(body.message || 'Delete failed');
    }
```

### Why

- `/api/{entity}/...` never existed as a route — every real save/delete
  route lives under `/crew/{entity}/...` (confirmed directly against
  `projects.py`). Saves and deletes were 404ing silently before this fix.
- The API's actual failure contract (HTTP 200 + `success: false`) means
  `resp.ok` can't distinguish success from failure for saves — it's
  `true` either way. Checking `body.success === false` explicitly is the
  only correct check, and matches what your project memory documents as
  the intended contract.
- Delete is asymmetric: success is bare 204 (no JSON body to parse),
  failure is 200 with a body. The check has to branch on status code
  first, not attempt `resp.json()` unconditionally (which would throw
  on the empty 204 body).
- Wrapped both in `try/catch` for network failures (server unreachable,
  connection dropped) — previously unhandled, would have thrown an
  uncaught promise rejection instead of a user-visible alert.

---

## File 2 — `static/js/detail-panel.js`

### BEFORE

```javascript
async function saveForm() {
  const form = getForm();
  if (!form) return null;

  const entity   = form.dataset.entity;
  const recordId = form.dataset.id;
  const isNew    = !recordId;

  const formData = new FormData(form);
  const data     = Object.fromEntries(formData);

  const url = isNew
    ? `/crew/${entity}/save`
    : `/crew/${entity}/${recordId}/save`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (res.ok) {
      const saved = await res.json();
      // Update form id to the newly saved record's id
      form.dataset.id = saved.id;
      const panel = getPanel();
      if (panel) panel.dataset.id = saved.id;
      return saved;
    } else {
      // crew.py returns {"success": false, "message": "..."} on proc
      // rejection (duplicate name, not found, etc.) — read message, not
      // detail, or this always falls back to the generic string below.
      const err = await res.json().catch(() => ({ message: res.statusText }));
      alert(err.message || 'Save failed');
      return null;
    }
  } catch (err) {
    console.error('Save error:', err);
    alert('Save error: ' + err.message);
    return null;
  }
}
```

### AFTER

```javascript
async function saveForm() {
  const form = getForm();
  if (!form) return null;

  const entity   = form.dataset.entity;
  const recordId = form.dataset.id;
  const isNew    = !recordId;

  const formData = new FormData(form);
  const data     = Object.fromEntries(formData);

  const url = isNew
    ? `/crew/${entity}/save`
    : `/crew/${entity}/${recordId}/save`;

  try {
    const res  = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const body = await res.json();

    // FOUND BUG (fixed here): this used to check res.ok, but crew.py's
    // proc-backed save routes return failures as {"success": false,
    // "message": "...", "data": ...} at HTTP 200 — not a non-2xx status.
    // res.ok was always true, so a rejected save (duplicate name, etc.)
    // was silently treated as successful: form.dataset.id got set to
    // undefined (saved.id on a failure body), and the caller proceeded
    // as if the record had saved. The only reliable check is
    // body.success !== false, matching datasheet.js's saveRow().
    if (body.success === false) {
      alert(body.message || 'Save failed');
      return null;
    }

    // Update form id to the newly saved record's id
    form.dataset.id = body.id;
    const panel = getPanel();
    if (panel) panel.dataset.id = body.id;
    return body;
  } catch (err) {
    console.error('Save error:', err);
    alert('Save error: ' + err.message);
    return null;
  }
}
```

### Why

- **This is a found bug in already-shipped code**, not part of the
  datasheet URL fix — flagged explicitly per "never silently fix
  problems." Before this fix, a rejected save (e.g. duplicate project
  name) was silently accepted by the UI: `res.ok` is `true` for a 200
  response regardless of body content, so the `if (res.ok)` branch ran,
  `saved.id` was `undefined` (since the failure body has no `id` key),
  and the form/panel were left thinking a save succeeded when it hadn't.
- Fix mirrors `datasheet.js`'s corrected `saveRow()` exactly — same
  contract, same check, so both files can never drift back into
  disagreement about how to read a save response.

---

## Not in scope for this changedoc

- `+ Add Task` button wiring — deferred to the Tasks UI wiring
  changedoc, now that the nested master-detail design doc
  (`nested_master_detail_design.md`) has settled what "Add" actually
  does for Tasks (opens the nested detail form, not an inline Tabulator
  row).
- `add_url` / `data-add-url` on `_datasheet_with_header.html` — left
  as-is for now; whether it's still needed depends on how the Tasks tab
  wiring changedoc wires `+ Add Task` to the nested form. Revisit then.
- Any other entity's save/delete routes beyond what's already confirmed
  in `projects.py` — assumed consistent (task/contact/organization
  routes should follow the same `call_proc_and_refetch` /
  `delete_via_proc` helper pattern in `deps.py`), but not individually
  re-verified here.

## Testing notes

- No existing test file covers `datasheet.js` or `detail-panel.js`
  directly (these are browser JS, not part of the pytest suite).
  Manual verification: open a Project's Tasks tab (once wired), edit a
  task inline, confirm it round-trips through `/crew/tasks/{id}/save`
  and shows updated values without a page reload. Try a save that
  should be rejected by the proc (e.g. blank required field, once
  validation exists) and confirm the alert fires instead of a false
  "success."
