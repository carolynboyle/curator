# Change: Remove `read_only: true` from pgAdmin Compose

**File:** `dev-utils/containers/pgadmin/docker-compose.yml`  
**Also applies to:** `curator/tools/pgadmin/docker-compose.yml`  
**Commit type:** `patch`

---

## Why

pgAdmin writes to several paths inside its own install directory at container
startup — specifically `/pgadmin4/config_distro.py` and `/var/log/pgadmin`.
These writes happen before the application is running and cannot be redirected
via environment variables.

`read_only: true` prevents all filesystem writes to the container root.
Mounting the affected paths as `tmpfs` is not a viable workaround because
mounting `/pgadmin4` as tmpfs wipes the entire application tree (all Python
source files live there), and the full set of paths pgAdmin needs to write
at runtime is not documented and changes between versions.

## Decision

Remove `read_only: true` from the pgAdmin compose file. All other hardening
remains in place:

- Port bound to Tailscale IP only
- All Linux capabilities dropped (`cap_drop: ALL`)
- `no-new-privileges: true`
- Memory and CPU limits
- Named network isolation
- No credentials in compose file

## Risk assessment

pgAdmin is a dev/maintenance tool accessible only via the Headscale mesh.
It is not internet-facing. The remaining hardening measures meaningfully
reduce blast radius without breaking the application.

`read_only: true` is appropriate for stateless application containers
(like Curator) but incompatible with pgAdmin's startup behavior.

---

## BEFORE

```yaml
    # -------------------------------------------------------------------------
    # Filesystem hardening
    # -------------------------------------------------------------------------
    read_only: true
    tmpfs:
      - /tmp:mode=1777
      - /run:mode=755,uid=5050,gid=5050
      - /var/log/pgadmin:mode=755,uid=5050,gid=5050
```

## AFTER

```yaml
    # -------------------------------------------------------------------------
    # Filesystem hardening
    # -------------------------------------------------------------------------
    # read_only: true is intentionally omitted -- pgAdmin writes to
    # /pgadmin4/config_distro.py and /var/log/pgadmin at startup and cannot
    # run with a read-only root filesystem. All other hardening is applied.
    tmpfs:
      - /tmp:mode=1777
      - /run:mode=755,uid=5050,gid=5050
      - /var/log/pgadmin:mode=755,uid=5050,gid=5050
```

---

## Additional changes made during setup

**`steward:/etc/postgresql/15/main/pg_hba.conf`** — added entry to allow
the `postgres` superuser to connect over TCP from the mesh:

```
host    all             postgres        100.64.0.0/10           scram-sha-256
```

This is required for pgAdmin to connect as superuser. The `postgres` role
previously had no TCP password and could only authenticate via Unix socket
peer auth. A password was set via `sudo -u postgres psql -c "\password postgres"`
and stored in Proton vault.
