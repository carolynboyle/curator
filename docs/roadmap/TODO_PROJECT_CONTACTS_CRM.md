# Project Contacts Tab — CRM-Style Outreach Tracking

Logged 2026-11-27. Not started. Needs a design conversation first.
The tab's "coming soon" placeholder stays until this is built (Carolyn, 2026-11-27).

---

## What was observed

The Contacts tab on a project's panel is only a placeholder ("Contacts —
coming soon"). Carolyn wondered whether the placeholder was even necessary,
then realised the tab is exactly where something valuable belongs.

## The use case that prompted it

Her ancestors appear in at least a dozen other people's family trees. Some of
those tree owners have well-documented trees and would be worth contacting.
Nobody has answered her messages on Ancestry so far, but she once tracked down
one tree-builder to a place in Iowa and cannot now remember how she did it.
The system should have kept that trail.

So the tab needs to work like a CRM sales pipeline, for people instead of
customers: who they are, how you found them, what you've tried, and what
happens next.

## What a CRM-style Contacts tab would hold

- **The people attached to the project**, each with a role (tree owner,
  relative, archivist) and a **status**: not contacted, contacted, replied,
  no response, dead end, and so on. The status names should live in YAML so
  they can be changed.
- **An interaction log per person**: date, channel (Ancestry message, email,
  phone, letter), direction (sent / received), a short summary, and the
  message text if wanted. Several per person, newest first.
- **Next follow-up date**, so a "no response yet" does not get forgotten.
- **How they were found**: the trail that led to them (the tree's URL, the
  search that surfaced it, a note such as "found via Iowa county page"). This
  is the part Carolyn could not reconstruct from memory.
- **Where they are online**: profile and tree URLs and usernames. Many
  contacts will have no email, only an Ancestry username.
- **Immediate family as well as outreach contacts** (added 2026-11-27). Family
  members are contacts too, with a role such as sibling or parent, so the same
  tab holds the people you are researching with and the people you are
  contacting. See `TODO_FAMILY_ACCESS.md` for letting them see parts of
  Curator.
- **What they connect to**: which tree, and ideally which people or records in
  the research they are relevant to.

## What already exists

- `projects.project_contacts` links a project to a contact, with a role, an
  `is_primary` flag and notes (steward `03_projects.sql`).
- `identity.contacts` plus emails, phones and URLs (`contact_urls`) already
  store the person and their details.
- Missing: a status, a next-follow-up date, a "how found" field, and a table
  for the interaction log.

## Ways to build it (to weigh later)

- The interaction log is a list with an edit form, so the shared list-and-edit
  widget (`docs/design/list_edit_widget_design.md`) could draw it from a
  definition in `curator.yaml` with little new code.
- The tab itself is a list of attached contacts with fields beside it, and the
  interaction log would sit under the selected contact. That is the nested
  master-detail pattern in `docs/design/nested_master_detail_design.md`.
- Add columns to `project_contacts` for status, next follow-up and how found,
  and a new `project_contact_interactions` table.
- The same tab would suit business projects (sales leads, clients), so build it
  generally rather than for genealogy only.

## Questions for the design conversation

- Should the pipeline stages be the same for every project type, or set per
  project type?
- Is the interaction log kept only here, or should a contact's history also be
  visible on the contact's own panel (across projects)?
- How much of a message to store: a summary, or the full text?
- This is personal information about private people. Curator should store only
  what Carolyn records herself, and nothing is fetched or scraped.

## Not part of this

- Sending email or messages from Curator, or reading replies automatically.
- Permissions on who may see or edit contacts (waits for the Captain role).
