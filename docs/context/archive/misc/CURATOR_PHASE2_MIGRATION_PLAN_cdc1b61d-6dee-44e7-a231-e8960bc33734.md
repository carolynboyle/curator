# Curator v2 Phase 2.1 — Data Migration Plan

**Date**: June 23, 2026  
**Status**: Ready to execute  
**Scope**: Core data migration (projects, tasks, contacts) + infrastructure schema + role views

---

## Overview

Migrate essential data from `projects` (old) → `wcyj` (new) on steward.

**In scope for Phase 2.1:**
- ✅ Add `infrastructure` schema to wcyj
- ✅ Migrate lookup tables (project_status, project_type, task_status, priority)
- ✅ Migrate core entities (projects, tasks, contacts, project_contacts)
- ✅ Create project_type_role_mapping table
- ✅ Create four role-specific views
- ✅ Verify with test route

**Out of scope (Phase 3+):**
- Tags / tagging system
- Project files
- User authentication / app_user linking

---

## Step 1: Add Infrastructure Schema to wcyj

Run in pgAdmin on steward (wcyj database):

```sql
-- Add infrastructure schema to wcyj
CREATE SCHEMA IF NOT EXISTS infrastructure;

-- Create placeholder table for future ansible/hardware tracking
-- (This can hold node definitions, hardware inventory, etc.)
CREATE TABLE infrastructure.nodes (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    role        VARCHAR(100),
    description TEXT,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_nodes_updated_at
    BEFORE UPDATE ON infrastructure.nodes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMENT ON SCHEMA infrastructure IS 'Ansible, node management, hardware inventory';
COMMENT ON TABLE infrastructure.nodes IS 'Tracks homelab nodes, VMs, devices';
```

**Verify:**
```sql
SELECT schema_name FROM information_schema.schemata 
WHERE schema_name IN ('audit', 'contacts', 'projects', 'infrastructure')
ORDER BY schema_name;
```

Expected output: audit, contacts, infrastructure, projects (4 rows)

---

## Step 2: Verify Lookup Table Matching

Before migrating, confirm lookup values exist in wcyj and match the old db.

Run in pgAdmin on steward (wcyj database):

```sql
-- Check wcyj has the expected lookup values
SELECT name FROM projects.project_status ORDER BY name;
-- Expected: active, archived, complete, on hold, queued

SELECT name FROM projects.project_type ORDER BY name;
-- Expected: homelab, refurb, writing

SELECT name, is_terminal FROM projects.task_status ORDER BY name;
-- Expected: backlog (false), blocked (false), cancelled (true), complete (true), in progress (false)

SELECT name FROM projects.priority ORDER BY name;
-- Expected: high, low, normal, urgent
```

**If any are missing**, insert them:
```sql
INSERT INTO projects.project_status (name) VALUES ('your_status');
INSERT INTO projects.project_type (name) VALUES ('your_type');
INSERT INTO projects.task_status (name, is_terminal) VALUES ('your_status', false);
INSERT INTO projects.priority (name) VALUES ('your_priority');
```

---

## Step 3: Migrate Contacts

Run in pgAdmin on steward (wcyj database):

```sql
-- Migrate contacts from projects.public to wcyj.contacts
-- Maps old contacts → new contacts (skip created_by/updated_by for Phase 2)

INSERT INTO contacts.contacts (
    name, email, title, notes, created_at, updated_at
)
SELECT 
    name, 
    email, 
    title, 
    notes, 
    created_at, 
    updated_at
FROM projects.public.contacts
WHERE NOT EXISTS (
    SELECT 1 FROM contacts.contacts c 
    WHERE c.name = projects.public.contacts.name AND c.email = projects.public.contacts.email
)
ON CONFLICT DO NOTHING;
```

**Verify count matches:**
```sql
SELECT 
    (SELECT COUNT(*) FROM projects.public.contacts) as old_count,
    (SELECT COUNT(*) FROM contacts.contacts) as new_count;
```

---

## Step 4: Migrate Projects

Run in pgAdmin on steward (wcyj database):

