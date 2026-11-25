# Фактическое состояние проекта

Дата аудита: 25.11.2026.

База аудита: `main` / `origin/main`, commit `26ebfa6bf4c1611982eb29f95f1fa6ddeb52a03a`.
Аудит выполняется в ветке `feat/mvp-phase0-audit`.

## 1. Вывод

Репозиторий находится в состоянии **bootstrap**, а не MVP. Работоспособен минимальный FastAPI API с одним endpoint `GET /healthz` и одним unit-тестом. Docker-образ API собирается и возвращает ожидаемый ответ. PostgreSQL, Redis и Qdrant только объявлены в development Compose; приложение с ними не связано. GigaChat, хранение данных, авторизация, React Dashboard и Telegram-бот не реализованы.

Первый сквозной результат должен доказать сценарий:

`вход пользователя → синтетическое сообщение → структурированный анализ GigaChat → сохранение результата в PostgreSQL → Dashboard с дайджестом и ссылкой на источник`.

До последнего шага допустимы только mock-вызовы GigaChat. Live smoke выполняется отдельно, после явного разрешения владельца и настройки секретов вне Git.

## 2. Проверенная структура и реализация

| Компонент | Фактическое состояние | Подтверждение |
|---|---|---|
| FastAPI | Создано приложение `AI Executive Co-pilot API` версии `0.1.0`; есть только `GET /healthz`, возвращающий `{"status":"ok"}` | `backend/src/copilot_api/main.py` |
| Backend-тесты | Один тест проверяет статус и тело `/healthz`; локально `1 passed` | `backend/tests/test_health.py` |
| Python-зависимости | Runtime: FastAPI и Uvicorn; dev: pytest, httpx, Ruff. Указан Python `>=3.13,<3.14` | `backend/pyproject.toml` |
| GigaChat | Нет адаптера, OAuth, моделей результата, вызовов API или тестов | Отсутствует в tracked-файлах и зависимостях |
| PostgreSQL / SQLAlchemy / Alembic | Нет моделей, session/engine, репозиториев, миграций и зависимостей | Отсутствует в `backend/` |
| Авторизация и tenant isolation | Нет login/session, tenant/user и проверок `tenant_id` / `owner_id` | Отсутствует в `backend/` |
| Celery / Redis | Нет worker, scheduler, tasks, outbox или кода клиента Redis | Отсутствует в `backend/` |
| Qdrant | Нет коллекции, адаптера, индексации или поиска | Отсутствует в `backend/` |
| React Dashboard | Только README-заглушка; нет `package.json`, lock-файла, исходников, сборки и тестов | `frontend/README.md` |
| Telegram / aiogram | Только README-заглушка; нет webhook, обработчиков и зависимости aiogram | `bot/README.md` |
| API Dockerfile | Образ на `python:3.13-slim`, установка backend-пакета, запуск от UID `10001`; локальная сборка успешна | `backend/Dockerfile` |
| Development Compose | Объявлены `api`, `postgres:17-alpine`, `redis:7-alpine`, `qdrant/qdrant:v1.20.2`; порты опубликованы только на `127.0.0.1`; есть named volumes | `infra/compose.dev.yml` |
| GitLab CI | Secret Detection template; backend jobs выполняют установку зависимостей, `compileall`, `ruff check` и `pytest` | `.gitlab-ci.yml` |
| Production / VPS | Нет production Compose, reverse proxy, HTTPS, backup/restore и deploy job; VPS не подключался | Tracked-файлы `infra/`, `.gitlab-ci.yml` |

## 3. Проблемы и ограничения

### Функциональные

1. Нет доменных API, persistence, авторизации и изоляции данных; `/healthz` не доказывает готовность MVP.
2. Нет `/readyz`, конфигурации через `pydantic-settings`, request IDs и единого формата ошибок.
3. Compose не передает API параметры подключения к PostgreSQL/Redis/Qdrant и не задает `depends_on`; у `api` нет container healthcheck.
4. PostgreSQL, Redis и Qdrant не используются кодом. Их наличие в Compose нельзя считать реализованной интеграцией.
5. Нет frontend и backend CI для frontend, E2E, миграций, Docker build или проверки Compose.
6. Нет версионированной архитектуры v1.1: `docs/architecture/README.md` содержит только просьбу добавить документ.
7. Документы `BOARD_ITERATION_2.md`, `ITERATION2_SCOPE_AND_ACCEPTANCE.md`, `DECISIONS_DRAFT.md` и `VPS_DEPLOY_RUNBOOK.md`, упомянутые в handoff-инструкции, отсутствуют в tracked `docs/` текущего `main`. Они найдены только в неотслеживаемом `AI_Copilot_MVP_Handoff/` и не являются содержимым базового commit.

