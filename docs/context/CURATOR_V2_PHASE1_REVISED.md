# Curator v2 Phase 1 — Revised Scaffold

*Landing page + crew route skeleton. Modular CSS, config-driven, database-ready.*

---

## Updated Directory Structure (treekit)

```
curator/
├── curator/
│   ├── __init__.py
│   ├── config.py
│   ├── exceptions.py
│   ├── data/
│   │   └── curator.yaml
│   ├── db/
│   │   └── __init__.py
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── landing.py
│   │       └── crew.py
│   └── templates/
│       ├── base.html
│       ├── landing.html
│       └── crew.html
├── static/
│   ├── css/
│   │   ├── base.css
│   │   ├── layout.css
│   │   ├── components/
│   │   │   ├── navbar.css
│   │   │   ├── card.css
│   │   │   ├── table.css
│   │   │   └── empty-state.css
│   │   └── themes/
│   │       ├── light.css
│   │       └── dark.css
│   ├── captain.png
│   ├── curator.png
│   ├── mechanic.png
│   ├── envoy.png
│   └── scribe.png
├── tests/
│   ├── __init__.py
│   └── conftest.py
├── pyproject.toml
├── .env
├── .gitignore
└── README.md
```

---

## Key Changes from Original

1. **CSS structure** — modular components + themes (Phase 3 ready)
2. **Theme selection** — read from `curator.yaml`, Phase 3 will read from `settings` table
3. **App config** — expanded to include branding, theme, crew definitions
4. **No hardcoding** — all values externalized

---

## File Contents

### `curator/__init__.py`

```python
"""Curator v2 — Web UI for the Project Crew."""

__version__ = "0.2.0"
```

---

### `curator/exceptions.py`

```python
"""Curator exceptions."""


class CuratorError(Exception):
    """Base exception for Curator."""
    pass


class ConfigError(CuratorError):
    """Configuration error."""
    pass


class DatabaseError(CuratorError):
    """Database connection or query error."""
    pass
```

---

### `curator/config.py`

```python
"""Curator configuration management.

Loads curator.yaml from shipped defaults in curator/data/, with optional
user overrides from ~/.config/curator/curator.yaml.

Database connection is handled by dbkit — Curator does not manage credentials.
"""

from pathlib import Path
from typing import Any, Optional

import yaml

from curator.exceptions import ConfigError


# Shipped defaults live in curator/data/
_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_CONFIG = _DATA_DIR / "curator.yaml"

# User config lives in ~/.config/curator/
_USER_CONFIG_DIR = Path.home() / ".config" / "curator"
_USER_CONFIG = _USER_CONFIG_DIR / "curator.yaml"


class ConfigManager:
    """Load and merge Curator configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize ConfigManager.

        Args:
            config_path: Override path to curator.yaml for testing.
                        Defaults to ~/.config/curator/curator.yaml with
                        fallback to shipped defaults.
        """
        self._config = self._load(config_path)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a config value by section and key.

        Args:
            section: Top-level section (e.g., "server", "ui").
            key: Key within the section.
            default: Default if not found.

        Returns:
            Config value or default.
        """
        return self._config.get(section, {}).get(key, default)

    def get_section(self, section: str) -> dict:
        """Get an entire config section as a dict.

        Args:
            section: Top-level section name.

        Returns:
            Dict of key/value pairs, or empty dict if absent.
        """
        return self._config.get(section, {})

    @staticmethod
    def _load(config_path: Optional[Path]) -> dict:
        """Load and merge default and user curator.yaml files.

        Args:
            config_path: Explicit path override, or None for defaults.

        Returns:
            Merged config dict.

        Raises:
            ConfigError: If config file exists but cannot be read.
        """
        defaults = ConfigManager._load_yaml(_DEFAULT_CONFIG)

        if config_path is not None:
            user = ConfigManager._load_yaml(config_path)
            return ConfigManager._merge(defaults, user)

        if _USER_CONFIG.exists():
            user = ConfigManager._load_yaml(_USER_CONFIG)
            return ConfigManager._merge(defaults, user)

        return defaults

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        """Load a single YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed dict, or empty dict if file is empty.

        Raises:
            ConfigError: If file cannot be read or parsed.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise ConfigError(
                f"Could not read config file {path}: {exc}"
            ) from exc

        return data or {}

    @staticmethod
    def _merge(base: dict, override: dict) -> dict:
        """Recursively merge override into base.

        Args:
            base: Default config dict.
            override: User config dict.

        Returns:
            Merged dict.
        """
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigManager._merge(result[key], value)
            else:
                result[key] = value
        return result
```

---

### `curator/data/curator.yaml`

```yaml
# Curator v2 Configuration
# Branding, crew definitions, UI defaults, theme selection

branding:
  site_title: "Curator"
  site_subtitle: "Navigate the Project Crew"
  site_icon: "🎭"

server:
  host: localhost
  port: 8080
  reload: true

ui:
  page_size: 20
  theme: "light"           # Phase 1: read from here
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
```

---

### `curator/db/__init__.py`

```python
"""Database layer for Curator.

Phase 3: This is where settings queries will go to fetch user theme preference
instead of reading from curator.yaml.
"""
```

---

### `curator/web/__init__.py`

```python
"""Curator web application."""
```

---

### `curator/web/deps.py`

```python
"""Dependency injection for Curator routes."""

from typing import AsyncGenerator

from dbkit.connection import AsyncDBConnection

from curator.config import ConfigManager


async def get_db() -> AsyncGenerator[AsyncDBConnection, None]:
    """Yield a database connection per request.

    Closes on exit regardless of outcome.
    """
    db = AsyncDBConnection()
    try:
        await db.__aenter__()
        yield db
    finally:
        await db.__aexit__(None, None, None)


def get_config() -> ConfigManager:
    """Get the ConfigManager instance."""
    return ConfigManager()
```

---

### `curator/web/routes/__init__.py`

```python
"""Curator route modules."""
```

---

### `curator/web/routes/landing.py`

```python
"""Landing page route."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from curator.config import ConfigManager
from curator.web.deps import get_config

router = APIRouter()

# Initialize Jinja2 for landing
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def landing(config: ConfigManager = Depends(get_config)):
    """Landing page with crew role cards.
    
    All text, icons, crew definitions come from config — no hardcoding.
    """
    template = env.get_template("landing.html")
    
    context = {
        "site_title": config.get("branding", "site_title"),
        "site_subtitle": config.get("branding", "site_subtitle"),
        "site_icon": config.get("branding", "site_icon"),
        "theme": config.get("ui", "theme"),
        "crew_roles": config.get("crew", "roles"),
    }
    
    return template.render(**context)
```

---

### `curator/web/routes/crew.py`

```python
"""Crew role dashboard routes."""

from fastapi import APIRouter, Query, Depends
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from curator.config import ConfigManager
from curator.web.deps import get_config

router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


@router.get("/crew", response_class=HTMLResponse)
async def crew_dashboard(
    role: str = Query("captain"),
    config: ConfigManager = Depends(get_config)
):
    """Crew dashboard — displays data for the requested role.

    Query parameters:
        role: One of the roles defined in curator.yaml

    Phase 1: Accepts role param, renders template.
    Phase 2: Will load role-specific views from database.
    Phase 3: Will query settings table for user's theme preference.
    """
    crew_roles = config.get("crew", "roles")
    valid_roles = [r["name"] for r in crew_roles]
    
    if role not in valid_roles:
        role = "captain"  # Safe fallback
    
    # Find the role's metadata
    role_meta = next((r for r in crew_roles if r["name"] == role), None)
    
    template = env.get_template("crew.html")
    
    # Phase 2: Replace this with database query for role's view
    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": [],  # Will be populated in Phase 2
        "message": f"Crew dashboard for {role.title()} (Phase 1 — no data yet)"
    }
    
    return template.render(**data)
```

---

### `curator/web/app.py`

```python
"""Curator FastAPI application."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from curator.web.routes import landing, crew

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
)

# Mount static files
STATIC_DIR = Path(__file__).parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include routes
app.include_router(landing.router)
app.include_router(crew.router)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}
```