```sql
-- Migrate projects from projects.public to wcyj.projects
-- Uses name matching for lookups (status_id, type_id)

INSERT INTO projects.projects (
    name, slug, description, notes, status_id, type_id, parent_id, target_date, created_at, updated_at
)
SELECT 
    old.name,
    old.slug,
    old.description,
    old.notes,
    ps.id,  -- match by name to new project_status table
    pt.id,  -- match by name to new project_type table
    NULL,   -- parent_id: Phase 2 limitation (can't match old parent_id yet)
    old.target_date,
    old.created_at,
    old.updated_at
FROM projects.public.projects old
LEFT JOIN projects.project_status ps ON ps.name = (
    SELECT name FROM projects.public.project_status 
    WHERE id = old.status_id
)
LEFT JOIN projects.project_type pt ON pt.name = (
    SELECT name FROM projects.public.project_type 
    WHERE id = old.type_id
)
WHERE NOT EXISTS (
    SELECT 1 FROM projects.projects p 
    WHERE p.slug = old.slug
)
ON CONFLICT (slug) DO NOTHING;
```

**Verify count:**
```sql
SELECT 
    (SELECT COUNT(*) FROM projects.public.projects) as old_count,
    (SELECT COUNT(*) FROM projects.projects) as new_count;
```

**Inspect a few rows:**
```sql
SELECT id, name, slug, status_id, type_id 
FROM projects.projects 
LIMIT 5;
```

---

## Step 5: Migrate Tasks

Run in pgAdmin on steward (wcyj database):

```sql
-- Migrate tasks from projects.public to wcyj.projects.tasks
-- Maps old project_id + task fields to new task structure
-- parent_id handling: Phase 2 limitation (can map after task ids stabilize)

INSERT INTO projects.tasks (
    project_id, description, notes, status_id, priority_id, sort_order, created_at, updated_at
)
SELECT 
    new_p.id,  -- map old project_id to new project_id via slug lookup
    old.title,  -- old.title → new.description (name change in schema)
    old.notes,
    ts.id,     -- match by name to new task_status table
    pri.id,    -- match by name to new priority table
    0,         -- sort_order: default 0 for now
    old.created_at,
    old.updated_at
FROM projects.public.tasks old
JOIN projects.public.projects old_p ON old_p.id = old.project_id
JOIN projects.projects new_p ON new_p.slug = old_p.slug
LEFT JOIN projects.task_status ts ON ts.name = (
    SELECT name FROM projects.public.task_status 
    WHERE id = old.status_id
)
LEFT JOIN projects.priority pri ON pri.name = (
    SELECT name FROM projects.public.priority 
    WHERE id = old.priority_id
)
WHERE NOT EXISTS (
    SELECT 1 FROM projects.tasks t 
    WHERE t.description = old.title 
    AND t.project_id = new_p.id
)
ON CONFLICT DO NOTHING;
```

**Verify count:**
```sql
SELECT 
    (SELECT COUNT(*) FROM projects.public.tasks) as old_count,
    (SELECT COUNT(*) FROM projects.tasks) as new_count;
```

---

## Step 6: Migrate Project Contacts

Run in pgAdmin on steward (wcyj database):

```sql
-- Migrate project_contacts from projects.public to wcyj.projects.project_contacts
-- Maps via slug + name matching

INSERT INTO projects.project_contacts (
    project_id, contact_id, role, is_primary, notes
)
SELECT 
    new_p.id,           -- map old project_id to new project_id
    new_c.id,           -- map old contact_id to new contact_id
    old.role,
    old.is_primary,
    NULL                -- notes: not in old schema
FROM projects.public.project_contacts old
JOIN projects.public.projects old_p ON old_p.id = old.project_id
JOIN projects.public.contacts old_c ON old_c.id = old.contact_id
JOIN projects.projects new_p ON new_p.slug = old_p.slug
JOIN contacts.contacts new_c ON new_c.name = old_c.name AND new_c.email = old_c.email
WHERE NOT EXISTS (
    SELECT 1 FROM projects.project_contacts pc 
    WHERE pc.project_id = new_p.id 
    AND pc.contact_id = new_c.id
)
ON CONFLICT (project_id, contact_id) DO NOTHING;
```

**Verify:**
```sql
SELECT 
    (SELECT COUNT(*) FROM projects.public.project_contacts) as old_count,
    (SELECT COUNT(*) FROM projects.project_contacts) as new_count;
```

---

## Step 7: Create project_type_role_mapping Table

This is the core of Phase 2 — maps project types to crew roles.

Run in pgAdmin on steward (wcyj database):

