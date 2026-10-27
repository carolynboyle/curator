-- =============================================================================
-- 03_projects.sql — Projects schema
-- =============================================================================
--
-- Covers projects, tasks, and Curator role-filtering machinery:
--   - Lookup tables: project_status, project_type, task_status, priority
--   - Mapping tables: project_type_role_mapping, project_type_status_mapping
--   - Entity tables: projects, tasks, project_contacts
--   - Role-filtered views: captain_view, scribe_view, mechanic_view, envoy_view
--
-- Depends on: 01_audit.sql, 02_identity.sql
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS projects;


-- =============================================================================
-- Lookup tables
-- =============================================================================

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


-- =============================================================================
-- Mapping tables
-- Managed by Captain's Command Center UI — no hardcoded rules in app code.
-- =============================================================================

-- Which project types are visible to each crew role
CREATE TABLE projects.project_type_role_mapping (
    id             BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_type_id BIGINT     NOT NULL REFERENCES projects.project_type (id) ON DELETE CASCADE,
    crew_role_id   BIGINT      NOT NULL REFERENCES identity.crew_role (id)    ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT project_type_role_mapping_unique UNIQUE (project_type_id, crew_role_id)
);

-- Which statuses are valid for each project type
CREATE TABLE projects.project_type_status_mapping (
    id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_type_id BIGINT      NOT NULL REFERENCES projects.project_type (id)   ON DELETE CASCADE,
    status_id       BIGINT      NOT NULL REFERENCES projects.project_status (id)  ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT project_type_status_mapping_unique UNIQUE (project_type_id, status_id)
);


-- =============================================================================
-- projects.projects
-- Flat in UI — parent_id exists for future subproject support only.
-- =============================================================================

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
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
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


-- =============================================================================
-- projects.tasks
-- Tasks support sub-tasks via parent_id.
-- project_id stored on every row for query simplicity.
-- =============================================================================

CREATE TABLE projects.tasks (
    id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id   BIGINT      NOT NULL REFERENCES projects.projects (id)   ON DELETE CASCADE,
    parent_id    BIGINT      REFERENCES projects.tasks (id)                ON DELETE NO ACTION,
    description  TEXT        NOT NULL,
    notes        TEXT,
    status_id    BIGINT      NOT NULL REFERENCES projects.task_status (id),
    priority_id  BIGINT      REFERENCES projects.priority (id),
    sort_order   INT         NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_by   BIGINT      REFERENCES identity.app_user (id) ON DELETE SET NULL,
    updated_by   BIGINT      REFERENCES identity.app_user (id) ON DELETE SET NULL
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


-- =============================================================================
-- projects.project_contacts  (junction)
-- Links contacts to projects with an optional role and notes.
-- =============================================================================

CREATE TABLE projects.project_contacts (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT      NOT NULL REFERENCES projects.projects (id)  ON DELETE CASCADE,
    contact_id BIGINT      NOT NULL REFERENCES identity.contacts (id)  ON DELETE CASCADE,
    role       VARCHAR(100),
    is_primary BOOLEAN     NOT NULL DEFAULT FALSE,
    notes      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_project_contacts UNIQUE (project_id, contact_id)
);

CREATE INDEX idx_project_contacts_project ON projects.project_contacts (project_id);
CREATE INDEX idx_project_contacts_contact ON projects.project_contacts (contact_id);


-- =============================================================================
-- Role-filtered views
-- Each view joins projects to the type mapping for its role.
-- Captain sees all projects regardless of type mapping.
-- =============================================================================

CREATE VIEW projects.captain_view AS
SELECT p.*
FROM projects.projects p;

CREATE VIEW projects.scribe_view AS
SELECT p.*
FROM projects.projects p
JOIN projects.project_type_role_mapping ptrm ON ptrm.project_type_id = p.type_id
JOIN identity.crew_role cr ON cr.id = ptrm.crew_role_id
WHERE cr.name = 'scribe';

CREATE VIEW projects.mechanic_view AS
SELECT p.*
FROM projects.projects p
JOIN projects.project_type_role_mapping ptrm ON ptrm.project_type_id = p.type_id
JOIN identity.crew_role cr ON cr.id = ptrm.crew_role_id
WHERE cr.name = 'mechanic';

CREATE VIEW projects.envoy_view AS
SELECT p.*
FROM projects.projects p
JOIN projects.project_type_role_mapping ptrm ON ptrm.project_type_id = p.type_id
JOIN identity.crew_role cr ON cr.id = ptrm.crew_role_id
WHERE cr.name = 'envoy';


-- =============================================================================
-- GRANTs
-- =============================================================================

GRANT USAGE ON SCHEMA projects TO steward;

GRANT SELECT, INSERT, UPDATE ON
    projects.projects,
    projects.tasks,
    projects.project_contacts
TO steward;

GRANT SELECT ON
    projects.project_status,
    projects.project_type,
    projects.task_status,
    projects.priority,
    projects.project_type_role_mapping,
    projects.project_type_status_mapping,
    projects.captain_view,
    projects.scribe_view,
    projects.mechanic_view,
    projects.envoy_view
TO steward;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA projects TO steward;
