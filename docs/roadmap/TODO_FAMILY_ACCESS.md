# Family Access Over the Headscale Mesh

Logged 2026-11-27. Not started. Waits on the Captain role and permissions.

---

## What Carolyn wants

Immediate family can see the parts of Curator she chooses to show them,
reaching it over her headscale mesh (the self-hosted Tailscale-compatible
network Curator is already served on).

## Carolyn's design (2026-11-27)

A user is someone in the contacts table, and what a user may do is controlled
by the Captain. So a family member such as her sister Maureen is a contact
(role: sister) who is given a login as a **Seanchaí guest**: a role the Captain
defines as **read-only, with access to pertinent records** only.

What the database already has: `identity.app_user.contact_id` is required and
unique (a user *is* a contact); `user_role` (admin / staff / customer) is the
permission tier and `crew_role` (captain, envoy, mechanic, scribe, seanchai) is
the persona, extensible from the Captain's UI. A guest could be a new value in
either. Decision for the design conversation: new crew role, new tier, or both.

What is missing (the real work): a table saying what each role may do,
enforcement on every save/delete route and database function (including
passing the signed-in user to them), and a "shared" marker saying which
records or projects a guest may see (default: not shared). See also
`TODO_LEAST_PRIVILEGE_DB_USER.md`.

### Clarification (Carolyn, 2026-11-27, later): the role decides, not each record

The guest's world is defined by the **role**, not by marking individual
records. A Seanchaí guest:

- sees **only the Seanchaí card** on the landing page (nothing else listed);
- does **not see the Contacts tab** on forms that have one;
- has **read-only** access throughout Seanchaí;
- will also see the polished pages once they are ported into Curator: the
  **Seanchaí Register** (people and places, timeline, relationships) and the
  **Boyle Family Tree** that exist today as Claude artifacts.

This replaces the per-record "shared" marker described below as the default
mechanism; a per-record flag stays an option for later if some records ever
need to be held back.

Implementation notes: the landing card list is already configurable per role
(`CONFIGURABLE_LANDING_CARDS_DESIGN.md`), and hiding a tab is a role-aware
template decision. **Hiding is not blocking**: the guest being unable to
change anything must be enforced on the server (save and delete routes and
database functions), not only by hiding buttons.

### Multiple roles and per-person limits (Carolyn, 2026-11-27)

- A user can hold **more than one role**: for example a writing partner given
  the Scribe role, who might also be a Seanchaí guest. This needs the
  multi-role change already designed in `DESIGN_MULTI_ROLE_IDENTITY.md`
  (a join table replacing the single `crew_role_id` on `identity.app_user`,
  with one role marked primary). **Not built yet**: today a user has one crew
  role.
- **Limiting which Scribe records a user sees.** Roles already map to project
  types (`projects.project_type_role_mapping`; the Scribe view shows only
  projects of types mapped to Scribe), which limits things per role. A
  per-person limit would be a second layer: a per-user list of allowed project
  types that narrows what the role would otherwise show. Decide when the
  Captain permissions work starts whether this belongs in the same table as
  the role-to-type mapping or in its own.

## Two separate questions

1. **Can their device reach Curator?** That is the mesh: a family member's
   device joins the headscale network and gets an address in it.
2. **What may they do once there?** That is Curator's own sign-in and
   permissions. Being on the mesh answers only the first question.

## Important: do this in order

Curator has user accounts, roles and sessions, but **no enforcement of what a
role may see or change yet** (deferred to the Captain role work). Until that
exists, anyone who can reach Curator and sign in could see everything. So:

- Do **not** add family devices to the mesh with access to Curator until
  permissions are enforced on the server, or limit them with headscale
  access rules (ACLs) to something that is not the full app.
- The Captain-role permissions work comes first. This item builds on it.

## What would be needed in Curator

- A **family role** (read-only to start), with its own dashboard.
- Role-wide visibility as described in the clarification above (landing card,
  tabs hidden, read-only). A per-record "shared" flag is optional and later.
- **Read-only views** first (the research ledger, the memoir progress, family
  tree pages); letting family add notes or corrections could come later.
- Family members as **contacts** (see `TODO_PROJECT_CONTACTS_CRM.md`) linked
  to a Curator user account, so a person and their login are one thing.
- Care with **living people**: details about living relatives should not be
  shared by default.

## What would be needed on the mesh

- Decide how family devices join (pre-auth keys, one per person, expiring).
- Headscale ACLs so a family device can reach only Curator's family-facing
  address, not the rest of the network (homelab hosts, Proxmox and so on).
- Possibly a second Curator listener or hostname for family traffic, so the
  split can be enforced in the network as well as in the app.

## Questions for the design conversation

- Does family see the same Curator with fewer things showing, or a separate,
  simpler front page?
- Should family be able to leave comments or questions on a record?
- Who approves a new family account, and how is one removed?

## Not part of this

- Anything outside the family (collaborators, clients). That is the same
  mechanism later but a different set of decisions.
