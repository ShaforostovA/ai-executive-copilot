# Phase 5 — Public MVP safeguards, Yandex Mail и production preparation

## LIVE GigaChat

LIVE provider отключен по умолчанию (`COPILOT_GIGACHAT_ENABLED=false`) и требует credentials только из защищенного env/secret manager. Frontend получает только typed API responses и никогда не получает GigaChat credentials.

Provider сохраняет OAuth cache, UUID4 RqUID, TLS verification, timeout, 401 refresh, 429/5xx/network/validation errors. Workflow доступен только с серверной сессией и принимает только LIVE provider result. DEMO не используется как fallback.

Платные запросы ограничены двумя механизмами:

- PostgreSQL `ai_requests`: per-owner per-minute и UTC daily limits с transactional advisory lock;
- idempotent replay возвращает сохраненный анализ без нового provider call.

`POST /api/v1/analysis/run` возвращает `429` при исчерпании budget. Настройки: `COPILOT_GIGACHAT_REQUESTS_PER_MINUTE`, `COPILOT_GIGACHAT_DAILY_REQUEST_LIMIT`.

Ручной smoke `backend/scripts/gigachat_smoke.py --confirm-live` дополнительно требует `COPILOT_GIGACHAT_ENABLED=true` и выполняет один synthetic analysis. Он не запускался; реальные платные запросы запрещены без разрешения.

## Security

- Все mutating `/api/*` запросы требуют browser `Origin` из `COPILOT_ALLOWED_ORIGINS`; остальные получают `403 csrf_rejected`.
- CORS использует explicit origins, credentials и ограниченные methods/headers, без wildcard.
- Login ограничен per-IP sliding window (`COPILOT_LOGIN_RATE_LIMIT_ATTEMPTS` в минуту).
- Cookie остается HttpOnly/SameSite=Lax и Secure в production.
- Expired server sessions удаляются maintenance loop с настраиваемым `COPILOT_SESSION_CLEANUP_INTERVAL_SECONDS`.
- Production запрещает DEMO repository и insecure cookie; synthetic seed не имеет встроенного пароля и отклоняет production.
- Migration `20261126_0002` добавляет AI usage и encrypted integration credentials.

## Yandex Mail

Реализация находится в `infrastructure/yandex_imap.py` и `services/yandex_mail.py`.

- `imaplib.IMAP4_SSL` с `ssl.create_default_context()` и системной проверкой сертификата.
- Отдельный app password или поддерживаемые провайдером credentials; plaintext password не хранится в БД.
- Credentials сериализуются и шифруются Fernet ключом `COPILOT_CREDENTIAL_ENCRYPTION_KEY`; ciphertext находится в `integration_credentials`.
- `SELECT folder readonly=True`; разрешены только папки из `COPILOT_YANDEX_ALLOWED_FOLDERS` (default `INBOX`).
- UID SEARCH/FETCH по UIDVALIDITY + UID cursor, incremental sync и bounded batch.
- Plain-text extraction, synthetic tests без реального mailbox.
- Идемпотентный source import и deterministic source UUID; повтор не создает дубликат и не вызывает AI повторно.
- Tenant/owner filters применяются к connection, credentials, source и analysis.
- Новые сообщения передаются в общий `AnalysisWorkflowService.run_source` и появляются в PostgreSQL Dashboard как LIVE.
- Revoke удаляет ciphertext, очищает cursor и переводит integration в `NOT_CONFIGURED`; импортированные сообщения не выдаются за удаленные.

Protected endpoints:

- `POST /api/v1/integrations/yandex/connect`;
- `POST /api/v1/integrations/yandex/sync`;
- `DELETE /api/v1/integrations/yandex`.

Реальные почтовые аккаунты не подключались. Mock IMAP tests проверяют encryption, allowed folder, two-message sync, AI analysis, idempotent second sync, dashboard LIVE, cross-tenant denial и revoke.

## CI и воспроизводимость

- `backend/requirements.lock` фиксирует runtime/dev dependencies и используется как constraint в Docker и CI.
- `backend:test:postgresql` запускает disposable PostgreSQL integration suite.
- `frontend:e2e` изолированно устанавливает Node 22 и Chromium, запускает PostgreSQL 17, migrations, synthetic seed, FastAPI и Playwright desktop/mobile tests.
- Frontend lint/typecheck/unit/build и npm lockfile остаются обязательными checks.
- `.dockerignore` исключает secrets, VCS, virtualenvs, node_modules, test artifacts и backups из Docker build context.

## Production preparation

`infra/compose.prod.yml` содержит PostgreSQL 17, one-shot Alembic migrate, FastAPI, frontend Nginx и Caddy HTTPS. Публичны только 80/443; PostgreSQL internal-only. Настроены named volumes, healthchecks, memory limits для Ubuntu 4 GB RAM и production Secure cookies/origins.

- Frontend image: `frontend/Dockerfile`, SPA/PWA + `/api` proxy в `frontend/nginx.conf`.
- HTTPS: `infra/Caddyfile`, DOMAIN/ACME_EMAIL из защищенного env.
- Единый безопасный template: `.env.example`; реальный `.env.production` должен быть вне Git с `chmod 600`.
- Backup/restore: `infra/scripts/backup_postgres.sh`, `infra/scripts/restore_postgres.sh`.
- Deploy/rollback/restore: `docs/PRODUCTION_RUNBOOK.md`.

Production images и Compose config проверяются локально с фиктивными значениями. VPS, DNS, firewall, restore и реальные API не запускались.
