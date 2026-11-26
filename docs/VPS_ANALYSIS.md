# VPS Analysis — staging deployment

Дата диагностики: 26.11.2026. Документ содержит только обезличенные результаты; raw diagnostic file не включается в Git, MR или публичную документацию.

## Фактическое состояние

| Область | Результат диагностики |
|---|---|
| Ubuntu | 24.04 LTS (Noble Numbat) |
| Архитектура | x86_64, KVM virtual machine |
| CPU | 2 virtual CPUs |
| RAM | 3.8 GiB total, 3.4 GiB available на момент проверки |
| Swap | 512 MiB total, полностью свободен |
| Disk | 59 GiB total, 54 GiB свободно, 6% использовано |
| Docker Engine / Compose | Не установлены |
| containerd | Пакет отсутствует, service inactive |
| Nginx / Caddy | Пакеты отсутствуют, services inactive |
| SSH | Только порт 22 listening; менять его нельзя без отдельного плана |
| Ports 80/443 | Свободны |
| UFW | Inactive |
| nftables | Пустой ruleset |
| Существующие конфликты | Не обнаружены |
| Network | `download.docker.com` и `github.com` возвращают HTTP 200 |
| Staging DNS | DOMAIN не был задан во время диагностики |

## Проблемы и риски

1. **Базовый memory budget 3.25 GiB слишком велик.** При available 3.4 GiB он оставляет около 150 MiB для ОС и роста рабочей нагрузки. Swap 512 MiB не устраняет риск OOM/throttling.
2. Docker и Compose отсутствуют, поэтому сначала требуется установка официальными пакетами Docker.
3. UFW выключен. Открытие 80/443 публично требует отдельного согласованного правила; PostgreSQL и internal services нельзя публиковать.
4. Существующего proxy нет, поэтому Caddy может работать напрямую без миграции существующей конфигурации.
5. Домен и DNS еще не определены. Публичный ACME невозможен до их предоставления.
6. При пиковой нагрузке возможна нехватка RAM. Следить за memory pressure, container restarts и swap usage.

## Пригодность

Сервер подходит для **staging с memory-tuned profile**, но не для запуска базового Compose с лимитом 3.25 GiB. Для production workload с ростом данных и внешних LLM/почтовых интеграций рекомендуется минимум 6 GiB RAM, предпочтительно 8 GiB.

Добавлен `infra/compose.vps-4gb.yml`:

| Service | Limit |
|---|---:|
| PostgreSQL | 768 MiB |
| migrate | 384 MiB |
| API | 768 MiB |
| frontend | 192 MiB |
| Caddy | 192 MiB |
| **Total** | **2.25 GiB** |

Профиль оставляет около 1.15 GiB по доступной памяти на момент диагностики для ОС и временных пиков. Он не является гарантией отсутствия OOM при тяжелых миграциях/запросах; требуется мониторинг.

## Последовательность установки

1. Проверить отсутствие изменений: порты 80/443 по-прежнему свободны, SSH 22 доступен, network и disk не деградировали.
2. Установить Docker Engine, Buildx и Compose Plugin только по https://docs.docker.com/engine/install/ubuntu/:
   - apt prerequisites `ca-certificates`, `curl`;
   - официальный Docker GPG key и apt repository;
   - `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, `docker-compose-plugin`;
   - `systemctl enable --now docker`;
   - проверить `docker --version`, `docker compose version` и `docker run --rm hello-world`.
3. Не добавлять пользователя в `docker` group автоматически и не менять SSH/VPN/firewall.
4. Создать `/opt/copilot-staging`, `/etc/copilot-staging`, `/var/backups/copilot-staging`; env и backups ограничить `chmod 600/700`.
5. Проверить `v0.1.0-rc1`, protected env, DOMAIN/ACME_EMAIL и отдельные staging secrets. DEMO seed не использовать.
6. Использовать production Compose **обязательно с** `infra/compose.vps-4gb.yml`.
7. Запустить PostgreSQL, migrations, secure initial admin, API/frontend/Caddy.
8. Настроить DNS и только потом публичный HTTPS; проверить healthz/readyz, login/dashboard/source/logout и persistence.
9. Настроить backup, проверить restore в отдельную БД и сохранить off-VPS copy.

## Первый staging deployment — форма команд

```bash
cd /opt/copilot-staging/app
git checkout v0.1.0-rc1
export COMPOSE_FILE=infra/compose.prod.yml:infra/compose.vps-4gb.yml
docker compose --env-file /etc/copilot-staging/.env.production config --quiet
docker compose --env-file /etc/copilot-staging/.env.production build
docker compose --env-file /etc/copilot-staging/.env.production up -d postgres
docker compose --env-file /etc/copilot-staging/.env.production up -d migrate
docker compose --env-file /etc/copilot-staging/.env.production run --rm \
  -e COPILOT_ADMIN_ORGANIZATION_SLUG \
  -e COPILOT_ADMIN_ORGANIZATION_NAME \
  -e COPILOT_ADMIN_EMAIL \
  -e COPILOT_ADMIN_PASSWORD \
  api python backend/scripts/create_initial_user.py
docker compose --env-file /etc/copilot-staging/.env.production up -d
curl --fail "https://$DOMAIN/healthz"
curl --fail "https://$DOMAIN/readyz"
```

`COMPOSE_FILE` задает оба файла и не требует повторять `-f` в каждой команде. Эти команды не выполнялись на VPS.

## Необходимо от владельца перед запуском

- Staging hostname и DNS A/AAAA на публичный IP VPS.
- Подтверждение разрешения на открытие 80/443 и настройку firewall.
- Отдельный способ передачи secrets, не через Git или общий чат.
- Подтверждение, что memory-tuned profile 2.25 GiB приемлем; иначе увеличить VPS RAM.
- Подтверждение backup/offsite storage и rollback window.
- Отдельное разрешение на live GigaChat и read-only Yandex IMAP; оно не требуется для базового staging без live integrations.
