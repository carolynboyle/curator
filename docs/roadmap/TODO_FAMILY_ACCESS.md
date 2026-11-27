# Family Access Over the Headscale Mesh

Logged 2026-11-27. Not started. Waits on the Captain role and permissions.

---

## What Carolyn wants

Immediate family can see the parts of Curator she chooses to show them,
reaching it over her headscale mesh (the self-hosted Tailscale-compatible
network Curator is already served on).

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
- A way to choose **what is shared**: per project, per record, or per tab,
  with the default being *not shared*. A clear "shared with family" marker on
  anything visible to them.
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
- Sharing granularity: whole projects, or individual records?
- Should family be able to leave comments or questions on a record?
- Who approves a new family account, and how is one removed?

## Not part of this

- Anything outside the family (collaborators, clients). That is the same
  mechanism later but a different set of decisions.
