"""
curator.web.routes.tasks - Task CRUD routes.

Tasks always belong to a project. The project slug is carried through
all routes so we can redirect back correctly after create, edit, or delete.

Route map:
    GET  /tasks/project/{slug}          — list tasks for a project
    GET  /tasks/new/{slug}              — new task form
    POST /tasks/new/{slug}              — create task
    POST /tasks/new-panel/{slug}        — create task from board dialog (HTMX)
    GET  /tasks/{id}/edit               — edit form
    POST /tasks/{id}/edit               — update task
    POST /tasks/{id}/edit-panel         — update task from board dialog (HTMX)
    POST /tasks/{id}/delete             — delete task (raises if children)
    POST /tasks/{id}/force-delete       — delete task and all descendants
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from dbkit.connection import AsyncDBConnection
from viewkit import ViewBuilder

from curator.db import FileRepository, ProjectRepository, TagRepository, TaskRepository
from curator.exceptions import DeleteBlockedError, RecordNotFoundError
from curator.web.app import templates
from curator.web.deps import get_config, get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])

_BOARD = "/projects/board"


def _next(request: Request, fallback: str = _BOARD) -> str:
    return request.headers.get("referer") or fallback


@router.get("/project/{slug}", response_class=HTMLResponse)
async def list_tasks(
    slug: str,
    request: Request,
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
    tasks = await task_repo.get_tree_for_project(project["id"])
    view = ViewBuilder(config.views_path).get_view("tasks")

    return templates.TemplateResponse(
        request=request,
        name="tasks/list.html",
        context={
            "project": project,
            "tasks": tasks,
            "view": view,
        },
    )


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
            "next": _next(request),
            "status_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
            "parent_options": await task_repo.get_parent_options(project["id"]),
        },
    )


@router.post("/new/{slug}")
async def create_task(
    request: Request,
    slug: str,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    parent_id: int | None = Form(None),
    links: str = Form(""),
    sort_order: int = Form(0),
    next_url: str = Form(_BOARD),
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
    return RedirectResponse(url=next_url, status_code=303)


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
    config=Depends(get_config),
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

    # Return refreshed panel partial for HTMX
    tag_repo = TagRepository(db)
    file_repo = FileRepository(db)

    tasks = await task_repo.get_tree_for_project(project["id"])
    tags = await tag_repo.get_for_project(project["id"])
    files = await file_repo.get_for_project(project["id"])
    subprojects = await proj_repo.get_subprojects(project["id"])

    return templates.TemplateResponse(
        request=request,
        name="projects/_panel.html",
        context={
            "project": project,
            "tasks": tasks,
            "tags": tags,
            "files": files,
            "subprojects": subprojects,
            "status_options": await proj_repo.get_status_options(),
            "type_options": await proj_repo.get_type_options(),
            "parent_options": await proj_repo.get_parent_options(),
            "status_task_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
        },
    )


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
            "next": _next(request),
            "status_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
            "parent_options": await task_repo.get_parent_options(task["project_id"]),
        },
    )


@router.post("/{task_id}/edit")
async def update_task(
    request: Request,
    task_id: int,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    is_terminal: bool = Form(False),
    parent_id: int | None = Form(None),
    links: str = Form(""),
    sort_order: int = Form(0),
    project_slug: str = Form(...),
    next_url: str = Form(_BOARD),
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
    return RedirectResponse(url=next_url, status_code=303)


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
    config=Depends(get_config),
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

    # Return refreshed panel partial for HTMX
    proj_repo = ProjectRepository(db)
    project = await proj_repo.get_by_slug(project_slug)
    tag_repo = TagRepository(db)
    file_repo = FileRepository(db)

    tasks = await task_repo.get_tree_for_project(project["id"])
    tags = await tag_repo.get_for_project(project["id"])
    files = await file_repo.get_for_project(project["id"])
    subprojects = await proj_repo.get_subprojects(project["id"])

    return templates.TemplateResponse(
        request=request,
        name="projects/_panel.html",
        context={
            "project": project,
            "tasks": tasks,
            "tags": tags,
            "files": files,
            "subprojects": subprojects,
            "status_options": await proj_repo.get_status_options(),
            "type_options": await proj_repo.get_type_options(),
            "parent_options": await proj_repo.get_parent_options(),
            "status_task_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
        },
    )


@router.post("/{task_id}/delete")
async def delete_task(
    request: Request,
    task_id: int,
    project_slug: str = Form(...),
    next_url: str = Form(_BOARD),
    db: AsyncDBConnection = Depends(get_db),
):
    task_repo = TaskRepository(db)
    try:
        await task_repo.delete(task_id)
    except DeleteBlockedError as exc:
        return RedirectResponse(
            url=f"{next_url}?delete_blocked={task_id}&count={exc.count}",
            status_code=303,
        )
    return RedirectResponse(url=next_url, status_code=303)


@router.post("/{task_id}/force-delete")
async def force_delete_task(
    request: Request,
    task_id: int,
    project_slug: str = Form(...),
    next_url: str = Form(_BOARD),
    db: AsyncDBConnection = Depends(get_db),
):
    task_repo = TaskRepository(db)
    await task_repo.force_delete(task_id)
    return RedirectResponse(url=next_url, status_code=303)
