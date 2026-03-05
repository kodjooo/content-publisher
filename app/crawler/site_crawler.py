from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, Tag

from app.config.models import DelayConfig, SelectorValue, SiteConfig
from app.crawler.behavior import BehaviorContext
from app.crawler.engines import EngineRequest, create_engine
from app.crawler.models import CategoryMetrics, ProductSnapshot, SiteCrawlResult
from app.crawler.utils import jitter_sleep, normalize_url
from app.logger import get_logger
from app.runtime import RuntimeContext

logger = get_logger(__name__)

_PRICE_NUMBER_PATTERN = re.compile(r"\d[\d\s.,]*")
_RATING_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")
_OUT_OF_STOCK_PATTERNS = (
    "нет в наличии",
    "распродан",
    "out of stock",
    "нет товара",
)


@dataclass(slots=True)
class CategoryResult:
    records: list[ProductSnapshot]
    metrics: CategoryMetrics


class SiteCrawler:
    """Обходит категории сайта и собирает витринные параметры товара."""

    _EMPTY_CATEGORY_RETRY_DELAYS = (60, 600, 1200, 3600)
    _MAX_EMPTY_PAGES_STREAK = 3

    def __init__(self, context: RuntimeContext, site: SiteConfig):
        self.context = context
        self.site = site
        self._behavior_config = self._prepare_behavior_config(context.config.runtime.behavior)
        self.engine = create_engine(site.engine, context.config.network, self._behavior_config)
        self.dedupe_strip = context.config.dedupe.strip_params_blacklist
        self._seen_urls: set[str] = set()
        self._page_delay: DelayConfig = context.config.runtime.page_delay
        self._fail_cooldown_threshold = context.config.runtime.fail_cooldown_threshold
        self._fail_cooldown_seconds = context.config.runtime.fail_cooldown_seconds
        self._category_fail_streak = 0
        self._fetch_attempt_fail_streak = 0
        self._cooldown_active = False

    def crawl(self) -> SiteCrawlResult:
        logger.info("Старт обхода сайта", extra={"site": self.site.name})
        records: list[ProductSnapshot] = []
        metrics: list[CategoryMetrics] = []
        try:
            for category_url in self.site.category_urls:
                if self._cooldown_active:
                    logger.warning(
                        "Останавливаем обход из-за активного cooldown",
                        extra={"site": self.site.name},
                    )
                    break
                category_result = self._crawl_category(str(category_url))
                records.extend(category_result.records)
                metrics.append(category_result.metrics)
                if self._global_stop_reached():
                    break
        finally:
            self.engine.shutdown()
        return SiteCrawlResult(site_name=self.site.name, records=records, metrics=metrics)

    def _crawl_category(self, category_url: str) -> CategoryResult:
        pagination_mode = self.site.pagination.mode
        if pagination_mode == "numbered_pages":
            return self._crawl_numbered_pages(category_url)
        if pagination_mode == "next_button":
            return self._crawl_next_button(category_url)
        return self._crawl_infinite_scroll(category_url)

    def _crawl_numbered_pages(self, category_url: str) -> CategoryResult:
        pagination = self.site.pagination
        start_page = max(1, pagination.start_page or 1)
        max_pages_limit = self.site.limits.max_pages or pagination.max_pages or 100
        if pagination.end_page is not None:
            max_pages = min(max_pages_limit, pagination.end_page)
        else:
            max_pages = max_pages_limit
        category_pages = self.site.category_pages.get(category_url)
        if category_pages is not None:
            max_pages = min(max_pages, category_pages)

        metrics = CategoryMetrics(site_name=self.site.name, category_url=category_url)
        records: list[ProductSnapshot] = []
        page = start_page
        empty_pages_streak = 0
        while page <= max_pages and not self._global_stop_reached():
            if self._cooldown_active:
                break
            url = self._build_page_url(category_url, page)
            try:
                html = self._fetch_page_html(url)
            except Exception as exc:
                self._handle_category_page_exception(category_url, page, metrics, exc)
                page += 1
                continue

            page_records, has_data, limit_hit = self._parse_page_html(html, category_url, page, metrics)
            records.extend(page_records)
            should_retry = not has_data and metrics.total_parsed == 0 and page == start_page
            if should_retry:
                retry = self._retry_empty_category_page(page, category_url, metrics)
                if retry:
                    retry_records, has_data, limit_hit = retry
                    records.extend(retry_records)
            if has_data:
                empty_pages_streak = 0
                metrics.last_page = page
            else:
                empty_pages_streak += 1
                if empty_pages_streak >= self._MAX_EMPTY_PAGES_STREAK:
                    logger.info(
                        "Достигнут лимит пустых страниц подряд, прерываем обход категории",
                        extra={"site": self.site.name, "category_url": category_url, "page": page},
                    )
                    break
            if limit_hit or self._should_stop(metrics):
                break
            page += 1
        return CategoryResult(records=records, metrics=metrics)

    def _crawl_next_button(self, category_url: str) -> CategoryResult:
        next_url = category_url
        metrics = CategoryMetrics(site_name=self.site.name, category_url=category_url)
        records: list[ProductSnapshot] = []
        max_pages = self.site.limits.max_pages or self.site.pagination.max_pages or 100
        page = 1
        empty_pages_streak = 0

        while next_url and page <= max_pages and not self._global_stop_reached():
            if self._cooldown_active:
                break
            try:
                html = self._fetch_page_html(next_url)
            except Exception as exc:
                self._handle_category_page_exception(category_url, page, metrics, exc)
                break

            page_records, has_data, limit_hit = self._parse_page_html(html, category_url, page, metrics)
            records.extend(page_records)
            should_retry = not has_data and metrics.total_parsed == 0 and page == 1
            if should_retry:
                retry = self._retry_empty_category_page(page, category_url, metrics)
                if retry:
                    retry_records, has_data, limit_hit = retry
                    records.extend(retry_records)

            if has_data:
                empty_pages_streak = 0
                metrics.last_page = page
            else:
                empty_pages_streak += 1
                if empty_pages_streak >= self._MAX_EMPTY_PAGES_STREAK:
                    break

            if limit_hit or self._should_stop(metrics):
                break

            soup = BeautifulSoup(html, "lxml")
            next_url = self._extract_next_link(soup, current_url=next_url)
            page += 1

        return CategoryResult(records=records, metrics=metrics)

    def _crawl_infinite_scroll(self, category_url: str) -> CategoryResult:
        scroll_limit = self.site.limits.max_scrolls
        metrics = CategoryMetrics(site_name=self.site.name, category_url=category_url)
        if self._cooldown_active:
            return CategoryResult(records=[], metrics=metrics)
        try:
            html = self._fetch_page_html(category_url, scroll_limit=scroll_limit)
        except Exception as exc:
            self._handle_category_page_exception(category_url, 1, metrics, exc)
            return CategoryResult(records=[], metrics=metrics)

        records, has_data, limit_hit = self._parse_page_html(html, category_url, 1, metrics)
        if not has_data and metrics.total_parsed == 0:
            retry = self._retry_empty_category_page(1, category_url, metrics)
            if retry:
                retry_records, has_data, limit_hit = retry
                records.extend(retry_records)
        if has_data:
            metrics.last_page = 1
        if limit_hit:
            metrics.last_page = 1
        return CategoryResult(records=records, metrics=metrics)

    def _fetch_page_html(self, url: str, scroll_limit: int | None = None) -> str:
        if self._cooldown_active:
            raise RuntimeError("Cooldown активен, прекращаем обработку")
        request = EngineRequest(
            url=url,
            wait_conditions=self.site.wait_conditions,
            pagination=self.site.pagination,
            scroll_limit=scroll_limit,
            behavior_context=self._build_behavior_context(category_url=url),
            on_timeout=self._register_fetch_attempt_failure,
        )
        try:
            html = self.engine.fetch_html(request)
            self._register_category_fetch_success()
            self._register_fetch_attempt_success()
        except Exception:
            self._register_category_fetch_failure()
            raise

        retries = 0
        while not self._wait_conditions_met(html) and retries < 2:
            try:
                html = self.engine.fetch_html(request)
                self._register_category_fetch_success()
                self._register_fetch_attempt_success()
            except Exception:
                self._register_category_fetch_failure()
                raise
            retries += 1
        self._sleep_between_pages()
        return html

    def _wait_conditions_met(self, html: str) -> bool:
        soup = BeautifulSoup(html, "lxml")
        for condition in self.site.wait_conditions:
            if condition.type == "selector" and not soup.select(condition.value):
                return False
        return True

    def _prepare_behavior_config(self, base_behavior):
        behavior = base_behavior.model_copy()
        hover_targets = self.site.selectors.hover_targets
        if hover_targets:
            mouse_cfg = behavior.mouse.model_copy(update={"hover_selectors": hover_targets})
            behavior = behavior.model_copy(update={"mouse": mouse_cfg})
        return behavior

    def _build_behavior_context(self, category_url: str) -> BehaviorContext | None:
        behavior = self.context.config.runtime.behavior
        if not behavior.enabled:
            return None
        root_url = self.site.base_url
        if not root_url:
            parsed = urlparse(category_url)
            root_url = f"{parsed.scheme}://{parsed.netloc}"
        return BehaviorContext(
            product_link_selector=self.site.selectors.product_link_selector,
            category_url=category_url,
            base_url=self.site.base_url or category_url,
            root_url=root_url,
            scroll_min_percent=self.site.pagination.scroll_min_percent,
            scroll_max_percent=self.site.pagination.scroll_max_percent,
        )

    def _parse_page_html(
        self,
        html: str,
        category_url: str,
        page_num: int,
        metrics: CategoryMetrics,
    ) -> tuple[list[ProductSnapshot], bool, bool]:
        soup = BeautifulSoup(html, "lxml")
        if self._should_stop_on_missing_selector(soup):
            return [], False, False

        cards = soup.select(self.site.selectors.product_card_selector)
        metrics.total_found += len(cards)
        if not cards:
            return [], False, False

        records: list[ProductSnapshot] = []
        limit_hit = False
        for card in cards:
            link_node = card.select_one(self.site.selectors.product_link_selector)
            if not link_node or not link_node.get("href"):
                continue
            normalized_url, _ = normalize_url(
                link_node.get("href"),
                self.site.base_url,
                self.dedupe_strip,
            )
            if normalized_url in self._seen_urls:
                continue
            if self.site.selectors.allowed_domains:
                domain = urlparse(normalized_url).netloc
                if domain not in self.site.selectors.allowed_domains:
                    continue

            try:
                price_without_discount = self._extract_price(card, self.site.selectors.price_without_discount_selector)
                price_with_discount = self._extract_price(card, self.site.selectors.price_with_discount_selector)
                current_price = self._select_current_price(price_without_discount, price_with_discount)
                rating = self._extract_rating(card)
                in_stock = self._extract_in_stock(card)
            except Exception:
                metrics.total_failed += 1
                continue

            snapshot = ProductSnapshot(
                source_site=self.site.domain,
                category_url=category_url,
                product_url=normalized_url,
                page_num=page_num,
                current_price=current_price,
                rating=rating,
                in_stock=in_stock,
            )
            records.append(snapshot)
            self._seen_urls.add(normalized_url)
            metrics.total_parsed += 1
            if self.context.register_product() or self._reached_product_limit(metrics):
                limit_hit = True
                break

        return records, bool(records), limit_hit

    def _retry_empty_category_page(
        self,
        page_num: int,
        category_url: str,
        metrics: CategoryMetrics,
    ) -> tuple[list[ProductSnapshot], bool, bool] | None:
        page_url = self._build_page_url(category_url, page_num)
        for delay in self._EMPTY_CATEGORY_RETRY_DELAYS:
            if self._global_stop_reached():
                break
            self._mark_last_proxy_for_retry()
            logger.warning(
                "Категория вернула 0 карточек, повтор с другим прокси",
                extra={
                    "site": self.site.name,
                    "category_url": category_url,
                    "page": page_num,
                    "retry_delay_sec": delay,
                },
            )
            self._wait_before_retry(delay)
            try:
                html = self._fetch_page_html(page_url)
            except Exception:
                continue
            records, has_data, limit_hit = self._parse_page_html(html, category_url, page_num, metrics)
            if has_data:
                return records, has_data, limit_hit
        return None

    def _wait_before_retry(self, delay_sec: int) -> None:
        logger.info(
            "Ожидание перед повторной загрузкой категории",
            extra={
                "site": self.site.name,
                "delay_sec": delay_sec,
                "delay_min": round(delay_sec / 60, 2),
            },
        )
        time.sleep(delay_sec)

    def _extract_price(self, card: Tag, selector: SelectorValue) -> float | None:
        text = self._extract_text_by_selector(card, selector)
        return self._parse_price_value(text)

    def _extract_text_by_selector(self, card: Tag, selector: SelectorValue) -> str | None:
        if not selector:
            return None
        selectors = [selector] if isinstance(selector, str) else [item for item in selector if item]
        for css in selectors:
            node = card.select_one(css)
            if node:
                text = node.get_text(" ", strip=True)
                if text:
                    return text
        return None

    def _parse_price_value(self, text: str | None) -> float | None:
        if not text:
            return None
        match = _PRICE_NUMBER_PATTERN.search(text.replace("\xa0", " "))
        if not match:
            return None
        raw = match.group(0)
        cleaned = raw.replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _select_current_price(
        self,
        price_without_discount: float | None,
        price_with_discount: float | None,
    ) -> float | None:
        values = [value for value in [price_without_discount, price_with_discount] if value is not None]
        if not values:
            return None
        return max(values)

    def _extract_rating(self, card: Tag) -> float | None:
        text = self._extract_text_by_selector(card, self.site.selectors.rating_selector)
        if not text:
            return None
        match = _RATING_PATTERN.search(text.replace("\xa0", " "))
        if not match:
            return None
        raw = match.group(0).replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None

    def _extract_in_stock(self, card: Tag) -> bool:
        if self.site.selectors.out_of_stock_selector and card.select_one(
            self.site.selectors.out_of_stock_selector
        ):
            return False
        if self.site.selectors.in_stock_selector:
            return bool(card.select_one(self.site.selectors.in_stock_selector))
        text = card.get_text(" ", strip=True).lower()
        return not any(pattern in text for pattern in _OUT_OF_STOCK_PATTERNS)

    def _handle_category_page_exception(
        self,
        category_url: str,
        page_num: int,
        metrics: CategoryMetrics,
        exc: Exception,
    ) -> None:
        metrics.total_failed += 1
        logger.error(
            "Не удалось загрузить страницу категории, переходим к следующей",
            extra={
                "site": self.site.name,
                "category_url": category_url,
                "page": page_num,
                "error": str(exc),
            },
            exc_info=True,
        )
        self._mark_last_proxy_for_retry()

    def _mark_last_proxy_for_retry(self) -> None:
        marker = getattr(self.engine, "mark_last_proxy_bad", None)
        if not callable(marker):
            return
        try:
            marker(reason="empty_category_page")
        except Exception:
            logger.debug(
                "Не удалось пометить последний прокси перед повторной попыткой",
                extra={"site": self.site.name},
                exc_info=True,
            )

    def _should_stop_on_missing_selector(self, soup: BeautifulSoup) -> bool:
        for condition in self.site.stop_conditions:
            if condition.type == "missing_selector" and condition.value and not soup.select(condition.value):
                return True
        return False

    def _sleep_between_pages(self) -> None:
        if self._page_delay.max_sec <= 0:
            return
        jitter_sleep(self._page_delay.min_sec, self._page_delay.max_sec)

    def _extract_next_link(self, soup: BeautifulSoup, current_url: str) -> str | None:
        selector = self.site.pagination.next_button_selector
        if not selector:
            return None
        node = soup.select_one(selector)
        if node and node.get("href"):
            base = self.site.base_url or current_url
            return urljoin(base, node["href"])
        return None

    def _build_page_url(self, category_url: str, page_num: int) -> str:
        param = self.site.pagination.param_name or "page"
        if page_num <= 1:
            return category_url
        parsed = urlparse(category_url)
        query = dict(parse_qsl(parsed.query)) if parsed.query else {}
        query[param] = str(page_num)
        new_query = urlencode(query)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))

    def _reached_product_limit(self, metrics: CategoryMetrics) -> bool:
        max_products = self.site.limits.max_products
        if max_products and metrics.total_parsed >= max_products:
            return True
        return False

    def _should_stop(self, metrics: CategoryMetrics) -> bool:
        for condition in self.site.stop_conditions:
            if condition.type == "no_new_products" and metrics.total_parsed == 0:
                return True
        return False

    def _global_stop_reached(self) -> bool:
        return self.context.product_limit_reached()

    def _register_category_fetch_success(self) -> None:
        if self._category_fail_streak:
            self._category_fail_streak = 0

    def _register_category_fetch_failure(self) -> None:
        self._category_fail_streak += 1
        self._try_cooldown("category", self._category_fail_streak)

    def _register_fetch_attempt_failure(self) -> None:
        self._fetch_attempt_fail_streak += 1
        self._try_cooldown("attempt", self._fetch_attempt_fail_streak)

    def _register_fetch_attempt_success(self) -> None:
        if self._fetch_attempt_fail_streak:
            self._fetch_attempt_fail_streak = 0

    def _try_cooldown(self, target: str, streak: int) -> None:
        if self._fail_cooldown_threshold <= 0:
            return
        if streak < self._fail_cooldown_threshold:
            return
        message = {
            "category": "Достигнут предел подряд неудачных загрузок категорий, временно приостанавливаем обход",
            "attempt": "Достигнут предел подряд неудачных попыток загрузки страниц, временно приостанавливаем обход",
        }.get(target, "Достигнут предел подряд неудачных загрузок, временно приостанавливаем обход")
        logger.warning(
            message,
            extra={
                "site": self.site.name,
                "target": target,
                "streak": streak,
                "threshold": self._fail_cooldown_threshold,
                "cooldown_sec": self._fail_cooldown_seconds,
            },
        )
        self._cooldown_active = True
        if target == "category":
            self._category_fail_streak = 0
            self._fetch_attempt_fail_streak = 0
        elif target == "attempt":
            self._fetch_attempt_fail_streak = 0


def format_price_for_excel(value: float | None) -> float | int | None:
    if value is None:
        return None
    if value.is_integer():
        return int(value)
    return round(value, 2)
