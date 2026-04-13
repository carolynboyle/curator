# __init__.py

**Path:** src/curator/__init__.py
**Syntax:** python
**Generated:** 2026-04-13 04:51:40

```python
"""
curator - The Curator, a Project Crew member.

Web UI and database interface for the projects database.
Connects to a PostgreSQL instance via dbkit and renders
YAML-driven views via viewkit.

Plugin registration:
    The 'plugin' dict is discovered by Project Crew via the
    'projectcrew.plugins' entry point declared in pyproject.toml.
"""

plugin = {
    "name": "The Curator",
    "version": "0.1.0",
    "description": "Web UI and database interface for the projects database",
    "type": "web",
    "crew_member": "curator",
}
```
