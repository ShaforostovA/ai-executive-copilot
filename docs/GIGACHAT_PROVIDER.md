# GigaChatProvider

## Статус и границы

`GigaChatProvider` реализует `AnalysisProvider` через асинхронный `httpx.AsyncClient`. Код использует реальный HTTP-контракт GigaChat, но по умолчанию не вызывается из DEMO dashboard. Live-запросы не выполнялись при разработке; автоматические тесты используют только `httpx.MockTransport` и фиктивные credentials.

Provider не подменяет ошибки модели DEMO-результатом. `data_origin=LIVE` устанавливается только после успешного HTTP-ответа и строгой Pydantic-валидации structured output.

## Официальные источники

- [Авторизация GigaChat API](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api): OAuth, `RqUID`, scopes и `expires_at`.
- [Генерация ответа](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat).
- [Структурированный output](https://developers.sber.ru/docs/ru/gigachat/guides/structured-output): `response_format.type=json_schema` и `strict=true`.
- [Выбор модели](https://developers.sber.ru/docs/ru/gigachat/guides/selecting-a-model).

Используются endpoints:

- OAuth: `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`;
- completion: `https://api.giga.chat/v1/chat/completions`.

## Конфигурация

| Переменная | Значение по умолчанию | Назначение |
|---|---|---|
| `COPILOT_GIGACHAT_CREDENTIALS` | не задано | Ключ авторизации для Basic OAuth; обязателен для provider |
| `COPILOT_GIGACHAT_SCOPE` | `GIGACHAT_API_PERS` | `PERS`, `B2B` или `CORP`; выбор зависит от разрешенного договора/тарифа |
| `COPILOT_GIGACHAT_MODEL` | `GigaChat-2` | Идентификатор модели |
| `COPILOT_GIGACHAT_OAUTH_URL` | официальный OAuth URL | HTTPS endpoint получения токена |
| `COPILOT_GIGACHAT_CHAT_URL` | официальный completion URL | HTTPS endpoint генерации |
| `COPILOT_GIGACHAT_TEMPERATURE` | `0.1` | Температура генерации |
| `COPILOT_GIGACHAT_TOP_P` | `1.0` | Top-p sampling |
| `COPILOT_GIGACHAT_MAX_TOKENS` | `1024` | Максимум токенов ответа |
| `COPILOT_GIGACHAT_TIMEOUT_SECONDS` | `20` | Timeout каждого HTTP-запроса |
| `COPILOT_GIGACHAT_TOKEN_REFRESH_SKEW_SECONDS` | `30` | Запас обновления токена до истечения |

Credentials задаются только в локальном `.env` или менеджере секретов. Они представлены `SecretStr`; provider не логирует credentials, access token, Authorization headers, тела запросов или содержимое сообщений. TLS verification включена, а URL схем ограничены HTTPS.

## Поведение

1. OAuth вызывается с новым UUID4 `RqUID` при каждом получении токена.
2. Access token кэшируется по `expires_at` и повторно используется до refresh window.
3. При completion `401` токен принудительно обновляется и completion повторяется один раз.
4. `429`, `5xx`, timeout и сетевые ошибки преобразуются в отдельные typed exceptions.
5. HTTP error body не копируется в исключение, чтобы не раскрывать служебные или конфиденциальные данные.
6. Structured output запрашивается через JSON Schema и повторно валидируется Pydantic. Невалидный JSON, пустой `choices`, отсутствующие поля и score вне `0..100` вызывают `GigaChatResponseError`.
7. Async-интерфейс не блокирует event loop и может быть вызван из последующего Celery/worker workflow. Очередь, retry policy и idempotency — отдельный этап; provider сам не выполняет фоновые повторы платных запросов.

## Synthetic вход и результат

Входной `SourceDetail` может иметь `data_origin=DEMO`, поскольку сообщение синтетическое. После успешного анализа моделью результат независимо маркируется `LIVE`.

Пример входа:

```json
{
  "source_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "external_id": "synthetic-smoke-001",
  "source_type": "synthetic",
  "title": "Synthetic smoke: budget approval",
  "content": "Synthetic test message only. Review the demo budget proposal and prepare a recommendation by Friday.",
  "source_timestamp": "2026-11-25T12:00:00Z",
  "data_origin": "DEMO"
}
```

Ожидаемая структура результата после успешного live-вызова:

```json
{
  "item_id": "<generated-uuid>",
  "tenant_id": "<source-tenant-uuid>",
  "owner_id": "<source-owner-uuid>",
  "source_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "score": 82,
  "summary": "Требуется рекомендация по бюджетному предложению.",
  "importance_reason": "В сообщении указан срок подготовки решения.",
  "next_step": "Изучить предложение и подготовить рекомендацию до пятницы.",
  "source_timestamp": "2026-11-25T12:00:00Z",
  "data_origin": "LIVE"
}
```

Значения анализа в примере иллюстрируют схему и не являются полученным live-ответом.

## Ручной smoke — только после разрешения

Скрипт `backend/scripts/gigachat_smoke.py` использует synthetic сообщение и настройки окружения. Он выводит только типизированный результат либо безопасное typed error message, но не credentials/token.

1. Установить backend: `pip install -e './backend[dev]'`.
2. Самостоятельно задать действительные `COPILOT_GIGACHAT_CREDENTIALS`, подходящие scope/model в локальном `.env` с ограниченными правами.
3. Подтвердить разрешение на live-запрос и условия провайдера.
4. Запустить `COPILOT_GIGACHAT_ENABLED=true python backend/scripts/gigachat_smoke.py --confirm-live`. Флаг подтверждает разрешение на один synthetic paid request.

Не запускайте скрипт в CI и не добавляйте его output с реальными данными в Git. На текущем этапе live smoke **не выполнялся**.
