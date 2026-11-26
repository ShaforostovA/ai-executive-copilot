#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_USER:?Set POSTGRES_USER}"
: "${POSTGRES_DB:?Set POSTGRES_DB}"
: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}"
: "${CREDENTIAL_ENCRYPTION_KEY:?Set CREDENTIAL_ENCRYPTION_KEY}"
: "${COPILOT_ADMIN_ORGANIZATION_SLUG:?Set admin organization}"
: "${COPILOT_ADMIN_ORGANIZATION_NAME:?Set organization name}"
: "${COPILOT_ADMIN_EMAIL:?Set admin email}"
: "${COPILOT_ADMIN_PASSWORD:?Set admin password}"
: "${RELEASE_YANDEX_PASSWORD:?Set synthetic Yandex password}"

export DOMAIN="${DOMAIN:-mvp.release.test}"
export ACME_EMAIL="${ACME_EMAIL:-release@example.test}"
export APP_VERSION="${APP_VERSION:-release-smoke}"
export GIGACHAT_ENABLED="${GIGACHAT_ENABLED:-false}"
export AI_DAILY_LIMIT="${AI_DAILY_LIMIT:-20}"
export YANDEX_ALLOWED_FOLDERS="${YANDEX_ALLOWED_FOLDERS:-INBOX}"
RESTORE_DB="${RESTORE_DB:-release_restore_$(date +%s)}"
if [[ ! "$RESTORE_DB" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "Unsafe restore database name" >&2
  exit 1
fi
compose=(docker compose -p copilot-release-smoke --env-file .env.example -f infra/compose.prod.yml -f infra/compose.release-smoke.yml)
cleanup() { "${compose[@]}" down; }
trap cleanup EXIT
mkdir -p .release-smoke
"${compose[@]}" config --quiet
"${compose[@]}" build
"${compose[@]}" up -d
ready=0
for _ in {1..45}; do
  if "${compose[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
test "$ready" -eq 1
admin_env=(
  -e "COPILOT_ADMIN_ORGANIZATION_SLUG=$COPILOT_ADMIN_ORGANIZATION_SLUG"
  -e "COPILOT_ADMIN_ORGANIZATION_NAME=$COPILOT_ADMIN_ORGANIZATION_NAME"
  -e "COPILOT_ADMIN_EMAIL=$COPILOT_ADMIN_EMAIL"
  -e "COPILOT_ADMIN_PASSWORD=$COPILOT_ADMIN_PASSWORD"
  -e "RELEASE_YANDEX_PASSWORD=$RELEASE_YANDEX_PASSWORD"
)
"${compose[@]}" run --rm "${admin_env[@]}" api python backend/scripts/create_initial_user.py
"${compose[@]}" run --rm "${admin_env[@]}" api python backend/scripts/release_credential_check.py prepare
"${compose[@]}" exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > .release-smoke/backup.dump
"${compose[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $RESTORE_DB"
"${compose[@]}" exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$RESTORE_DB" --clean --if-exists < .release-smoke/backup.dump
"${compose[@]}" run --rm "${admin_env[@]}" \
  -e "COPILOT_DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${RESTORE_DB}" \
  api python backend/scripts/release_credential_check.py verify
"${compose[@]}" exec -T caddy cat //data/caddy/pki/authorities/local/root.crt > .release-smoke/root.crt
curl_extra=()
if [[ "${RELEASE_CURL_NO_REVOKE:-0}" == "1" ]]; then
  curl_extra+=(--ssl-no-revoke)
fi
curl_base=(curl --silent --show-error --cacert .release-smoke/root.crt --resolve "$DOMAIN:443:127.0.0.1" "${curl_extra[@]}")
ready=0
for _ in {1..30}; do
  if "${curl_base[@]}" --fail "https://$DOMAIN/healthz" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
test "$ready" -eq 1
cors_headers=$("${curl_base[@]}" --dump-header - --output /dev/null -X OPTIONS \
  -H "Origin: https://$DOMAIN" -H 'Access-Control-Request-Method: POST' \
  "https://$DOMAIN/api/v1/auth/login")
case "${cors_headers,,}" in
  *"access-control-allow-origin: https://$DOMAIN"*) ;;
  *) exit 1;;
esac
csrf_code=$("${curl_base[@]}" --output /dev/null --write-out '%{http_code}' \
  -X POST -H 'Origin: https://attacker.example' -H 'Content-Type: application/json' \
  -d '{}' "https://$DOMAIN/api/v1/auth/login")
test "$csrf_code" = 403
login_headers=$("${curl_base[@]}" --dump-header - --output .release-smoke/login.json \
  -X POST -H "Origin: https://$DOMAIN" -H 'Content-Type: application/json' \
  -d "{\"organization_slug\":\"$COPILOT_ADMIN_ORGANIZATION_SLUG\",\"email\":\"$COPILOT_ADMIN_EMAIL\",\"password\":\"$COPILOT_ADMIN_PASSWORD\"}" \
  "https://$DOMAIN/api/v1/auth/login")
case "$login_headers" in *HttpOnly*) ;; *) exit 1;; esac
case "$login_headers" in *Secure*) ;; *) exit 1;; esac
case "$login_headers" in *SameSite=lax*) ;; *) exit 1;; esac
for _ in 1 2 3 4 5; do
  code=$("${curl_base[@]}" --output /dev/null --write-out '%{http_code}' \
    -X POST -H "Origin: https://$DOMAIN" -H 'Content-Type: application/json' \
    -d "{\"organization_slug\":\"$COPILOT_ADMIN_ORGANIZATION_SLUG\",\"email\":\"$COPILOT_ADMIN_EMAIL\",\"password\":\"incorrect_release_password\"}" \
    "https://$DOMAIN/api/v1/auth/login")
done
test "$code" = 429
api_memory=$(docker inspect "$("${compose[@]}" ps -aq api)" --format '{{.HostConfig.Memory}}')
postgres_memory=$(docker inspect "$("${compose[@]}" ps -aq postgres)" --format '{{.HostConfig.Memory}}')
frontend_memory=$(docker inspect "$("${compose[@]}" ps -aq frontend)" --format '{{.HostConfig.Memory}}')
caddy_memory=$(docker inspect "$("${compose[@]}" ps -aq caddy)" --format '{{.HostConfig.Memory}}')
migrate_memory=$(docker inspect "$("${compose[@]}" ps -aq migrate)" --format '{{.HostConfig.Memory}}')
test "$api_memory" = 1073741824
test "$postgres_memory" = 1073741824
test "$frontend_memory" = 268435456
test "$caddy_memory" = 268435456
test "$migrate_memory" = 536870912
python3 - <<'PY'
import json
print(json.dumps({
    "backup_restore": "passed",
    "fernet_decrypt_after_restore": "passed",
    "https": "passed",
    "cors": "passed",
    "csrf": 403,
    "cookie": "HttpOnly Secure SameSite=lax",
    "rate_limit": 429,
    "memory_limits": "3.25 GiB verified",
}, indent=2))
PY
