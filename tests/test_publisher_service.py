"""Тесты сервиса публикаций."""

from unittest.mock import MagicMock

import pytest

from publisher.gs.sheets import RSSRow, SetkaRow, VKRow
from publisher.services.publisher import PublisherService


@pytest.fixture()
def clients():
    sheets = MagicMock()
    telegraph = MagicMock()
    vk = MagicMock()
    telegram = MagicMock()
    service = PublisherService(sheets, telegraph, vk, telegram)
    return sheets, telegraph, vk, telegram, service


def test_process_rss_flow_success(clients):
    sheets, telegraph, vk, telegram, service = clients
    row = RSSRow(
        row_number=2,
        gpt_post_title="Заголовок статьи",
        gpt_post="Заголовок статьи\n\nОсновной текст",
        short_post="Короткая версия\n\nЧитать подробнее > https://example.com",
        image_url="https://example.com/image.jpg",
        telegraph_link="",
        vk_post_link="",
        telegram_post_link="",
        status="Revised",
    )
    sheets.fetch_rss_ready_rows.return_value = [row]
    telegraph.create_page.return_value = "https://telegra.ph/page"
    vk.get_short_link.return_value = "vk.cc/short"
    vk.publish_post.return_value = "https://vk.com/wall-1_1"
    telegram.send_post.return_value = "https://t.me/channel/1"

    service.process_rss_flow()

    telegraph.create_page.assert_called_once_with(title="Заголовок статьи", gpt_post=row.gpt_post, image_url=row.image_url)
    vk.get_short_link.assert_called_once_with("https://telegra.ph/page")
    vk.publish_post.assert_called_once()
    vk_message = vk.publish_post.call_args[0][0]
    assert vk_message.startswith("#Обзор_Новостей")
    assert "Заголовок статьи" in vk_message.splitlines()[1]
    assert "Читать подробнее > vk.cc/short" in vk_message
    telegram.send_post.assert_called_once_with("#Обзор_Новостей\nЗаголовок статьи\n\nКороткая версия", row.image_url, "https://telegra.ph/page", add_spacing=True)
    sheets.update_rss_row.assert_called_once_with(row, "https://telegra.ph/page", "https://vk.com/wall-1_1", "https://t.me/channel/1")
    sheets.write_rss_error.assert_not_called()


def test_process_rss_flow_uses_existing_telegraph_link(clients):
    sheets, telegraph, vk, telegram, service = clients
    row = RSSRow(
        row_number=3,
        gpt_post_title="",
        gpt_post="Существующий пост",
        short_post="Коротко\n\nЧитать подробнее > https://example.com",
        image_url="https://example.com/image.jpg",
        telegraph_link="https://telegra.ph/existing",
        vk_post_link="",
        telegram_post_link="",
        status="Revised",
    )
    sheets.fetch_rss_ready_rows.return_value = [row]
    vk.get_short_link.return_value = "vk.cc/existing"
    vk.publish_post.return_value = "https://vk.com/wall-1_2"
    telegram.send_post.return_value = "https://t.me/channel/2"

    service.process_rss_flow()

    telegraph.create_page.assert_not_called()
    sheets.update_rss_row.assert_called_once_with(row, "https://telegra.ph/existing", "https://vk.com/wall-1_2", "https://t.me/channel/2")
    vk.get_short_link.assert_called_once_with("https://telegra.ph/existing")
    telegram.send_post.assert_called_once_with("#Обзор_Новостей\n\nКоротко", row.image_url, "https://telegra.ph/existing", add_spacing=True)
    vk_message = vk.publish_post.call_args[0][0]
    assert vk_message.startswith("#Обзор_Новостей")
    assert "Читать подробнее > vk.cc/existing" in vk_message


def test_process_rss_flow_handles_errors(clients):
    sheets, telegraph, vk, telegram, service = clients
    row = RSSRow(
        row_number=4,
        gpt_post_title="",
        gpt_post="Текст",
        short_post="Коротко",
        image_url="https://example.com/image.jpg",
        telegraph_link="",
        vk_post_link="",
        telegram_post_link="",
        status="Revised",
    )
    sheets.fetch_rss_ready_rows.return_value = [row]
    telegraph.create_page.return_value = "https://telegra.ph/page"
    vk.publish_post.side_effect = RuntimeError("Ошибка VK")

    service.process_rss_flow()

    sheets.write_rss_error.assert_called_once()
    sheets.update_rss_row.assert_not_called()


def test_process_vk_flow_success(clients):
    sheets, _, vk, _, service = clients
    row = VKRow(
        row_number=5,
        title="Заголовок",
        content="Содержимое",
        image_url="https://example.com/image.jpg",
        post_link="",
        status="Revised",
    )
    sheets.fetch_vk_rows.return_value = [row]
    vk.publish_post.return_value = "https://vk.com/wall-1_3"

    service.process_vk_flow()

    vk.publish_post.assert_called_once()
    sheets.mark_vk_published.assert_called_once_with(row, "https://vk.com/wall-1_3")


def test_process_setka_flow_success(clients):
    sheets, _, _, telegram, service = clients
    row = SetkaRow(
        row_number=6,
        title="Заголовок",
        content="Содержимое",
        image_url="https://example.com/image.jpg",
        post_link="",
        status="Revised",
    )
    sheets.fetch_setka_rows.return_value = [row]
    telegram.send_post.return_value = "https://t.me/channel/3"

    service.process_setka_flow()

    telegram.send_post.assert_called_once()
    sheets.mark_setka_published.assert_called_once_with(row, "https://t.me/channel/3")
