# curator_v2_schema_design.md

**Path:** docs/design/curator_v2_schema_design.md
**Syntax:** markdown
**Generated:** 2026-06-23 12:09:21

```markdown
# Curator v2 — Schema Design

*Designed: June 2026*  
*Status: Approved for implementation*

---

## Design Principles

- Flat projects — no project hierarchy in UI; `parent_id` exists in DB for future use
- Tasks can have sub-tasks via `parent_id`
- Contacts are the central entity — users, organization members, project contacts all hang off contacts
- Organizations have contacts via junction table — a contact can belong to multiple organizations
- Separate PostgreSQL schemas by domain
- Audit log on all entity tables via PostgreSQL triggers
- `created_by` / `updated_by` on all entity tables for quick reference
- All lookup tables sorted alphabetically by name — no `sort_order` column
- Notes field on all entity tables; not on child detail tables (phones, emails, urls) or audit tables
- Retention policy on audit log: delete records older than 12 months (implement after launch)

---

## PostgreSQL Schemas

- `contacts` — organizations, people, phones, emails, URLs, auth
- `projects` — projects, tasks, tags, files
- `audit` — audit log (shared across domains)

---

## contacts schema

### Lookup Tables

#### `contacts.url_type`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(50) NOT NULL UNIQUE | website, linkedin, github, twitter, instagram, etc. |

#### `contacts.user_role`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(50) NOT NULL UNIQUE | admin, staff, customer |

#### `contacts.organization_contact_role`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(50) NOT NULL UNIQUE | owner, employee, customer, vendor, etc. |

---

### Entity Tables

#### `contacts.organizations`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(255) NOT NULL UNIQUE | |
| notes | TEXT | |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMP NOT NULL DEFAULT now() | |
| created_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |
| updated_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |

#### `contacts.contacts`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(255) | nullable — phone/email-only contacts allowed |
| title | VARCHAR(255) | |
| notes | TEXT | |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMP NOT NULL DEFAULT now() | |
| created_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |
| updated_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |

#### `contacts.contact_emails`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| contact_id | BIGINT NOT NULL FK → contacts.contacts.id ON DELETE CASCADE | |
| email | VARCHAR(255) | |
| email_type | VARCHAR(50) | personal, work, etc. |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |

#### `contacts.contact_phones`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| contact_id | BIGINT NOT NULL FK → contacts.contacts.id ON DELETE CASCADE | |
| phone_number | VARCHAR(50) NOT NULL | |
| description | VARCHAR(100) | mobile, work, home, etc. |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |

#### `contacts.contact_urls`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| contact_id | BIGINT NOT NULL FK → contacts.contacts.id ON DELETE CASCADE | |
| url_type_id | BIGINT NOT NULL FK → contacts.url_type.id | |
| value | VARCHAR(500) NOT NULL | full URL or @handle |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |

---

### Auth Tables

#### `contacts.app_user`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| contact_id | BIGINT NOT NULL UNIQUE FK → contacts.contacts.id ON DELETE RESTRICT | |
| username | VARCHAR(100) NOT NULL UNIQUE | |
| password_hash | VARCHAR(255) NOT NULL | |
| role_id | BIGINT NOT NULL FK → contacts.user_role.id | |
| is_active | BOOLEAN NOT NULL DEFAULT TRUE | |
| last_login | TIMESTAMP | |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMP NOT NULL DEFAULT now() | |

---

### Junction Tables

#### `contacts.organization_contacts`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| organization_id | BIGINT NOT NULL FK → contacts.organizations.id ON DELETE CASCADE | |
| contact_id | BIGINT NOT NULL FK → contacts.contacts.id ON DELETE CASCADE | |
| role_id | BIGINT FK → contacts.organization_contact_role.id | |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |

---

### Audit Table (shared)

#### `audit.audit_log`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| schema_name | VARCHAR(100) NOT NULL | which schema the change was in |
| table_name | VARCHAR(100) NOT NULL | which table changed |
| record_id | BIGINT NOT NULL | PK of the changed record |
| action | VARCHAR(10) NOT NULL | INSERT, UPDATE, DELETE |
| changed_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |
| changed_at | TIMESTAMP NOT NULL DEFAULT now() | |
| old_values | JSONB | NULL on INSERT |
| new_values | JSONB | NULL on DELETE |

---

## projects schema

### Lookup Tables

#### `projects.project_status`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(50) NOT NULL UNIQUE | active, queued, on hold, complete, archived |

#### `projects.project_type`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(50) NOT NULL UNIQUE | writing, refurb, homelab, etc. |

#### `projects.task_status`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(50) NOT NULL UNIQUE | |
| is_terminal | BOOLEAN NOT NULL DEFAULT FALSE | |

#### `projects.priority`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(50) NOT NULL UNIQUE | low, normal, high, urgent |

---

### Entity Tables

#### `projects.projects`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| name | VARCHAR(255) NOT NULL | |
| slug | VARCHAR(100) NOT NULL UNIQUE | |
| description | TEXT | |
| notes | TEXT | |
| status_id | BIGINT NOT NULL FK → projects.project_status.id | |
| type_id | BIGINT FK → projects.project_type.id | |
| parent_id | BIGINT FK → projects.projects.id ON DELETE SET NULL | future use only — not exposed in UI |
| target_date | DATE | |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMP NOT NULL DEFAULT now() | |
| created_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |
| updated_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |

#### `projects.tasks`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| project_id | BIGINT NOT NULL FK → projects.projects.id ON DELETE CASCADE | |
| parent_id | BIGINT FK → projects.tasks.id ON DELETE SET NULL | sub-tasks |
| description | TEXT NOT NULL | |
| notes | TEXT | |
| status_id | BIGINT NOT NULL FK → projects.task_status.id | |
| priority_id | BIGINT FK → projects.priority.id | |
| is_terminal | BOOLEAN NOT NULL DEFAULT FALSE | |
| sort_order | INT NOT NULL DEFAULT 0 | |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMP NOT NULL DEFAULT now() | |
| created_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |
| updated_by | BIGINT FK → contacts.app_user.id ON DELETE SET NULL | |

---

### Junction Tables

#### `projects.project_contacts`
| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT GENERATED ALWAYS AS IDENTITY PK | |
| project_id | BIGINT NOT NULL FK → projects.projects.id ON DELETE CASCADE | |
| contact_id | BIGINT NOT NULL FK → contacts.contacts.id ON DELETE CASCADE | |
| role | VARCHAR(100) | customer, vendor, collaborator, etc. |
| is_primary | BOOLEAN NOT NULL DEFAULT FALSE | |
| notes | TEXT | |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |

---

## Seed Data

### contacts.url_type
github, instagram, linkedin, twitter, website

### contacts.user_role
admin, customer, staff

### contacts.organization_contact_role
customer, employee, owner, vendor

### projects.project_status
active, archived, complete, on hold, queued

### projects.task_status
| name | is_terminal |
|------|-------------|
| backlog | false |
| in progress | false |
| blocked | false |
| complete | true |
| cancelled | true |

### projects.priority
high, low, normal, urgent

---

## Notes & Decisions

- `parent_id` on projects exists in DB but is not exposed in UI until subproject support is deliberately added
- Tasks support sub-tasks via `parent_id` from day one
- A user must be a contact before they can have an `app_user` record
- `ON DELETE RESTRICT` on `app_user.contact_id` — you cannot delete a contact who has a login
- Audit log retention policy (delete records older than 12 months) to be implemented after launch
- All lookup tables sorted by name in queries — no sort_order column
- Landing page cards filter by `project_type.name` directly on the projects table — no tree traversal needed
- `email_type` and `phone description` are free text for now — can be normalized to lookup tables later if needed

```
