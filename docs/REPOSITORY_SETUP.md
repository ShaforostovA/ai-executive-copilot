# Создание репозиториев с нуля: Windows + GitLab + GitHub

**Порядок важен:** сначала создайте два пустых репозитория, затем запушьте локальный каркас в GitLab, после этого включите mirror.

## 1. GitLab.com: группа и проект

- Создайте приватную группу `ai-executive-copilot-team` (название можно выбрать другое).
- В группе: `New project/repository -> Create blank project`.
- Project name: `AI Executive Co-pilot`; slug: `ai-executive-copilot`.
- Visibility: **Private**; **не** отмечайте `Initialize repository with a README`.
- Запишите адрес: `https://gitlab.com/<GROUP>/ai-executive-copilot.git`.

Если проект создан с README: **не** применяйте команды `git init ...` ниже для отдельной истории. Вместо этого `git clone` GitLab-проекта и добавьте в него файлы каркаса.

## 2. GitHub.com: пустой проект

- `New repository` -> `ai-executive-copilot`, **Private**.
- НЕ отмечайте `Add a README file`, `.gitignore`, `Choose a license`.
- Не делайте в GitHub прямые коммиты.

## 3. Первый push с ПК (PowerShell / VS Code)

Распакуйте архив, откройте корень `ai-executive-copilot` в VS Code.

```powershell
# Выполнить один раз, если Git еще не настроен
git config --global user.name "Ваше имя"
git config --global user.email "your-verified-email@example.com"

# Из корня папки ai-executive-copilot
git init -b main
git add .
git commit -m "chore: initialize repository structure"
git remote add origin https://gitlab.com/<GROUP>/ai-executive-copilot.git
git push -u origin main
```

Альтернатива: SSH URL `git@gitlab.com:<GROUP>/ai-executive-copilot.git`, если ранее настроили SSH-ключ GitLab.
Для HTTPS используйте Git Credential Manager и разрешенную GitLab аутентификацию; не вводите пароль основного аккаунта в командную строку.

## 4. GitLab: участники и защита main

- `Manage -> Members`: добавьте трех остальных участников. Рекомендация: один Owner группы, один Maintainer проекта, двое Developer (роли уточняются внутри команды).
- `Settings -> Repository -> Branch rules -> main`: Allowed to push/merge -> запретить прямой push, разрешить слияние Maintainers.
- `Settings -> Merge requests`: включите запрет merge при failed CI, удаление source branch после merge.
- `Build -> Pipelines`: проверьте, что оба job завершились успешно. Runner GitLab.com обычно доступен по умолчанию.
- В CI переменные пока не добавляйте реальные секреты GigaChat/Yandex/Telegram: они понадобятся после определения среды и границ доступа.

## 5. Подключите GitHub зеркало

См. [MIRRORING.md](MIRRORING.md). Используйте GitHub fine-grained PAT только с Contents: Read/Write на один репозиторий.

## 6. Проверка

- На GitLab есть `main`, README и `.gitlab-ci.yml`.
- CI выполняет backend lint и backend тест.
- Создали ветку `docs/mirror-check`, сделали MR, pipeline прошел, ветка слита в `main`.
- SHA HEAD `main` совпадает в GitLab и GitHub.
- GitHub private; отсутствуют прямые коммиты, не вводили токены в MR, CI logs и Git.

## Проверенные официальные источники

- https://docs.gitlab.com/user/project/repository/mirror/push/
- https://docs.gitlab.com/ci/
- https://docs.gitlab.com/user/project/repository/branches/protected/
- https://docs.gitlab.com/user/free_user_limit/
- https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository
