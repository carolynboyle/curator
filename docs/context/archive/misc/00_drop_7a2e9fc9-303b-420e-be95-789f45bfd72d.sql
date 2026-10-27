-- =============================================================================
-- 00_drop.sql — Drop all wcyj schemas in reverse dependency order
-- =============================================================================
-- Run this BEFORE recreating schemas from scratch.
-- Drops CASCADE handles all tables, views, triggers, sequences within each schema.
-- Run order matters: infrastructure references projects and identity,
-- projects references identity, identity references audit.
-- =============================================================================

DROP SCHEMA IF EXISTS infrastructure CASCADE;
DROP SCHEMA IF EXISTS projects       CASCADE;
DROP SCHEMA IF EXISTS identity       CASCADE;
DROP SCHEMA IF EXISTS audit          CASCADE;

-- Drop shared trigger function in public schema
DROP FUNCTION IF EXISTS public.set_updated_at() CASCADE;
