# Changedoc: Fix contact_emails / contact_phones column mismatches

**File:** `src/curator/data/queries.yaml`
**Type:** Data fix — no schema change, no Python change, no JS change
**Reason:** `queries.yaml` referenced columns that don't exist in
`identity.contact_emails` / `identity.contact_phones`. Confirmed against
`02_identity.sql`:

- `contact_emails` has columns `label`, `address` (not `email`, `email_type`)
- `contact_phones` has columns `label`, `number` (not `phone_number`, `description`)

These datasheets ("coming soon" per `curator_handoff_2026-06-30.md`) have no
live JS consumer yet, so there's no existing contract to preserve — decision
made to use the real column names as-is rather than aliasing them to
invented names.

---

## BEFORE

```yaml
contact_emails:
  # Fetch all emails for a contact (detail panel Emails tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          email::text,
          email_type::text
      FROM identity.contact_emails
      WHERE contact_id = %s
      ORDER BY id
```

```yaml
contact_phones:
  # Fetch all phones for a contact (detail panel Phones tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          phone_number::text,
          description::text
      FROM identity.contact_phones
      WHERE contact_id = %s
      ORDER BY id
```

## AFTER

```yaml
contact_emails:
  # Fetch all emails for a contact (detail panel Emails tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          address::text,
          label::text
      FROM identity.contact_emails
      WHERE contact_id = %s
      ORDER BY id
```

```yaml
contact_phones:
  # Fetch all phones for a contact (detail panel Phones tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          number::text,
          label::text
      FROM identity.contact_phones
      WHERE contact_id = %s
      ORDER BY id
```

---

## Notes
- `contact_urls` and `organization_contacts` queries were checked against
  `02_identity.sql` and already reference correct column names — no change
  needed there.
- No consumers of these two queries exist yet in Python or JS, so this is a
  pure data-definition fix with zero blast radius.
