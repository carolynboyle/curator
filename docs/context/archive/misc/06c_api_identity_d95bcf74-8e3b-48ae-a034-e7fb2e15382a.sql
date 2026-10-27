-- =============================================================================
-- 06c_api_identity.sql — API schema: identity.* stored procedures
-- =============================================================================
--
-- Paired with 02_identity.sql (the schema these procs operate on). A
-- future database reusing 02_identity.sql's schema can also reuse this
-- file without dragging along auth or projects procs.
--
-- All procs SECURITY DEFINER — see 06a_api_auth.sql header for the full
-- security model note (applies to all api.* files, not repeated per file).
--
-- Depends on: 01_audit.sql, 02_identity.sql
-- GRANTs live in 06d_api_grants.sql.
-- =============================================================================

-- =============================================================================
-- api.save_contact(payload JSONB, user_id BIGINT)
--
-- Insert or update based on presence of payload->>'id'.
-- contacts.name has no UNIQUE constraint — people can share names — so,
-- unlike save_organization/save_project, there is no duplicate-name
-- rejection here.
--
-- Payload shape:
-- {
--   "id":    null,         -- null/absent = INSERT, int = UPDATE
--   "name":  "Jane Doe",   -- required
--   "title": "...",        -- optional
--   "notes": "..."         -- optional
-- }
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
--
-- Payload shape:
-- {
--   "id":    null,          -- null/absent = INSERT, int = UPDATE
--   "name":  "Bailey Ltd",  -- required, must be unique
--   "notes": "..."          -- optional
-- }
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
