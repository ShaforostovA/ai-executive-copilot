# Frontend — AI Executive Co-pilot

React + TypeScript + Vite + PWA. Интерфейс использует FastAPI и серверную HttpOnly cookie-сессию. API-ключи и GigaChat credentials в браузере отсутствуют.

## Команды

```bash
npm ci
npm run dev
npm run lint
npm run typecheck
npm test
npm run build
```

Vite proxy направляет `/api`, `/healthz` и `/readyz` на `http://127.0.0.1:8000`. Адрес можно изменить через `VITE_API_PROXY_TARGET`; для отдельного API origin production build использует `VITE_API_BASE_URL`.

## Playwright с реальным backend

1. Запустить PostgreSQL/API и synthetic seed согласно `docs/PHASE3_POSTGRES_AUTH.md`.
2. Установить Chromium: `npx playwright install chromium`.
3. Задать `E2E_DEMO_PASSWORD` в соответствии с локальным synthetic seed.
4. Выполнить `npm run test:e2e`.

Playwright запускает Vite и проверяет login → dashboard → source → logout и invalid credentials в desktop Chromium и mobile viewport. Тесты используют только synthetic учетную запись.

## Структура

- `src/lib/api.ts` — typed fetch client, `credentials: include`, structured errors.
- `src/auth/AuthContext.tsx` — server session lifecycle и session expiry.
- `src/pages/` — login, dashboard, source detail.
- `src/components/` — priority cards, action items, integrations, badges и UI states.
- `e2e/` — Playwright browser tests.

DEMO и LIVE данные визуально различаются. Не добавляйте реальные credentials, пользовательские данные или session tokens в исходники, screenshots и отчеты.
