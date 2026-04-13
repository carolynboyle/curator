# files.py

**Path:** src/curator/web /routes/files.py
**Syntax:** python
**Generated:** 2026-04-12 14:30:33

```python
"""
curator.web.routes.files - File attachment routes.

Files are always attached to a project (or task). There is no
top-level files list — files are shown on the parent project's
detail page. Routes here handle create, edit, and delete only.

Route map:
    GET  /files/new                    — new file form (project or task context)
    POST /files/new                    — create file attachment
    GET  /files/{id}/edit              — edit form
    POST /files/{id}/edit              — update file attachment
    POST /files/{id}/delete            — delete file attachment
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from dbkit.connection import AsyncDBConnection
from viewkit import ViewBuilder

from curator.db import FileRepository, ProjectRepository
from curator.exceptions import RecordNotFoundError
from curator.web.app import templates
from curator.web.deps import get_config, get_db

router = APIRouter(prefix="/files", tags=["files"])


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

    # Resolve project slug for the cancel/back link
    project_slug = None
    if project_id:
        proj_repo = ProjectRepository(db)
        try:
            project = await proj_repo.get_by_id(project_id)
            project_slug = project["slug"]
        except RecordNotFoundError:
            pass

    return templates.TemplateResponse(
        "files/form.html",
        {
            "request": request,
            "view": view,
            "file": None,
            "project_id": project_id,
            "task_id": task_id,
            "project_slug": project_slug,
            "file_type_options": await repo.get_file_type_options(),
            "location_type_options": await repo.get_location_type_options(),
        },
    )


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
            "404.html", {"request": request}, status_code=404
        )

    # Resolve project slug for cancel/back link
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
        "files/form.html",
        {
            "request": request,
            "view": view,
            "file": file,
            "project_id": file.get("project_id"),
            "task_id": file.get("task_id"),
            "project_slug": project_slug,
            "file_type_options": await repo.get_file_type_options(),
            "location_type_options": await repo.get_location_type_options(),
        },
    )


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
