from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProductSnapshot:
    source_site: str
    category_url: str
    product_url: str
    page_num: int
    current_price: float | None = None
    rating: float | None = None
    in_stock: bool = False


@dataclass(slots=True)
class CategoryMetrics:
    site_name: str
    category_url: str
    total_found: int = 0
    total_parsed: int = 0
    total_failed: int = 0
    last_page: int | None = None


@dataclass(slots=True)
class SiteCrawlResult:
    site_name: str
    records: list[ProductSnapshot]
    metrics: list[CategoryMetrics]
