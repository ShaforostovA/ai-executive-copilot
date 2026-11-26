# Staging Deployment — Ubuntu VPS 4 GB RAM

## Статус

- RC1 объединен в `main` и отмечен тегом `v0.1.0-rc1`.
- SSH, DNS, firewall и production VPS не изменялись.
- Live GigaChat и реальная Яндекс Почта не вызывались.
- Этот документ описывает будущий запуск только после разрешения владельца и получения безопасных diagnostic results.

Полученная диагностика подтверждает Ubuntu 24.04 x86_64, 2 CPU, 3.4 GiB available RAM, 512 MiB swap и 54 GiB free disk. Docker/containerd отсутствуют, 80/443 свободны, UFW inactive, nftables пуст, конфликтующих служб нет. Подробности: `docs/VPS_ANALYSIS.md`.

Базовый memory budget 3.25 GiB не оставляет достаточного запаса. Для этого VPS обязательно использовать `infra/compose.vps-4gb.yml` с общим лимитом 2.25 GiB; команды ниже уже содержат его. Не запускать базовый Compose без override.

## 1. Read-only диагностика

Скопировать `infra/scripts/vps_diagnostic.sh` на VPS только после разрешения доступа и запустить:

```bash
bash infra/scripts/vps_diagnostic.sh
```

Скрипт не устанавливает пакеты и не меняет конфигурацию. Он проверяет Ubuntu/architecture, CPU, RAM, swap, disk, порты 22/80/443, firewall, containers, Docker/containerd/Nginx/Caddy, network и DNS. Raw output может содержать IP/hostname/service details — не прикладывать его в Git, Issue или общий чат без очистки.

Ожидаемые preflight условия:

- x86_64 Ubuntu с Docker Engine support;
- не менее 2.25 GiB для контейнеров плюс запас для ОС и временных пиков; для базового 3.25 GiB профиля — больше RAM;
- не менее 10 GiB свободного места для images, PostgreSQL и backups;
- порты 80/443 свободны или согласован существующий reverse proxy;
- отсутствуют конфликтующие контейнеры/службы;
- разрешены outbound HTTPS к Docker Hub, GitHub и Docker apt repository;
- DNS staging hostname указывает на публичный IP VPS.

При конфликтах остановиться. Не удалять пакеты, контейнеры или существующие конфигурации без отдельного согласования.

## 2. План установки Docker Engine и Compose Plugin

Использовать только официальную инструкцию: https://docs.docker.com/engine/install/ubuntu/.

После проверки diagnostic results:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
docker --version
docker compose version
```

Проверить `docker run --rm hello-world`. Не добавлять пользователя в `docker` group автоматически: это root-equivalent доступ. Не отключать SSH/VPN/firewall.

## 3. Изолированный staging-каталог и secrets

```bash
sudo mkdir -p /opt/copilot-staging /etc/copilot-staging /var/backups/copilot-staging
sudo chmod 755 /opt/copilot-staging
sudo chmod 700 /etc/copilot-staging /var/backups/copilot-staging
```

В `/opt/copilot-staging` разместить только `v0.1.0-rc1`:

```bash
git clone https://gitlab.com/ai-executive-copilot-team/ai-executive-copilot.git /opt/copilot-staging/app
cd /opt/copilot-staging/app
git checkout v0.1.0-rc1
```

Если проект приватный, аутентификацию выполнить через разрешенный deploy credential с read-only scope; не сохранять PAT в Git или командной строке.

Создать `/etc/copilot-staging/.env.production` на основе `.env.example`, `chmod 600`. Задать отдельные staging PostgreSQL password, Fernet key, DOMAIN/ACME_EMAIL и только разрешенные LIVE secrets. Не использовать DEMO seed или DEMO credentials.

## 4. Compose, migrations и admin

```bash
cd /opt/copilot-staging/app
docker compose --env-file /etc/copilot-staging/.env.production -f infra/compose.prod.yml -f infra/compose.vps-4gb.yml config --quiet
docker compose --env-file /etc/copilot-staging/.env.production -f infra/compose.prod.yml -f infra/compose.vps-4gb.yml build
docker compose --env-file /etc/copilot-staging/.env.production -f infra/compose.prod.yml -f infra/compose.vps-4gb.yml up -d postgres
docker compose --env-file /etc/copilot-staging/.env.production -f infra/compose.prod.yml -f infra/compose.vps-4gb.yml up -d migrate
docker compose --env-file /etc/copilot-staging/.env.production -f infra/compose.prod.yml -f infra/compose.vps-4gb.yml ps
```

Проверить успешный exit one-shot migrate и схему БД. Затем создать отдельного admin через защищенную env-сессию, без пароля в command line:

```bash
docker compose --env-file /etc/copilot-staging/.env.production -f infra/compose.prod.yml -f infra/compose.vps-4gb.yml run --rm \
  -e COPILOT_ADMIN_ORGANIZATION_SLUG \
  -e COPILOT_ADMIN_ORGANIZATION_NAME \
  -e COPILOT_ADMIN_EMAIL \
  -e COPILOT_ADMIN_PASSWORD \
  api python backend/scripts/create_initial_user.py
