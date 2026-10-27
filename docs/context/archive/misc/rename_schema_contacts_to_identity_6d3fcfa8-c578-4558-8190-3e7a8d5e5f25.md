# Changedoc: Rename Schema `contacts` → `identity`

**Date**: 2026-06-24  
**Type**: Schema change  
**Status**: Ready to execute  
**Run via**: pgAdmin query tool connected to wcyj on steward (100.64.0.7)  
**Git commit message**: `chart: rename contacts schema to identity`

---

## Reason

The `contacts` schema was named for its initial contents (people, organizations).
As the design matured, it became clear it also owns role definitions, authentication,
and crew roster — everything about *who* someone is and what they're allowed to do.
`identity` is the more accurate name and scales naturally as auth and crew management
are built out.

This rename happens now, before the Phase 2.1 data migration runs and before any
app code references the schema directly.

---

## What Changes

### In the database
- Schema `contacts` renamed to `identity`
- PostgreSQL automatically updates all FK references on a schema rename
- All tables, indexes, triggers, and constraints are preserved as-is

### Files to update after running SQL
- `wcyj_schema.sql` — all `contacts.` references → `identity.`
- `wcyj_infrastructure_schema.sql` — check for any `contacts.` references
- Any future app code — use `identity.` schema prefix throughout

---

## Step 1: Run in pgAdmin (wcyj query tool)

```sql
ALTER SCHEMA contacts RENAME TO identity;
```

One line. PostgreSQL handles all internal references automatically.

---

## Step 2: Verify

```sql
-- Confirm schema renamed
SELECT schema_name FROM information_schema.schemata
WHERE schema_name IN ('contacts', 'identity')
ORDER BY schema_name;
-- Expected: only 'identity' appears, 'contacts' is gone

-- Confirm tables still exist under new schema name
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'identity'
ORDER BY tablename;
-- Expected: app_user, contact_emails, contact_phones, contact_urls,
--           contacts, organization_contact_role, organization_contacts,
--           organizations, url_type, user_role

-- Confirm seed data survived
SELECT id, name FROM identity.url_type ORDER BY id;
SELECT id, name FROM identity.user_role ORDER BY id;
SELECT id, name FROM identity.organization_contact_role ORDER BY id;
```

---

## Updated wcyj_schema.sql

Replace the entire contents of `wcyj_schema.sql` with the version below.
The only changes are `contacts.` → `identity.` and `CREATE SCHEMA contacts`
→ `CREATE SCHEMA identity`.

