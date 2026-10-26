-- ============================================================================
-- Infrastructure Schema & Lookup Tables
-- Lookups live in projects schema; infrastructure owns nodes/devices/components
-- Follows wcyj conventions: BIGINT PKs, created_at/updated_at, audit logging
-- ============================================================================

-- =============================================================================
-- LOOKUP TABLES (in projects schema)
-- =============================================================================

CREATE TABLE IF NOT EXISTS projects.node_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS projects.node_role (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS projects.device_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS projects.device_status (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS projects.component_type (
    id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


-- =============================================================================
-- INFRASTRUCTURE SCHEMA
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS infrastructure;

-- Nodes: physical locations (homelab, customer home, store, office, etc.)
CREATE TABLE infrastructure.nodes (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL UNIQUE,
    type_id         BIGINT       REFERENCES projects.node_type (id),
    role_id         BIGINT       REFERENCES projects.node_role (id),
    organization_id BIGINT       REFERENCES contacts.organizations (id) ON DELETE SET NULL,
    contact_id      BIGINT       REFERENCES contacts.contacts (id) ON DELETE SET NULL,
    description     TEXT,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_nodes_type ON infrastructure.nodes (type_id);
CREATE INDEX idx_nodes_role ON infrastructure.nodes (role_id);
CREATE INDEX idx_nodes_org ON infrastructure.nodes (organization_id);
CREATE INDEX idx_nodes_contact ON infrastructure.nodes (contact_id);

CREATE TRIGGER trg_nodes_updated_at
    BEFORE UPDATE ON infrastructure.nodes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_nodes_audit
    AFTER INSERT OR UPDATE OR DELETE ON infrastructure.nodes
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- Devices: hardware units at a node (servers, laptops, monitors, etc.)
CREATE TABLE infrastructure.devices (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    node_id         BIGINT       NOT NULL REFERENCES infrastructure.nodes (id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    device_type_id  BIGINT       REFERENCES projects.device_type (id),
    serial_number   VARCHAR(100),
    status_id       BIGINT       REFERENCES projects.device_status (id),
    project_id      BIGINT       REFERENCES projects.projects (id) ON DELETE SET NULL,
    description     TEXT,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_devices_node ON infrastructure.devices (node_id);
CREATE INDEX idx_devices_type ON infrastructure.devices (device_type_id);
CREATE INDEX idx_devices_status ON infrastructure.devices (status_id);
CREATE INDEX idx_devices_project ON infrastructure.devices (project_id);

CREATE TRIGGER trg_devices_updated_at
    BEFORE UPDATE ON infrastructure.devices
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_devices_audit
    AFTER INSERT OR UPDATE OR DELETE ON infrastructure.devices
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- Components: parts inside a device (SSDs, RAM, NICs, GPUs, etc.)
CREATE TABLE infrastructure.components (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id       BIGINT       NOT NULL REFERENCES infrastructure.devices (id) ON DELETE CASCADE,
    component_type_id BIGINT     REFERENCES projects.component_type (id),
    name            VARCHAR(255) NOT NULL,
    serial_number   VARCHAR(100),
    description     TEXT,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_components_device ON infrastructure.components (device_id);
CREATE INDEX idx_components_type ON infrastructure.components (component_type_id);

CREATE TRIGGER trg_components_updated_at
    BEFORE UPDATE ON infrastructure.components
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_components_audit
    AFTER INSERT OR UPDATE OR DELETE ON infrastructure.components
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();


-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON SCHEMA infrastructure IS 'Homelab nodes, refurb device tracking, hardware inventory, ansible integration';

COMMENT ON TABLE projects.node_type IS 'Node types: homelab, customer-home, store, office, etc.';
COMMENT ON TABLE projects.node_role IS 'Node roles: headscale-server, database, hypervisor, etc.';
COMMENT ON TABLE projects.device_type IS 'Device types: server, laptop, desktop, monitor, printer, etc.';
COMMENT ON TABLE projects.device_status IS 'Device lifecycle: intake, testing, refurbished, deployed, in-stock, shipped, etc.';
COMMENT ON TABLE projects.component_type IS 'Component types: ssd, ram, nic, gpu, psu, motherboard, etc.';

COMMENT ON TABLE infrastructure.nodes IS 'Physical locations: homelab, customer homes, stores, offices. Can have multiple devices.';
COMMENT ON TABLE infrastructure.devices IS 'Hardware units at a node: servers, laptops, monitors. Can have multiple components.';
COMMENT ON TABLE infrastructure.components IS 'Parts inside a device: SSDs, RAM, NICs, GPUs, power supplies, etc.';

COMMENT ON COLUMN infrastructure.nodes.type_id IS 'References projects.node_type (homelab, customer-home, store, etc.)';
COMMENT ON COLUMN infrastructure.nodes.role_id IS 'References projects.node_role (headscale-server, database, etc.) - optional, primarily for homelab nodes';
COMMENT ON COLUMN infrastructure.nodes.organization_id IS 'References contacts.organizations - for chain stores, companies, etc.';
COMMENT ON COLUMN infrastructure.nodes.contact_id IS 'References contacts.contacts - owner/operator/primary contact for this node';

COMMENT ON COLUMN infrastructure.devices.node_id IS 'References infrastructure.nodes - which location this device is at';
COMMENT ON COLUMN infrastructure.devices.device_type_id IS 'References projects.device_type (server, laptop, monitor, etc.)';
COMMENT ON COLUMN infrastructure.devices.status_id IS 'References projects.device_status (intake, testing, refurbished, deployed, etc.)';
COMMENT ON COLUMN infrastructure.devices.project_id IS 'References projects.projects - if this device is part of a refurb or tracking project';

COMMENT ON COLUMN infrastructure.components.component_type_id IS 'References projects.component_type (ssd, ram, nic, gpu, etc.)';
COMMENT ON COLUMN infrastructure.components.device_id IS 'References infrastructure.devices - which device this component is in';
