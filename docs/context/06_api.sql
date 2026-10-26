-- =============================================================================
-- 06_api.sql — API schema: stored procedures and web_app_user role
-- =============================================================================
--
-- This schema is the ONLY interface between the application and raw data.
-- Python routes call procs here; they never touch identity.* or projects.*
-- tables directly.
--
-- Security model:
--   web_app_user  — application DB role; EXECUTE on api.* only
--   steward       — existing dev/admin role; retained for direct table access
--                   during development; revoke when going public
--   All procs use SECURITY DEFINER so they run as the proc owner (postgres),
--   not as web_app_user. web_app_user cannot read tables directly.
--
-- Auth flow:
--   1. Python receives username + password from login form
--   2. Python calls api.login(username, password)
--   3. Proc fetches hash, verifies with pgcrypto crypt(), creates session
--   4. Proc returns JSONB: {success, session_token, user_id, role, crew_role}
--   5. Python sets signed cookie containing session_token
--   6. Every request: Python calls api.validate_session(token)
--   7. Logout: Python calls api.invalidate_session(token)
--
-- Uniform response envelope:
--   Success: {"success": true,  "data": {...}, "message": "..."}
--   Failure: {"success": false, "data": null,  "message": "Human-readable error"}
--
-- Depends on: 01_audit.sql, 02_identity.sql, 03_projects.sql, pgcrypto extension
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS api;


-- =============================================================================
-- web_app_user role
-- The application connects to PostgreSQL as this role in production.
-- Cannot SELECT, INSERT, UPDATE, or DELETE any table directly.
-- Can only EXECUTE functions in the api schema.
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'web_app_user') THEN
        CREATE ROLE web_app_user WITH LOGIN PASSWORD 'change_me_before_production';
    END IF;
END
$$;

-- web_app_user gets schema visibility but no table access
GRANT USAGE ON SCHEMA api TO web_app_user;

-- Explicitly deny direct table access (belt and suspenders)
-- web_app_user has no GRANT on identity.* or projects.* so this is
-- already the default — stated here for documentation clarity.


-- =============================================================================
-- api.create_session(user_id, remember_me)
--
-- Internal helper — called by api.login(), also available standalone
-- for future SSO or token refresh flows.
--
-- Generates a 32-byte (64 hex char) cryptographically random session token.
-- remember_me = TRUE  → expires in 30 days
-- remember_me = FALSE → expires in 8 hours
--
-- Returns the session token as TEXT.
-- =============================================================================

CREATE OR REPLACE FUNCTION api.create_session(
    p_user_id    BIGINT,
    p_remember   BOOLEAN  DEFAULT FALSE,
    p_ip         VARCHAR  DEFAULT NULL,
    p_user_agent VARCHAR  DEFAULT NULL
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_token      VARCHAR(128);
    v_expires_at TIMESTAMPTZ;
BEGIN
    -- Generate cryptographically random token (32 bytes = 64 hex chars)
    v_token := encode(gen_random_bytes(32), 'hex');

    -- Set expiry based on remember_me flag
    v_expires_at := CASE
        WHEN p_remember THEN NOW() + INTERVAL '30 days'
        ELSE                  NOW() + INTERVAL '8 hours'
    END;

    INSERT INTO identity.app_user_sessions (
        user_id,
        session_token,
        expires_at,
        ip_address,
        user_agent
    ) VALUES (
        p_user_id,
        v_token,
        v_expires_at,
        p_ip,
        p_user_agent
    );

    RETURN v_token;
END;
$$;


-- =============================================================================
-- api.login(username, password, remember_me, ip, user_agent)
--
-- Verifies credentials using pgcrypto bcrypt.
-- On success: creates a session, updates last_login, returns full user context.
-- On failure: returns success=false with a safe error message.
--
-- The password hash never leaves the database.
-- Python receives only the session token and user metadata.
--
-- Response JSONB shape (success):
-- {
--   "success": true,
--   "message": "Login successful.",
--   "data": {
--     "session_token": "...",
--     "user_id": 1,
--     "username": "carolyn",
--     "user_role": "admin",
--     "crew_role": "captain",   -- null for customer portal users
--     "contact_id": 1
--   }
-- }
-- =============================================================================

CREATE OR REPLACE FUNCTION api.login(
    p_username   VARCHAR,
    p_password   VARCHAR,
    p_remember   BOOLEAN  DEFAULT FALSE,
    p_ip         VARCHAR  DEFAULT NULL,
    p_user_agent VARCHAR  DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user        identity.app_user%ROWTYPE;
    v_user_role   VARCHAR(50);
    v_crew_role   VARCHAR(50);
    v_token       TEXT;
BEGIN
    -- Fetch user record by username
    SELECT * INTO v_user
    FROM identity.app_user
    WHERE username = p_username;

    -- User not found — same message as wrong password (no enumeration)
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Invalid username or password.'
        );
    END IF;

    -- Account inactive
    IF NOT v_user.is_active THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Account is inactive. Contact your administrator.'
        );
    END IF;

    -- Verify password using pgcrypto bcrypt
    -- crypt() with the stored hash as salt re-hashes the input and compares
    IF v_user.password_hash != crypt(p_password, v_user.password_hash) THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Invalid username or password.'
        );
    END IF;

    -- Fetch role names for response
    SELECT name INTO v_user_role
    FROM identity.user_role
    WHERE id = v_user.role_id;

    SELECT name INTO v_crew_role
    FROM identity.crew_role
    WHERE id = v_user.crew_role_id;
    -- v_crew_role will be NULL for customer portal users — that's correct

    -- Create session
    v_token := api.create_session(v_user.id, p_remember, p_ip, p_user_agent);

    -- Update last_login timestamp
    UPDATE identity.app_user
    SET last_login = NOW()
    WHERE id = v_user.id;

    -- Return success envelope
    RETURN jsonb_build_object(
        'success', TRUE,
        'message', 'Login successful.',
        'data', jsonb_build_object(
            'session_token', v_token,
            'user_id',       v_user.id,
            'username',      v_user.username,
            'user_role',     v_user_role,
            'crew_role',     v_crew_role,
            'contact_id',    v_user.contact_id
        )
    );