```sql
-- =============================================================================
-- wcyj database schema
-- =============================================================================
--
-- Conventions:
--   - All tables use BIGINT GENERATED ALWAYS AS IDENTITY primary keys
--   - All FK columns are BIGINT to match
--   - created_at / updated_at on every mutable entity table
--   - updated_at maintained automatically by trigger
--   - Categorical values use lookup tables with BIGINT foreign keys
--   - Lookup tables have no sort_order — ORDER BY name in queries
--   - slug columns are the stable human-readable handle for URL references
--   - created_by / updated_by on all entity tables
--   - Audit log covers all schemas via audit.audit_log
--
-- Schemas:
--   audit    — shared audit log
--   identity — people, organizations, roles, auth
--   projects — projects, tasks
--
-- =============================================================================


-- =============================================================================
-- SCHEMAS
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS projects;


-- =============================================================================
-- SHARED TRIGGER FUNCTION
-- Keeps updated_at current on any UPDATE.
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
-- AUDIT SCHEMA
-- Single audit log covering all schemas.
-- Populated by per-table triggers defined alongside each table.
-- =============================================================================

CREATE TABLE audit.audit_log (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schema_name VARCHAR(100) NOT NULL,
    table_name  VARCHAR(100) NOT NULL,
    record_id   BIGINT       NOT NULL,
    action      VARCHAR(10)  NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    changed_by  BIGINT,      -- FK to identity.app_user added after that table exists
    changed_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    old_values  JSONB,
    new_values  JSONB
);

CREATE INDEX idx_audit_log_table   ON audit.audit_log (schema_name, table_name);
CREATE INDEX idx_audit_log_record  ON audit.audit_log (record_id);
CREATE INDEX idx_audit_log_changed ON audit.audit_log (changed_at DESC);
CREATE INDEX idx_audit_log_who     ON audit.audit_log (changed_by);

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
-- IDENTITY SCHEMA
-- People, organizations, crew roles, and authentication.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Lookup tables
-- -----------------------------------------------------------------------------

CREATE TABLE identity.url_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE identity.crew_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE identity.organization_contact_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


-- -----------------------------------------------------------------------------
-- identity.organizations
-- -----------------------------------------------------------------------------

CREATE TABLE identity.organizations (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    notes      TEXT,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_by BIGINT,      -- FK to identity.app_user added below
    updated_by BIGINT       -- FK to identity.app_user added below
);

CREATE INDEX idx_organizations_name ON identity.organizations (name);

CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON identity.organizations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_organizations_audit
    AFTER INSERT OR UPDATE OR DELETE ON identity.organizations
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- -----------------------------------------------------------------------------
-- identity.contacts
-- name nullable — phone/email-only contacts are allowed.
-- -----------------------------------------------------------------------------

CREATE TABLE identity.contacts (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(255),
    title      VARCHAR(255),
    notes      TEXT,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_by BIGINT,      -- FK to identity.app_user added below
    updated_by BIGINT       -- FK to identity.app_user added below
);

CREATE INDEX idx_contacts_name ON identity.contacts (name);

CREATE TRIGGER trg_contacts_updated_at
    BEFORE UPDATE ON identity.contacts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_contacts_audit
    AFTER INSERT OR UPDATE OR DELETE ON identity.contacts
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- -----------------------------------------------------------------------------
-- identity.app_user
-- A user must be a contact first.
-- ON DELETE RESTRICT — cannot delete a contact who has a login.
-- -----------------------------------------------------------------------------

CREATE TABLE identity.app_user (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id    BIGINT       NOT NULL UNIQUE
                               REFERENCES identity.contacts (id) ON DELETE RESTRICT,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id       BIGINT       NOT NULL REFERENCES identity.crew_role (id),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login    TIMESTAMP,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_app_user_contact  ON identity.app_user (contact_id);
CREATE INDEX idx_app_user_username ON identity.app_user (username);
CREATE INDEX idx_app_user_role     ON identity.app_user (role_id);

CREATE TRIGGER trg_app_user_updated_at
    BEFORE UPDATE ON identity.app_user
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_app_user_audit
    AFTER INSERT OR UPDATE OR DELETE ON identity.app_user
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- Now that app_user exists, add FK constraints for created_by / updated_by
-- on organizations and contacts.

ALTER TABLE identity.organizations
    ADD CONSTRAINT fk_organizations_created_by
        FOREIGN KEY (created_by) REFERENCES identity.app_user (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_organizations_updated_by
        FOREIGN KEY (updated_by) REFERENCES identity.app_user (id) ON DELETE SET NULL;

ALTER TABLE identity.contacts
    ADD CONSTRAINT fk_contacts_created_by
        FOREIGN KEY (created_by) REFERENCES identity.app_user (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_contacts_updated_by
        FOREIGN KEY (updated_by) REFERENCES identity.app_user (id) ON DELETE SET NULL;

ALTER TABLE audit.audit_log
    ADD CONSTRAINT fk_audit_log_changed_by
        FOREIGN KEY (changed_by) REFERENCES identity.app_user (id) ON DELETE SET NULL;


-- -----------------------------------------------------------------------------
-- identity.contact_emails
-- -----------------------------------------------------------------------------

CREATE TABLE identity.contact_emails (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id BIGINT       NOT NULL REFERENCES identity.contacts (id) ON DELETE CASCADE,
    email      VARCHAR(255),
    email_type VARCHAR(50),
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_emails_contact ON identity.contact_emails (contact_id);
CREATE INDEX idx_contact_emails_email   ON identity.contact_emails (email);


-- -----------------------------------------------------------------------------
-- identity.contact_phones
-- -----------------------------------------------------------------------------

CREATE TABLE identity.contact_phones (
    id           BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id   BIGINT       NOT NULL REFERENCES identity.contacts (id) ON DELETE CASCADE,
    phone_number VARCHAR(50)  NOT NULL,
    description  VARCHAR(100),
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_phones_contact ON identity.contact_phones (contact_id);


-- -----------------------------------------------------------------------------
-- identity.contact_urls
-- -----------------------------------------------------------------------------

CREATE TABLE identity.contact_urls (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id  BIGINT       NOT NULL REFERENCES identity.contacts (id) ON DELETE CASCADE,
    url_type_id BIGINT       NOT NULL REFERENCES identity.url_type (id),
    value       VARCHAR(500) NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_urls_contact ON identity.contact_urls (contact_id);


-- -----------------------------------------------------------------------------
-- identity.organization_contacts  (junction)
-- -----------------------------------------------------------------------------

CREATE TABLE identity.organization_contacts (
    id              BIGINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id BIGINT    NOT NULL REFERENCES identity.organizations (id) ON DELETE CASCADE,
    contact_id      BIGINT    NOT NULL REFERENCES identity.contacts (id)      ON DELETE CASCADE,
    role_id         BIGINT    REFERENCES identity.organization_contact_role (id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_organization_contacts UNIQUE (organization_id, contact_id)
);

CREATE INDEX idx_org_contacts_org     ON identity.organization_contacts (organization_id);
CREATE INDEX idx_org_contacts_contact ON identity.organization_contacts (contact_id);


-- =============================================================================
-- PROJECTS SCHEMA
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Lookup tables
-- -----------------------------------------------------------------------------

CREATE TABLE projects.project_status (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE projects.project_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE projects.task_status (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,
    is_terminal BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE TABLE projects.priority (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


-- -----------------------------------------------------------------------------
-- projects.project_type_role_mapping
-- Maps project types to crew roles for filtering.
-- Captain mapped to all types by default; adjustable via Captain UI.
-- -----------------------------------------------------------------------------

CREATE TABLE projects.project_type_role_mapping (
    id              BIGINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_type_id BIGINT    NOT NULL REFERENCES projects.project_type (id) ON DELETE CASCADE,
    crew_role_id    BIGINT    NOT NULL REFERENCES identity.crew_role (id)    ON DELETE CASCADE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by      BIGINT    REFERENCES identity.app_user (id) ON DELETE SET NULL,
    UNIQUE(project_type_id, crew_role_id)
);

CREATE INDEX idx_type_mapping_type ON projects.project_type_role_mapping (project_type_id);
CREATE INDEX idx_type_mapping_role ON projects.project_type_role_mapping (crew_role_id);

COMMENT ON TABLE projects.project_type_role_mapping IS 'Maps project types to crew roles for filtering.';


-- -----------------------------------------------------------------------------
-- projects.project_status_role_mapping
-- Maps project statuses to crew roles for dropdown filtering.
-- Captain mapped to all statuses by default; adjustable via Captain UI.
-- -----------------------------------------------------------------------------

CREATE TABLE projects.project_status_role_mapping (
    id           BIGINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status_id    BIGINT    NOT NULL REFERENCES projects.project_status (id) ON DELETE CASCADE,
    crew_role_id BIGINT    NOT NULL REFERENCES identity.crew_role (id)      ON DELETE CASCADE,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by   BIGINT    REFERENCES identity.app_user (id) ON DELETE SET NULL,
    UNIQUE(status_id, crew_role_id)
);

CREATE INDEX idx_status_mapping_status ON projects.project_status_role_mapping (status_id);
CREATE INDEX idx_status_mapping_role   ON projects.project_status_role_mapping (crew_role_id);

COMMENT ON TABLE projects.project_status_role_mapping IS 'Maps project statuses to crew roles for dropdown filtering.';


-- -----------------------------------------------------------------------------
-- projects.projects
-- -----------------------------------------------------------------------------

CREATE TABLE projects.projects (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    notes       TEXT,
    status_id   BIGINT       NOT NULL REFERENCES projects.project_status (id),
    type_id     BIGINT       REFERENCES projects.project_type (id),
    parent_id   BIGINT       REFERENCES projects.projects (id) ON DELETE SET NULL,
    target_date DATE,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_by  BIGINT       REFERENCES identity.app_user (id) ON DELETE SET NULL,
    updated_by  BIGINT       REFERENCES identity.app_user (id) ON DELETE SET NULL
);

CREATE INDEX idx_projects_status ON projects.projects (status_id);
CREATE INDEX idx_projects_type   ON projects.projects (type_id);
CREATE INDEX idx_projects_parent ON projects.projects (parent_id);
CREATE INDEX idx_projects_slug   ON projects.projects (slug);

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects.projects
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_projects_audit
    AFTER INSERT OR UPDATE OR DELETE ON projects.projects
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- -----------------------------------------------------------------------------
-- projects.tasks
-- -----------------------------------------------------------------------------

CREATE TABLE projects.tasks (
    id           BIGINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id   BIGINT    NOT NULL REFERENCES projects.projects (id) ON DELETE CASCADE,
    parent_id    BIGINT    REFERENCES projects.tasks (id) ON DELETE NO ACTION,
    description  TEXT      NOT NULL,
    notes        TEXT,
    status_id    BIGINT    NOT NULL REFERENCES projects.task_status (id),
    priority_id  BIGINT    REFERENCES projects.priority (id),
    is_terminal  BOOLEAN   NOT NULL DEFAULT FALSE,
    sort_order   INT       NOT NULL DEFAULT 0,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    created_by   BIGINT    REFERENCES identity.app_user (id) ON DELETE SET NULL,
    updated_by   BIGINT    REFERENCES identity.app_user (id) ON DELETE SET NULL
);

CREATE INDEX idx_tasks_project  ON projects.tasks (project_id);
CREATE INDEX idx_tasks_parent   ON projects.tasks (parent_id);
CREATE INDEX idx_tasks_status   ON projects.tasks (status_id);
CREATE INDEX idx_tasks_priority ON projects.tasks (priority_id);

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON projects.tasks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_tasks_audit
    AFTER INSERT OR UPDATE OR DELETE ON projects.tasks
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- -----------------------------------------------------------------------------
-- projects.project_contacts  (junction)
-- -----------------------------------------------------------------------------

CREATE TABLE projects.project_contacts (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT       NOT NULL REFERENCES projects.projects (id)  ON DELETE CASCADE,
    contact_id BIGINT       NOT NULL REFERENCES identity.contacts (id)  ON DELETE CASCADE,
    role       VARCHAR(100),
    is_primary BOOLEAN      NOT NULL DEFAULT FALSE,
    notes      TEXT,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_project_contacts UNIQUE (project_id, contact_id)
);

CREATE INDEX idx_project_contacts_project ON projects.project_contacts (project_id);
CREATE INDEX idx_project_contacts_contact ON projects.project_contacts (contact_id);


-- =============================================================================
-- SEED DATA
-- =============================================================================

-- identity.url_type
INSERT INTO identity.url_type (name) VALUES
    ('github'),
    ('instagram'),
    ('linkedin'),
    ('twitter'),
    ('website');

-- identity.crew_role
INSERT INTO identity.crew_role (name) VALUES
    ('captain'),
    ('envoy'),
    ('mechanic'),
    ('scribe');

-- identity.organization_contact_role
INSERT INTO identity.organization_contact_role (name) VALUES
    ('customer'),
    ('employee'),
    ('owner'),
    ('vendor');

-- projects.project_status
INSERT INTO projects.project_status (name) VALUES
    ('active'),
    ('archived'),
    ('complete'),
    ('on hold'),
    ('queued'),
    ('published'),
    ('ready to write'),
    ('in progress');

-- projects.project_type
INSERT INTO projects.project_type (name) VALUES
    ('homelab'),
    ('refurb'),
    ('writing'),
    ('coding'),
    ('game-dev'),
    ('personal');

-- projects.task_status
INSERT INTO projects.task_status (name, is_terminal) VALUES
    ('backlog',     FALSE),
    ('blocked',     FALSE),
    ('cancelled',   TRUE),
    ('complete',    TRUE),
    ('in progress', FALSE);

-- projects.priority
INSERT INTO projects.priority (name) VALUES
    ('high'),
    ('low'),
    ('normal'),
    ('urgent');
```

---

## After Running

1. Run the verify queries in Step 2 above
2. Update `wcyj_schema.sql` in the repo with the version above
3. Proceed to `phase2_migration.md` — the migration SQL references `identity.crew_role` by name lookup, so the rename must be complete first
4. Git commit: `chart: rename contacts schema to identity`

