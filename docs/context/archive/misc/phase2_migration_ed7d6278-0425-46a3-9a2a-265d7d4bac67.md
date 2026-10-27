# Curator v2 Phase 2.1 — Data Migration SQL

**Date**: 2026-06-24  
**Source**: `public_projects.ods` (exported from old `projects` database)  
**Target**: `wcyj` database on steward (100.64.0.7)  
**Run via**: pgAdmin query tool connected to wcyj

---

## What This Does

1. Adds missing project types (`coding`, `game-dev`, `personal`)
2. Adds writing-specific project statuses (`published`, `ready to write`, `in progress`)
3. Creates `project_type_role_mapping` table
4. Creates `project_status_role_mapping` table
5. Seeds both mapping tables with sensible defaults (Captain adjusts via UI)
6. Inserts 61 projects with corrected lookup IDs
7. Resets projects ID sequence
8. Inserts 96 tasks with corrected lookup IDs
9. Resets tasks ID sequence

---

## Lookup ID Mappings

### project_type (old → new)
| Old name | Old ID | New ID | New name |
|----------|--------|--------|----------|
| coding | 1 | 4 | coding (added) |
| homelab | 2 | 1 | homelab |
| game-dev | 3 | 5 | game-dev (added) |
| personal | 4 | 6 | personal (added) |
| writing | 7 | 3 | writing |
| refurb | 8 | 2 | refurb |

### project_status (old → new)
| Old name | Old ID | New ID | New name |
|----------|--------|--------|----------|
| active | 1 | 1 | active |
| paused | 2 | 4 | on hold |
| completed | 3 | 3 | complete |
| abandoned | 4 | 2 | archived |
| Published | 5 | 6 | published (added) |
| Ready to Write | 6 | 7 | ready to write (added) |
| In Progress | 7 | 8 | in progress (added) |
| Queued | 8 | 5 | queued |

### task_status (old → new)
| Old name | Old ID | New ID | New name |
|----------|--------|--------|----------|
| open | 1 | 1 | backlog |
| in progress | 2 | 5 | in progress |
| on hold | 3 | 2 | blocked |
| complete | 4 | 4 | complete |

### priority (old → new)
| Old name | Old ID | New ID | New name |
|----------|--------|--------|----------|
| low | 1 | 2 | low |
| normal | 2 | 3 | normal |
| high | 3 | 1 | high |
| blocking | 4 | 4 | urgent |

---

## Default Role Mappings (seed data — Captain adjusts via UI)

### project_type_role_mapping
| Role | Types |
|------|-------|
| Captain | all |
| Scribe | writing |
| Mechanic | homelab, coding, game-dev, personal |
| Envoy | refurb |

### project_status_role_mapping
| Role | Statuses |
|------|----------|
| Captain | all |
| Scribe | active, on hold, queued, ready to write, in progress, published, complete |
| Mechanic | active, archived, complete, on hold, queued |
| Envoy | active, archived, complete, on hold, queued |

---

## Notes

- 2 projects have `NULL type_id` — Captain assigns via UI later
- `links`, `source_file`, `completed_at` task columns dropped (not in wcyj schema)
- `parent_id` preserved from old db on projects
- Both mapping tables assume new type/status IDs are assigned sequentially — verify after Steps 1 and 2 before proceeding

---

## Migration SQL

