# project-structure.md

**Path:** docs/project-structure.md
**Syntax:** markdown
**Generated:** 2026-04-13 04:51:40

```markdown
curator/
├── .gitignore
├── README.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
│
├── curator/
│   ├── __init__.py
│   ├── config.py                      # ConfigManager — finds and loads curator.yaml
│   ├── exceptions.py                  # CuratorError hierarchy
│   │
│   ├── data/                          # Shipped defaults
│   │   ├── curator.yaml               # App defaults (page size, etc.)
│   │   └── views.yaml                 # YAML-driven form/column definitions
│   │
│   ├── db/                            # Database layer — one class per resource
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseRepository — shared async query helpers
│   │   ├── projects.py                # ProjectRepository
│   │   ├── tasks.py                   # TaskRepository
│   │   ├── tags.py                    # TagRepository
│   │   └── files.py                   # FileRepository
│   │
│   ├── web/                           # FastAPI app
│   │   ├── __init__.py
│   │   ├── app.py                     # App factory, lifespan, mounts static/templates
│   │   ├── deps.py                    # FastAPI dependencies — db connection, config
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── projects.py
│   │       ├── tasks.py
│   │       ├── tags.py
│   │       ├── files.py
│   │       └── export.py              # CSV export endpoints
│   │
│   └── templates/                     # Jinja2 templates
│       ├── base.html                  # Layout, nav, WCYJ palette
│       ├── partials/                  # HTMX partial responses
│       │   ├── project_row.html
│       │   ├── task_row.html
│       │   └── confirm_delete.html
│       ├── projects/
│       │   ├── list.html
│       │   ├── detail.html
│       │   └── form.html
│       └── tasks/
│           ├── list.html
│           └── form.html
│
├── static/
│   └── curator.css                    # Pico base + WCYJ theme variables
│
└── tests/
    ├── conftest.py                    # Shared fixtures
    ├── test_config.py
    ├── test_db_projects.py
    ├── test_db_tasks.py
    └── test_routes_projects.py
```
