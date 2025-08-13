
# tg-mini (Telethon + FastAPI)
Лёгкий сервис, который отдаёт посты публичного канала Telegram с метриками (`views`, `forwards`) за N дней.
Предназначен, чтобы дергать его из n8n.

## Быстрый деплой на Render
1. Создай пустой репозиторий на GitHub и залей файлы из этого архива (`app.py`, `requirements.txt`).
2. На https://render.com → New → **Web Service** → подключи репозиторий.
3. **Runtime:** Python; **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. В разделе **Environment → Secrets** добавь:
   - `TG_API_ID` — с my.telegram.org
   - `TG_API_HASH` — с my.telegram.org
   - `TG_STRING_SESSION` — сгенерируй как ниже
   - `API_KEY` — любая случайная строка (эту же строку укажешь в заголовке `x-api-key` в n8n)
5. Нажми Deploy, дождись URL вида `https://<name>.onrender.com`.

### Как получить TG_STRING_SESSION один раз локально
1) Установи зависимости: `pip install telethon`
2) Запусти `python gen_session.py` и следуй инструкциям (код придет в Telegram).
3) Полученную длинную строку вставь в Secret `TG_STRING_SESSION` на Render.

## Проверка
```bash
curl -H "x-api-key: <твоя-строка>"       "https://<name>.onrender.com/posts?channel=@durov&days=7"
```

## Использование в n8n (HTTP Request)
- Method: GET
- URL: `https://<name>.onrender.com/posts`
- Query: `channel={{$json.channel}}`, `days=7`
- Headers: `x-api-key: <твоя-строка>`
- Concurrency: 5–10

## Эндпоинты
- `GET /` — статус
- `GET /healthz` — health
- `GET /posts?channel=@username&days=7` — список постов (JSON)

## Примечания
- Работают **только публичные каналы**.
- Сессия хранится как строка в переменной окружения, поэтому диск не нужен.
- Для больших списков каналов добавь ретраи и лимиты в n8n.