---

### `curator/templates/base.html`

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

---

### `curator/templates/landing.html`

```html
{% extends "base.html" %}

{% block title %}{{ site_title }} — {{ site_subtitle }}{% endblock %}

{% block content %}
<section class="landing">
    <h1>{{ site_title }}</h1>
    <p class="subtitle">{{ site_subtitle }}</p>

    <div class="crew-cards">
        {% for role in crew_roles %}
        <a href="/crew?role={{ role.name }}" class="crew-card {{ role.name }}">
            <div class="card-image">
                <img src="/static/{{ role.name }}.png" alt="{{ role.title }}">
            </div>
            <h2>{{ role.title }}</h2>
            <p>{{ role.description }}</p>
        </a>
        {% endfor %}
    </div>
</section>
{% endblock %}
```

---

### `curator/templates/crew.html`

```html
{% extends "base.html" %}

{% block title %}{{ role_title }} — Curator{% endblock %}

{% block content %}
<section class="crew-section">
    <div class="crew-header">
        <h1>{{ role_title }}</h1>
        <a href="/" class="btn-back">← Back to Crew</a>
    </div>

    <div class="crew-content">
        {% if records %}
            <table class="records-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Status</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {% for record in records %}
                    <tr>
                        <td>{{ record.name }}</td>
                        <td>{{ record.status }}</td>
                        <td>{{ record.details }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <div class="empty-state">
                <p>{{ message }}</p>
                <p class="hint">Phase 2 will load role-specific views from the database.</p>
            </div>
        {% endif %}
    </div>
</section>
{% endblock %}
```

---

## CSS Structure

### `static/css/base.css`

```css
/* =============================================================================
   Base Styles — Resets, Typography, CSS Variables
   ============================================================================= */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    /* Colors — overridden by theme files */
    --color-primary: #2c3e50;
    --color-accent: #3498db;
    --color-success: #27ae60;
    --color-warning: #f39c12;
    --color-danger: #e74c3c;
    --color-light: #ecf0f1;
    --color-lighter: #f5f7fa;
    --color-border: #bdc3c7;
    --color-text: #2c3e50;
    --color-text-light: #7f8c8d;
    
    /* Spacing */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    --spacing-2xl: 3rem;
    
    /* Borders & Shadows */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.15);
}

html, body {
    height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 16px;
    line-height: 1.6;
    color: var(--color-text);
    background: var(--color-lighter);
}

h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    line-height: 1.2;
}

a {
    color: var(--color-accent);
    text-decoration: none;
    transition: color 0.3s ease;
}

a:hover {
    color: var(--color-primary);
}

footer {
    margin-top: var(--spacing-2xl);
    padding: var(--spacing-xl) 0;
    text-align: center;
    border-top: 1px solid var(--color-border);
    color: var(--color-text-light);
    font-size: 0.9rem;
}
```

---

### `static/css/layout.css`

```css
/* =============================================================================
   Layout — Grid, Flexbox, Container
   ============================================================================= */

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 var(--spacing-lg);
}

.landing {
    padding: var(--spacing-2xl) 0;
    text-align: center;
}

.landing h1 {
    font-size: 2.5rem;
    margin-bottom: var(--spacing-md);
    color: var(--color-primary);
}

.landing .subtitle {
    font-size: 1.25rem;
    color: var(--color-text-light);
    margin-bottom: var(--spacing-2xl);
}

.crew-section {
    padding: var(--spacing-2xl) 0;
}

.crew-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-2xl);
    padding-bottom: var(--spacing-lg);
    border-bottom: 2px solid var(--color-light);
}

.crew-header h1 {
    font-size: 2rem;
    color: var(--color-primary);
}

.btn-back {
    color: var(--color-accent);
    font-weight: 500;
}

.crew-content {
    background: white;
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    box-shadow: var(--shadow-md);
}

@media (max-width: 768px) {
    .landing h1 {
        font-size: 1.75rem;
    }

    .crew-header {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-lg);
    }
}
```

---

### `static/css/components/navbar.css`

