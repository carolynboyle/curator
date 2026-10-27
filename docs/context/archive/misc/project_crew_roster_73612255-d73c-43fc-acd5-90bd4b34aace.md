# Project Crew — Crew Roster & Design Notes

## The Metaphor

Project Crew uses a tall-ship sailing crew as its organizing metaphor. Each component of the system is a named crew member with a distinct role and domain. Crew members do not step on each other's responsibilities, but work together toward the same destination.

Shared utilities (the "kits") are not crew members — they are the shared equipment locker that crew members draw from as needed.

---

## The Crew

### The Shipwright
**Role:** Project scaffolding and setup

The Shipwright builds the vessel before it leaves port. Responsible for creating new project structures — folder layout, `.gitignore`, editor config, and other setup tasks. The Shipwright's job is done before the ship leaves; they hand the project over to the crew and step back.

*Refactored from the original `projs` CLI package. The Builder engine will be separated from the launch/orchestration functions during refactor.*

---

### The Pilot
**Role:** Project launch and environment activation

In the 19th century, a Harbor Pilot came aboard specifically to navigate a ship out of port and get it underway. The Pilot handles launching a project into its working environment: changing to the correct directory, starting a tmux session, activating the virtual environment, launching the selected editor, and running custom startup commands. Once everything is running, the Pilot's job is done.

*To be separated from the Shipwright during the `projs` refactor.*

---

### The Steward
**Role:** Database container and data management

The Steward tends the ship's stores — provisions, inventory, and the integrity of what's held aboard. In Project Crew, the Steward is the PostgreSQL container (`steward` LXC on Proxmox). The Steward's responsibilities include:

- Hosting and maintaining PostgreSQL databases
- Schema migrations
- Database health checks
- Data export and backup

**Backup strategy (planned):**
Backup type and destination are defined in YAML config. Supported destination types:

| Destination | Formats allowed |
|---|---|
| `git` | CSV only — pg_dump to git is a hard error |
| `local` | CSV, JSON, pg_dump |
| `gdrive` | CSV, JSON, pg_dump |

The Steward's backup scripts read from YAML config and validate destination/format combinations before running. Attempting to send a pg_dump to a git destination produces an explicit refusal, not a warning.

*The Steward container currently hosts the projects database and a draft LAN infrastructure/Ansible coordination database.*

---

### The Supernumerary
**Role:** Floating privilege — scoped, temporary, cross-cutting tasks

*Known aboard as* **`floater`** *(the Postgres account name, and the nickname any working crew would actually use).*

On a tall ship, a supernumerary is carried on the muster roll but holds no fixed station. They are present for a purpose — a specialist, a passenger, an observer — and when that purpose is done, they disembark. They are not part of the permanent establishment.

In Project Crew, the Supernumerary is a Postgres role (`floater`) with tightly bounded privileges and no fixed home database. Current duties:

- **Test database ownership** — `floater` creates and owns `test_curator`, giving the integration test suite a clean, isolated target with no access to production data
- **Scoped to its lane** — `CREATEDB` only; no `SUPERUSER`, no `CREATEROLE`, no access to `projects` or any other live database

**Privileges granted:**

| Privilege | Why |
|---|---|
| `LOGIN` | Must connect to Postgres |
| `CREATEDB` | Bootstrap and teardown of test databases |
| No access to `projects` | Hard boundary — isolation by design |

**Credentials:** Password in `~/.pgpass` on `wcyjvs2`. No secrets in code or config.

*As the system grows, `floater` may take on other floating duties — staging migrations, destructive seed operations, or any task requiring temporary elevated scope that the `steward` user should not hold permanently.*

---

### The Curator
**Role:** Web UI and information management

The Curator manages the information held in the Steward's databases, surfacing it through a web interface. Built with FastAPI and Jinja2, backed by PostgreSQL on Steward. Views are driven by YAML configuration via `viewkit`, with `dbkit` handling async database connections.

The Curator is a subproject of Project Crew and is tracked in its own database record — it eats its own dog food.

*Repo: `curator`. Currently operational for CRUD on the projects database.*

---

### Dr. Filewalker
**Role:** Filesystem documentation and diffing

Dr. Filewalker walks a project filesystem tree and generates:

