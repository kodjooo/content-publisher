from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.config.loader import ConfigLoaderError, iter_site_configs, load_global_config


def _base_global_payload() -> dict:
    return {
        "runtime": {"max_concurrency_per_site": 2, "global_stop": {}},
        "network": {
            "user_agents": ["agent-1"],
            "proxy_pool": [],
            "request_timeout_sec": 10,
            "retry": {"max_attempts": 3, "backoff_sec": [1, 2, 3]},
        },
        "dedupe": {"strip_params_blacklist": ["utm_*"]},
        "excel": {
            "workbook_path": "/tmp/products.xlsx",
            "sheet_name": "Sheet1",
            "header_row": 1,
        },
    }


def _site_payload(name: str) -> dict:
    return {
        "site": {
            "name": name,
            "domain": f"{name}.example.com",
            "engine": "http",
        },
        "selectors": {
            "product_card_selector": ".product-card",
            "product_link_selector": "a.product-link",
        },
        "pagination": {"mode": "numbered_pages", "param_name": "page", "max_pages": 3},
        "limits": {"max_products": 10},
        "category_urls": ["https://example.com/catalog/"],
    }


def test_load_global_config_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "global.yml"
    config_path.write_text(yaml.safe_dump(_base_global_payload()), encoding="utf-8")

    config = load_global_config(config_path)
    assert config.excel.sheet_name == "Sheet1"
    assert config.network.user_agents == ["agent-1"]


def test_load_global_config_json(tmp_path: Path) -> None:
    config_path = tmp_path / "global.json"
    config_path.write_text(json.dumps(_base_global_payload()), encoding="utf-8")

    config = load_global_config(config_path)
    assert config.runtime.max_concurrency_per_site == 2


def test_load_global_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUNTIME_MAX_CONCURRENCY_PER_SITE", "3")
    monkeypatch.setenv("NETWORK_USER_AGENTS", "env-agent-1,env-agent-2")
    monkeypatch.setenv("NETWORK_REQUEST_TIMEOUT_SEC", "42")
    monkeypatch.setenv("NETWORK_RETRY_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("NETWORK_RETRY_BACKOFF_SEC", "1,2,3")
    monkeypatch.setenv("NETWORK_PROXY_ALLOW_DIRECT", "true")
    monkeypatch.setenv("NETWORK_BROWSER_STORAGE_STATE_PATH", "/tmp/auth.json")
    monkeypatch.setenv("NETWORK_BROWSER_HEADLESS", "false")
    monkeypatch.setenv("NETWORK_BROWSER_PREVIEW_DELAY_SEC", "3.5")
    monkeypatch.setenv("NETWORK_BROWSER_PREVIEW_BEFORE_BEHAVIOR_SEC", "2")
    monkeypatch.setenv("NETWORK_BROWSER_EXTRA_PAGE_PREVIEW_SEC", "1.5")
    monkeypatch.setenv("NETWORK_BROWSER_SLOW_MO_MS", "750")
    monkeypatch.setenv("NETWORK_ACCEPT_LANGUAGE", "ru-RU")
    monkeypatch.setenv("BEHAVIOR_ENABLED", "true")
    monkeypatch.setenv("BEHAVIOR_MOUSE_MOVE_MIN", "2")
    monkeypatch.setenv("BEHAVIOR_MOUSE_MOVE_MAX", "4")
    monkeypatch.setenv("BEHAVIOR_NAV_EXTRA_PRODUCTS_LIMIT", "1")
    monkeypatch.setenv("EXCEL_FILE_PATH", "/tmp/products.xlsx")
    monkeypatch.setenv("EXCEL_SHEET_NAME", "Products")
    monkeypatch.setenv("EXCEL_URL_COLUMN_CANDIDATES", "product_url,ссылка")

    config = load_global_config(None)
    assert config.runtime.max_concurrency_per_site == 3
    assert config.network.retry.max_attempts == 4
    assert str(config.network.browser_storage_state_path) == "/tmp/auth.json"
    assert config.network.accept_language == "ru-RU"
    assert config.network.browser_headless is False
    assert config.network.proxy_allow_direct is True
    assert config.network.browser_preview_delay_sec == 3.5
    assert config.network.browser_preview_before_behavior_sec == 2.0
    assert config.network.browser_extra_page_preview_sec == 1.5
    assert config.network.browser_slow_mo_ms == 750
    assert config.runtime.behavior.enabled is True
    assert config.runtime.behavior.mouse.move_count_min == 2
    assert config.runtime.behavior.navigation.extra_products_limit == 1
    assert str(config.excel.workbook_path) == "/tmp/products.xlsx"
    assert config.excel.sheet_name == "Products"
    assert config.excel.url_column_candidates == ["product_url", "ссылка"]


def test_iter_site_configs_supports_multiple_files(tmp_path: Path) -> None:
    (tmp_path / "first.yml").write_text(
        yaml.safe_dump(_site_payload("first")), encoding="utf-8"
    )
    (tmp_path / "second.json").write_text(
        json.dumps(_site_payload("second")), encoding="utf-8"
    )

    sites = list(iter_site_configs(tmp_path))
    assert {site.name for site in sites} == {"first", "second"}


def test_invalid_site_config_raises(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yml"
    broken.write_text(yaml.safe_dump({"site": {"name": "broken"}}), encoding="utf-8")

    with pytest.raises(ConfigLoaderError):
        list(iter_site_configs(tmp_path))
