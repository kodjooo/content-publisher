#!/bin/bash

# Скрипт для настройки cron задачи email-processor
# Оптимизирован для production среды с мониторингом

# ВАЖНО: Измените путь на актуальный путь на вашем сервере
PROJECT_DIR="/usr/local/other-scripts/email-processor"
CRON_SCRIPT="$PROJECT_DIR/run_email_processor.sh"

echo "=== Настройка cron задачи для email-processor ==="
echo "Проект: $PROJECT_DIR"
echo "Скрипт: $CRON_SCRIPT"
echo ""

# Проверка существования директории проекта
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ ОШИБКА: Директория проекта $PROJECT_DIR не существует"
    echo "Создайте директорию или измените PROJECT_DIR в скрипте"
    exit 1
fi

# Проверка существования скрипта запуска
if [ ! -f "$CRON_SCRIPT" ]; then
    echo "❌ ОШИБКА: Скрипт $CRON_SCRIPT не найден"
    echo "Убедитесь что файл run_email_processor.sh скопирован на сервер"
    exit 1
fi

# Проверка и установка прав на выполнение
if [ ! -x "$CRON_SCRIPT" ]; then
    echo "🔧 Добавление прав на выполнение для скрипта..."
    chmod +x "$CRON_SCRIPT"
    
    if [ $? -eq 0 ]; then
        echo "✅ Права на выполнение добавлены"
    else
        echo "❌ ОШИБКА: Не удалось добавить права на выполнение"
        exit 1
    fi
fi

# Проверка доступности Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ ОШИБКА: Docker не установлен или недоступен"
    echo "Установите Docker перед настройкой cron"
    exit 1
fi

# Создание временного файла для cron задач
TEMP_CRON=$(mktemp)

# Получение текущих cron задач пользователя
crontab -l 2>/dev/null > "$TEMP_CRON"

# Проверка существующих задач email-processor
if grep -q "email-processor" "$TEMP_CRON"; then
    echo "⚠️  Задача для email-processor уже существует в cron:"
    echo ""
    grep "email-processor" "$TEMP_CRON" | sed 's/^/   /'
    echo ""
    
    read -p "Заменить существующую задачу? (y/N): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        # Удаление старых задач email-processor
        grep -v "email-processor" "$TEMP_CRON" > "${TEMP_CRON}.tmp"
        mv "${TEMP_CRON}.tmp" "$TEMP_CRON"
        echo "✅ Старая задача удалена"
    else
        echo "🚫 Настройка отменена пользователем"
        rm -f "$TEMP_CRON"
        exit 0
    fi
fi

# Добавление новой cron задачи
echo "" >> "$TEMP_CRON"
echo "# Email processor - автоматический запуск каждый день в 12:00 МСК" >> "$TEMP_CRON"
echo "# Время: 09:00 UTC = 12:00 МСК (летнее время)" >> "$TEMP_CRON"
echo "# Логи: $PROJECT_DIR/cron.log" >> "$TEMP_CRON"
echo "0 9 * * * $CRON_SCRIPT >/dev/null 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# Добавление еженедельной очистки Docker (опционально)
echo "# Еженедельная очистка Docker (каждое воскресенье в 02:00)" >> "$TEMP_CRON"
echo "0 2 * * 0 docker system prune -f >/dev/null 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# Установка новой cron таблицы
if crontab "$TEMP_CRON"; then
    echo "✅ Cron задача успешно добавлена!"
    echo ""
    echo "📅 Расписание:"
    echo "   Основной запуск: каждый день в 09:00 UTC (12:00 МСК летом)"
    echo "   Очистка Docker:  каждое воскресенье в 02:00 UTC"
    echo ""
    echo "📊 Мониторинг:"
    echo "   Логи cron:       tail -f $PROJECT_DIR/cron.log"
    echo "   Логи приложения: docker compose -f $PROJECT_DIR/docker-compose.yml run --rm email-processor tail -f /app/logs/email_processor.log"
    echo ""
    echo "⚠️  ВАЖНО для зимнего времени (ноябрь-февраль):"
    echo "   Измените время на: 0 8 * * * (08:00 UTC = 12:00 МСК зимой)"
    echo "   Команда: crontab -e"
    echo ""
    
    # Показать активные cron задачи
    echo "📋 Текущие cron задачи:"
    crontab -l | grep -E "(email-processor|docker system prune|^[^#])" | sed 's/^/   /'
    
else
    echo "❌ ОШИБКА: Не удалось установить cron задачу"
    echo "Проверьте права доступа и попробуйте снова"
    rm -f "$TEMP_CRON"
    exit 1
fi

# Очистка временного файла
rm -f "$TEMP_CRON"

echo ""
echo "=== Настройка завершена успешно! ==="
echo ""
echo "🔧 Полезные команды для управления:"
echo "   Просмотр всех cron задач:    crontab -l"
echo "   Редактирование cron:         crontab -e"
echo "   Удаление всех cron задач:    crontab -r"
echo "   Тестовый запуск:             $CRON_SCRIPT"
echo "   Просмотр логов:              tail -f $PROJECT_DIR/cron.log"
echo "   Поиск ошибок:                grep -i error $PROJECT_DIR/cron.log"
echo ""
echo "🎯 Следующие шаги:"
echo "   1. Убедитесь что .env файл настроен: $PROJECT_DIR/.env"
echo "   2. Проверьте тестовый запуск: $CRON_SCRIPT"
echo "   3. Дождитесь автоматического запуска в 12:00 МСК"
echo ""
