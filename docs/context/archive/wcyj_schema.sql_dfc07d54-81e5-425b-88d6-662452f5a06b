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
--   contacts — people, organizations, auth
--   projects — projects, tasks
--
-- =============================================================================


-- =============================================================================
-- SCHEMAS
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS contacts;
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


-- -----------------------------------------------------------------------------
-- audit.audit_log
-- Records every INSERT, UPDATE, DELETE on audited tables.
-- changed_by is nullable — captures NULL if action occurs before auth exists.
-- old_values is NULL on INSERT; new_values is NULL on DELETE.
-- -----------------------------------------------------------------------------

CREATE TABLE audit.audit_log (
    id          BIGINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schema_name VARCHAR(100) NOT NULL,
    table_name  VARCHAR(100) NOT NULL,
    record_id   BIGINT    NOT NULL,
    action      VARCHAR(10)  NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    changed_by  BIGINT,      -- FK to contacts.app_user added after that table exists
    changed_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    old_values  JSONB,
    new_values  JSONB
);

CREATE INDEX idx_audit_log_table     ON audit.audit_log (schema_name, table_name);
CREATE INDEX idx_audit_log_record    ON audit.audit_log (record_id);
CREATE INDEX idx_audit_log_changed   ON audit.audit_log (changed_at DESC);
CREATE INDEX idx_audit_log_who       ON audit.audit_log (changed_by);


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
-- CONTACTS SCHEMA
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Lookup tables
-- -----------------------------------------------------------------------------

CREATE TABLE contacts.url_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE contacts.user_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE contacts.organization_contact_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


-- -----------------------------------------------------------------------------
-- contacts.organizations
-- -----------------------------------------------------------------------------

CREATE TABLE contacts.organizations (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    notes      TEXT,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_by BIGINT,      -- FK to contacts.app_user added below
    updated_by BIGINT       -- FK to contacts.app_user added below
);

CREATE INDEX idx_organizations_name ON contacts.organizations (name);

CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON contacts.organizations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_organizations_audit
    AFTER INSERT OR UPDATE OR DELETE ON contacts.organizations
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- -----------------------------------------------------------------------------
-- contacts.contacts
-- name nullable — phone/email-only contacts are allowed.
-- -----------------------------------------------------------------------------

CREATE TABLE contacts.contacts (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(255),
    title      VARCHAR(255),
    notes      TEXT,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_by BIGINT,      -- FK to contacts.app_user added below
    updated_by BIGINT       -- FK to contacts.app_user added below
);

CREATE INDEX idx_contacts_name ON contacts.contacts (name);

CREATE TRIGGER trg_contacts_updated_at
    BEFORE UPDATE ON contacts.contacts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_contacts_audit
    AFTER INSERT OR UPDATE OR DELETE ON contacts.contacts
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- -----------------------------------------------------------------------------
-- contacts.app_user
-- A user must be a contact first.
-- ON DELETE RESTRICT — cannot delete a contact who has a login.
-- -----------------------------------------------------------------------------

