# GitLab -> GitHub push mirroring

Официальное руководство: https://docs.gitlab.com/user/project/repository/mirror/push/

1. В GitHub создайте ПУСТОЙ приватный репозиторий `ai-executive-copilot` (без README, LICENSE и .gitignore).
2. В GitHub откройте `Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens`.
3. Выдайте доступ **только к этому репозиторию**, Repository permissions: `Contents: Read and write`. Если в репозитории есть `.github/workflows`, добавьте `Workflows: Read and write`.
4. Запишите токен в менеджер секретов. Не включайте его в URL, файлы Git, Issue или скриншоты.
5. GitLab: `Settings -> Repository -> Mirroring repositories -> Add new`.
6. URL: `https://github.com/<GITHUB_OWNER>/ai-executive-copilot.git`.
7. Direction: **Push**. Authentication: **Username and Password**.
8. Username: имя владельца GitHub PAT; Password: PAT.
9. `Only mirror protected branches`: **off** (чтобы копировались все ветки); `Keep divergent refs`: обычно **off** для зеркала, которое никто не меняет вручную.
10. `Mirror repository`, затем `Update now`. Смотрите `Last successful update`.
11. Сравните SHA `main` в GitLab и GitHub и наличие всех ожидаемых веток.

Важно: GitHub не синхронизирует GitLab Issues, Merge Requests, CI/CD variables, секреты и базу. Это зеркало GIT-репозитория, не полноценный бэкап GitLab.

Если настройка mirroring недоступна в UI, проверьте права Maintainer/Owner и ограничения тарифа; в качестве запасного решения — отдельный job GitLab CI для `git push --mirror` с секретом, только после отдельного security review.
