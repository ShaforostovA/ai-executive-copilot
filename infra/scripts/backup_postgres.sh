#!/bin/sh
set -eu

ENV_FILE=${ENV_FILE:-.env.production}
BACKUP_DIRECTORY=${1:-./backups}
set -a
. "$ENV_FILE"
set +a
mkdir -p "$BACKUP_DIRECTORY"
chmod 700 "$BACKUP_DIRECTORY"
umask 077
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE="$BACKUP_DIRECTORY/copilot-$TIMESTAMP.dump"
docker compose --env-file "$ENV_FILE" -f infra/compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$FILE"
sha256sum "$FILE" > "$FILE.sha256"
printf '%s\n' "$FILE"
