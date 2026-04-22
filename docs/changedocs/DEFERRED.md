# Curator — Deferred Cleanup Items

Items logged here are known issues or improvements that are intentionally
postponed until the UI and routes are stable. No point fixing or documenting
a moving target.

---

## Code Quality

- [ ] Add docstrings to all route functions in `projects.py`
- [ ] Audit `tasks.py`, `files.py`, `tags.py` for missing docstrings and add them
- [ ] Clear Pylance linter warnings across route files:
      - Unused variables
      - Missing type annotations
      - Any remaining syntax/style warnings
- [ ] Do this pass *after* UI is stable and all routes are in final form

---

## Notes

- Linter warnings as of 2026-04-21 are non-breaking — unused imports and missing
  docstrings only. No functional impact.
