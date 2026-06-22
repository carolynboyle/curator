# Curator v2 — Repository Structure

```
curator/
├── .gitignore
├── .env.example
├── README.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
│
├── docs/
│   ├── design/
│   └── change/
│
├── src/
│   └── curator/
│       ├── __init__.py
│       ├── config.py
│       ├── exceptions.py
│       │
│       ├── data/
│       │   └── curator.yaml
│       │
│       ├── db/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── contacts/
│       │   │   ├── __init__.py
│       │   │   ├── organizations.py
│       │   │   └── contacts.py
│       │   └── projects/
│       │       ├── __init__.py
│       │       ├── projects.py
│       │       └── tasks.py
│       │
│       ├── web/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── deps.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── contacts.py
│       │       ├── organizations.py
│       │       └── projects.py
│       │
│       └── templates/
│           ├── base.html
│           ├── index.html
│           ├── partials/
│           ├── contacts/
│           ├── organizations/
│           └── projects/
│
├── static/
│   ├── curator.css
│   └── img/
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   ├── __init__.py
    │   └── conftest.py
    └── integration/
        ├── __init__.py
        └── conftest.py
```
