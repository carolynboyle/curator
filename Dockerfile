# Three stages:
#   base  runtime dependencies and the curator package (editable install)
#   test  base + pytest/pylint and the tests; built only on request
#         (docker compose run --rm test) — see tests/README.md
#   app   the production image; last stage, so a plain
#         `docker compose up --build` builds this one and nothing else
FROM python:3.12-slim AS base

WORKDIR /app

# git: pip installs dbkit and viewkit from git+https (see pyproject.toml)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# README.md: pyproject.toml names it as the package readme
COPY pyproject.toml README.md ./
COPY src/ ./src/
# static/: CSS, JS and images, served from /app/static (see web/app.py)
COPY static/ ./static/

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e .


FROM base AS test

# The [test] extra (pytest, pytest-asyncio, httpx, pylint) comes from
# pyproject.toml. src/ and tests/ are bind-mounted by the compose "test"
# service, so edits are picked up without a rebuild; rebuild only when
# dependencies change.
RUN pip install --no-cache-dir -e ".[test]"
COPY tests/ ./tests/

# Same checks, same order, locally and in CI: pylint errors, then the unit
# tests. Pass another command to run something narrower, e.g.
#   docker compose run --rm test pytest -k tab
CMD ["sh", "-c", "pylint --errors-only src/curator && pytest"]


FROM base AS app

RUN addgroup --system curator && adduser --system --ingroup curator curator
USER curator

EXPOSE 8080

# dbkit reads DBKIT_* env vars; PGPASSWORD is honored by psycopg.
# All connection config comes from docker-compose environment, not config files.
CMD ["uvicorn", "curator.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
