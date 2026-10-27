# Navigation Redirect Fixes

**Date:** April 2026  
**Status:** Resolved

---

## Problem

After adding a file from the board panel, the user was redirected to
`/projects/{slug}` (the old standalone project detail page) instead of
back to `/projects/board`. The Cancel button on the file form also did
nothing (empty `href`).

Both problems had the same root cause: `next_url` was not reaching the
file form template, so the hidden field and the Cancel link both rendered
empty.

---

## Root Cause

In `_panel.html`, the "+ Add" link for files was:

```html
<a href="/files/new?project_id={{ project.id }}&next_url=/projects/board">
```

The unescaped `&` in the HTML attribute caused browsers to misparsed the
query string. `project_id` arrived correctly but `next_url` was silently
dropped. The GET handler's referer fallback also failed because the panel
is loaded via HTMX (XHR), so no useful `Referer` header is sent when the
user clicks the link.

With `next_url` empty, the POST handler fell through to the `project_slug`
branch and redirected to `/projects/{slug}`.

---

## Fix

One character change in `_panel.html` line 176 — `&` → `&amp;`:

```html
<a href="/files/new?project_id={{ project.id }}&amp;next_url=/projects/board">
```

---

## Contributing Factor: Browser Cache

After applying the fix, behaviour appeared unchanged at first because
Falkon was serving the old `_panel.html` from cache. A hard refresh
(Ctrl+Shift+R) cleared it and confirmed the fix was working.

---

## Development Workflow Fix

Uvicorn was being started without `--reload`:

```bash
uvicorn curator.web.app:app --host localhost --port 8080
```

Without `--reload`, code changes to route files are not picked up until
uvicorn is manually restarted. This also contributed to the confusion
during debugging (a debug `print` statement did not appear in server
output because the old code was still running).

Updated `go.sh` to add `--reload`:

```bash
uvicorn curator.web.app:app --host localhost --port 8080 --reload
```

A companion `stop.sh` was also added:

```bash
#!/bin/bash
if pkill -f "uvicorn curator.web.app:app"; then
    echo "Curator stopped."
else
    echo "Curator was not running."
fi
```

---

## Lesson

Ampersands in HTML attributes must always be written as `&amp;`. An
unescaped `&` in an `href` is technically invalid HTML and browsers may
silently drop query parameters that follow it. This is especially hard
to debug when the first parameter arrives correctly and only subsequent
ones are lost.
