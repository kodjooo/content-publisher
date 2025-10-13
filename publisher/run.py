"""Точка входа для сервиса публикации."""

from datetime import datetime, date
import time
from typing import Dict, Tuple

import pytz

from publisher.config import load_config
from publisher.core.logger import configure_logging, get_logger
from publisher.gs.sheets import SheetsClient
from publisher.services.publisher import PublisherService
from publisher.telegraph.client import TelegraphClient
from publisher.tg.client import TelegramClient
from publisher.vk.client import VKClient


def main() -> None:
    """Запускает сервис и держит его запущенным для работы по расписанию."""
    config = load_config()
    configure_logging(config.log_level)
    logger = get_logger("publisher.entry")

    logger.info("Сервис запускается и переходит в режим ожидания расписания")

    sheets = SheetsClient(config.google)
    telegraph = TelegraphClient(config.telegraph)
    vk = VKClient(config.vk)
    telegram = TelegramClient(config.telegram)

    service = PublisherService(sheets, telegraph, vk, telegram)

    moscow_tz = pytz.timezone("Europe/Moscow")

    if config.run_on_start:
        logger.info("Тестовый запуск по стартовой конфигурации")
        _process_all(service, logger)

    last_runs_rss: Dict[int, date] = {}
    last_run_vk: Tuple[date, int] | None = None
    last_run_setka: Tuple[date, int] | None = None

    last_skip_logged = {
        "rss": None,
        "vk": None,
        "setka": None,
    }

    try:
        while True:
            now_msk = datetime.now(moscow_tz)
            minute = now_msk.minute
            current_date = now_msk.date()
            weekday = now_msk.weekday()

            # RSS – два окна в сутки
            if minute == 0 and now_msk.hour in config.rss_hours:
                hour = now_msk.hour
                if last_runs_rss.get(hour) != current_date:
                    logger.info(
                        "Запуск RSS-публикаций",
                        extra={"hour": hour, "date": str(current_date)},
                    )
                    service.process_rss_flow()
                    last_runs_rss[hour] = current_date
                else:
                    _log_skip_once(
                        logger,
                        last_skip_logged,
                        "rss",
                        now_msk,
                        reason="RSS уже опубликован в этот час",
                    )
            elif minute == 0 and last_skip_logged["rss"] != (current_date, now_msk.hour):
                _log_skip_once(
                    logger,
                    last_skip_logged,
                    "rss",
                    now_msk,
                    reason="вне окна публикации",
                    extra={"allowed_hours": config.rss_hours},
                )

            # VK – один пост в разрешённые дни
            if (
                minute == 0
                and now_msk.hour == config.vk_hour
                and weekday in config.vk_schedule_days
            ):
                if last_run_vk != (current_date, config.vk_hour):
                    logger.info(
                        "Запуск публикации VK",
                        extra={"hour": config.vk_hour, "weekday": weekday},
                    )
                    service.process_vk_flow()
                    last_run_vk = (current_date, config.vk_hour)
                else:
                    _log_skip_once(
                        logger,
                        last_skip_logged,
                        "vk",
                        now_msk,
                        reason="пост VK уже опубликован сегодня",
                    )
            elif minute == 0 and last_skip_logged["vk"] != (current_date, now_msk.hour):
                reason = (
                    "неразрешённый день" if weekday not in config.vk_schedule_days else "вне окна"
                )
                _log_skip_once(
                    logger,
                    last_skip_logged,
                    "vk",
                    now_msk,
                    reason=reason,
                    extra={"allowed_days": sorted(config.vk_schedule_days)},
                )

            # Setka – один пост в разрешённые дни
            if (
                minute == 0
                and now_msk.hour == config.setka_hour
                and weekday in config.setka_schedule_days
            ):
                if last_run_setka != (current_date, config.setka_hour):
                    logger.info(
                        "Запуск публикации Setka",
                        extra={"hour": config.setka_hour, "weekday": weekday},
                    )
                    service.process_setka_flow()
                    last_run_setka = (current_date, config.setka_hour)
                else:
                    _log_skip_once(
                        logger,
                        last_skip_logged,
                        "setka",
                        now_msk,
                        reason="пост Setka уже опубликован сегодня",
                    )
            elif minute == 0 and last_skip_logged["setka"] != (current_date, now_msk.hour):
                reason = (
                    "неразрешённый день"
                    if weekday not in config.setka_schedule_days
                    else "вне окна"
                )
                _log_skip_once(
                    logger,
                    last_skip_logged,
                    "setka",
                    now_msk,
                    reason=reason,
                    extra={"allowed_days": sorted(config.setka_schedule_days)},
                )

            # Сон до начала следующей минуты
            sleep_seconds = 60 - now_msk.second
            if sleep_seconds <= 0:
                sleep_seconds = 60
            time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        logger.info("Сервис остановлен пользователем")


def _log_skip_once(logger, cache, key, timestamp, reason, extra=None):
    """Логирует события пропуска не чаще одного раза в час."""
    signature = (timestamp.date(), timestamp.hour)
    if cache[key] == signature:
        return
    payload = {"reason": reason, "hour": timestamp.hour, "weekday": timestamp.weekday()}
    if extra:
        payload.update(extra)
    logger.info("Пропуск публикации", extra={"flow": key, **payload})
    cache[key] = signature


def _process_all(service: PublisherService, logger) -> None:
    """Выполняет полный цикл публикаций вне расписания."""
    try:
        logger.info("Тестовый запуск: RSS")
        service.process_rss_flow()
    except Exception as exc:  # noqa: BLE001
        logger.error("Тестовый запуск RSS завершился ошибкой", extra={"error": str(exc)})

    try:
        logger.info("Тестовый запуск: VK")
        service.process_vk_flow()
    except Exception as exc:  # noqa: BLE001
        logger.error("Тестовый запуск VK завершился ошибкой", extra={"error": str(exc)})

    try:
        logger.info("Тестовый запуск: Setka")
        service.process_setka_flow()
    except Exception as exc:  # noqa: BLE001
        logger.error("Тестовый запуск Setka завершился ошибкой", extra={"error": str(exc)})


if __name__ == "__main__":
    main()
