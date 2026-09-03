#!/usr/bin/env bash
# pg_dump the Postgres volume to a timestamped file. Keeps the last 14.
# Cron example (daily 03:00):
#   0 3 * * * /opt/knsb/scripts/backup_db.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP="${BACKUP_KEEP:-14}"
COMPOSE="${COMPOSE:-docker compose}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/knsb-$STAMP.sql.gz"

$COMPOSE exec -T db pg_dump -U "${POSTGRES_USER:-knsb}" "${POSTGRES_DB:-knsb}" | gzip > "$OUT"
echo "wrote $OUT"

# prune old backups
ls -1t "$BACKUP_DIR"/knsb-*.sql.gz 2>/dev/null | tail -n "+$((KEEP + 1))" | xargs -r rm -v
