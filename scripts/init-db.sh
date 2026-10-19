#!/usr/bin/env bash
# init-db.sh — Copy SQL init files from steward into db/init/
#
# Run once before first `docker compose up` on a new host.
# Postgres runs everything in db/init/ alphabetically on first start
# (only when the data volume is empty — safe to re-run after that).
#
# Usage:
#   ./scripts/init-db.sh /path/to/steward
#
# Example (VPS, both repos in /srv):
#   ./scripts/init-db.sh /srv/steward

set -euo pipefail

STEWARD_DIR="${1:-}"
if [[ -z "$STEWARD_DIR" ]]; then
    echo "Usage: $0 /path/to/steward" >&2
    exit 1
fi

SQL_SRC="$STEWARD_DIR/databases/wcyj/sql"
SQL_DST="$(dirname "$0")/../db/init"

if [[ ! -d "$SQL_SRC" ]]; then
    echo "Error: SQL directory not found at $SQL_SRC" >&2
    exit 1
fi

# Copy init SQL files — exclude 00_drop.sql (destructive, not for init)
# and archive/
for f in "$SQL_SRC"/0[1-9]_*.sql "$SQL_SRC"/0[1-9][a-z]_*.sql; do
    [[ -f "$f" ]] || continue
    cp "$f" "$SQL_DST/"
    echo "  copied $(basename "$f")"
done

echo "Done. Files in $SQL_DST:"
ls "$SQL_DST"
