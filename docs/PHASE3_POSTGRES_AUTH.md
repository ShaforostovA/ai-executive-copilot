# Phase 3 — PostgreSQL и серверная авторизация

## Цель

Заменить DEMO repository PostgreSQL 17-адаптером, добавить Alembic-миграции, серверные сессии и обязательную organization/owner isolation. Phase 3 остается модульным монолитом и не активирует live GigaChat автоматически.

## Модель данных

- `organizations`: tenant, уникальный slug.
- `users`: пользователь организации, normalized email, scrypt password hash, active flag.
- `connections`: источник владельца, provider/status/last sync/data origin.
- `source_messages`: исходное сообщение владельца; уникальность `(organization_id, owner_id, source_type, external_id)` обеспечивает идемпотентный импорт.
- `analysis_results`: результат анализа сообщения; один результат на `source_message_id`, score/summary/reason/next step/model/data origin.
- `auth_sessions`: SHA-256 hash случайного session token, user, expiry и timestamps. Исходный token существует только в HttpOnly cookie и памяти запроса.

Все dashboard/source/integration queries фильтруются по `organization_id` и `owner_id`. Получение source по UUID без этих условий не используется.

## API и инфраструктура

- `POST /api/v1/auth/login`: organization slug + email + password; создает server-side session и Secure-by-default HttpOnly SameSite=Lax cookie.
- `POST /api/v1/auth/logout`: удаляет server-side session и очищает cookie.
- `GET /api/v1/auth/me`: текущий authenticated principal.
- Dashboard/integration/source endpoints требуют authenticated principal.
- `/healthz` остается liveness без БД.
- `/readyz` в PostgreSQL-режиме выполняет `SELECT 1`; ошибка БД дает `503` и `database=error`. В явном DEMO-режиме database check обозначается `disabled`.
- DEMO repository и production взаимоисключаются на уровне настроек. Тестовые dependency overrides не являются production auth bypass.

## Основные файлы

- `infrastructure/database/`: SQLAlchemy Base/models, async engine и PostgreSQL repository.
- `services/auth.py`: credentials validation, session lifecycle и principal resolution.
- `core/security.py`: scrypt password hashing, random session tokens и token hashing.
- `schemas/auth.py`: login/principal contracts без session token в response body.
- `routers/auth.py`: cookie login/logout/me.
- `backend/alembic/`: async Alembic environment и initial migration.
- `backend/tests/integration/`: реальные PostgreSQL migration/auth/isolation/idempotency/readiness tests.
- `backend/scripts/seed_demo_data.py`: явный development-only synthetic seed, запрещенный в production.
- `infra/compose.dev.yml`: PostgreSQL URL, health dependency и dev migrations перед API startup.

## Проверки и критерии приемки

1. Alembic `downgrade base` и `upgrade head` успешны на чистой PostgreSQL 17.
2. Повторная запись одинакового source event возвращает существующую запись и не создает дубликат.
3. Пользователь A не видит данные пользователя B той же организации; пользователь организации B не видит данные организации A.
4. Session token не хранится в БД в исходном виде и не возвращается в JSON; cookie HttpOnly/SameSite, Secure обязателен в production.
5. Неверные credentials дают одинаковый `401`; logout делает cookie бесполезным.
6. DashboardService работает через PostgreSQL repository и возвращает только собственные digest/source/integration данные.
7. `/readyz` успешен только при фактическом `SELECT 1` в PostgreSQL-режиме.
8. Unit-тесты без Docker продолжают проходить; integration-тесты с `COPILOT_TEST_DATABASE_URL` выполняются на реальном PostgreSQL.
9. Ruff, compileall, Pytest, pip check, Compose config, Docker build и authenticated HTTP smoke успешны.
10. CI/CD не изменяется; live GigaChat и production VPS не вызываются.

## Запуск integration-тестов

После запуска изолированного PostgreSQL 17:

```bash
export COPILOT_TEST_DATABASE_URL='postgresql+asyncpg://<test-user>:<test-password>@127.0.0.1:5432/<test-db>'
pytest -q backend/tests
```

Без переменной PostgreSQL integration-тесты явно пропускаются, а не заменяются SQLite. GitLab CI содержит отдельный `backend:test:postgresql` job с одноразовым PostgreSQL 17 service; полный PostgreSQL suite также проверяется локально в Docker до MR.

## Synthetic development login

Seed разрешен только при `COPILOT_ENVIRONMENT=development` или `test` и требует локально заданный `COPILOT_DEMO_SEED_PASSWORD` длиной не менее 12 символов. Он не содержит встроенного пароля и отказывается запускаться в production.

После миграций выполните:

```bash
python backend/scripts/seed_demo_data.py
```

Скрипт идемпотентно создает организацию `demo`, пользователя `demo@example.test`, NOT_CONFIGURED connection, synthetic source и DEMO analysis. Пароль выводится только из локальной переменной и не печатается. Login выполняется через `POST /api/v1/auth/login` с JSON-полями `organization_slug`, `email`, `password`; session token присутствует только в HttpOnly cookie, не в JSON.
