-- =============================================================================
-- Seed Data
-- =============================================================================
-- Run after schema.sql.
-- Assumes schema.sql has already created all tables, triggers, and views.
--
-- To reset the database completely:
--   psql -h <host> -U steward -d projects -f schema.sql
--   psql -h <host> -U steward -d projects -f seed.sql
-- =============================================================================


-- -----------------------------------------------------------------------------
-- task_status
-- Names match todo.py VALID_STATUSES exactly.
-- display markers match _STATUS_DISPLAY in todo.py exactly.
-- -----------------------------------------------------------------------------

INSERT INTO task_status (name, display, sort_order, is_terminal) VALUES
    ('open',        '[ ]', 1, FALSE),
    ('in progress', '[~]', 2, FALSE),
    ('on hold',     '[!]', 3, FALSE),
    ('complete',    '[x]', 4, TRUE);


-- -----------------------------------------------------------------------------
-- project_status
-- -----------------------------------------------------------------------------

INSERT INTO project_status (name, sort_order) VALUES
    ('active',    1),
    ('paused',    2),
    ('completed', 3),
    ('abandoned', 4);


-- -----------------------------------------------------------------------------
-- project_type
-- 'Job Application' is required by v_job_hunt_summary.
-- -----------------------------------------------------------------------------

INSERT INTO project_type (name, sort_order) VALUES
    ('coding',           1),
    ('homelab',          2),
    ('game-dev',         3),
    ('personal',         4),
    ('Job Application',  5),
    ('other',            6);


-- -----------------------------------------------------------------------------
-- tag_category
-- -----------------------------------------------------------------------------

INSERT INTO tag_category (name, sort_order) VALUES
    ('component',  1),   -- a named sub-system, e.g. doc-gen, project-crew
    ('technology', 2),   -- language, tool, or platform, e.g. python, bind9
    ('area',       3),   -- broad domain, e.g. networking, job-search
    ('skill',      4);   -- competency being developed or demonstrated


-- -----------------------------------------------------------------------------
-- location_type
-- -----------------------------------------------------------------------------

INSERT INTO location_type (name, sort_order) VALUES
    ('local', 1),
    ('url',   2),
    ('git',   3),
    ('s3',    4);


-- -----------------------------------------------------------------------------
-- file_type
-- -----------------------------------------------------------------------------

INSERT INTO file_type (name, sort_order) VALUES
    ('markdown', 1),
    ('config',   2),
    ('script',   3),
    ('log',      4),
    ('json',     5),
    ('yaml',     6),
    ('other',    7);


-- -----------------------------------------------------------------------------
-- priority
-- -----------------------------------------------------------------------------

INSERT INTO priority (name, sort_order) VALUES
    ('low',      1),
    ('normal',   2),
    ('high',     3),
    ('blocking', 4);


-- =============================================================================
-- CORE SEED DATA
-- =============================================================================


-- -----------------------------------------------------------------------------
-- tags
-- -----------------------------------------------------------------------------

INSERT INTO tags (name, category_id) VALUES
    -- components
    ('project-crew', (SELECT id FROM tag_category WHERE name = 'component')),
    ('doc-gen',      (SELECT id FROM tag_category WHERE name = 'component')),
    ('todo',         (SELECT id FROM tag_category WHERE name = 'component')),
    ('menukit',      (SELECT id FROM tag_category WHERE name = 'component')),
    ('fletcher',     (SELECT id FROM tag_category WHERE name = 'component')),
    ('dbkit',        (SELECT id FROM tag_category WHERE name = 'component')),
    -- technologies
    ('python',       (SELECT id FROM tag_category WHERE name = 'technology')),
    ('bash',         (SELECT id FROM tag_category WHERE name = 'technology')),
    ('postgres',     (SELECT id FROM tag_category WHERE name = 'technology')),
    ('ansible',      (SELECT id FROM tag_category WHERE name = 'technology')),
    ('bind9',        (SELECT id FROM tag_category WHERE name = 'technology')),
    ('dhcp',         (SELECT id FROM tag_category WHERE name = 'technology')),
    ('docker',       (SELECT id FROM tag_category WHERE name = 'technology')),
    ('pygame',       (SELECT id FROM tag_category WHERE name = 'technology')),
    -- areas
    ('networking',   (SELECT id FROM tag_category WHERE name = 'area')),
    ('job-search',   (SELECT id FROM tag_category WHERE name = 'area')),
    ('homelab',      (SELECT id FROM tag_category WHERE name = 'area')),
    ('game-dev',     (SELECT id FROM tag_category WHERE name = 'area'));


