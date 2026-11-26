# Release Readiness — Ubuntu VPS 4 GB RAM

Дата проверки: 26.11.2026. Статус: **release candidate готов локально**, production rollout не выполнялся.

## Фактические результаты

| Область | Результат | Подтверждение |
|---|---|---|
| Production Compose | PASS | `infra/compose.prod.yml` и smoke override валидны; PostgreSQL не имеет published port |
| Production builds | PASS | Backend/migrate и frontend images собраны с lockfiles |
| Initial migration | PASS | One-shot migrate завершился перед healthy API |
| Initial user | PASS | `create_initial_user.py` создал synthetic admin без встроенного пароля |
| Backup/restore | **PASS, реальный** | `pg_dump -Fc` и `pg_restore --clean --if-exists` в отдельную `release_restore_*` БД |
| Yandex encryption | **PASS, реальный** | Ciphertext восстановлен из restore; Fernet decrypt вернул ожидаемые synthetic username/password; plaintext не выводился |
| HTTPS | PASS для release smoke | Caddy internal CA, `curl --cacert` и hostname `mvp.release.test`; ACME/public HTTPS еще не проверялся |
| CORS | PASS | Разрешенный origin возвращается при preflight через Caddy/Nginx |
| CSRF | PASS | `https://attacker.example` получил `403` |
| Cookie | PASS | `HttpOnly`, `Secure`, `SameSite=lax` при login через HTTPS |
| Login rate limit | PASS | Повторные запросы получили `429` после лимита |
| Trusted proxy | PASS | Uvicorn middleware принимает forwarded proto только от allowlist; 2 unit-теста |
| Memory | PASS | `ps -aq` + `docker inspect`: API 1 GiB, PostgreSQL 1 GiB, migrate 512 MiB, frontend 256 MiB, Caddy 256 MiB; всего 3.25 GiB |
| Backend suite | PASS | 53 теста, включая 12 PostgreSQL integration tests |
| Frontend | PASS | 7 unit tests, lint/typecheck/build, npm audit 0 |
| Browser E2E | PASS | 4 desktop/mobile tests против реального backend; отдельный GitLab job также прошел |
| Secrets scan | PASS | Реальных ключей в diff не найдено; release values только фиктивные |

`infra/scripts/release_smoke.sh` был выполнен от начала до конца и повторил все отмеченные smoke checks автоматически. Временные backup/cert artifacts игнорируются Git и удаляются при необходимости; production data не использовались.

## Критерии, оставшиеся PENDING перед production

- Предоставлены домен, DNS A/AAAA и доступ к Ubuntu VPS.
- Public ACME certificate и внешний HTTPS smoke.
- Фактические VPS CPU/RAM/disk/ports/firewall проверены владельцем.
- Off-VPS backup copy и отдельное разрешение на destructive restore drill.
- Отдельное разрешение владельца на live GigaChat и read-only Yandex IMAP.
- Review и merge release MR.

## Повторяемый release smoke

Используются только фиктивные значения. Скрипт создает и останавливает isolated Compose project, выполняет backup/restore в новую одноразовую БД, проверяет Fernet, HTTPS internal CA, CORS/CSRF/cookie/rate limit и memory limits.

```bash
export POSTGRES_USER=copilot
export POSTGRES_DB=copilot
export POSTGRES_PASSWORD=release_only_password
export CREDENTIAL_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export COPILOT_ADMIN_ORGANIZATION_SLUG=release
export COPILOT_ADMIN_ORGANIZATION_NAME=ReleaseTest
export COPILOT_ADMIN_EMAIL=admin@release.test
export COPILOT_ADMIN_PASSWORD=release_admin_only_password
export RELEASE_YANDEX_PASSWORD=release_yandex_only_password
export RESTORE_DB=release_restore_$(date +%s)
infra/scripts/release_smoke.sh
```

