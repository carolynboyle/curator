# Change: Crew Images in Board Empty Panel

**Commit type:** `trim`  
**Commit message:** `trim: show crew image in board panel before project is selected`

---

## Overview

When the board loads with no project selected, the right panel shows a
crew image appropriate to the current board context. The image for each
context is configured in `curator.yaml` so it can be swapped without
touching code or templates.

The Captain image shows on the unfiltered board. The Scribe image shows
when `?type=writing` is active. Additional types map to their own images
as they are added.

---

## Prerequisites (manual step on wcyjvs2)

Copy the four new crew images into `static/img/`:

```
captain.png
scribe.png
mechanic.png
envoy.png
```

These are served as static files — no conversion needed.

---

## Files changed

1. `src/curator/data/curator.yaml` — add `board_image` to each landing card
2. `src/curator/web/routes/projects.py` — pass `board_image` to board template
3. `src/curator/templates/projects/board.html` — render image in empty panel
4. `static/curator.css` — style the empty panel image

---

## 1. src/curator/data/curator.yaml

Add `board_image` to each card entry under `landing.cards`.

### BEFORE

```yaml
landing:
  cards:
    - title: "The Captain"
      subtitle: "Full project management · All records"
      url: "/projects/board"
      color: "teal"
    - title: "The Scribe"
      subtitle: "Writing projects · Draft · Publish · Archive"
      url: "/projects/board?type=writing"
      color: "slate"
    - title: "The Mechanic"
      subtitle: "Hardware management · Refurb · Inventory"
      url: "/projects/board?type=refurb"
      color: "amber"
    - title: "The Envoy"
      subtitle: "Connections · Remote support · Network"
      url: "/envoy"
      color: "navy"
```

### AFTER

```yaml
landing:
  cards:
    - title: "The Captain"
      subtitle: "Full project management · All records"
      url: "/projects/board"
      color: "teal"
      board_image: "captain.png"
    - title: "The Scribe"
      subtitle: "Writing projects · Draft · Publish · Archive"
      url: "/projects/board?type=writing"
      color: "slate"
      board_image: "scribe.png"
    - title: "The Mechanic"
      subtitle: "Hardware management · Refurb · Inventory"
      url: "/projects/board?type=refurb"
      color: "amber"
      board_image: "mechanic.png"
    - title: "The Envoy"
      subtitle: "Connections · Remote support · Network"
      url: "/envoy"
      color: "navy"
      board_image: "envoy.png"
```

**Why:** `board_image` lives alongside the other per-card config so all
crew member properties are in one place. The Envoy has an image assigned
even though it has no board view yet — harmless, and ready when it does.

---

## 2. src/curator/web/routes/projects.py

The board route already passes `project_type` to the template. Extend it
to also resolve the correct `board_image` from config.

### BEFORE

```python
@router.get("/board", response_class=HTMLResponse)
async def project_board(
    request: Request,
    project_type: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    tree = await repo.get_tree(project_type=project_type)
    return templates.TemplateResponse(
        request=request,
        name="projects/board.html",
        context={"tree": tree, "project_type": project_type},
    )
```

### AFTER

```python
@router.get("/board", response_class=HTMLResponse)
async def project_board(
    request: Request,
    project_type: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
    config=Depends(get_config),
):
    repo = ProjectRepository(db)
    tree = await repo.get_tree(project_type=project_type)

    cards = config.get_section("landing").get("cards", [])
    board_image = "captain.png"
    for card in cards:
        card_url = card.get("url", "")
        if project_type and f"type={project_type}" in card_url:
            board_image = card.get("board_image", "captain.png")
            break
        elif not project_type and "type=" not in card_url and card.get("board_image"):
            board_image = card.get("board_image", "captain.png")
            break

    return templates.TemplateResponse(
        request=request,
        name="projects/board.html",
        context={
            "tree": tree,
            "project_type": project_type,
            "board_image": board_image,
        },
    )
```

**Why:** Resolves the image by matching `project_type` against the card
URLs in config. The unfiltered board matches the first card with no
`type=` parameter. Falls back to `captain.png` if nothing matches.
`config` is added as a dependency — it is already available in other
board-adjacent routes via `Depends(get_config)`.

---

## 3. src/curator/templates/projects/board.html

Replace the static placeholder text in `#board-detail` with the crew image.

### BEFORE

```html
  {# ---- Right panel: detail (starts empty) ---- #}
  <div class="board-right">
    <div id="board-detail" class="board-detail">
      <div class="board-empty">
        Double-click a project to open it.
      </div>
    </div>
  </div>
```

### AFTER

```html
  {# ---- Right panel: detail (starts empty) ---- #}
  <div class="board-right">
    <div id="board-detail" class="board-detail">
      <div class="board-empty">
        <img src="/static/img/{{ board_image }}"
             alt="Project Crew"
             class="board-empty-img">
      </div>
    </div>
  </div>
```

**Why:** The `board_image` variable is now in context from the route.
The `board-empty` wrapper div is kept so existing `.board-empty` CSS
continues to center the content.

---

## 4. static/curator.css

Add a rule to size the image within the empty panel. Append to the
`/* -- Empty state */` section.

### BEFORE

```css
/* -- Empty state ---------------------------------------------------------- */

.empty-state {
    text-align: center;
    color: var(--color-muted);
    padding: 2rem;
    font-size: 0.9rem;
}
```

### AFTER

```css
/* -- Empty state ---------------------------------------------------------- */

.empty-state {
    text-align: center;
    color: var(--color-muted);
    padding: 2rem;
    font-size: 0.9rem;
}

.board-empty-img {
    max-width: 100%;
    max-height: 420px;
    object-fit: contain;
    opacity: 0.9;
}
```

**Why:** `max-width: 100%` keeps the image inside the panel. `max-height`
prevents it from overflowing on shorter screens. `object-fit: contain`
preserves the aspect ratio. Slight opacity makes it feel like a background
hint rather than active content.
