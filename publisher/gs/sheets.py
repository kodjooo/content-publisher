"""Работа с Google Sheets."""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import gspread
from gspread.exceptions import APIError
from gspread.utils import rowcol_to_a1

from publisher.config import GoogleSheetsConfig
from publisher.core.retry import retry_on_exceptions


@dataclass
class RSSRow:
    row_number: int
    gpt_post_title: str
    gpt_post: str
    short_post: str
    average_post: str
    link: str
    image_url: str
    telegraph_link: str
    vk_post_link: str
    telegram_post_link: str
    status: str


@dataclass
class VKRow:
    row_number: int
    title: str
    content: str
    image_url: str
    post_link: str
    status: str


@dataclass
class SetkaRow:
    row_number: int
    title: str
    content: str
    image_url: str
    post_link: str
    status: str


class SheetsClient:
    """Клиент для чтения и обновления строк Google Sheets."""

    def __init__(self, config: GoogleSheetsConfig) -> None:
        self._client = gspread.service_account(filename=str(config.service_account_json))
        self._spreadsheet = self._client.open_by_key(config.sheet_id)

    def fetch_rss_ready_rows(self) -> List[RSSRow]:
        """Возвращает строки RSS со статусом Revised."""
        worksheet, header_map, rows = self._fetch_rows("RSS")
        result: List[RSSRow] = []
        for row_number, data in rows:
            status = data.get("Status", "")
            if status.lower() != "revised":
                continue
            result.append(
                RSSRow(
                    row_number=row_number,
                    gpt_post_title=data.get("GPT Post Title", ""),
                    gpt_post=data.get("GPT Post", ""),
                    short_post=data.get("Short Post", ""),
                    average_post=data.get("Average Post", ""),
                    link=data.get("Link", ""),
                    image_url=data.get("Image URL", ""),
                    telegraph_link=data.get("Telegraph Link", ""),
                    vk_post_link=data.get("VK Post Link", ""),
                    telegram_post_link=data.get("TG Post Link", ""),
                    status=status,
                )
            )
        return result

    def update_rss_row(self, row: RSSRow, telegraph_link: str, vk_link: str, telegram_link: str) -> None:
        """Обновляет ссылки и статус строки RSS."""
        worksheet, header_map, _ = self._fetch_rows("RSS")
        updates = {
            "Telegraph Link": telegraph_link,
            "VK Post Link": vk_link,
            "TG Post Link": telegram_link,
            "Status": "Published",
            "Notes": "",
        }
        self._update_cells(worksheet, header_map, row.row_number, updates)

    def write_rss_error(self, row: RSSRow, message: str) -> None:
        """Записывает ошибку для строки RSS."""
        worksheet, header_map, _ = self._fetch_rows("RSS")
        updates = {
            "Notes": message,
        }
        self._update_cells(worksheet, header_map, row.row_number, updates)

    def fetch_vk_rows(self) -> List[VKRow]:
        """Возвращает строки вкладки VK, требующие публикации."""
        _, _, rows = self._fetch_rows("VK")
        result: List[VKRow] = []
        for row_number, data in rows:
            status = data.get("Status", "")
            if status.lower() != "revised":
                continue
            result.append(
                VKRow(
                    row_number=row_number,
                    title=data.get("Title", ""),
                    content=data.get("Content", ""),
                    image_url=data.get("Image URL", ""),
                    post_link=data.get("Post Link", ""),
                    status=status,
                )
            )
        return result

    def mark_vk_published(self, row: VKRow, link: str) -> None:
        """Отмечает строку VK как опубликованную."""
        worksheet, header_map, _ = self._fetch_rows("VK")
        updates = {
            "Post Link": link,
            "Status": "Published",
            "Publish Note": "",
        }
        self._update_cells(worksheet, header_map, row.row_number, updates)

    def write_vk_error(self, row: VKRow, message: str) -> None:
        """Записывает ошибку для строки VK."""
        worksheet, header_map, _ = self._fetch_rows("VK")
        updates = {
            "Publish Note": message,
        }
        self._update_cells(worksheet, header_map, row.row_number, updates)

    def fetch_setka_rows(self) -> List[SetkaRow]:
        """Возвращает строки вкладки Setka, требующие публикации."""
        _, _, rows = self._fetch_rows("Setka")
        result: List[SetkaRow] = []
        for row_number, data in rows:
            status = data.get("Status", "")
            if status.lower() != "revised":
                continue
            result.append(
                SetkaRow(
                    row_number=row_number,
                    title=data.get("Title", ""),
                    content=data.get("Content", ""),
                    image_url=data.get("Image URL", ""),
                    post_link=data.get("Post Link", ""),
                    status=status,
                )
            )
        return result

    def mark_setka_published(self, row: SetkaRow, link: str) -> None:
        """Отмечает строку Setka как опубликованную."""
        worksheet, header_map, _ = self._fetch_rows("Setka")
        updates = {
            "Post Link": link,
            "Status": "Published",
            "Publish Note": "",
        }
        self._update_cells(worksheet, header_map, row.row_number, updates)

    def write_setka_error(self, row: SetkaRow, message: str) -> None:
        """Записывает ошибку для строки Setka."""
        worksheet, header_map, _ = self._fetch_rows("Setka")
        updates = {
            "Publish Note": message,
        }
        self._update_cells(worksheet, header_map, row.row_number, updates)

    @retry_on_exceptions((APIError,))
    def _fetch_rows(self, tab_name: str) -> Tuple[gspread.Worksheet, Dict[str, int], List[Tuple[int, Dict[str, str]]]]:
        """Читает все строки вкладки с номерами и заголовками."""
        worksheet = self._spreadsheet.worksheet(tab_name)
        all_values = worksheet.get_all_values()
        if not all_values:
            return worksheet, {}, []

        headers = [header.strip() for header in all_values[0]]
        header_map = {header: idx for idx, header in enumerate(headers)}

        result: List[Tuple[int, Dict[str, str]]] = []
        for offset, row_values in enumerate(all_values[1:], start=2):
            row_dict: Dict[str, str] = {}
            for idx, header in enumerate(headers):
                value = row_values[idx] if idx < len(row_values) else ""
                row_dict[header] = value.strip()
            result.append((offset, row_dict))
        return worksheet, header_map, result

    @retry_on_exceptions((APIError,))
    def _update_cells(
        self,
        worksheet: gspread.Worksheet,
        header_map: Dict[str, int],
        row_number: int,
        updates: Dict[str, str],
    ) -> None:
        """Записывает значения в указанные ячейки."""
        for header, value in updates.items():
            if header not in header_map:
                continue
            column_index = header_map[header] + 1
            cell = rowcol_to_a1(row_number, column_index)
            worksheet.update(cell, [[value]])