```sql
CREATE TABLE projects.project_type_role_mapping (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_type_id BIGINT       NOT NULL REFERENCES projects.project_type (id) ON DELETE CASCADE,
    crew_role       VARCHAR(50)  NOT NULL CHECK (crew_role IN ('captain', 'scribe', 'mechanic', 'envoy')),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_by      BIGINT,      -- FK to contacts.app_user (optional for Phase 2)
    UNIQUE(project_type_id, crew_role)
);

CREATE INDEX idx_mapping_type ON projects.project_type_role_mapping (project_type_id);
CREATE INDEX idx_mapping_role ON projects.project_type_role_mapping (crew_role);

COMMENT ON TABLE projects.project_type_role_mapping IS 'Maps project types to crew roles for filtering';
```

---

## Step 8: Seed project_type_role_mapping

Assign project types to crew roles. Adjust based on your actual intentions.

Run in pgAdmin on steward (wcyj database):

```sql
-- Default mapping: one type per role, Captain sees all
INSERT INTO projects.project_type_role_mapping (project_type_id, crew_role)
SELECT id, 'scribe' FROM projects.project_type WHERE name = 'writing'
UNION ALL
SELECT id, 'mechanic' FROM projects.project_type WHERE name = 'refurb'
UNION ALL
SELECT id, 'envoy' FROM projects.project_type WHERE name = 'homelab'
UNION ALL
-- Captain can also see writing and refurb (multi-role assignment)
SELECT id, 'captain' FROM projects.project_type WHERE name = 'writing'
UNION ALL
SELECT id, 'captain' FROM projects.project_type WHERE name = 'refurb'
UNION ALL
SELECT id, 'captain' FROM projects.project_type WHERE name = 'homelab';
```

**Verify:**
```sql
SELECT crew_role, COUNT(*) as type_count
FROM projects.project_type_role_mapping
GROUP BY crew_role
ORDER BY crew_role;
```

Expected output:
```
captain   | 3
envoy     | 1
mechanic  | 1
scribe    | 1
```

---

## Step 9: Create Role-Specific Views

These views filter projects by crew role.

Run in pgAdmin on steward (wcyj database):

```sql
-- Captain sees all projects (no filter)
CREATE OR REPLACE VIEW projects.captain_view AS
SELECT 
    p.id, p.name, p.slug, p.description, p.notes,
    ps.name as status,
    pt.name as project_type,
    p.target_date, p.parent_id, p.created_at, p.updated_at
FROM projects.projects p
LEFT JOIN projects.project_status ps ON ps.id = p.status_id
LEFT JOIN projects.project_type pt ON pt.id = p.type_id
ORDER BY p.created_at DESC;

-- Scribe sees projects assigned to 'scribe' role
CREATE OR REPLACE VIEW projects.scribe_view AS
SELECT 
    p.id, p.name, p.slug, p.description, p.notes,
    ps.name as status,
    pt.name as project_type,
    p.target_date, p.parent_id, p.created_at, p.updated_at
FROM projects.projects p
LEFT JOIN projects.project_status ps ON ps.id = p.status_id
LEFT JOIN projects.project_type pt ON pt.id = p.type_id
WHERE p.type_id IN (
    SELECT project_type_id FROM projects.project_type_role_mapping
    WHERE crew_role = 'scribe'
)
ORDER BY p.created_at DESC;

-- Mechanic sees projects assigned to 'mechanic' role
CREATE OR REPLACE VIEW projects.mechanic_view AS
SELECT 
    p.id, p.name, p.slug, p.description, p.notes,
    ps.name as status,
    pt.name as project_type,
    p.target_date, p.parent_id, p.created_at, p.updated_at
FROM projects.projects p
LEFT JOIN projects.project_status ps ON ps.id = p.status_id
LEFT JOIN projects.project_type pt ON pt.id = p.type_id
WHERE p.type_id IN (
    SELECT project_type_id FROM projects.project_type_role_mapping
    WHERE crew_role = 'mechanic'
)
ORDER BY p.created_at DESC;

-- Envoy sees projects assigned to 'envoy' role
CREATE OR REPLACE VIEW projects.envoy_view AS
SELECT 
    p.id, p.name, p.slug, p.description, p.notes,
    ps.name as status,
    pt.name as project_type,
    p.target_date, p.parent_id, p.created_at, p.updated_at
FROM projects.projects p
LEFT JOIN projects.project_status ps ON ps.id = p.status_id
LEFT JOIN projects.project_type pt ON pt.id = p.type_id
WHERE p.type_id IN (
    SELECT project_type_id FROM projects.project_type_role_mapping
    WHERE crew_role = 'envoy'
)
ORDER BY p.created_at DESC;
```

