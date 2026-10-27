# Curator v2 Phase 1 — Fix Changes
# Date: 2026-06-23

Three files need changes to get Phase 1 running. Apply them in this order:
1. `src/curator/data/curator.yaml`
2. `src/curator/web/app.py`
3. `src/curator/templates/base.html`

---

## Change 1: `src/curator/data/curator.yaml`

**Why:** The routes call `config.get("branding", ...)`, `config.get("crew", ...)`,
and `config.get("ui", "theme")` — none of these sections exist in the current yaml.
Everything returns `None`, templates render nothing. Add all three sections.

**BEFORE:**
```yaml
# curator.yaml - Curator default configuration
#
# This file ships with the Curator and provides defaults.
# To override, create ~/.config/curator/curator.yaml with only
# the keys you want to change. You do not need to repeat keys
# that match the defaults.
#
# The database connection is configured separately in
# ~/.config/dev-utils/config.yaml under the 'dbkit:' key.
# Passwords are handled by ~/.pgpass — never put credentials here.

app:
  name: "The Curator"
  version: "0.1.0"

server:
  host: "127.0.0.1"      # Override with Tailscale IP in production
  port: 8080

ui:
  page_size: 25           # Rows per page in list views
  date_format: "%Y-%m-%d"

plugin:
  name: "The Curator"
  version: "0.1.0"
  description: "Web UI and database interface for the projects database"
  type: "web"
  crew_member: "curator"
```

**AFTER:**
```yaml
# curator.yaml - Curator default configuration
#
# This file ships with the Curator and provides defaults.
# To override, create ~/.config/curator/curator.yaml with only
# the keys you want to change. You do not need to repeat keys
# that match the defaults.
#
# The database connection is configured separately in
# ~/.config/dev-utils/config.yaml under the 'dbkit:' key.
# Passwords are handled by ~/.pgpass — never put credentials here.

branding:
  site_title: "Curator"
  site_subtitle: "Navigate the Project Crew"
  site_icon: "🎭"

server:
  host: "127.0.0.1"      # Override with Tailscale IP in production
  port: 8080

ui:
  page_size: 25           # Rows per page in list views
  date_format: "%Y-%m-%d"
  theme: "light"          # Phase 1: read from here
                          # Phase 3: read from settings table instead

crew:
  roles:
    - name: "captain"
      title: "The Captain"
      description: "Full admin access to all projects and records"
    - name: "curator"
      title: "The Curator"
      description: "Manage projects and tasks"
    - name: "mechanic"
      title: "The Mechanic"
      description: "Hardware management and refurb tracking"
    - name: "envoy"
      title: "The Envoy"
      description: "Connection tracking and coordination"
    - name: "scribe"
      title: "The Scribe"
      description: "Writing projects and documentation"

plugin:
  name: "The Curator"
  version: "0.2.0"
  description: "Web UI and database interface for the projects database"
  type: "web"
  crew_member: "curator"
```

---

## Change 2: `src/curator/web/app.py`

**Why:** The current file imports v1 routers (`files`, `projects`, `tags`, `tasks`)
that don't exist in v2. The `landing` and `crew` routers are never registered.
There's also a bare `GET /` route tacked on after `create_app()` that duplicates
(and conflicts with) the landing router's `GET /`. Replace the whole file with a
clean flat factory that registers only the v2 routers.

**BEFORE:**
```python
"""
curator.web.app - FastAPI application factory.

Creates and configures the FastAPI app instance, registers routers,
and sets up Jinja2 templating.

The app instance is imported by route modules to access the templates
object, and by uvicorn as the ASGI entry point.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from curator import plugin

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

templates = Jinja2Templates(
    directory=Path(__file__).parent.parent / "templates"
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title=plugin["name"],
        version=plugin["version"],
        description=plugin["description"],
    )

    # Static files
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parents[3] / "static"),
        name="static",
    )

    # Routers
    from curator.web.routes import files, projects, tags, tasks
    app.include_router(projects.router)
    app.include_router(tags.router)
    app.include_router(files.router)
    app.include_router(tasks.router)

    return app


app = create_app()
from fastapi import Request
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
```

**AFTER:**
```python
"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from curator.web.routes import landing, crew

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
)

# Static files — resolved relative to this file: src/curator/web/ -> static/
_STATIC_DIR = Path(__file__).parents[3] / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Routers
app.include_router(landing.router)
app.include_router(crew.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

---

## Change 3: `src/curator/templates/base.html`

**Why:** The current template references a multi-file CSS structure
(`static/css/base.css`, `static/css/layout.css`, `static/css/components/...`,
`static/css/themes/...`) that doesn't exist yet. Only `static/curator.css` exists.
This causes multiple 404s and the page renders unstyled. Also adds the Pico CSS
CDN link, since `curator.css` layers on top of Pico. Also updates the nav classes
to match the ones defined in `curator.css` (`curator-nav`, `curator-main`,
`curator-footer`).

**BEFORE:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ site_title | default("Curator") }}{% endblock %}</title>
    
    <!-- Base styles -->
    <link rel="stylesheet" href="/static/css/base.css">
    <link rel="stylesheet" href="/static/css/layout.css">
    
    <!-- Component styles -->
    <link rel="stylesheet" href="/static/css/components/navbar.css">
    <link rel="stylesheet" href="/static/css/components/card.css">
    <link rel="stylesheet" href="/static/css/components/table.css">
    <link rel="stylesheet" href="/static/css/components/empty-state.css">
    
    <!-- Theme (Phase 3: loaded from settings table) -->
    <link rel="stylesheet" href="/static/css/themes/{{ theme | default('light') }}.css">
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <div class="nav-brand">
                <a href="/">{{ site_icon | default("🎭") }} {{ site_title | default("Curator") }}</a>
            </div>
            <ul class="nav-links">
                <li><a href="/">Home</a></li>
            </ul>
        </div>
    </nav>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <footer>
        <p>&copy; 2026 Project Crew. All hands on deck.</p>
    </footer>
</body>
</html>
```

**AFTER:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ site_title | default("Curator") }}{% endblock %}</title>

    <!-- Pico CSS (base layer) -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">

    <!-- Curator theme (layers on top of Pico) -->
    <link rel="stylesheet" href="/static/curator.css">
</head>
<body>
    <nav class="curator-nav">
        <a href="/" class="nav-brand">{{ site_icon | default("🎭") }} {{ site_title | default("Curator") }}</a>
        <a href="/">Home</a>
    </nav>

    <main class="curator-main">
        {% block content %}{% endblock %}
    </main>

    <footer class="curator-footer">
        <p>&copy; 2026 Project Crew. All hands on deck.</p>
    </footer>
</body>
</html>
```

---

## After Applying All Three

Start the app:
```bash
cd ~/projects/curator
source .venv/bin/activate
uvicorn curator.web.app:app --host localhost --port 8080 --reload
```

Test in browser:
- `http://localhost:8080` — landing page with 5 crew cards
- `http://localhost:8080/crew?role=captain` — crew dashboard placeholder
- `http://localhost:8080/crew?role=mechanic` — crew dashboard placeholder
- `http://localhost:8080/health` — should return `{"status": "ok"}`

**Note on crew images:** `landing.html` expects `static/captain.png`, `static/curator.png`,
etc. If those files aren't there yet, the cards will render with broken image icons.
That's fine for Phase 1 — the routing and navigation are what we're proving.
