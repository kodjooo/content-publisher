"""Бизнес-логика публикации контента."""

from typing import Optional

from publisher.core.logger import get_logger
from publisher.gs.sheets import RSSRow, SetkaRow, SheetsClient, VKRow
from publisher.telegraph.client import TelegraphClient
from publisher.tg.client import TelegramClient
from publisher.vk.client import VKClient


class PublisherService:
    """Оркестратор публикаций."""

    def __init__(
        self,
        sheets: SheetsClient,
        telegraph: TelegraphClient,
        vk: VKClient,
        telegram: TelegramClient,
    ) -> None:
        self._sheets = sheets
        self._telegraph = telegraph
        self._vk = vk
        self._telegram = telegram
        self._logger = get_logger("publisher")

    def run_all(self) -> None:
        """Запускает все сценарии."""
        self.process_rss_flow()
        self.process_vk_flow()
        self.process_setka_flow()

    def process_rss_flow(self) -> None:
        """Обрабатывает RSS-строки."""
        rows = self._sheets.fetch_rss_ready_rows()
        if not rows:
            self._logger.info("Нет строк RSS для публикации")
            return
        for row in rows:
            self._logger.info("Начало обработки RSS", extra={"row": row.row_number})
            try:
                telegraph_link = row.telegraph_link
                if not telegraph_link:
                    title = self._derive_title(row.gpt_post_title, row.gpt_post)
                    telegraph_link = self._telegraph.create_page(title=title, gpt_post=row.gpt_post, image_url=row.image_url or None)
                sanitized_short = self._prepare_short_post(row.short_post, row.gpt_post_title)
                short_link = self._vk.get_short_link(telegraph_link) if telegraph_link else telegraph_link
                vk_message = self._compose_vk_short_post(sanitized_short, short_link)
                vk_link = self._vk.publish_post(vk_message, row.image_url)
                telegram_link = self._telegram.send_post(sanitized_short, row.image_url, telegraph_link, add_spacing=True)
                self._sheets.update_rss_row(row, telegraph_link, vk_link, telegram_link)
                self._logger.info(
                    "RSS опубликован",
                    extra={
                        "row": row.row_number,
                        "telegraph_link": telegraph_link,
                        "vk_link": vk_link,
                        "telegram_link": telegram_link,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                self._logger.error("Ошибка RSS", extra={"row": row.row_number, "error": message})
                self._sheets.write_rss_error(row, message)

    def process_vk_flow(self) -> None:
        """Обрабатывает точечные посты VK."""
        rows = self._sheets.fetch_vk_rows()
        if not rows:
            self._logger.info("Нет строк VK для публикации")
            return
        row = rows[0]
        self._logger.info("Начало обработки VK", extra={"row": row.row_number})
        try:
            message = self._compose_vk_message(row.title, row.content)
            link = self._vk.publish_post(message, row.image_url)
            self._sheets.mark_vk_published(row, link)
            self._logger.info("VK опубликован", extra={"row": row.row_number, "vk_link": link})
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            self._logger.error("Ошибка VK", extra={"row": row.row_number, "error": message})
            self._sheets.write_vk_error(row, message)

    def process_setka_flow(self) -> None:
        """Обрабатывает точечные посты Telegram."""
        rows = self._sheets.fetch_setka_rows()
        if not rows:
            self._logger.info("Нет строк Setka для публикации")
            return
        row = rows[0]
        self._logger.info("Начало обработки Setka", extra={"row": row.row_number})
        try:
            message = self._compose_vk_message(row.title, row.content)
            image_url = row.image_url.strip()
            link = self._telegram.send_post(message, image_url or None, add_spacing=True)
            self._sheets.mark_setka_published(row, link)
            self._logger.info("Setka опубликован", extra={"row": row.row_number, "telegram_link": link})
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            self._logger.error("Ошибка Setka", extra={"row": row.row_number, "error": message})
            self._sheets.write_setka_error(row, message)

    def _derive_title(self, explicit_title: str, gpt_post: str) -> str:
        """Формирует заголовок для Telegraph."""
        if explicit_title.strip():
            return explicit_title.strip()[:100]
        text = gpt_post.strip()
        if not text:
            return "Без названия"
        return text[:100]

    def _compose_vk_short_post(self, short_post: str, telegraph_link: str) -> str:
        """Возвращает короткий пост с ссылкой для VK."""
        short = short_post.strip()
        parts = [short] if short else []
        if telegraph_link:
            parts.append(f"Читать подробнее > {telegraph_link}")
        return "\n\n".join(part for part in parts if part)

    def _prepare_short_post(self, short_post: str, title: str) -> str:
        """Удаляет старую подпись и добавляет хэштег с заголовком."""
        lines = [line.rstrip() for line in short_post.strip().splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        if not lines:
            body = ""
        else:
            last = lines[-1]
            lowered = last.lower()
            if "читать подробнее" in lowered:
                lines.pop()
                while lines and not lines[-1]:
                    lines.pop()
            body = "\n".join(lines)
        header_lines = ["#Обзор_Новостей"]
        normalized_title = title.strip()
        if normalized_title:
            header_lines.append(normalized_title)
        content_lines = [part for part in [body] if part]
        return "\n".join(header_lines + ([""] if content_lines else []) + content_lines)

    def _compose_vk_message(self, title: str, content: str) -> str:
        """Собирает текст для VK или Telegram."""
        parts = [title.strip(), content.strip()]
        filtered = [part for part in parts if part]
        return "\n\n".join(filtered)
