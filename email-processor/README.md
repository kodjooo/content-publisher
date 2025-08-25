# Email Payment Processor

Автоматизированная система для обработки платежных данных из электронной почты.

## Описание

Этот скрипт автоматически:
1. 📧 Подключается к почтовому серверу и получает новые письма
2. 🔍 Ищет в письмах ссылки для скачивания файлов
3. 🤖 Использует автоматизацию браузера для клика на кнопки и скачивания архивов
4. 📦 Распаковывает скачанные архивы (ZIP, RAR, 7Z)
5. 📊 Находит CSV файлы и обрабатывает их согласно заданным условиям
6. 💰 Извлекает информацию об оплатах из определенных полей
7. 🔗 Создает webhook с данными об оплатах и отправляет на сервер

## Архитектура

```
email-processor/
├── src/                     # Исходный код
│   ├── main.py             # Главный скрипт
│   ├── email_handler.py    # Работа с email
│   ├── browser_automation.py # Автоматизация браузера
│   ├── file_processor.py   # Обработка файлов
│   └── webhook_sender.py   # Отправка webhook
├── config/                 # Конфигурация
│   └── config.py          # Настройки приложения
├── downloads/              # Скачанные файлы
├── logs/                   # Логи приложения
├── requirements.txt        # Python зависимости
├── Dockerfile             # Docker образ
└── env.example            # Пример настроек
```

## Установка

### Использование с Docker (рекомендуется)

1. **Клонировайте репозиторий и перейдите в директорию:**
   ```bash
   cd email-processor
   ```

2. **Создайте файл `.env` на основе примера:**
   ```bash
   cp env.example .env
   ```

3. **Настройте переменные окружения в `.env`:**
   ```env
   # Email Configuration
   EMAIL_ADDRESS=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   
   # Webhook Configuration
   WEBHOOK_URL=https://your-server.com/webhook/payments
   WEBHOOK_TOKEN=your_webhook_token
   
   # CSV Processing (настройте под ваши данные)
   CSV_FILTER_COLUMN=status
   CSV_FILTER_VALUE=completed
   PAYMENT_AMOUNT_COLUMN=amount
   PAYMENT_DATE_COLUMN=date
   PAYMENT_ID_COLUMN=transaction_id
   CUSTOMER_ID_COLUMN=customer_id
   ```

4. **Запустите контейнер:**
   ```bash
   docker-compose up -d
   ```

### Локальная установка

1. **Установите Python 3.11+ и зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Установите Google Chrome и ChromeDriver:**
   - Chrome будет установлен автоматически через webdriver-manager

3. **Настройте переменные окружения и запустите:**
   ```bash
   python src/main.py --mode once
   ```

## Настройка

### Email Configuration

- `IMAP_SERVER`: IMAP сервер (по умолчанию: imap.gmail.com)
- `EMAIL_ADDRESS`: Ваш email адрес
- `EMAIL_PASSWORD`: Пароль приложения (для Gmail создайте App Password)
- `MAILBOX`: Папка для мониторинга (по умолчанию: INBOX)

### CSV Processing

Настройте поля CSV файла под ваш формат данных:
- `CSV_FILTER_COLUMN`: Колонка для фильтрации
- `CSV_FILTER_VALUE`: Значение для фильтрации
- `PAYMENT_AMOUNT_COLUMN`: Колонка с суммой платежа
- `PAYMENT_DATE_COLUMN`: Колонка с датой платежа
- `PAYMENT_ID_COLUMN`: Колонка с ID транзакции
- `CUSTOMER_ID_COLUMN`: Колонка с ID клиента

### Webhook Configuration

- `WEBHOOK_URL`: URL для отправки данных
- `WEBHOOK_TOKEN`: Токен авторизации
- `WEBHOOK_TIMEOUT`: Таймаут запроса в секундах

## Использование

### Режимы работы

1. **Одноразовый запуск:**
   ```bash
   python src/main.py --mode once
   ```

2. **Непрерывный мониторинг:**
   ```bash
   python src/main.py --mode continuous --interval 30
   ```

### Docker

```bash
# Запуск в фоне
docker-compose up -d

# Просмотр логов
docker-compose logs -f email-processor

# Остановка
docker-compose down
```

## Формат Webhook

Отправляемые данные имеют следующий формат:

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "event_type": "payments_processed",
  "data": {
    "payments_count": 5,
    "summary": {
      "total_amount": 1500.00,
      "currencies": ["USD"],
      "primary_currency": "USD",
      "count": 5,
      "unique_customers": 3
    },
    "payments": [
      {
        "transaction_id": "TXN123456",
        "customer_id": "CUST001",
        "amount": 299.99,
        "currency": "USD",
        "date": "2024-01-01T10:30:00",
        "status": "processed",
        "source_file": "payments_2024_01.csv",
        "metadata": {
          "processed_at": "2024-01-01T12:00:00",
          "processor_version": "1.0.0"
        }
      }
    ]
  }
}
```

## Безопасность

- 🔐 Используйте App Passwords для Gmail (не основной пароль)
- 🛡️ Храните токены в переменных окружения
- 🔒 Используйте HTTPS для webhook URL
- 📝 Регулярно проверяйте логи на наличие ошибок

## Мониторинг

### Логи

Логи сохраняются в папке `logs/` и включают:
- Подключение к email серверу
- Скачивание файлов
- Обработку CSV данных
- Отправку webhook

### Health Check

Docker контейнер включает health check для мониторинга состояния.

## Устранение неполадок

### Частые проблемы

1. **Ошибка подключения к email:**
   - Проверьте настройки IMAP
   - Включите "Менее безопасные приложения" или используйте App Password

2. **Браузер не запускается:**
   - Убедитесь что Chrome установлен
   - Проверьте права доступа к файлам

3. **CSV файлы не обрабатываются:**
   - Проверьте названия колонок в настройках
   - Убедитесь что данные соответствуют ожидаемому формату

4. **Webhook не отправляется:**
   - Проверьте URL и токен
   - Убедитесь что сервер доступен

### Отладка

Включите детальное логирование:
```env
LOG_LEVEL=DEBUG
```

## Требования

- Python 3.11+
- Google Chrome
- IMAP доступ к email
- Интернет соединение для webhook

## Поддерживаемые форматы

- **Архивы:** ZIP, RAR, 7Z
- **Данные:** CSV файлы
- **Email:** IMAP серверы (Gmail, Outlook, и др.)

## Лицензия

MIT License

## Поддержка

Для вопросов и поддержки создайте issue в репозитории.
