"""
curator.web.routes.projects - Project CRUD routes.

All routes return Jinja2 template responses. HTMX partial responses
are returned for requests that include the HX-Request header.

Route map:
    GET  /projects              — list all projects
    GET  /projects/new          — new project form
    POST /projects/new          — create project
    GET  /projects/{slug}       — project detail
    GET  /projects/{slug}/edit  — edit form
    POST /projects/{slug}/edit  — update project
    POST /projects/{slug}/delete — delete project
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from dbkit.connection import AsyncDBConnection
from viewkit import ViewBuilder

from curator.db import ProjectRepository
from curator.exceptions import RecordNotFoundError
from curator.web.app import templates
from curator.web.deps import get_config, get_db

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_view_builder(config=Depends(get_config)):
    return ViewBuilder(config.views_path)


@router.get("/", response_class=HTMLResponse)
async def list_projects(
    request: Request,
    status: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    projects = await repo.get_all(status=status)
    view = ViewBuilder(config.views_path).get_view("projects")
    status_options = await repo.get_status_options()

    return templates.TemplateResponse(
        "projects/list.html",
        {
            "request": request,
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
):
    repo = ProjectRepository(db)
    view = ViewBuilder(config.views_path).get_view("projects")

    return templates.TemplateResponse(
        "projects/form.html",
        {
            "request": request,
            "view": view,
            "project": None,
            "status_options": await repo.get_status_options(),
            "type_options": await repo.get_type_options(),
            "parent_options": await repo.get_parent_options(),
        },
    )


@router.post("/new")
async def create_project(
    request: Request,
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


@router.get("/{slug}", response_class=HTMLResponse)
async def project_detail(
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
            "404.html", {"request": request}, status_code=404
        )

    from curator.db import FileRepository, TagRepository, TaskRepository

    task_repo = TaskRepository(db)
    tag_repo = TagRepository(db)
    file_repo = FileRepository(db)

    tasks = await task_repo.get_all_for_project(project["id"])
    tags = await tag_repo.get_for_project(project["id"])
    files = await file_repo.get_for_project(project["id"])
    subprojects = await repo.get_subprojects(project["id"])
    task_view = ViewBuilder(config.views_path).get_view("tasks")

    return templates.TemplateResponse(
        "projects/detail.html",
        {
            "request": request,
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
):
    repo = ProjectRepository(db)
    try:
        project = await repo.get_by_slug(slug)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )

    view = ViewBuilder(config.views_path).get_view("projects")

    return templates.TemplateResponse(
        "projects/form.html",
        {
            "request": request,
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


@router.post("/{slug}/delete")
async def delete_project(
    slug: str,
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    await repo.delete(slug)
    return RedirectResponse(url="/projects/", status_code=303)