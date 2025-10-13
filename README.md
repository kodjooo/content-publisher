# Модуль публикации контента

Сервис обрабатывает очереди публикаций из Google Sheets и размещает контент в Telegra.ph, VK и Telegram. Базовый способ запуска — через Docker Compose (`docker compose up --build`).

## Структура
- `publisher/config.py` — загрузка конфигурации из `.env`.
- `publisher/gs/sheets.py` — клиент Google Sheets.
- `publisher/telegraph/client.py`, `publisher/vk/client.py`, `publisher/tg/client.py` — клиенты внешних API.
- `publisher/services/publisher.py` — бизнес-логика потоков RSS/VK/Setka.
- `publisher/run.py` — точка входа сервиса.
- `tests/` — модульные тесты.

> Обрабатываются только строки со статусом `Revised`; успешные публикации переводятся в `Published`, ошибки записываются в `Notes` (RSS) и `Publish Note` (VK/Setka). Заголовок для Telegraph берётся из столбца `GPT Post Title`; короткие тексты очищаются от заранее вставленного “Читать подробнее >”, после чего ссылки формируются: в VK — через `utils.getShortLink` (`Читать подробнее > vk.cc/...`), в Telegram — HTML-гиперссылкой. Расписание: RSS — в 08:00 и 20:00 (мск) ежедневно, VK и Setka — в 18:00 (мск) в дни, указанные в `VK_PUBLISH_DAYS`/`SETKA_PUBLISH_DAYS`; за один запуск публикуется не более одного поста на каждую вкладку VK/Setka.

## Подготовка окружения
1. Скопируйте `.env.example` в `.env` и заполните токены (`VK_USER_ACCESS_TOKEN`, `VK_GROUP_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAPH_ACCESS_TOKEN` и т.д.), а также задайте дни публикаций в `VK_PUBLISH_DAYS` и `SETKA_PUBLISH_DAYS`.
2. Разместите сервисный аккаунт Google по пути, указанному в переменной `GOOGLE_SERVICE_ACCOUNT_JSON`.
3. Соберите образ и установите зависимости внутри контейнера:
   ```bash
   docker compose build
   ```

## Запуск
```bash
# Запуск в фоне
docker compose up -d publisher

# Или запуск в фореграунде (Ctrl+C для остановки)
docker compose up publisher
```

## Развёртывание на удалённом сервере
- Установите Docker и Docker Compose (`curl -fsSL https://get.docker.com | sh`, затем `sudo usermod -aG docker <user>`).
- Склонируйте репозиторий: `git clone https://github.com/kodjooo/content-publisher.git && cd content-publisher`.
- Заполните `.env` (секреты передавайте безопасным каналом, файл в git не коммитится).
- При необходимости скопируйте файл сервисного аккаунта Google в `/app/sa.json` внутри проекта или настройте том.
- Соберите образ: `docker compose build`.
- Запустите сервис в фоне: `docker compose up -d publisher` (для фореграунда — `docker compose up publisher`).
- Для просмотра логов во время работы используйте `docker compose logs -f`.

### Автозапуск по расписанию
После запуска контейнер остаётся активным и каждые 60 секунд сверяет текущее московское время с расписанием: RSS публикуется в 08:00 и 20:00 ежедневно, VK и Setka — в 18:00 только в дни, перечисленные в `VK_PUBLISH_DAYS` и `SETKA_PUBLISH_DAYS`. Дополнительный cron не требуется.

## Тесты
```bash
docker compose run --rm publisher pytest
```
