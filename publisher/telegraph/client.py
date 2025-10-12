"""Клиент Telegra.ph API."""

import json
from typing import Dict, List, Optional

import requests
from requests import Response

from publisher.config import TelegraphConfig
from publisher.core.retry import retry_on_exceptions


class TelegraphError(RuntimeError):
    """Ошибка при работе с Telegra.ph."""


class TelegraphClient:
    """Создание страниц в Telegra.ph."""

    API_BASE = "https://api.telegra.ph"

    def __init__(self, config: TelegraphConfig) -> None:
        self._token = config.access_token
        self._author_name = config.author_name
        self._author_url = config.author_url
        self._session = requests.Session()

    def ensure_token(self) -> None:
        """Гарантирует наличие access_token."""
        if self._token:
            return
        payload = {
            "short_name": "Mark",
            "author_name": self._author_name,
            "author_url": self._author_url,
        }
        response = self._post("/createAccount", data=payload)
        data = response.json()
        if not data.get("ok"):
            raise TelegraphError(f"Не удалось создать аккаунт: {data}")
        result = data["result"]
        self._token = result["access_token"]

    def create_page(self, title: str, gpt_post: str, image_url: Optional[str] = None) -> str:
        """Создаёт страницу и возвращает ссылку."""
        self.ensure_token()
        if not self._token:
            raise TelegraphError("access_token не установлен")

        content = self._build_content(gpt_post, image_url)
        payload = {
            "access_token": self._token,
            "title": title[:100],
            "author_name": self._author_name,
            "author_url": self._author_url,
            "content": json.dumps(content, ensure_ascii=False),
            "return_content": False,
        }
        response = self._post("/createPage", data=payload)
        data = response.json()
        if not data.get("ok"):
            raise TelegraphError(f"Не удалось создать страницу: {data}")
        return data["result"]["url"]

    def _build_content(self, gpt_post: str, image_url: Optional[str]) -> List[Dict[str, object]]:
        """Формирует структуру контента для Telegraph."""
        parsed: Optional[List[Dict[str, object]]] = None
        try:
            data = json.loads(gpt_post)
            if isinstance(data, dict):
                parsed = [data]
            elif isinstance(data, list):
                parsed = data  # type: ignore[assignment]
        except (json.JSONDecodeError, TypeError):
            parsed = None

        if parsed is not None:
            nodes = parsed.copy()
        else:
            nodes = []
            text = gpt_post.replace("\r\n", "\n")
            for paragraph in text.split("\n\n"):
                cleaned = paragraph.strip()
                if not cleaned:
                    continue
                nodes.append({"tag": "p", "children": [cleaned]})

        if image_url:
            figure_node: Dict[str, object] = {
                "tag": "figure",
                "children": [
                    {
                        "tag": "img",
                        "attrs": {"src": image_url},
                    }
                ],
            }
            nodes = [figure_node] + nodes
        return nodes

    @retry_on_exceptions((requests.RequestException,))
    def _post(self, path: str, **kwargs) -> Response:
        """Выполняет POST-запрос с повторами."""
        url = f"{self.API_BASE}{path}"
        response = self._session.post(url, **kwargs, timeout=10)
        response.raise_for_status()
        return response
