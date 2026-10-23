FROM python:3.12-slim

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

RUN addgroup --system curator && adduser --system --ingroup curator curator
USER curator

EXPOSE 8080

# dbkit reads DBKIT_* env vars; PGPASSWORD is honored by psycopg.
# All connection config comes from docker-compose environment, not config files.
CMD ["uvicorn", "curator.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