```css
/* =============================================================================
   Navigation Bar Component
   ============================================================================= */

.navbar {
    background: white;
    border-bottom: 1px solid var(--color-border);
    box-shadow: var(--shadow-sm);
    position: sticky;
    top: 0;
    z-index: 100;
}

.navbar .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) var(--spacing-lg);
}

.nav-brand a {
    font-size: 1.5rem;
    font-weight: bold;
    color: var(--color-primary);
    text-decoration: none;
}

.nav-brand a:hover {
    color: var(--color-accent);
}

.nav-links {
    display: flex;
    list-style: none;
    gap: var(--spacing-lg);
}

.nav-links a {
    color: var(--color-text-light);
    text-decoration: none;
    transition: color 0.3s ease;
}

.nav-links a:hover {
    color: var(--color-accent);
}
```

---

### `static/css/components/card.css`

```css
/* =============================================================================
   Card Component (Crew Cards on Landing)
   ============================================================================= */

.crew-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: var(--spacing-xl);
    margin: var(--spacing-2xl) 0;
}

.crew-card {
    background: white;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    text-decoration: none;
    color: inherit;
    transition: all 0.3s ease;
    box-shadow: var(--shadow-sm);
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
}

.crew-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
    border-color: var(--color-accent);
}

.crew-card .card-image {
    width: 100%;
    height: 200px;
    margin-bottom: var(--spacing-lg);
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-lighter);
    border-radius: var(--radius-md);
    overflow: hidden;
}

.crew-card .card-image img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.crew-card h2 {
    font-size: 1.25rem;
    margin-bottom: var(--spacing-sm);
    color: var(--color-primary);
}

.crew-card p {
    color: var(--color-text-light);
    font-size: 0.95rem;
}

@media (max-width: 768px) {
    .crew-cards {
        grid-template-columns: 1fr;
    }
}
```

---

### `static/css/components/table.css`

```css
/* =============================================================================
   Table Component
   ============================================================================= */

.records-table {
    width: 100%;
    border-collapse: collapse;
}

.records-table thead {
    background: var(--color-lighter);
    border-bottom: 2px solid var(--color-border);
}

.records-table th {
    padding: var(--spacing-md);
    text-align: left;
    font-weight: 600;
    color: var(--color-primary);
}

.records-table td {
    padding: var(--spacing-md);
    border-bottom: 1px solid var(--color-light);
}

.records-table tbody tr:hover {
    background: var(--color-lighter);
}

@media (max-width: 768px) {
    .records-table {
        font-size: 0.9rem;
    }

    .records-table th,
    .records-table td {
        padding: var(--spacing-sm);
    }
}
```

---

### `static/css/components/empty-state.css`

```css
/* =============================================================================
   Empty State Component
   ============================================================================= */

.empty-state {
    text-align: center;
    padding: var(--spacing-2xl);
    color: var(--color-text-light);
}

.empty-state p {
    margin: var(--spacing-md) 0;
}

.empty-state .hint {
    font-size: 0.9rem;
    font-style: italic;
}
```

---

### `static/css/themes/light.css`

```css
/* =============================================================================
   Light Theme — Default Colors
   ============================================================================= */

:root {
    --color-primary: #2c3e50;
    --color-accent: #3498db;
    --color-success: #27ae60;
    --color-warning: #f39c12;
    --color-danger: #e74c3c;
    --color-light: #ecf0f1;
    --color-lighter: #f5f7fa;
    --color-border: #bdc3c7;
    --color-text: #2c3e50;
    --color-text-light: #7f8c8d;
}

body {
    background: #f8f9fa;
    color: var(--color-text);
}

.crew-card {
    background: white;
}

.crew-content {
    background: white;
}
```

---

### `static/css/themes/dark.css`

