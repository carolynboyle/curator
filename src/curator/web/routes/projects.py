"""
curator.web.routes.projects - Project CRUD routes.

All routes return Jinja2 template responses.

Route map:
    GET  /projects/              — list all projects
    GET  /projects/new           — new project form
    POST /projects/new           — create project
    GET  /projects/{slug}        — project detail
    GET  /projects/{slug}/edit   — edit form
    POST /projects/{slug}/edit   — update project
    POST /projects/{slug}/delete — delete project
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from dbkit.connection import AsyncDBConnection
from viewkit import QueryLoader, ViewBuilder

from curator.db import FileRepository, ProjectRepository, TagRepository, TaskRepository
from curator.exceptions import RecordNotFoundError
from curator.web.app import templates
from curator.web.deps import get_config, get_db, get_query_loader

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_class=HTMLResponse)
async def list_projects(
    request: Request,
    status: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
    projects = await repo.get_all(status=status)
    view = ViewBuilder(config.views_path).get_view("projects")
    status_options = await repo.get_status_options()

    return templates.TemplateResponse(
        request=request,
        name="projects/list.html",
        context={
            "projects": projects,
            "view": view,
            "status_options": status_options,
            "active_status": status,
        },
    )


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


@router.get("/{slug}", response_class=HTMLResponse)
async def project_detail(
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

    task_repo = TaskRepository(db, loader)
    tag_repo = TagRepository(db, loader)
    file_repo = FileRepository(db, loader)

    tasks = await task_repo.get_tree_for_project(project["id"])
    tags = await tag_repo.get_for_project(project["id"])
    files = await file_repo.get_for_project(project["id"])
    subprojects = await repo.get_subprojects(project["id"])
    task_view = ViewBuilder(config.views_path).get_view("tasks")

    return templates.TemplateResponse(
        request=request,
        name="projects/detail.html",
        context={
            "project": project,
            "tasks": tasks,
            "tags": tags,
            "files": files,
            "subprojects": subprojects,
            "task_view": task_view,
        },
    )


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
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
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


@router.post("/{slug}/delete")
async def delete_project(
    slug: str,
    db: AsyncDBConnection = Depends(get_db),
    loader: QueryLoader = Depends(get_query_loader),
):
    repo = ProjectRepository(db, loader)
    await repo.delete(slug)
    return RedirectResponse(url="/projects/", status_code=303)


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
