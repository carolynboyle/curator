"""
curator.list_edit - List-and-edit tab definitions from curator.yaml.

A detail panel can carry tabs that show a searchable list of child items on
the left and an edit form on the right (a record's Documents, a project's
Links). Each tab is described under ``list_edit_tabs`` in curator.yaml,
keyed by the entity whose panel shows it::

    list_edit_tabs:
      projects:
        - id: "links"
          label: "Links"
          noun: "link"
          parent_key: "project_id"
          list_url: "/api/query/project_links/for_project?params={parent_id}"
          save_new_url: "/crew/project_links/save"
          save_url: "/crew/project_links/{id}/save"
          delete_url: "/crew/project_links/{id}"
          title_field: "label"
          search_fields: ["label", "url"]
          empty_text: "No links yet. Use New to add one."
          fields:
            - {name: "label", label: "Label", control: "text", required: true}
            - {name: "url", label: "URL", control: "text", open: "url"}

This module only reads, checks and resolves the config; the generic widget
lives in static/js/list-edit-widget.js and the markup in
templates/partials/_list_edit_widget.html. Two values may point at other
parts of the config instead of repeating them, using a dotted
``section.key`` name:

    options_from   on a select field: the list of choices
    repo_base_from on a tab: the base URL that fields with ``open: "repo"``
                   join their path onto

Anything wrong with one tab (missing key, duplicate id, unknown control)
skips that tab with a warning, so one bad entry never takes a panel down.
"""

import logging
from typing import Any, Callable, Optional

REQUIRED_TAB_KEYS = (
    "id", "label", "noun", "parent_key", "list_url", "save_new_url",
    "save_url", "delete_url", "title_field", "fields",
)
REQUIRED_FIELD_KEYS = ("name", "label", "control")
CONTROLS = ("text", "select")
OPEN_KINDS = ("url", "repo")

_log = logging.getLogger(__name__)


def _choices(values: Any) -> list[dict]:
    """Turn a list of plain values into select choices with readable labels."""
    return [{"value": str(v), "label": str(v).replace("_", " ")} for v in values]


def _resolve_field(field: Any, lookup: Callable[[str], Any]) -> Optional[dict]:
    """Return a checked copy of one field definition, or None to reject it."""
    if not isinstance(field, dict):
        return None
    if any(not field.get(key) for key in REQUIRED_FIELD_KEYS):
        return None
    if field["control"] not in CONTROLS:
        return None
    if field.get("open") and field["open"] not in OPEN_KINDS:
        return None

    resolved = dict(field)
    if field["control"] == "select":
        values = field.get("options")
        if field.get("options_from"):
            values = lookup(field["options_from"])
        if not values:
            return None
        resolved["options"] = _choices(values)
    return resolved


def _resolve_tab(tab: Any, lookup: Callable[[str], Any]) -> Optional[dict]:
    """Return a checked, resolved copy of one tab definition, or None."""
    if not isinstance(tab, dict):
        _log.warning("Ignoring list-edit tab that is not a mapping: %r", tab)
        return None
    missing = [key for key in REQUIRED_TAB_KEYS if not tab.get(key)]
    if missing:
        _log.warning("Ignoring list-edit tab %r: missing %s", tab.get("id"), ", ".join(missing))
        return None

    fields = [_resolve_field(f, lookup) for f in tab["fields"]]
    if not all(fields):
        _log.warning("Ignoring list-edit tab %r: a field is invalid", tab["id"])
        return None
    names = [f["name"] for f in fields]
    if len(set(names)) != len(names):
        _log.warning("Ignoring list-edit tab %r: duplicate field names", tab["id"])
        return None

    for key in ("require_one_of", "duplicate_of", "search_fields"):
        unknown = [n for n in _names_in(tab.get(key)) if n not in names and n != tab["title_field"]]
        if unknown:
            _log.warning("Ignoring list-edit tab %r: %s names unknown fields %s",
                         tab["id"], key, ", ".join(unknown))
            return None

    resolved = dict(tab)
    resolved["fields"] = fields
    resolved["repo_base"] = str(lookup(tab["repo_base_from"]) or "") if tab.get("repo_base_from") else ""
    return resolved


def _names_in(value: Any) -> list[str]:
    """Field names referenced by a search/duplicate list or a require_one_of block."""
    if isinstance(value, dict):
        value = value.get("fields")
    return [str(n) for n in value] if isinstance(value, (list, tuple)) else []


def list_edit_tabs_for(
    entity: str,
    tabs_config: Optional[dict],
    lookup: Callable[[str], Any],
) -> list[dict]:
    """Return the valid list-edit tab definitions for one entity.

    Args:
        entity:       The entity whose panel is being drawn (projects, records).
        tabs_config:  The ``list_edit_tabs`` section of curator.yaml.
        lookup:       Resolves a dotted ``section.key`` name from the rest of
                      the config, for ``options_from`` and ``repo_base_from``.

    Returns:
        Resolved tab dicts in config order; empty when the entity has none.
        Tabs that are invalid, or repeat an earlier ``id``, are skipped with
        a warning.
    """
    raw = (tabs_config or {}).get(entity) or []
    tabs: list[dict] = []
    seen: set[str] = set()
    for entry in raw:
        tab = _resolve_tab(entry, lookup)
        if tab is None:
            continue
        if tab["id"] in seen:
            _log.warning("Ignoring list-edit tab %r: duplicate id", tab["id"])
            continue
        seen.add(tab["id"])
        tabs.append(tab)
    return tabs
