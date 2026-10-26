# Changedoc: New procs — api.save_contact, api.delete_contact, api.save_organization, api.delete_organization

**File:** `06_api.sql` (append after `api.delete_project`, before the GRANTs
block at the end of the file)
**Type:** New procs — additive, mirrors the existing `api.save_project` /
`api.delete_project` pattern exactly (SECURITY DEFINER, JSONB envelope
return, same exception handling shape).
**Reason:** Contacts and Organizations have no procs at all yet — this is
what's missing to make the Identities tab's Save actually succeed (the
"Save failed" alert is a 404, since `crew.py` has nothing to call).

Schema fields used:
- `identity.contacts`: `name`, `title`, `notes` — `name` is **not**
  unique (people can share names), so no conflict check, matching the
  schema's own constraints.
- `identity.organizations`: `name` (UNIQUE), `notes` — conflict check
  included, same shape as `api.save_project`'s duplicate-name check.

---

## New SQL — append to `06_api.sql`

```sql
-- =============================================================================
-- api.save_contact(payload JSONB, user_id BIGINT)
--
-- Insert or update based on presence of payload->>'id'.
-- contacts.name has no UNIQUE constraint — people can share names — so,
-- unlike save_project, there is no duplicate-name rejection here.
-- =============================================================================

CREATE OR REPLACE FUNCTION api.save_contact(
    p_payload JSONB,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id        BIGINT;
    v_name      VARCHAR(255);
    v_title     VARCHAR(255);
    v_notes     TEXT;
    v_is_update BOOLEAN;
BEGIN
    v_name := TRIM(p_payload->>'name');

    IF v_name IS NULL OR v_name = '' THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Contact name is required.'
        );
    END IF;

    v_id        := (p_payload->>'id')::BIGINT;
    v_is_update := v_id IS NOT NULL;

    v_title := NULLIF(TRIM(p_payload->>'title'), '');
    v_notes := NULLIF(TRIM(p_payload->>'notes'), '');

    IF v_is_update THEN
        IF NOT EXISTS (SELECT 1 FROM identity.contacts WHERE id = v_id) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'Contact not found.'
            );
        END IF;

        UPDATE identity.contacts SET
            name       = v_name,
            title      = v_title,
            notes      = v_notes,
            updated_by = p_user_id
        WHERE id = v_id;

        RETURN jsonb_build_object(
            'success', TRUE,
            'data',    jsonb_build_object('id', v_id),
            'message', 'Contact updated.'
        );

    ELSE
        INSERT INTO identity.contacts (
            name, title, notes, created_by, updated_by
        ) VALUES (
            v_name, v_title, v_notes, p_user_id, p_user_id
        )
        RETURNING id INTO v_id;

        RETURN jsonb_build_object(
            'success', TRUE,
            'data',    jsonb_build_object('id', v_id),
            'message', 'Contact created.'
        );
    END IF;

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'api.save_contact error: %', SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred saving the contact.'
    );
END;
$$;


-- =============================================================================
-- api.delete_contact(id BIGINT, user_id BIGINT)
--
-- Hard delete. Audit trigger on identity.contacts captures the DELETE.
-- Returns error if contact has dependent records that block deletion
-- (e.g. organization_contacts, contact_emails without ON DELETE CASCADE —
-- verify against 02_identity.sql's actual FK ON DELETE behavior before
-- relying on this catching every case; adjust message if some child
-- tables cascade instead of blocking).
-- =============================================================================

CREATE OR REPLACE FUNCTION api.delete_contact(
    p_id      BIGINT,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM identity.contacts WHERE id = p_id) THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Contact not found.'
        );
    END IF;

    DELETE FROM identity.contacts WHERE id = p_id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'data',    jsonb_build_object('id', p_id),
        'message', 'Contact deleted.'
    );

EXCEPTION WHEN foreign_key_violation THEN
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'Cannot delete contact — it has dependent records.'
    );
WHEN OTHERS THEN
    RAISE WARNING 'api.delete_contact error for id %: %', p_id, SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred deleting the contact.'
    );
END;
$$;


-- =============================================================================
-- api.save_organization(payload JSONB, user_id BIGINT)
--
-- organizations.name IS UNIQUE — same duplicate-name check shape as
-- api.save_project.
-- =============================================================================

CREATE OR REPLACE FUNCTION api.save_organization(
    p_payload JSONB,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id        BIGINT;
    v_name      VARCHAR(255);
    v_notes     TEXT;
    v_is_update BOOLEAN;
BEGIN
    v_name := TRIM(p_payload->>'name');

    IF v_name IS NULL OR v_name = '' THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Organization name is required.'
        );
    END IF;

    v_id        := (p_payload->>'id')::BIGINT;
    v_is_update := v_id IS NOT NULL;

    v_notes := NULLIF(TRIM(p_payload->>'notes'), '');

    IF v_is_update THEN
        IF NOT EXISTS (SELECT 1 FROM identity.organizations WHERE id = v_id) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'Organization not found.'
            );
        END IF;

        IF EXISTS (
            SELECT 1 FROM identity.organizations
            WHERE name = v_name AND id != v_id
        ) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'An organization with that name already exists.'
            );
        END IF;

        UPDATE identity.organizations SET
            name       = v_name,
            notes      = v_notes,
            updated_by = p_user_id
        WHERE id = v_id;

        RETURN jsonb_build_object(
            'success', TRUE,
            'data',    jsonb_build_object('id', v_id),
            'message', 'Organization updated.'
        );

    ELSE
        IF EXISTS (SELECT 1 FROM identity.organizations WHERE name = v_name) THEN
            RETURN jsonb_build_object(
                'success', FALSE,
                'data',    NULL,
                'message', 'An organization with that name already exists.'
            );
        END IF;

        INSERT INTO identity.organizations (
            name, notes, created_by, updated_by
        ) VALUES (
            v_name, v_notes, p_user_id, p_user_id
        )
        RETURNING id INTO v_id;

        RETURN jsonb_build_object(
            'success', TRUE,
            'data',    jsonb_build_object('id', v_id),
            'message', 'Organization created.'
        );
    END IF;

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'api.save_organization error: %', SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred saving the organization.'
    );
END;
$$;


-- =============================================================================
-- api.delete_organization(id BIGINT, user_id BIGINT)
-- =============================================================================

CREATE OR REPLACE FUNCTION api.delete_organization(
    p_id      BIGINT,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM identity.organizations WHERE id = p_id) THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'data',    NULL,
            'message', 'Organization not found.'
        );
    END IF;

    DELETE FROM identity.organizations WHERE id = p_id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'data',    jsonb_build_object('id', p_id),
        'message', 'Organization deleted.'
    );

EXCEPTION WHEN foreign_key_violation THEN
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'Cannot delete organization — it has dependent records.'
    );
WHEN OTHERS THEN
    RAISE WARNING 'api.delete_organization error for id %: %', p_id, SQLERRM;
    RETURN jsonb_build_object(
        'success', FALSE,
        'data',    NULL,
        'message', 'An unexpected error occurred deleting the organization.'
    );
END;
$$;
```

---

## Live migration (run in pgAdmin against `wcyj`)

Since these are `CREATE OR REPLACE FUNCTION`, run the four blocks above
directly — no `ALTER` needed, no existing data affected. The existing
`GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_app_user;` (and the
matching `steward` grant) already covers these new functions since it
grants on the whole schema, not per-function — no new GRANT statements
needed.

---

## Notes
- `api.save_contact` deliberately has **no** duplicate-name check —
  matches the schema (`contacts.name` has no UNIQUE constraint). Don't
  copy the `save_organization`/`save_project` conflict-check pattern here
  by habit; it would reject legitimate same-named contacts.
- Delete procs assume dependent records (organization_contacts,
  contact_emails/phones/urls, project_contacts) either cascade or raise
  `foreign_key_violation` — verify against `02_identity.sql`'s actual
  `ON DELETE` clauses for those FKs before relying on the "has dependent
  records" message being accurate in every case. Not verified in this
  pass — flagging so it's checked before Felipe hits a delete that
  behaves unexpectedly.
- `is_active`/soft-delete is not implemented anywhere yet (same as
  projects) — these are hard deletes, consistent with `api.delete_project`.
