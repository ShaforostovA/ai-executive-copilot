# Offline Staging Deployment — mariandr.ru

## Зафиксированный релиз

- Git tag: `v0.1.0-rc2`.
- Release commit: `59ea315e33b469693dddf9d604b8f575d61f1caf`.
- Platform: `linux/amd64`.
- Memory override: `infra/compose.vps-4gb.yml`, 2.25 GiB total.
- `APP_VERSION`: `0.1.0-rc2`.

Подготовленные локально файлы в `.release-smoke`:

- `copilot-images-0.1.0-rc2.tar` — все Docker images, linux/amd64;
- `copilot-images-0.1.0-rc2.tar.sha256` — checksum;
- `copilot-release-0.1.0-rc2.tar.gz` — только tracked release files;
- `copilot-release-0.1.0-rc2.tar.gz.sha256` — checksum.

Состав image archive подтвержден:

- `copilot-api:0.1.0-rc2` — backend и migration, один общий image;
- `copilot-frontend:0.1.0-rc2`;
- `postgres:17-alpine`;
- `caddy:2-alpine`.

Все 4 образа имеют `linux/amd64`. Archive release files не содержит `.env.production`, diagnostic output, handoff, node_modules или virtualenv.

## 1. PowerShell — передача на VPS

Выполнить на рабочем ПК, не на VPS:

```powershell
scp .release-smoke\copilot-images-0.1.0-rc2.tar <USER>@mariandr.ru:/tmp/
scp .release-smoke\copilot-images-0.1.0-rc2.tar.sha256 <USER>@mariandr.ru:/tmp/
scp .release-smoke\copilot-release-0.1.0-rc2.tar.gz <USER>@mariandr.ru:/tmp/
scp .release-smoke\copilot-release-0.1.0-rc2.tar.gz.sha256 <USER>@mariandr.ru:/tmp/
scp infra\scripts\offline_load.sh <USER>@mariandr.ru:/tmp/
```

`<USER>` заменить на разрешенного deploy user. Не включать пароли/keys в команды или имена файлов.

## 2. Ubuntu — checksum, распаковка и import

```bash
cd /tmp
sha256sum -c copilot-images-0.1.0-rc2.tar.sha256
sha256sum -c copilot-release-0.1.0-rc2.tar.gz.sha256
bash /tmp/offline_load.sh 0.1.0-rc2
```

`offline_load.sh` повторно проверяет checksums, распаковывает release в `/opt/copilot-staging/app`, помещает archive в `/opt/copilot-staging/images`, выполняет `docker load` и проверяет все 4 image tags и архитектуру.

Ожидаемые теги:

```text
copilot-api:0.1.0-rc2
copilot-frontend:0.1.0-rc2
postgres:17-alpine
caddy:2-alpine
```

Проверить вручную:

```bash
docker image inspect --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}' \
  copilot-api:0.1.0-rc2 copilot-frontend:0.1.0-rc2 postgres:17-alpine caddy:2-alpine
```

## 3. Production environment

Создать `/etc/copilot-staging/.env.production` через защищенную сессию с `chmod 600`. Не включать его в Git и не передавать через обычный чат.

Обязательная форма:

```dotenv
DOMAIN=mariandr.ru
ACME_EMAIL=<letsencrypt-notification-mailbox>
APP_VERSION=0.1.0-rc2
POSTGRES_USER=copilot
POSTGRES_DB=copilot
POSTGRES_PASSWORD=<unique-random-postgres-password>
CREDENTIAL_ENCRYPTION_KEY=<unique-fernet-key>
GIGACHAT_ENABLED=false
GIGACHAT_CREDENTIALS=
GIGACHAT_SCOPE=GIGACHAT_API_PERS
AI_DAILY_LIMIT=20
YANDEX_ALLOWED_FOLDERS=INBOX
```

Настройки production Compose уже задают:

- `COPILOT_ENVIRONMENT=production`;
- `COPILOT_USE_DEMO_REPOSITORY=false`;
- `COPILOT_SESSION_COOKIE_SECURE=true`;
- `COPILOT_ALLOWED_ORIGINS=https://mariandr.ru`;
- `COPILOT_TRUSTED_PROXY_IPS=172.30.0.0/24`.

DEMO seed не запускать. Пароли генерировать независимо:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Не отправлять вывод этих команд в Git, Issues, MR или чат. Сохранить Fernet key в `/etc/copilot-staging/.env.production` и отдельно в менеджере секретов для восстановления credentials после backup/restore.

## 4. Проверка перед запуском

