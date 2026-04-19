# tags.py

**Path:** src/curator/web/routes/tags.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
curator.web.routes.tags - Tag CRUD routes.

Route map:
    GET  /tags/          — list all tags
    GET  /tags/new       — new tag form
    POST /tags/new       — create tag
    GET  /tags/{id}/edit — edit form
    POST /tags/{id}/edit — update tag
    POST /tags/{id}/delete — delete tag
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from dbkit.connection import AsyncDBConnection
from viewkit import ViewBuilder

from curator.db import TagRepository
from curator.exceptions import RecordNotFoundError
from curator.web.app import templates
from curator.web.deps import get_config, get_db

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_class=HTMLResponse)
async def list_tags(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = TagRepository(db)
    tags = await repo.get_all()
    view = ViewBuilder(config.views_path).get_view("tags")

    return templates.TemplateResponse(
        request=request,
        name="tags/list.html",
        context={
            "tags": tags,
            "view": view,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_tag_form(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = TagRepository(db)
    view = ViewBuilder(config.views_path).get_view("tags")

    return templates.TemplateResponse(
        request=request,
        name="tags/form.html",
        context={
            "view": view,
            "tag": None,
            "category_options": await repo.get_category_options(),
        },
    )


@router.post("/new")
async def create_tag(
    name: str = Form(...),
    category_id: int | None = Form(None),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.create({"name": name, "category_id": category_id})
    return RedirectResponse(url="/tags/", status_code=303)


@router.get("/{tag_id}/edit", response_class=HTMLResponse)
async def edit_tag_form(
    tag_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = TagRepository(db)
    try:
        tag = await repo.get_by_id(tag_id)
    except RecordNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404,
        )

    view = ViewBuilder(config.views_path).get_view("tags")

    return templates.TemplateResponse(
        request=request,
        name="tags/form.html",
        context={
            "view": view,
            "tag": tag,
            "category_options": await repo.get_category_options(),
        },
    )


@router.post("/{tag_id}/edit")
async def update_tag(
    tag_id: int,
    name: str = Form(...),
    category_id: int | None = Form(None),
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.update(tag_id, {"name": name, "category_id": category_id})
    return RedirectResponse(url="/tags/", status_code=303)


@router.post("/{tag_id}/delete")
async def delete_tag(
    tag_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    repo = TagRepository(db)
    await repo.delete(tag_id)
    return RedirectResponse(url="/tags/", status_code=303)

```