```

После этого запустить API/frontend/Caddy:

```bash
docker compose --env-file /etc/copilot-staging/.env.production -f infra/compose.prod.yml -f infra/compose.vps-4gb.yml up -d
```

## 5. DNS и HTTPS

1. Создать DNS A/AAAA staging hostname на публичный IP VPS.
2. Открыть 80/443 только после проверки существующего proxy/firewall.
3. Дождаться ACME certificate от Caddy.
4. Проверить сертификат и hostname через внешний клиент, не только localhost.

## 6. Staging acceptance

```bash
curl --fail "https://$DOMAIN/healthz"
curl --fail "https://$DOMAIN/readyz"
curl --fail "https://$DOMAIN/"
```

Проверить login → Dashboard → source detail → logout на desktop и mobile. Убедиться:

- HttpOnly/Secure/SameSite cookie;
- CSRF rejection для чужого Origin;
- login rate limit;
- trusted forwarded proto только от внутреннего proxy subnet;
- `database=ok` в `/readyz`;
- отсутствие секретов в `docker compose logs`;
- PostgreSQL не имеет published port и недоступен извне.

## 7. Persistence и backup/restore

1. Выполнить login и записать идентификатор synthetic тестового источника.
2. Перезапустить `docker compose ... down && docker compose ... up -d` без `down -v`.
3. Проверить сохранность admin session-independent user data и Dashboard.
4. Создать backup:

```bash
ENV_FILE=/etc/copilot-staging/.env.production infra/scripts/backup_postgres.sh /var/backups/copilot-staging
```

5. Восстановить в отдельную тестовую БД и сравнить user/connection/source/analysis, затем проверить Fernet decrypt через `release_credential_check.py`. Не выполнять destructive restore в основную БД.
6. Сохранить off-VPS копию и ограничить доступ к backups.

## 8. Rollback

- Зафиксировать предыдущий `APP_VERSION` и image digests.
- При failed healthchecks остановить rollout и вернуть предыдущий `APP_VERSION` через `up -d`, не удаляя volumes.
- Rollback image не отменяет миграции; DB rollback требует отдельного согласованного restore/forward-fix плана.
- Не делать `down -v`, force push или production downgrade автоматически.

## 9. Реальные интеграции — отдельное разрешение

GigaChat smoke выполняется только после явного подтверждения стоимости с `COPILOT_GIGACHAT_DAILY_REQUEST_LIMIT=1` и `GIGACHAT_ENABLED=true` через `backend/scripts/gigachat_smoke.py --confirm-live`.

Yandex IMAP проверяется только на отдельном тестовом mailbox с отдельным app password и `--confirm-read-only --limit 1`. Не читать персональные письма. После smoke отозвать доступ и удалить app password.

## Фактические результаты на момент подготовки

- RC1 и release smoke проверены локально: 53 backend tests, 7 frontend unit, 4 Playwright, production builds, реальный backup/restore и Fernet verification.
- VPS, DNS, firewall, production migrations, public ACME, live GigaChat и реальная Яндекс Почта **не выполнялись**.
