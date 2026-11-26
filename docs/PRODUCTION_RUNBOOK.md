# Production deployment и rollback — Ubuntu 4 GB RAM

**Статус:** конфигурация подготовлена, VPS не изменялся. Нужны домен и явное разрешение владельца перед выполнением команд на сервере.

## Архитектура

`Internet → Caddy HTTPS → frontend Nginx → FastAPI → PostgreSQL`.

PostgreSQL не публикует порт. Caddy — единственный публичный web entrypoint (80/443). Frontend Nginx проксирует `/api`, `/healthz`, `/readyz` и отдает PWA. Отдельный one-shot `migrate` контейнер завершает Alembic upgrade перед запуском API. Named volumes: PostgreSQL data/backups и Caddy certificates/state.

## Preflight

1. Ubuntu с 4 GB RAM, достаточный свободный диск, DNS A/AAAA на публичный IP.
2. Открыты только необходимые SSH и 80/443; проверить отсутствие конфликтующего proxy.
3. Установить Docker Engine и Compose plugin только после подтвержденного плана; не менять существующий firewall/VPN.
4. Скопировать `.env.example` в защищенный `.env.production` вне Git, `chmod 600`.
5. Задать реальный домен, уникальный PostgreSQL password, Fernet key и только разрешенные LIVE secrets. DEMO seed не задавать.

Fernet key создается локально через `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`; результат сохраняется только в защищенном env/secret manager.

## Проверка конфигурации

```bash
docker compose --env-file .env.production -f infra/compose.prod.yml config --quiet
docker compose --env-file .env.production -f infra/compose.prod.yml build
docker compose --env-file .env.production -f infra/compose.prod.yml up -d
docker compose --env-file .env.production -f infra/compose.prod.yml ps
curl --fail "https://$DOMAIN/healthz"
curl --fail "https://$DOMAIN/readyz"
```

Проверить HTTPS certificate, login, dashboard, mobile viewport, DEMO/LIVE маркировку и отсутствие секретов в логах. LIVE GigaChat включается только `GIGACHAT_ENABLED=true` после отдельного разрешения и smoke с лимитом.

## Initial production user

Не используйте DEMO seed или общий пароль. После successful migrate создайте отдельную организацию и первого пользователя через `backend/scripts/create_initial_user.py`, передав secrets только через защищенную env-сессию:

```bash
docker compose --env-file .env.production -f infra/compose.prod.yml run --rm \
  -e COPILOT_ADMIN_ORGANIZATION_SLUG \
  -e COPILOT_ADMIN_ORGANIZATION_NAME \
  -e COPILOT_ADMIN_EMAIL \
  -e COPILOT_ADMIN_PASSWORD \
  api python backend/scripts/create_initial_user.py
```

Скрипт требует уникальный email и пароль длиной не менее 12 символов, сохраняет только scrypt hash и не печатает пароль. Полная release-процедура и проверенный smoke находятся в `docs/RELEASE_READINESS.md`.

## Backup

Перед миграциями и обновлениями:

```bash
ENV_FILE=.env.production infra/scripts/backup_postgres.sh /secure/backups
```

Скрипт создает PostgreSQL custom-format dump с правами owner-only и SHA-256 checksum. Копию следует хранить off-VPS с отдельной ротацией и периодической проверкой восстановления.

## Restore — destructive

Восстановление перезаписывает текущую БД. Сначала создать новый backup, проверить checksum и выполнить restore на отдельной тестовой БД. Только после явного подтверждения владельца:

```bash
RESTORE_CONFIRM=yes ENV_FILE=.env.production \
  infra/scripts/restore_postgres.sh /secure/backups/verified.dump
```

После restore проверить migrations, `/readyz`, login и tenant isolation. Откат БД отдельный: rollback Docker image не отменяет миграции.

## Deploy update

1. Создать backup и зафиксировать текущий `APP_VERSION`/image digests.
2. Проверить MR pipeline, включая PostgreSQL integration и Playwright.
3. Собрать новую версию, запустить `up -d`; дождаться successful one-shot migrate и healthy services.
4. Проверить HTTPS, login/dashboard/source/logout и отсутствие ошибок.

## Rollback

1. Остановить rollout при failed healthchecks.
2. Установить предыдущий `APP_VERSION` в защищенном env и повторить `up -d` без force-recreate volumes.
3. Если новая миграция несовместима, не запускать downgrade автоматически: использовать отдельный согласованный restore/forward-fix план.
4. Проверить `/healthz`, `/readyz` и пользовательский сценарий.

Production deploy, DNS/firewall, restore и реальные API-запросы не выполнялись.
