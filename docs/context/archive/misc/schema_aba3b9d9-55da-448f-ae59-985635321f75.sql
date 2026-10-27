-- =============================================================================
-- Project Tracker Schema
-- =============================================================================
-- Conventions:
--   - All tables use BIGINT GENERATED ALWAYS AS IDENTITY primary keys
--   - All FK columns are BIGINT to match
--   - created_at / updated_at on every mutable table
--   - updated_at maintained automatically by trigger
--   - Categorical values use lookup tables with BIGINT foreign keys
--   - slug columns are the stable human-readable handle for external references
--   - Lookup table names are singular (task_status, project_type, etc.)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Tear down in dependency order
-- Views first, then junction tables, then tables with FKs, then lookup tables
-- -----------------------------------------------------------------------------

DROP VIEW  IF EXISTS v_task_tree       CASCADE;
DROP VIEW  IF EXISTS v_tasks           CASCADE;
DROP VIEW  IF EXISTS v_project_tree    CASCADE;
DROP VIEW  IF EXISTS v_projects        CASCADE;

DROP TABLE IF EXISTS project_files     CASCADE;
DROP TABLE IF EXISTS task_tags         CASCADE;
DROP TABLE IF EXISTS project_tags      CASCADE;
DROP TABLE IF EXISTS tags              CASCADE;
DROP TABLE IF EXISTS tasks             CASCADE;
DROP TABLE IF EXISTS projects          CASCADE;

DROP TABLE IF EXISTS priority          CASCADE;
DROP TABLE IF EXISTS file_type         CASCADE;
DROP TABLE IF EXISTS location_type     CASCADE;
DROP TABLE IF EXISTS tag_category      CASCADE;
DROP TABLE IF EXISTS project_type      CASCADE;
DROP TABLE IF EXISTS project_status    CASCADE;
DROP TABLE IF EXISTS task_status       CASCADE;

DROP FUNCTION IF EXISTS set_updated_at CASCADE;


-- -----------------------------------------------------------------------------
-- Trigger function — keeps updated_at current on any UPDATE
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- LOOKUP TABLES
-- Small, stable, human-readable reference data.
-- sort_order controls display sequence in menus and reports.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- task_status
-- Matches todo.py VALID_STATUSES exactly. The name column is what the
-- application reads and writes — no translation layer needed.
-- -----------------------------------------------------------------------------

CREATE TABLE task_status (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(50)  NOT NULL UNIQUE,
    display     VARCHAR(10)  NOT NULL,        -- CLI marker: [ ] [~] [!] [x]
    sort_order  INT          NOT NULL DEFAULT 0,
    is_terminal BOOLEAN      NOT NULL DEFAULT FALSE  -- TRUE = no further updates expected
);


-- -----------------------------------------------------------------------------
-- project_status
-- -----------------------------------------------------------------------------

CREATE TABLE project_status (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,
    sort_order INT         NOT NULL DEFAULT 0
);


-- -----------------------------------------------------------------------------
-- project_type
-- -----------------------------------------------------------------------------

CREATE TABLE project_type (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,
    sort_order INT         NOT NULL DEFAULT 0
);


-- -----------------------------------------------------------------------------
-- tag_category
-- Groups tags by kind: component, technology, area, skill, etc.
-- -----------------------------------------------------------------------------

CREATE TABLE tag_category (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,
    sort_order INT         NOT NULL DEFAULT 0
);


-- -----------------------------------------------------------------------------
-- location_type
-- Classifies file/path references in project_files.
-- -----------------------------------------------------------------------------

CREATE TABLE location_type (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,   -- local, url, git, s3
    sort_order INT         NOT NULL DEFAULT 0
);


-- -----------------------------------------------------------------------------
-- file_type
-- Classifies the content kind of a project_files entry.
-- -----------------------------------------------------------------------------

CREATE TABLE file_type (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,   -- markdown, config, log, script, etc.
    sort_order INT         NOT NULL DEFAULT 0
);


-- -----------------------------------------------------------------------------
-- priority
-- Task priority levels.
-- -----------------------------------------------------------------------------

CREATE TABLE priority (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,   -- low, normal, high, blocking
    sort_order INT         NOT NULL DEFAULT 0
);


-- =============================================================================
-- CORE TABLES
-- =============================================================================


