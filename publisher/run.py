"""Точка входа для сервиса публикации."""

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
    service.run_all()

    logger.info("Сервис завершил работу")


if __name__ == "__main__":
    main()
