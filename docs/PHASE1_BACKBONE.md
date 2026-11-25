# Phase 1 — FastAPI Backbone

## Цель и границы

Создать модульную основу модульного монолита для следующих адаптеров GigaChat и PostgreSQL. Phase 1 не реализует live-интеграции, авторизацию и persistence. Единственный источник данных на этом этапе — явно маркированные синтетические `DEMO` fixtures.

## API-контракты

- `GET /healthz` — liveness процесса, без зависимости от внешних сервисов.
- `GET /readyz` — readiness HTTP-приложения; в Phase 1 обязательных внешних зависимостей нет, поэтому проверка не объявляет PostgreSQL или GigaChat доступными.
- `GET /api/v1/dashboard` — текущий synthetic `Digest` с attention items и integration statuses.
- `GET /api/v1/integrations` — synthetic статусы интеграций; реальные источники обозначены как `NOT_CONFIGURED`.
- `GET /api/v1/sources/{source_id}` — synthetic source detail или единый error response `404`.
- Каждый ответ содержит `X-Request-ID`; допустимый входящий ID сохраняется, недопустимый заменяется UUID.
- Ошибки HTTP, валидации и необработанные исключения возвращают единый JSON-контракт `ErrorResponse` без stacktrace.

## План файлов

### Конфигурация и сборка

- `backend/pyproject.toml` — добавить `pydantic-settings` в runtime dependencies.
- `.env.example` — добавить только нечувствительные настройки приложения с префиксом `COPILOT_`.
- `backend/src/copilot_api/main.py` — application factory и регистрация модулей.

### Core

- `backend/src/copilot_api/core/config.py` — `pydantic-settings`, значения по умолчанию и чтение окружения.
- `backend/src/copilot_api/core/middleware.py` — генерация, проверка и propagation request ID.
- `backend/src/copilot_api/core/errors.py` — обработчики HTTP/validation/internal ошибок.

### Схемы

- `backend/src/copilot_api/schemas/common.py` — `DataOrigin` и integration state.
- `backend/src/copilot_api/schemas/dashboard.py` — `AttentionItem`, `Digest`, `IntegrationStatus`, `SourceDetail`.
- `backend/src/copilot_api/schemas/health.py` — liveness/readiness responses.
- `backend/src/copilot_api/schemas/errors.py` — единый error response и validation details.

### Сервисы и инфраструктура

- `backend/src/copilot_api/services/interfaces.py` — Protocols `AnalysisProvider` для будущего GigaChat и `DashboardRepository` для будущего PostgreSQL.
- `backend/src/copilot_api/services/dashboard.py` — application service, изолированный от FastAPI и конкретного хранилища.
- `backend/src/copilot_api/services/dependencies.py` — composition root для FastAPI dependencies.
- `backend/src/copilot_api/infrastructure/demo_repository.py` — read-only synthetic repository; не является реализацией PostgreSQL или внешнего connector.

### Routers

- `backend/src/copilot_api/routers/health.py` — `/healthz` и `/readyz`.
- `backend/src/copilot_api/routers/dashboard.py` — версионированные dashboard/integration/source endpoints.
- `backend/src/copilot_api/routers/__init__.py` — сборка API v1 router.

### Тесты

- `backend/tests/conftest.py` — изолированный app/TestClient без чтения локального `.env`.
- `backend/tests/test_health.py` — liveness, readiness и request IDs.
- `backend/tests/test_dashboard.py` — контракты, DEMO-маркировка и source detail.
- `backend/tests/test_errors.py` — `404`, `405`, `422`, `500`, request ID и отсутствие раскрытия исключения.
- `backend/tests/test_config.py` — defaults и environment override.
- `backend/tests/test_schemas.py` — границы score и обязательность timezone-aware timestamps.

## Критерии приемки

1. Все endpoints возвращают заявленные Pydantic v2 response models; префикс `/api/v1` применяется только к versioned API.
2. Каждый synthetic объект Digest/AttentionItem/IntegrationStatus/SourceDetail имеет `data_origin = "DEMO"`; integration fixtures не утверждают наличие подключения.
3. `AnalysisProvider` не имеет фиктивной live-реализации; `DashboardRepository` используется через Protocol и может быть заменен PostgreSQL-адаптером.
4. `/healthz` не проверяет внешние сервисы; `/readyz` отражает готовность приложения и не содержит фиктивных database checks.
5. Error responses имеют поля `error.code`, `error.message`, `error.request_id` и опциональные structured details; внутреннее сообщение исключения не раскрывается.
6. Request ID из доверенного формата сохраняется, некорректный заменяется; response header и error payload согласованы.
7. Настройки читаются из `COPILOT_*`; тесты не зависят от пользовательского `.env`.
8. `compileall`, Ruff lint/format, Pytest и `pip check` проходят; Docker build и HTTP smoke проверяют реальный запуск.
9. GitLab CI/CD не изменяется; Phase 1 не отправляется в GitLab без отдельного разрешения.

## Следующий этап

GigaChatProvider реализует `AnalysisProvider` отдельным адаптером с OAuth, TLS, timeout, token TTL, typed output и mock HTTP tests. PostgreSQL-адаптер затем заменит demo repository и добавит миграции, server-side auth и tenant/owner isolation отдельным этапом.