### Воспроизводимость и эксплуатация

1. Для Python и Docker-образов нет lock/constraints-файла; диапазоны зависимостей и mutable base tag не фиксируют повторяемый набор артефактов.
2. Во время аудита установились FastAPI `0.165.0`, pytest `9.2.0` и Ruff `0.17.6`; тест выдал `StarletteDeprecationWarning` о переходе TestClient с `httpx` на `httpx2`. Это предупреждение, не падение.
3. Development Compose не является production-конфигурацией: нет HTTPS, secrets management, backup/restore, resource limits и полноценных healthchecks.
4. Состояние удаленных GitLab pipeline, protected branches и GitHub mirror по API/UI не проверялось. Проверены локальный CI YAML, URL `origin` и совпадение `main` с `origin/main` после fetch.

## 4. Выполненные локальные проверки

Среда: Windows, Python Launcher с Python 3.13, Docker `29.4.3`, Docker Compose `v5.1.3`. Системная команда `python` указывала на Python `3.14.6` без pip, поэтому для соответствия `pyproject.toml` создано окружение через `py -3.13`.

| Проверка / команда | Результат |
|---|---|
| `git fetch origin --prune` | Успешно; `HEAD` и `origin/main` совпали на `26ebfa6` |
| `git remote -v` | `origin` для fetch и push указывает на GitLab; GitHub remote не настроен |
| `py -3.13 -m venv backend/.venv` | Успешно; каталог исключен через `.gitignore` |
| `backend/.venv/Scripts/python.exe -m pip install --disable-pip-version-check -e './backend[dev]'` | Успешно |
| `backend/.venv/Scripts/python.exe -m compileall -q backend/src backend/tests` | Успешно |
| `backend/.venv/Scripts/python.exe -m ruff check backend` | `All checks passed!` |
| `backend/.venv/Scripts/python.exe -m ruff format --check backend` | `3 files already formatted` |
| `backend/.venv/Scripts/python.exe -m pytest -q backend/tests` | `1 passed, 1 warning in 0.24s` |
| `backend/.venv/Scripts/python.exe -m pip check` | `No broken requirements found.` |
| `POSTGRES_USER=copilot POSTGRES_DB=copilot POSTGRES_PASSWORD=local_audit_only docker compose -f infra/compose.dev.yml config --quiet` | Успешно; пароль является фиктивным значением только для проверки |
| `... docker compose -f infra/compose.dev.yml config --services` | Получены `api`, `postgres`, `qdrant`, `redis` |
| `docker info --format '{{.ServerVersion}}'` | До запуска Docker Desktop: engine недоступен; после запуска: `29.4.3` |
| `... docker compose -p copilot-phase0-audit -f infra/compose.dev.yml up --build -d api` | API image собран, изолированный контейнер запущен |
| `curl --silent --show-error --fail http://127.0.0.1:8000/healthz` | После ожидания старта получено `{"status":"ok"}` |
| `... docker compose -p copilot-phase0-audit -f infra/compose.dev.yml down` | Созданные API-контейнер и сеть остановлены и удалены |

Сокращение `...` в таблице обозначает те же три фиктивные переменные окружения, что в команде `config --quiet`.

## 5. Что не проверено

- Live GigaChat OAuth и completions: не выполнялись, реальные ключи не использовались, платных запросов не было.
- Полный `docker compose up`: PostgreSQL, Redis и Qdrant не запускались; проверены их YAML-декларации, но не runtime и не интеграция с API.
- Миграции, запросы к БД, tenant isolation, auth, Telegram, Qdrant и Celery: соответствующая реализация отсутствует.
- Frontend lint/test/build и браузерный E2E: frontend-инструментарий и приложение отсутствуют.
- Удаленный GitLab CI и настройки зеркала: внешние UI/API не запрашивались.
- Production deploy и VPS: не выполнялись.

## 6. План первой сквозной реализации