```sql
-- =============================================================
-- Curator v2 Phase 2.1 Data Migration
-- Source: projects database (old) -> wcyj (new)
-- Generated from: public_projects.ods
-- Date: 2026-06-24
-- Run in pgAdmin query tool connected to wcyj database
-- =============================================================

-- -------------------------------------------------------------
-- Step 1: Add missing project types
-- After insert: 4=coding, 5=game-dev, 6=personal
-- -------------------------------------------------------------
INSERT INTO projects.project_type (name) VALUES
    ('coding'),
    ('game-dev'),
    ('personal')
ON CONFLICT DO NOTHING;

-- Verify: SELECT id, name FROM projects.project_type ORDER BY id;

-- -------------------------------------------------------------
-- Step 2: Add writing-specific project statuses
-- After insert: 6=published, 7=ready to write, 8=in progress
-- -------------------------------------------------------------
INSERT INTO projects.project_status (name) VALUES
    ('published'),
    ('ready to write'),
    ('in progress')
ON CONFLICT DO NOTHING;

-- Verify: SELECT id, name FROM projects.project_status ORDER BY id;

-- -------------------------------------------------------------
-- Step 3: Create project_type_role_mapping table
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects.project_type_role_mapping (
    id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_type_id BIGINT      NOT NULL REFERENCES projects.project_type (id) ON DELETE CASCADE,
    crew_role       VARCHAR(50) NOT NULL CHECK (crew_role IN ('captain', 'scribe', 'mechanic', 'envoy')),
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_by      BIGINT,
    UNIQUE(project_type_id, crew_role)
);

CREATE INDEX IF NOT EXISTS idx_type_mapping_type ON projects.project_type_role_mapping (project_type_id);
CREATE INDEX IF NOT EXISTS idx_type_mapping_role ON projects.project_type_role_mapping (crew_role);

COMMENT ON TABLE projects.project_type_role_mapping IS 'Maps project types to crew roles for filtering. Captain mapped to all types by default.';

-- -------------------------------------------------------------
-- Step 4: Create project_status_role_mapping table
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects.project_status_role_mapping (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status_id   BIGINT      NOT NULL REFERENCES projects.project_status (id) ON DELETE CASCADE,
    crew_role   VARCHAR(50) NOT NULL CHECK (crew_role IN ('captain', 'scribe', 'mechanic', 'envoy')),
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_by  BIGINT,
    UNIQUE(status_id, crew_role)
);

CREATE INDEX IF NOT EXISTS idx_status_mapping_status ON projects.project_status_role_mapping (status_id);
CREATE INDEX IF NOT EXISTS idx_status_mapping_role   ON projects.project_status_role_mapping (crew_role);

COMMENT ON TABLE projects.project_status_role_mapping IS 'Maps project statuses to crew roles for filtering. Captain mapped to all statuses by default.';

-- -------------------------------------------------------------
-- Step 5: Seed project_type_role_mapping
-- Captain: all types
-- Scribe: writing only
-- Mechanic: homelab, coding, game-dev, personal
-- Envoy: refurb (customer-facing)
-- Adjust via Captain UI after migration
-- -------------------------------------------------------------
INSERT INTO projects.project_type_role_mapping (project_type_id, crew_role)
VALUES
    -- Captain sees all types
    (1, 'captain'), (2, 'captain'), (3, 'captain'),
    (4, 'captain'), (5, 'captain'), (6, 'captain'),
    -- Scribe: writing
    (3, 'scribe'),
    -- Mechanic: homelab, coding, game-dev, personal
    (1, 'mechanic'), (4, 'mechanic'), (5, 'mechanic'), (6, 'mechanic'),
    -- Envoy: refurb
    (2, 'envoy')
ON CONFLICT DO NOTHING;

-- -------------------------------------------------------------
-- Step 6: Seed project_status_role_mapping
-- Captain: all statuses
-- Scribe: active, on hold, queued, ready to write, in progress, published, complete, archived
-- Mechanic: active, on hold, queued, complete, archived
-- Envoy: active, on hold, queued, complete, archived
-- Adjust via Captain UI after migration
-- -------------------------------------------------------------
INSERT INTO projects.project_status_role_mapping (status_id, crew_role)
VALUES
    -- Captain sees all statuses
    (1, 'captain'), (2, 'captain'), (3, 'captain'), (4, 'captain'),
    (5, 'captain'), (6, 'captain'), (7, 'captain'), (8, 'captain'),
    -- Scribe: all except archived
    (1, 'scribe'), (3, 'scribe'), (4, 'scribe'),
    (5, 'scribe'), (6, 'scribe'), (7, 'scribe'), (8, 'scribe'),
    -- Mechanic: operational statuses only
    (1, 'mechanic'), (2, 'mechanic'), (3, 'mechanic'), (4, 'mechanic'), (5, 'mechanic'),
    -- Envoy: operational statuses only
    (1, 'envoy'), (2, 'envoy'), (3, 'envoy'), (4, 'envoy'), (5, 'envoy')
ON CONFLICT DO NOTHING;

-- -------------------------------------------------------------
-- Step 7: Insert projects (61 records)
-- NULL type_id left as NULL — assign via Captain UI later
-- -------------------------------------------------------------
INSERT INTO projects.projects
    (id, name, slug, description, notes, status_id, type_id, target_date, created_at, updated_at)
VALUES
    (1, 'Project Crew', 'project-crew', 'Python CLI tool for automating creation and management of coding projects. Interactive menu interface; GUI planned as a visualizer layer on top of the CLI.', NULL, 1, 4, NULL, '2026-04-14 05:48:24.298313', '2026-04-14 05:48:24.298313'),
    (3, 'Job Hunt', 'job-hunt', 'Track job applications, contacts, interviews, and follow-ups.', NULL, 1, 6, NULL, '2026-04-14 05:48:24.298313', '2026-04-14 05:48:24.298313'),
    (4, 'Story Gems', 'story-gems', 'Story-based game development project.', NULL, 1, 5, NULL, '2026-04-14 05:48:24.298313', '2026-04-14 05:48:24.298313'),
    (5, 'Todo Plugin', 'project-crew-todo', 'Migrate todo package into project-crew as a plugin. Verify Project Crew plugin compatibility and add postgres integration.', NULL, 1, 4, NULL, '2026-04-14 05:48:24.332879', '2026-04-14 05:48:24.332879'),
    (7, 'dbkit', 'dbkit', 'Shared postgres utility library: DBConnection, SlugResolver, FileRegistry, CSVImporter. Lives in dev-utils alongside menukit and fletcher.', NULL, 1, 4, NULL, '2026-04-14 05:48:24.332879', '2026-04-14 05:48:24.332879'),
    (9, 'WCYJ Refurbs & WCYJ Store', 'wcyj-refurbs-wcyj-store', 'The project is to get a small business going, to refurbish Windows 10 eol machines into linux, as either a home media center or using a Zorin  OS/ MX linux/other OS.A mozilla solo website was created for the business. refurbs.whycantyoujust.tech will be pointed at it. Images for the website are uploaded to this project. I''ve also created a solo website for store.whycantyoujust.tech ', NULL, 4, 4, NULL, '2026-04-14 23:38:06.888039', '2026-04-14 23:38:06.888039'),
    (8, 'The Curator', 'the-curator', 'Web UI for projects database CRUD operations."Built with FastAPI and Jinja2, backed by PostgreSQL on steward. Views are driven by YAML configuration via viewkit, with dbkit handling async database connections."', 'These notes are a pain', 1, 4, NULL, '2026-04-14 06:41:44.522109', '2026-04-22 01:04:27.455285'),
    (12, 'dev-utils', 'dev-utils', 'repo for useful small devlopment tools that can serve as standalone tools as well as plugins to other packages.', NULL, 1, 4, NULL, '2026-04-16 20:29:44.828124', '2026-04-16 20:29:44.828124'),
    (13, 'code patterns', 'code-patterns', 'way to identify coding patterns in a personal library to create structures like the dev-utils *kits', NULL, 4, 4, NULL, '2026-04-16 21:18:27.257935', '2026-04-16 21:18:27.257935'),
    (15, 'setupkit', 'setupkit', 'refactor: add date checking for manifest and if different from runtime  prompt to generate a fresh one (y/n)', NULL, 4, 4, NULL, '2026-04-17 04:04:52.475366', '2026-04-17 04:04:52.475366'),
    (14, 'Fletcher', 'fletcher', 'dev-utils utility for generating a manifest of raw urls for github repos.', NULL, 1, 4, NULL, '2026-04-17 03:43:24.724252', '2026-04-17 04:49:05.45188'),
    (2, 'DNS/DHCP Hardening', 'bind9-dhcp', 'Standardise and systematise bind9 and isc-dhcp server settings for LAN devices.', NULL, 4, 1, NULL, '2026-04-14 05:48:24.298313', '2026-04-17 17:43:45.043833'),
    (19, 'PostgreSQL/ansible lan automation', 'postgresqlansible-lan-automation', NULL, NULL, 4, 1, NULL, '2026-04-17 17:46:44.779715', '2026-04-17 17:46:44.779715'),
    (17, 'Taming wild kittens', 'taming-wild-kittens', 'Childhood skills, Mama Cat''s pedagogy, meeting learners where they are', 'Uploaded to project 2/26/26', 6, 3, NULL, '2026-04-17 17:23:01.028048', '2026-06-21 04:41:20.229883'),
    (24, 'Decorations That Destroy', 'decorations-that-destroy', 'Firefox crash → the Vorlt → systemic fragility in complex systems; Boyle''s Law of trivial executables', 'Strong outline developed; hook, anatomy of fragility, Vorlt expansion', 7, 3, NULL, '2026-04-18 15:45:58.02814', '2026-06-21 04:41:20.229883'),
    (18, 'Homelab as SMB model', 'homelab-as-smb-model', 'infrastructure', NULL, 1, 3, NULL, '2026-04-17 17:41:28.887472', '2026-06-21 04:41:20.229883'),
    (52, 'roles', 'roles', 'create auth-level roles for users', NULL, 5, NULL, NULL, '2026-04-18 18:42:19.053377', '2026-04-18 18:42:19.053377'),
    (34, 'The Johnstown Flood Keeps Happening', 'the-johnstown-flood-keeps-happening', 'AI company liability parallels; wealthy owners, dismissed warnings, no legal consequences; Carson Chronicles as narrative hook', 'Plot hole in the novel (civil engineer missed foundational civil engineering case study) killed interest in the series', 8, 3, NULL, '2026-04-18 15:46:58.217445', '2026-06-21 04:41:20.229883'),
    (58, 'website security', 'website-security-1', 'Implement tools to harden security for self-hosted websites', 'cloudflare, fail2ban on DO droplet, hardened containers for websites', 4, 1, NULL, '2026-04-22 01:25:18.74164', '2026-04-22 01:25:18.74164'),
    (60, 'viewkit', 'viewkit', 'tools for viewing databases and interfacing with websites', NULL, 1, 4, NULL, '2026-04-24 16:17:51.816913', '2026-04-24 16:17:51.816913'),
    (61, 'On the Fly Query Tool', 'on-the-fly-query-tool', 'dev-utils/viewkit tool for connecting to databases on the fly', NULL, 1, 4, NULL, '2026-04-24 16:19:28.282079', '2026-04-24 16:19:28.282079'),
    (63, 'testing scratchpad', 'testing-scratchpad', 'duh, obvs', NULL, 1, 4, NULL, '2026-04-25 19:14:58.062646', '2026-04-25 19:14:58.062646'),
    (64, 'create testing containers', 'create-testing-containers', 'create testing containers', NULL, 1, 4, NULL, '2026-04-27 13:35:47.953357', '2026-04-27 13:35:47.953357'),
    (65, 'sounding', 'sounding-1', 'create debian 12 lxc for testing code', NULL, 1, NULL, NULL, '2026-04-27 13:37:15.058857', '2026-04-27 13:37:15.058857'),
    (66, 'Sr Barbara''s Class', 'sr-barbaras-class', 'Sentence diagramming web game', NULL, 1, 4, NULL, '2026-04-27 23:18:07.796706', '2026-04-27 23:18:07.796706'),
    (67, 'Postgres Database setup', 'postgres-database-setup', 'Postgres database project for web game "Sr. Barbara''s Class', NULL, 1, 4, NULL, '2026-04-27 23:20:00.385572', '2026-04-27 23:20:00.385572'),
    (68, 'Slingcode  Conversion', 'slingcode-conversion', 'convert the flask app to a self-contained web game using slingcode', NULL, 1, 4, NULL, '2026-04-27 23:21:04.402163', '2026-04-27 23:21:04.402163'),
    (69, '"Mechanic" database schema', 'mechanic-database-schema', 'Create a postgres schema for managing infrastructure with ansible automation', NULL, 1, 1, NULL, '2026-05-06 19:03:23.354042', '2026-05-06 19:03:23.354042'),
    (73, 'create a config tracker system', 'create-a-config-tracker-system', 'have config settings saved in a sqlite db that holds all related dev-utils config information to steamline infrastructure changes', NULL, 4, 4, NULL, '2026-05-07 19:22:04.525469', '2026-05-07 19:22:04.525469'),
    (74, 'website for refurb.whycantyoujust.tech', 'website-for-refurbwhycantyoujusttech', NULL, NULL, 8, 4, NULL, '2026-05-07 19:24:54.716463', '2026-05-07 19:24:54.716463'),
    (25, 'If Hemingway Had Been Happy With His Dingus...', 'if-hemingway-had-been-happy-with-his-dingus', 'Projection & reaction formation: Hemingway → Pizzagate → Epstein; Anna Freud''s 1936 work', 'Three-part structure developed; personal hook (7th grade Hills Like White Elephants), current events, academic foundation', 7, 3, NULL, '2026-04-18 15:45:58.02814', '2026-06-21 04:41:20.229883'),
    (26, 'The AI Personality Taxonomy (Or: Why I Pay $20/Month)', 'the-ai-personality-taxonomy', 'ChatGPT''s ''Aha!'', Gemini''s ODD energy, Claude''s economy of language; unsolicited rewriting as insult', 'Voice/craft argument + presumption critique; the pen-grabbing metaphor', 7, 3, NULL, '2026-04-18 15:45:58.02814', '2026-06-21 04:41:20.229883'),
    (27, 'May You Live in Interesting Times', 'may-you-live-in-interesting-times', 'Iran-Contra adjacency, Danny Casolaro, weapons on tables, the curse disguised as a blessing', 'Architecture: opens with curse, closes with survival-as-joke; ''glad no one decided I needed to be killed''', 7, 3, NULL, '2026-04-18 15:45:58.02814', '2026-06-21 04:41:20.229883'),
    (28, 'The Mindfulness Industrial Complex', 'the-mindfulness-industrial-complex', '32% adverse effects, 1500-yr documented history of harm, $2.2B industry stripping contraindications from commercialized meditation', 'Sources: Willoughby Britton (Brown U), Cheetah House; smartphone apps as unregulated psych interventions', 7, 3, NULL, '2026-04-18 15:45:58.02814', '2026-06-21 04:41:20.229883'),
    (29, 'The Rapey Priest Who Primed His Constituents...', 'the-rapey-priest-who-primed-his-constituents', 'Frank Pavone, dismantling the seamless garment, priming for moral inconsistency → Trump', 'Connects anti-death-penalty Catholic organizing to larger authoritarian priming thesis', 7, 3, NULL, '2026-04-18 15:45:58.02814', '2026-06-21 04:41:20.229883'),
    (30, 'Hallucination Is Itself a Lie', 'hallucination-is-itself-a-lie', 'Industry euphemism as rhetorical cover; business model may structurally depend on misinformation driving token consumption', 'Openers: ''People who lie to me make my back teeth grind'' / ''People pay for this''', 7, 3, NULL, '2026-04-18 15:45:58.02814', '2026-06-21 04:41:20.229883'),
    (31, 'Kevin Cooper & the Death Penalty Machine', 'kevin-cooper-death-penalty-machine', 'Evidence tampering, wrongful conviction, the activist behind the scenes; possible update if Anne can be located', 'Need to search Gmail for Anne''s contact; Telegram Ken account now appears to belong to a teenager', 8, 3, NULL, '2026-04-18 15:46:58.217445', '2026-06-21 04:41:20.229883'),
    (32, 'Hubcap Willie and the Romance of Dropping Out', 'hubcap-willie-romance-dropping-out', 'William Angus McDavid, 1962 Life magazine, American mythology of ''lighting out for the territory'' vs. the Manson inflection point', 'Series anchor for book project; connects to siblings'' hitchhiking stories, desert swimming hole Manson encounter', 8, 3, NULL, '2026-04-18 15:46:58.217445', '2026-06-21 04:41:20.229883'),
    (33, 'Synchronicity for Skeptics', 'synchronicity-for-skeptics', 'Jung without the dense prose; Fromm''s malignant narcissism as bridge; Accidental Mystic manifesto piece', 'Fromm needed clinical vocab to say ''evil''; same project as Jung. Fr. Steve + the man without a soul as case studies', 8, 3, NULL, '2026-04-18 15:46:58.217445', '2026-06-21 04:41:20.229883'),
    (16, 'Substack', 'substack', 'article ideas for accidentalmystic substack', NULL, 8, 3, NULL, '2026-04-17 17:21:36.906668', '2026-06-21 04:41:20.229883'),
    (35, 'Back to the Grind', 'back-to-the-grind', 'Third place theory (Oldenburg, 1989); Darren Conkerite; Arianna Huffington / feudalism; algorithm conversation; civic infrastructure that doesn''t announce itself', 'Reach out to Darren Conkerite before writing; confirm Huffington visit details; belongs in Accidental Mystic', 8, 3, NULL, '2026-04-18 15:46:58.217445', '2026-06-21 04:41:20.229883'),
    (36, 'Industrial Fraud Anatomy', 'industrial-fraud-anatomy', 'Myanmar/Mekong Delta pig-butchering scam; AT&T breach pipeline; LLM+human hybrid handler; ''Happy Easter'' as localization failure = evidence of industrialized crime', 'Complete anatomy documented in chat; trafficking embedded in infrastructure; ''what the supply chain of organized crime looks like when you catch it mid-operation''', 8, 3, NULL, '2026-04-18 15:46:58.217445', '2026-06-21 04:41:20.229883'),
    (37, 'Words Create Reality: The Meme That Ate Itself', 'words-create-reality-meme-ate-itself', 'Dawkins'' original meme concept → degraded meaning; semantic evolution as power structure', 'Also: ''Pharmakon'' framing — words that simultaneously name and do the thing', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (70, 'Hetzner Server', 'hetzner-server', '4GB alma linux cloud server for headscale coordination, postgres database replication, and website hosting', NULL, 1, 3, NULL, '2026-05-06 19:58:01.729428', '2026-06-21 04:41:20.229883'),
    (71, 'Setup of Headscale Coordination server', 'setup-of-headscale-coordination-server', 'what the name says', NULL, 1, 3, NULL, '2026-05-06 20:00:21.211203', '2026-06-21 04:41:20.229883'),
    (38, 'Local Paper, Local Power', 'local-paper-local-power', 'Press-Enterprise, Richard de Atley, how building relationships beats fighting editorial bias; DA excluded from frame = lead that writes itself', 'Words create reality in practical media strategy; Mama Cat''s positioning principle', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (39, 'Terry Pratchett Saw This Coming', 'terry-pratchett-saw-this-coming', 'Ankh-Morpork as prescient kakistocracy; the difference between satirizing dysfunction and predicting it', 'Connects to newkakistocracy thesis; Pratchett as accidental prophet', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (40, 'AI Safety Director, Meet Your AI', 'ai-safety-director-meet-your-ai', 'Summer Yue''s OpenClaw deletes her emails while ignoring stop commands; pharmakon paradox; read→suggest→confirm→act vs. full autonomy', 'Perfect parable; the impressive demo has it deleting; ''really good suggestion engine'' vs. funding pitch', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (41, 'COBOL, the California Courts, and the Spaghetti Nobody Reads', 'cobol-california-courts-spaghetti-nobody-reads', 'IBM stock wipeout, VentureBeat cold water; 60-year baked-in legal logic; what actually happens to defendants when the code can''t represent the situation', 'IBM 13% drop on Anthropic COBOL announcement; the horror isn''t the language, it''s the undocumented business logic', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (42, 'The Ransomware Taxonomy of Institutional Stupidity', 'ransomware-taxonomy-institutional-stupidity', 'Systematic look at conditions enabling high-profile breaches: unpatched known vulns, no MFA, perverse targeting of can''t-afford-to-lose sectors', 'SonicWall/Marquis lawsuit; it''s institutional stupidity, not individual — that''s the more interesting beast', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (43, 'AI Datacenters Are an Environmental Disaster', 'ai-datacenters-environmental-disaster', 'Crystal storage as potential mitigation; honest accounting of what training and inference actually cost the planet', 'BBC Future article on everlasting memory crystals in queue; pair with datacenter emissions data', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (44, 'Paulo Coelho vs. Hemingway: Same Wound, Different Scar', 'paulo-coelho-vs-hemingway-same-wound-different-scar', 'Similar trauma, radically different responses; what determines whether damage becomes projection or transcendence', 'Companion piece to Hemingway article', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (45, 'Jen Mercieca at the Minefield''s Edge', 'jen-mercieca-at-the-minefields-edge', 'Teaching rhetoric at Texas A&M after they ban Plato; the cost of ''people are not pleased''; Boyle''s Law at the institutional selection layer', 'Check if Jen still active on Twitter/Bsky; ''professionally heroic'' understatement from someone doing the math every day', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (46, 'The Physicist Who Found Heaven at the Universe''s Edge', 'the-physicist-who-found-heaven-at-the-universes-edge', 'Categorical error of assigning coordinates to transcendent concepts; the Flatlander mapping the third dimension', 'Popular Mechanics headline; ''safe for angry atheists'' territory; good early Accidental Mystic piece', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (47, 'The Joan Shakespeare Problem', 'the-joan-shakespeare-problem', 'ChatGPT couldn''t render ''technically competent AND creative''; AI anthropomorphization and the gaps between human and AI understanding; the uncertainty-as-decoration trap', 'Sophisticated users trust AI MORE when they hear appropriate hedging — not realizing it''s decorative, not functional', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (48, 'KTLA and the Kakistocracy of Competence', 'ktla-and-the-kakistocracy-of-competence', 'Emmy-winning journalists shown the door; merit decoupled from survival; the audition process filters for a particular kind of person', 'Kriski/Parker/Walker; pair with Congressional clown thesis — not anomalous, features not bugs', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (49, '... and the Mule You Rode In On', 'and-the-mule-you-rode-in-on', 'Claude usage limits, re-subscribing, UI too dumb to know you just paid; Gemini quote: ''selling intelligence, interface can''t recognize your payment''', 'Anger-ready. Wayne-quality title. Connect to Danish MitID specimen and broader design-for-someone-else''s-wallet theme', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (50, 'Anthropic''s Unusual Marketing Campaign', 'anthropics-unusual-marketing-campaign', 'Fear narrative + product-as-solution; Mythos data leak as probable intentional; async errors as atmosphere; ''we have unleashed something'' as emergent institutional mythology', 'Economist ad irony; Sandwich Incident; Sam Bowman''s sandwich email; the incentive structure runs the play without conscious direction', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (51, 'This Article Is Dumb Clickbait So Why Did I Read It?', 'this-article-is-dumb-clickbait-so-why-did-i-read-it', 'BGR ''no one needs USB drives'' → Boyle''s Law of cloud expansion; Cloudflare as single point of failure; the psychology of hate-reading', 'Hook: ''Just use the cloud'' said the guy oblivious to infrastructure fragility; pairs with Johnstown Flood piece', 5, 3, NULL, '2026-04-18 15:51:31.07339', '2026-06-21 04:41:20.229883'),
    (72, 'Headscale Coordination server on Hetzner', 'headscale-coordination-server-on-hetzner', NULL, NULL, 1, 3, NULL, '2026-05-06 20:19:02.988818', '2026-06-21 04:41:20.229883'),
    (76, 'WCYJ Refurb Customer Records', 'wcyj-refurb-customer-records', 'Project tracking Windows 10 eol refurb customers ', NULL, 1, 2, NULL, '2026-06-21 18:18:59.880519', '2026-06-21 18:18:59.880519')
ON CONFLICT (slug) DO NOTHING;

-- Verify: SELECT COUNT(*) FROM projects.projects; -- expect 61

-- -------------------------------------------------------------
-- Step 8: Reset projects ID sequence
-- -------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('projects.projects', 'id'),
    (SELECT MAX(id) FROM projects.projects));

-- -------------------------------------------------------------
-- Step 9: Insert tasks (96 records)
-- links/source_file/completed_at dropped (not in wcyj schema)
-- -------------------------------------------------------------
INSERT INTO projects.tasks
    (id, project_id, description, notes, status_id, priority_id, sort_order, created_at, updated_at)
VALUES
    (8, 8, 'Add contacts management', NULL, 5, 3, 0, '2026-04-14 06:42:43.399942', '2026-04-14 06:42:43.399942'),
    (10, 8, 'Add sticky navbar', NULL, 1, 2, 0, '2026-04-14 06:44:26.305409', '2026-04-14 06:44:26.305409'),
    (18, 8, 'Contacts feature — repository, routes, templates.', NULL, 1, 3, 7, '2026-04-14 20:26:56.784934', '2026-04-14 20:26:56.784934'),
    (19, 8, 'Superuser SQL box — authenticated route, raw SQL input, result table for SELECT, confirm step for writes, session query history.', NULL, 1, 3, 8, '2026-04-14 20:26:56.784934', '2026-04-14 20:26:56.784934'),
    (20, 8, 'Basic auth — session cookies, login route, users table linked to contacts, two roles: standard and superuser.', NULL, 1, 3, 9, '2026-04-14 20:26:56.784934', '2026-04-14 20:26:56.784934'),
    (21, 8, 'Write tests — test_db_projects.py, test_db_tasks.py, test_routes_projects.py.', NULL, 1, 3, 10, '2026-04-14 20:26:56.784934', '2026-04-14 20:26:56.784934'),
    (22, 8, 'Deploy to wcyjvs2.', NULL, 1, 3, 11, '2026-04-14 20:26:56.784934', '2026-04-14 20:26:56.784934'),
    (11, 8, 'Fix "add parent"', NULL, 4, 4, 0, '2026-04-14 06:45:49.652087', '2026-04-14 21:58:28.087539'),
    (24, 9, 'create a customized MX linux live usb for refurbishing computers', NULL, 1, 3, 0, '2026-04-14 23:39:53.539835', '2026-04-14 23:39:53.539835'),
    (25, 9, 'identify necessary fonts that should be installed so that things like brower emojis are rendered properly.', NULL, 1, 3, 0, '2026-04-14 23:42:02.004119', '2026-04-14 23:42:02.004119'),
    (27, 8, 'ui theme options: enable viewing this task list on as the old alternating green/white row stripes from the olden days of paper outputs.', NULL, 1, 2, 0, '2026-04-15 00:36:53.702991', '2026-04-15 00:36:53.702991'),
    (28, 8, 'Test the full flow — type a description, set status and priority, hit Save, and confirm it lands back on the board.', NULL, 4, 4, 0, '2026-04-15 01:03:31.292592', '2026-04-15 01:28:24.017097'),
    (29, 8, 'fix add task so that after saving a new task it goes back to the board', NULL, 4, 3, 0, '2026-04-15 01:30:55.719491', '2026-04-15 01:31:42.559649'),
    (12, 8, 'Fix inverted task hierarchy UX — subtasks should be added from the parent task, not the other way around.', NULL, 4, 4, 0, '2026-04-14 20:26:56.784934', '2026-04-15 01:36:58.491957'),
    (30, 8, 'make index.html show cards for every database the Curator interacts with', NULL, 1, 2, 0, '2026-04-15 01:40:16.340205', '2026-04-15 01:40:16.340205'),
    (31, 3, 'UCSD Help Desk Support Analysthttps://www.indeed.com/viewjob?jk=34bd7e89ec38cab6&tk=1jm6h234incsh801&from=jobi2a_jobmatch-reactivation-en-US_email&rjptk=1jm6h22a0mt27805&xpse=SoC267I3kHUoCS2FVJ0LbzkdCdPP&xfps=550d9f13-cd70-4496-992c-a65aa3149b6f&xkcb=SoC167M3kGqHErWuRx0ObzkdCdPP', NULL, 1, 3, 0, '2026-04-15 02:09:21.239784', '2026-04-15 02:09:21.239784'),
    (32, 3, 'Technical Writer, SDCCDhttps://www.sdccdjobs.com/postings/16756', NULL, 1, 1, 0, '2026-04-15 02:20:05.434055', '2026-04-15 02:20:05.434055'),
    (15, 8, 'Replace task status dropdown symbols with double-click dialog showing word labels.', NULL, 4, 3, 0, '2026-04-14 20:26:56.784934', '2026-04-15 02:28:18.681453'),
    (14, 8, 'Add collapsible tree to board left panel.', NULL, 4, 3, 0, '2026-04-14 20:26:56.784934', '2026-04-15 02:28:28.368535'),
    (17, 8, 'Task status change in board panel should stay in panel via HTMX, not redirect to detail page.', NULL, 4, 3, 0, '2026-04-14 20:26:56.784934', '2026-04-15 02:29:29.251238'),
    (13, 8, 'Fix parent_id data issue — existing subprojects have wrong parent_id causing incorrect tree display in board view.', NULL, 4, 1, 0, '2026-04-14 20:26:56.784934', '2026-04-15 02:29:49.086758'),
    (34, 8, 'Add new task dialog to board panel — no navigation away, no parent field ', NULL, 4, 3, 0, '2026-04-15 02:30:54.73236', '2026-04-15 02:30:54.73236'),
    (35, 8, 'Add Curator character image to empty panel state', NULL, 1, 2, 0, '2026-04-15 02:31:45.666829', '2026-04-15 02:31:45.666829'),
    (23, 8, 'Write README.', NULL, 2, 2, 0, '2026-04-14 20:26:56.784934', '2026-04-15 02:34:33.312803'),
    (39, 2, 'Audit devices for lan inventory databases', NULL, 2, 2, 0, '2026-04-15 02:40:51.338405', '2026-04-15 02:40:51.338405'),
    (38, 2, 'Create a PostgreSQL database for lan information and interaction with ansible', NULL, 2, 3, 0, '2026-04-15 02:40:07.149754', '2026-04-15 02:41:06.518526'),
    (33, 8, 'Add a task search bar at the top of the tasks detail page', NULL, 4, 3, 0, '2026-04-15 02:27:15.75587', '2026-04-15 03:15:10.33656'),
    (16, 8, 'Add Board link to nav in base.html.', NULL, 4, 3, 0, '2026-04-14 20:26:56.784934', '2026-04-15 03:16:41.966674'),
    (41, 8, 'Align task page buttons', NULL, 1, 2, 0, '2026-04-15 03:28:13.793046', '2026-04-15 03:28:13.793046'),
    (43, 8, 'Fix inline project type edit redirect — stay on board after save, verify all other inline edits are the same', NULL, 1, 3, 0, '2026-04-16 16:25:00.522071', '2026-04-16 16:25:00.522071'),
    (44, 8, 'Delete the standalone project detail page/route', NULL, 1, 2, 0, '2026-04-16 16:25:26.188654', '2026-04-16 16:25:26.188654'),
    (45, 12, 'refactor any python tools that use flat layout to use src layout.', NULL, 1, 3, 0, '2026-04-16 20:34:03.865333', '2026-04-16 20:34:03.865333'),
    (46, 8, '"Add a related items section to project and task detail pages. A dropdown allowing users to link any project or task to any other project or task, with the relationship displayed as a navigable link on both detail pages."', NULL, 1, 2, 0, '2026-04-16 20:41:45.615121', '2026-04-16 20:41:45.615121'),
    (47, 8, 'come up with a way to save repos in a list so they don''t have to be typed from scatch every time. A filterable search page like the project tasks details page maybe or a combo dropdown bos if that''s still a thing.', NULL, 1, 2, 0, '2026-04-16 20:50:05.682627', '2026-04-16 20:50:05.682627'),
    (51, 14, 'modify fletcher to detect local git first.', NULL, 4, 3, 0, '2026-04-17 04:13:17.245829', '2026-04-17 04:51:57.632369'),
    (49, 14, 'refactor: have fletcher manifest.yml file date to compare to run date, prompt for ok if different', NULL, 1, 3, 0, '2026-04-17 03:49:46.920373', '2026-04-17 03:49:46.920373'),
    (50, 8, 'Add ability to add sub-projects to a project record instead of having to create a new project and set a parent id', NULL, 1, 3, 0, '2026-04-17 04:06:29.50634', '2026-04-17 04:06:29.50634'),
    (48, 14, 'fix confusion related if fletcher ever gets a version.py added to it', NULL, 1, 2, 0, '2026-04-17 03:44:08.511069', '2026-04-17 04:50:33.925486'),
    (36, 8, 'Keep board panel open and refreshed after task status change via HTMX | open | normal', NULL, 4, 2, 0, '2026-04-15 02:32:22.37792', '2026-04-17 04:54:32.089104'),
    (9, 8, 'modify projects and tasks to use list boxes', NULL, 4, 2, 0, '2026-04-14 06:43:42.450723', '2026-04-24 17:06:36.548813'),
    (52, 14, 'add --manifest cli parameter so that fletcher can run from the folder where toml is located and still find manifest.yml in the dev-utils project root.', NULL, 5, 4, 0, '2026-04-17 04:47:16.327363', '2026-04-17 04:51:27.080818'),
    (53, 8, 'redo the search bar to fit the page better', NULL, 1, 2, 0, '2026-04-17 04:53:08.504011', '2026-04-17 04:53:08.504011'),
    (54, 8, 'add space to the right of the pencil icon for task editing ', NULL, 1, 3, 0, '2026-04-17 04:53:46.881805', '2026-04-17 04:53:46.881805'),
    (55, 8, 'add left and right borders to project detail page', NULL, 1, 3, 0, '2026-04-17 13:47:38.79413', '2026-04-17 13:47:38.79413'),
    (56, 8, 'align buttons on detail page.', NULL, 1, 3, 0, '2026-04-17 13:48:05.18552', '2026-04-17 13:48:05.18552'),
    (84, 8, 'Verify all hard-coded script values that can be moved to external configs have been moved', NULL, 1, 2, 0, '2026-04-21 21:21:03.253357', '2026-04-21 21:21:03.253357'),
    (58, 8, 'Add the links text box to the inline editing detail page for adding a new task', NULL, 1, 2, 0, '2026-04-17 14:20:44.17362', '2026-04-17 14:20:44.17362'),
    (57, 8, 'Add tabbed panel view with Snippets — tabs for Tasks, Subprojects, and Snippets; Snippets are project-scoped searchable reference entries (title, body, category)', NULL, 1, 2, 0, '2026-04-17 14:18:34.107614', '2026-04-17 14:29:29.761007'),
    (59, 1, 'Reporting', NULL, 1, 2, 0, '2026-04-17 14:31:29.384333', '2026-04-17 14:31:29.384333'),
    (62, 14, 'creat a simple lookup like fletcher manifest-url dbkit that reads the local manifest and returns the raw URL.', NULL, 1, 3, 0, '2026-04-17 15:50:20.594755', '2026-04-17 15:50:20.594755'),
    (63, 15, 'change repro branch first guess from "master" to "main"', NULL, 1, 3, 0, '2026-04-17 15:54:50.902911', '2026-04-17 15:54:50.902911'),
    (64, 15, 'Filter out egginfo* from the list of directories.', NULL, 1, 3, 0, '2026-04-17 15:59:33.819869', '2026-04-17 15:59:33.819869'),
    (61, 15, 'add packaging to pyproject.toml for setupkit', NULL, 4, 4, 0, '2026-04-17 15:31:00.867342', '2026-04-17 16:09:22.772249'),
    (66, 15, 'add default directory option to detected that shows as <suggested in the list', NULL, 1, 3, 0, '2026-04-17 16:10:22.042906', '2026-04-17 16:10:22.042906'),
    (69, 8, 'Between the word PROJECTS and the + sign at the top of the projects list, include a dropdown to filter for project type', NULL, 1, 3, 0, '2026-04-17 23:55:15.585916', '2026-04-17 23:55:15.585916'),
    (71, 8, 'create a query to filter task status based on project type', NULL, 1, 2, 0, '2026-04-18 15:34:11.491619', '2026-04-18 15:34:11.491619'),
    (72, 8, 'Projects searching', NULL, 1, 3, 0, '2026-04-18 15:49:17.680181', '2026-04-18 15:49:17.680181'),
    (73, 12, 'bugfix: repo branch detection', NULL, 5, 4, 0, '2026-04-18 18:33:57.504865', '2026-04-18 18:33:57.504865'),
    (74, 1, 'New member of the project crew: The Quartermaster', NULL, 1, 3, 0, '2026-04-19 18:23:39.236346', '2026-04-19 18:23:39.236346'),
    (70, 8, 'Externalize sql that is currently in projects.py to comply with project_rules.md', NULL, 4, 4, 0, '2026-04-18 00:42:03.300443', '2026-04-20 04:07:46.832778'),
    (79, 8, 'Add a "full edit" button to the add task dialog', NULL, 1, 2, 0, '2026-04-21 18:36:00.568298', '2026-04-21 18:36:00.568298'),
    (80, 8, 'save notes and urls from add task popup', NULL, 1, 1, 0, '2026-04-21 18:36:48.049234', '2026-04-21 18:37:10.815089'),
    (91, 15, 'changedoc for venv path and logger', 'etupkit_venv_path_and_bootstrap.md in setupkit/docs/changedocs', 4, 3, 0, '2026-04-24 16:44:42.747119', '2026-04-24 16:44:42.747119'),
    (85, 8, 'assure all functions have docstrings and fix anything else the linter complains about ', NULL, 1, 3, 0, '2026-04-21 21:22:11.795146', '2026-04-21 21:22:11.795146'),
    (92, 8, 'Add a link to parent project if it exists.', 'same as parent project shows sub project links in board detail.', 1, 2, 0, '2026-04-24 16:46:40.560955', '2026-04-24 16:46:40.560955'),
    (88, 8, 'Add status message to project add form so that records don''t get duplicated on save,', 'Also, consider ways to prevent duplication of records in general, unless they''re supposed to be duplicated.', 1, 3, 0, '2026-04-22 01:36:03.032082', '2026-04-22 01:36:03.032082'),
    (93, 15, 'setupkit_logger_and_setup_sh.md changedoc', 'setupkit_logger_and_setup_sh.md', 4, 3, 0, '2026-04-24 16:47:54.441882', '2026-04-24 16:47:54.441882'),
    (90, 8, 'decided whether project tree should show project trees fully or if only one level display is sufficient.', 'right now a sub-project of a sub-project displays as if the project is a direct sub of the top level project. changing that to reflect the actual hierarch would likely be a mess.', 1, 2, 0, '2026-04-24 16:22:04.607918', '2026-04-24 16:22:04.607918'),
    (94, 8, 'Remove hardcoded variables from all code. Task status appears to be hard-coded since there are other status values in the task status table that do not appear in this task add dialog.', NULL, 1, 2, 0, '2026-04-24 16:49:39.393503', '2026-04-24 16:49:39.393503'),
    (95, 15, 'Add venv_path to setupkit.yaml', 'Apply changes from setupkit_venv_path_and_bootstrap.md', 5, 4, 0, '2026-04-24 16:50:56.952413', '2026-04-24 16:50:56.952413'),
    (96, 15, 'Add venv_path property to config.py', 'Apply changes from setupkit_venv_path_and_bootstrap.md', 1, 3, 0, '2026-04-24 16:51:31.114003', '2026-04-24 16:51:31.114003'),
    (97, 8, 'decide if tasks should have files link', 'do this after original us is solid, I''m leaning toward do this.', 1, 2, 0, '2026-04-24 16:52:31.365093', '2026-04-24 16:52:31.365093'),
    (98, 15, 'create logger.py', 'Apply changes from setupkit_venv_path_and_bootstrap.md', 1, 3, 0, '2026-04-24 16:53:18.210739', '2026-04-24 16:53:18.210739'),
    (99, 15, 'remove _setup_logging() from installer.py6', NULL, 1, 3, 0, '2026-04-24 16:54:10.467498', '2026-04-24 16:54:10.467498'),
    (100, 15, 'remove LOG_PATH from installer.py', 'setupkit_logger_and_setup_sh.md', 1, 3, 0, '2026-04-24 16:55:19.692868', '2026-04-24 16:55:19.692868'),
    (101, 15, 'update main() in installer.py', 'setupkit_logger_and_setup_sh.md', 1, 3, 0, '2026-04-24 16:55:40.601317', '2026-04-24 16:55:40.601317'),
    (102, 8, 'Enable opening local file links from  curator.', 'Currently opens url links fine but local file links try to find the file on localhost and return: "{"detail":"Not Found"}" error', 1, 2, 0, '2026-04-24 16:59:13.28808', '2026-04-24 16:59:13.28808'),
    (103, 14, 'create the ability to only generate raw urls for a subset, like "everything in the docs folder [repo root]/docs/*', NULL, 1, 2, 0, '2026-04-24 17:00:34.240839', '2026-04-24 17:00:34.240839'),
    (65, 14, 'bugfix: manifest.fletch shows branch master when it is really main', NULL, 4, 3, 0, '2026-04-17 16:07:30.846375', '2026-04-24 17:04:24.682703'),
    (67, 8, 'walk thru all board edit re-directs to identify any issues.', NULL, 4, 4, 0, '2026-04-17 16:26:22.574573', '2026-04-24 17:06:22.967917'),
    (104, 14, 'fits ignore patterns so that they apply to every level of the repo hierarchy.', 'It must not be doing this right now because  egginfo should never make it into the manifest', 1, 3, 0, '2026-04-24 17:01:39.037874', '2026-04-24 17:01:39.037874'),
    (105, 15, 'create setup.sh at dev-utils repo root', NULL, 1, 3, 0, '2026-04-24 17:03:13.130584', '2026-04-24 17:03:13.130584'),
    (106, 8, 'Add delete task button to task full edit form. ', 'visibility to be user role-based', 1, 3, 0, '2026-04-24 17:05:46.614153', '2026-04-24 17:05:46.614153'),
    (107, 63, 'this is a test task to see if task notes get saved', 'test task not', 1, 3, 0, '2026-04-25 19:16:07.305221', '2026-04-25 19:16:07.305221'),
    (108, 15, 'Eventually change setpkit readme to skip reference to opt venv installtion', 'this a network path I use so that any user on the machine can use what''s installed there, but that''s a personal preference that doesn''t belong in the readme', 1, 2, 0, '2026-04-26 17:37:57.222615', '2026-04-26 17:37:57.222615'),
    (109, 12, 'Update the README.md in the repo root', 'done and in local repo, not yet committed.', 4, 3, 0, '2026-04-26 17:40:54.779986', '2026-04-26 17:40:54.779986'),
    (60, 12, 'create a tool to automate creation of a network venv for installing python packages accessible to all users.', NULL, 1, 2, 0, '2026-04-17 14:43:52.770544', '2026-04-26 17:46:17.415233'),
    (110, 8, 'fix links in tasks', 'saved links to claude.ai conversations, copied from adminer, and pasted into chromium got an error message', 1, 2, 0, '2026-04-26 17:51:06.138036', '2026-04-26 17:51:06.138036'),
    (111, 12, 'fix task edit updating', 'added links to a task, save shows they''re in adminer but they don''t show in curator until the whole thing is restarted.', 1, 3, 0, '2026-04-26 17:52:58.713974', '2026-04-26 17:52:58.713974'),
    (112, 69, 'Install ansible', NULL, 1, 3, 0, '2026-05-06 19:03:54.340915', '2026-05-06 19:03:54.340915'),
    (113, 70, 'firewall setup ', NULL, 1, 1, 0, '2026-05-06 19:58:50.654226', '2026-05-06 19:58:50.654226'),
    (115, 70, 'Headscale coordination server', 'curl -s https://api.github.com/repos/juanfont/headscale/releases/latest | grep "browser_download_url.*linux_amd64.rpm" | cut -d ''"'' -f 4', 1, 1, 0, '2026-05-06 19:59:41.202105', '2026-05-06 20:17:34.898614'),
    (117, 70, 'certbot for headscale', NULL, 1, 1, 0, '2026-05-06 21:11:52.866975', '2026-05-06 21:11:52.866975'),
    (114, 70, 'fail2ban', NULL, 4, 1, 0, '2026-05-06 19:59:05.636045', '2026-05-06 21:12:01.39467'),
    (116, 71, 'install headscale', NULL, 4, 1, 0, '2026-05-06 20:19:45.276002', '2026-05-07 19:22:45.645266'),
    (118, 71, 'Document everything it took to setup the lan on the new VPS and get everything working again', 'new mesh broke everything, that is bad', 1, 3, 0, '2026-05-07 19:23:52.097081', '2026-05-07 19:23:52.097081')
ON CONFLICT DO NOTHING;

-- Verify: SELECT COUNT(*) FROM projects.tasks; -- expect 96

-- -------------------------------------------------------------
-- Step 10: Reset tasks ID sequence
-- -------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('projects.tasks', 'id'),
    (SELECT MAX(id) FROM projects.tasks));

-- =============================================================
-- Migration complete — verify counts then proceed to Phase 2.2
-- =============================================================
```
