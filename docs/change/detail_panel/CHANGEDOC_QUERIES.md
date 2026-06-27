# Changedoc: queries.yaml — Add Child Datasheet Queries

**Date:** 2026-06-27  
**File:** `queries.yaml`  
**Reason:** Add queries for fetching child datasheets (tasks for projects, emails/phones/URLs for contacts, contacts for organizations) — used by detail panel and `/api/query` endpoint

---

## BEFORE

```yaml
# viewkit test fixture
# Mirrors the shape of a real queries.yaml without coupling to
# any specific application's schema.

projects:
  get_all:
    type: select_all
    sql: "SELECT * FROM v_projects ORDER BY name"

  get_all_by_status:
    type: select_all
    sql: >
      SELECT * FROM v_projects
      WHERE status = %s
      ORDER BY name

  get_by_slug:
    type: select_one
    sql: "SELECT * FROM v_projects WHERE slug = %s"

  slug_exists:
    type: select_scalar
    sql: "SELECT EXISTS (SELECT 1 FROM projects WHERE slug = %s)"

  create:
    type: execute
    sql: >
      INSERT INTO projects (name, slug, description, status_id, type_id, parent_id)
      VALUES (%s, %s, %s, %s, %s, %s)

  delete:
    type: execute
    sql: "DELETE FROM projects WHERE slug = %s"

tasks:
  get_by_id:
    type: select_one
    sql: "SELECT * FROM v_tasks WHERE id = %s"

  get_child_count:
    type: select_scalar
    sql: "SELECT COUNT(*) FROM tasks WHERE parent_id = %s"

  create:
    type: select_scalar
    sql: >
      INSERT INTO tasks
          (project_id, parent_id, description, status_id, priority_id,
           links, source_file, sort_order)
      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
      RETURNING id
```

---

## AFTER

```yaml
# viewkit test fixture
# Mirrors the shape of a real queries.yaml without coupling to
# any specific application's schema.

projects:
  get_all:
    type: select_all
    sql: "SELECT * FROM v_projects ORDER BY name"

  get_all_by_status:
    type: select_all
    sql: >
      SELECT * FROM v_projects
      WHERE status = %s
      ORDER BY name

  get_by_slug:
    type: select_one
    sql: "SELECT * FROM v_projects WHERE slug = %s"

  slug_exists:
    type: select_scalar
    sql: "SELECT EXISTS (SELECT 1 FROM projects WHERE slug = %s)"

  create:
    type: execute
    sql: >
      INSERT INTO projects (name, slug, description, status_id, type_id, parent_id)
      VALUES (%s, %s, %s, %s, %s, %s)

  delete:
    type: execute
    sql: "DELETE FROM projects WHERE slug = %s"

tasks:
  get_by_id:
    type: select_one
    sql: "SELECT * FROM v_tasks WHERE id = %s"

  get_child_count:
    type: select_scalar
    sql: "SELECT COUNT(*) FROM tasks WHERE parent_id = %s"

  create:
    type: select_scalar
    sql: >
      INSERT INTO tasks
          (project_id, parent_id, description, status_id, priority_id,
           links, source_file, sort_order)
      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
      RETURNING id

  # NEW: Fetch all tasks for a project (detail panel Tasks tab)
  for_project:
    type: select_all
    sql: >
      SELECT
          id,
          description::text,
          status_id,
          priority_id,
          created_at
      FROM projects.tasks
      WHERE project_id = %s
      ORDER BY created_at DESC

contact_emails:
  # NEW: Fetch all emails for a contact (detail panel Emails tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          label::text,
          address::text
      FROM identity.contact_emails
      WHERE contact_id = %s
      ORDER BY id

contact_phones:
  # NEW: Fetch all phones for a contact (detail panel Phones tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          label::text,
          number::text
      FROM identity.contact_phones
      WHERE contact_id = %s
      ORDER BY id

contact_urls:
  # NEW: Fetch all URLs for a contact (detail panel URLs tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          (SELECT name FROM identity.url_type ut WHERE ut.id = url_type_id)::text AS type,
          value::text
      FROM identity.contact_urls
      WHERE contact_id = %s
      ORDER BY id

organization_contacts:
  # NEW: Fetch all contacts in an organization (detail panel Contacts tab)
  for_organization:
    type: select_all
    sql: >
      SELECT
          c.id,
          c.name::text,
          c.title::text,
          (SELECT name FROM identity.organization_contact_role ocr WHERE ocr.id = oc.role_id)::text AS role
      FROM identity.contacts c
      JOIN identity.organization_contacts oc
          ON oc.contact_id = c.id
      WHERE oc.organization_id = %s
      ORDER BY c.name

  # NEW: Fetch all organizations for a contact (detail panel Organizations tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          o.id,
          o.name::text,
          (SELECT name FROM identity.organization_contact_role ocr WHERE ocr.id = oc.role_id)::text AS role
      FROM identity.organizations o
      JOIN identity.organization_contacts oc
          ON oc.organization_id = o.id
      WHERE oc.contact_id = %s
      ORDER BY o.name
```

---

## Why These Changes

**New query groups:**
- `tasks.for_project` — fetch all tasks for a project in the detail panel Tasks tab
- `contact_emails.for_contact` — fetch all emails for a contact
- `contact_phones.for_contact` — fetch all phones for a contact
- `contact_urls.for_contact` — fetch all URLs for a contact
- `organization_contacts.for_organization` — fetch all contacts in an organization
- `organization_contacts.for_contact` — fetch all organizations for a contact

Each query returns only the columns needed for the child datasheet, cast to `::text` for consistency. Lookup values (like URL type name, role name) are subqueried to return the display text rather than the ID.

These queries power the `/api/query/{entity}/{query_name}?params=X` endpoint, which is called by `_datasheet.html` via Tabulator's `ajax` configuration.
