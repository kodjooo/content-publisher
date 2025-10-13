"""Загрузка и валидация конфигурации приложения."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set, Tuple

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
    group_id: int


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
    vk_schedule_days: Set[int]
    setka_schedule_days: Set[int]
    rss_hours: Tuple[int, int]
    vk_hour: int
    setka_hour: int
    run_on_start: bool


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
        service_account_json=_resolve_path(_require("GOOGLE_SERVICE_ACCOUNT_JSON")),
    )

    telegraph = TelegraphConfig(
        access_token=os.getenv("TELEGRAPH_ACCESS_TOKEN"),
        author_name=_require("TELEGRAPH_AUTHOR_NAME"),
        author_url=_require("TELEGRAPH_AUTHOR_URL"),
    )

    vk = VKConfig(
        user_access_token=_require("VK_USER_ACCESS_TOKEN"),
        group_id=int(_require("VK_GROUP_ID")),
    )

    telegram = TelegramConfig(
        bot_token=_require("TELEGRAM_BOT_TOKEN"),
        channel_username=_require("TELEGRAM_CHANNEL_USERNAME"),
    )

    log_level = os.getenv("LOG_LEVEL", "INFO")

    vk_days = _parse_publish_days(os.getenv("VK_PUBLISH_DAYS", "mon,tue,wed,thu,fri,sat,sun"))
    setka_days = _parse_publish_days(os.getenv("SETKA_PUBLISH_DAYS", "mon,tue,wed,thu,fri,sat,sun"))

    return AppConfig(
        google=google,
        telegraph=telegraph,
        vk=vk,
        telegram=telegram,
        log_level=log_level,
        vk_schedule_days=vk_days,
        setka_schedule_days=setka_days,
        rss_hours=(8, 20),
        vk_hour=18,
        setka_hour=18,
        run_on_start=_parse_bool(os.getenv("RUN_ON_START", "false")),
    )


def _parse_publish_days(raw: str) -> Set[int]:
    """Преобразует список дней недели в набор индексов (0=понедельник)."""
    day_map = {
        "mon": 0,
        "monday": 0,
        "tue": 1,
        "tues": 1,
        "tuesday": 1,
        "wed": 2,
        "wednesday": 2,
        "thu": 3,
        "thur": 3,
        "thurs": 3,
        "thursday": 3,
        "fri": 4,
        "friday": 4,
        "sat": 5,
        "saturday": 5,
        "sun": 6,
        "sunday": 6,
    }
    result: Set[int] = set()
    for token in raw.replace(";", ",").split(","):
        value = token.strip().lower()
        if not value:
            continue
        if value not in day_map:
            raise ValueError(f"Неизвестное значение дня недели: {token}")
        result.add(day_map[value])
    if not result:
        raise ValueError("Список дней публикации не может быть пустым")
    return result


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(raw: str) -> Path:
    """Находит существующий путь к файлу сервисного аккаунта."""
    primary = Path(raw).expanduser()
    if primary.exists():
        return primary
    alternative = Path.cwd() / raw.lstrip("/")
    if alternative.exists():
        return alternative
    raise FileNotFoundError(f"Файл {raw} не найден (пробованы {primary} и {alternative})")
