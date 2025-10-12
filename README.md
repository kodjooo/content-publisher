# Модуль публикации контента

Сервис обрабатывает очереди публикаций из Google Sheets и размещает контент в Telegra.ph, VK и Telegram. Запуск осуществляется командой `python -m publisher.run`.

## Структура
- `publisher/config.py` — загрузка конфигурации из `.env`.
- `publisher/gs/sheets.py` — клиент Google Sheets.
- `publisher/telegraph/client.py`, `publisher/vk/client.py`, `publisher/tg/client.py` — клиенты внешних API.
- `publisher/services/publisher.py` — бизнес-логика потоков RSS/VK/Setka.
- `publisher/run.py` — точка входа сервиса.
- `tests/` — модульные тесты.

> Обрабатываются только строки со статусом `Revised`; успешные публикации переводятся в `Published`, ошибки записываются в `Notes` (RSS) и `Publish Note` (VK/Setka).

## Подготовка окружения
1. Скопируйте `.env.example` в `.env` и заполните токены (`VK_USER_ACCESS_TOKEN`, `VK_GROUP_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAPH_ACCESS_TOKEN` и т.д.).
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

## Развёртывание на удалённом сервере
- Установите Docker и Docker Compose (`curl -fsSL https://get.docker.com | sh`, затем `sudo usermod -aG docker <user>`).
- Склонируйте репозиторий: `git clone git@github.com:kodjooo/content-publisher.git && cd content-publisher`.
- Заполните `.env` (секреты передавайте безопасным каналом, файл в git не коммитится).
- При необходимости скопируйте файл сервисного аккаунта Google в `/app/sa.json` внутри проекта или настройте том.
- Запустите сервис: `docker compose up -d --build`.
- Логи доступны через `docker compose logs -f`; обновление — `git pull`, далее `docker compose up -d --build`.

## Тесты
```bash
pytest
```
