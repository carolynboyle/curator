-- =============================================================================
-- 05_seed.sql — Seed data for wcyj database
-- =============================================================================
-- Run after all schema files (01 through 04).
-- Uses name-based subquery lookups throughout — never hardcoded IDs.
-- =============================================================================


-- =============================================================================
-- identity schema
-- =============================================================================

INSERT INTO identity.url_type (name) VALUES
    ('github'),
    ('instagram'),
    ('linkedin'),
    ('twitter'),
    ('website');

INSERT INTO identity.user_role (name) VALUES
    ('admin'),
    ('staff'),
    ('customer');

INSERT INTO identity.organization_contact_role (name) VALUES
    ('customer'),
    ('employee'),
    ('owner'),
    ('vendor');

-- Curator crew roles
INSERT INTO identity.crew_role (name) VALUES
    ('captain'),
    ('envoy'),
    ('mechanic'),
    ('scribe');


-- =============================================================================
-- projects schema — lookup tables
-- =============================================================================

-- Statuses: common set plus writing-specific
INSERT INTO projects.project_status (name) VALUES
    ('active'),
    ('archived'),
    ('complete'),
    ('on hold'),
    ('queued'),
    ('published'),
    ('ready to write'),
    ('in progress');

-- Project types
INSERT INTO projects.project_type (name) VALUES
    ('coding'),
    ('game-dev'),
    ('homelab'),
    ('personal'),
    ('refurb'),
    ('writing');

INSERT INTO projects.task_status (name, is_terminal) VALUES
    ('backlog',     FALSE),
    ('blocked',     FALSE),
    ('cancelled',   TRUE),
    ('complete',    TRUE),
    ('in progress', FALSE);

INSERT INTO projects.priority (name) VALUES
    ('high'),
    ('low'),
    ('normal'),
    ('urgent');


-- =============================================================================
-- projects schema — mapping tables
-- =============================================================================

-- Role → project type mapping
-- Captain sees all types
INSERT INTO projects.project_type_role_mapping (project_type_id, crew_role_id)
SELECT pt.id, cr.id
FROM projects.project_type pt
CROSS JOIN identity.crew_role cr
WHERE cr.name = 'captain';

-- Scribe sees writing only
INSERT INTO projects.project_type_role_mapping (project_type_id, crew_role_id)
SELECT pt.id, cr.id
FROM projects.project_type pt
JOIN identity.crew_role cr ON cr.name = 'scribe'
WHERE pt.name = 'writing';

-- Mechanic sees homelab and refurb
INSERT INTO projects.project_type_role_mapping (project_type_id, crew_role_id)
SELECT pt.id, cr.id
FROM projects.project_type pt
JOIN identity.crew_role cr ON cr.name = 'mechanic'
WHERE pt.name IN ('homelab', 'refurb');

-- Envoy sees refurb
-- Note: review whether Envoy should see refurb or if that belongs to Mechanic only
-- Adjust via Captain's Command Center once UI is built
INSERT INTO projects.project_type_role_mapping (project_type_id, crew_role_id)
SELECT pt.id, cr.id
FROM projects.project_type pt
JOIN identity.crew_role cr ON cr.name = 'envoy'
WHERE pt.name = 'refurb';


-- Project type → valid status mapping
-- Common statuses for all types
INSERT INTO projects.project_type_status_mapping (project_type_id, status_id)
SELECT pt.id, ps.id
FROM projects.project_type pt
CROSS JOIN projects.project_status ps
WHERE ps.name IN ('active', 'archived', 'complete', 'on hold', 'queued');

-- Writing-specific statuses — writing type only
INSERT INTO projects.project_type_status_mapping (project_type_id, status_id)
SELECT pt.id, ps.id
FROM projects.project_type pt
CROSS JOIN projects.project_status ps
WHERE pt.name = 'writing'
AND ps.name IN ('published', 'ready to write', 'in progress');


-- =============================================================================
-- infrastructure schema — lookup tables
-- =============================================================================

INSERT INTO infrastructure.node_type (name) VALUES
    ('customer-home'),
    ('homelab'),
    ('office'),
    ('store');

INSERT INTO infrastructure.node_role (name) VALUES
    ('database'),
    ('headscale-server'),
    ('hypervisor'),
    ('workstation');

INSERT INTO infrastructure.device_type (name) VALUES
    ('desktop'),
    ('laptop'),
    ('monitor'),
    ('printer'),
    ('server'),
    ('tablet');

INSERT INTO infrastructure.device_status (name) VALUES
    ('deployed'),
    ('in-stock'),
    ('intake'),
    ('refurbished'),
    ('shipped'),
    ('testing');

INSERT INTO infrastructure.component_type (name) VALUES
    ('gpu'),
    ('motherboard'),
    ('nic'),
    ('psu'),
    ('ram'),
    ('ssd');
