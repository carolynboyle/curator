# Changedoc: Lowercase constraint on `app_user.username`

**Files:** `02_identity.sql` (canonical source), `steward` DB (`wcyj`, live migration)
**Type:** Additive constraint — no existing data expected to violate it, but
verify before applying (see Step 1 below)
**Reason:** Prevent case-variant duplicate usernames (`Carolyn` vs `carolyn`)
at the database level rather than relying on application-layer discipline.

---

## BEFORE — `02_identity.sql`

```sql
CREATE TABLE identity.app_user (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id    BIGINT       NOT NULL UNIQUE
                               REFERENCES identity.contacts (id) ON DELETE RESTRICT,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id       BIGINT       NOT NULL REFERENCES identity.user_role (id),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

## AFTER — `02_identity.sql`

```sql
CREATE TABLE identity.app_user (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id    BIGINT       NOT NULL UNIQUE
                               REFERENCES identity.contacts (id) ON DELETE RESTRICT,
    username      VARCHAR(100) NOT NULL UNIQUE
                               CONSTRAINT chk_username_lowercase
                               CHECK (username = LOWER(username)),
    password_hash VARCHAR(255) NOT NULL,
    role_id       BIGINT       NOT NULL REFERENCES identity.user_role (id),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

---

## Live migration (run in pgAdmin against `wcyj`)

**Step 1 — check for existing violations first:**
```sql
SELECT id, username FROM identity.app_user
WHERE username <> LOWER(username);
```
If this returns any rows, decide with Carolyn how to resolve them (rename in
place, or normalize via `UPDATE ... SET username = LOWER(username)`) before
adding the constraint — the `ALTER TABLE` below will fail otherwise.

**Step 2 — add the constraint:**
```sql
ALTER TABLE identity.app_user
    ADD CONSTRAINT chk_username_lowercase
    CHECK (username = LOWER(username));
```

---

## Notes
- Additive/constraining only — no column type or default changes, no data
  migration required assuming Step 1 comes back clean.
- Should be low-risk: current known users are `carolyn` and whatever
  Felipe's demo account username is — worth eyeballing Step 1's output
  before running Step 2 regardless.
