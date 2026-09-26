"""Independent source scheduling with shared request pacing and bounded workers."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime

from trading_radar.config import Config
from trading_radar.http import HTTPClient, RequestPacing
from trading_radar.http_cache import JSONCache
from trading_radar.models import ScanMetrics, utcnow
from trading_radar.notifications import Notifier
from trading_radar.runtime_status import WatcherPulse
from trading_radar.scanner import scan
from trading_radar.source_schedule import due_at, scan_lock
from trading_radar.storage import Repository


async def watch_sources(
    config: Config,
    repo: Repository,
    pulse: WatcherPulse,
    *,
    notifier: Notifier | None = None,
    json_cache: JSONCache | None = None,
    stop: asyncio.Event | None = None,
    tick: float = 5,
) -> AsyncIterator[ScanMetrics]:
    """A completed source frees its slot without waiting for the slowest source."""
    selected = {key: company for key, company in config.companies.items() if company.enabled}
    if not selected:
        return
    pacing = RequestPacing()
    cache = json_cache if json_cache is not None else JSONCache()
    running: dict[str, tuple[asyncio.Task[ScanMetrics], datetime]] = {}
    with scan_lock(repo) as lease:

        async def collect(key: str) -> ScanMetrics:
            # One session per attempt prevents campus/professional cookies from
            # changing another collector's anonymous search context.
            http = HTTPClient(
                config.settings.timeout, config.settings.retries, json_cache=cache, pacing=pacing
            )
            scoped = config.model_copy(update={"companies": {key: selected[key]}})
            try:
                return await scan(scoped, repo, http=http, notifier=notifier, _scan_lease=lease)
            finally:
                await http.close()

        try:
            while stop is None or not stop.is_set():
                pulse.check()
                finished = [key for key, (task, _) in running.items() if task.done()]
                results = []
                for key in finished:
                    task, _ = running.pop(key)
                    results.append(task.result())
                now = utcnow()
                waiting = sorted(
                    (due_at(company, repo.state(key)), key)
                    for key, company in selected.items()
                    if key not in running
                )
                for due, key in waiting:
                    if due > now or len(running) >= config.settings.concurrency:
                        break
                    running[key] = (asyncio.create_task(collect(key)), now)
                pulse.publish(
                    "scanning" if running else "waiting",
                    scan_started=min((started for _, started in running.values()), default=None),
                )
                for result in results:
                    yield result
                if running:
                    await asyncio.wait(
                        [task for task, _ in running.values()],
                        timeout=tick,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                else:
                    await asyncio.sleep(tick)
        finally:
            for task, _ in running.values():
                task.cancel()
            await asyncio.gather(*(task for task, _ in running.values()), return_exceptions=True)
