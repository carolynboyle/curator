# Curator UI Routing Fixes — Summary of Changes

## Overview

Three routing issues fixed to keep board panel interactions on the board instead of redirecting away. The solution uses HTMX for client-side form interception and a shared helper function for DRY panel rendering.

---

## File 1: `_panel.html`

**Purpose:** Template for the project detail panel loaded into the board's `#board-detail` container.

**Changes:** Add HTMX attributes to three forms so they POST via HTMX instead of full-page form submission.

### Change 1A: Inline Project Edit Form

**Location:** Line 29 (the `<form>` tag for inline editable fields)

**BEFORE:**
```html
    <form method="post" action="/projects/{{ project.slug }}/edit" id="panel-edit-form">
```

**AFTER:**
```html
    <form method="post" action="/projects/{{ project.slug }}/edit" id="panel-edit-form"
          hx-post="/projects/{{ project.slug }}/edit"
          hx-target="#board-detail"
          hx-swap="innerHTML"
          hx-on::after-request="panelCancelAll()">
```

**Effect:**
- Form posts via HTMX instead of standard form submission
- Response targets `#board-detail` container
- Response swaps as `innerHTML` (replaces old panel with new)
- After successful request, `panelCancelAll()` hides edit inputs and save bar

---

### Change 1B: Add Task Dialog Form

**Location:** Line 201-204 (already correct, just verify)

**VERIFY THESE ATTRIBUTES PRESENT:**
```html
    <form hx-post="/tasks/new-panel/{{ project.slug }}"
      hx-target="#board-detail"
      hx-swap="innerHTML"
      hx-on::after-request="closeAddTaskDialog()">
```

---

### Change 1C: Task Edit Dialog Form

**Location:** Line 246-250 (already correct, just verify)

**VERIFY THESE ATTRIBUTES PRESENT:**
```html
    <form id="task-dialog-form"
      hx-post=""
      hx-target="#board-detail"
      hx-swap="innerHTML"
      hx-on::after-request="closeTaskDialog()">
```

Note: The `hx-post=""` is filled in by JavaScript in the `openTaskDialog()` function (line 311).

---

## File 2: `tasks.py`

**Purpose:** FastAPI routes for task CRUD operations. Contains two panel-specific routes that return panel HTML instead of redirecting.

**Design Pattern:** DRY helper function `_panel_response()` shared by both panel routes.

### Change 2A: Update Docstring Route Map

**Location:** Lines 8-18 (module docstring)

**ADD THESE LINES:**
```python
    POST /tasks/new-panel/{slug}        — create task from panel (HTMX)
    POST /tasks/{id}/edit-panel         — update task from panel (HTMX)
```

---

### Change 2B: Update Imports

**Location:** Line 24

**BEFORE:**
```python
from curator.db import ProjectRepository, TaskRepository
```

**AFTER:**
```python
from curator.db import FileRepository, ProjectRepository, TagRepository, TaskRepository
```

**Why:** The panel helper needs to fetch tags and files alongside tasks.

---

### Change 2C: Add Shared Panel Helper Function

**Location:** After line 29 (before the first route decorator), lines 36-73

**ADD THIS FUNCTION:**
```python
# ---------------------------------------------------------------------------
# Shared panel helper
# ---------------------------------------------------------------------------

async def _panel_response(
    request: Request,
    slug: str,
    proj_repo: ProjectRepository,
    task_repo: TaskRepository,
    db: AsyncDBConnection,
):
    """
    Fetch all data needed to render projects/_panel.html and return the response.

    Used by panel-targeted POST routes (create and update) so both return a
    fresh panel fragment for htmx to swap into #board-detail.

    Args:
        request:   The current request (required by TemplateResponse).
        slug:      Project slug — used to reload the project after a write.
        proj_repo: An already-constructed ProjectRepository.
        task_repo: An already-constructed TaskRepository.
        db:        The current DB connection (used to construct tag/file repos).

    Returns:
        TemplateResponse rendering projects/_panel.html.
    """
    tag_repo = TagRepository(db)
    file_repo = FileRepository(db)

    project = await proj_repo.get_by_slug(slug)

    return templates.TemplateResponse(
        request=request,
        name="projects/_panel.html",
        context={
            "project": project,
            "tasks": await task_repo.get_tree_for_project(project["id"]),
            "tags": await tag_repo.get_for_project(project["id"]),
            "files": await file_repo.get_for_project(project["id"]),
            "subprojects": await proj_repo.get_subprojects(project["id"]),
            "status_options": await proj_repo.get_status_options(),
            "type_options": await proj_repo.get_type_options(),
            "parent_options": await proj_repo.get_parent_options(),
            "status_task_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
        },
    )
```

**Design Benefit:** Single source of truth for panel rendering. Both panel routes use this helper, eliminating duplication.

---

### Change 2D: Add Create Task from Panel Route

**Location:** After `update_task()` (around line 254), new lines 254-283

**ADD THIS ROUTE:**
```python
@router.post("/new-panel/{slug}", response_class=HTMLResponse)
async def create_task_panel(
    slug: str,
    request: Request,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    parent_id: int | None = Form(None),
    links: str = Form(""),
    sort_order: int = Form(0),
    db: AsyncDBConnection = Depends(get_db),
):
    proj_repo = ProjectRepository(db)
    project = await proj_repo.get_by_slug(slug)

    task_repo = TaskRepository(db)
    await task_repo.create(
        {
            "project_id": project["id"],
            "description": description,
            "status_id": status_id,
            "priority_id": priority_id,
            "parent_id": parent_id,
            "links": links,
            "sort_order": sort_order,
        }
    )
    return await _panel_response(request, slug, proj_repo, task_repo, db)
```

