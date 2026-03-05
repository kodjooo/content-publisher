from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.config.models import GlobalConfig, SiteConfig


@dataclass(slots=True)
class RuntimeContext:
    """Общий контекст выполнения для всего запуска."""

    run_id: str
    started_at: datetime
    config: GlobalConfig
    sites: list[SiteConfig]
    dry_run: bool = False
    products_seen: int = 0

    def iter_sites(self) -> Iterable[SiteConfig]:
        return iter(self.sites)

    def register_product(self) -> bool:
        self.products_seen += 1
        limit = self.config.runtime.global_stop.stop_after_products
        return bool(limit and self.products_seen >= limit)

    def product_limit_reached(self) -> bool:
        limit = self.config.runtime.global_stop.stop_after_products
        return bool(limit and self.products_seen >= limit)