**Test each view:**
```sql
SELECT COUNT(*) FROM projects.captain_view;
SELECT COUNT(*) FROM projects.scribe_view;
SELECT COUNT(*) FROM projects.mechanic_view;
SELECT COUNT(*) FROM projects.envoy_view;

-- Spot-check Scribe's projects
SELECT name, project_type FROM projects.scribe_view LIMIT 5;
```

---

## Step 10: Verification Queries

Run these in order to confirm everything is wired correctly.

```sql
-- 1. Total project count across all roles
SELECT 
    'captain' as role, COUNT(*) FROM projects.captain_view
UNION ALL
SELECT 'scribe', COUNT(*) FROM projects.scribe_view
UNION ALL
SELECT 'mechanic', COUNT(*) FROM projects.mechanic_view
UNION ALL
SELECT 'envoy', COUNT(*) FROM projects.envoy_view;

-- 2. Project types and their assigned roles
SELECT 
    pt.name,
    ARRAY_AGG(DISTINCT ptrm.crew_role ORDER BY ptrm.crew_role) as assigned_roles
FROM projects.project_type pt
LEFT JOIN projects.project_type_role_mapping ptrm ON ptrm.project_type_id = pt.id
GROUP BY pt.name
ORDER BY pt.name;

-- 3. Sample projects by type
SELECT 
    pt.name as project_type,
    COUNT(*) as count
FROM projects.projects p
LEFT JOIN projects.project_type pt ON pt.id = p.type_id
GROUP BY pt.name
ORDER BY pt.name;

-- 4. Tasks per project (first 10)
SELECT 
    p.name, 
    COUNT(t.id) as task_count
FROM projects.projects p
LEFT JOIN projects.tasks t ON t.project_id = p.id
GROUP BY p.id, p.name
ORDER BY p.created_at DESC
LIMIT 10;
```

---

## Next: Test Route Implementation

Once migration is verified, update `src/curator/web/routes/crew.py`:

```python
from fastapi import APIRouter, Query
from curator.db import get_db
from curator.config import load_config

router = APIRouter()

@router.get("/crew")
async def crew_dashboard(role: str = Query("captain"), db = get_db()):
    """
    Render crew role dashboard with projects filtered by role.
    
    Args:
        role: One of 'captain', 'scribe', 'mechanic', 'envoy'
        db: Database connection
    
    Returns:
        Rendered crew.html with role-filtered projects
    """
    
    # Validate role
    if role not in ["captain", "scribe", "mechanic", "envoy"]:
        role = "captain"
    
    # Query appropriate view
    view_name = f"{role}_view"
    query = f"SELECT * FROM projects.{view_name}"
    
    projects = await db.fetch_all(query)
    
    config = load_config()
    
    return {
        "role": role,
        "projects": projects,
        "crew_colors": config.get("crew_colors", {})
    }
```

---

## Rollback Plan

If something goes wrong:

```sql
-- Drop the new schema elements (keep old db intact)
DROP VIEW IF EXISTS projects.envoy_view CASCADE;
DROP VIEW IF EXISTS projects.mechanic_view CASCADE;
DROP VIEW IF EXISTS projects.scribe_view CASCADE;
DROP VIEW IF EXISTS projects.captain_view CASCADE;
DROP TABLE IF EXISTS projects.project_type_role_mapping CASCADE;

-- Drop migrated entities if needed
TRUNCATE TABLE projects.project_contacts CASCADE;
TRUNCATE TABLE projects.tasks CASCADE;
TRUNCATE TABLE projects.projects CASCADE;
TRUNCATE TABLE contacts.contacts CASCADE;

-- Remove infrastructure schema
DROP SCHEMA IF EXISTS infrastructure CASCADE;
```

---

## Summary

**After completing all steps:**
- ✅ wcyj has infrastructure schema
- ✅ All projects, tasks, contacts migrated
- ✅ project_type_role_mapping seeded
- ✅ Four role-specific views ready
- ✅ Old db (projects) still intact for reference

**Phase 2.2 (next session):**
- Wire `/crew` route to query views
- Create `/test/role-filtering` verification page
- Update crew.html template to render projects
- Build Captain's project type assignment UI

---

## Files to Update After Migration

1. `src/curator/web/routes/crew.py` — Query views + render
2. `src/curator/templates/crew.html` — Display projects + assignment form
3. `curator.yaml` — Any new branding/role settings
4. Git commit → `patch: wcyj Phase 2.1 data migration complete`

