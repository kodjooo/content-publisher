"""Точка входа для сервиса публикации."""

from datetime import datetime

import pytz

from publisher.config import load_config
from publisher.core.logger import configure_logging, get_logger
from publisher.gs.sheets import SheetsClient
from publisher.services.publisher import PublisherService
from publisher.telegraph.client import TelegraphClient
from publisher.tg.client import TelegramClient
from publisher.vk.client import VKClient


def main() -> None:
    """Запускает обработку всех очередей."""
    config = load_config()
    configure_logging(config.log_level)
    logger = get_logger("publisher.entry")

    logger.info("Старт сервиса публикации")

    sheets = SheetsClient(config.google)
    telegraph = TelegraphClient(config.telegraph)
    vk = VKClient(config.vk)
    telegram = TelegramClient(config.telegram)

    service = PublisherService(sheets, telegraph, vk, telegram)

    moscow_tz = pytz.timezone("Europe/Moscow")
    now_msk = datetime.now(moscow_tz)

    should_run_rss = now_msk.hour in config.rss_hours
    should_run_vk = now_msk.hour == config.vk_hour and now_msk.weekday() in config.vk_schedule_days
    should_run_setka = now_msk.hour == config.setka_hour and now_msk.weekday() in config.setka_schedule_days

    if should_run_rss:
        logger.info("Запуск RSS-публикаций", extra={"hour": now_msk.hour})
        service.process_rss_flow()
    else:
        logger.info(
            "Пропуск RSS по расписанию",
            extra={"hour": now_msk.hour, "allowed_hours": config.rss_hours},
        )

    if should_run_vk:
        logger.info(
            "Запуск публикаций VK",
            extra={"weekday": now_msk.weekday(), "hour": now_msk.hour},
        )
        service.process_vk_flow()
    else:
        logger.info(
            "Пропуск VK по расписанию",
            extra={"weekday": now_msk.weekday(), "hour": now_msk.hour},
        )

    if should_run_setka:
        logger.info(
            "Запуск публикаций Setka",
            extra={"weekday": now_msk.weekday(), "hour": now_msk.hour},
        )
        service.process_setka_flow()
    else:
        logger.info(
            "Пропуск Setka по расписанию",
            extra={"weekday": now_msk.weekday(), "hour": now_msk.hour},
        )

    logger.info("Сервис завершил работу")


if __name__ == "__main__":
    main()
