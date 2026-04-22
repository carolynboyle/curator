# Next Steps for Curator UI Testing

## What Was Fixed (In This Session)

Three routing issues on the board panel that caused unwanted navigation:

1. **Inline project edit** — Now stays on board, refreshes panel in place
2. **Add task from dialog** — Now stays on board, adds task and refreshes
3. **Edit task status/priority** — Now stays on board, updates and refreshes

All three required either:
- Adding HTMX attributes to forms
- Creating new route variants that return panel HTML instead of redirecting
- Updating existing routes to detect HTMX requests and behave differently

---

## How to Deploy These Changes

**Status:** Code is already implemented in your repo. Refer to `CHANGES_SUMMARY.md` and `IMPLEMENTATION_VERIFIED.md` for exact details.

On your dev machine (`mx`):
1. Verify the three files are updated:
   - **_panel.html**: HTMX attributes on inline edit form (line 29-33)
   - **tasks.py**: New `_panel_response()` helper + two panel routes (`create_task_panel`, `update_task_panel`)
2. Commit and push:
   ```bash
   git add _panel.html tasks.py
   git commit -m "Fix board panel navigation — HTMX for inline edits and task dialogs"
   git push
   ```

Then on `wcyjvs2`:
```bash
cd ~/curator
git pull
systemctl restart curator  # or however you restart it
```

---

## Testing the Fixes

Use the checklist from `ROUTING_FIXES.md` to verify each action:

1. Inline edit → Save (should stay on board)
2. Add task → Save (should stay on board)
3. Edit task status/priority → Save (should stay on board)
4. Full edit buttons (should still go to form pages)
5. File operations (should still work as before)

As you test, log any unexpected behavior in your checklist spreadsheet.

---

## What Remains from Tomorrow's Queue

From your session notes:

1. **Walk the board UI and identify every action that doesn't return to the board correctly**
   - Use the checklist spreadsheet to track results
   - The three main routing issues should now be fixed

2. **Check that the `notes` field is properly wired in everywhere**
   - This was predated by the SQL externalization
   - May have been missed in query refactoring

3. **Run fletcher to update the manifest**
   - After all commits from this session

---

## Summary of File Changes

See `CHANGES_SUMMARY.md` for detailed before/after. Quick summary:

```
_panel.html
- Line 29-33: Added hx-post, hx-target, hx-swap, hx-on::after-request to inline edit form

tasks.py
- Line 24: Added FileRepository, TagRepository to imports
- Lines 8-18: Updated docstring route map with two new HTMX routes
- Lines 36-73: Added _panel_response() helper (DRY panel rendering)
- Lines 254-283: Added create_task_panel() route (uses helper)
- Lines 286-310: Added update_task_panel() route (uses helper)
```

**Design note:** Both panel routes use a shared `_panel_response()` helper to eliminate code duplication and provide a single source of truth for panel data fetching.

---

## Key Patterns Used

### Pattern 1: HTMX Form Attributes
Add to any form that should stay on the board:
```html
<form hx-post="/endpoint" hx-target="#board-detail" hx-swap="innerHTML" hx-on::after-request="callbackFn()">
```

### Pattern 2: DRY Panel Helper
For routes that return panel HTML, use a shared helper:
```python
async def _panel_response(request, slug, proj_repo, task_repo, db):
    """Fetch all panel data and render template."""
    # Single source of truth for panel rendering
    return templates.TemplateResponse(...)

# Both routes call the same helper
return await _panel_response(request, slug, proj_repo, task_repo, db)
```

### Pattern 3: Panel Data Context
Panel always needs the same context variables:
- project (fresh from DB)
- tasks, tags, files, subprojects
- All status/priority/parent options

Centralize this in the helper to avoid duplication.

### Future Board Navigation Issues

If you encounter other board actions that redirect away:

1. Check if they're intentional (full forms, delete operations)
2. If they should stay on board:
   - Add HTMX attributes to the form
   - Create a panel-specific route variant that returns panel HTML
   - Use the `_panel_response()` helper to keep code DRY

This pattern keeps board interactions smooth while preserving standalone form workflows.
