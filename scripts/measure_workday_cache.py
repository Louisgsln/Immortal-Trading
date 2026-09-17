"""Measure two conditional reads of one existing job per enabled Workday source.

The default is an offline plan. --network explicitly enables at most eight detail
GETs plus robots reads, with no retries, searches, database writes or notifications.
"""

import argparse
import asyncio
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx

from trading_radar.config import Config, load_config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.http_cache import JSONCache
from trading_radar.models import utcnow
from trading_radar.workday import WorkdayCollector, external_path, workday_base


def select_targets(config: Config) -> list[dict[str, Any]]:
    """Read a stable SQLite snapshot without opening the writing Repository."""
    url = config.settings.database_url
    if not url.startswith("sqlite:///") or url in {"sqlite:///", "sqlite:///:memory:"}:
        raise ValueError("An existing SQLite file is required")
    path = Path(url.removeprefix("sqlite:///")).resolve()
    if not path.is_file():
        raise ValueError("Database does not exist")
    sources = [(s, c) for s, c in config.companies.items() if c.enabled and c.ats == "workday"]
    if len(sources) > 4:
        raise ValueError("Measurement is bounded to four configured Workday sources")
    targets: list[dict[str, Any]] = []
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        for source, company in sources:
            site, api = workday_base(company)
            row = db.execute(
                "SELECT id,payload FROM jobs WHERE is_active=1 "
                "AND json_extract(payload, '$.source')=? ORDER BY score DESC,id LIMIT 1",
                (source,),
            ).fetchone()
            if row is None:
                targets.append({"source": source, "status": "skipped", "reason": "no active job"})
                continue
            apply_url = json.loads(row[1]).get("apply_url")
            if not isinstance(apply_url, str) or not apply_url.startswith(site + "/job/"):
                raise ValueError(f"Stored job URL does not match configured source: {source}")
            detail_path = external_path(apply_url[len(site) :])
            targets.append(
                {
                    "source": source,
                    "status": "planned",
                    "job_id": row[0],
                    "path": detail_path,
                    "url": api + detail_path,
                }
            )
    return targets


async def measure(
    config: Config, targets: list[dict[str, Any]], *, transport=None
) -> dict[str, Any]:
    """Opt-in caller controls network; all requests still pass HTTPClient policy."""
    if len(targets) > 4 or len({t["source"] for t in targets}) != len(targets):
        raise ValueError("At most one job per source and four sources are allowed")
    source_reports: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "measured_at": utcnow().isoformat(),
        "mode": "network",
        "sources": source_reports,
    }
    cache = JSONCache()
    http = HTTPClient(
        timeout=min(config.settings.timeout, 20), retries=0, json_cache=cache, transport=transport
    )
    try:
        for target in targets:
            result: dict[str, Any] = {**target, "requests": [], "reads": [], "cache_reused": False}
            source_reports.append(result)
            if target["status"] == "skipped":
                continue
            source = target["source"]
            company = config.companies[source].model_copy(deep=True)
            company.options["conditional_details"] = True
            collector = WorkdayCollector(source, company, http)
            # Re-derive from validated configuration even when called programmatically.
            if target["url"] != collector.api + external_path(target["path"]):
                raise ValueError("Target is not the configured public Workday detail")

            async def observe(response: httpx.Response, result: dict[str, Any] = result) -> None:
                await response.aread()
                result["requests"].append(
                    {
                        "kind": "robots"
                        if response.request.url.path == "/robots.txt"
                        else "detail",
                        "status": response.status_code,
                        "decoded_body_bytes": len(response.content),
                        "downloaded_body_bytes": response.num_bytes_downloaded,
                        "etag": response.headers.get("etag"),
                        "last_modified": response.headers.get("last-modified"),
                        "cache_control": response.headers.get("cache-control"),
                        "vary": response.headers.get("vary"),
                        "set_cookie_present": "set-cookie" in response.headers,
                        "request_cookie_present": "cookie" in response.request.headers,
                        "if_none_match": response.request.headers.get("if-none-match"),
                        "if_modified_since": response.request.headers.get("if-modified-since"),
                    }
                )

            http.client.event_hooks["response"] = [observe]
            previous = None
            try:
                async with asyncio.timeout(90):
                    for number in (1, 2):
                        start = len(result["requests"])
                        job = await collector._detail(target["path"], {})
                        entry = cache.get(source, target["url"])
                        exchanges = result["requests"][start:]
                        reused = any(
                            r["kind"] == "detail" and r["status"] == 304 for r in exchanges
                        )
                        result["reads"].append(
                            {
                                "number": number,
                                "cache_stored": entry is not None,
                                "cache_reused": reused,
                                "same_job_as_first": None if previous is None else job == previous,
                            }
                        )
                        result["cache_reused"] |= reused
                        previous = job
                result["status"] = "ok"
            except (SourceUnavailable, ValueError, TimeoutError) as exc:
                result["status"] = "unavailable"
                result["reason"] = (
                    str(exc) if isinstance(exc, SourceUnavailable) else type(exc).__name__
                )
            result["request_count"] = http.counts[source]
    finally:
        await http.close()
    report["cache_reused_sources"] = sum(s["cache_reused"] for s in source_reports)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--network", action="store_true", help="Explicitly enable the bounded probe"
    )
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/discovery/lot23/workday-cache/report.json")
    )
    args = parser.parse_args(argv)
    # Evidence is restricted to the workspace's ignored discovery directory.
    destination = args.output.resolve()
    discovery = Path("data/discovery").resolve()
    if not destination.is_relative_to(discovery) or destination.suffix != ".json":
        raise ValueError("Output must be a JSON file inside data/discovery")
    config = load_config(args.config_dir)
    database_url = config.settings.database_url
    if database_url.startswith("sqlite:///"):
        database = Path(database_url.removeprefix("sqlite:///")).absolute()
        for base in (database, database.resolve()):
            for suffix in ("", "-wal", "-shm", "-journal", ".lock"):
                protected = Path(str(base) + suffix)
                if destination == protected.resolve() or (
                    destination.exists() and protected.exists() and destination.samefile(protected)
                ):
                    raise ValueError("Output must not overwrite the database or its sidecars")
    if destination.exists() and not destination.is_file():
        raise ValueError("Output must be a regular JSON file")
    targets = select_targets(config)
    report: dict[str, Any] = (
        asyncio.run(measure(config, targets))
        if args.network
        else {"mode": "offline-plan", "sources": targets}
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(args.network and any(s["status"] == "unavailable" for s in report["sources"]))


if __name__ == "__main__":
    raise SystemExit(main())
