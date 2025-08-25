# 📧 Email Payment Processor

Автоматизированная система для обработки платежных данных из электронной почты с использованием Python и Docker.

## 🎯 Описание

Система автоматически:
- 📧 Получает новые письма с почтового сервера через IMAP
- 🔍 Ищет в письмах ссылки для скачивания файлов
- 🤖 Использует автоматизацию браузера для клика на кнопки и скачивания архивов
- 📦 Распаковывает архивы (ZIP, RAR, 7Z)
- 📊 Обрабатывает CSV файлы с платежными данными
- 💰 Извлекает информацию об оплатах согласно заданным условиям
- 🔗 Отправляет webhook с данными об оплатах на внешний сервер

## ⚡ Быстрый старт

### Docker (рекомендуется)

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd email-payment-processor

# Настройте конфигурацию
cp email-processor/env.example email-processor/.env
# Отредактируйте .env файл с вашими настройками

# Запустите систему
docker-compose up -d

# Просмотр логов
docker-compose logs -f email-processor
```

### Локальная установка

```bash
cd email-processor
pip install -r requirements.txt
python src/main.py --mode once
```

## 📋 Конфигурация

Основные настройки в `.env` файле:

```env
# Email Configuration
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Webhook Configuration  
WEBHOOK_URL=https://your-server.com/webhook/payments
WEBHOOK_TOKEN=your_secret_token

# CSV Processing
CSV_FILTER_COLUMN=status
CSV_FILTER_VALUE=completed
PAYMENT_AMOUNT_COLUMN=amount
PAYMENT_DATE_COLUMN=date
PAYMENT_ID_COLUMN=transaction_id
CUSTOMER_ID_COLUMN=customer_id
```

## 🏗️ Архитектура

```
📧 Email Server → 📨 Email Handler → 🔍 Link Extraction → 
🤖 Browser Automation → 📦 File Download → 🗃️ Archive Extraction → 
📊 CSV Processing → 💰 Payment Extraction → 📡 Webhook Sender → 🖥️ External Server
```

## 📁 Структура проекта

```
email-processor/
├── src/                    # Исходный код
│   ├── main.py            # Главный скрипт
│   ├── email_handler.py   # Работа с email
│   ├── browser_automation.py # Автоматизация браузера
│   ├── file_processor.py  # Обработка файлов
│   └── webhook_sender.py  # Отправка webhook
├── config/                # Конфигурация
├── downloads/             # Скачанные файлы
├── logs/                  # Логи приложения
├── requirements.txt       # Python зависимости
├── Dockerfile            # Docker образ
└── docker-compose.yml    # Docker композиция
```

## 🔧 Возможности

- ✅ **Модульная архитектура** - легко расширяемая и настраиваемая
- ✅ **Docker поддержка** - готов к развертыванию в контейнерах
- ✅ **Автоматизация браузера** - обработка сложных веб-форм
- ✅ **Множество форматов архивов** - ZIP, RAR, 7Z
- ✅ **Гибкая обработка CSV** - настраиваемые поля и условия
- ✅ **Webhook интеграция** - отправка данных в реальном времени
- ✅ **Детальное логирование** - полный мониторинг процесса
- ✅ **Безопасность** - переменные окружения для чувствительных данных

## 📊 Формат Webhook

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "event_type": "payments_processed", 
  "data": {
    "payments_count": 5,
    "summary": {
      "total_amount": 1500.00,
      "currencies": ["USD"],
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
        "status": "processed"
      }
    ]
  }
}
```

## 🛠️ Требования

- Python 3.11+
- Google Chrome (для автоматизации)
- IMAP доступ к email
- Docker (для контейнеризации)

## 📖 Документация

- [📚 Подробное руководство](email-processor/README.md)
- [⚡ Быстрый старт](email-processor/QUICK_START.md)

## 🔒 Безопасность

- 🔐 Используйте App Passwords для Gmail
- 🛡️ Храните токены в переменных окружения  
- 🔒 Используйте HTTPS для webhook URL
- 📝 Регулярно проверяйте логи

## 🤝 Поддержка

Для вопросов и поддержки создайте issue в репозитории.

## 📄 Лицензия

MIT License
