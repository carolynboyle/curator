# Curator v2 Session Handoff — 2026-06-22/23

## What Was Done Tonight

**Infrastructure fixed:**
- Headscale VPS was broken, now fixed
- wcyjv20 (new LMDE dev VM) created and on mesh at 100.64.0.21
- Mesh connectivity verified (tailscale daemon restarted, now working)
- wcyjv20 can reach steward (100.64.0.7) database
- DB connection tested: `psql -h 100.64.0.7 -U steward -d wcyj` ✓
- `.pgpass` configured for wcyj database on wcyjv20

**Architecture designed & scaffolded:**
- Curator v2 Phase 1 complete scaffold created
- Three-phase plan locked in:
  - **Phase 1:** Landing page + crew route skeleton (ready to build)
  - **Phase 2:** Load role-filtered PostgreSQL views
  - **Phase 3:** User auth + role validation + settings table for themes
- Design principles established:
  - **No hardcoding:** All configurable values in YAML or database
  - **Modular CSS:** base + components + themes structure
  - **Database-first:** Use Postgres for dynamic data, YAML for static
  - **Configuration-driven:** Routes read from ConfigManager

---

## Current State

### Environment

| Component | Status | Location |
|-----------|--------|----------|
| wcyjv20 VM | ✅ Running | 100.64.0.21 (Tailscale) |
| Headscale coordination | ✅ Running | wcyj-meet (100.64.0.1) |
| PostgreSQL wcyj database | ✅ Ready | steward (100.64.0.7) |
| Mesh connectivity | ✅ Verified | All nodes connected |
| `.pgpass` | ✅ Configured | `~/.pgpass` on wcyjv20 |

### Downloaded Files (Ready to Use)

1. **`CURATOR_V2_PHASE1_REVISED.md`** — Complete scaffold with:
   - treekit-compatible directory structure
   - All Python code (app.py, routes, config, deps)
   - All template files (base.html, landing.html, crew.html)
   - All CSS files organized by purpose (base, layout, components, themes)
   - curator.yaml configuration
   - Full README with architecture notes

2. **`curator_v2_pyproject.toml`** — Project dependencies
   - FastAPI, Uvicorn, Jinja2, python-multipart
   - dbkit (from dev-utils)

3. **`CURATOR_V2_HANDOFF_2026-06-23.md`** — This file. Your continuity doc.

### Database

**Schema:** wcyj on steward (100.64.0.7)
- 18 tables across 3 schemas: `contacts`, `projects`, `mechanic`
- Full schema applied and documented in `curator_v2_schema_design.md`
- **Ready for Phase 2 view creation**

---

## Exact Next Steps (Tomorrow Morning)

### On wcyjv20:

**1. Navigate to curator repo:**
```bash
cd ~/curator
```

**2. Generate directory structure with treekit:**
Copy this from CURATOR_V2_PHASE1_REVISED.md and save as structure.md:
```bash
treekit generate --markdown < structure.md
```

**3. Copy all file contents** from `CURATOR_V2_PHASE1_REVISED.md`:
- Each section is marked with file path (e.g., `### curator/__init__.py`)
- Copy content into that file path

**4. Create `~/.config/dev-utils/config.yaml`:**
```yaml
dbkit:
  host: 100.64.0.7
  port: 5432
  dbname: wcyj
  user: steward
```

**5. Copy the 5 crew graphic images** to `static/`:
- `captain.png`
- `curator.png`
- `mechanic.png`
- `envoy.png`
- `scribe.png`
(These were uploaded earlier)

**6. Set up Python venv:**
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

**7. Start the app:**
```bash
uvicorn curator.web.app:app --host localhost --port 8080 --reload
```

**8. Test in browser:**
- Open http://localhost:8080
- Should see landing page with 4 crew cards
- Click a card → should route to `/crew?role={role}`
- See Phase 1 placeholder message ("no data yet")
- Try switching theme in `curator.yaml` (change `theme: "light"` to `theme: "dark"`)

### Success Criteria for Phase 1

✅ Landing page loads with all crew cards from `curator.yaml`  
✅ Click card → routes to `/crew?role={role}` with correct role  
✅ Crew dashboard template renders with phase 1 message  
✅ Theme switching works (edit curator.yaml, refresh browser)  
✅ All CSS loads (no 404s in browser console)  
✅ Database connection verified (even if not used yet)  

Once Phase 1 is working, start Phase 2: create role-filtered PostgreSQL views.

---

## Phase 2 Work (Preview)

Not starting tomorrow, but be aware of what's needed:

**Create PostgreSQL views for each role:**
```sql
-- In wcyj database, projects schema

-- v_captain_dashboard — all records, all domains
-- v_curator_dashboard — projects/tasks only
-- v_mechanic_dashboard — devices/refurb only
-- v_envoy_dashboard — connections only
-- v_scribe_dashboard — writing projects only
```

**Modify `/crew` route** to query appropriate view based on role param.

**Update template** to loop over records returned from view.

---

## Key Files & Locations

| File | Location | Purpose |
|------|----------|---------|
| Scaffold doc | CURATOR_V2_PHASE1_REVISED.md | All code, configs, CSS |
| pyproject.toml | curator_v2_pyproject.toml | Dependencies |
| curator.yaml | `curator/data/curator.yaml` | Branding, crew roles, theme |
| config.py | `curator/config.py` | ConfigManager class |
| app.py | `curator/web/app.py` | FastAPI app init |
| routes | `curator/web/routes/landing.py`, `crew.py` | Endpoints |
| templates | `curator/templates/` | Jinja2 HTML |
| CSS | `static/css/` | Modular styles + themes |
| `.pgpass` | `~/.pgpass` | DB credentials (already set) |
| dev-utils config | `~/.config/dev-utils/config.yaml` | dbkit connection (create tomorrow) |

---

## Important Notes

1. **No SSH needed yet** — using local uvicorn on 8080, accessible from Mac via Tailscale mesh
2. **Headscale IP is stable** — wcyj-meet at 100.64.0.1, check if needed in Phase 3
3. **Database password in Proton Pass** — only in `~/.pgpass`, never in code
4. **curator_init.py is deferred** — you decided to set up config manually for Phase 1, build it later
5. **Docker not yet needed** — Phase 1 is local dev with `--reload`
6. **Three-phase approach is locked in** — don't skip phases, foundation matters

---

## Blockers/Gotchas

None identified. Environment is clean and ready.

---

## Handoff Checklist for Tomorrow

- [ ] Download all three files
- [ ] SSH into wcyjv20 (or use console/RDP)
- [ ] Run treekit to generate structure
- [ ] Copy all files from scaffold
- [ ] Create `~/.config/dev-utils/config.yaml`
- [ ] Copy PNG images to `static/`
- [ ] Create venv and install with `pip install -e .`
- [ ] Run `uvicorn curator.web.app:app --host localhost --port 8080 --reload`
- [ ] Test in browser (landing page, click card, theme switch)
- [ ] Celebrate Phase 1 working ⛵

---

## Questions for Tomorrow

None that need answering now. You have everything. Just execute Phase 1.

---

## Session Stats

- **Duration:** ~2 hours
- **Infrastructure work:** 45 min (mesh, VM, DB connectivity)
- **Architecture & design:** 45 min (three-phase plan, principles)
- **Scaffold creation:** 30 min (complete Phase 1 scaffold)
- **Result:** Ready-to-build Phase 1, zero blockers

Good stopping point. You've got a solid foundation. 🎭
