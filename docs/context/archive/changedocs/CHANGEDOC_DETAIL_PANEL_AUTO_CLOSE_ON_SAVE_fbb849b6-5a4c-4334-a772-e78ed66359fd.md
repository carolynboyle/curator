# Changedoc: Auto-close Detail Panel on Save Success

## File
`static/js/detail-panel.js`

## What Changed
After a successful project save, the detail panel automatically closes and the hero image becomes visible again. This provides clear visual feedback that the save succeeded.

## Why
UX signal: save succeeds → panel closes → back to hero view. Confirms the operation worked and returns user to the previous state naturally.

---

## BEFORE
```javascript
  // Save button click handler
  saveBtn.addEventListener('click', async () => {
    const formData = new FormData(detailForm);
    const body = {
      name: formData.get('name'),
      type_id: formData.get('type_id') || null,
      status_id: formData.get('status_id') || null,
      description: formData.get('description') || null,
    };

    try {
      const resp = await fetch(`/crew/projects/${projectId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (resp.ok) {
        const updated = await resp.json();
        populateFormFromRecord(updated);
        // Panel stayed open; user had to click X to close
      } else {
        const error = await resp.text();
        alert(`Save failed: ${error}`);
      }
    } catch (err) {
      alert(`Save error: ${err.message}`);
    }
  });
```

## AFTER
```javascript
  // Save button click handler
  saveBtn.addEventListener('click', async () => {
    const formData = new FormData(detailForm);
    const body = {
      name: formData.get('name'),
      type_id: formData.get('type_id') || null,
      status_id: formData.get('status_id') || null,
      description: formData.get('description') || null,
    };

    try {
      const resp = await fetch(`/crew/projects/${projectId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (resp.ok) {
        const updated = await resp.json();
        populateFormFromRecord(updated);
        
        // Auto-close detail panel as visual success signal
        detailPanel.classList.remove('active');
        heroImage.classList.remove('hidden');
      } else {
        const error = await resp.text();
        alert(`Save failed: ${error}`);
      }
    } catch (err) {
      alert(`Save error: ${err.message}`);
    }
  });
```

---

## What Changed Specifically
- After `populateFormFromRecord(updated)`, added two lines:
  - `detailPanel.classList.remove('active');` — hides the detail form
  - `heroImage.classList.remove('hidden');` — shows the hero image
- This mirrors the behavior when the close (X) button is clicked
- Only happens on successful save (resp.ok === true)
- If save fails, alert appears and panel stays open so user can fix and retry

---

## Testing
1. Open a project detail panel (click `⋯`)
2. Edit a field (e.g., change name)
3. Click Save
4. Verify: detail panel closes, hero image becomes visible again
5. Verify: the saved value persists (reload page to confirm it was actually saved)
