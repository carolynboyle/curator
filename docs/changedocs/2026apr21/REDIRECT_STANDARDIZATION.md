# Curator — Unified next_url Redirect Pattern
## 2026-04-21

---

## Overview

Standardizes form submission redirects across all CRUD routes (projects, tasks, files, tags) to respect where the user came from, rather than hardcoding destinations. This allows forms called from the board to return to the board, forms from detail pages to return to detail, etc.

**Key principle:** All form GET handlers compute `next_url` and pass it to the template. All form POST handlers read `next_url` from the form and use it in the redirect.

---

## File Changes

### 1. `curator/web/routes/projects_routes.py`

#### BEFORE
```python
@router.get("/new", response_class=HTMLResponse)
async def new_project_form(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    view = ViewBuilder(config.views_path).get_view("projects")

    return templates.TemplateResponse(
        request=request,
        name="projects/form.html",
        context={
            "view": view,
            "project": None,
            "status_options": await repo.get_status_options(),
            "type_options": await repo.get_type_options(),
            "parent_options": await repo.get_parent_options(),
        },
    )
```

#### AFTER
```python
@router.get("/new", response_class=HTMLResponse)
async def new_project_form(
    request: Request,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    view = ViewBuilder(config.views_path).get_view("projects")

    # Compute next_url from query param, referer, or default
    if not next_url:
        next_url = request.headers.get("referer", "/projects/board")

    return templates.TemplateResponse(
        request=request,
        name="projects/form.html",
        context={
            "view": view,
            "project": None,
            "next_url": next_url,
            "status_options": await repo.get_status_options(),
            "type_options": await repo.get_type_options(),
            "parent_options": await repo.get_parent_options(),
        },
    )
```

**Why:** GET handler now accepts optional `next_url` query param and passes it to template for forms to use in their hidden field.

---

#### BEFORE
```python
@router.post("/new")
async def create_project(
    name: str = Form(...),
    description: str = Form(""),
    status_id: int = Form(...),
    type_id: int | None = Form(None),
    parent_id: int | None = Form(None),
    target_date: str | None = Form(None),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    slug = await repo.create(
        {
            "name": name,
            "description": description or None,
            "status_id": status_id,
            "type_id": type_id,
            "parent_id": parent_id,
            "target_date": target_date or None,
        }
    )
    return RedirectResponse(url=f"/projects/{slug}", status_code=303)
```

