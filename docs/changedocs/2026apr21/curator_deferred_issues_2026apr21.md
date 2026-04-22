# Curator — Deferred Issues & Technical Debt
# 2026-04-21

---

## 1. Redirect Targets After Save/Delete

### Problem
Many routes redirect to hardcoded URLs (detail page or list page) instead of
respecting a `next_url` parameter. This sends users to the wrong place when
they arrived from the board.

### Fix Pattern
The projects edit form already handles this correctly — pass `next_url` as a
hidden field in the form, read it in the route, use it in `RedirectResponse`.

### Affected Routes

#### projects.py
| Line | Current redirect | Should be |
|------|-----------------|-----------|
| 317  | `/projects/` (delete) | `/projects/board` or `next_url` |

#### tasks.py
| Line | Current redirect | Should be |
|------|-----------------|-----------|
| 180  | `/projects/{slug}` (create) | `next_url` |
| 247  | `/projects/{project_slug}` (update) | `next_url` |
| 324  | `/projects/{project_slug}?delete_blocked=...` | `next_url` with params |
| 328  | `/projects/{project_slug}` (delete) | `next_url` |
| 339  | `/projects/{project_slug}` (force delete) | `next_url` |

#### files.py
| Line | Current redirect | Should be |
|------|-----------------|-----------|
| 110  | `/projects/{project_slug}` (create, has slug) | `next_url` |
| 111  | `/projects/` (create, no slug) | `next_url` or board |
| 180  | `/projects/{project_slug}` (update, has slug) | `next_url` |
| 181  | `/projects/` (update, no slug) | `next_url` or board |
| 193  | `/projects/{project_slug}` (delete, has slug) | `next_url` |
| 194  | `/projects/` (delete, no slug) | `next_url` or board |

#### tags.py
| Line | Current redirect | Notes |
|------|-----------------|-------|
| 75   | `/tags/` (create) | Probably correct — tags aren't project-specific |
| 117  | `/tags/` (update) | Probably correct |
| 127  | `/tags/` (delete) | Probably correct |

### Required Template Changes
Task and file forms need a `next_url` hidden field added, mirroring what
the project form already does:
```html
<input type="hidden" name="next_url" value="{{ next_url }}">
```
And the corresponding route GET handlers need to pass `next_url` in context,
set to the referer or a sensible default (the board).

---

## 2. Double-Submit Prevention

### Problem
Clicking the submit button twice (or hesitating before redirect completes)
creates duplicate records. The slug deduplication logic handles the slug
correctly but still creates two database rows.

### Planned Fix
Disable and relabel the submit button on first click:
```javascript
document.querySelector('.curator-form').addEventListener('submit', function() {
    var btn = this.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Saving...';
});
```
Add to base template or individual form templates. Low priority.

---

## 3. setupkit Bug — Missing dbkit Config Section

### Problem
`setupkit` does not write the `dbkit:` section to
`~/.config/dev-utils/config.yaml` during setup. The section must be added
manually on each new machine.

### Required Fix
setupkit setup script should write:
```yaml
dbkit:
  host: <host>
  port: 5432
  dbname: projects
  user: steward
```
Prompting for host during setup if not already configured.

---

## 4. update_project Route Missing loader

### Problem
In `web/routes/projects.py`, the `update_project` POST handler instantiates
`ProjectRepository(db)` without passing `loader`, unlike every other route.

```python
repo = ProjectRepository(db)  # should be ProjectRepository(db, loader)
```

Not currently causing visible bugs since `update()` uses inline SQL, but
inconsistent and will matter if update is ever refactored to use the query loader.

### Fix
Add `loader: QueryLoader = Depends(get_query_loader)` to the route signature
and pass it to the repository constructor.

---

## 5. target_date Missing from projects INSERT

### Problem
In `db/projects.py`, the `create()` method's INSERT statement may be missing
`target_date` from the column list. Needs audit against the values tuple.

### Fix
Audit `create()` in `db/projects.py` and ensure column list and values tuple
match exactly, including `target_date`.

---

## 6. go.sh Hardcoded to Specific Tailscale IP

### Problem
`go.sh` hardcodes `--host 100.64.0.3` (wcyjvs2's IP). This breaks on any
other machine.

### Planned Fix
Either use `--host 0.0.0.0` to bind all interfaces, or detect the correct
IP dynamically. Access restriction is handled at the network/pg_hba level,
not by binding to a specific IP.

### Current Workaround
Run uvicorn manually: `uvicorn curator.web.app:app --host localhost --port 8080`

---

## 7. Security Hardening — Website (wcyjvs2)

### Context
wcyjvs2 will host a politically-oriented online magazine and is expected to
attract hostile traffic once live.

### Tasks
- [ ] Set up fail2ban on the DO headscale droplet
- [ ] Put Cloudflare in front of wcyjvs2 (hides origin IP, absorbs DDoS)
- [ ] Evaluate hardened container base images (Wolfi, Alpine, distroless)
- [ ] Pin container images by digest (`image@sha256:...`) instead of tag
- [ ] Review and tighten pg_hba.conf access rules

---

## Priority Summary

| Issue | Priority | Effort |
|-------|----------|--------|
| Redirect targets (tasks, files) | Medium | Medium |
| Double-submit prevention | Low | Trivial |
| setupkit dbkit config bug | Medium | Small |
| update_project missing loader | Low | Trivial |
| target_date in INSERT audit | Low | Trivial |
| go.sh dynamic host | Low | Small |
| Security hardening | High (before go-live) | Medium-Large |