EXCEPTION WHEN OTHERS THEN
    -- Never leak internal error details to the caller
    RAISE WARNING 'api.login error for user %: %', p_username, SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred. Please try again.'
    );
END;
$$;


-- =============================================================================
-- api.validate_session(token, ip)
--
-- Called by Python middleware on every authenticated request.
-- Returns full user context if session is valid and not expired.
-- Returns null data if session is missing, expired, or invalid.
-- Updates last_seen_at as a sliding window.
--
-- Python middleware pattern:
--   result = await db.fetch_one("SELECT api.validate_session(%s)", (token,))
--   if not result["success"]: redirect to login
--   request.state.user = result["data"]
-- =============================================================================

CREATE OR REPLACE FUNCTION api.validate_session(
    p_token VARCHAR,
    p_ip    VARCHAR DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_session identity.app_user_sessions%ROWTYPE;
    v_user    identity.app_user%ROWTYPE;
    v_user_role  VARCHAR(50);
    v_crew_role  VARCHAR(50);
BEGIN
    -- Fetch session
    SELECT * INTO v_session
    FROM identity.app_user_sessions
    WHERE session_token = p_token;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Session not found.'
        );
    END IF;

    -- Check expiry
    IF v_session.expires_at < NOW() THEN
        -- Clean up expired session
        DELETE FROM identity.app_user_sessions WHERE id = v_session.id;
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Session expired.'
        );
    END IF;

    -- Fetch user
    SELECT * INTO v_user
    FROM identity.app_user
    WHERE id = v_session.user_id AND is_active = TRUE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'User not found or inactive.'
        );
    END IF;

    -- Fetch role names
    SELECT name INTO v_user_role FROM identity.user_role  WHERE id = v_user.role_id;
    SELECT name INTO v_crew_role FROM identity.crew_role  WHERE id = v_user.crew_role_id;

    -- Slide the window — update last_seen_at
    UPDATE identity.app_user_sessions
    SET last_seen_at = NOW()
    WHERE id = v_session.id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'message', 'Session valid.',
        'data', jsonb_build_object(
            'user_id',    v_user.id,
            'username',   v_user.username,
            'user_role',  v_user_role,
            'crew_role',  v_crew_role,
            'contact_id', v_user.contact_id,
            'session_id', v_session.id
        )
    );

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'api.validate_session error: %', SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'Session validation error.'
    );
END;
$$;


-- =============================================================================
-- api.invalidate_session(token)
--
-- Logout. Deletes the session row — instant revocation.
-- Always returns success=true (idempotent — logging out twice is not an error).
-- =============================================================================

CREATE OR REPLACE FUNCTION api.invalidate_session(
    p_token VARCHAR
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    DELETE FROM identity.app_user_sessions
    WHERE session_token = p_token;

    RETURN jsonb_build_object(
        'success', TRUE,
        'data',    NULL,
        'message', 'Logged out.'
    );

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'api.invalidate_session error: %', SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'Logout error.'
    );
END;
$$;


-- =============================================================================
-- api.purge_expired_sessions()
--
-- Housekeeping proc — deletes all expired session rows.
-- Call this on a schedule (e.g. pg_cron nightly, or from a Python startup hook).
-- Returns count of deleted rows in message.
-- =============================================================================

CREATE OR REPLACE FUNCTION api.purge_expired_sessions()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INT;
BEGIN
    DELETE FROM identity.app_user_sessions
    WHERE expires_at < NOW();

    GET DIAGNOSTICS v_count = ROW_COUNT;

    RETURN jsonb_build_object(
        'success', TRUE,
        'data',    jsonb_build_object('deleted_count', v_count),
        'message', format('Purged %s expired session(s).', v_count)
    );

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'api.purge_expired_sessions error: %', SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'Purge error.'
    );
END;
$$;


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


-- =============================================================================
-- GRANTs
-- web_app_user: EXECUTE on all api functions, nothing else.
-- steward: EXECUTE on all api functions (dev/admin convenience).
-- =============================================================================

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO steward;

