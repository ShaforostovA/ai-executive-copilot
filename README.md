# AI Executive Co-pilot

B2B SaaS-ассистент руководителя. Основной репозиторий — **GitLab**, GitHub — автоматически обновляемое **read-only зеркало**.

> Состояние: **локальный MVP vertical slice**. FastAPI, PostgreSQL, server auth, mock-tested GigaChatProvider и React Dashboard проверяются локально; production rollout еще не выполнен.

## Основной стек и границы

- Backend: Python 3.13, FastAPI (модульный монолит).
- Telegram-бот: aiogram 3.x (внедряется по отдельной задаче).
- Jobs: Celery + Redis; состояние и аудит: PostgreSQL 17.
- Векторный поиск: Qdrant 1.x; интеллект: GigaChat API.
- Frontend: React + TypeScript + Vite / PWA, server cookie-session auth.
- Dev-окружение: Docker Compose. CI: GitLab CI.

## Первый локальный запуск

1. Скопируйте `.env.example` в `.env` и замените пароль PostgreSQL (только локальные значения).
2. Убедитесь, что установлены Docker Desktop с Compose V2, Node.js 22+ и Git.
3. Запустите `docker compose -f infra/compose.dev.yml --env-file .env up --build -d`.
4. Откройте http://127.0.0.1:8000/healthz — ответ должен быть `{"status":"ok"}`.
5. Создайте synthetic development login по инструкции `docs/PHASE3_POSTGRES_AUTH.md`.
6. Запустите интерфейс: `cd frontend && npm ci && npm run dev`; откройте http://127.0.0.1:5173.
7. Остановите контейнеры: `docker compose -f infra/compose.dev.yml --env-file .env down`.

Без Docker backend: `cd backend && python -m venv .venv`; активируйте окружение, выполните `pip install -e ".[dev]"`, `uvicorn copilot_api.main:app --reload`, `pytest -q`.

## Как работать в команде

- Только GitLab: все `push`, Issues, Merge Requests и CI — там.
- `main` — защищенная и выпускаемая ветка; без прямых push.
- Рабочие ветки: `feat/123-mail-adapter`, `fix/124-calendar-etag`.
- Merge Request: описание задачи, результаты проверки, подтверждение ревьюера.
- Не записывайте в репозиторий ключи API, пользовательские данные, Telegram sessions, `.env`, логи и дампы.

## Структура

```text
backend/                    FastAPI, PostgreSQL, auth, GigaChat и AI workflow
frontend/                   React/TS/Vite/PWA Dashboard и Playwright E2E
bot/                        интеграционные обработчики Telegram — заполняются позже
infra/                      локальная инфраструктура Docker Compose
docs/                       правила работы, решения, архитектура, инструкции
.gitlab-ci.yml              backend/PostgreSQL/frontend lint, tests и build
.env.example                образец только локальных настроек
```

## Документация

- [Staging deployment и VPS diagnostics](docs/STAGING_DEPLOYMENT.md)
- [Release readiness и Ubuntu rollout](docs/RELEASE_READINESS.md)
- [Live integration smoke после разрешения](docs/LIVE_INTEGRATION_SMOKE.md)
- [Public MVP safeguards и Яндекс Почта](docs/PHASE5_PUBLIC_MVP.md)
- [Production deploy, backup и rollback](docs/PRODUCTION_RUNBOOK.md)
- [Текущий vertical slice: React и AI workflow](docs/PHASE4_REACT_AI_WORKFLOW.md)
- [PostgreSQL и серверная авторизация](docs/PHASE3_POSTGRES_AUTH.md)
- [GigaChatProvider](docs/GIGACHAT_PROVIDER.md)
- [Создание GitLab и GitHub](docs/REPOSITORY_SETUP.md)
- [Порядок разработки](docs/CONTRIBUTING.md)
- [Инструкция по зеркалированию](docs/MIRRORING.md)
- [Решения и предстоящие работы](docs/DECISIONS.md)

**Важно:** репозиторий не содержит учетных данных. Live GigaChat и production deploy выполняются только после отдельного разрешения.
