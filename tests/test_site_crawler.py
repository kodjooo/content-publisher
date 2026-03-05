from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.config.models import GlobalConfig, SiteConfig
from app.crawler.site_crawler import SiteCrawler
from app.runtime import RuntimeContext


class FakeEngine:
    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.calls: list[str] = []

    def fetch_html(self, request) -> str:
        self.calls.append(request.url)
        return self.responses.get(request.url, "<div></div>")

    def shutdown(self) -> None:
        pass


def _site_config() -> SiteConfig:
    payload: dict[str, Any] = {
        "site": {
            "name": "demo",
            "domain": "demo.example",
            "engine": "http",
            "base_url": "https://demo.example",
        },
        "selectors": {
            "product_card_selector": ".product",
            "product_link_selector": "a",
            "price_without_discount_selector": ".old",
            "price_with_discount_selector": ".new",
            "rating_selector": ".rating",
            "out_of_stock_selector": ".oos",
            "allowed_domains": ["demo.example"],
        },
        "pagination": {
            "mode": "numbered_pages",
            "param_name": "page",
            "max_pages": 5,
        },
        "limits": {"max_products": 10},
        "category_urls": ["https://demo.example/catalog/"],
    }
    return SiteConfig.model_validate(payload)


def _global_config(tmp_path: Path) -> GlobalConfig:
    return GlobalConfig.model_validate(
        {
            "runtime": {
                "max_concurrency_per_site": 1,
                "global_stop": {},
                "page_delay": {"min_sec": 0, "max_sec": 0},
            },
            "network": {
                "user_agents": ["test-agent"],
                "proxy_pool": [],
                "request_timeout_sec": 5,
                "retry": {"max_attempts": 1, "backoff_sec": [1, 2]},
            },
            "dedupe": {"strip_params_blacklist": ["utm_*"]},
            "excel": {"workbook_path": str(tmp_path / "products.xlsx")},
        }
    )


def test_site_crawler_numbered_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    site = _site_config()
    config = _global_config(tmp_path)
    context = RuntimeContext(
        run_id="run-1",
        started_at=datetime.now(timezone.utc),
        config=config,
        sites=[site],
        dry_run=True,
    )
    html_page1 = """
    <div class="product">
      <a href="https://demo.example/p/1">1</a>
      <span class="old">1 500 ₽</span>
      <span class="new">1 200 ₽</span>
      <span class="rating">4.8</span>
    </div>
    <div class="product">
      <a href="https://demo.example/p/2?utm_source=test">2</a>
      <span class="old">2 000 ₽</span>
      <span class="rating">4,5</span>
      <span class="oos">Нет в наличии</span>
    </div>
    """
    html_page2 = """
    <div class="product">
      <a href="/p/3">3</a>
      <span class="new">950 ₽</span>
    </div>
    """
    responses = {
        "https://demo.example/catalog/": html_page1,
        "https://demo.example/catalog/?page=2": html_page2,
        "https://demo.example/catalog/?page=3": "<div></div>",
    }
    fake_engine = FakeEngine(responses)
    monkeypatch.setattr("app.crawler.site_crawler.create_engine", lambda *args, **kwargs: fake_engine)

    crawler = SiteCrawler(context, site)
    result = crawler.crawl()

    assert len(result.records) == 3
    assert result.records[0].product_url == "https://demo.example/p/1"
    assert result.records[0].current_price == 1500.0
    assert result.records[0].rating == 4.8
    assert result.records[0].in_stock is True
    assert result.records[1].product_url == "https://demo.example/p/2"
    assert result.records[1].current_price == 2000.0
    assert result.records[1].in_stock is False


def test_site_crawler_category_pages_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    site = _site_config()
    category_url = str(site.category_urls[0])
    site.category_pages = {category_url: 2}
    config = _global_config(tmp_path)
    context = RuntimeContext(
        run_id="run-1",
        started_at=datetime.now(timezone.utc),
        config=config,
        sites=[site],
        dry_run=True,
    )
    html = '<div class="product"><a href="https://demo.example/p/1">1</a></div>'
    responses = {
        "https://demo.example/catalog/": html,
        "https://demo.example/catalog/?page=2": html,
        "https://demo.example/catalog/?page=3": html,
    }
    fake_engine = FakeEngine(responses)
    monkeypatch.setattr("app.crawler.site_crawler.create_engine", lambda *args, **kwargs: fake_engine)

    crawler = SiteCrawler(context, site)
    result = crawler.crawl()

    assert len(result.records) == 1
    assert "https://demo.example/catalog/?page=3" not in fake_engine.calls