- `manifest.yml` — inventory of non-binary files
- `project-tree.txt` — complete filesystem snapshot
- Syntax-highlighted markdown documentation from source files

Fletcher consumes `manifest.yml` to generate raw GitHub URLs, saved as `manifest.fletch`.

The saved filesystem snapshots can be diffed over time, enabling change detection and audit trails without requiring full git history. This makes Dr. Filewalker a potential telemetry source for the Durin Observatory project.

**Planned refactors:**
1. Bring codebase into conformance with `project_rules.md` (written before the rules existed)
2. Externalize hard-coded values to `data/` YAML
3. Add missing unit tests
4. Add filesystem diffing as new functionality (with tests from the start)

*Repo: `doc-gen` (character name Dr. Filewalker). Has its own repo due to complexity.*

---

### Fletcher
**Role:** Remote provisioning and version management

Fletcher is the crew's quartermaster — handles procurement and keeps the kit current. At install time, a plugin checks its source repo for version information. If a newer version exists, Fletcher downloads it via a raw GitHub URL generated from `manifest.fletch`.

Fletcher also records the version from `pyproject.toml` in the manifest it generates, and sets `__init__.py` version from the same source rather than hard-coding it.

*Lives in `dev-utils`. Works as both a standalone tool and a Project Crew plugin.*

---

### The Bosun
**Role:** Git operations

The Bosun is responsible for the ship's lines — what's connected to what, and managing what goes ashore and what comes aboard. In Project Crew, the Bosun handles git operations: push, pull, branch management, stash, rebase.

*Planned plugin. Character art exists (see `/docs/art/bosun.png`).*

---

### The Purser
**Role:** Secrets and credentials management

The Purser kept the coin purse for the ship — the keeper of the keys. In Project Crew, the Purser handles secrets, credentials, keychain integration, and access to secured resources including the headscale mesh.

Implements the secrets rules from `project_rules.md`:
- Secrets never in code or config files
- Secrets never in the manifest
- System keychain (`keyring` in Python) as the default store
- No hidden background processes — all credential operations are explicit and visible

*Planned plugin. Character art exists (see `/docs/art/purser.png`).*

---

### The MCP Envoy
**Role:** Model Context Protocol bridge

The Envoy carries context between systems — a Victorian-era traveler arriving with a glowing manifest of servers and routing information. Handles MCP server integration and context protocol bridging.

*Planned. Character art exists (see `/docs/art/mcp_envoy.png`).*

---

## The Kits (Shared Equipment)

The kits live in `dev-utils` and are the shared equipment locker. They are not crew members — they are tools any crew member can draw from.

| Kit | Purpose |
|---|---|
| `menukit` | YAML-driven menu construction — menus change without touching code |
| `dbkit` | Generic async database connector (PostgreSQL and SQLite) |
| `viewkit` | YAML-driven web view configuration for FastAPI/Jinja2 |

---

## Commit Message Conventions

Project Crew uses nautical terms as commit types, drawn from actual sailing vocabulary so the terms carry meaning in both contexts.

| Type | Meaning | Maps to |
|---|---|---|
| `launch` | First working version, leaving the dock | Initial release / first working state |
| `trim` | Adjusting for better performance | UX improvements, optimization, polish |
| `patch` | Quick repair | Bug fixes, typo corrections |
| `refit` | Modifying equipment for broader use | Refactoring, extending existing functionality |
| `provision` | Supplying the ship before departure | Setup scripts, config scaffolding |
| `stow` | Putting things in their proper place | Generated artifacts, file organization |
| `chart` | Adding navigational information | Schema changes, migrations, documentation |

*This vocabulary is evolving from actual use. A complete conventions document will be written once enough real examples exist to make the patterns obvious.*

---

## Future Projects

### Durin Observatory
A graphical web UI wrapping around the full Project Crew ecosystem. Each device on the LAN is a "star" on a Star Map. Dr. Filewalker's filesystem diffs generate telemetry — for example, rapidly increasing storage use causes a star to render in red. Mermaid handles the map rendering.

Named for Durin of Tolkien's legendarium — a separate metaphor register from the nautical Project Crew vocabulary, appropriate for the observability/infrastructure layer.

---

*This document generated from conversation. Last updated: 2026-04-19.*
