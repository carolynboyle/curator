-- =============================================================================
-- 02_identity.sql — Identity schema
-- =============================================================================
--
-- Covers everything that identifies a person or role:
--   - contacts and organizations (people, companies)
--   - app_user (authentication)
--   - crew_role (Curator crew dashboard roles)
--   - lookup tables: url_type, user_role, organization_contact_role
--
-- Depends on: 01_audit.sql (audit.log_change, public.set_updated_at)
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS identity;


-- =============================================================================
-- Lookup tables
-- =============================================================================

CREATE TABLE identity.url_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE identity.user_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE identity.organization_contact_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Curator crew roles — extensible via Captain's Command Center UI
-- New roles added here without schema changes
CREATE TABLE identity.crew_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


-- =============================================================================
-- identity.organizations
-- =============================================================================

CREATE TABLE identity.organizations (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    notes      TEXT,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
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


-- =============================================================================
-- identity.contacts
-- name nullable — phone/email-only contacts are valid.
-- =============================================================================

CREATE TABLE identity.contacts (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(255),
    title      VARCHAR(255),
    notes      TEXT,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
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


-- =============================================================================
-- identity.app_user
-- A user must be a contact first.
-- ON DELETE RESTRICT — cannot delete a contact who has a login.
-- =============================================================================

CREATE TABLE identity.app_user (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id    BIGINT       NOT NULL UNIQUE
                               REFERENCES identity.contacts (id) ON DELETE RESTRICT,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id       BIGINT       NOT NULL REFERENCES identity.user_role (id),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
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


-- Add deferred FKs for created_by / updated_by now that app_user exists

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


-- =============================================================================
-- identity.contact_phones
-- =============================================================================

CREATE TABLE identity.contact_phones (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id BIGINT       NOT NULL REFERENCES identity.contacts (id) ON DELETE CASCADE,
    label      VARCHAR(50),
    number     VARCHAR(50)  NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_phones_contact ON identity.contact_phones (contact_id);


-- =============================================================================
-- identity.contact_emails
-- =============================================================================

CREATE TABLE identity.contact_emails (
    id         BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id BIGINT       NOT NULL REFERENCES identity.contacts (id) ON DELETE CASCADE,
    label      VARCHAR(50),
    address    VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_emails_contact ON identity.contact_emails (contact_id);


-- =============================================================================
-- identity.contact_urls
-- =============================================================================

CREATE TABLE identity.contact_urls (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id  BIGINT       NOT NULL REFERENCES identity.contacts (id) ON DELETE CASCADE,
    url_type_id BIGINT       NOT NULL REFERENCES identity.url_type (id),
    value       VARCHAR(500) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contact_urls_contact ON identity.contact_urls (contact_id);


-- =============================================================================
-- identity.organization_contacts  (junction)
-- =============================================================================

CREATE TABLE identity.organization_contacts (
    id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id BIGINT      NOT NULL REFERENCES identity.organizations (id) ON DELETE CASCADE,
    contact_id      BIGINT      NOT NULL REFERENCES identity.contacts (id)      ON DELETE CASCADE,
    role_id         BIGINT      REFERENCES identity.organization_contact_role (id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_organization_contacts UNIQUE (organization_id, contact_id)
);

CREATE INDEX idx_org_contacts_org     ON identity.organization_contacts (organization_id);
CREATE INDEX idx_org_contacts_contact ON identity.organization_contacts (contact_id);


-- =============================================================================
-- GRANTs
-- =============================================================================

GRANT USAGE ON SCHEMA identity TO steward;

GRANT SELECT, INSERT, UPDATE ON
    identity.contacts,
    identity.organizations,
    identity.contact_phones,
    identity.contact_emails,
    identity.contact_urls,
    identity.organization_contacts,
    identity.app_user
TO steward;

GRANT SELECT ON
    identity.url_type,
    identity.user_role,
    identity.organization_contact_role,
    identity.crew_role
TO steward;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA identity TO steward;
