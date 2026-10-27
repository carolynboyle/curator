# PostgreSQL `.pgpass` — Fleet Configuration

## Overview

`.pgpass` stores PostgreSQL credentials so client tools (`psql`, `asyncpg`) can
connect without interactive password prompts. The file must be owned by the
connecting user and permissions must be exactly `0600` — Postgres silently
ignores it otherwise.

Format: one entry per line, all five fields required:
```
hostname:port:database:user:password
```
`*` is a wildcard and may be used in any field. First matching entry wins.

---

## Postgres Roles

| Role | Purpose | CREATEDB | Notes |
|---|---|---|---|
| `steward` | Application user — Curator, dbkit connections | No | Owns the `projects` database |
| `floater` | The Supernumerary — test suite and floating admin tasks | Yes | No access to `projects`; owns `test_curator` |
| `postgres` | Superuser | Yes | Peer auth only on steward — use `sudo -u postgres psql`, no password |

Credentials for `steward` and `floater` are in the Proton vault.
The `postgres` superuser has no password — access via OS peer auth only.

---

## pg_hba.conf

Location on steward: `/etc/postgresql/15/main/pg_hba.conf`

Relevant entries (as of 2026-04-19):
```
host    projects    steward    192.168.10.0/24    md5
host    projects    steward    100.64.0.0/10      scram-sha-256
host    all         steward    100.64.0.0/10      scram-sha-256
host    all         floater    100.64.0.0/10      scram-sha-256
```

After any edit: `sudo systemctl reload postgresql`

---

## Fleet `.pgpass` Contents

### steward (`100.64.0.10`)
```
steward:5432:projects:steward:<password>
100.64.0.10:5432:projects:steward:<password>
100.64.0.10:5432:*:floater:<password>
```
Note: `postgres` superuser is not in `.pgpass` — use `sudo -u postgres psql` for admin work.

### mx (daily driver / development machine)
```
steward:5432:projects:steward:<password>
100.64.0.10:5432:projects:steward:<password>
100.64.0.10:5432:*:floater:<password>
```
Fallback machine for direct DB access if wcyjvs2 is unavailable.

### wcyjvs2 (`100.64.0.3`) — Curator web server
```
100.64.0.10:5432:projects:steward:<password>
100.64.0.10:5432:*:floater:<password>
```
No `psql` installed — connections are via `asyncpg` (Curator/dbkit) and pytest.

### wcyjvs1 — Adminer / Directus
```
100.64.0.10:5432:projects:steward:<password>
```
No `floater` entry needed — no test suite runs here.

---

## Verification Commands

Test from any machine that has `psql`:
```bash
# steward user
psql -h steward -U steward -d projects -c "SELECT current_user, current_database();"
psql -h 100.64.0.10 -U steward -d projects -c "SELECT current_user, current_database();"

# floater
psql -h 100.64.0.10 -U floater -d postgres -c "SELECT current_user;"
```

All three should return results without prompting for a password.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Prompted for password despite `.pgpass` existing | Permissions not `0600` — run `chmod 600 ~/.pgpass` |
| Prompted for password despite correct permissions | Host in `.pgpass` doesn't match `-h` argument exactly (`localhost` vs `127.0.0.1` vs IP) |
| `FATAL: no pg_hba.conf entry` | New role not added to `pg_hba.conf` on steward — edit and reload |
| `FATAL: password authentication failed` | Wrong password, or role uses peer auth only (use `sudo -u postgres psql`) |
| `.pgpass` contains garbled entries | Check for stray `echo` or redirect commands that may have appended shell output to the file |

---

## Adding a New Role

1. Create the role in psql (as superuser via `sudo -u postgres psql` on steward):
   ```sql
   CREATE ROLE newrole WITH LOGIN PASSWORD 'password';
   -- Grant CREATEDB if needed:
   ALTER ROLE newrole CREATEDB;
   ```
2. Add a `pg_hba.conf` entry for the appropriate subnet and reload.
3. Add `.pgpass` entries on every machine that needs to connect as that role.
4. Test from each machine.
5. Store credentials in Proton vault.
6. Document the role in `project_crew_roster.md` if it has a crew identity.

---

*Last updated: 2026-04-19*
