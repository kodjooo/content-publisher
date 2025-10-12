# Модуль публикации контента

Сервис обрабатывает очереди публикаций из Google Sheets и размещает контент в Telegra.ph, VK и Telegram. Базовый способ запуска — через Docker Compose (`docker compose up --build`).

## Структура
- `publisher/config.py` — загрузка конфигурации из `.env`.
- `publisher/gs/sheets.py` — клиент Google Sheets.
- `publisher/telegraph/client.py`, `publisher/vk/client.py`, `publisher/tg/client.py` — клиенты внешних API.
- `publisher/services/publisher.py` — бизнес-логика потоков RSS/VK/Setka.
- `publisher/run.py` — точка входа сервиса.
- `tests/` — модульные тесты.

> Обрабатываются только строки со статусом `Revised`; успешные публикации переводятся в `Published`, ошибки записываются в `Notes` (RSS) и `Publish Note` (VK/Setka). Ссылки на статьи добавляются в формате “Подробнее >”, заголовок для Telegraph берётся из столбца `GPT Post Title`.

## Подготовка окружения
1. Скопируйте `.env.example` в `.env` и заполните токены (`VK_USER_ACCESS_TOKEN`, `VK_GROUP_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAPH_ACCESS_TOKEN` и т.д.).
2. Разместите сервисный аккаунт Google по пути, указанному в переменной `GOOGLE_SERVICE_ACCOUNT_JSON`.
3. Соберите образ и установите зависимости внутри контейнера:
   ```bash
   docker compose build
   ```

## Запуск
```bash
docker compose run --rm publisher
```

## Развёртывание на удалённом сервере
- Установите Docker и Docker Compose (`curl -fsSL https://get.docker.com | sh`, затем `sudo usermod -aG docker <user>`).
- Склонируйте репозиторий: `git clone git@github.com:kodjooo/content-publisher.git && cd content-publisher`.
- Заполните `.env` (секреты передавайте безопасным каналом, файл в git не коммитится).
- При необходимости скопируйте файл сервисного аккаунта Google в `/app/sa.json` внутри проекта или настройте том.
- Соберите образ: `docker compose build`.
- Запустите однократное выполнение: `docker compose run --rm publisher`.
- Для просмотра логов во время выполнения используйте `docker compose logs -f`.

## Тесты
```bash
docker compose run --rm publisher pytest
```
