# Deploy checklist

Run this after deploying Curator, in a browser on the live app. Anyone can
follow it, and Claude can too when asked to "run the deploy checklist"
(Claude's built-in browser, or Claude in Chrome).

Record **PR-039** is the reference record. Use it for the checks below.

**Rules for the run**

- Do **not** create new records. There is no way to delete one yet, so a
  test record stays in the ledger. The "New" check only opens the blank
  panel, then you click Exit without saving.
- Any edit to a real record is undone before you move on.
- A document part added for the check is deleted again.

## 1. The app starts

- [ ] `docker compose logs app --tail 60` shows `Application startup complete`
      and no traceback.

## 2. Opening a record (PR-039)

- [ ] The panel opens with three tabs: **Details**, **Notes**, **Documents**.
- [ ] Details shows Record ID, Type, Status and Year on one line, and
      County, State / Province and Country on one line.
- [ ] Display Order is not shown.
- [ ] Details fits without a scrollbar inside the panel.

## 3. Notes tab

- [ ] The text fills the whole panel.
- [ ] There is at most one scrollbar (the text box's own), none nested
      inside another.
- [ ] The text is intact (compare the start and end with the grid's record).

## 4. Documents tab

- [ ] Part 1 is listed with its status chip and links.
- [ ] **+ Add part**: add one labelled `checklist test`; it appears and the
      count goes up by one.
- [ ] Edit its label; the change shows.
- [ ] Delete it; the count returns to what it was.

## 5. Saving updates one row

Before saving, set a filter or sort on the grid and note the scroll position.

- [ ] On Details, add ` (checklist)` to the end of Source Citation and Save.
- [ ] Only that grid row changed; the filter, sort and scroll position are
      unchanged and the grid did not reload.
- [ ] Remove ` (checklist)` and Save again. The record is back to how it was.

## 6. Closing the panel

- [ ] Close the panel (×, Exit, Esc or Alt+X): the hero stays hidden and the grid
      scrolls back to the row you opened it from.

## 7. The New panel

- [ ] Click **New**: the panel shows **Details** and **Notes** only, no
      Documents tab.
- [ ] Click **Exit** without saving.

## 8. Other panels still work

- [ ] Open a project from the Projects dashboard: it still has its Tasks and
      Contacts tabs, and closing it behaves as in step 6.

## Result

Note anything that failed, with the record and what you saw, and attach a
screenshot if you can.
