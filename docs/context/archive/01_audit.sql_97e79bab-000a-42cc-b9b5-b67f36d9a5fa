-- =============================================================================
-- 01_audit.sql — Audit schema
-- =============================================================================
--
-- Single audit log covering all schemas.
-- Reusable: drop this file into any database that needs audit logging.
-- Populated by per-table triggers defined alongside each table.
--
-- Conventions:
--   - BIGINT GENERATED ALWAYS AS IDENTITY primary keys
--   - created_at / updated_at on every mutable entity table
--   - updated_at maintained by public.set_updated_at() trigger
--   - No sort_order columns — ORDER BY name in queries
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS audit;


-- =============================================================================
-- Shared trigger function
-- Defined in public schema so all schemas can use it.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- audit.audit_log
-- Records every INSERT, UPDATE, DELETE on audited tables.
-- changed_by is nullable — captures NULL if action occurs before auth exists.
-- old_values is NULL on INSERT; new_values is NULL on DELETE.
-- =============================================================================

CREATE TABLE audit.audit_log (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schema_name VARCHAR(100) NOT NULL,
    table_name  VARCHAR(100) NOT NULL,
    record_id   BIGINT       NOT NULL,
    action      VARCHAR(10)  NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    changed_by  BIGINT,      -- FK to identity.app_user added after that table exists
    changed_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    old_values  JSONB,
    new_values  JSONB
);

CREATE INDEX idx_audit_log_table   ON audit.audit_log (schema_name, table_name);
CREATE INDEX idx_audit_log_record  ON audit.audit_log (record_id);
CREATE INDEX idx_audit_log_changed ON audit.audit_log (changed_at DESC);
CREATE INDEX idx_audit_log_who     ON audit.audit_log (changed_by);


-- Shared audit trigger function
-- Each audited table gets a trigger that calls this function.

CREATE OR REPLACE FUNCTION audit.log_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit.audit_log (schema_name, table_name, record_id, action, new_values)
        VALUES (TG_TABLE_SCHEMA, TG_TABLE_NAME, NEW.id, 'INSERT', to_jsonb(NEW));

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.audit_log (schema_name, table_name, record_id, action, old_values, new_values)
        VALUES (TG_TABLE_SCHEMA, TG_TABLE_NAME, NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW));

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit.audit_log (schema_name, table_name, record_id, action, old_values)
        VALUES (TG_TABLE_SCHEMA, TG_TABLE_NAME, OLD.id, 'DELETE', to_jsonb(OLD));
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- GRANTs
-- =============================================================================

GRANT USAGE ON SCHEMA audit TO steward;
GRANT INSERT ON audit.audit_log TO steward;
