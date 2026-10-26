# Curator v2 Phase 1 Complete — Handoff Doc

**Session**: June 23-24, 2026  
**Status**: Phase 1 ✅ LAUNCHED to GitHub  
**Next**: Phase 2 (Database views + project type assignment)

---

## Phase 1 Completion Summary

**What's done:**
- Landing page with Curator hero image + 4 crew role cards
- Crew dashboard pages for each role (/crew?role=captain|scribe|mechanic|envoy)
- Complete crew color system:
  - Captain: French Blue `#234187`
  - Scribe: Slate `#475569`
  - Mechanic: Forest Green `#166534`
  - Envoy: Crimson `#9b1c1c`
  - App shell: WCYJ Teal `#0f766e`
- Light + dark theme switching via `curator.yaml` (`ui.theme: light|dark`)
- Modular CSS architecture (base + layout + components + themes + crew roles)
- Responsive design: 4 cards desktop, 2×2 tablet, 1 column phone
- All four crew CSS files with color shade ranges (primary/dark/mid/light/tint)
- GitHub pushed to main branch

**Still needed (cosmetic, post-Phase-2):**
- Dark theme paragraph text color (`dark.css` needs `p { color: var(--color-text); }`)
- Curator landing page hero image is too small (can wait)
- Jinja2 env duplication in landing.py + crew.py (deferred, cosmetic)

---

## Phase 2 Plan

### Immediate Next Steps

**1. Data Migration (old DB → new wcyj)**
- Old database location: (specify your old DB connection string/location)
- New database: wcyj on steward at 100.64.0.7
- What to migrate:
  - projects table (with all fields)
  - tasks table (with sub-task hierarchy via parent_id)
  - project_types table (new — defines what types exist)

**2. Schema: Project Type → Crew Role Assignment**

New table in wcyj.projects schema:

```sql
CREATE TABLE projects.project_type_role_mapping (
    id SERIAL PRIMARY KEY,
    project_type_id INTEGER NOT NULL REFERENCES projects.project_type(id) ON DELETE CASCADE,
    crew_role VARCHAR(50) NOT NULL,  -- 'captain' | 'scribe' | 'mechanic' | 'envoy'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_by TEXT,
    UNIQUE(project_type_id, crew_role)
);
```

This allows:
- Captain to assign "writing" projects to Scribe
- Captain to assign "hardware refurb" projects to Mechanic
- etc.

**3. PostgreSQL Views Per Role**

Example view for Scribe (writing projects only):

```sql
CREATE VIEW projects.scribe_view AS
SELECT p.* FROM projects.projects p
WHERE p.project_type_id IN (
    SELECT project_type_id FROM projects.project_type_role_mapping 
    WHERE crew_role = 'scribe'
);
```

Do the same for captain, mechanic, envoy. Captain's view = all projects (no filter).

**4. Update /crew Route**

Current route at `src/curator/web/routes/crew.py` renders Phase 1 placeholder. Needs to:
- Query the appropriate role view from wcyj
- Pass records to crew.html template
- Remove the empty-state placeholder

**5. Captain's Project Type Assignment Form**

Location: `/crew?role=captain` page, below the data records.

UI: Dual listbox with dropdown
```
[Assign project types to crew roles]

Select role: [Dropdown: Captain|Scribe|Mechanic|Envoy]

Available Types        │  Assigned to [Role Name]
─────────────────────────────────────────────────
[ ] Writing           │  [✓] Writing
[ ] Hardware Refurb   │  [✓] Hardware Refurb
[ ] Blog Post         │
[ ] Component Test    │  [✓] Component Test
```

Left side = all project types not assigned to this role  
Right side = types currently assigned to this role  
Buttons to move items left/right  
Save commits to project_type_role_mapping table

---

## Technical Decisions Locked In

**Crew color hierarchy:**
- Base CSS (card.css) sets NO colors — purely layout/spacing
- Crew CSS files (captain|scribe|mechanic|envoy.css) own all color
- Selectors scoped to `.crew-card.{role}` and `.crew-section.{role}` to avoid cascade conflicts
- Per-crew shade ranges: primary/dark/mid/light/tint for use in tables/badges/hovers

