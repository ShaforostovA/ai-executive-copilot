#!/bin/sh
set -eu

if [ "${RESTORE_CONFIRM:-}" != "yes" ]; then
  echo "Refusing destructive restore. Set RESTORE_CONFIRM=yes after reviewing the runbook." >&2
  exit 1
fi
ENV_FILE=${ENV_FILE:-.env.production}
BACKUP_FILE=${1:?Usage: restore_postgres.sh /path/to/verified.dump}
set -a
. "$ENV_FILE"
set +a
sha256sum -c "$BACKUP_FILE.sha256"
docker compose --env-file "$ENV_FILE" -f infra/compose.prod.yml stop api
cat "$BACKUP_FILE" | docker compose --env-file "$ENV_FILE" -f infra/compose.prod.yml exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists
docker compose --env-file "$ENV_FILE" -f infra/compose.prod.yml start api