-- -----------------------------------------------------------------------------
-- projects
-- Self-referencing for unlimited subproject depth.
-- parent_id NULL = top-level project.
-- -----------------------------------------------------------------------------

CREATE TABLE projects (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_id   BIGINT       REFERENCES projects(id) ON DELETE SET NULL,
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    status_id   BIGINT       NOT NULL REFERENCES project_status(id),
    type_id     BIGINT       REFERENCES project_type(id),
    target_date DATE,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_projects_parent ON projects(parent_id);
CREATE INDEX idx_projects_status ON projects(status_id);
CREATE INDEX idx_projects_type   ON projects(type_id);


-- -----------------------------------------------------------------------------
-- tasks
-- Self-referencing for unlimited subtask depth.
-- parent_id NULL = top-level task (must belong to a project directly).
-- Subtasks inherit project_id from parent — application enforces this on
-- insert; project_id is stored on every row for query simplicity.
-- links is comma-separated text, matching todo.py storage format.
-- source_file records which markdown/json file the task originated from.
--
-- Deletion rules:
--   parent_id ON DELETE NO ACTION — application must detect children,
--   present double confirmation, then delete children before parent.
--   project_id ON DELETE CASCADE — if a project is deleted, all its
--   tasks (and their subtasks, via cascade) go with it.
-- -----------------------------------------------------------------------------

CREATE TABLE tasks (
    id           BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id   BIGINT       NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_id    BIGINT       REFERENCES tasks(id) ON DELETE NO ACTION,
    description  TEXT         NOT NULL,
    status_id    BIGINT       NOT NULL REFERENCES task_status(id),
    priority_id  BIGINT       NOT NULL REFERENCES priority(id),
    links        TEXT         NOT NULL DEFAULT '',
    source_file  VARCHAR(255) NOT NULL DEFAULT '',
    sort_order   INT          NOT NULL DEFAULT 0,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_tasks_project  ON tasks(project_id);
CREATE INDEX idx_tasks_parent   ON tasks(parent_id);
CREATE INDEX idx_tasks_status   ON tasks(status_id);
CREATE INDEX idx_tasks_priority ON tasks(priority_id);


-- -----------------------------------------------------------------------------
-- tags
-- -----------------------------------------------------------------------------

CREATE TABLE tags (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    category_id BIGINT       REFERENCES tag_category(id)
);

CREATE INDEX idx_tags_category ON tags(category_id);


-- -----------------------------------------------------------------------------
-- project_tags  (many-to-many)
-- -----------------------------------------------------------------------------

CREATE TABLE project_tags (
    id         BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tag_id     BIGINT NOT NULL REFERENCES tags(id)     ON DELETE CASCADE,
    CONSTRAINT uq_project_tags UNIQUE (project_id, tag_id)
);


-- -----------------------------------------------------------------------------
-- task_tags  (many-to-many)
-- -----------------------------------------------------------------------------

CREATE TABLE task_tags (
    id      BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    tag_id  BIGINT NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
    CONSTRAINT uq_task_tags UNIQUE (task_id, tag_id)
);


-- -----------------------------------------------------------------------------
-- project_files
-- Attaches file paths or URLs to a project or task.
-- Either project_id or task_id must be set (enforced by CHECK).
-- -----------------------------------------------------------------------------

CREATE TABLE project_files (
    id               BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id       BIGINT       REFERENCES projects(id) ON DELETE CASCADE,
    task_id          BIGINT       REFERENCES tasks(id)    ON DELETE CASCADE,
    label            VARCHAR(255) NOT NULL,
    file_type_id     BIGINT       NOT NULL REFERENCES file_type(id),
    location         TEXT         NOT NULL,
    location_type_id BIGINT       NOT NULL REFERENCES location_type(id),
    notes            TEXT,
    created_at       TIMESTAMP    NOT NULL DEFAULT NOW(),
    CHECK (project_id IS NOT NULL OR task_id IS NOT NULL)
);

CREATE INDEX idx_project_files_project ON project_files(project_id);
CREATE INDEX idx_project_files_task    ON project_files(task_id);


-- =============================================================================
-- VIEWS
-- =============================================================================


-- -----------------------------------------------------------------------------
-- v_tasks
-- Joins lookup names back in so application queries don't need to.
-- Includes parent_id and parent description for subtask context.
-- -----------------------------------------------------------------------------

CREATE VIEW v_tasks AS
SELECT
    t.id,
    t.project_id,
    p.name          AS project_name,
    p.slug          AS project_slug,
    t.parent_id,
    pt.description  AS parent_description,
    t.description,
    ts.name         AS status,
    ts.display      AS status_display,
    ts.is_terminal,
    pr.name         AS priority,
    t.links,
    t.source_file,
    t.sort_order,
    t.created_at,
    t.updated_at,
    t.completed_at
FROM      tasks        t
JOIN      projects     p  ON p.id  = t.project_id
JOIN      task_status  ts ON ts.id = t.status_id
JOIN      priority     pr ON pr.id = t.priority_id
LEFT JOIN tasks        pt ON pt.id = t.parent_id;


-- -----------------------------------------------------------------------------
-- v_projects
-- Flat view with all lookup names resolved and task counts included.
-- Task counts reflect direct project tasks only (not subtasks).
-- -----------------------------------------------------------------------------

CREATE VIEW v_projects AS
SELECT
    p.id,
    p.parent_id,
    parent.name     AS parent_name,
    parent.slug     AS parent_slug,
    p.name,
    p.slug,
    p.description,
    ps.name         AS status,
    pt.name         AS project_type,
    p.target_date,
    p.created_at,
    p.updated_at,
    COUNT(t.id)                                          AS total_tasks,
    COUNT(t.id) FILTER (WHERE ts.is_terminal = TRUE)     AS completed_tasks,
    COUNT(t.id) FILTER (WHERE ts.is_terminal = FALSE)    AS open_tasks
FROM           projects       p
JOIN           project_status ps     ON ps.id     = p.status_id
LEFT JOIN      project_type   pt     ON pt.id     = p.type_id
LEFT JOIN      projects       parent ON parent.id = p.parent_id
LEFT JOIN      tasks          t      ON t.project_id = p.id
LEFT JOIN      task_status    ts     ON ts.id     = t.status_id
GROUP BY p.id, parent.name, parent.slug, ps.name, pt.name;


-- -----------------------------------------------------------------------------
-- v_project_tree
-- Recursive view — expands full ancestry for any project.
-- depth 0 = top-level project.
-- -----------------------------------------------------------------------------

CREATE VIEW v_project_tree AS
WITH RECURSIVE tree AS (
    SELECT
        id,
        parent_id,
        name,
        slug,
        0               AS depth,
        ARRAY[slug]::VARCHAR[] AS path
    FROM projects
    WHERE parent_id IS NULL

    UNION ALL

    SELECT
        p.id,
        p.parent_id,
        p.name,
        p.slug,
        t.depth + 1,
        t.path || p.slug
    FROM  projects p
    JOIN  tree     t ON t.id = p.parent_id
)
SELECT * FROM tree;


-- -----------------------------------------------------------------------------
-- v_task_tree
-- Recursive view — expands full subtask ancestry for any task.
-- depth 0 = top-level task (parent_id IS NULL).
-- path shows the chain of task IDs from root to current node.
-- project_id and project_slug carried through for filtering by project.
-- -----------------------------------------------------------------------------

CREATE VIEW v_task_tree AS
WITH RECURSIVE tree AS (
    SELECT
        t.id,
        t.parent_id,
        t.project_id,
        p.slug          AS project_slug,
        t.description,
        ts.name         AS status,
        ts.is_terminal,
        pr.name         AS priority,
        t.sort_order,
        0               AS depth,
        ARRAY[t.id]     AS path
    FROM      tasks       t
    JOIN      projects    p  ON p.id  = t.project_id
    JOIN      task_status ts ON ts.id = t.status_id
    JOIN      priority    pr ON pr.id = t.priority_id
    WHERE t.parent_id IS NULL

    UNION ALL

    SELECT
        t.id,
        t.parent_id,
        t.project_id,
        p.slug          AS project_slug,
        t.description,
        ts.name         AS status,
        ts.is_terminal,
        pr.name         AS priority,
        t.sort_order,
        tree.depth + 1,
        tree.path || t.id
    FROM      tasks       t
    JOIN      projects    p  ON p.id  = t.project_id
    JOIN      task_status ts ON ts.id = t.status_id
    JOIN      priority    pr ON pr.id = t.priority_id
    JOIN      tree            ON tree.id = t.parent_id
)
SELECT * FROM tree;