```bash
cd /opt/copilot-staging/app
export COMPOSE_FILE=infra/compose.prod.yml:infra/compose.vps-4gb.yml
docker compose --env-file /etc/copilot-staging/.env.production config --quiet
docker compose --env-file /etc/copilot-staging/.env.production config | less
docker images --format '{{.Repository}}:{{.Tag}}' | sort
docker info --format 'ServerVersion={{.ServerVersion}}'
```

Не запускать сервис, если:

- checksum не совпадает;
- image tag отсутствует или отличается;
- `APP_VERSION` не равен `0.1.0-rc2`;
- env отсутствует или содержит DEMO/demo seed;
- доступная RAM недостаточна для 2.25 GiB + ОС;
- DNS `mariandr.ru` не указывает на VPS.

## 5. Запуск без Docker Hub

Порядок: PostgreSQL → Alembic → admin → API → frontend → Caddy.

```bash
cd /opt/copilot-staging/app
export COMPOSE_FILE=infra/compose.prod.yml:infra/compose.vps-4gb.yml

docker compose --env-file /etc/copilot-staging/.env.production --pull never --no-build up -d postgres
docker compose --env-file /etc/copilot-staging/.env.production --pull never --no-build up -d migrate
docker compose --env-file /etc/copilot-staging/.env.production ps
```

После успешного migrate создать первоначального admin через защищенную env-сессию:

```bash
docker compose --env-file /etc/copilot-staging/.env.production run --rm \
  -e COPILOT_ADMIN_ORGANIZATION_SLUG \
  -e COPILOT_ADMIN_ORGANIZATION_NAME \
  -e COPILOT_ADMIN_EMAIL \
  -e COPILOT_ADMIN_PASSWORD \
  api python backend/scripts/create_initial_user.py
```

Пароль не записывать в command line, Git или logs. Затем:

```bash
docker compose --env-file /etc/copilot-staging/.env.production --pull never --no-build up -d
```

Эти команды не требуют `docker pull` и не собирают images на VPS.

## 6. Проверка публичного сервиса

```bash
docker compose --env-file /etc/copilot-staging/.env.production ps
docker compose --env-file /etc/copilot-staging/.env.production logs --tail=100 migrate
docker compose --env-file /etc/copilot-staging/.env.production logs --tail=100 api
docker compose --env-file /etc/copilot-staging/.env.production logs --tail=100 caddy
ss -ltn
curl --fail https://mariandr.ru/healthz
curl --fail https://mariandr.ru/readyz
```

Проверить:

- только Caddy публикует 80/443; PostgreSQL и API не имеют published ports;
- memory limits соответствуют override;
- сертификат и hostname `mariandr.ru` корректны;
- `/readyz` возвращает `database=ok`;
- login → Dashboard → source detail → logout работает на desktop/mobile;
- logs не содержат паролей, access tokens, Fernet key или session cookies.

Проверить memory limits:

```bash
docker inspect $(docker compose --env-file /etc/copilot-staging/.env.production ps -aq postgres) --format '{{.HostConfig.Memory}}'
docker inspect $(docker compose --env-file /etc/copilot-staging/.env.production ps -aq api) --format '{{.HostConfig.Memory}}'
docker inspect $(docker compose --env-file /etc/copilot-staging/.env.production ps -aq migrate) --format '{{.HostConfig.Memory}}'
docker inspect $(docker compose --env-file /etc/copilot-staging/.env.production ps -aq frontend) --format '{{.HostConfig.Memory}}'
docker inspect $(docker compose --env-file /etc/copilot-staging/.env.production ps -aq caddy) --format '{{.HostConfig.Memory}}'
```

Ожидаемые значения: 768/768/384/192/192 MiB.

## 7. Persistence и backup

```bash
docker compose --env-file /etc/copilot-staging/.env.production down
docker compose --env-file /etc/copilot-staging/.env.production --pull never --no-build up -d
```

Не использовать `down -v`. Повторно проверить login и Dashboard; данные должны сохраниться.

Backup:

```bash
ENV_FILE=/etc/copilot-staging/.env.production /opt/copilot-staging/app/infra/scripts/backup_postgres.sh /var/backups/copilot-staging
```

Проверить restore в отдельную тестовую БД и Fernet decrypt. Off-VPS copy обязателен для реального rollout.

## 8. Rollback

- Зафиксировать текущий `APP_VERSION` и working image digests.
- При failed healthchecks вернуть предыдущий `APP_VERSION` через `up -d` без удаления volumes.
- Не выполнять `down -v` или автоматический DB downgrade.
- Rollback image не отменяет миграции; отдельный согласованный restore/forward-fix план обязателен.

## Фактические ограничения

- SSH и изменение VPS не выполнялись.
- Docker Hub не используется после import.
- Live GigaChat и реальная Яндекс Почта не запускались.
- Public ACME certificate будет проверен только после DNS и запуска Caddy.
