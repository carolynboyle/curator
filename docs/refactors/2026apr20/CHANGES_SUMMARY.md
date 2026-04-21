================================================================================
CURATOR UI ROUTING FIXES — SUMMARY OF CHANGES
================================================================================

FILE 1: _panel.html
================================================================================
LOCATION: Line 29 (panel edit form)

BEFORE:
    <form method="post" action="/projects/{{ project.slug }}/edit" id="panel-edit-form">

AFTER:
    <form method="post" action="/projects/{{ project.slug }}/edit" id="panel-edit-form"
          hx-post="/projects/{{ project.slug }}/edit"
          hx-target="#board-detail"
          hx-swap="innerHTML"
          hx-on::after-request="panelCancelAll()">

EFFECT:
- Inline edits now post via HTMX
- Response swaps into #board-detail (replaces panel)
- After save, panelCancelAll() hides edit inputs and save bar

================================================================================

FILE 2: projects_routes.py
================================================================================
LOCATION: Lines 173-234 (update_project route)

BEFORE:
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
        await repo.update(slug, {...})
        return RedirectResponse(url=f"/projects/{slug}", status_code=303)

AFTER:
    @router.post("/{slug}/edit")
    async def update_project(
        slug: str,
        request: Request,                    ← NEW: detect HTMX
        name: str = Form(...),
        description: str = Form(""),
        status_id: int = Form(...),
        type_id: int | None = Form(None),
        parent_id: int | None = Form(None),
        target_date: str | None = Form(None),
        db: AsyncDBConnection = Depends(get_db),
        config=Depends(get_config),         ← NEW: for views
    ):
        repo = ProjectRepository(db)
        await repo.update(slug, {...})
        
        # NEW: Check if HTMX request
        if request.headers.get("hx-request") == "true":
            # NEW: Fetch fresh data and return panel
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
                context={...all variables...}
            )
        
        # UNCHANGED: Regular form submissions still redirect
        return RedirectResponse(url=f"/projects/{slug}", status_code=303)

EFFECT:
- HTMX requests return the refreshed panel (stays on board)
- Regular form submissions redirect as before (backward compatible)
- Fully updated project data included in response

================================================================================

FILE 3: tasks_routes.py
================================================================================
LOCATION: Line 24 (imports)

BEFORE:
    from curator.db import ProjectRepository, TaskRepository

AFTER:
    from curator.db import FileRepository, ProjectRepository, TagRepository, TaskRepository

EFFECT:
- Added FileRepository and TagRepository for panel rendering

================================================================================
LOCATION: Lines 8-17 (docstring route map)

ADDED:
    POST /tasks/new-panel/{slug}        — create task from panel (HTMX)
    POST /tasks/{id}/edit-panel         — update task from panel (HTMX)

EFFECT:
- Documents new panel-specific routes

================================================================================
LOCATION: Line 221+ (NEW ROUTE 1)

ADDED:
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
        await task_repo.create({...})
        
        # Return updated panel with new task
        tasks = await task_repo.get_tree_for_project(project["id"])
        ... fetch all panel data ...
        
        return templates.TemplateResponse(
            request=request,
            name="projects/_panel.html",
            context={...all variables...}
        )

EFFECT:
- Creates task from panel dialog
- Returns refreshed panel (stays on board)
- Task appears immediately in list

================================================================================
LOCATION: Line 278+ (NEW ROUTE 2)

ADDED:
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
        await task_repo.update(task_id, {...})
        
        # Return updated panel with edited task
        proj_repo = ProjectRepository(db)
        project = await proj_repo.get_by_slug(project_slug)
        ... fetch all panel data ...
        
        return templates.TemplateResponse(
            request=request,
            name="projects/_panel.html",
            context={...all variables...}
        )

EFFECT:
- Updates task status/priority from panel dialog
- Returns refreshed panel (stays on board)
- Updated task appears immediately with new status/priority

================================================================================

SUMMARY OF PATTERNS
================================================================================

1. ALL HTMX FORMS now target "#board-detail" and swap "innerHTML"
   → Keeps user on board, refreshes panel in place

2. ROUTES check for HTMX request header
   if request.headers.get("hx-request") == "true":
       return panel_response  # HTMX path
   else:
       return redirect        # backward compatible

3. PANEL RESPONSES include complete context
   - Fresh project/task data
   - All status/priority/parent options
   - Tags, files, subprojects
   → Panel renders correctly with latest data

4. DIALOG JS ATTRIBUTES already in place
   → No JS changes needed (forms already had hx-post)

================================================================================
