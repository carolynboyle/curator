# Testing Curator

Run the checks (needs only Docker):

```
scripts/check.sh
```

That runs **Pylint (errors only)** and then **all unit tests**, inside a
container built from this repo's `Dockerfile`. It is exactly what GitHub
Actions runs on every push (`.github/workflows/tests.yml`), so a green run
here and a green run on GitHub mean the same thing.

The first run builds the test image (a minute or two: it installs the
dependencies, including `dbkit` and `viewkit` from GitHub). After that it
starts in seconds. `src/` and `tests/` are mounted into the container, so
code edits need no rebuild; rebuild happens automatically when
`pyproject.toml` or the `Dockerfile` change.

## Running part of it

Anything after `scripts/check.sh` runs in the test image instead of the
default checks:

```
scripts/check.sh pytest tests/unit/test_fieldkit.py     # one file
scripts/check.sh pytest -k tab                          # tests matching a name
scripts/check.sh pylint --errors-only src/curator       # lint only
```

## The layers

| Layer | What it covers | Needs | Run it |
|---|---|---|---|
| **Unit** (`tests/unit/`) | Logic and template rendering, with the database mocked | Docker only | `scripts/check.sh` |
| **Integration** (`tests/integration/`) | Round trips against the live `wcyj` database. None written yet. | The steward database | `scripts/check.sh pytest -m integration` |
| **Deploy checklist** ([DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)) | The real app in a browser, after a deploy | A deployed Curator | Follow the file, by hand or with Claude's browser |

Plain `pytest` skips integration tests (`addopts` in `pyproject.toml`); you
ask for them on purpose.

## Adding tests

- Tests mirror `src/`: `src/curator/web/fieldkit.py` is tested in
  `tests/unit/test_fieldkit.py`.
- Mock the database and anything outside the process; unit tests must not
  need a network or a running Postgres.
- Template markup is tested by rendering the template with Jinja and
  checking the HTML (see `tests/unit/test_detail_panel_template.py`).
- New functionality is not done until it has tests and the checks pass
  (project_rules.md).

## If something fails

- **Pylint reports errors**: fix them; the run stops before the tests.
  Only errors fail the build, not style warnings (`--errors-only`).
- **The build fails fetching `dbkit` / `viewkit`**: they are installed from
  the dev-utils repo on GitHub; the machine (or the GitHub runner) must be
  able to read it.
- **Stale results after changing dependencies**:
  `docker compose build --no-cache test`.
