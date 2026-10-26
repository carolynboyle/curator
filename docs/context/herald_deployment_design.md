# Herald Deployment & Failover — Design Notes

**Date:** 2026-07-11
**Status:** Decided in discussion, not yet built. No code or containers exist for this yet.

---

## Context

This captures a planning conversation that started from a pasted Gemini chat about
multi-container Docker setups, and ended up clarifying the actual node topology
Curator needs to support once Felipe starts using it.

---

## Node Roles

| Node | Purpose | Who reaches it |
|---|---|---|
| **Dev machine (wcyjv20)** | Active development, `localhost:8080` | Carolyn only |
| **wcyj-meet (Hetzner VPS)** | Most durable host — target for Postgres primary and Carolyn's main Curator instance | Carolyn only |
| **steward** | Postgres standby (per 6/18 replication plan); also hosts **herald's failover** | Carolyn only |
| **herald (LXC, not yet provisioned)** | Felipe's *only* reachable node, enforced by Headscale ACL | Felipe only |

---

## Why Herald Is Its Own Node, Not Just a Role

Felipe's Headscale identity is ACL-limited to reach herald and nothing else. That means
the Curator instance he uses must physically run **on herald** — there's nothing to
proxy through if he can't reach any other node. Herald is a deployment target, not just
a permissions label.

Two independent security boundaries protect refurb data, and neither substitutes for
the other:

1. **Headscale ACL** — stops Felipe from reaching any node except herald.
2. **Postgres `refurb` role** (already roadmapped) — stops Felipe from seeing anything
   but refurb records, even from inside herald.

This is the same "polite API calls" philosophy already applied to `web_app_user` having
no direct table access — extended from the app layer down to the per-person layer.

---

## Same Image, Multiple Deployments

Docker's value here isn't primarily network isolation — Curator and Postgres already
live on separate physical/VM hosts on the mesh, which is stronger isolation than a
single-host Docker bridge network gives you. The real value is **deploy portability**:
the same Curator image needs to run in at least three places with three different
configs.

| Deployment | Postgres role | Notes |
|---|---|---|
| Dev machine | `steward` (full access) | Current state |
| wcyj-meet | `steward` (full access) | Carolyn's main instance, future |
| herald | `refurb` (scoped) | Felipe's instance |
| steward (failover) | `refurb` (scoped) | Herald's failover, idle/cold until needed |

This maps directly onto the existing "same container, multiple deployments" decision
from the 2026-06-18 session, and onto what `curator_init.py` was already scoped to do:
write `config.yaml` / `.pgpass` / `.env` per node, role-aware, ending in a live DB
connection check. Herald and its failover just become two more targets for that same
script.

---

## Herald's Failover: Why Steward, Not wcyj-meet

The instinct to put herald's failover on wcyj-meet (the most durable box) doesn't hold
up once you look at what's already slated to live there: Postgres primary, and
Carolyn's own main Curator instance. Stacking herald's failover there too means a
single wcyj-meet outage takes out the DB primary, Carolyn's app, *and* Felipe's fallback
door simultaneously — the opposite of redundancy.

**Steward** is the better home:

- Already slated as the Postgres standby — it's specifically the node meant to survive
  a wcyj-meet outage.
- Already has local DB access, minimizing network hops during a failover scenario.
- One outage triggers one coordinated response (promote Postgres standby + herald
  failover together) instead of two independent redundancy plans that have to both
  happen to survive.

---

## Failover Philosophy: Manual, Not Automatic

Consistent with the existing decision to skip Patroni/repmgr for Postgres — no
automatic health-check-and-switch machinery here either. A cold or warm Curator
container on steward, started manually (or already idle) when needed, plus a manual
heads-up to Felipe with the new address.

**Important ACL constraint:** Felipe's Headscale ACL must include steward's
failover address *before* it's ever needed. It can't be granted reactively while
he's locked out and trying to reach you — the fallback door has to already be on
his approved list, sitting unused until it's needed.

---

## Open / Not Yet Decided

- Herald has not been provisioned yet (LXC doesn't exist).
- `refurb` Postgres role has not been created yet (roadmapped, not built).
- `curator_init.py` has not been written yet — currently just a design intent.
- Whether herald's failover container runs cold (start on demand) or warm (always
  running, idle) is not yet decided.
- Container definitions for `containers/herald/` (or reuse of `containers/curator/`
  with a different env) not yet designed.
