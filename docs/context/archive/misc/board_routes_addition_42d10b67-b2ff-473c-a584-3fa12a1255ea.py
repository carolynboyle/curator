
# ---------------------------------------------------------------------------
# Add these two routes to projects_routes.py
# ---------------------------------------------------------------------------

@router.get("/board", response_class=HTMLResponse)
async def project_board(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    tree = await repo.get_tree()
    return templates.TemplateResponse(
        request=request,
        name="projects/board.html",
        context={"tree": tree},
    )


@router.get("/{slug}/panel", response_class=HTMLResponse)
async def project_panel(
    slug: str,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    try:
        project = await repo.get_by_slug(slug)
    except RecordNotFoundError:
        return HTMLResponse("<p class='board-empty'>Project not found.</p>", status_code=404)

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
