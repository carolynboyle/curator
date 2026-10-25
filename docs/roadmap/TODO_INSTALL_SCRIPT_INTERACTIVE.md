# TODO: Interactive install script

**Status:** Not started  
**Related:** `db/install.sh`, `install.conf.example`, `docs/install.md`

---

## Problem

The current install script is a one-shot, non-interactive tool that requires
the user to manually:

- copy and edit `install.conf` before running
- start the containers separately (unless `RUN_COMPOSE=true`)
- create the first admin user by hand via `psql` after the containers are up

This is fine for a developer installing their own instance, but it's friction
for anyone setting up Curator for the first time without reading the install
guide first.

---

## Proposed: `install-interactive.sh`

A guided companion script (keep the existing `install.sh` as the
non-interactive path for automation and CI) that walks the user through setup
step by step.

### Prompts to collect

| Setting | Default | Validation |
|---------|---------|------------|
| `POSTGRES_PASSWORD` | *(none)* | Non-empty; optionally generate one |
| `WEB_APP_USER_PASSWORD` | *(none)* | Non-empty; optionally generate one |
| `APP_PORT` | `8080` | Numeric; probe `lsof -i :PORT` and warn if occupied |
| `APP_HOST` | *(blank)* | Empty (→ `0.0.0.0`) or an IP address |
| `STEWARD_BRANCH` | `main` | Free text |
| `RUN_COMPOSE` | `yes` | y/n |

Port conflict detection should be a first-class check — the most common
configuration mistake on VPS installs is picking a port that's already in use.

### First-user creation

After the containers are healthy, prompt for the first admin account:

```
Create the first admin user? [Y/n]
Username: 
Password: (hidden input)
```

Then run the `INSERT INTO identity.app_user` statement via
`docker compose exec db psql` rather than requiring the user to do it
manually. Role should be `admin` by default (from `identity.user_role`).

### Password generation option

At each password prompt, allow the user to press Enter to auto-generate a
secure random password (e.g. `openssl rand -base64 18 | tr -d '=/+'`).
Print generated passwords to the terminal at the end with a clear "save
these now" warning.

### Post-install summary

Print a summary on success:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Curator is running
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 URL:      http://localhost:8080
 Username: admin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Related: update path

The install script is currently one-shot only. A separate TODO covers the
re-runnable update path (diff-based SQL fetch, manifest tracking, `--force`
flag). See `TODO_INSTALL_SCRIPT_UPDATE_PATH.md` when that note exists, or
look for the "Updating" section in `docs/install.md`.

---

## Out of scope for this TODO

- Web-based admin setup UI (separate product decision)
- Unattended / CI mode (that's what `install.sh` already is)
- Multi-database support beyond wcyj
