# Design Doc — Multi-Role Identity Refactor

**Status:** Design only. No SQL or Python in this doc is final — a
changedoc with complete BEFORE/AFTER blocks follows once this design is
agreed, per project convention.

**Why this exists:** Two upcoming crew roles — **Sparks** (messages)
and **Merchant** (future online store, if Felipe builds one) — are
both *additive* to a user's existing persona, not alternatives to it.
Felipe should be able to remain Mechanic and also pick up Sparks (and
later Merchant) without losing Mechanic. The current identity model
can't express that.

---

## Current state

- `identity.app_user` carries a single `crew_role` value (nullable —
  `NULL` means customer-portal user, non-`NULL` means crew member).
- `identity.crew_role` is a lookup table (captain, mechanic, scribe,
  envoy).
- Landing page card visibility (`landing.py`) reads that one value off
  the session and does an equality check: Captain sees every card,
  everyone else sees exactly one card matching their single role.
- Whatever populates `request.state.user` at login time embeds
  `crew_role` as a single string.

This is a "which persona is this person" model. It has no way to
represent "this person is Mechanic *and* Sparks."

---

## Proposed change

### Schema

Replace the single `crew_role` column on `identity.app_user` with a
join table:

```
identity.app_user_crew_role
    id            BIGINT  PK
    user_id       BIGINT  NOT NULL REFERENCES identity.app_user (id) ON DELETE CASCADE
    crew_role_id  BIGINT  NOT NULL REFERENCES identity.crew_role (id) ON DELETE CASCADE
    is_primary    BOOLEAN NOT NULL DEFAULT FALSE
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    UNIQUE (user_id, crew_role_id)
```

`is_primary` preserves the concept of "which dashboard do I land on
first after login" — a user can hold several roles, but exactly one
should be flagged primary to decide the default landing view. (Open
question below on whether this needs a partial unique index to enforce
"at most one primary per user.")

The existing `identity.crew_role` lookup table is untouched — Sparks
and Merchant are just new rows in it, same as Captain/Mechanic/Scribe/
Envoy already are.

`identity.app_user.crew_role` (the old single column) gets dropped
once the join table is populated and everything reads from it instead.
Per existing convention, this is a new numbered migration file, not an
edit to whichever file originally created that column.

### Backfill

Every existing `app_user` with a non-`NULL` `crew_role` gets exactly
one row inserted into `app_user_crew_role` with `is_primary = TRUE`,
carrying their current role forward unchanged. Customer-portal users
(`crew_role IS NULL`) get no row at all — absence from the join table
*is* "no crew role," same meaning as `NULL` had before.

### Code impact

- **Session/auth payload** — wherever `request.state.user` gets built
  at login, `crew_role` (single string) becomes something like
  `crew_roles` (list of role names) plus `primary_crew_role` (single
  string, from the `is_primary` row) if the "land on this dashboard by
  default" behavior is still wanted.
- **`landing.py`** — the current filter:
  ```python
  if user_crew_role == "captain" or user_crew_role is None:
      visible_roles = all_roles
  else:
      visible_roles = [r for r in all_roles if r.get("name") == user_crew_role]
  ```
  becomes a set-membership check:
  ```python
  if "captain" in user_crew_roles or not user_crew_roles:
      visible_roles = all_roles
  else:
      visible_roles = [r for r in all_roles if r.get("name") in user_crew_roles]
  ```
  (Illustrative only — exact shape depends on how the session payload
  ends up structured.)
- **Anywhere else reading `.crew_role` as a scalar** needs an audit —
  this is the part of the refactor most likely to have a missed
  call site, since "single value" reads are easy to sprinkle around
  and easy to forget.

---

## Open questions

1. **Does "primary role" need enforcement at the DB level** (a partial
   unique index ensuring at most one `is_primary = TRUE` row per
   user), or is that better handled as an application-level rule
   enforced in `api.*` when roles are assigned/changed?
2. **Who assigns roles to a user, and how?** Currently role assignment
   isn't self-service — worth deciding whether this becomes a Captain-
   only admin action (a form on the Captain's Configuration tab) as
   part of this refactor, or stays a manual pgAdmin operation for now
   and the UI comes later.
3. **Does Captain's "sees everything" special-case still make sense**
   once roles are combinable, or should Captain become "just another
   role someone can hold, that happens to also grant all-card
   visibility" — functionally the same outcome, but worth being
   explicit that this is a deliberate carve-out rather than an
   accidental side effect of the old equality check.
4. **Test coverage** — `test_routes_crew.py` and related tests
   presumably assert against the old single-role shape; this refactor
   should include updating those, not just the production code path.

---

## Sequencing

This refactor is a prerequisite for both the Sparks (messages) design
and any future Merchant role — neither should be built against the
old single-role model. Recommend landing this first, verified on its
own (existing four roles still work exactly as before, just expressed
through the join table), before Sparks touches it.
