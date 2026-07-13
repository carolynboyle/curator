# Changedoc: Tasks SQL Layer

**Date:** 2026-07-06
**Depends on:** `03_projects.sql`, `07_detail_views.sql`, `07_detail_api.sql`,
`06b_api_projects.sql`, `08b_api_lookup.sql` (all as uploaded this session)

**Scope:** Database layer only. This is step 1 of wiring Tasks into the UI —
`v_task_detail`, `api.get_task_detail()`, `api.save_task()`,
`api.delete_task()`, two new `api.get_lookup()` branches, and dropping
`projects.tasks.sort_order`. Python/fieldkit/template work follows once this
is verified in pgAdmin.

**Decisions this reflects (confirmed with Carolyn):**
- `project_id` is a hidden, pre-filled field on the task form (fieldkit change,
  not part of this changedoc — noted at the bottom).
- Subtasks (`parent_id`) are in scope. A parent task must belong to the same
  project; a task can't be its own parent. Deeper cycle detection
  (grandparent loops) is **not** implemented — flagged as a known gap below.
- `sort_order` is dead weight with no consumer — dropped entirely. Ordering
  is expected to come from naming convention (`01_task`, `02_task`) or
  sorting by name/due-date in the UI, not a stored order column.

---

## Apply order

Run these **in pgAdmin, in this exact order**, against `wcyj`:

1. **Live-DB migration** (Section 1) — drops `sort_order`
2. **New view** (Section 2) — incremental statement only, not the whole file
3. **New read function** (Section 3)
4. **New save/delete functions** (Section 4)
5. **Updated `get_lookup()`** (Section 5) — full `CREATE OR REPLACE`, safe to
   rerun whole
6. **Re-run grants** (Section 6)

Then update the five files on disk in your `steward` repo to the AFTER
versions below, so the canonical schema source matches what's live.

---

## Section 1 — Live-DB migration (run first)

```sql
ALTER TABLE projects.tasks DROP COLUMN sort_order;
```

