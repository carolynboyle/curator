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
    -- Extract and validate required fields
    v_name := TRIM(p_payload->>'name');

    IF v_name IS NULL OR v_name = '' THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Project name is required.'
        );
    END IF;

    -- Determine insert vs update
    v_id        := (p_payload->>'id')::BIGINT;
    v_is_update := v_id IS NOT NULL;

    -- Optional fields
    v_description := NULLIF(TRIM(p_payload->>'description'), '');
    v_notes       := NULLIF(TRIM(p_payload->>'notes'), '');
    v_target_date := NULLIF(p_payload->>'target_date', '')::DATE;

    -- Resolve status by name (required)
    SELECT id INTO v_status_id
    FROM projects.project_status
    WHERE name = LOWER(TRIM(p_payload->>'status'));

    IF v_status_id IS NULL THEN
        -- Default to 'active' if not provided or not found
        SELECT id INTO v_status_id
        FROM projects.project_status
        WHERE name = 'active';
    END IF;

    -- Resolve type by name (optional)
    IF p_payload->>'type' IS NOT NULL AND p_payload->>'type' != '' THEN
        SELECT id INTO v_type_id
        FROM projects.project_type
        WHERE name = LOWER(TRIM(p_payload->>'type'));
    END IF;

    IF v_is_update THEN
        -- Verify record exists
        IF NOT EXISTS (SELECT 1 FROM projects.projects WHERE id = v_id) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'Project not found.'
            );
        END IF;

        -- Check for name conflict on other records
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
        -- INSERT path

        -- Check for name conflict
        IF EXISTS (SELECT 1 FROM projects.projects WHERE name = v_name) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'A project with that name already exists.'
            );
        END IF;

        -- Generate slug from name
        -- lowercase, replace non-alphanumeric with hyphens, collapse multiples
        v_slug_base := LOWER(REGEXP_REPLACE(
            REGEXP_REPLACE(v_name, '[^a-zA-Z0-9\s-]', '', 'g'),
            '\s+', '-', 'g'
        ));
        v_slug_base := TRIM(BOTH '-' FROM v_slug_base);
        v_slug      := v_slug_base;

        -- Deduplicate slug if needed
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
