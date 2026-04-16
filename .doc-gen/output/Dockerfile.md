# Dockerfile

**Path:** Dockerfile
**Syntax:** text
**Generated:** 2026-04-16 11:00:26

```
# =============================================================================
# Curator - Dockerfile
# =============================================================================
#
# Builds the Curator web app on Alma Linux 9 (matching wcyjvs1).
#
# Security posture:
#   - Non-root user (curator, uid 1000)
#   - No build tools in final image
#   - dbkit and viewkit installed directly from GitHub
#   - DB credentials via ~/.pgpass mounted at runtime (never in image)
#   - App config via ~/.config/curator/ mounted at runtime
#
# Build:
#   docker build -t curator:latest .
#
# Run via docker-compose — see docker-compose.yml.
# =============================================================================

FROM almalinux:9-minimal AS base

# Install Python 3.11 and git (needed for pip install from GitHub)
RUN microdnf install -y python3.11 python3.11-pip git && \
    microdnf clean all

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash curator

# ---------------------------------------------------------------------------
# Build stage — install dependencies
# ---------------------------------------------------------------------------

FROM base AS builder

WORKDIR /build

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install into user site-packages
RUN pip3.11 install --no-cache-dir .

# ---------------------------------------------------------------------------
# Final image
# ---------------------------------------------------------------------------

FROM base

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy application
WORKDIR /app
COPY --chown=curator:curator src/curator/ ./src/curator/
COPY --chown=curator:curator static/ ./static/
COPY --chown=curator:curator pyproject.toml .

USER curator

# Config and pgpass are mounted at runtime — see docker-compose.yml
# ~/.config/dev-utils/config.yaml  — dbkit connection config
# ~/.config/curator/curator.yaml   — optional user config override
# ~/.pgpass                         — postgres password (mode 0600)

EXPOSE 8080

CMD ["uvicorn", "curator.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
```
