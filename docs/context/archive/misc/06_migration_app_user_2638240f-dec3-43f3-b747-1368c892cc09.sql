-- =============================================================================
-- 06_migration_app_user.sql — Add crew_role_id to app_user + sessions table
-- =============================================================================
--
-- Run this ONCE against the live wcyj database.
-- Safe to run on a DB that already has the 01–05 schema applied.
-- Do NOT run 00_drop + full rebuild unless you intend to lose all data.
--
-- What this migration does:
--   1. Adds crew_role_id (nullable) to identity.app_user
--   2. Creates identity.app_user_sessions
--   3. Updates GRANTs for steward role to cover new column and table
--
-- After running, update 02_identity.sql in the steward repo to match
-- (already done — the updated file is the deliverable alongside this one).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Add crew_role_id to identity.app_user
--    Nullable — crew members get a value, customer portal users get NULL.
-- -----------------------------------------------------------------------------

ALTER TABLE identity.app_user
    ADD COLUMN crew_role_id BIGINT REFERENCES identity.crew_role (id);

CREATE INDEX idx_app_user_crew_role ON identity.app_user (crew_role_id);

COMMENT ON COLUMN identity.app_user.crew_role_id IS
    'Application persona (captain, mechanic, etc). NULL = customer portal user with no crew UI access.';

COMMENT ON COLUMN identity.app_user.role_id IS
    'Permission tier (admin, staff, customer). Required for all users.';


-- -----------------------------------------------------------------------------
-- 2. Create identity.app_user_sessions
--    Server-side session store. Deleting a row = instant revocation.
--
--    session_token — opaque 256-bit hex string, stored in signed cookie
--    expires_at    — NOW()+30d for "remember me", NOW()+8h for session-only
--    last_seen_at  — updated on every authenticated request (sliding window)
--    ip_address    — IPv4 or IPv6, VARCHAR(45) covers both
-- -----------------------------------------------------------------------------

CREATE TABLE identity.app_user_sessions (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id       BIGINT       NOT NULL REFERENCES identity.app_user (id) ON DELETE CASCADE,
    session_token VARCHAR(128) NOT NULL UNIQUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ  NOT NULL,
    last_seen_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    ip_address    VARCHAR(45),
    user_agent    VARCHAR(500)
);

CREATE INDEX idx_sessions_user    ON identity.app_user_sessions (user_id);
CREATE INDEX idx_sessions_token   ON identity.app_user_sessions (session_token);
CREATE INDEX idx_sessions_expires ON identity.app_user_sessions (expires_at);


-- -----------------------------------------------------------------------------
-- 3. GRANTs for steward role
--    Sessions need all four operations:
--      INSERT  — create session on login
--      SELECT  — validate session on every request
--      UPDATE  — refresh last_seen_at on every request
--      DELETE  — revoke session on logout
-- -----------------------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE, DELETE ON identity.app_user_sessions TO steward;

-- crew_role SELECT already granted in 02_identity.sql — confirming it exists
-- (harmless to re-run; PostgreSQL ignores duplicate grants)
GRANT SELECT ON identity.crew_role TO steward;


-- -----------------------------------------------------------------------------
-- Verification queries — run these in pgAdmin after applying the migration
-- to confirm everything landed correctly.
-- -----------------------------------------------------------------------------

-- Should show crew_role_id column in app_user:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'identity' AND table_name = 'app_user'
-- ORDER BY ordinal_position;

-- Should show app_user_sessions table with all columns:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'identity' AND table_name = 'app_user_sessions'
-- ORDER BY ordinal_position;

-- Should show steward has DELETE on app_user_sessions:
-- SELECT grantee, privilege_type
-- FROM information_schema.role_table_grants
-- WHERE table_schema = 'identity' AND table_name = 'app_user_sessions';
