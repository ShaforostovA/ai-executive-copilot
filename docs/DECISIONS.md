# Решения уровня bootstrap

- ADR-B01: GitLab.com — единственный upstream и площадка управления разработкой.
- ADR-B02: GitHub — downstream mirror, без двусторонней синхронизации.
- ADR-B03: Монорепозиторий для 4 участников: Python backend + бот + PWA frontend + docs + infra.
- ADR-B04: Защищенная main + Merge Request + ранний CI, без постоянной ветки develop.
- ADR-B05: CI собирает и проверяет только готовый backend scaffold. Frontend CI, deploy и secrets вводятся по мере реализации соответствующих модулей.
- ADR-B06: Локальные Docker Compose и .env не являются конфигурацией продакшена; пока нет auth, tenant isolation, HTTPS ingress, backups.

## Следующие задачи

1. Разработать модели PostgreSQL + Alembic и миграции.
2. Интегрировать aiogram 3 webhook и дедупликацию Telegram update.
3. Добавить React/Vite PWA и lock-file + frontend CI.
4. Подключить GigaChat API через провайдер и тестовые секреты CI.
5. Ввести self-hosted окружение pilot с HTTPS, резервным копированием, secrets management и деплоем.
6. Зафиксировать architecture v1.1 в `docs/architecture/` после утверждения командой.
