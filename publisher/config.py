"""Загрузка и валидация конфигурации приложения."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import os


@dataclass(frozen=True)
class GoogleSheetsConfig:
    sheet_id: str
    service_account_json: Path


@dataclass(frozen=True)
class TelegraphConfig:
    access_token: Optional[str]
    author_name: str
    author_url: str


@dataclass(frozen=True)
class VKConfig:
    user_access_token: str
    user_id: str


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    channel_username: str


@dataclass(frozen=True)
class AppConfig:
    google: GoogleSheetsConfig
    telegraph: TelegraphConfig
    vk: VKConfig
    telegram: TelegramConfig
    log_level: str


def _require(env_name: str) -> str:
    """Возвращает обязательную переменную окружения."""
    value = os.getenv(env_name)
    if not value:
        raise ValueError(f"Переменная окружения {env_name} не задана")
    return value


def load_config() -> AppConfig:
    """Загружает конфигурацию из окружения."""
    load_dotenv()

    google = GoogleSheetsConfig(
        sheet_id=_require("GOOGLE_SHEET_ID"),
        service_account_json=Path(_require("GOOGLE_SERVICE_ACCOUNT_JSON")),
    )

    telegraph = TelegraphConfig(
        access_token=os.getenv("TELEGRAPH_ACCESS_TOKEN"),
        author_name=_require("TELEGRAPH_AUTHOR_NAME"),
        author_url=_require("TELEGRAPH_AUTHOR_URL"),
    )

    vk = VKConfig(
        user_access_token=_require("VK_USER_ACCESS_TOKEN"),
        user_id=_require("VK_USER_ID"),
    )

    telegram = TelegramConfig(
        bot_token=_require("TELEGRAM_BOT_TOKEN"),
        channel_username=_require("TELEGRAM_CHANNEL_USERNAME"),
    )

    log_level = os.getenv("LOG_LEVEL", "INFO")

    return AppConfig(
        google=google,
        telegraph=telegraph,
        vk=vk,
        telegram=telegram,
        log_level=log_level,
    )
