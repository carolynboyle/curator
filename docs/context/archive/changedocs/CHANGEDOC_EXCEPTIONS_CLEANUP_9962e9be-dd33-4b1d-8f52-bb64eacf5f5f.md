# Changedoc: exceptions.py — remove unnecessary pass statements

**File:** `src/curator/exceptions.py`
**Date:** 2026-06-29
**Source verified:** Viewed directly from Carolyn's upload before writing
this changedoc.

## Summary

Pylint flagged three `W0107: Unnecessary pass statement` warnings (one per
class) and one `C0304: Final newline missing`. Both are purely mechanical
— no behavior change. A class body consisting only of a docstring is
already valid Python; the docstring itself satisfies the requirement for a
non-empty class body, making `pass` redundant dead code in each case.

Verified by actually instantiating and raising each exception class after
the edit, and confirming the inheritance chain still works
(`ConfigError`/`DatabaseError` are still catchable as `CuratorError`) —
not just a visual diff.

---

## BEFORE (complete file, as uploaded)

```python
"""Curator exceptions."""


class CuratorError(Exception):
    """Base exception for Curator."""
    pass


class ConfigError(CuratorError):
    """Configuration error."""
    pass


class DatabaseError(CuratorError):
    """Database connection or query error."""
    pass
```

## AFTER (complete file — replace the whole thing with this)

```python
"""Curator exceptions."""


class CuratorError(Exception):
    """Base exception for Curator."""


class ConfigError(CuratorError):
    """Configuration error."""


class DatabaseError(CuratorError):
    """Database connection or query error."""
```

(File ends with a trailing newline after the last line, resolving the
`C0304` warning as well — not visible as a textual diff above, but present
in the actual file.)

---

## Why this is safe

`pass` is a no-op statement that does nothing at runtime. A class with only
a docstring as its body is already complete and valid — the docstring
itself counts as the body. Removing `pass` here changes nothing about how
these exceptions behave: they still inherit correctly, still carry their
docstrings, still raise and catch exactly as before.

## Verification steps

1. Replace the file as shown above.
2. Run `pylint src/curator/exceptions.py` — should show zero warnings.
3. No functional test needed beyond what's already covered by anything
   that imports and raises `ConfigError` or `DatabaseError` elsewhere in
   the codebase (e.g. `config.py`'s `_load_yaml`, which raises
   `ConfigError` on a bad YAML file) — those continue to work unchanged.