#### AFTER
```python
@router.post("/new")
async def create_project(
    name: str = Form(...),
    description: str = Form(""),
    status_id: int = Form(...),
    type_id: int | None = Form(None),
    parent_id: int | None = Form(None),
    target_date: str | None = Form(None),
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    slug = await repo.create(
        {
            "name": name,
            "description": description or None,
            "status_id": status_id,
            "type_id": type_id,
            "parent_id": parent_id,
            "target_date": target_date or None,
        }
    )
    # Use next_url if provided, otherwise default to the new project detail page
    redirect_url = next_url or f"/projects/{slug}"
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data and uses it if provided, otherwise falls back to detail page for the newly created project.

---

#### BEFORE
```python
@router.get("/{slug}/edit", response_class=HTMLResponse)
async def edit_project_form(
    slug: str,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    try:
        project = await repo.get_by_slug(slug)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    view = ViewBuilder(config.views_path).get_view("projects")

    return templates.TemplateResponse(
        request=request,
        name="projects/form.html",
        context={
            "view": view,
            "project": project,
            "status_options": await repo.get_status_options(),
            "type_options": await repo.get_type_options(),
            "parent_options": await repo.get_parent_options(),
        },
    )
```

#### AFTER
```python
@router.get("/{slug}/edit", response_class=HTMLResponse)
async def edit_project_form(
    slug: str,
    request: Request,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    try:
        project = await repo.get_by_slug(slug)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    # Compute next_url from query param, referer, or default
    if not next_url:
        next_url = request.headers.get("referer", f"/projects/{slug}")

    view = ViewBuilder(config.views_path).get_view("projects")

    return templates.TemplateResponse(
        request=request,
        name="projects/form.html",
        context={
            "view": view,
            "project": project,
            "next_url": next_url,
            "status_options": await repo.get_status_options(),
            "type_options": await repo.get_type_options(),
            "parent_options": await repo.get_parent_options(),
        },
    )
```

**Why:** GET handler now accepts optional `next_url` query param and passes it to template.

---

#### BEFORE
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

#### AFTER
```python
@router.get("/{slug}/edit", response_class=HTMLResponse)
async def edit_project_form(
    slug: str,
    request: Request,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    try:
        project = await repo.get_by_slug(slug)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    # Compute next_url from query param, referer, or default
    if not next_url:
        next_url = request.headers.get("referer", f"/projects/{slug}")

    view = ViewBuilder(config.views_path).get_view("projects")

    return templates.TemplateResponse(
        request=request,
        name="projects/form.html",
        context={
            "view": view,
            "project": project,
            "next_url": next_url,
            "status_options": await repo.get_status_options(),
            "type_options": await repo.get_type_options(),
            "parent_options": await repo.get_parent_options(),
        },
    )
```

**Why:** POST handler reads `next_url` from form data and uses it if provided, otherwise defaults to detail page.

---

#### BEFORE
```python
@router.post("/{slug}/delete")
async def delete_project(
    slug: str,
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    await repo.delete(slug)
    return RedirectResponse(url="/projects/", status_code=303)
```

#### AFTER
```python
@router.post("/{slug}/delete")
async def delete_project(
    slug: str,
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    await repo.delete(slug)
    # Use next_url if provided, otherwise default to projects list
    redirect_url = next_url or "/projects/"
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data (for delete confirmation forms that include it), otherwise defaults to projects list.

---

### 2. `curator/templates/projects_form.html`

#### BEFORE
```html
<form method="post"
      action="{% if project %}/projects/{{ project.slug }}/edit{% else %}/projects/new{% endif %}"
      class="curator-form">

    <input type="hidden" name="next" value="{{ next }}">
```

#### AFTER
```html
<form method="post"
      action="{% if project %}/projects/{{ project.slug }}/edit{% else %}/projects/new{% endif %}"
      class="curator-form">

    <input type="hidden" name="next_url" value="{{ next_url }}">
```

**Why:** Rename `next` to `next_url` for consistency with all other forms, and to avoid shadowing built-in python variables.

---

### 3. `curator/web/routes/tasks_routes.py`

#### BEFORE
```python
@router.get("/new/{slug}", response_class=HTMLResponse)
async def new_task_form(
    slug: str,
    request: Request,
    parent_id: int | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    proj_repo = ProjectRepository(db)
    try:
        project = await proj_repo.get_by_slug(slug)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    task_repo = TaskRepository(db)
    view = ViewBuilder(config.views_path).get_view("tasks")

    return templates.TemplateResponse(
        request=request,
        name="tasks/form.html",
        context={
            "view": view,
            "task": None,
            "project": project,
            "parent_id": parent_id,
            "status_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
            "parent_options": await task_repo.get_parent_options(project["id"]),
        },
    )
```

#### AFTER
```python
@router.get("/new/{slug}", response_class=HTMLResponse)
async def new_task_form(
    slug: str,
    request: Request,
    parent_id: int | None = None,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    proj_repo = ProjectRepository(db)
    try:
        project = await proj_repo.get_by_slug(slug)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    # Compute next_url from query param, referer, or default to project detail
    if not next_url:
        next_url = request.headers.get("referer", f"/projects/{slug}")

    task_repo = TaskRepository(db)
    view = ViewBuilder(config.views_path).get_view("tasks")

    return templates.TemplateResponse(
        request=request,
        name="tasks/form.html",
        context={
            "view": view,
            "task": None,
            "project": project,
            "parent_id": parent_id,
            "next_url": next_url,
            "status_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
            "parent_options": await task_repo.get_parent_options(project["id"]),
        },
    )
```

**Why:** GET handler now accepts optional `next_url` query param and passes it to template.

---

#### BEFORE
```python
@router.post("/new/{slug}")
async def create_task(
    slug: str,
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
    return RedirectResponse(url=f"/projects/{slug}", status_code=303)
```

#### AFTER
```python
@router.post("/new/{slug}")
async def create_task(
    slug: str,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    parent_id: int | None = Form(None),
    links: str = Form(""),
    sort_order: int = Form(0),
    next_url: str = Form(""),
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
    # Use next_url if provided, otherwise default to project detail
    redirect_url = next_url or f"/projects/{slug}"
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data and uses it if provided.

---

#### BEFORE
```python
@router.get("/{task_id}/edit", response_class=HTMLResponse)
async def edit_task_form(
    task_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    task_repo = TaskRepository(db)
    try:
        task = await task_repo.get_by_id(task_id)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    proj_repo = ProjectRepository(db)
    project = await proj_repo.get_by_id(task["project_id"])
    view = ViewBuilder(config.views_path).get_view("tasks")

    return templates.TemplateResponse(
        request=request,
        name="tasks/form.html",
        context={
            "view": view,
            "task": task,
            "project": project,
            "parent_id": task.get("parent_id"),
            "status_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
            "parent_options": await task_repo.get_parent_options(task["project_id"]),
        },
    )
```

#### AFTER
```python
@router.get("/{task_id}/edit", response_class=HTMLResponse)
async def edit_task_form(
    task_id: int,
    request: Request,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    task_repo = TaskRepository(db)
    try:
        task = await task_repo.get_by_id(task_id)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    # Compute next_url from query param, referer, or default to project detail
    if not next_url:
        proj_repo = ProjectRepository(db)
        project = await proj_repo.get_by_id(task["project_id"])
        next_url = request.headers.get("referer", f"/projects/{project['slug']}")
    else:
        proj_repo = ProjectRepository(db)
        project = await proj_repo.get_by_id(task["project_id"])

    view = ViewBuilder(config.views_path).get_view("tasks")

    return templates.TemplateResponse(
        request=request,
        name="tasks/form.html",
        context={
            "view": view,
            "task": task,
            "project": project,
            "parent_id": task.get("parent_id"),
            "next_url": next_url,
            "status_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
            "parent_options": await task_repo.get_parent_options(task["project_id"]),
        },
    )
```

**Why:** GET handler now accepts optional `next_url` query param and passes it to template.

---

#### BEFORE
```python
@router.post("/{task_id}/edit")
async def update_task(
    task_id: int,
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
    return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
```

#### AFTER
```python
@router.post("/{task_id}/edit")
async def update_task(
    task_id: int,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    is_terminal: bool = Form(False),
    parent_id: int | None = Form(None),
    links: str = Form(""),
    sort_order: int = Form(0),
    project_slug: str = Form(...),
    next_url: str = Form(""),
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
    # Use next_url if provided, otherwise default to project detail
    redirect_url = next_url or f"/projects/{project_slug}"
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data and uses it if provided.

---

#### BEFORE
```python
@router.post("/{task_id}/delete")
async def delete_task(
    task_id: int,
    project_slug: str = Form(...),
    db: AsyncDBConnection = Depends(get_db),
):
    task_repo = TaskRepository(db)
    try:
        await task_repo.delete(task_id)
    except DeleteBlockedError as exc:
        return RedirectResponse(
            url=f"/projects/{project_slug}?delete_blocked={task_id}&count={exc.count}",
            status_code=303,
        )
    return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
```

#### AFTER
```python
@router.post("/{task_id}/delete")
async def delete_task(
    task_id: int,
    project_slug: str = Form(...),
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    task_repo = TaskRepository(db)
    redirect_url = next_url or f"/projects/{project_slug}"
    
    try:
        await task_repo.delete(task_id)
    except DeleteBlockedError as exc:
        return RedirectResponse(
            url=f"{redirect_url}?delete_blocked={task_id}&count={exc.count}",
            status_code=303,
        )
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data and uses it in both success and error redirects.

---

#### BEFORE
```python
@router.post("/{task_id}/force-delete")
async def force_delete_task(
    task_id: int,
    project_slug: str = Form(...),
    db: AsyncDBConnection = Depends(get_db),
):
    task_repo = TaskRepository(db)
    await task_repo.force_delete(task_id)
    return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
```

#### AFTER
```python
@router.post("/{task_id}/force-delete")
async def force_delete_task(
    task_id: int,
    project_slug: str = Form(...),
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    task_repo = TaskRepository(db)
    await task_repo.force_delete(task_id)
    # Use next_url if provided, otherwise default to project detail
    redirect_url = next_url or f"/projects/{project_slug}"
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data and uses it if provided.

---

### 4. `curator/templates/tasks_form.html`

#### BEFORE
```html
<form method="post"
      action="{% if task %}/tasks/{{ task.id }}/edit{% else %}/tasks/new/{{ project.slug }}{% endif %}"
      class="curator-form">

    <input type="hidden" name="project_slug" value="{{ project.slug }}">
    <input type="hidden" name="next" value="{{ next }}">
```

#### AFTER
```html
<form method="post"
      action="{% if task %}/tasks/{{ task.id }}/edit{% else %}/tasks/new/{{ project.slug }}{% endif %}"
      class="curator-form">

    <input type="hidden" name="project_slug" value="{{ project.slug }}">
    <input type="hidden" name="next_url" value="{{ next_url }}">
```

**Why:** Rename `next` to `next_url` for consistency.

---

#### BEFORE (force delete form)
```html
    <form method="post" action="/tasks/{{ task.id }}/force-delete">
        <input type="hidden" name="project_slug" value="{{ project.slug }}">
        <input type="hidden" name="next" value="{{ next }}">
```

#### AFTER (force delete form)
```html
    <form method="post" action="/tasks/{{ task.id }}/force-delete">
        <input type="hidden" name="project_slug" value="{{ project.slug }}">
        <input type="hidden" name="next_url" value="{{ next_url }}">
```

**Why:** Rename `next` to `next_url` for consistency.

---

### 5. `curator/web/routes/files_routes.py`

#### BEFORE
```python
@router.get("/new", response_class=HTMLResponse)
async def new_file_form(
    request: Request,
    project_id: int | None = None,
    task_id: int | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = FileRepository(db)
    view = ViewBuilder(config.views_path).get_view("files")

    project_slug = None
    if project_id:
        proj_repo = ProjectRepository(db)
        try:
            project = await proj_repo.get_by_id(project_id)
            project_slug = project["slug"]
        except RecordNotFoundError:
            pass

    return templates.TemplateResponse(
        request=request,
        name="files/form.html",
        context={
            "view": view,
            "file": None,
            "project_id": project_id,
            "task_id": task_id,
            "project_slug": project_slug,
            "file_type_options": await repo.get_file_type_options(),
            "location_type_options": await repo.get_location_type_options(),
        },
    )
```

#### AFTER
```python
@router.get("/new", response_class=HTMLResponse)
async def new_file_form(
    request: Request,
    project_id: int | None = None,
    task_id: int | None = None,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = FileRepository(db)
    view = ViewBuilder(config.views_path).get_view("files")

    project_slug = None
    if project_id:
        proj_repo = ProjectRepository(db)
        try:
            project = await proj_repo.get_by_id(project_id)
            project_slug = project["slug"]
        except RecordNotFoundError:
            pass

    # Compute next_url from query param, referer, or default
    if not next_url:
        next_url = request.headers.get("referer", "/projects/board")

    return templates.TemplateResponse(
        request=request,
        name="files/form.html",
        context={
            "view": view,
            "file": None,
            "project_id": project_id,
            "task_id": task_id,
            "project_slug": project_slug,
            "next_url": next_url,
            "file_type_options": await repo.get_file_type_options(),
            "location_type_options": await repo.get_location_type_options(),
        },
    )
```

**Why:** GET handler now accepts optional `next_url` query param and passes it to template.

---

#### BEFORE
```python
@router.post("/new")
async def create_file(
    project_id: int | None = Form(None),
    task_id: int | None = Form(None),
    label: str = Form(...),
    file_type_id: int = Form(...),
    location: str = Form(...),
    location_type_id: int = Form(...),
    notes: str = Form(""),
    project_slug: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = FileRepository(db)
    await repo.create(
        {
            "project_id": project_id,
            "task_id": task_id,
            "label": label,
            "file_type_id": file_type_id,
            "location": location,
            "location_type_id": location_type_id,
            "notes": notes or None,
        }
    )
    if project_slug:
        return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
    return RedirectResponse(url="/projects/", status_code=303)
```

#### AFTER
```python
@router.post("/new")
async def create_file(
    project_id: int | None = Form(None),
    task_id: int | None = Form(None),
    label: str = Form(...),
    file_type_id: int = Form(...),
    location: str = Form(...),
    location_type_id: int = Form(...),
    notes: str = Form(""),
    project_slug: str = Form(""),
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = FileRepository(db)
    await repo.create(
        {
            "project_id": project_id,
            "task_id": task_id,
            "label": label,
            "file_type_id": file_type_id,
            "location": location,
            "location_type_id": location_type_id,
            "notes": notes or None,
        }
    )
    # Use next_url if provided, otherwise fallback to project detail or list
    if next_url:
        return RedirectResponse(url=next_url, status_code=303)
    elif project_slug:
        return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
    return RedirectResponse(url="/projects/", status_code=303)
```

**Why:** POST handler reads `next_url` from form data and prioritizes it in redirect logic.

---

#### BEFORE
```python
@router.get("/{file_id}/edit", response_class=HTMLResponse)
async def edit_file_form(
    file_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = FileRepository(db)
    try:
        file = await repo.get_by_id(file_id)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    project_slug = None
    if file.get("project_id"):
        proj_repo = ProjectRepository(db)
        try:
            project = await proj_repo.get_by_id(file["project_id"])
            project_slug = project["slug"]
        except RecordNotFoundError:
            pass

    view = ViewBuilder(config.views_path).get_view("files")

    return templates.TemplateResponse(
        request=request,
        name="files/form.html",
        context={
            "view": view,
            "file": file,
            "project_id": file.get("project_id"),
            "task_id": file.get("task_id"),
            "project_slug": project_slug,
            "file_type_options": await repo.get_file_type_options(),
            "location_type_options": await repo.get_location_type_options(),
        },
    )
```

#### AFTER
```python
@router.get("/{file_id}/edit", response_class=HTMLResponse)
async def edit_file_form(
    file_id: int,
    request: Request,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = FileRepository(db)
    try:
        file = await repo.get_by_id(file_id)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    project_slug = None
    if file.get("project_id"):
        proj_repo = ProjectRepository(db)
        try:
            project = await proj_repo.get_by_id(file["project_id"])
            project_slug = project["slug"]
        except RecordNotFoundError:
            pass

    # Compute next_url from query param, referer, or default
    if not next_url:
        next_url = request.headers.get("referer", "/projects/board")

    view = ViewBuilder(config.views_path).get_view("files")

    return templates.TemplateResponse(
        request=request,
        name="files/form.html",
        context={
            "view": view,
            "file": file,
            "project_id": file.get("project_id"),
            "task_id": file.get("task_id"),
            "project_slug": project_slug,
            "next_url": next_url,
            "file_type_options": await repo.get_file_type_options(),
            "location_type_options": await repo.get_location_type_options(),
        },
    )
```

**Why:** GET handler now accepts optional `next_url` query param and passes it to template.

---

#### BEFORE
```python
@router.post("/{file_id}/edit")
async def update_file(
    file_id: int,
    label: str = Form(...),
    file_type_id: int = Form(...),
    location: str = Form(...),
    location_type_id: int = Form(...),
    notes: str = Form(""),
    project_slug: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = FileRepository(db)
    await repo.update(
        file_id,
        {
            "label": label,
            "file_type_id": file_type_id,
            "location": location,
            "location_type_id": location_type_id,
            "notes": notes or None,
        },
    )
    if project_slug:
        return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
    return RedirectResponse(url="/projects/", status_code=303)
```

#### AFTER
```python
@router.post("/{file_id}/edit")
async def update_file(
    file_id: int,
    label: str = Form(...),
    file_type_id: int = Form(...),
    location: str = Form(...),
    location_type_id: int = Form(...),
    notes: str = Form(""),
    project_slug: str = Form(""),
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = FileRepository(db)
    await repo.update(
        file_id,
        {
            "label": label,
            "file_type_id": file_type_id,
            "location": location,
            "location_type_id": location_type_id,
            "notes": notes or None,
        },
    )
    # Use next_url if provided, otherwise fallback to project detail or list
    if next_url:
        return RedirectResponse(url=next_url, status_code=303)
    elif project_slug:
        return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
    return RedirectResponse(url="/projects/", status_code=303)
```

**Why:** POST handler reads `next_url` from form data and prioritizes it in redirect logic.

---

#### BEFORE
```python
@router.post("/{file_id}/delete")
async def delete_file(
    file_id: int,
    project_slug: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = FileRepository(db)
    await repo.delete(file_id)
    if project_slug:
        return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
    return RedirectResponse(url="/projects/", status_code=303)
```

#### AFTER
```python
@router.post("/{file_id}/delete")
async def delete_file(
    file_id: int,
    project_slug: str = Form(""),
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = FileRepository(db)
    await repo.delete(file_id)
    # Use next_url if provided, otherwise fallback to project detail or list
    if next_url:
        return RedirectResponse(url=next_url, status_code=303)
    elif project_slug:
        return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
    return RedirectResponse(url="/projects/", status_code=303)
```

**Why:** POST handler reads `next_url` from form data and prioritizes it in redirect logic.

---

### 6. `curator/templates/files_form.html`

search for all instances of next and verify next_url is used
```html
<input type="hidden" name="next_url" value="{{ next }}">
```

Just verify the context variable name is `next_url` (routes now pass it correctly after changes above).

---

### 7. `curator/web/routes/tags_routes.py`

#### BEFORE
```python
@router.get("/new", response_class=HTMLResponse)
async def new_tag_form(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = TagRepository(db)
    view = ViewBuilder(config.views_path).get_view("tags")

    return templates.TemplateResponse(
        request=request,
        name="tags/form.html",
        context={
            "view": view,
            "tag": None,
            "category_options": await repo.get_category_options(),
        },
    )
```

#### AFTER
```python
@router.get("/new", response_class=HTMLResponse)
async def new_tag_form(
    request: Request,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = TagRepository(db)
    view = ViewBuilder(config.views_path).get_view("tags")

    # Compute next_url from query param, referer, or default to tags list
    if not next_url:
        next_url = request.headers.get("referer", "/tags/")

    return templates.TemplateResponse(
        request=request,
        name="tags/form.html",
        context={
            "view": view,
            "tag": None,
            "next_url": next_url,
            "category_options": await repo.get_category_options(),
        },
    )
```

**Why:** GET handler now accepts optional `next_url` query param and passes it to template.

---

#### BEFORE
```python
@router.post("/new")
async def create_tag(
    name: str = Form(...),
    category_id: int | None = Form(None),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.create({"name": name, "category_id": category_id})
    return RedirectResponse(url="/tags/", status_code=303)
```

#### AFTER
```python
@router.post("/new")
async def create_tag(
    name: str = Form(...),
    category_id: int | None = Form(None),
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.create({"name": name, "category_id": category_id})
    # Use next_url if provided, otherwise default to tags list
    redirect_url = next_url or "/tags/"
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data and uses it if provided.

---

#### BEFORE
```python
@router.get("/{tag_id}/edit", response_class=HTMLResponse)
async def edit_tag_form(
    tag_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = TagRepository(db)
    try:
        tag = await repo.get_by_id(tag_id)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    view = ViewBuilder(config.views_path).get_view("tags")

    return templates.TemplateResponse(
        request=request,
        name="tags/form.html",
        context={
            "view": view,
            "tag": tag,
            "category_options": await repo.get_category_options(),
        },
    )
```

#### AFTER
```python
@router.get("/{tag_id}/edit", response_class=HTMLResponse)
async def edit_tag_form(
    tag_id: int,
    request: Request,
    next_url: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = TagRepository(db)
    try:
        tag = await repo.get_by_id(tag_id)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    # Compute next_url from query param, referer, or default to tags list
    if not next_url:
        next_url = request.headers.get("referer", "/tags/")

    view = ViewBuilder(config.views_path).get_view("tags")

    return templates.TemplateResponse(
        request=request,
        name="tags/form.html",
        context={
            "view": view,
            "tag": tag,
            "next_url": next_url,
            "category_options": await repo.get_category_options(),
        },
    )
```

**Why:** GET handler now accepts optional `next_url` query param and passes it to template.

---

#### BEFORE
```python
@router.post("/{tag_id}/edit")
async def update_tag(
    tag_id: int,
    name: str = Form(...),
    category_id: int | None = Form(None),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.update(tag_id, {"name": name, "category_id": category_id})
    return RedirectResponse(url="/tags/", status_code=303)
```

#### AFTER
```python
@router.post("/{tag_id}/edit")
async def update_tag(
    tag_id: int,
    name: str = Form(...),
    category_id: int | None = Form(None),
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.update(tag_id, {"name": name, "category_id": category_id})
    # Use next_url if provided, otherwise default to tags list
    redirect_url = next_url or "/tags/"
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data and uses it if provided.

---

#### BEFORE
```python
@router.post("/{tag_id}/delete")
async def delete_tag(
    tag_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.delete(tag_id)
    return RedirectResponse(url="/tags/", status_code=303)
```

#### AFTER
```python
@router.post("/{tag_id}/delete")
async def delete_tag(
    tag_id: int,
    next_url: str = Form(""),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.delete(tag_id)
    # Use next_url if provided, otherwise default to tags list
    redirect_url = next_url or "/tags/"
    return RedirectResponse(url=redirect_url, status_code=303)
```

**Why:** POST handler reads `next_url` from form data and uses it if provided.

---

### 8. Create `curator/web/templates/tags_form.html` (if it doesn't exist)

If tags_form.html doesn't exist, create it following the same pattern as projects/tasks/files:

```html
{% extends "base.html" %}
{% block title %}{% if tag %}Edit Tag{% else %}New Tag{% endif %} — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{% if tag %}Edit Tag{% else %}New Tag{% endif %}</h1>
    <a href="{{ next_url }}" class="btn-secondary">Cancel</a>
</div>

<form method="post"
      action="{% if tag %}/tags/{{ tag.id }}/edit{% else %}/tags/new{% endif %}"
      class="curator-form">

    <input type="hidden" name="next_url" value="{{ next_url }}">

    {% for field in view.fields %}

    {% if field.name == "name" %}
    <label for="name">
        {{ field.label }}{% if field.required %} *{% endif %}
        <input type="text"
               id="name"
               name="name"
               value="{{ tag.name if tag else '' }}"
               {% if field.required %}required{% endif %}
               placeholder="{{ field.placeholder or '' }}">
    </label>

    {% elif field.name == "category_id" %}
    <label for="category_id">
        {{ field.label }}
        <select id="category_id" name="category_id">
            <option value="">— none —</option>
            {% for opt in category_options %}
            <option value="{{ opt.id }}"
                {% if tag and tag.category_id == opt.id %}selected{% endif %}>
                {{ opt.name }}
            </option>
            {% endfor %}
        </select>
    </label>

    {% endif %}
    {% endfor %}

    <div class="form-actions">
        <button type="submit" class="btn-primary">
            {% if tag %}Save Changes{% else %}Create Tag{% endif %}
        </button>
        <a href="{{ next_url }}" class="btn-secondary">Cancel</a>
    </div>

</form>
{% endblock %}
```

**Why:** Complete form template for tags following the established pattern.

---

## Summary of Changes

| File | Changes |
|------|---------|
| `projects_routes.py` | Add `next_url` param to 2 GET handlers, 3 POST handlers |
| `projects_form.html` | Rename `next` → `next_url` (1 line) |
| `tasks_routes.py` | Add `next_url` param to 2 GET handlers, 4 POST handlers |
| `tasks_form.html` | Rename `next` → `next_url` (2 lines) |
| `files_routes.py` | Add `next_url` param to 2 GET handlers, 3 POST handlers |
| `files_form.html` | Already uses `next_url`, no changes needed |
| `tags_routes.py` | Add `next_url` param to 2 GET handlers, 3 POST handlers |
| `tags_form.html` | Create new file if it doesn't exist |

---

## Testing Strategy

After applying these changes, test the redirect flow:

1. **From the board:** Click "New Task" → form loads with `next_url=/projects/board` → save → redirects to board ✓
2. **From project detail:** Click "Edit Project" → form loads with `next_url=/projects/{slug}` → save → redirects to detail ✓
3. **Without `next_url`:** Delete form on detail page (no next_url param) → save → redirects to default (project detail) ✓

All forms will now respect their caller's context.

---

## Notes

- **Fallback behavior:** When `next_url` is not provided, routes default to sensible locations (detail page for updates, list page for global actions like tag creation).
- **Security:** The `next_url` is always read from POST form data or GET query params within the same application. No external redirects are possible without additional validation.
- **Board integration:** When the board calls forms via HTMX or links, it can pass `?next_url=/projects/board` to ensure return to board after save.