CREATE TABLE contacts.app_user (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id    BIGINT       NOT NULL UNIQUE
                               REFERENCES contacts.contacts (id) ON DELETE RESTRICT,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id       BIGINT       NOT NULL REFERENCES contacts.user_role (id),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login    TIMESTAMP,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_app_user_contact  ON contacts.app_user (contact_id);
CREATE INDEX idx_app_user_username ON contacts.app_user (username);
CREATE INDEX idx_app_user_role     ON contacts.app_user (role_id);

CREATE TRIGGER trg_app_user_updated_at
    BEFORE UPDATE ON contacts.app_user
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_app_user_audit
    AFTER INSERT OR UPDATE OR DELETE ON contacts.app_user
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- Now that app_user exists, add FK constraints for created_by / updated_by
-- on organizations and contacts.

ALTER TABLE contacts.organizations
    ADD CONSTRAINT fk_organizations_created_by
        FOREIGN KEY (created_by) REFERENCES contacts.app_user (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_organizations_updated_by
        FOREIGN KEY (updated_by) REFERENCES contacts.app_user (id) ON DELETE SET NULL;

ALTER TABLE contacts.contacts
    ADD CONSTRAINT fk_contacts_created_by
        FOREIGN KEY (created_by) REFERENCES contacts.app_user (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_contacts_updated_by
        FOREIGN KEY (updated_by) REFERENCES contacts.app_user (id) ON DELETE SET NULL;

ALTER TABLE audit.audit_log
    ADD CONSTRAINT fk_audit_log_changed_by
        FOREIGN KEY (changed_by) REFERENCES contacts.app_user (id) ON DELETE SET NULL;


-- -----------------------------------------------------------------------------
-- contacts.contact_emails
-- -----------------------------------------------------------------------------

CREATE TABLE contacts.contact_emails (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id BIGINT       NOT NULL REFERENCES contacts.contacts (id) ON DELETE CASCADE,
    email      VARCHAR(255),
    email_type VARCHAR(50),
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_emails_contact ON contacts.contact_emails (contact_id);
CREATE INDEX idx_contact_emails_email   ON contacts.contact_emails (email);


-- -----------------------------------------------------------------------------
-- contacts.contact_phones
-- -----------------------------------------------------------------------------

CREATE TABLE contacts.contact_phones (
    id           BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id   BIGINT       NOT NULL REFERENCES contacts.contacts (id) ON DELETE CASCADE,
    phone_number VARCHAR(50)  NOT NULL,
    description  VARCHAR(100),
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_phones_contact ON contacts.contact_phones (contact_id);


-- -----------------------------------------------------------------------------
-- contacts.contact_urls
-- -----------------------------------------------------------------------------

CREATE TABLE contacts.contact_urls (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id  BIGINT       NOT NULL REFERENCES contacts.contacts (id) ON DELETE CASCADE,
    url_type_id BIGINT       NOT NULL REFERENCES contacts.url_type (id),
    value       VARCHAR(500) NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_urls_contact ON contacts.contact_urls (contact_id);


-- -----------------------------------------------------------------------------
-- contacts.organization_contacts  (junction)
-- -----------------------------------------------------------------------------

CREATE TABLE contacts.organization_contacts (
    id              BIGINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id BIGINT    NOT NULL REFERENCES contacts.organizations (id) ON DELETE CASCADE,
    contact_id      BIGINT    NOT NULL REFERENCES contacts.contacts (id)      ON DELETE CASCADE,
    role_id         BIGINT    REFERENCES contacts.organization_contact_role (id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_organization_contacts UNIQUE (organization_id, contact_id)
);

CREATE INDEX idx_org_contacts_org     ON contacts.organization_contacts (organization_id);
CREATE INDEX idx_org_contacts_contact ON contacts.organization_contacts (contact_id);


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
-- projects.projects
-- Flat in UI — parent_id exists for future subproject support only.
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
    created_by  BIGINT       REFERENCES contacts.app_user (id) ON DELETE SET NULL,
    updated_by  BIGINT       REFERENCES contacts.app_user (id) ON DELETE SET NULL
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
-- Tasks support sub-tasks via parent_id.
-- project_id stored on every row for query simplicity.
-- ON DELETE NO ACTION on parent_id — app must handle child tasks before
-- deleting a parent task.
-- -----------------------------------------------------------------------------

CREATE TABLE projects.tasks (
    id          BIGINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id  BIGINT    NOT NULL REFERENCES projects.projects (id) ON DELETE CASCADE,
    parent_id   BIGINT    REFERENCES projects.tasks (id) ON DELETE NO ACTION,
    description TEXT      NOT NULL,
    notes       TEXT,
    status_id   BIGINT    NOT NULL REFERENCES projects.task_status (id),
    priority_id BIGINT    REFERENCES projects.priority (id),
    is_terminal BOOLEAN   NOT NULL DEFAULT FALSE,
    sort_order  INT       NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    created_by  BIGINT    REFERENCES contacts.app_user (id) ON DELETE SET NULL,
    updated_by  BIGINT    REFERENCES contacts.app_user (id) ON DELETE SET NULL
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
-- Links contacts to projects with an optional role and notes.
-- -----------------------------------------------------------------------------

CREATE TABLE projects.project_contacts (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT       NOT NULL REFERENCES projects.projects (id)  ON DELETE CASCADE,
    contact_id BIGINT       NOT NULL REFERENCES contacts.contacts (id)  ON DELETE CASCADE,
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

-- contacts.url_type
INSERT INTO contacts.url_type (name) VALUES
    ('github'),
    ('instagram'),
    ('linkedin'),
    ('twitter'),
    ('website');

-- contacts.user_role
INSERT INTO contacts.user_role (name) VALUES
    ('admin'),
    ('customer'),
    ('staff');

-- contacts.organization_contact_role
INSERT INTO contacts.organization_contact_role (name) VALUES
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
    ('queued');

-- projects.project_type
INSERT INTO projects.project_type (name) VALUES
    ('homelab'),
    ('refurb'),
    ('writing');

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
