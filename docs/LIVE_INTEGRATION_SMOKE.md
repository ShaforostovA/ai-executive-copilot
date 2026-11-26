# Live integration smoke — только после отдельного разрешения

Оба сценария подготовлены, но **не выполнялись**. Использовать только технический тестовый аккаунт и synthetic сообщение. Не читать личные письма и не публиковать credentials, access tokens, содержимое ответов или писем в Git/логах/чате.

## GigaChat — одно synthetic сообщение

Предусловия:

1. Владелец явно разрешил один платный completion и подтвердил условия провайдера/тарифа.
2. Credentials заданы только в защищенном `.env`/secret manager, не в командной строке или Git.
3. `COPILOT_GIGACHAT_ENABLED=true`, подходящие scope/model и TLS verification включены.
4. Установить `COPILOT_GIGACHAT_DAILY_REQUEST_LIMIT=1` на время smoke.

```bash
python backend/scripts/gigachat_smoke.py --confirm-live
```

`--confirm-live` обязателен. Выполняется один synthetic analysis; LIVE результат проверяется Pydantic. Ошибки 401/429/5xx/timeout не заменяются DEMO. Не сохранять output, если он может содержать конфиденциальные данные.

## Yandex IMAP — read-only

Предусловия:

1. Отдельный тестовый mailbox с разрешением владельца; выдан отдельный app password, не основной пароль.
2. Разрешена только ожидаемая папка (`YANDEX_ALLOWED_FOLDERS`, по умолчанию `INBOX`).
3. `YANDEX_EMAIL`, `YANDEX_APP_PASSWORD` и опциональный `YANDEX_FOLDER` заданы в защищенной среде.
4. Разрешено не более 1–5 сообщений, без открытия реальных персональных писем.

```bash
python backend/scripts/yandex_imap_smoke.py --confirm-read-only --limit 1
```

Adapter использует `IMAP4_SSL` с системным TLS context и `SELECT ... readonly=True`. Печатаются только UIDVALIDITY и количество сообщений; subject, content, credentials не выводятся. Для production connect/sync используется Fernet-encrypted credential storage и owner/tenant isolation. После проверки доступ следует отозвать через `DELETE /api/v1/integrations/yandex` и удалить app password в Yandex ID.

## Запрещено без нового подтверждения

- Повторные paid completions или увеличение лимита.
- Production deploy, миграции и restore.
- Подключение личного/рабочего mailbox без отдельного согласия владельца.
- Логирование credentials, cookies, access tokens или содержимого писем.