```css
/* =============================================================================
   Dark Theme — Inverted Colors
   ============================================================================= */

:root {
    --color-primary: #ecf0f1;
    --color-accent: #3498db;
    --color-success: #2ecc71;
    --color-warning: #f39c12;
    --color-danger: #e74c3c;
    --color-light: #34495e;
    --color-lighter: #2c3e50;
    --color-border: #7f8c8d;
    --color-text: #ecf0f1;
    --color-text-light: #bdc3c7;
}

body {
    background: #1a252f;
    color: var(--color-text);
}

.navbar {
    background: #2c3e50;
    border-bottom-color: var(--color-border);
}

.crew-card {
    background: #34495e;
    border-color: var(--color-border);
}

.crew-content {
    background: #34495e;
    color: var(--color-text);
}

.records-table thead {
    background: #2c3e50;
}

.records-table tbody tr:hover {
    background: #2c3e50;
}
```

---

## Other Files

### `tests/__init__.py`

```python
"""Curator test suite."""
```

---

### `tests/conftest.py`

```python
"""Pytest configuration for Curator tests."""

import pytest


@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from curator.web.app import app
    
    return TestClient(app)
```

---

### `.env`

```
PYTHONUNBUFFERED=1
CURATOR_HOST=localhost
CURATOR_PORT=8080
CURATOR_RELOAD=true
```

---

### `.gitignore`

```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
htmlcov/
.DS_Store
.env
.env.local
*.log
.idea/
.vscode/
*.swp
*.swo
```

---

### `README.md`

```markdown
# Curator v2

The Curator — web UI for the Project Crew.

## Architecture Principles

- **No hardcoding:** All configurable values in YAML or database
- **Modular CSS:** Components separated, themes switchable
- **Database-first:** Use Postgres for dynamic data, YAML for static structure
- **Phase-aware:** Structure ready for evolution (Phase 1 → 3)

## Setup

1. **Create venv:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```

3. **Create `~/.config/dev-utils/config.yaml`:**
   ```yaml
   dbkit:
     host: 100.64.0.7
     port: 5432
     dbname: wcyj
     user: steward
   ```

4. **Update `~/.pgpass`:**
   ```
   100.64.0.7:5432:wcyj:steward:password_here
   chmod 0600 ~/.pgpass
   ```

5. **Copy crew graphics** to `static/`:
   - captain.png
   - curator.png
   - mechanic.png
   - envoy.png
   - scribe.png

## Run

```bash
source venv/bin/activate
uvicorn curator.web.app:app --host localhost --port 8080 --reload
```

Open http://localhost:8080

## Configuration

**`curator/data/curator.yaml`** — All static configuration:
- Branding (title, subtitle, icon)
- Theme selection (Phase 1: hardcoded in config; Phase 3: from settings table)
- Crew roles (names, titles, descriptions)
- Server settings

Everything in this file is read at startup. Change it and restart.

## CSS Structure

```
static/css/
├── base.css              # Resets, typography, variables
├── layout.css            # Grid, flex, containers
├── components/           # Individual components
│   ├── navbar.css
│   ├── card.css
│   ├── table.css
│   └── empty-state.css
└── themes/               # Color overrides
    ├── light.css
    └── dark.css
```

**To add a new component:**
1. Create `static/css/components/mycomponent.css`
2. Add `<link>` in `base.html`
3. Use CSS variables from base.css for colors

**To add a new theme:**
1. Create `static/css/themes/mytheme.css`
2. Override CSS variables
3. Update `curator.yaml` theme setting

## Phases

**Phase 1 (now):** Landing + crew route skeleton
- Landing page reads crew roles from curator.yaml
- `/crew?role={role}` route reads crew metadata from curator.yaml
- Theme selection from curator.yaml

**Phase 2 (next):** Load role-filtered views
- Create PostgreSQL views for each role
- Query appropriate view based on role
- Display records in template

**Phase 3 (after):** User auth + dynamic settings
- Login form validates user
- Settings table stores user preferences (theme, etc.)
- Queries read from settings table instead of YAML
```

---

## Key Improvements

✓ **All hardcoding eliminated** — crew roles, titles, descriptions in curator.yaml  
✓ **CSS modular** — base + components + themes, easy to extend  
✓ **Database-ready** — Phase 3 will replace YAML config with settings queries  
✓ **Theme-ready** — Light/dark themes included, easy to add more  
✓ **Config-driven** — routes read from config.yaml, not hardcoded  

Ready to build?
