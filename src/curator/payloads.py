"""
curator.payloads - Helpers for building api.* payloads from a request body.
"""

from typing import Iterable


def sent_fields(body: dict, keys: Iterable[str]) -> dict:
    """Return the listed keys that the request body actually carries.

    Some columns are saved with "a key that is present is set (blank
    clears it); a key that is absent is left alone" semantics, for example
    seanchai.searches.source and search_url (steward 10m). For those, a
    route must not add a key the client never sent, or every save from a
    client that doesn't know the field (such as the grid's inline edit)
    would silently blank it.

    A blank or whitespace-only string is passed on as None, which the proc
    treats as "clear".

    Args:
        body: The decoded JSON request body.
        keys: Field names to look for.

    Returns:
        A dict with only the keys found in body, in the order given.
    """
    fields = {}
    for key in keys:
        if key not in body:
            continue
        value = body[key]
        if isinstance(value, str):
            value = value.strip()
        fields[key] = value or None
    return fields
