# Модуль публикации контента

Сервис обрабатывает очереди публикаций из Google Sheets и размещает контент в Telegra.ph, VK и Telegram. Запуск осуществляется командой `python -m publisher.run`.

## Структура
- `publisher/config.py` — загрузка конфигурации из `.env`.
- `publisher/gs/sheets.py` — клиент Google Sheets.
- `publisher/telegraph/client.py`, `publisher/vk/client.py`, `publisher/tg/client.py` — клиенты внешних API.
- `publisher/services/publisher.py` — бизнес-логика потоков RSS/VK/Setka.
- `publisher/run.py` — точка входа сервиса.
- `tests/` — модульные тесты.

## Подготовка окружения
1. Скопируйте `.env.example` в `.env` и заполните токены (`VK_USER_ACCESS_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAPH_ACCESS_TOKEN` и т.д.).
2. Разместите сервисный аккаунт Google по пути, указанному в переменной `GOOGLE_SERVICE_ACCOUNT_JSON`.
3. Установите зависимости:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Запуск
- Локально: `python -m publisher.run`
- В Docker:
  ```bash
  docker compose up --build
  ```

## Тесты
```bash
pytest
```
