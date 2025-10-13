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

### Автозапуск по расписанию
Сам сервис рассчитывает, что его запускает внешнее расписание (например, cron). Запускайте контейнер `docker compose run --rm publisher` в нужные моменты, а внутренняя логика уже проверит, попадает ли текущее время в окна публикации (RSS: 08:00/20:00 мск, VK/Setka: 18:00 мск по указанным дням).

Пример кронтаба для сервера в часовом поясе МСК:

```
# RSS в 08:00 и 20:00
0 8,20 * * * cd /path/to/content-publisher && docker compose run --rm publisher >> /var/log/content-publisher.log 2>&1
# VK/Setka в 18:00
0 18 * * * cd /path/to/content-publisher && docker compose run --rm publisher >> /var/log/content-publisher.log 2>&1
```

Если сервер работает в другом часовом поясе — настройте cron с учётом смещения или используйте `TZ='Europe/Moscow'` в записи.

## Тесты
```bash
docker compose run --rm publisher pytest
```
