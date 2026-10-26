-- =============================================================================
-- 04_infrastructure.sql — Infrastructure schema
-- =============================================================================
--
-- Homelab nodes, refurb device tracking, hardware inventory.
-- Lookup tables live in this schema (not projects — that was a prior mistake).
--
-- Hierarchy: nodes → devices → components
--
-- Depends on: 01_audit.sql, 02_identity.sql, 03_projects.sql
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS infrastructure;


-- =============================================================================
-- Lookup tables
-- =============================================================================

CREATE TABLE infrastructure.node_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE infrastructure.node_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE infrastructure.device_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE infrastructure.device_status (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE infrastructure.component_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


-- =============================================================================
-- infrastructure.nodes
-- Physical locations: homelab, customer homes, stores, offices.
-- =============================================================================

CREATE TABLE infrastructure.nodes (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL UNIQUE,
    type_id         BIGINT       REFERENCES infrastructure.node_type (id),
    role_id         BIGINT       REFERENCES infrastructure.node_role (id),
    organization_id BIGINT       REFERENCES identity.organizations (id) ON DELETE SET NULL,
    contact_id      BIGINT       REFERENCES identity.contacts (id)       ON DELETE SET NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_nodes_type    ON infrastructure.nodes (type_id);
CREATE INDEX idx_nodes_role    ON infrastructure.nodes (role_id);
CREATE INDEX idx_nodes_org     ON infrastructure.nodes (organization_id);
CREATE INDEX idx_nodes_contact ON infrastructure.nodes (contact_id);

CREATE TRIGGER trg_nodes_updated_at
    BEFORE UPDATE ON infrastructure.nodes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_nodes_audit
    AFTER INSERT OR UPDATE OR DELETE ON infrastructure.nodes
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- =============================================================================
-- infrastructure.devices
-- Hardware units at a node: servers, laptops, monitors, etc.
-- =============================================================================

CREATE TABLE infrastructure.devices (
    id             BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    node_id        BIGINT       NOT NULL REFERENCES infrastructure.nodes (id)       ON DELETE CASCADE,
    name           VARCHAR(255) NOT NULL,
    device_type_id BIGINT       REFERENCES infrastructure.device_type (id),
    serial_number  VARCHAR(100),
    status_id      BIGINT       REFERENCES infrastructure.device_status (id),
    project_id     BIGINT       REFERENCES projects.projects (id)                   ON DELETE SET NULL,
    description    TEXT,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_devices_node    ON infrastructure.devices (node_id);
CREATE INDEX idx_devices_type    ON infrastructure.devices (device_type_id);
CREATE INDEX idx_devices_status  ON infrastructure.devices (status_id);
CREATE INDEX idx_devices_project ON infrastructure.devices (project_id);

CREATE TRIGGER trg_devices_updated_at
    BEFORE UPDATE ON infrastructure.devices
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_devices_audit
    AFTER INSERT OR UPDATE OR DELETE ON infrastructure.devices
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- =============================================================================
-- infrastructure.components
-- Parts inside a device: SSDs, RAM, NICs, GPUs, etc.
-- =============================================================================

CREATE TABLE infrastructure.components (
    id                BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id         BIGINT       NOT NULL REFERENCES infrastructure.devices (id) ON DELETE CASCADE,
    component_type_id BIGINT       REFERENCES infrastructure.component_type (id),
    name              VARCHAR(255) NOT NULL,
    serial_number     VARCHAR(100),
    description       TEXT,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_components_device ON infrastructure.components (device_id);
CREATE INDEX idx_components_type   ON infrastructure.components (component_type_id);

CREATE TRIGGER trg_components_updated_at
    BEFORE UPDATE ON infrastructure.components
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_components_audit
    AFTER INSERT OR UPDATE OR DELETE ON infrastructure.components
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- =============================================================================
-- GRANTs
-- =============================================================================

GRANT USAGE ON SCHEMA infrastructure TO steward;

GRANT SELECT, INSERT, UPDATE ON
    infrastructure.nodes,
    infrastructure.devices,
    infrastructure.components
TO steward;

GRANT SELECT ON
    infrastructure.node_type,
    infrastructure.node_role,
    infrastructure.device_type,
    infrastructure.device_status,
    infrastructure.component_type
TO steward;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA infrastructure TO steward;
