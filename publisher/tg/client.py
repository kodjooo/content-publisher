"""Клиент Telegram Bot API."""

import html
from typing import Optional

import requests
from requests import Response

from publisher.config import TelegramConfig
from publisher.core.retry import retry_on_exceptions


class TelegramError(RuntimeError):
    """Ошибка Telegram API."""


class TelegramClient:
    """Публикация постов в Telegram канал."""

    API_BASE = "https://api.telegram.org"
    CAPTION_LIMIT = 1024

    def __init__(self, config: TelegramConfig) -> None:
        self._token = config.bot_token
        self._channel = config.channel_username if config.channel_username.startswith("@") else f"@{config.channel_username}"
        self._session = requests.Session()

    def send_post(self, text: str, image_url: str, telegraph_link: Optional[str] = None) -> str:
        """Отправляет пост и возвращает ссылку."""
        safe_text = html.escape(text.strip())
        caption = safe_text
        if telegraph_link:
            link = html.escape(telegraph_link, quote=True)
            caption = f"{safe_text}\n\n<a href=\"{link}\">Читать подробнее &gt;</a>" if safe_text else f"<a href=\"{link}\">Читать подробнее &gt;</a>"
        caption = self._truncate_caption(caption)
        payload = {
            "chat_id": self._channel,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML",
        }
        response = self._post("/sendPhoto", data=payload)
        data = response.json()
        if not data.get("ok"):
            raise TelegramError(f"Ошибка отправки сообщения: {data}")
        result = data["result"]
        message_id = result["message_id"]
        channel = self._channel.lstrip("@")
        return f"https://t.me/{channel}/{message_id}"

    def _truncate_caption(self, caption: str) -> str:
        """Обрезает подпись до допустимого размера."""
        if len(caption) <= self.CAPTION_LIMIT:
            return caption
        return caption[: self.CAPTION_LIMIT - 1] + "…"

    @retry_on_exceptions((requests.RequestException,))
    def _post(self, path: str, **kwargs) -> Response:
        """POST-запрос к Telegram Bot API."""
        url = f"{self.API_BASE}/bot{self._token}{path}"
        response = self._session.post(url, timeout=10, **kwargs)
        response.raise_for_status()
        return response