Порядок: **FastAPI → GigaChat → PostgreSQL → React Dashboard**. Каждый этап — отдельный небольшой MR с тестами; live GigaChat не нужен для разработки и CI.

### Этап 1. FastAPI application backbone

- Добавить `pydantic-settings`, версионированный API router, `/healthz`, `/readyz`, request ID и безопасный единый error response без секретов и stacktrace.
- Зафиксировать Pydantic-контракты `AttentionItem`, `Digest`, `IntegrationStatus` и source detail; добавить только синтетические fixtures с явной маркировкой `DEMO`.
- Определить интерфейс application service, чтобы следующие адаптеры не внедрялись в HTTP handlers напрямую.
- Проверки: unit-тесты контрактов, ошибок и request ID; существующий health-тест; Ruff.

### Этап 2. GigaChatProvider

- Реализовать отдельный provider и OAuth adapter для официальных endpoints: `https://ngw.devices.sberbank.ru:9443/api/v2/oauth` и `https://api.giga.chat`.
- Обеспечить TLS verification, timeout, уникальный `RqUID` (`uuid4`) на OAuth-запрос, кэширование токена до истечения, одно обновление после 401 и запрет логирования токенов/содержимого.
- Валидировать структурированный ответ через Pydantic: score, summary, next step, source timestamp; ошибки классифицировать, fallback явно маркировать как non-live.
- Все автоматические тесты использовать с mock HTTP transport: успех, timeout, 401/refresh, 429, 5xx, malformed JSON, отсутствие секрета.
- Live `/v1/models` и один синтетический completion — только отдельный ручной smoke после разрешения владельца.

### Этап 3. PostgreSQL и серверная авторизация

- Добавить SQLAlchemy 2, PostgreSQL driver и Alembic; настроить engine/session и `readyz` с реальной проверкой БД.
- Создать миграцию для tenant/user, server session, integration, source message/event, digest/action item, outbox/audit. Обязательные `tenant_id` и `owner_id`, constraints и индексы закладываются сразу.
- Реализовать ограниченный login с безопасной серверной сессией; repository/service queries принимают контекст tenant/owner и не полагаются на фильтр клиента.
- Связать application flow: synthetic input → provider → transaction в PostgreSQL → API читает сохраненный digest. Идемпотентность обеспечивается source external ID и tenant/owner scope.
- Проверки на одноразовой БД: upgrade/downgrade/upgrade, повтор импорта без дублей, ошибка provider без ложного успеха, изоляция пользователей A/B и tenant A/B.

### Этап 4. React Dashboard и E2E

- Инициализировать React + TypeScript + Vite с committed lock-файлом; не хранить секреты в браузере.
- Реализовать login, Dashboard «Требует внимания», карточку интеграций и source detail. Карточка содержит score, summary, next step, timestamp и ссылку на источник; synthetic data визуально помечается `DEMO`.
- Добавить loading/empty/error states, клавиатурную доступность и адаптивный mobile viewport. PWA подключается после основного сценария, если не задерживает поставку.
- Добавить frontend unit tests, `tsc`, production build и E2E `login → dashboard → source detail` против API с mock provider и тестовой PostgreSQL.
- После реализации отдельным согласованным изменением включить frontend и E2E jobs в GitLab CI.

### Что не входит в первый slice

Telegram/Yandex connectors, Celery workers/scheduler, Qdrant semantic search, production/VPS deploy и автономные действия AI. Они разрабатываются после проверенного сквозного сценария отдельными задачами.

## 7. Два первых deliverable

1. **MR «FastAPI backbone»**: настройки, routers, `/healthz` и `/readyz`, request IDs, typed API contracts, error handling и unit-тесты. Не требует внешних секретов.
2. **MR «Mock-tested GigaChatProvider»**: OAuth/token lifecycle, typed structured output, timeouts/errors и полный unit-набор на mock transport. Live smoke остается отдельной ручной операцией и не блокирует merge mock-tested адаптера.

Критерий завершения всего slice: два синтетических пользователя могут войти только в свои данные; анализ сообщения через mock-tested provider сохраняется в PostgreSQL; Dashboard отображает результат и source detail; повтор сообщения не создает дубликат; backend/frontend/E2E проверки воспроизводятся на чистом clone. Live GigaChat подтверждается отдельным протоколом, а не подменяется mock-результатом.
