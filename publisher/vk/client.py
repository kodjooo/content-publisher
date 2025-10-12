"""Клиент VK API."""

from typing import Dict, Optional, Tuple

import requests
from requests import Response

from publisher.config import VKConfig
from publisher.core.retry import retry_on_exceptions


class VKError(RuntimeError):
    """Ошибка работы с VK API."""


class VKClient:
    """Публикация постов во VK."""

    API_BASE = "https://api.vk.com/method"
    API_VERSION = "5.131"

    def __init__(self, config: VKConfig) -> None:
        self._access_token = config.user_access_token
        self._group_id = config.group_id
        self._session = requests.Session()

    def publish_post(self, message: str, image_url: str) -> str:
        """Публикует пост и возвращает ссылку."""
        upload_url = self._get_upload_url()
        attachment = self._upload_photo(upload_url, image_url)
        post_id = self._create_post(message, attachment)
        return f"https://vk.com/wall-{self._group_id}_{post_id}"

    def get_short_link(self, url: str) -> str:
        """Возвращает сокращённую ссылку через utils.getShortLink."""
        if not url:
            return url
        response = self._api_call("utils.getShortLink", url=url)
        short = response.get("short_url")
        return short or url

    def _get_upload_url(self) -> str:
        """Возвращает URL загрузки фото."""
        response = self._api_call(
            "photos.getWallUploadServer",
            group_id=self._group_id,
        )
        upload_url = response["upload_url"]
        return upload_url

    def _upload_photo(self, upload_url: str, image_url: str) -> str:
        """Загружает фото и возвращает идентификатор вложения."""
        image_bytes, mime, filename = self._download_image(image_url)
        from io import BytesIO
        files = {"photo": (filename, BytesIO(image_bytes), mime or "image/jpeg")}
        upload_response = self._post(upload_url, files=files)
        data = upload_response.json()
        photo_payload = data.get("photo")
        if not photo_payload or photo_payload in ("[]", []):
            raise VKError(f"Сервер загрузки VK вернул пустой результат: {data}")
        server = data.get("server")
        upload_hash = data.get("hash")
        if server is None or upload_hash is None:
            raise VKError(f"В ответе VK отсутствуют обязательные поля: {data}")
        saved = self._api_call(
            "photos.saveWallPhoto",
            group_id=self._group_id,
            photo=photo_payload,
            server=server,
            hash=upload_hash,
        )
        if not saved:
            raise VKError("VK не вернул сохранённое фото")
        photo = saved[0]
        return f"photo{photo['owner_id']}_{photo['id']}"

    def _create_post(self, message: str, attachment: str) -> int:
        """Создаёт запись на стене и возвращает идентификатор поста."""
        response = self._api_call(
            "wall.post",
            owner_id=-self._group_id,
            from_group=1,
            message=message,
            attachments=attachment,
        )
        post_id = response["post_id"]
        return post_id

    def _download_image(self, image_url: str) -> Tuple[bytes, Optional[str], str]:
        """Загружает изображение по URL."""
        response = self._get(image_url, stream=True)
        content_type = response.headers.get("Content-Type")
        filename = self._derive_filename(image_url, content_type)
        return response.content, content_type, filename

    @retry_on_exceptions((requests.RequestException,))
    def _api_call(self, method: str, **params) -> Dict[str, object]:
        """Вызывает метод VK API и возвращает результат."""
        url = f"{self.API_BASE}/{method}"
        payload = {
            "access_token": self._access_token,
            "v": self.API_VERSION,
            **params,
        }
        response = self._session.post(url, data=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise VKError(f"Ошибка VK API: {data['error']}")
        return data["response"]

    @retry_on_exceptions((requests.RequestException,))
    def _post(self, url: str, **kwargs) -> Response:
        """POST-запрос с повторами."""
        response = self._session.post(url, timeout=20, **kwargs)
        response.raise_for_status()
        return response

    @retry_on_exceptions((requests.RequestException,))
    def _get(self, url: str, **kwargs) -> Response:
        """GET-запрос с повторами."""
        response = self._session.get(url, timeout=20, **kwargs)
        response.raise_for_status()
        return response

    def _derive_filename(self, image_url: str, content_type: Optional[str]) -> str:
        """Определяет имя файла для загрузки в VK."""
        from urllib.parse import urlparse
        import mimetypes
        path = urlparse(image_url).path
        name = path.rsplit("/", 1)[-1] if "/" in path else ""
        if not name:
            extension = mimetypes.guess_extension(content_type or "") or ".jpg"
            return f"image{extension}"
        if "." not in name:
            extension = mimetypes.guess_extension(content_type or "") or ".jpg"
            return f"{name}{extension}"
        return name