-- -----------------------------------------------------------------------------
-- projects
-- Four top-level projects, with subprojects under project-crew.
-- References use subqueries so IDs don't need to be hard-coded.
-- -----------------------------------------------------------------------------

INSERT INTO projects (name, slug, description, status_id, type_id) VALUES
    (
        'Project Crew',
        'project-crew',
        'Python CLI tool for automating creation and management of coding projects. '
        'Interactive menu interface; GUI planned as a visualizer layer on top of the CLI.',
        (SELECT id FROM project_status WHERE name = 'active'),
        (SELECT id FROM project_type   WHERE name = 'coding')
    ),
    (
        'DNS/DHCP Hardening',
        'bind9-dhcp',
        'Standardise and systematise bind9 and isc-dhcp server settings for LAN devices.',
        (SELECT id FROM project_status WHERE name = 'active'),
        (SELECT id FROM project_type   WHERE name = 'homelab')
    ),
    (
        'Job Hunt',
        'job-hunt',
        'Track job applications, contacts, interviews, and follow-ups.',
        (SELECT id FROM project_status WHERE name = 'active'),
        (SELECT id FROM project_type   WHERE name = 'personal')
    ),
    (
        'Story Gems',
        'story-gems',
        'Story-based game development project.',
        (SELECT id FROM project_status WHERE name = 'active'),
        (SELECT id FROM project_type   WHERE name = 'game-dev')
    );


-- Subprojects under Project Crew

INSERT INTO projects (name, slug, description, status_id, type_id, parent_id) VALUES
    (
        'Todo Plugin',
        'project-crew-todo',
        'Migrate todo package into project-crew as a plugin. '
        'Verify Project Crew plugin compatibility and add postgres integration.',
        (SELECT id FROM project_status WHERE name = 'active'),
        (SELECT id FROM project_type   WHERE name = 'coding'),
        (SELECT id FROM projects       WHERE slug  = 'project-crew')
    ),
    (
        'Project Tracker DB',
        'project-crew-db',
        'Postgres schema and integration for tracking projects, tasks, and files.',
        (SELECT id FROM project_status WHERE name = 'active'),
        (SELECT id FROM project_type   WHERE name = 'coding'),
        (SELECT id FROM projects       WHERE slug  = 'project-crew')
    ),
    (
        'dbkit',
        'dbkit',
        'Shared postgres utility library: DBConnection, SlugResolver, FileRegistry, '
        'CSVImporter. Lives in dev-utils alongside menukit and fletcher.',
        (SELECT id FROM project_status WHERE name = 'active'),
        (SELECT id FROM project_type   WHERE name = 'coding'),
        (SELECT id FROM projects       WHERE slug  = 'project-crew')
    );


-- -----------------------------------------------------------------------------
-- project_tags
-- -----------------------------------------------------------------------------