**Responsive breakpoints:**
- Desktop: `grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))`
- Tablet (≤768px): 2 columns
- Phone (≤480px): 1 column

**Theme switching:**
- Set in `src/curator/data/curator.yaml`: `ui.theme: light` or `ui.theme: dark`
- Route picks up via `curator.get_config()` → passes to Jinja2
- `base.html` links both `light.css` and the active theme (one wins on color vars)

**File structure (Phase 2 ready):**
```
src/curator/
├── web/
│   ├── app.py
│   ├── routes/
│   │   ├── landing.py
│   │   └── crew.py  ← update with view queries
│   └── ...
├── data/
│   └── curator.yaml  ← crew roles, branding, theme
└── ...

static/
├── css/
│   ├── base.css
│   ├── layout.css
│   ├── components/
│   │   ├── card.css  ← NO colors
│   │   ├── navbar.css
│   │   ├── table.css
│   │   ├── empty-state.css
│   │   └── ...
│   ├── crew/
│   │   ├── captain.css  ← all color
│   │   ├── scribe.css
│   │   ├── mechanic.css
│   │   └── envoy.css
│   └── themes/
│       ├── light.css
│       └── dark.css
└── img/
    ├── curator.png
    ├── captain.png
    ├── scribe.png
    ├── mechanic.png
    └── envoy.png
```

---

## Known Issues & Workarounds

**SSH Agent Refusing to Sign**
- Problem: Seahorse loads ED25519 key but agent won't sign
- Solution: Kill agent, restart, re-add manually
  ```bash
  ssh-add -D
  killall ssh-agent
  eval "$(ssh-agent -s)"
  ssh-add ~/.ssh/keys/GH_id_ed25519
  ```
- Consider: Ditch Seahorse for this key, manage with `ssh-add` only

**Dark theme readability**
- Some paragraph text still too dark
- Fix: Add to `static/css/themes/dark.css`:
  ```css
  p { color: var(--color-text); }
  ```

**Jinja2 env duplication**
- landing.py and crew.py both create their own Jinja2 environments
- Cosmetic issue, deferred to Phase 3
- Solution: Create single shared env factory in app.py

---

## Captain's Settings Gear (Deferred)

Mentioned but not yet designed. Should appear in crew.html when `role == 'captain'`. Options:
- Manage users (Phase 3: auth)
- Add/edit contacts
- Configure project types
- Theme preferences (Phase 3: settings table)

Park until we have actual user auth + settings table.

---

## sitekit Naming Decision & YAML Generation Pattern

Future utility library for site identity (colors, crew roster, branding). NOT csskit — scope is bigger than CSS. Deferred to Phase 3 when settings move to database.

**Important: YAML generation on-request (not startup)**

When settings move to PostgreSQL (Phase 3), generate YAML on-demand:
- Captain edits theme/colors in UI → writes to settings table
- Save endpoint exports settings table → `curator_settings.yaml`
- Code reads YAML (immutable during request)
- Manual YAML edits never get overwritten by startup code
- Old YAML versions stay in git history

Pattern:
```python
# On Captain's save:
def save_settings(role, color, theme, ...):
    db.settings.update(...)  # write to postgres
    export_yaml_from_db()     # generate YAML on demand
    
# Code reads (at startup or per-request):
config = load_yaml('curator_settings.yaml')
```

This keeps config loading simple (just parse YAML) while DB holds the source of truth. Manual config changes and automation don't fight.

---

## Git Log (Phase 1)

```
commit [hash] — launch: Curator v2 Phase 1 — crew color system + dark theme
- Add crew-specific color palettes (Captain/Scribe/Mechanic/Envoy)
- Implement light/dark theme switching via curator.yaml
- Modular CSS: base + layout + components + themes + crew roles
- Responsive landing page with themed crew role cards
- Update base.html and crew.html templates
- Dark theme text readability improvements
- Phase 2 ready: database views + project type assignment
```

---

## Next Session: Phase 2 Kickoff

1. Decide on data migration tool/approach (psql, Python script, etc.)
2. Write schema: project_type_role_mapping table
3. Create four role-specific views
4. Update /crew route to query views + render records
5. Build Captain's project type assignment form

All crew colors + theme system are locked in — Phase 2 is data-driven.
