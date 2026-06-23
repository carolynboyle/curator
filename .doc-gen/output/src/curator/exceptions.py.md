# exceptions.py

**Path:** src/curator/exceptions.py
**Syntax:** python
**Generated:** 2026-06-23 12:09:21

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
