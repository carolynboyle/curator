# Design Doc — Message Center ↔ Notification Hub Interaction

**Status:** Design only. Covers how the Messages schema (persistent,
mesh-gated, queryable) and Apprise (stateless, one-directional
dispatcher) fit together, plus the failure modes this design needs to
account for.

---

## Core distinction

Apprise is not a message store and has no memory of past calls — it
receives "send this notification" and dispatches outward (Telegram,
email, SMS). It never gets queried later for history. The **message
center** (the `messages` schema from `DESIGN_MESSAGES_SCHEMA_SPARKS.md`)
is the durable, retrievable record; Apprise is the side-effect that
pings a phone.

Not every event needs both halves. Producers split into two
categories:

**Category 1 — persisted + notified.** Customer questions, audit-trail
alerts, inbound email — anything someone should be able to log into
Curator later and review. These write through `api.create_message()`,
which conditionally fires `pg_notify` based on the message's
notification level.

**Category 2 — fire-and-forget, no persistence.** Ephemeral
infrastructure pings (disk usage, a failed systemd unit) with no
lasting value in a "read again later" sense. These call Apprise
directly — no `messages` schema involvement.

```
Category 1 producers                Category 2 producers
(audit trigger, customer form,       (disk check, systemd watcher,
 inbound-email Worker)                anything ephemeral)
        │                                    │
        ▼                                    │
  api.create_message()                       │
   (INSERT + conditional pg_notify)          │
        │                                    │
        ▼                                    │
  Python LISTEN process                      │
        │                                    │
        └──────────────┬─────────────────────┘
                        ▼
                 Apprise REST API
                  (tag-based routing)
                        │
                        ▼
           Telegram / Email / SMS, per tag config
```

---

## Failure modes and mitigations

### 1. Silent notification loss at the LISTEN boundary
`pg_notify` is fire-and-forget, not a queue — if the listener isn't
connected at the exact moment `NOTIFY` fires (restart, blip, Postgres
bounce), that signal is gone permanently. The message row is safe
(durable INSERT); the "tell someone" signal is not.

*Mitigation:* `Restart=always` on the listener's systemd unit shrinks
the vulnerable window but doesn't close it. Closing it needs a second,
independent mechanism — a systemd *timer* unit running a periodic
sweep of `messages.messages` for rows above the notification floor
with no recorded "notification sent" confirmation, re-firing those.
This requires `create_message()`/the listener to actually record
successful dispatch somewhere (a `notified_at` column, or similar) so
the sweep knows what still needs sending.

### 2. Silent misconfiguration in `notification_level`
No crash, no error — a level gets set wrong (or a producer passes the
wrong id) and something important is quietly treated as low-priority.

*Mitigation:* a floor on certain sources (e.g. `source = 'audit'`
can't resolve below a minimum level) enforced in `create_message()`'s
logic, not just left to lookup-table content. Carried over from the
Messages schema doc as an open decision.

### 3. Dispatch failure that never surfaces
The listener calls Apprise; Apprise's own call to Telegram/SMTP/SMS
can fail (expired token, SMTP auth lapsed, rate limit) with nothing in
the chain checking or surfacing that failure.

*Mitigation:* the listener treats an Apprise failure response as its
own failure (non-zero exit, not log-and-continue), so systemd's
`OnFailure=` can chain to a separate escalation unit — one that
notifies through an independent path, ideally not routed through
Apprise itself, so an Apprise-specific outage doesn't also silence its
own failure alert. journald captures the crash/restart trail for
after-the-fact forensics regardless.

### 4. Alert storms / lack of aggregation
A real incident (repeated failed logins) could fire the trigger
hundreds of times in a burst, each independently notifying — a wall of
pings instead of one useful summary.

*Mitigation:* debouncing/aggregation decided at the trigger or listener
level (don't re-fire for the same pattern within N minutes) — this is
an application-logic decision, not something infrastructure solves.
Left as an explicit open question for whoever writes the audit
trigger, not silently deferred.

### 5. Partial availability — notified but unreachable
The listener and Apprise don't depend on Curator's web process at all,
so someone can be pinged "you have a message" while Curator itself is
down (deploy, crash, reboot) and have nowhere to actually read it yet.

*Mitigation:* not a bug to fix so much as a known gap to document —
notify-success doesn't imply read-access-success. `Restart=always` on
Curator's own unit shrinks the downtime window but doesn't eliminate
it.

### 6. Drift between producers and the `create_message()` contract
Same class of problem already seen elsewhere in this project (the
`steward` repo's on-disk SQL drifting from what's live in `wcyj`). If
`create_message()`'s signature or the `notification_level` values
change, a producer not updated in lockstep can silently pass a
malformed or stale payload.

*Mitigation:* no systemd or infrastructure fix applies here — this is
a coordination/versioning discipline problem, addressed the same way
the project already addresses SQL drift: confirm live behavior before
assuming producers match the current contract, rather than trusting
that everything was updated together.

---

## What systemd can and can't do here

Useful for: **1** (partially — narrows the window, doesn't close it),
**3** (meaningfully — `OnFailure=` gives a real escalation path), **5**
(partially — faster recovery, not elimination).

No help for: **2**, **4**, **6** — these are logic/configuration/
coordination failures, not process-liveness failures, and systemd has
no visibility into any of them.

`StartLimitIntervalSec=`/`StartLimitBurst=` on the listener's unit is
worth setting regardless, so a genuine crash-loop doesn't also become
an alert-loop — and systemd giving up entirely after repeated restart
failures is arguably the one state that most deserves its own loud,
one-time notification, since that's also the point where the
reconciliation sweep (mitigation for #1) has likely stopped running
too.

---

## Open questions

1. Where does "notification sent" get recorded — a column on
   `messages.messages`, or a separate log table? Needed either way for
   the reconciliation sweep in #1 to function.
2. Does the independent fallback channel for #3 exist yet, or is this
   the point where a second, Apprise-independent notification path
   (e.g. a carrier SMS gateway hit directly) gets scoped as its own
   small piece of work?
3. Debouncing logic for #4 — trigger-level (Postgres) or listener-level
   (Python)? Affects where the "have I already alerted on this pattern
   recently" state lives.
