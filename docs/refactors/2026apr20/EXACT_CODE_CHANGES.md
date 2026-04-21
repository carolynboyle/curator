# Curator UI Routing Fixes — Exact Code to Apply

This document shows the exact lines to change in three files.

---

## File 1: `_panel.html`

**Location:** Line 29 (the `<form>` tag starting the inline edit form)

**REPLACE THIS:**
```html
    <form method="post" action="/projects/{{ project.slug }}/edit" id="panel-edit-form">
```

**WITH THIS:**
```html
    <form method="post" action="/projects/{{ project.slug }}/edit" id="panel-edit-form"
          hx-post="/projects/{{ project.slug }}/edit"
          hx-target="#board-detail"
          hx-swap="innerHTML"
          hx-on::after-request="panelCancelAll()">
```

---

## File 2: `projects_routes.py`

**Location:** Lines 173-197 (the entire `update_project` function and its decorator)

**REPLACE THESE LINES:**
```python
@router.post("/{slug}/edit")
async def update_project(
    slug: str,
    name: str = Form(...),
    description: str = Form(""),
    status_id: int = Form(...),
    type_id: int | None = Form(None),
    parent_id: int | None = Form(None),
    target_date: str | None = Form(None),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    await repo.update(
        slug,
        {
            "name": name,
            "description": description or None,
            "status_id": status_id,
            "type_id": type_id,
            "parent_id": parent_id,
            "target_date": target_date or None,
        },
    )
    return RedirectResponse(url=f"/projects/{slug}", status_code=303)
```

**WITH THIS:**
```python
@router.post("/{slug}/edit")
async def update_project(
    slug: str,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    status_id: int = Form(...),
    type_id: int | None = Form(None),
    parent_id: int | None = Form(None),
    target_date: str | None = Form(None),
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    await repo.update(
        slug,
        {
            "name": name,
            "description": description or None,
            "status_id": status_id,
            "type_id": type_id,
            "parent_id": parent_id,
            "target_date": target_date or None,
        },
    )
    
    # If HTMX request (from board panel), return updated panel
    if request.headers.get("hx-request") == "true":
        project = await repo.get_by_slug(slug)
        task_repo = TaskRepository(db)
        tag_repo = TagRepository(db)
        file_repo = FileRepository(db)

        tasks = await task_repo.get_tree_for_project(project["id"])
        tags = await tag_repo.get_for_project(project["id"])
        files = await file_repo.get_for_project(project["id"])
        subprojects = await repo.get_subprojects(project["id"])
        status_options = await repo.get_status_options()
        type_options = await repo.get_type_options()
        parent_options = await repo.get_parent_options()
        status_task_options = await task_repo.get_status_options()
        priority_options = await task_repo.get_priority_options()

        return templates.TemplateResponse(
            request=request,
            name="projects/_panel.html",
            context={
                "project": project,
                "tasks": tasks,
                "tags": tags,
                "files": files,
                "subprojects": subprojects,
                "status_options": status_options,
                "type_options": type_options,
                "parent_options": parent_options,
                "status_task_options": status_task_options,
                "priority_options": priority_options,
            },
        )
    
    # Regular form submission (from standalone edit page)
    return RedirectResponse(url=f"/projects/{slug}", status_code=303)
```

**Note:** The imports at the top of `projects_routes.py` are already correct—no changes needed there.

---

## File 3: `tasks_routes.py`

### Change 3A: Update the imports

**Location:** Line 24 (the import statement for repositories)

**REPLACE THIS:**
```python
from curator.db import ProjectRepository, TaskRepository
```

**WITH THIS:**
```python
from curator.db import FileRepository, ProjectRepository, TagRepository, TaskRepository
```

---

### Change 3B: Update the docstring route map

**Location:** Lines 8-16 (the docstring at the top of the file)

**REPLACE THIS:**
```python
"""
curator.web.routes.tasks - Task CRUD routes.

Tasks always belong to a project. The project slug is carried through
all routes so we can redirect back to the project detail page after
create, edit, or delete.

Route map:
    GET  /tasks/project/{slug}          — list tasks for a project
    GET  /tasks/new/{slug}              — new task form
    POST /tasks/new/{slug}              — create task
    GET  /tasks/{id}/edit               — edit form
    POST /tasks/{id}/edit               — update task
    POST /tasks/{id}/delete             — delete task (raises if children)
    POST /tasks/{id}/force-delete       — delete task and all descendants
"""
```

