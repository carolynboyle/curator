-- =============================================================================
-- 06d_api_grants.sql — GRANTs for all api.* functions
-- =============================================================================
--
-- Must run AFTER 06a_api_auth.sql, 06b_api_projects.sql, and
-- 06c_api_identity.sql (or any future 06x_api_*.sql file that adds
-- functions to the api schema).
--
-- A single shared block rather than one GRANT per file — the wildcard
-- (ALL FUNCTIONS IN SCHEMA api) covers every function that exists in the
-- schema at the time this runs, regardless of which file created it, so
-- there's no reason to duplicate the same two GRANT lines three times.
--
-- web_app_user: EXECUTE on all api functions, nothing else.
-- steward:      EXECUTE on all api functions (dev/admin convenience).
-- =============================================================================

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO steward;