На Windows Schannel допускается `RELEASE_CURL_NO_REVOKE=1`: отключается только проверка отзыва internal test CA, не TLS/hostname verification. На Ubuntu это не требуется.

## Ubuntu rollout — команды для будущего согласованного запуска

### 1. Диагностика

```bash
cat /etc/os-release
uname -m
nproc
free -h
df -h
ss -ltnp
systemctl list-units --type=service --state=running
docker --version || true
docker compose version || true
```

Не менять существующие proxy, VPN, firewall или занятые порты до фиксации плана и отката.

### 2. Установка Docker Engine и Compose Plugin

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

Добавление пользователя в `docker` group выполнять отдельно с пониманием root-equivalent риска; не завершать текущую SSH-сессию до проверки доступа.

### 3. Каталоги и secrets

```bash
sudo mkdir -p /opt/copilot /etc/copilot /var/backups/copilot
sudo chmod 755 /opt/copilot
sudo chmod 700 /etc/copilot /var/backups/copilot
sudo cp .env.example /etc/copilot/.env.production
sudo chmod 600 /etc/copilot/.env.production
```

Заполнить через защищенный канал: DOMAIN, ACME_EMAIL, новый PostgreSQL password, Fernet key и только разрешенные integration secrets. Не копировать `.env.production` в Git, backup images, logs или chat. LIVE GigaChat остается `GIGACHAT_ENABLED=false` до разрешения.

### 4. DNS и HTTPS

Настроить A/AAAA `app.<domain>` на публичный IP VPS. Открыть 80/443 только после проверки текущего proxy/firewall. Caddy получит ACME certificate автоматически через `infra/Caddyfile`.

### 5. Запуск и initial admin

```bash
cd /opt/copilot
docker compose --env-file /etc/copilot/.env.production -f infra/compose.prod.yml config --quiet
docker compose --env-file /etc/copilot/.env.production -f infra/compose.prod.yml build
docker compose --env-file /etc/copilot/.env.production -f infra/compose.prod.yml up -d
docker compose --env-file /etc/copilot/.env.production -f infra/compose.prod.yml ps
```

One-shot migrate должен завершиться успешно до API. Затем, используя защищенную admin-сессию env (не значения в command line):

```bash
docker compose --env-file /etc/copilot/.env.production -f infra/compose.prod.yml run --rm \
  -e COPILOT_ADMIN_ORGANIZATION_SLUG \
  -e COPILOT_ADMIN_ORGANIZATION_NAME \
  -e COPILOT_ADMIN_EMAIL \
  -e COPILOT_ADMIN_PASSWORD \
  api python backend/scripts/create_initial_user.py
```

Пароль должен быть уникальным, не коротким и не DEMO. Не записывать его в shell history, Git или логи.

### 6. Проверка и мониторинг

```bash
curl --fail "https://$DOMAIN/healthz"
curl --fail "https://$DOMAIN/readyz"
docker compose --env-file /etc/copilot/.env.production -f infra/compose.prod.yml ps
docker compose --env-file /etc/copilot/.env.production -f infra/compose.prod.yml logs --tail=100 api
docker compose --env-file /etc/copilot/.env.production -f infra/compose.prod.yml logs --tail=100 caddy
```

Проверить login/logout, Dashboard, mobile viewport, CSRF/CORS, отсутствие секретов в logs и backup расписание. `readyz` должен возвращать `database=ok`.

## Backup и rollback

Перед каждым update/migration:

```bash
ENV_FILE=/etc/copilot/.env.production infra/scripts/backup_postgres.sh /var/backups/copilot
```

Проверить restore на отдельной БД, сохранить off-VPS copy. Image rollback выполняется через предыдущий `APP_VERSION` и не отменяет миграции. Destructive restore только с новым backup и `RESTORE_CONFIRM=yes` после отдельного разрешения.

## Статус внешних действий

VPS, DNS, firewall, production migrations, restore, live GigaChat и реальная Яндекс Почта не выполнялись.
