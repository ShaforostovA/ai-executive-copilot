# Phase 4 — React Dashboard и защищенный AI workflow

## React / TypeScript / Vite / PWA

Frontend реализован в `frontend/` и работает с FastAPI через same-origin `/api` в development/production topology. Vite dev proxy направляет запросы на backend; GigaChat credentials и другие API-секреты в браузере отсутствуют.

Реализованы:

- organization/email/password login через серверную HttpOnly cookie;
- protected layout, session check, logout и переход на login при `401`;
- Dashboard «Что требует внимания» с score, summary, reason, action item, timestamp и source link;
- integration statuses и DEMO/LIVE badges;
- source detail с исходным текстом и внешней ссылкой при наличии;
- loading, empty, error и retry states;
- responsive desktop/mobile layout и keyboard focus states;
- production PWA manifest и service worker;
- typed API errors с request ID;
- Vitest/Testing Library unit tests и Playwright desktop/mobile E2E.

## Защищенный AI workflow

`POST /api/v1/analysis/run` доступен только с действительной серверной сессией и при `COPILOT_USE_DEMO_REPOSITORY=false`.

Сценарий:

1. Клиент передает `SyntheticAnalysisRequest` без tenant/owner/data origin.
2. Backend создает `SourceDetail` с `organization_id` и `owner_id` из session principal и `data_origin=DEMO` для synthetic input.
3. `PostgresDashboardRepository.record_source_message` идемпотентно сохраняет источник.
4. Существующий анализ возвращается без повторного вызова модели.
5. `AnalysisProvider` анализирует сохраненный источник.
6. Workflow отклоняет non-LIVE provider result, принудительно восстанавливает tenant/owner/source binding и валидирует typed result.
7. `AnalysisResult` сохраняется с unique `source_message_id`; при concurrency conflict возвращается уже сохраненный анализ.
8. Dashboard читает LIVE результат из PostgreSQL.

Rate limit возвращает `429`; provider/validation failures возвращают безопасный `503`. Ошибка модели не создает DEMO analysis и не выдает ее за успех. Автоматические тесты используют только mock `AnalysisProvider`; live GigaChat не вызывается.

## Проверки

```bash
# Backend unit и все PostgreSQL integration tests
pytest -q backend/tests

# Frontend
npm ci --prefix frontend
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm test --prefix frontend
npm run build --prefix frontend

# После запуска PostgreSQL/API и synthetic seed
npx --prefix frontend playwright install chromium
npm run test:e2e --prefix frontend
```

Playwright проверяет login → dashboard → source → logout и invalid credentials в desktop Chromium и mobile viewport. `E2E_DEMO_PASSWORD` должен соответствовать только локальному synthetic seed.

GitLab CI содержит backend lint/unit, PostgreSQL 17 integration job, frontend lint/typecheck/unit/build и изолированный `frontend:e2e` job с PostgreSQL, migrations, synthetic seed и Chromium. Playwright также выполняется локально против реального Docker backend и не заменяется моковым production auth.

## Границы

- Автоматический запуск live GigaChat из UI не добавлен; workflow вызывается отдельным защищенным API и требует явной операции.
- Production static hosting/reverse proxy и HTTPS настраиваются при VPS rollout.
- Public signup, password reset и административное управление пользователями остаются отдельными задачами.
- Реальные платные запросы и production deploy не выполнялись.
