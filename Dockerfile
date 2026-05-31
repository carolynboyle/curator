# =============================================================================
# Curator - Dockerfile
# =============================================================================
#
# Builds the Curator web app on Alma Linux 9 (matching wcyjvs1).
#
# Security posture:
#   - Non-root user (curator, uid 1000)
#   - DB credentials via ~/.pgpass mounted at runtime (never in image)
#   - App config via ~/.config/curator/ mounted at runtime
#
# Design notes:
#   - Dependencies installed from pyproject.toml but curator itself is NOT
#     installed as a package — it runs from /app/src so that relative paths
#     (templates, static) resolve correctly against the source tree.
#   - pip install --no-build-isolation avoids OOM during wheel builds in
#     memory-constrained environments.
#
# Build:
#   docker build -t curator:latest .
#
# Run via docker-compose — see docker-compose.yml.
# =============================================================================

FROM almalinux:9-minimal

# Install Python 3.11, pip, and git (needed for pip install from GitHub)
RUN microdnf install -y python3.11 python3.11-pip git && \
    microdnf clean all

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash curator

# ---------------------------------------------------------------------------
# Install dependencies only (not the curator package itself)
# ---------------------------------------------------------------------------

WORKDIR /build

COPY pyproject.toml .

# Install all dependencies declared in pyproject.toml except curator itself
RUN pip3.11 install --no-cache-dir \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "jinja2>=3.1.0" \
    "python-multipart>=0.0.9" \
    "pyyaml>=6.0" \
    "dbkit @ git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/dbkit" \
    "viewkit @ git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/viewkit"

# ---------------------------------------------------------------------------
# Set up application — run from source, not from installed package
# ---------------------------------------------------------------------------

WORKDIR /app

COPY --chown=curator:curator src/ ./src/
COPY --chown=curator:curator static/ ./static/
COPY --chown=curator:curator pyproject.toml .

USER curator

# Config and pgpass are mounted at runtime — see docker-compose.yml
# ~/.config/dev-utils/config.yaml  — dbkit connection config
# ~/.config/curator/curator.yaml   — optional user config override
# ~/.pgpass                         — postgres password (mode 0600)

EXPOSE 8080

# PYTHONPATH tells Python where to find the curator package in /app/src
ENV PYTHONPATH=/app/src

CMD ["uvicorn", "curator.web.app:app", "--host", "0.0.0.0", "--port", "8080"]