# Архитектура мониторинга цен в Excel

## 1. Общее описание
Сервис работает как контейнерное CLI-приложение и в цикле обходит список категорий одного сайта (Winestyle), извлекая витринные параметры товаров:
- текущая цена;
- рейтинг;
- наличие.

После каждого цикла данные применяются к локальному Excel-файлу по совпадению URL товара.

## 2. Основные компоненты
- `app.cli` — команды `run` (один цикл) и `watch` (постоянный цикл с паузой и автоповтором после ошибок).
- `app.workflow.runner.AgentRunner` — оркестрация: загрузка конфигов, запуск краулера, обновление Excel.
- `app.config` — модели и загрузка конфигурации из `.env` или YAML/JSON.
- `app.crawler.engines` — HTTP/Playwright движки, прокси-пул, retries, anti-block, cooldown-хуки.
- `app.crawler.site_crawler` — обход категорий и пагинации, извлечение `product_url/current_price/rating/in_stock` из карточек.
- `app.excel.updater` — обновление существующего Excel по ссылке (`product_url`), добавление колонок при отсутствии.
- `scripts/cooldown_watchdog.py` — внешний watchdog для перезапуска docker-compose при cooldown-сигналах.

## 3. Поток данных
1. CLI поднимает `AgentRunner`.
2. `AgentRunner` загружает `GlobalConfig` и `SiteConfig`.
3. `CrawlService` запускает `SiteCrawler` для сайта.
4. `SiteCrawler` обходит все `category_urls`, собирает `ProductSnapshot`.
5. `ExcelUpdater` открывает workbook, ищет строку по URL и обновляет поля.
6. Workbook сохраняется в `EXCEL_FILE_PATH`.

## 4. Модель данных
`ProductSnapshot`:
- `product_url`
- `current_price`
- `rating`
- `in_stock`
- служебные поля: `source_site`, `category_url`, `page_num`

## 5. Извлечение значений
- Цена:
  - читаются `price_without_discount_selector` и `price_with_discount_selector`;
  - итоговая цена = `max(обычная, скидочная)`;
  - если есть только одна цена — берётся она.
- Рейтинг:
  - извлекается по `rating_selector` и нормализуется до `float`.
- Наличие:
  - приоритет `out_of_stock_selector` (если совпал — `False`),
  - затем `in_stock_selector` (если совпал — `True`),
  - fallback: текстовые маркеры «нет в наличии» и аналоги.

## 6. Обновление Excel
- Путь и правила берутся из блока `excel`:
  - `workbook_path`, `sheet_name`, `header_row`;
  - `url_column_candidates`;
  - названия колонок `price/rating/in_stock`.
- Сопоставление по нормализованному URL (с применением `dedupe.strip_params_blacklist`).
- Если ссылка не найдена — запись пропускается.
- Если целевой колонки нет — она создаётся в заголовке.

## 7. Конфигурация
### .env (ключевое)
- `EXCEL_FILE_PATH`, `EXCEL_SHEET_NAME`, `EXCEL_*_COLUMN_NAME`
- `NETWORK_*`, `BEHAVIOR_*`
- `FAIL_COOLDOWN_*`
- `SITE_CONFIG_DIR`

### Site config
- `category_urls` — список категорий одного домена
- `selectors.product_card_selector`
- `selectors.product_link_selector`
- `selectors.price_without_discount_selector`
- `selectors.price_with_discount_selector`
- `selectors.rating_selector`
- `selectors.in_stock_selector` / `selectors.out_of_stock_selector`
- `pagination` + `limits`

## 8. Контейнеризация
`docker-compose.yml`:
- сервис `parser` — запуск `python -m app.main run`
- сервис `watchdog` — следит за логом и при cooldown перезапускает стек
- volume для Excel: `./products.xlsx:/app/products.xlsx`
- volume для логов: `./logs:/var/log/parser`

## 9. Что удалено из бизнес-потока
- Google Sheets слой (`app/sheets`), OAuth и запись `_runs/_state`.
- Локальный `state/resume` слой (`app/state`).
- Загрузка контента карточек и сохранение изображений (`content_fetcher`, `image_saver`).

HTTP-движок и watchdog/cooldown намеренно сохранены как технически полезные блоки.
