# Мониторинг цен Winestyle в Excel

Контейнеризованный агент обходит список категорий одного сайта (Winestyle), собирает по карточкам товаров:
- текущую цену (`max(обычная, скидочная)`),
- рейтинг,
- наличие,

и обновляет существующий Excel-файл по совпадению ссылки товара.

## Что делает сервис
1. Читает конфиг сайта из `config/sites/*.yml`.
2. Обходит `category_urls` (Playwright/HTTP + пагинация).
3. Извлекает `product_url/current_price/rating/in_stock`.
4. Открывает Excel и ищет строку по URL товара.
5. Если товар найден — обновляет поля, если нет — пропускает.

## Структура
- `app/cli.py` — `run` и `watch`.
- `app/crawler/*` — обход категорий и парсинг карточек.
- `app/excel/updater.py` — обновление Excel по ссылкам.
- `scripts/cooldown_watchdog.py` — watchdog при cooldown-сигналах.

## Переменные окружения
Пример: `.env.example`.

Ключевые:
- `EXCEL_FILE_PATH` — путь к Excel (в Docker: `/app/products.xlsx`).
- `EXCEL_SHEET_NAME` — лист (пусто = активный).
- `EXCEL_URL_COLUMN_CANDIDATES` — варианты названия колонки ссылки.
- `EXCEL_PRICE_COLUMN_NAME`, `EXCEL_RATING_COLUMN_NAME`, `EXCEL_IN_STOCK_COLUMN_NAME`.
- `NETWORK_*`, `BEHAVIOR_*`, `FAIL_COOLDOWN_*`.
- `SITE_CONFIG_DIR`.

## Конфиг сайта
Минимум:
```yaml
site:
  name: "winestyle"
  domain: "winestyle.ru"
  base_url: "https://winestyle.ru"
  engine: "browser"

selectors:
  product_card_selector: "div.ws-products div.m-catalog-item--list"
  product_link_selector: "a.m-catalog-item__image"
  price_without_discount_selector: "div.m-catalog-item__price-old"
  price_with_discount_selector: "div.m-catalog-item__price-current"
  rating_selector: "div.m-catalog-item__rating-value"
  out_of_stock_selector: ".out-of-stock"

pagination:
  mode: "numbered_pages"
  param_name: "page"
  max_pages: 1000

category_urls:
  - "https://winestyle.ru/wine/all/"
```

## Запуск через Docker Compose
```bash
docker compose up -d --build parser
```

Для авто-перезапуска по cooldown:
```bash
docker compose up -d --build watchdog
```

Логи:
```bash
docker compose logs -f parser
tail -f logs/parser.log
```

## Локальный запуск
```bash
source .venv/bin/activate
set -a && source .env && set +a
python -m app.main run
```

Постоянный режим:
```bash
python -m app.main watch --success-delay 300 --error-delay 120
```

## Тесты
```bash
.venv/bin/python -m pytest -q
```

## Деплой на удалённый сервер
1. Клонировать репозиторий:
```bash
git clone git@github.com:kodjooo/content-publisher.git
cd content-publisher
```
2. Подготовить файлы:
- `.env`
- `config/sites/*.yml`
- `products.xlsx`
- директорию `logs/`
3. Запустить:
```bash
docker compose up -d --build watchdog
```
4. Проверить:
```bash
docker compose ps
docker compose logs -f parser
```

## Важно
- `.env` не коммитится в GitHub.
- Если колонка URL в Excel не найдена, агент завершится ошибкой конфигурации.
- Если целевые колонки отсутствуют, агент создаст их автоматически в строке заголовков.