**WITH THIS:**
```python
"""
curator.web.routes.tasks - Task CRUD routes.

Tasks always belong to a project. The project slug is carried through
all routes so we can redirect back to the project detail page after
create, edit, or delete.

Route map:
    GET  /tasks/project/{slug}          — list tasks for a project
    GET  /tasks/new/{slug}              — new task form
    POST /tasks/new/{slug}              — create task
    GET  /tasks/{id}/edit               — edit form
    POST /tasks/{id}/edit               — update task
    POST /tasks/{id}/delete             — delete task (raises if children)
    POST /tasks/{id}/force-delete       — delete task and all descendants
    POST /tasks/new-panel/{slug}        — create task from panel (HTMX)
    POST /tasks/{id}/edit-panel         — update task from panel (HTMX)
"""
```

---

### Change 3C: Add the new route for creating tasks from the panel

**Location:** After line 219 (after the `force_delete_task` function)

**ADD THIS NEW FUNCTION:**
```python


@router.post("/new-panel/{slug}")
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
    config=Depends(get_config),
):
    """Create task from panel and return updated panel (HTMX)."""
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
    
    # Return updated panel
    tasks = await task_repo.get_tree_for_project(project["id"])
    tag_repo = TagRepository(db)
    file_repo = FileRepository(db)

    tags = await tag_repo.get_for_project(project["id"])
    files = await file_repo.get_for_project(project["id"])
    subprojects = await proj_repo.get_subprojects(project["id"])
    status_options = await proj_repo.get_status_options()
    type_options = await proj_repo.get_type_options()
    parent_options = await proj_repo.get_parent_options()
    status_task_options = await task_repo.get_status_options()
    priority_options = await task_repo.get_priority_options()

    return templates.TemplateResponse(
        request=request,
        name="projects/_panel.html",
        context={
            "project": project,
            "tasks": tasks,
            "tags": tags,
            "files": files,
            "subprojects": subprojects,
            "status_options": status_options,
            "type_options": type_options,
            "parent_options": parent_options,
            "status_task_options": status_task_options,
            "priority_options": priority_options,
        },
    )


@router.post("/{task_id}/edit-panel")
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
    config=Depends(get_config),
):
    """Update task from panel and return updated panel (HTMX)."""
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
    
    # Return updated panel
    proj_repo = ProjectRepository(db)
    project = await proj_repo.get_by_slug(project_slug)
    
    tasks = await task_repo.get_tree_for_project(project["id"])
    tag_repo = TagRepository(db)
    file_repo = FileRepository(db)

    tags = await tag_repo.get_for_project(project["id"])
    files = await file_repo.get_for_project(project["id"])
    subprojects = await proj_repo.get_subprojects(project["id"])
    status_options = await proj_repo.get_status_options()
    type_options = await proj_repo.get_type_options()
    parent_options = await proj_repo.get_parent_options()
    status_task_options = await task_repo.get_status_options()
    priority_options = await task_repo.get_priority_options()

    return templates.TemplateResponse(
        request=request,
        name="projects/_panel.html",
        context={
            "project": project,
            "tasks": tasks,
            "tags": tags,
            "files": files,
            "subprojects": subprojects,
            "status_options": status_options,
            "type_options": type_options,
            "parent_options": parent_options,
            "status_task_options": status_task_options,
            "priority_options": priority_options,
        },
    )
```

---

## Verification Checklist

After applying all changes:

- [ ] `_panel.html` line 29 has 4 HTMX attributes
- [ ] `projects_routes.py` `update_project()` has `request: Request` parameter
- [ ] `projects_routes.py` `update_project()` has `config=Depends(get_config)` parameter
- [ ] `projects_routes.py` `update_project()` checks `request.headers.get("hx-request")`
- [ ] `tasks_routes.py` imports include `FileRepository` and `TagRepository`
- [ ] `tasks_routes.py` docstring includes two new HTMX routes
- [ ] `tasks_routes.py` has `create_task_panel()` function
- [ ] `tasks_routes.py` has `update_task_panel()` function

---

## Testing

1. On `wcyjvs2`, pull the updated code
2. Restart the curator service
3. Use the checklist spreadsheet to test:
   - Inline edit → Save
   - Add task → Save
   - Edit task status/priority → Save
4. All three should stay on the board and refresh the panel

---

## Backward Compatibility

The changes are fully backward compatible:
- Regular form submissions (from `/projects/{slug}/edit` standalone page) still redirect normally
- Full-page navigation (edit forms, delete) unchanged
- Old code paths unaffected

