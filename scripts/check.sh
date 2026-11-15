#!/usr/bin/env bash
# check.sh — run Curator's lint and unit tests in Docker.
#
#   scripts/check.sh                          pylint (errors) + all unit tests
#   scripts/check.sh pytest -k tab            any other command, in the test image
#   scripts/check.sh pytest tests/unit/test_fieldkit.py
#
# This is the same thing the GitHub Actions workflow runs
# (.github/workflows/tests.yml). Nothing to install except Docker.
# See tests/README.md.

set -euo pipefail

cd "$(dirname "$0")/.."

# Builds the test image on first use, and again whenever pyproject.toml or the
# Dockerfile change; src/ and tests/ are mounted, so code edits need no rebuild.
docker compose build test

# No arguments: the image's default command (pylint, then pytest).
# With arguments: run them in the test image instead.
docker compose run --rm test "$@"
