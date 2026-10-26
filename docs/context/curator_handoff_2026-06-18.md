# Curator Session Handoff — 2026-06-18

## What We Were Doing

Trying to get Curator running again after a Headscale mesh migration changed all node IPs.
Turned into an architecture planning session. No code was written tonight — decisions only.

---

## Immediate Fix Still Needed (wcyjvs2)

Before Curator can run, two files need manual IP updates on `wcyjvs2`:

**`~/.config/dev-utils/config.yaml`** — change steward host:
- Old: `100.64.0.10`
- New: `100.64.0.7`

**`~/.pgpass`** — change steward entry host:
- Old: `100.64.0.10`
- New: `100.64.0.7`
- Format: `100.64.0.7:5432:projects:steward:<password>`
- Must be `chmod 0600`

`.env` was already updated (`CURATOR_TAILSCALE_IP=100.64.0.6`).

Verify DB connection after updating:
```bash
psql -h 100.64.0.7 -U steward -d projects -c "SELECT current_user, current_database();"
```

Then start Curator:
```bash
docker compose up -d
```

---

## Architecture Decisions Made Tonight

### Principle: Docker Everywhere
All services run in Docker containers. No bare-metal service installs going forward.
Container definitions live in `dev-utils/containers/`, one directory per service.

### Target node roster (current mesh IPs)

| Hostname   | IP           | Role                                        |
|------------|--------------|---------------------------------------------|
| wcyj-meet  | 100.64.0.1   | VPS (Hetzner) — future Curator + PG primary |
| wcyjvs2    | 100.64.0.6   | Proxmox VM — current/future Curator standby |
| steward    | 100.64.0.7   | Debian LXC — current/future PG standby      |

### Postgres: migrate to Docker on steward first
- `steward` keeps its hostname and IP — nothing changes externally
- Bare PostgreSQL 15.16 replaced with `postgres:15` container
- Same container definition will deploy to `wcyj-meet` (VPS) as primary
- Container definition goes in `dev-utils/containers/postgres/`

### Curator: same container, two deployments
- Current `curator` container definition moves to `dev-utils/containers/curator/`
- Deploys to `wcyjvs2` now (local only, validate first)
- Deploys to `wcyj-meet` once local is confirmed working

### Replication
- PostgreSQL streaming replication: `wcyj-meet` (primary) → `steward` (standby)
- Manual failover — no Patroni/repmgr for now
- Both Curator instances point at whichever Postgres is primary
- On failover: promote steward, update Curator config, restart

### Deployment sequence
1. Containerize Postgres on `steward` (local, validate)
2. Verify Curator on `wcyjvs2` still works against containerized Postgres
3. Set up `wcyj-meet` (Docker install, mesh already joined as node 1)
4. Deploy Postgres container to `wcyj-meet` as primary
5. Configure streaming replication wcyj-meet → steward
6. Deploy Curator container to `wcyj-meet` as primary instance

---

## curator_init.py — Planned, Not Yet Written

A role-aware first-run/reconfiguration script. Replaces the current manual process
of hunting down which files need updating after a mesh IP change.

**Writes all three required files in one pass — no separate steps:**
1. `~/.config/dev-utils/config.yaml` (dbkit DB connection)
2. `~/.pgpass` (password, 0600 permissions — non-negotiable, always written)
3. `.env` (CURATOR_TAILSCALE_IP for Docker port binding)

**Role-aware prompts:**
- What role is this node? (`primary` / `standby`)
- What is the Postgres primary's mesh IP?
- DB name, user, password
- This host's Tailscale IP

**Ends with a live DB connection verification** before declaring success.

Existing `setup.py` (dbkit config) and `pgpass.py` logic will be absorbed into this script
rather than duplicated.

---

## dev-utils/containers/ additions needed

```
containers/
├── postgres/
│   ├── docker-compose.yml
│   └── README.md
├── curator/
│   ├── docker-compose.yml
│   ├── Dockerfile        (move from curator repo)
│   └── README.md
```

---

## Next Session Priorities

1. **Write `curator_init.py`** — design the role-aware flow, then implement
2. **Design `containers/postgres/`** — compose file for Postgres 15, replication-ready config
3. **Migrate steward** from bare Postgres to containerized Postgres
4. **Verify** Curator on wcyjvs2 still connects correctly

---

## Key Facts to Remember

- `wcyj-meet` is the Hetzner VPS (not just the coordination server — it's also mesh node 1)
- `steward` has no `.pgpass` currently — it disappeared, password is in Proton vault
- `wcyj-meet` needs Docker installed (clean rebuild happened, nothing is there yet)
- Postgres version on steward: **15.16** → use `postgres:15` image
- Headscale registration always requires `:443` explicit port — never `:8080`
