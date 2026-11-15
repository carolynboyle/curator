# Curator

Containerized web interface for the steward PostgreSQL project database.

## Testing

```
scripts/check.sh
```

Runs Pylint (errors) and the unit tests in Docker; GitHub Actions runs the
same thing on every push. Details, and how to run just part of it, are in
[tests/README.md](tests/README.md). After a deploy, work through
[tests/DEPLOY_CHECKLIST.md](tests/DEPLOY_CHECKLIST.md).
