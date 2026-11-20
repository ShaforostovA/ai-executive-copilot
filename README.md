# AI Executive Co-pilot

B2B SaaS-ассистент руководителя. Основной репозиторий — **GitLab**, GitHub — автоматически обновляемое **read-only зеркало**.

> Состояние: **bootstrap**. Это каркас репозитория и минимальный проверяемый API, а не готовый MVP.

## Основной стек и границы

- Backend: Python 3.13, FastAPI (модульный монолит).
- Telegram-бот: aiogram 3.x (внедряется по отдельной задаче).
- Jobs: Celery + Redis; состояние и аудит: PostgreSQL 17.
- Векторный поиск: Qdrant 1.x; интеллект: GigaChat API.
- Frontend: React + TypeScript + Vite / PWA (пока только каталог-заготовка).
- Dev-окружение: Docker Compose. CI: GitLab CI.

## Первый локальный запуск

1. Скопируйте `.env.example` в `.env` и замените пароль PostgreSQL (только локальные значения).
2. Убедитесь, что установлены Docker Desktop с Compose V2 и Git.
3. Запустите `docker compose -f infra/compose.dev.yml --env-file .env up --build -d`.
4. Откройте http://127.0.0.1:8000/healthz — ответ должен быть `{"status":"ok"}`.
5. Остановите контейнеры: `docker compose -f infra/compose.dev.yml --env-file .env down`.

Без Docker: `cd backend && python -m venv .venv`; активируйте окружение, выполните `pip install -e ".[dev]"`, `uvicorn copilot_api.main:app --reload`, `pytest -q`.

## Как работать в команде

- Только GitLab: все `push`, Issues, Merge Requests и CI — там.
- `main` — защищенная и выпускаемая ветка; без прямых push.
- Рабочие ветки: `feat/123-mail-adapter`, `fix/124-calendar-etag`.
- Merge Request: описание задачи, результаты проверки, подтверждение ревьюера.
- Не записывайте в репозиторий ключи API, пользовательские данные, Telegram sessions, `.env`, логи и дампы.

## Структура

```text
backend/                    Python API и будущие доменные модули
frontend/                   React/TS/PWA — заполняется в задаче по веб-клиенту
bot/                        интеграционные обработчики Telegram — заполняются позже
infra/                      локальная инфраструктура Docker Compose
docs/                       правила работы, решения, архитектура, инструкции
.gitlab-ci.yml              первый CI: синтаксис, lint и backend-тесты
.env.example                образец только локальных настроек
```

## Документация

- [Создание GitLab и GitHub](docs/REPOSITORY_SETUP.md)
- [Порядок разработки](docs/CONTRIBUTING.md)
- [Инструкция по зеркалированию](docs/MIRRORING.md)
- [Решения и предстоящие работы](docs/DECISIONS.md)

**Важно:** этот архив не создает проекты на внешних сервисах и не содержит учетных данных.
