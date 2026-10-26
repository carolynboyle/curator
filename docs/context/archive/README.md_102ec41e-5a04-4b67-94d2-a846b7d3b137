# The Curator

Part of [Project Crew](https://github.com/carolynboyle/dev-utils) — a personal infrastructure toolset with a nautical naming theme.

The Curator is a FastAPI web application for managing project information stored in PostgreSQL. It surfaces data from the Steward database through a browser UI built with Jinja2 templates, HTMX for partial-page updates, and PicoCSS for styling.

The Curator is self-referential: it tracks its own development as a project in the database it manages.

---

## Stack

- **Python 3.11** / FastAPI / uvicorn
- **Jinja2** templates + **HTMX** for partial-page updates
- **PicoCSS** for styling
- **PostgreSQL 15** on Steward (dedicated LXC)
- **dbkit** — async PostgreSQL connection management (from dev-utils)
- **viewkit** — YAML-driven SQL query and view definitions (from dev-utils)

---

## UI

The primary entry point is the kanban-style board at `/projects/board`. A project tree is displayed in the left panel; clicking a project loads its detail panel on the right via HTMX. All CRUD operations return to the board — there are no standalone detail pages.

---

## Runtime Configuration

No credentials are baked into the image. The following files must exist on the host before running:

| File | Purpose |
|---|---|
| `~/.config/dev-utils/config.yaml` | DB host, port, dbname, user (read by dbkit) |
| `~/.pgpass` | DB password — must be `chmod 0600` |
| `.env` | `CURATOR_TAILSCALE_IP` — host IP to bind the container port to |

An optional `~/.config/curator/curator.yaml` can override app defaults.

---

## Running with Docker

```bash
cp .env.example .env   # set CURATOR_TAILSCALE_IP to your host's mesh IP
docker compose up -d
```

To rebuild after code changes:

```bash
docker compose up --build -d
```

---

## Development

For local development without Docker, install dependencies and run uvicorn directly:

```bash
pip install -e ".[test]"
PYTHONPATH=src uvicorn curator.web.app:app --host localhost --port 8080 --reload
```

A machine-specific `go.sh` startup script can be created for convenience — it is gitignored.

---

## Project Crew

| Member | Role |
|---|---|
| The Curator | This app — web UI and information management |
| The Steward | PostgreSQL — database appliance |
| dbkit | Async PostgreSQL connection management |
| viewkit | YAML-driven SQL queries and view definitions |
| Fletcher | Remote provisioning and version management |
| Dr. Filewalker | Filesystem documentation and diffing |
