# Change Doc: Add `notes` to Task Save Pipeline

**Problem:** The Add Task and Edit Task dialogs have `notes` and `links` fields
that render correctly in the UI but `notes` is never saved. The field exists in
the database (`tasks.notes`, exposed via `v_tasks`) and in the template, but was
never wired through the repository layer or the routes.

**Files changed:** 3

---

## 1. `src/curator/data/queries.yaml`

### tasks.create — BEFORE
```yaml
  create:
    type: select_scalar
    sql: >
      INSERT INTO tasks
          (project_id, parent_id, description, status_id, priority_id,
           links, source_file, sort_order)
      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
      RETURNING id
```

### tasks.create — AFTER
```yaml
  create:
    type: select_scalar
    sql: >
      INSERT INTO tasks
          (project_id, parent_id, description, status_id, priority_id,
           notes, links, source_file, sort_order)
      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
      RETURNING id
```

**Why:** `notes` column was missing from the INSERT entirely.

---

### tasks.update — BEFORE
```yaml
  update:
    type: execute
    sql: >
      UPDATE tasks SET
          description  = %s,
          status_id    = %s,
          priority_id  = %s,
          parent_id    = %s,
          links        = %s,
          sort_order   = %s,
          completed_at = %s
      WHERE id = %s
```

### tasks.update — AFTER
```yaml
  update:
    type: execute
    sql: >
      UPDATE tasks SET
          description  = %s,
          status_id    = %s,
          priority_id  = %s,
          parent_id    = %s,
          notes        = %s,
          links        = %s,
          sort_order   = %s,
          completed_at = %s
      WHERE id = %s
```

**Why:** `notes` column was missing from the UPDATE entirely.

---

## 2. `src/curator/db/tasks.py`

### `create()` — BEFORE
```python
    async def create(self, data: dict) -> int:
        result = await self.fetch_scalar(
            """
            INSERT INTO tasks
                (project_id, parent_id, description, status_id, priority_id,
                 links, source_file, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data["project_id"],
                data.get("parent_id"),
                data["description"],
                data["status_id"],
                data["priority_id"],
                data.get("links", ""),
                data.get("source_file", ""),
                data.get("sort_order", 0),
            ),
        )
        return int(result)
```

### `create()` — AFTER
```python
    async def create(self, data: dict) -> int:
        result = await self.fetch_scalar(
            """
            INSERT INTO tasks
                (project_id, parent_id, description, status_id, priority_id,
                 notes, links, source_file, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data["project_id"],
                data.get("parent_id"),
                data["description"],
                data["status_id"],
                data["priority_id"],
                data.get("notes", ""),
                data.get("links", ""),
                data.get("source_file", ""),
                data.get("sort_order", 0),
            ),
        )
        return int(result)
```

**Why:** `notes` was not extracted from `data` or passed to the query.

---

### `update()` — BEFORE
```python
        await self.execute(
            """
            UPDATE tasks SET
                description  = %s,
                status_id    = %s,
                priority_id  = %s,
                parent_id    = %s,
                links        = %s,
                sort_order   = %s,
                completed_at = %s
            WHERE id = %s
            """,
            (
                data["description"],
                data["status_id"],
                data["priority_id"],
                data.get("parent_id"),
                data.get("links", ""),
                data.get("sort_order", 0),
                completed_at,
                task_id,
            ),
        )
```

### `update()` — AFTER
```python
        await self.execute(
            """
            UPDATE tasks SET
                description  = %s,
                status_id    = %s,
                priority_id  = %s,
                parent_id    = %s,
                notes        = %s,
                links        = %s,
                sort_order   = %s,
                completed_at = %s
            WHERE id = %s
            """,
            (
                data["description"],
                data["status_id"],
                data["priority_id"],
                data.get("parent_id"),
                data.get("notes", ""),
                data.get("links", ""),
                data.get("sort_order", 0),
                completed_at,
                task_id,
            ),
        )
```

**Why:** `notes` was not extracted from `data` or passed to the query.

---

## 3. `src/curator/web/routes/tasks.py`

Four POST routes each need `notes: str = Form("")` added as a parameter and
`"notes": notes` added to the dict passed to the repository.

---

### `create_task` (`POST /tasks/new/{slug}`) — BEFORE
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

### `create_task` — AFTER
```python
@router.post("/new/{slug}")
async def create_task(
    slug: str,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    parent_id: int | None = Form(None),
    notes: str = Form(""),
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
            "notes": notes,
            "links": links,
            "sort_order": sort_order,
        }
    )
    return RedirectResponse(url=f"/projects/{slug}", status_code=303)
```

---

### `update_task` (`POST /tasks/{task_id}/edit`) — BEFORE
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

### `update_task` — AFTER
```python
@router.post("/{task_id}/edit")
async def update_task(
    task_id: int,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    is_terminal: bool = Form(False),
    parent_id: int | None = Form(None),
    notes: str = Form(""),
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
            "notes": notes,
            "links": links,
            "sort_order": sort_order,
        },
    )
    return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
```

---

### `create_task_panel` (`POST /tasks/new-panel/{slug}`) — BEFORE
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

### `create_task_panel` — AFTER
```python
@router.post("/new-panel/{slug}", response_class=HTMLResponse)
async def create_task_panel(
    slug: str,
    request: Request,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    parent_id: int | None = Form(None),
    notes: str = Form(""),
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
            "notes": notes,
            "links": links,
            "sort_order": sort_order,
        }
    )
    return await _panel_response(request, slug, proj_repo, task_repo, db)
```

---

### `update_task_panel` (`POST /tasks/{task_id}/edit-panel`) — BEFORE
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

### `update_task_panel` — AFTER
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
    notes: str = Form(""),
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
            "notes": notes,
            "links": links,
            "sort_order": sort_order,
        },
    )
    proj_repo = ProjectRepository(db)
    return await _panel_response(request, project_slug, proj_repo, task_repo, db)
```

---

## Notes

- The hardcoded SQL in `db/tasks.py` is redundant with `queries.yaml` now that
  the viewkit refactor is in place. Both are changed here for correctness, but
  wiring `TaskRepository` to use `QueryLoader` instead of inline SQL is a
  separate cleanup task.
- No schema migration needed — `notes` column already exists in the `tasks`
  table and is exposed via `v_tasks`.
- No template changes needed — `_panel.html` already has both fields in both
  dialogs and populates them from `data-task-notes` on the row element.
