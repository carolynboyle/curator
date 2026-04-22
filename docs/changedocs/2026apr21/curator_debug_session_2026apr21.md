# Curator Debug Session — 2026-04-21

## Summary

Debugging session to resolve notes field not saving in the Curator web UI,
plus environment issues encountered when switching from Alma Linux to MX Linux.

---

## The Notes Bug — Investigation

### Symptom
Notes entered in the project edit form appeared to save (303 redirect, no errors)
but the field showed NULL in the database and blank in the UI.

### Full Stack Reviewed (all clean)
- `views.yaml` — `notes` field present in both projects and tasks view definitions
- `templates/projects/form.html` — `<textarea name="notes">` correct
- `templates/tasks/form.html` — `<textarea name="notes">` correct
- `templates/projects/_panel.html` — notes field present in both panel form and display
- `web/routes/projects.py` — route receives `notes: str = Form("")` and passes to repo
- `web/routes/tasks.py` — same, correct
- `db/projects.py` — `update()` includes notes in correct tuple position
- `db/tasks.py` — same, correct
- `queries.yaml` — notes included in both projects.update and tasks.update SQL
- `db/base.py` — thin pass-through, no issues
- `dbkit/connection.py` — commit logic correct in `__aexit__`

### Root Cause (likely)
The Alma Linux VM (`wcyjvs1`) was running a stale version of the code that
predated the notes refactor. The database on steward was being written to by
old code that didn't include notes in the update tuple. When the session moved
to MX (`wcyjv10`) running the current codebase, notes saved correctly immediately.

### Confirmed Working
- Debug print confirmed note value arriving at route: `DEBUG notes='These notes are a pain'`
- Adminer confirmed value written to database
- Edit form confirmed value read back correctly
- Board panel confirmed value displayed correctly
- Task notes also confirmed working

---

## Environment Issues Encountered

### Issue 1: Tailscale IP not available on wcyjv10
`go.sh` hardcoded `--host 100.64.0.3` (wcyjvs2's IP). wcyjv10 is `100.64.0.11`.

**Fix:** Run uvicorn with `--host localhost` for local development:
```bash
uvicorn curator.web.app:app --host localhost --port 8080
```

### Issue 2: Missing dbkit config section
`~/.config/dev-utils/config.yaml` existed on wcyjv10 but had no `dbkit:` section.
This is a **setupkit bug** — setup should create this section automatically.

**Manual fix applied:**
```yaml
dbkit:
  host: 100.64.0.10
  port: 5432
  dbname: projects
  user: steward
```

**Bug logged:** setupkit needs to write the `dbkit:` section to config during setup.

### Issue 3: pg_hba.conf — wrong username
Initial config used `user: carolyn` (the Linux username). The PostgreSQL role
on steward is `steward`, not `carolyn`. The `100.64.0.0/10` subnet is already
authorized for the `steward` user in `pg_hba.conf`.

**Fix:** Change config to `user: steward`.

---

## Other Bugs Identified (not fixed this session)

### Bug: `update_project` route missing `loader`
In `web/routes/projects.py`, the `update_project` route instantiates:
```python
repo = ProjectRepository(db)  # missing loader
```
All other routes pass `loader`. This is inconsistent and should be fixed,
though it doesn't affect current functionality since `update()` uses inline SQL.

### Bug: `target_date` missing from projects INSERT
In `db/projects.py`, the `create()` method's INSERT statement omits `target_date`
from the column list despite passing it in the values tuple (or vice versa).
Needs audit.

---

## Infrastructure Reference

| Hostname  | Tailscale IP   | Role                        |
|-----------|----------------|-----------------------------|
| steward   | 100.64.0.10    | PostgreSQL database server  |
| wcyjvs1   | 100.64.0.9     | Alma Linux — primary web server |
| wcyjv10   | 100.64.0.11    | MX Linux — dev workstation  |
| wcyjvs2   | 100.64.0.3     | (was hardcoded in go.sh)    |

---

## Next Steps (deferred from this session)

- Fix `go.sh` to use `localhost` or detect the correct Tailscale IP dynamically
- Fix setupkit to write `dbkit:` config section on setup
- Fix `update_project` route to pass `loader` for consistency
- Audit `create()` in `db/projects.py` for `target_date` in INSERT
- Resume original work: confirm notes saving via panel inline edit (HTMX path)
