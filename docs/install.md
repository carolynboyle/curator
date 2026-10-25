# Curator — Install Guide

Curator is a containerised FastAPI + PostgreSQL web application managed with
Docker Compose. This guide covers a fresh install on any Linux host or macOS
development machine.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Git** | To clone the repo |
| **Docker** + **Docker Compose** | Docker Desktop on macOS; on Linux install `docker-ce` and the `docker-compose-plugin`. Colima (`brew install colima docker && colima start`) is a lighter alternative on macOS. |
| **curl** | Pre-installed on macOS and most Linux distros |
| **bash** | macOS's built-in bash 3.2 is fine — no upgrade needed |

---

## 1 — Clone the repo

```bash
git clone https://github.com/carolynboyle/curator.git
cd curator
```

---

## 2 — Create install.conf

```bash
cp install.conf.example install.conf
```

Open `install.conf` in any editor and fill in the values.

**Minimum required:**

| Key | Description |
|-----|-------------|
| `POSTGRES_PASSWORD` | Password for the `steward` database superuser |
| `WEB_APP_USER_PASSWORD` | Password for the lower-privilege `web_app_user` role |

**Worth checking before you run:**

| Key | Default | Notes |
|-----|---------|-------|
| `APP_PORT` | `8080` | The host port the app will listen on. Check it is free first (`lsof -i :8080`). Change it if something else is already there. |
| `APP_HOST` | *(blank → `0.0.0.0`)* | Leave blank for local installs. On a VPS accessible via Tailscale only, set this to your Tailscale IP (e.g. `100.64.0.1`) to prevent the app from binding on the public interface. |
| `RUN_COMPOSE` | `false` | Set to `true` to start the containers automatically at the end of the install. |
| `STEWARD_BRANCH` | `main` | Change to a development branch to test against a different SQL version. |

> `install.conf` is deleted automatically when the script completes — its
> absence confirms the install has run. It contains secrets; never commit it.

---

## 3 — Run the install script

```bash
bash db/install.sh
```

The script:
1. Validates your `install.conf` values
2. Writes `.env` for Docker Compose
3. Fetches the 21 SQL init files from the steward repo into `db/init/`
4. Optionally starts the containers (if `RUN_COMPOSE=true`)
5. Deletes `install.conf`

Successful output ends with:

```
  SQL files written to db/init/.
Install complete. install.conf removed.
When ready: docker compose up --build -d
```

(Or "Containers started." if you set `RUN_COMPOSE=true`.)

---

## 4 — Start the containers (if you didn't set RUN_COMPOSE=true)

```bash
docker compose up --build -d
```

The first build downloads base images and installs Python dependencies —
allow a few minutes. Subsequent starts use the cached image and are fast.

---

## 5 — Verify

```bash
docker compose ps
```

Both services should show as running and the `db` service as `(healthy)`:

```
NAME           SERVICE   STATUS           PORTS
curator-app-1  app       Up               0.0.0.0:8080->8080/tcp
curator-db-1   db        Up (healthy)     5432/tcp
```

Open a browser and navigate to `http://localhost:8080` (or whatever port you
set). You should see the Curator login page.

To watch the database initialisation logs:

```bash
docker compose logs -f
```

All 21 SQL files should run without any `ERROR` lines.

---

## 6 — First login

No default user is created by the seed data. Create the first admin account
directly in the database:

```bash
docker compose exec db psql -U steward -d wcyj
```

Insert the user with a bcrypt-hashed password (pgcrypto is loaded by the init
scripts):

```sql
INSERT INTO identity.app_user (username, password_hash, role_id)
VALUES (
    'admin',
    crypt('yourpassword', gen_salt('bf')),
    (SELECT id FROM identity.user_role WHERE name = 'admin')
);
\q
```

Replace `yourpassword` with your chosen password before running. You can now
log in at `http://localhost:PORT` with those credentials.

---

## 7 — Updating an existing install

The install script is a **one-shot fresh install** only. It does not update a
running database. To apply schema changes to an existing container you must
stop the stack, drop the volume, and re-run the install — which destroys all
data.

```bash
docker compose down -v --rmi all   # wipes data
bash db/install.sh                 # re-fetches SQL and rebuilds
```

A re-runnable update path (diff-based fetch, `--force` flag, manifest
tracking) is planned. An interactive guided install (with port-conflict
detection and first-user creation) is also on the roadmap. See
`docs/roadmap/TODO_INSTALL_SCRIPT_INTERACTIVE.md`.

---

## Troubleshooting

**`docker: command not found` after installing Docker Desktop**
The terminal session was opened before Docker Desktop started. Open Docker
Desktop first (wait for the whale in the menu bar), then open a new terminal.

**`ports are not available: … bind: can't assign requested address`**
The `APP_HOST` in your `.env` is set to an IP that doesn't exist on this
machine. Edit `.env`, clear `APP_HOST`, and restart: `docker compose up -d`.

**DB init fails with `role "web_app_user" does not exist`**
The `db/init/` SQL files are from an older version of steward. Wipe and
reinstall: `docker compose down -v`, then re-run `bash db/install.sh` after
recreating `install.conf`.

**`localhost:PORT` refused to connect**
Check that both containers are running (`docker compose ps`). If the app
container is absent or restarting, check `docker compose logs app` for the
error.
