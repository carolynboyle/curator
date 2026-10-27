# Change Doc: Add `notes` to Project Save Pipeline

**Problem:** The Notes field exists in the project edit form and in the
database (`projects.notes`, exposed via `v_projects`) but is never saved.
The field is missing from the repository layer, the routes, and queries.yaml.

**Files changed:** 3

---

## 1. `src/curator/data/queries.yaml`

### projects.create — BEFORE
```yaml
  create:
    type: select_scalar
    sql: >
      INSERT INTO projects
          (name, slug, description, status_id, type_id, parent_id, target_date)
      VALUES (%s, %s, %s, %s, %s, %s, %s)
      RETURNING slug
```

### projects.create — AFTER
```yaml
  create:
    type: select_scalar
    sql: >
      INSERT INTO projects
          (name, slug, description, status_id, type_id, parent_id, target_date, notes)
      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
      RETURNING slug
```

**Why:** `notes` column missing from INSERT.

---

### projects.update — BEFORE
```yaml
  update:
    type: execute
    sql: >
      UPDATE projects SET
          name        = %s,
          description = %s,
          status_id   = %s,
          type_id     = %s,
          parent_id   = %s,
          target_date = %s
      WHERE slug = %s
```

### projects.update — AFTER
```yaml
  update:
    type: execute
    sql: >
      UPDATE projects SET
          name        = %s,
          description = %s,
          status_id   = %s,
          type_id     = %s,
          parent_id   = %s,
          target_date = %s,
          notes       = %s
      WHERE slug = %s
```

**Why:** `notes` column missing from UPDATE.

---

## 2. `src/curator/db/projects.py`

### `create()` — BEFORE
```python
    async def create(self, data: dict) -> str:
        """
        Insert a new project and return its slug.

        Generates a slug from the name. If the slug is already taken,
        appends a numeric suffix until unique.

        Args:
            data: Dict with keys: name, description, status_id, type_id,
                  parent_id. All optional except name and status_id.

        Returns:
            The slug of the newly created project.
        """
        base_slug = _slugify(data["name"])
        slug = base_slug
        suffix = 1
        while await self.slug_exists(slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        await self.execute(
            """
            INSERT INTO projects (name, slug, description, status_id, type_id, parent_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                data["name"],
                slug,
                data.get("description"),
                data["status_id"],
                data.get("type_id"),
                data.get("parent_id"),
            ),
        )
        return slug
```

### `create()` — AFTER
```python
    async def create(self, data: dict) -> str:
        """
        Insert a new project and return its slug.

        Generates a slug from the name. If the slug is already taken,
        appends a numeric suffix until unique.

        Args:
            data: Dict with keys: name, description, status_id, type_id,
                  parent_id, notes. All optional except name and status_id.

        Returns:
            The slug of the newly created project.
        """
        base_slug = _slugify(data["name"])
        slug = base_slug
        suffix = 1
        while await self.slug_exists(slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        await self.execute(
            """
            INSERT INTO projects (name, slug, description, status_id, type_id, parent_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["name"],
                slug,
                data.get("description"),
                data["status_id"],
                data.get("type_id"),
                data.get("parent_id"),
                data.get("notes"),
            ),
        )
        return slug
```

**Why:** `notes` not included in INSERT SQL or params tuple. Docstring Args updated.

---

### `update()` — BEFORE
```python
    async def update(self, slug: str, data: dict) -> None:
        """
        Update a project's mutable fields.

        Slug and created_at are immutable and ignored if present in data.

        Args:
            slug: Slug identifying the project to update.
            data: Dict with any of: name, description, status_id,
                  type_id, parent_id, target_date.

        Raises:
            RecordNotFoundError: If no project with that slug exists.
        """
        await self.get_by_slug(slug)  # raises if not found

        await self.execute(
            """
            UPDATE projects SET
                name        = %s,
                description = %s,
                status_id   = %s,
                type_id     = %s,
                parent_id   = %s,
                target_date = %s
            WHERE slug = %s
            """,
            (
                data["name"],
                data.get("description"),
                data["status_id"],
                data.get("type_id"),
                data.get("parent_id"),
                data.get("target_date"),
                slug,
            ),
        )
```

### `update()` — AFTER
```python
    async def update(self, slug: str, data: dict) -> None:
        """
        Update a project's mutable fields.

        Slug and created_at are immutable and ignored if present in data.

        Args:
            slug: Slug identifying the project to update.
            data: Dict with any of: name, description, status_id,
                  type_id, parent_id, target_date, notes.

        Raises:
            RecordNotFoundError: If no project with that slug exists.
        """
        await self.get_by_slug(slug)  # raises if not found

        await self.execute(
            """
            UPDATE projects SET
                name        = %s,
                description = %s,
                status_id   = %s,
                type_id     = %s,
                parent_id   = %s,
                target_date = %s,
                notes       = %s
            WHERE slug = %s
            """,
            (
                data["name"],
                data.get("description"),
                data["status_id"],
                data.get("type_id"),
                data.get("parent_id"),
                data.get("target_date"),
                data.get("notes"),
                slug,
            ),
        )
```

**Why:** `notes` not included in UPDATE SQL or params tuple. Docstring Args updated.

---

## 3. `src/curator/web/routes/projects.py`

### `create_project()` — BEFORE
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

### `create_project()` — AFTER
```python
@router.post("/new")
async def create_project(
    name: str = Form(...),
    description: str = Form(""),
    status_id: int = Form(...),
    type_id: int | None = Form(None),
    parent_id: int | None = Form(None),
    target_date: str | None = Form(None),
    notes: str = Form(""),
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
            "notes": notes or None,
        }
    )
    return RedirectResponse(url=next_url, status_code=303)
```

**Why:** `notes` form parameter missing; not passed to repo.

---

### `update_project()` — BEFORE
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

### `update_project()` — AFTER
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
    notes: str = Form(""),
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
            "notes": notes or None,
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

**Why:** `notes` form parameter missing; not passed to repo.

---

## Notes

- `notes or None` is used (rather than `notes or ""`) to stay consistent
  with how `description` and `target_date` are handled in this route —
  empty string from the form becomes NULL in the database.
- No schema migration needed — `notes` column already exists in the
  `projects` table and is exposed via `v_projects`.
- The "NoneSave this note!" display bug in the form will resolve once
  the value is correctly round-tripped through the database. The template
  is rendering `{{ project.notes or '' }}` which is correct — the problem
  was the value was never being saved in the first place.
