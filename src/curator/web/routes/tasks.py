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

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from dbkit.connection import AsyncDBConnection
from viewkit import ViewBuilder

from curator.db import ProjectRepository, TaskRepository
from curator.exceptions import DeleteBlockedError, RecordNotFoundError
from curator.web.app import templates
from curator.web.deps import get_config, get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


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
            "status_options": await task_repo.get_status_options(),
            "priority_options": await task_repo.get_priority_options(),
            "parent_options": await task_repo.get_parent_options(project["id"]),
        },
    )


@router.post("/new/{slug}")
async def create_task(
    slug: str,
    description: str = Form(...),
    status_id: int = Form(...),
    priority_id: int = Form(...),
    parent_id: int | None = Form(None),
    links: str = Form(""),
    sort_order: int = Form(0),
    next_page: str | None = Form(None),
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
    if next_page == "board":
        return RedirectResponse(url="/projects/board", status_code=303)
    return RedirectResponse(url=f"/projects/{slug}", status_code=303)


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
    next_page: str | None = Form(None),
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
    if next_page == "board":
        return RedirectResponse(url="/projects/board", status_code=303)
    return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)


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


@router.post("/{task_id}/force-delete")
async def force_delete_task(
    task_id: int,
    project_slug: str = Form(...),
    db: AsyncDBConnection = Depends(get_db),
):
    task_repo = TaskRepository(db)
    await task_repo.force_delete(task_id)
    return RedirectResponse(url=f"/projects/{project_slug}", status_code=303)
