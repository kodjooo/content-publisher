from __future__ import annotations

from app.crawler.models import SiteCrawlResult
from app.crawler.site_crawler import SiteCrawler
from app.logger import get_logger
from app.runtime import RuntimeContext

logger = get_logger(__name__)


class CrawlService:
    """Оркестровка обхода всех сайтов."""

    def __init__(self, context: RuntimeContext):
        self.context = context

    def collect(self) -> list[SiteCrawlResult]:
        results: list[SiteCrawlResult] = []
        for site in self.context.sites:
            if self.context.product_limit_reached():
                logger.info(
                    "Достигнут глобальный лимит по товарам, дальнейший обход остановлен",
                    extra={"limit": self.context.config.runtime.global_stop.stop_after_products},
                )
                break
            crawler = SiteCrawler(self.context, site)
            result = crawler.crawl()
            logger.info(
                "Завершён обход сайта",
                extra={"site": site.name, "records": len(result.records)},
            )
            results.append(result)
            if self.context.product_limit_reached():
                break
        return results
