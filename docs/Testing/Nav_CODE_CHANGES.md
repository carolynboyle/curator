# Curator — Project Form Navigation Fix — Exact Code Changes

**Date:** 2026-04-21
**Files changed:** `src/curator/web/routes/projects.py`, `src/curator/templates/projects/form.html`

---

## Problem

1. **Cancel button does nothing** — `{{ next_url }}` in the template was rendering as empty because
   the GET routes never passed `next_url` into the template context.
2. **Save goes to project detail instead of back to the board** — the POST routes never accepted
   `next_url` from the submitted form data, so the redirect destination was hardcoded.
3. **`next` is a Python builtin** — using it as a variable name shadows the built-in iterator
   function. Renamed to `next_url` throughout.

---

## File 1: `src/curator/web/routes/projects.py`

### Change 1A — Add module-level constant and helper (after imports)

**ADD after the `router = APIRouter(...)` line:**

```python
_BOARD = "/projects/board"


def _next(request: Request) -> str:
    return request.headers.get("referer", _BOARD)
```

---

### Change 1B — `new_project_form` GET /new

**REPLACE THIS FUNCTION:**

```python
@router.get("/new", response_class=HTMLResponse)
async def new_project_form(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
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

**WITH THIS:**

```python
@router.get("/new", response_class=HTMLResponse)
async def new_project_form(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
    view = ViewBuilder(config.views_path).get_view("projects")

    return templates.TemplateResponse(
        request=request,
        name="projects/form.html",
        context={
            "view": view,
            "project": None,
            "next_url": _next(request),
            "status_options": await repo.get_status_options(),
            "type_options": await repo.get_type_options(),
            "parent_options": await repo.get_parent_options(),
        },
    )
```

**EFFECT:** Cancel button and hidden input now have a destination.

---

### Change 1C — `create_project` POST /new

**REPLACE THIS FUNCTION:**

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
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
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

**WITH THIS:**

```python
@router.post("/new")
async def create_project(
    name: str = Form(...),
    description: str = Form(""),
    status_id: int = Form(...),
    type_id: int | None = Form(None),
    parent_id: int | None = Form(None),
    target_date: str | None = Form(None),
    next_url: str = Form(_BOARD),
    db: AsyncDBConnection = Depends(get_db),
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
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
    return RedirectResponse(url=next_url, status_code=303)
```

**EFFECT:** After creating a project, returns to wherever the user came from.

---

### Change 1D — `edit_project_form` GET /{slug}/edit

**REPLACE THIS FUNCTION:**

```python
@router.get("/{slug}/edit", response_class=HTMLResponse)
async def edit_project_form(
    slug: str,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
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

**WITH THIS:**

```python
@router.get("/{slug}/edit", response_class=HTMLResponse)
async def edit_project_form(
    slug: str,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
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
            "next_url": _next(request),
            "status_options": await repo.get_status_options(),
            "type_options": await repo.get_type_options(),
            "parent_options": await repo.get_parent_options(),
        },
    )
```

**EFFECT:** Cancel button and hidden input now have a destination on the edit form too.

---

### Change 1E — `update_project` POST /{slug}/edit

**REPLACE THIS FUNCTION:**

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
    next_url: str = Form(_BOARD),
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
    return RedirectResponse(url=next_url, status_code=303)
```

**EFFECT:** After saving an edit, returns to wherever the user came from instead of hardcoding
the project detail page.

---

## File 2: `src/curator/templates/projects/form.html`

### Change 2A — Three occurrences of `{{ next }}` → `{{ next_url }}`

The hidden input's `name` attribute was already updated to `next_url` in a prior pass.
The template variable in three places still reads `{{ next }}` and needs to match.

**Line 7 — page header Cancel link:**
```html
<!-- BEFORE -->
<a href="{{ next }}" class="btn-secondary">Cancel</a>

<!-- AFTER -->
<a href="{{ next_url }}" class="btn-secondary">Cancel</a>
```

**Line 14 — hidden input value:**
```html
<!-- BEFORE -->
<input type="hidden" name="next_url" value="{{ next }}">

<!-- AFTER -->
<input type="hidden" name="next_url" value="{{ next_url }}">
```

**Bottom of form — form-actions Cancel link:**
```html
<!-- BEFORE -->
<a href="{{ next }}" class="btn-secondary">Cancel</a>

<!-- AFTER -->
<a href="{{ next_url }}" class="btn-secondary">Cancel</a>
```

**NOTE:** VS Code search for `{{ next }}` may fail due to invisible characters if copied from
chat. Copy the text directly from the editor into the search box instead.

---

## Verification Checklist

- [ ] `_BOARD` constant defined after `router = APIRouter(...)`
- [ ] `_next()` helper defined after `_BOARD`
- [ ] `new_project_form` context includes `"next_url": _next(request)`
- [ ] `create_project` accepts `next_url: str = Form(_BOARD)` and redirects to it
- [ ] `edit_project_form` context includes `"next_url": _next(request)`
- [ ] `update_project` accepts `next_url: str = Form(_BOARD)` and redirects to it (non-HTMX path)
- [ ] `form.html` has no remaining `{{ next }}` references (all three replaced with `{{ next_url }}`)

## Testing

1. From the board, click **+** to add a new project
2. **Cancel** → should return to board
3. Fill form and **Save** → should return to board
4. From the board panel, click full edit on a project
5. **Cancel** → should return to board
6. Edit and **Save** → should return to board
