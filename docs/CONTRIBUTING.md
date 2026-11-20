# Как вносить изменения

1. В GitLab создайте Issue с четкими критериями приемки.
2. Ответвитесь от `main`: `git switch -c feat/123-my-task`.
3. Делайте небольшие коммиты; не включайте персональные данные, токены, `.env`.
4. `git push -u origin feat/123-my-task`.
5. Создайте Merge Request -> `main`, привяжите Issue и назначьте ревьюера.
6. Дождитесь зеленого pipeline. Проведите ревью; после согласования объедините ветку.
7. После merge GitLab обновит GitHub push mirror.

## Правила MR

- Не объединять при красном CI.
- Минимум один содержательный review командой — договоренность команды (встроенное требование approvals зависит от тарифа).
- Критерии готовности описать в MR.
- Для API-изменений добавить тесты и обновить документацию.

## Политика веток

- `main`: protected; Allowed to push = No one; Allowed to merge = Maintainers.
- `feat/*`, `fix/*`, `docs/*`: разработка; удалять после merge.
- Срочное исправление: `fix/<issue>-...` из `main`, обычный MR.
- GitHub — read-only копия. Не добавлять туда PR или коммиты.

## Именование коммитов

- `feat: add mail connector skeleton`
- `fix: avoid duplicate webhook update`
- `docs: describe Telegram restrictions`
- `chore: initialize CI`