No dependent index or view references `sort_order`, so this is a clean drop —
confirmed against `idx_tasks_project`/`idx_tasks_parent`/`idx_tasks_status`/
`idx_tasks_priority` and `v_task_detail` below (which doesn't select it).

---

## Section 2 — New view (run this statement only, not the whole file)

```sql
CREATE VIEW projects.v_task_detail AS
SELECT
    id,
    project_id,
    parent_id,
    description,
    notes,
    status_id,
    priority_id
FROM projects.tasks;

GRANT SELECT ON projects.v_task_detail TO steward;
```

`completed_at` is deliberately excluded — same reasoning as `slug` on
`v_project_detail`: it's server-managed, not a field the user edits directly.
`api.save_task()` (Section 4) sets it automatically from `status_id`.

---

## Section 3 — New read function

```sql
CREATE OR REPLACE FUNCTION api.get_task_detail(p_id BIGINT)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT row_to_json(t)::jsonb
    FROM projects.v_task_detail t
    WHERE t.id = p_id;
$$;
```

---

## Section 4 — New save/delete functions

```sql
-- =============================================================================
-- api.save_task(payload JSONB, user_id BIGINT)
--
-- Insert or update a task record.
-- payload.id present and non-null -> UPDATE; absent or null -> INSERT.
--
-- Unlike api.save_project(), status_id and priority_id are taken as ids
-- directly, not name strings -- fieldkit's <select> fields post the id
-- from api.get_lookup(), so there's no name-to-id resolution step needed
-- here the way the older hand-coded project form required.
--
-- completed_at is not accepted from the payload -- it's derived from
-- status_id.is_terminal on every save (stamped NOW() when terminal, cleared
-- when not), matching the project_templates_design.md rule that a task's
-- completed_at reflects its current status, not a preserved timestamp.
--
-- parent_id, if provided, must reference an existing task in the SAME
-- project, and can't be the task's own id. Deeper cycle detection
-- (e.g. a task set as its own grandparent) is not implemented -- flagged
-- as a known gap, not expected to come up with the shallow subtask depth
-- this UI supports.
--
-- Payload shape:
-- {
--   "id":          null,           -- null/absent = INSERT, int = UPDATE
--   "project_id":  12,              -- required
--   "parent_id":   null,            -- optional, must be same project
--   "description": "Fix the latch", -- required
--   "notes":       "...",           -- optional
--   "status_id":   3,               -- required
--   "priority_id": 2                -- optional
-- }
-- =============================================================================

CREATE OR REPLACE FUNCTION api.save_task(
    p_payload JSONB,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id                 BIGINT;
    v_project_id         BIGINT;
    v_parent_id          BIGINT;
    v_description        TEXT;
    v_notes              TEXT;
    v_status_id          BIGINT;
    v_priority_id        BIGINT;
    v_is_terminal        BOOLEAN;
    v_completed_at       TIMESTAMPTZ;
    v_is_update          BOOLEAN;
    v_parent_project_id  BIGINT;
BEGIN
    v_description := TRIM(p_payload->>'description');

    IF v_description IS NULL OR v_description = '' THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Task description is required.'
        );
    END IF;

    v_project_id := (p_payload->>'project_id')::BIGINT;

    IF v_project_id IS NULL THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'A project is required.'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM projects.projects WHERE id = v_project_id) THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Project not found.'
        );
    END IF;

    v_status_id := (p_payload->>'status_id')::BIGINT;

    IF v_status_id IS NULL THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Task status is required.'
        );
    END IF;

    SELECT is_terminal INTO v_is_terminal
    FROM projects.task_status
    WHERE id = v_status_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Task status not found.'
        );
    END IF;

    v_priority_id := (p_payload->>'priority_id')::BIGINT;
    v_notes       := NULLIF(TRIM(p_payload->>'notes'), '');
    v_parent_id   := (p_payload->>'parent_id')::BIGINT;
    v_id          := (p_payload->>'id')::BIGINT;
    v_is_update   := v_id IS NOT NULL;

    IF v_parent_id IS NOT NULL THEN
        IF v_is_update AND v_parent_id = v_id THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'A task cannot be its own parent.'
            );
        END IF;

        SELECT project_id INTO v_parent_project_id
        FROM projects.tasks
        WHERE id = v_parent_id;

        IF NOT FOUND THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'Parent task not found.'
            );
        END IF;

        IF v_parent_project_id != v_project_id THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'Parent task must belong to the same project.'
            );
        END IF;
    END IF;

    v_completed_at := CASE WHEN v_is_terminal THEN NOW() ELSE NULL END;

    IF v_is_update THEN
        IF NOT EXISTS (SELECT 1 FROM projects.tasks WHERE id = v_id) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'Task not found.'
            );
        END IF;

        UPDATE projects.tasks SET
            project_id   = v_project_id,
            parent_id    = v_parent_id,
            description  = v_description,
            notes        = v_notes,
            status_id    = v_status_id,
            priority_id  = v_priority_id,
            completed_at = v_completed_at,
            updated_by   = p_user_id
        WHERE id = v_id;

        RETURN jsonb_build_object(
            'success', TRUE,
            'data',    jsonb_build_object('id', v_id),
            'message', 'Task updated.'
        );
    ELSE
        INSERT INTO projects.tasks (
            project_id, parent_id, description, notes,
            status_id, priority_id, completed_at,
            created_by, updated_by
        ) VALUES (
            v_project_id, v_parent_id, v_description, v_notes,
            v_status_id, v_priority_id, v_completed_at,
            p_user_id, p_user_id
        )
        RETURNING id INTO v_id;

        RETURN jsonb_build_object(
            'success', TRUE,
            'data',    jsonb_build_object('id', v_id),
            'message', 'Task created.'
        );
    END IF;

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'api.save_task error: %', SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred saving the task.'
    );
END;
$$;


-- =============================================================================
-- api.delete_task(id BIGINT, user_id BIGINT)
--
-- Hard delete. parent_id is ON DELETE NO ACTION (03_projects.sql), so a task
-- with subtasks can't be deleted out from under them -- checked explicitly
-- for a clear message, with the foreign_key_violation catch kept as a
-- fallback for any other dependent-record case.
-- =============================================================================

CREATE OR REPLACE FUNCTION api.delete_task(
    p_id      BIGINT,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM projects.tasks WHERE id = p_id) THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Task not found.'
        );
    END IF;

    IF EXISTS (SELECT 1 FROM projects.tasks WHERE parent_id = p_id) THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Cannot delete task — it has subtasks. Delete or reassign them first.'
        );
    END IF;

    DELETE FROM projects.tasks WHERE id = p_id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'data',    jsonb_build_object('id', p_id),
        'message', 'Task deleted.'
    );

EXCEPTION WHEN foreign_key_violation THEN
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'Cannot delete task — it has dependent records.'
    );
WHEN OTHERS THEN
    RAISE WARNING 'api.delete_task error for id %: %', p_id, SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred deleting the task.'
    );
END;
$$;
```

---

## Section 5 — Updated `get_lookup()` (full replace, safe to rerun)

```sql
CREATE OR REPLACE FUNCTION api.get_lookup(p_source TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
BEGIN
    CASE p_source
        WHEN 'project_types' THEN
            SELECT jsonb_agg(
                       jsonb_build_object('value', id, 'label', name)
                       ORDER BY name
                   )
            INTO v_result
            FROM projects.project_type;

        WHEN 'project_statuses' THEN
            SELECT jsonb_agg(
                       jsonb_build_object('value', id, 'label', name)
                       ORDER BY name
                   )
            INTO v_result
            FROM projects.project_status;

        WHEN 'task_statuses' THEN
            SELECT jsonb_agg(
                       jsonb_build_object('value', id, 'label', name)
                       ORDER BY name
                   )
            INTO v_result
            FROM projects.task_status;

        WHEN 'priorities' THEN
            SELECT jsonb_agg(
                       jsonb_build_object('value', id, 'label', name)
                       ORDER BY name
                   )
            INTO v_result
            FROM projects.priority;

        ELSE
            v_result := NULL;
    END CASE;

    RETURN v_result;
END;
$$;
```

---

## Section 6 — Re-run grants

```sql
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO steward;
```

---

## Verify in pgAdmin

```sql
-- sort_order is gone
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'projects' AND table_name = 'tasks';

-- view shape is correct
SELECT * FROM projects.v_task_detail LIMIT 1;

-- read function: real id returns data, bogus id returns NULL, no error
SELECT api.get_task_detail(1);
SELECT api.get_task_detail(999999);

-- lookups
SELECT api.get_lookup('task_statuses');
SELECT api.get_lookup('priorities');

-- save: minimal insert (swap in a real project_id/status_id)
SELECT api.save_task('{"project_id": 1, "description": "test task", "status_id": 1}'::jsonb, NULL);

-- grants took
SELECT routine_name FROM information_schema.routine_privileges
WHERE grantee = 'web_app_user' AND routine_name IN ('get_task_detail', 'save_task', 'delete_task');
```

---

# File changes (for the `steward` repo — canonical schema source)

## `03_projects.sql`

### BEFORE

```sql
CREATE TABLE projects.tasks (
    id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id   BIGINT      NOT NULL REFERENCES projects.projects (id)   ON DELETE CASCADE,
    parent_id    BIGINT      REFERENCES projects.tasks (id)                ON DELETE NO ACTION,
    description  TEXT        NOT NULL,
    notes        TEXT,
    status_id    BIGINT      NOT NULL REFERENCES projects.task_status (id),
    priority_id  BIGINT      REFERENCES projects.priority (id),
    sort_order   INT         NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_by   BIGINT      REFERENCES identity.app_user (id) ON DELETE SET NULL,
    updated_by   BIGINT      REFERENCES identity.app_user (id) ON DELETE SET NULL
);
```

### AFTER

```sql
CREATE TABLE projects.tasks (
    id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id   BIGINT      NOT NULL REFERENCES projects.projects (id)   ON DELETE CASCADE,
    parent_id    BIGINT      REFERENCES projects.tasks (id)                ON DELETE NO ACTION,
    description  TEXT        NOT NULL,
    notes        TEXT,
    status_id    BIGINT      NOT NULL REFERENCES projects.task_status (id),
    priority_id  BIGINT      REFERENCES projects.priority (id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_by   BIGINT      REFERENCES identity.app_user (id) ON DELETE SET NULL,
    updated_by   BIGINT      REFERENCES identity.app_user (id) ON DELETE SET NULL
);
```

**Why:** `sort_order` had no consumer anywhere in the app — confirmed dead
weight. Ordering convention is naming (`01_task`, `02_task`) or sort-by-name/
due-date in the UI, not a stored column.

(No other part of `03_projects.sql` changes — the rest of the file, including
all lookup tables, `projects.projects`, indexes, triggers, role-filtered views,
and grants, stays exactly as uploaded.)

---

## `07_detail_views.sql`

### BEFORE

```sql
CREATE VIEW projects.v_project_detail AS
SELECT
    id,
    name,
    description,
    type_id,
    status_id
FROM projects.projects;

CREATE VIEW identity.v_contact_detail AS
SELECT
    id,
    name,
    title,
    notes
FROM identity.contacts;

CREATE VIEW identity.v_organization_detail AS
SELECT
    id,
    name,
    notes
FROM identity.organizations;


-- =============================================================================
-- GRANTs
-- steward already has broader SELECT access to the underlying tables
-- (02_identity.sql, 03_projects.sql) — granting on these views too for
-- the same reason the role-filtered list views (captain_view etc.) are
-- granted: pgAdmin browsability without needing steward to know which
-- underlying table backs a view.
-- web_app_user gets nothing here — all access is through api.get_*_detail()
-- (07_detail_api.sql), consistent with the api-only read/write model.
-- =============================================================================

GRANT SELECT ON
    projects.v_project_detail
TO steward;

GRANT SELECT ON
    identity.v_contact_detail,
    identity.v_organization_detail
TO steward;
```

### AFTER

```sql
CREATE VIEW projects.v_project_detail AS
SELECT
    id,
    name,
    description,
    type_id,
    status_id
FROM projects.projects;

CREATE VIEW projects.v_task_detail AS
SELECT
    id,
    project_id,
    parent_id,
    description,
    notes,
    status_id,
    priority_id
FROM projects.tasks;

CREATE VIEW identity.v_contact_detail AS
SELECT
    id,
    name,
    title,
    notes
FROM identity.contacts;

CREATE VIEW identity.v_organization_detail AS
SELECT
    id,
    name,
    notes
FROM identity.organizations;


-- =============================================================================
-- GRANTs
-- steward already has broader SELECT access to the underlying tables
-- (02_identity.sql, 03_projects.sql) — granting on these views too for
-- the same reason the role-filtered list views (captain_view etc.) are
-- granted: pgAdmin browsability without needing steward to know which
-- underlying table backs a view.
-- web_app_user gets nothing here — all access is through api.get_*_detail()
-- (07_detail_api.sql), consistent with the api-only read/write model.
-- =============================================================================

GRANT SELECT ON
    projects.v_project_detail,
    projects.v_task_detail
TO steward;

GRANT SELECT ON
    identity.v_contact_detail,
    identity.v_organization_detail
TO steward;
```

**Why:** `v_task_detail` excludes `completed_at` (server-managed, set by
`api.save_task()` from `status_id`) the same way `v_project_detail` excludes
`slug` — a deliberate whitelist, not "the table minus a few exclusions."

**Reminder:** in pgAdmin, only run the new `CREATE VIEW projects.v_task_detail`
statement and its `GRANT` (Section 2 above) — the other three views in this
file use plain `CREATE VIEW` and already exist live, so re-running the whole
file will error on them.

---

## `07_detail_api.sql`

### BEFORE

```sql
CREATE OR REPLACE FUNCTION api.get_project_detail(p_id BIGINT)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT row_to_json(t)::jsonb
    FROM projects.v_project_detail t
    WHERE t.id = p_id;
$$;

CREATE OR REPLACE FUNCTION api.get_contact_detail(p_id BIGINT)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT row_to_json(t)::jsonb
    FROM identity.v_contact_detail t
    WHERE t.id = p_id;
$$;

CREATE OR REPLACE FUNCTION api.get_organization_detail(p_id BIGINT)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT row_to_json(t)::jsonb
    FROM identity.v_organization_detail t
    WHERE t.id = p_id;
$$;
```

### AFTER

```sql
CREATE OR REPLACE FUNCTION api.get_project_detail(p_id BIGINT)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT row_to_json(t)::jsonb
    FROM projects.v_project_detail t
    WHERE t.id = p_id;
$$;

CREATE OR REPLACE FUNCTION api.get_task_detail(p_id BIGINT)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT row_to_json(t)::jsonb
    FROM projects.v_task_detail t
    WHERE t.id = p_id;
$$;

CREATE OR REPLACE FUNCTION api.get_contact_detail(p_id BIGINT)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT row_to_json(t)::jsonb
    FROM identity.v_contact_detail t
    WHERE t.id = p_id;
$$;

CREATE OR REPLACE FUNCTION api.get_organization_detail(p_id BIGINT)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT row_to_json(t)::jsonb
    FROM identity.v_organization_detail t
    WHERE t.id = p_id;
$$;


-- =============================================================================
-- GRANTs — re-run, don't skip
-- The wildcard grant in 06d_api_grants.sql only covered functions that
-- existed in the api schema at the moment it ran. New functions added
-- after that need this re-run, or web_app_user gets a permission error
-- on them specifically — an easy thing to chase as a mysterious bug if
-- this step is skipped.
-- =============================================================================

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO steward;
```

**Why:** Uses `CREATE OR REPLACE FUNCTION`, so unlike `07_detail_views.sql`
this whole file **is** safe to rerun in full — no ordering gotcha here.

---

## `06b_api_projects.sql`

### BEFORE

*(unchanged from the version you uploaded — full file below for reference,
diff is purely additive after `api.delete_project`)*

```sql
-- =============================================================================
-- 06b_api_projects.sql — API schema: projects.* stored procedures
-- =============================================================================
--
-- Split from 06_api.sql — paired with 03_projects.sql (the schema these
-- procs operate on). A future database reusing 03_projects.sql's schema
-- can also reuse this file without dragging along auth or identity procs.
--
-- All procs SECURITY DEFINER — see 06a_api_auth.sql header for the full
-- security model note (applies to all api.* files, not repeated per file).
--
-- Depends on: 01_audit.sql, 03_projects.sql
-- GRANTs live in 06d_api_grants.sql.
-- =============================================================================

-- =============================================================================
-- api.save_project(payload JSONB, user_id BIGINT)
--
-- Insert or update a project record.
-- payload.id present and non-null → UPDATE; absent or null → INSERT.
--
-- Handles:
--   - Slug generation from name (lowercase, spaces to hyphens, deduplication)
--   - status_id and type_id lookup by name if provided as strings
--   - created_by / updated_by stamping
--   - Conflict detection (duplicate name)
--
-- Payload shape:
-- {
--   "id":          null,           -- null/absent = INSERT, int = UPDATE
--   "name":        "My Project",   -- required
--   "description": "...",          -- optional
--   "notes":       "...",          -- optional
--   "status":      "active",       -- name string, looked up to id
--   "type":        "coding",       -- name string, looked up to id (nullable)
--   "target_date": "2026-12-31"    -- ISO date string (nullable)
-- }
-- =============================================================================

CREATE OR REPLACE FUNCTION api.save_project(
    p_payload JSONB,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id          BIGINT;
    v_name        VARCHAR(255);
    v_slug        VARCHAR(100);
    v_slug_base   VARCHAR(100);
    v_slug_suffix INT := 0;
    v_description TEXT;
    v_notes       TEXT;
    v_status_id   BIGINT;
    v_type_id     BIGINT;
    v_target_date DATE;
    v_is_update   BOOLEAN;
BEGIN
    v_name := TRIM(p_payload->>'name');

    IF v_name IS NULL OR v_name = '' THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Project name is required.'
        );
    END IF;

    v_id        := (p_payload->>'id')::BIGINT;
    v_is_update := v_id IS NOT NULL;

    v_description := NULLIF(TRIM(p_payload->>'description'), '');
    v_notes       := NULLIF(TRIM(p_payload->>'notes'), '');
    v_target_date := NULLIF(p_payload->>'target_date', '')::DATE;

    SELECT id INTO v_status_id
    FROM projects.project_status
    WHERE name = LOWER(TRIM(p_payload->>'status'));

    IF v_status_id IS NULL THEN
        SELECT id INTO v_status_id
        FROM projects.project_status
        WHERE name = 'active';
    END IF;

    IF p_payload->>'type' IS NOT NULL AND p_payload->>'type' != '' THEN
        SELECT id INTO v_type_id
        FROM projects.project_type
        WHERE name = LOWER(TRIM(p_payload->>'type'));
    END IF;

    IF v_is_update THEN
        IF NOT EXISTS (SELECT 1 FROM projects.projects WHERE id = v_id) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'Project not found.'
            );
        END IF;

        IF EXISTS (
            SELECT 1 FROM projects.projects
            WHERE name = v_name AND id != v_id
        ) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'A project with that name already exists.'
            );
        END IF;

        UPDATE projects.projects SET
            name        = v_name,
            description = v_description,
            notes       = v_notes,
            status_id   = v_status_id,
            type_id     = v_type_id,
            target_date = v_target_date,
            updated_by  = p_user_id
        WHERE id = v_id;

        RETURN jsonb_build_object(
            'success', TRUE,
            'data',    jsonb_build_object('id', v_id),
            'message', 'Project updated.'
        );

    ELSE
        IF EXISTS (SELECT 1 FROM projects.projects WHERE name = v_name) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'A project with that name already exists.'
            );
        END IF;

        v_slug_base := LOWER(REGEXP_REPLACE(
            REGEXP_REPLACE(v_name, '[^a-zA-Z0-9\s-]', '', 'g'),
            '\s+', '-', 'g'
        ));
        v_slug_base := TRIM(BOTH '-' FROM v_slug_base);
        v_slug      := v_slug_base;

        WHILE EXISTS (SELECT 1 FROM projects.projects WHERE slug = v_slug) LOOP
            v_slug_suffix := v_slug_suffix + 1;
            v_slug := v_slug_base || '-' || v_slug_suffix;
        END LOOP;

        INSERT INTO projects.projects (
            name, slug, description, notes,
            status_id, type_id, target_date,
            created_by, updated_by
        ) VALUES (
            v_name, v_slug, v_description, v_notes,
            v_status_id, v_type_id, v_target_date,
            p_user_id, p_user_id
        )
        RETURNING id INTO v_id;

        RETURN jsonb_build_object(
            'success', TRUE,
            'data',    jsonb_build_object('id', v_id, 'slug', v_slug),
            'message', 'Project created.'
        );
    END IF;

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'api.save_project error: %', SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred saving the project.'
    );
END;
$$;


-- =============================================================================
-- api.delete_project(id BIGINT, user_id BIGINT)
--
-- Soft-deletes are not implemented yet — this is a hard delete.
-- Audit trigger on projects.projects captures the DELETE for the log.
-- Returns error if project has dependent records that block deletion.
-- =============================================================================

CREATE OR REPLACE FUNCTION api.delete_project(
    p_id      BIGINT,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM projects.projects WHERE id = p_id) THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Project not found.'
        );
    END IF;

    DELETE FROM projects.projects WHERE id = p_id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'data',    jsonb_build_object('id', p_id),
        'message', 'Project deleted.'
    );

EXCEPTION WHEN foreign_key_violation THEN
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'Cannot delete project — it has dependent records.'
    );
WHEN OTHERS THEN
    RAISE WARNING 'api.delete_project error for id %: %', p_id, SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred deleting the project.'
    );
END;
$$;
```

### AFTER

Everything above stays identical, with `api.save_task()` and
`api.delete_task()` (full text in Section 4) appended at the end of the file.

**Why here:** `06b_api_projects.sql` is paired with `03_projects.sql`, which
contains both `projects.projects` and `projects.tasks` — same schema-pairing
convention that put `save_project`/`delete_project` here in the first place.

---

## `08b_api_lookup.sql`

### BEFORE / AFTER

Full replacement is Section 5 above (`CREATE OR REPLACE`, entire function) —
adds the `task_statuses` and `priorities` `WHEN` branches to the existing
`CASE`. Everything else in the file (header comments, grants at the bottom)
stays as uploaded.

---

## Known gaps, not addressed here

- **Cycle detection on `parent_id`** goes one level deep (same project,
  not self). A task set as its own grandparent isn't caught. Flag if this
  becomes a real risk once subtasks are actually used.
- **`project_id`/`parent_id` as hidden/picker fields** — fieldkit currently
  requires an explicit override for every `*_id` column, and has no
  "hidden" control type yet. That's the next piece of work, along with
  `app.py`/`panel.py` registration and wiring the Tasks tab's datasheet to
  open this detail panel via the `⋯` button, same as Identities.
- **`fieldkit_overrides.yaml`** entries for `projects.v_task_detail`
  (`status_id` → `task_statuses`, `priority_id` → `priorities`) are Python-
  layer work, not touched in this SQL-only changedoc.
