# Curator Companion App — Design Notes

**Date**: 2026-06-25  
**Status**: Concept / early thinking

---

## Background

`projs` is a menu-driven CLI tool that automates new project setup:
collects repo-specific information (name, preferred editor, etc.),
creates repo structure, writes `.gitignore`, inits git, activates venv,
and opens the project in the preferred editor. Per-project settings are
stored in YAML configs.

`projs` has been dormant because database records (via Curator) are
preferable to YAML configs as a source of truth. The two tools are
expected to eventually converge.

---

## The Convergence Model

**Curator web UI** is the source of truth for project records — what
exists, its status, type, tasks, notes. PostgreSQL is the canonical
store.

**Qt companion app** reads from the same `wcyj` database and handles
local filesystem operations that a browser-based web app cannot perform
due to security constraints:

- Create repo structure via treekit
- Write `.gitignore`
- Init git
- Set up and activate venv
- Open project in preferred editor
- Prompt "scaffold this locally?" when a new project appears in the database

---

## Why Qt

A web app cannot touch the local filesystem or spawn CLI processes
directly. Three options were considered:

- **Qt app** — native companion, reads wcyj database, triggers local
  operations, can display Curator crew interface natively. Clean
  separation: web for data, native app for filesystem ops. Most work
  but most polished long-term.
- **Local API bridge** — small FastAPI/Flask process on localhost that
  Curator web calls. Browser security allows same-machine calls. Simpler
  but less polished.
- **CLI daemon** — watches wcyj database for new projects and triggers
  local operations automatically. No UI, closest to original `projs`.

Qt is the preferred direction for the long term.

---

## Data Migration

The per-project YAML configs that `projs` currently uses become project
records in `wcyj`. The Qt companion reads project configuration from the
database instead of from YAML files. This eliminates the config drift
problem and makes Curator the single source of truth.

---

## Foundation Already in Place

- `curator_init.py` (planned) — writes `.pgpass`, `config.yaml`,
  verifies DB connection. This is the first piece the Qt companion
  would build on.
- `treekit` — directory scaffolding tool, already exists in dev-utils.
  The Qt app calls treekit for repo structure creation.
- `wcyj` database — already stores project records with type, status,
  and metadata. Qt app queries this directly.

---

## Possible Name

Nautical options: **Bosun** (already noted as a future git ops role),
**Rigger** (sets up the structure before launch). TBD.

---

## Next Steps (when ready)

1. Define what project-level metadata the Qt app needs from wcyj
2. Determine Qt framework (PyQt6 vs PySide6)
3. Build basic db connection + project list view in Qt
4. Wire treekit scaffolding to project creation event
5. Replace `projs` YAML configs with wcyj database reads
