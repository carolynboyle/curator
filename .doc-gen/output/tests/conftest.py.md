# conftest.py

**Path:** tests/conftest.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
tests.conftest - Top-level pytest configuration for the Curator test suite.

Loads tests/.env.test so integration tests can reach test_curator on steward
via the floater account. Unit tests do not touch the database and are
unaffected by these variables.

Markers:
    integration — requires steward to be reachable and test_curator to exist.
                  Skipped by default; run with: pytest -m integration
"""

from pathlib import Path

import pytest
from dotenv import load_dotenv


# Load test environment variables before any test collection occurs.
# .env.test sets DBKIT_* to point at test_curator / floater.
load_dotenv(Path(__file__).parent / ".env.test")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: requires steward test_curator database (run with -m integration)",
    )
```
