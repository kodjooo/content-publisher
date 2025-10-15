# Модуль публикации контента

Сервис следит за рабочими листами в Google Sheets, собирает подготовленные редакторами материалы и публикует их в Telegra.ph, VK и Telegram. Скрипт разворачивается как долгоживущий процесс (часто через Docker Compose), который каждую минуту сверяет текущее московское время с заданным расписанием и запускает нужные флоу.

## Что делает скрипт
- Читает вкладки RSS, VK и Setka из Google Sheets и берёт только строки со статусом `Revised`.
- Для RSS-материалов создаёт страницу в Telegra.ph, собирает короткий пост с ссылкой, публикует запись с изображением во VK и Telegram и сохраняет три полученные ссылки обратно в таблицу.
- Для точечных задач публикует один пост во VK и один пост в Telegram (Setka) за запуск, фиксирует URL-адреса и переводит строки в статус `Published`.
- Удаляет из коротких текстов вручную добавленный хвост “Читать подробнее >”, сокращает ссылку через VK API и добавляет обязательный хэштег `#Обзор_Новостей`.
- Пытается повторить сетевые операции до трёх раз, логирует результат в JSON и при ошибке записывает сообщение в `Notes` (RSS) или `Publish Note` (VK/Setka).
- Подчиняется расписанию: RSS — в 08:00 и 20:00 (мск) ежедневно; VK и Setka — в 18:00 (мск) только в дни, перечисленные в `VK_PUBLISH_DAYS` и `SETKA_PUBLISH_DAYS`.

## Структура
- `publisher/config.py` — загрузка конфигурации из `.env`.
- `publisher/gs/sheets.py` — клиент Google Sheets.
- `publisher/telegraph/client.py`, `publisher/vk/client.py`, `publisher/tg/client.py` — клиенты внешних API.
- `publisher/services/publisher.py` — бизнес-логика потоков RSS/VK/Setka.
- `publisher/run.py` — точка входа сервиса.
- `tests/` — модульные тесты.

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
