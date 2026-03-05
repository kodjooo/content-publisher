from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from app.config.loader import ConfigLoaderError, iter_site_configs, load_global_config
from app.crawler.service import CrawlService
from app.excel import ExcelUpdater
from app.logger import get_logger
from app.runtime import RuntimeContext

console = Console()
logger = get_logger(__name__)


@dataclass(slots=True)
class RunnerOptions:
    config_path: Path | None
    sites_dir: Path
    run_id: str | None = None
    dry_run: bool = False


class AgentRunner:
    """Высокоуровневый раннер, который координирует запуск агента."""

    def __init__(self) -> None:
        self.latest_results = []

    def run(self, options: RunnerOptions) -> None:
        load_dotenv()
        run_id = options.run_id or str(uuid.uuid4())
        logger.info(
            "Запуск агента",
            extra={
                "run_id": run_id,
                "config": str(options.config_path) if options.config_path else "env",
                "sites_dir": str(options.sites_dir),
            },
        )

        try:
            global_config = load_global_config(options.config_path)
            site_configs = list(iter_site_configs(options.sites_dir))
        except ConfigLoaderError as exc:
            console.print(f"[bold red]Ошибка конфигурации:[/bold red] {exc}")
            raise

        context = RuntimeContext(
            run_id=run_id,
            started_at=datetime.now(timezone.utc),
            config=global_config,
            sites=site_configs,
            dry_run=options.dry_run,
        )

        self._execute(context)

    def _execute(self, context: RuntimeContext) -> None:
        console.print(
            f"[yellow]Контекст подготовлен[/yellow]: сайтов={len(context.sites)}, "
            f"dry_run={context.dry_run}, excel={context.config.excel.workbook_path}"
        )

        crawler = CrawlService(context)
        self.latest_results = crawler.collect()
        total_records = sum(len(result.records) for result in self.latest_results)
        console.print(
            f"[green]Обход завершён[/green]: сайтов={len(self.latest_results)}, "
            f"товаров={total_records}"
        )

        if context.dry_run:
            console.print("[cyan]Dry-run: обновление Excel пропущено[/cyan]")
            return

        updater = ExcelUpdater(
            config=context.config.excel,
            strip_params=context.config.dedupe.strip_params_blacklist,
        )
        summary = updater.apply(self.latest_results)
        console.print(
            "[green]Excel обновлён[/green]: "
            f"processed={summary.processed}, "
            f"updated={summary.updated}, "
            f"skipped_not_found={summary.skipped_not_found}"
        )
