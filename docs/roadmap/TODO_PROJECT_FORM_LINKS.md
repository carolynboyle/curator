# Project Form — Links List and Layout

Logged 2026-11-25 while setting up the "Genealogy Resources" project for the
Resources popup. Not started; deliberately vague. Needs a short design
conversation before any code.

---

## What was observed

Adding links to a project's Links widget gave no visible sign that anything
had saved. The list of saved links sits at the bottom of the Details tab, below
the fold of the panel's scroll area, so it only showed up after scrolling down.
By then the same link (Ancestry) had been entered five times.

The edit area has the same problem in a smaller way: in the panel the Links
edit row's Save and Cancel buttons are partly cut off at the bottom edge.

## Likely contributing causes (not yet confirmed by reproducing)

- The list is off-screen after a save, so nothing confirms the save.
- After Save the widget reloads the list and returns to the search box, which
  is correct but invisible if the list is not on screen.
- Nothing stops a link with the same label and URL from being added again.
- The project Details form is long (Name, Description, Type, Status, Crew,
  then Links), so Links is always at or past the bottom.

## What Carolyn wants

A links listbox that is **always on the form, even when empty**, and is
refreshed every time a link is saved, so a save is visible straight away.

The same list is then the thing the dashboard Resources popup shows (see
`popup-links.js`). The popup already reads the same `projects.project_links`
rows, so the two stay consistent without extra plumbing.

## Ideas to weigh when this is picked up

- Where the list lives: a Links tab of its own (the tab bar already has
  Details, Tasks and Contacts; the template notes say a Links tab was planned),
  or a fixed section on Details that never scrolls out of view.
- Visible confirmation on save, such as the new row highlighted briefly, so a
  repeated click is less likely.
- A duplicate check (same label and URL on the same project): warn or refuse.
- Whether the list and the popup should share one small component (the render
  and filter code is now written twice: `project-links.js` and the links
  provider in the popup).
- Tidy the rest of the project Details form at the same time. Carolyn has said
  the project form needs refining generally; this is the natural moment.

## Not part of this

- Permissions on who may edit links. That waits for the Captain role work.
- Changes to the popup itself. It already works from whatever links the
  project has.
