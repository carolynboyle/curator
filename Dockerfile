FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg (binary mode, no build needed) and general hygiene
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first so layer is cached unless deps change
COPY pyproject.toml ./

# Install the app and its dependencies.
# pip installs from git+https for dbkit/viewkit; the proxy CA bundle is
# pre-configured in the build environment via REQUESTS_CA_BUNDLE / SSL_CERT_FILE.
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e .

# Copy application source
COPY src/ ./src/
COPY src/curator/data/ ./src/curator/data/

# Non-root user for runtime
RUN addgroup --system curator && adduser --system --ingroup curator curator
USER curator

EXPOSE 8080

# dbkit reads DBKIT_* env vars; PGPASSWORD is honored by psycopg.
# All connection config comes from docker-compose environment, not config files.
CMD ["uvicorn", "curator.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
