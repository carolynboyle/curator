"""
curator.popups - Dashboard popup definitions from curator.yaml.

A crew role may list floating popups (a bookmarks list, later an admin
settings list) under its entry in ``crew.roles``::

    - name: "seanchai"
      popups:
        - id: "resources"
          label: "Resources"
          type: "links"
          shortcut: "alt+r"
          project: "genealogy-resources"

Only ``id``, ``label`` and ``type`` are required here. Every other key is
passed through untouched for the popup's provider to use (the links
provider reads ``project``; ``shortcut`` is read by the popup shell).
This module only reads and checks the config; what a popup shows and does
lives in static/js/popup-shell.js and its provider modules.
"""

import logging
from typing import Optional

REQUIRED_KEYS = ("id", "label", "type")

_log = logging.getLogger(__name__)


def popups_for_role(role_meta: Optional[dict]) -> list[dict]:
    """Return the valid popup definitions for one crew role.

    Args:
        role_meta: The role's entry from ``crew.roles`` in curator.yaml,
                   or None for a role that isn't configured.

    Returns:
        A list of popup dicts in config order. Entries that are not a
        mapping, miss a required key, or repeat an earlier ``id`` are
        skipped with a warning, so one bad entry never takes the
        dashboard down. Empty when the role has no popups.
    """
    raw = (role_meta or {}).get("popups") or []
    popups: list[dict] = []
    seen: set[str] = set()

    for entry in raw:
        if not isinstance(entry, dict):
            _log.warning("Ignoring popup entry that is not a mapping: %r", entry)
            continue
        missing = [key for key in REQUIRED_KEYS if not entry.get(key)]
        if missing:
            _log.warning("Ignoring popup %r: missing %s", entry, ", ".join(missing))
            continue
        popup_id = str(entry["id"])
        if popup_id in seen:
            _log.warning("Ignoring popup %r: duplicate id", popup_id)
            continue
        seen.add(popup_id)
        popups.append(dict(entry))

    return popups
