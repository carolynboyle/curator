# Design Doc — Messages Schema ("The Sparks")

**Status:** Design only. Assumes the multi-role identity refactor
(see `DESIGN_MULTI_ROLE_IDENTITY.md`) is already in place — Sparks is
built as an *additive* crew role from day one, not bolted onto the old
single-role model.

**Naming:** Schema and tables use plain functional nouns (`messages`),
consistent with `identity`/`projects`/`audit`. "The Sparks" is the
crew-role display name and landing-card label only — same layer as
Captain/Mechanic/Envoy/Scribe, not the schema name. This keeps the
`/crew/{entity}/...` route convention and schema-naming convention
both intact; theming stays confined to the display layer as already
decided for the future crew-terminology work.

---

## Schema

### `messages.notification_level` (lookup table)

```
id         BIGINT PK
name       VARCHAR(50) UNIQUE   -- e.g. 'silent', 'normal', 'urgent'
rings_bell BOOLEAN              -- whether this level fires pg_notify at all
```

Values span from "do nothing" (recorded in the message center, no
outbound ping) up through "ring all the alarm bells" (immediate
Apprise dispatch). `rings_bell` is the flag `api.create_message()`
checks to decide whether to call `pg_notify` at all — every message
gets a row regardless of level; only some levels also trigger a push.

Open question carried over from the failure-modes discussion: should
certain sources (e.g. anything tagged `source = 'audit'`) have a
floor — a minimum notification level that can't be configured below —
so a security event can never be silently downgraded to "do nothing"
by a lookup-table edit? If so, that constraint lives in
`api.create_message()`'s logic, not in the lookup table itself, which
just holds the available levels.

### `messages.messages`

```
id               BIGINT PK
recipient_id     BIGINT NOT NULL REFERENCES identity.app_user (id)
sender_label     TEXT              -- not an FK; external senders
                                    -- ("audit trigger", "customer
                                    -- question form") aren't app_users
subject          TEXT NOT NULL
body             TEXT
source           VARCHAR(50)       -- 'audit', 'customer_question',
                                    -- 'inbound_email', etc.
notification_level_id  BIGINT NOT NULL REFERENCES messages.notification_level (id)
read_at          TIMESTAMPTZ       -- NULL = unread
created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

`recipient_id` is always the actual authenticated `app_user` — never
a client-supplied value trusted at read time (see `api.*` functions
below).

### `messages.v_message_detail`

Whitelisted view for the detail panel, following the existing
`v_*_detail` convention — `id` and `*_by`-style columns excluded,
column order matches intended field order. Realistically the only
"editable" field here is `read_at` (marking read), so this view is
mostly for display, not a general-purpose edit form.

---

## `api.*` functions

- **`api.create_message(payload JSONB)`** — the single write path
  every producer (audit trigger, customer-question handler, future
  inbound-email Worker) calls. Inserts the row; if the resolved
  `notification_level.rings_bell` is true, calls `pg_notify('new_message',
  ...)` with enough payload for the listener to act without a second
  query. This is where "was created" and "should notify" are decided
  together, at the database layer — no producer needs to know Apprise
  exists.
- **`api.get_messages_for_user(p_user_id BIGINT)`** — returns every
  message where `recipient_id = p_user_id`. `p_user_id` comes from the
  authenticated session, never trusted as a raw client parameter, same
  defensive posture as the rest of `api.*`.
- **`api.mark_message_read(p_message_id BIGINT, p_user_id BIGINT)`** —
  sets `read_at`, but only after confirming the message actually
  belongs to `p_user_id`. Returns `NULL`/an error shape if it doesn't,
  rather than silently succeeding on someone else's message.

All three follow the existing `06d_api_grants.sql` pattern —
`web_app_user` gets `EXECUTE`, nothing else; no direct table/view
grants, consistent with the rest of `api.*`.

---

## Landing card / role tie-in

- Sparks becomes a row in `identity.crew_role`, assignable via the
  (now multi-valued) `identity.app_user_crew_role` join table, same as
  any other role.
- A user holding Sparks gets a "Sparks" card on their landing page
  (via the existing `identity.landing_card`-style mechanism, or
  whatever the landing-card design lands on), routing to a new
  `/crew/messages/...` or similar path — the panel shows
  `api.get_messages_for_user()` results, most-recent first, unread
  visually distinct.
- Mesh + login gating is inherited for free from Curator's existing
  auth — no new access-control code needed here specifically, per the
  "reuse, don't rebuild" conclusion reached earlier.

---

## Open questions

1. **Does marking a message read need to be undoable** (mark unread
   again), or is `read_at` a one-way flag?
2. **Retention** — do old, read messages ever get purged/archived, or
   does this table grow forever? Not urgent at low volume, but worth a
   stated answer rather than an implicit "we'll deal with it later."
3. **Does every crew member with Sparks see *all* messages addressed
   to them regardless of source**, or does Sparks itself need
   sub-filtering (e.g. Felipe only sees `customer_question` and
   `inbound_email` messages, not internal audit alerts meant for you)?
   This may push `recipient_id` scoping to need a `source` allowlist
   per user, which isn't in the schema above yet.
4. **Notification-level floor enforcement** (carried over from
   above) — decide before `create_message()` is written, since it
   changes the function's logic, not just its schema.