INSERT INTO project_tags (project_id, tag_id) VALUES
    -- project-crew
    ((SELECT id FROM projects WHERE slug = 'project-crew'),
     (SELECT id FROM tags     WHERE name = 'project-crew')),
    ((SELECT id FROM projects WHERE slug = 'project-crew'),
     (SELECT id FROM tags     WHERE name = 'python')),
    -- bind9-dhcp
    ((SELECT id FROM projects WHERE slug = 'bind9-dhcp'),
     (SELECT id FROM tags     WHERE name = 'bind9')),
    ((SELECT id FROM projects WHERE slug = 'bind9-dhcp'),
     (SELECT id FROM tags     WHERE name = 'dhcp')),
    ((SELECT id FROM projects WHERE slug = 'bind9-dhcp'),
     (SELECT id FROM tags     WHERE name = 'ansible')),
    ((SELECT id FROM projects WHERE slug = 'bind9-dhcp'),
     (SELECT id FROM tags     WHERE name = 'networking')),
    -- job-hunt
    ((SELECT id FROM projects WHERE slug = 'job-hunt'),
     (SELECT id FROM tags     WHERE name = 'job-search')),
    -- story-gems
    ((SELECT id FROM projects WHERE slug = 'story-gems'),
     (SELECT id FROM tags     WHERE name = 'pygame')),
    ((SELECT id FROM projects WHERE slug = 'story-gems'),
     (SELECT id FROM tags     WHERE name = 'python')),
    -- project-crew-todo
    ((SELECT id FROM projects WHERE slug = 'project-crew-todo'),
     (SELECT id FROM tags     WHERE name = 'todo')),
    ((SELECT id FROM projects WHERE slug = 'project-crew-todo'),
     (SELECT id FROM tags     WHERE name = 'postgres')),
    -- project-crew-db
    ((SELECT id FROM projects WHERE slug = 'project-crew-db'),
     (SELECT id FROM tags     WHERE name = 'postgres')),
    ((SELECT id FROM projects WHERE slug = 'project-crew-db'),
     (SELECT id FROM tags     WHERE name = 'project-crew')),
    -- dbkit
    ((SELECT id FROM projects WHERE slug = 'dbkit'),
     (SELECT id FROM tags     WHERE name = 'dbkit')),
    ((SELECT id FROM projects WHERE slug = 'dbkit'),
     (SELECT id FROM tags     WHERE name = 'postgres')),
    ((SELECT id FROM projects WHERE slug = 'dbkit'),
     (SELECT id FROM tags     WHERE name = 'python'));


-- -----------------------------------------------------------------------------
-- project_files
-- Source repo links and the todo markdown file for project-crew-todo.
-- -----------------------------------------------------------------------------

INSERT INTO project_files (project_id, label, file_type_id, location, location_type_id)
VALUES
    (
        (SELECT id FROM projects      WHERE slug = 'project-crew'),
        'source repo',
        (SELECT id FROM file_type     WHERE name = 'other'),
        'https://github.com/carolynboyle/projs',
        (SELECT id FROM location_type WHERE name = 'git')
    ),
    (
        (SELECT id FROM projects      WHERE slug = 'project-crew-todo'),
        'source repo',
        (SELECT id FROM file_type     WHERE name = 'other'),
        'https://github.com/carolynboyle/dev-utils',
        (SELECT id FROM location_type WHERE name = 'git')
    ),
    (
        (SELECT id FROM projects      WHERE slug = 'project-crew-todo'),
        'todo list',
        (SELECT id FROM file_type     WHERE name = 'markdown'),
        'python/todo/docs/TODO.md',
        (SELECT id FROM location_type WHERE name = 'local')
    );


-- -----------------------------------------------------------------------------
-- Sample tasks for project-crew-db (the work we're doing right now)
-- -----------------------------------------------------------------------------

INSERT INTO tasks
    (project_id, description, status_id, priority_id, sort_order)
VALUES
    (
        (SELECT id FROM projects    WHERE slug = 'project-crew-db'),
        'Finalise schema.sql and seed.sql',
        (SELECT id FROM task_status WHERE name = 'in progress'),
        (SELECT id FROM priority    WHERE name = 'high'),
        1
    ),
    (
        (SELECT id FROM projects    WHERE slug = 'project-crew-db'),
        'Create dbkit package structure in dev-utils',
        (SELECT id FROM task_status WHERE name = 'open'),
        (SELECT id FROM priority    WHERE name = 'high'),
        2
    ),
    (
        (SELECT id FROM projects    WHERE slug = 'project-crew-db'),
        'Implement DBConnection class in dbkit',
        (SELECT id FROM task_status WHERE name = 'open'),
        (SELECT id FROM priority    WHERE name = 'high'),
        3
    ),
    (
        (SELECT id FROM projects    WHERE slug = 'project-crew-db'),
        'Implement SlugResolver class in dbkit',
        (SELECT id FROM task_status WHERE name = 'open'),
        (SELECT id FROM priority    WHERE name = 'normal'),
        4
    ),
    (
        (SELECT id FROM projects    WHERE slug = 'project-crew-db'),
        'Add postgres integration to todo package',
        (SELECT id FROM task_status WHERE name = 'open'),
        (SELECT id FROM priority    WHERE name = 'high'),
        5
    ),
    (
        (SELECT id FROM projects    WHERE slug = 'project-crew-db'),
        'Add --csv export option to todo.py',
        (SELECT id FROM task_status WHERE name = 'open'),
        (SELECT id FROM priority    WHERE name = 'normal'),
        6
    );