**Behavior:**
- Creates the task
- Calls `_panel_response()` to fetch updated project data
- Returns rendered panel HTML for HTMX to swap into `#board-detail`
- Panel shows new task immediately

---

### Change 2E: Add Update Task from Panel Route

**Location:** After `create_task_panel()` (around line 286), new lines 286-310

**ADD THIS ROUTE:**
```python
@router.post("/{task_id}/edit-panel", response_class=HTMLResponse)
async def update_task_panel(
    task_id: int,
    request: Request,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    is_terminal: bool = Form(False),
    parent_id: int | None = Form(None),
    links: str = Form(""),
    sort_order: int = Form(0),
    project_slug: str = Form(...),
    db: AsyncDBConnection = Depends(get_db),
):
    task_repo = TaskRepository(db)
    await task_repo.update(
        task_id,
        {
            "description": description,
            "status_id": status_id,
            "priority_id": priority_id,
            "is_terminal": is_terminal,
            "parent_id": parent_id,
            "links": links,
            "sort_order": sort_order,
        },
    )
    proj_repo = ProjectRepository(db)
    return await _panel_response(request, project_slug, proj_repo, task_repo, db)
```

**Behavior:**
- Updates the task (including `is_terminal` flag based on status)
- Calls `_panel_response()` to fetch updated project data
- Returns rendered panel HTML for HTMX to swap into `#board-detail`
- Panel shows updated task immediately

---

## File 3: `projects.py`

**Purpose:** Project repository with database operations.

**Status:** ✓ **NO CHANGES NEEDED**

This file contains the `ProjectRepository` class which is used by the routes. The HTMX detection and panel response logic happens in the route layer, not the repository layer. No modifications required.

---

## Architecture & Design Pattern

### HTMX-Based Navigation

**Flow for inline edits:**
1. User clicks edit field → JS shows input
2. User clicks Save → HTMX intercepts form POST
3. HTMX POSTs to `/projects/{slug}/edit` with `HX-Request: true` header
4. Route checks header and returns panel HTML instead of redirecting
5. HTMX swaps response into `#board-detail`
6. `panelCancelAll()` callback hides edit inputs
7. User stays on board with refreshed data

### DRY Panel Helper

**Why:** Both panel routes need identical context preparation (project, tasks, tags, files, subprojects, all options).

**Solution:** `_panel_response()` helper encapsulates this logic once.

**Benefits:**
- Single source of truth for panel rendering
- Easy to modify if panel data needs change
- No code duplication between routes
- Clear separation of concern

### HTMX Attributes Explained

| Attribute | Purpose |
|-----------|---------|
| `hx-post` | Route to POST to (intercepted HTMX) |
| `hx-target` | DOM element to target with response |
| `hx-swap` | How to swap response (innerHTML replaces content) |
| `hx-on::after-request` | JS callback after request completes (close dialog/hide edit) |

---

## Summary of Patterns

### 1. HTMX Request Detection
```python
if request.headers.get("hx-request") == "true":
    # HTMX path: return panel HTML
    return templates.TemplateResponse(...)
else:
    # Regular form path: redirect (backward compatible)
    return RedirectResponse(url=..., status_code=303)
```

### 2. Panel Data Fetching
```python
# Centralized in _panel_response()
project = await proj_repo.get_by_slug(slug)
tasks = await task_repo.get_tree_for_project(project["id"])
tags = await tag_repo.get_for_project(project["id"])
# ... etc
```

### 3. Form Interception via HTMX
```html
<form hx-post="/endpoint" hx-target="#board-detail" hx-swap="innerHTML">
```

---

## Backward Compatibility

✓ **Fully backward compatible**

- Regular form submissions (non-HTMX) still work and redirect as before
- Standalone form pages unchanged
- No breaking changes to existing routes
- HTMX detection is additive (doesn't affect non-HTMX clients)

---

## Testing Checklist

Use the `curator_ui_checklist.xlsx` spreadsheet:

1. [ ] Click project description → Save → stays on board, refreshes
2. [ ] Click project status → Save → stays on board, refreshes
3. [ ] Click "+ Add" task → fill form → Save → stays on board, new task appears
4. [ ] Double-click task → change status → Save → stays on board, status updates
5. [ ] Double-click task → change priority → Save → stays on board, priority updates
6. [ ] Click "Full edit" project → redirects to full form (intentional)
7. [ ] Click task full edit (✎) → redirects to full form (intentional)
8. [ ] Click delete → confirms and redirects to /projects/ (intentional)

---

## Files Modified Summary

```
_panel.html
  - 1 change: Add HTMX attributes to inline edit form (line 29)

tasks.py
  - 1 change: Update imports to include FileRepository, TagRepository (line 24)
  - 1 change: Update docstring route map (lines 8-18)
  - 1 addition: _panel_response() helper function (lines 36-73)
  - 1 addition: create_task_panel() route (lines 254-283)
  - 1 addition: update_task_panel() route (lines 286-310)

projects.py
  - No changes required
```

