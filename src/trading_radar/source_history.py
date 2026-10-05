"""Bounded source observations; old aggregate scans cannot identify successes."""

import json
import math
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_radar.audit import timestamp
from trading_radar.config import Config
from trading_radar.models import SelectionSummary
from trading_radar.source_failure import failure_summary

MAX_ROWS = 10000
MAX_LENGTH = 1000000
STATUSES = {"successful", "failed", "partial", "degraded"}


def source_history(config: Config, now: datetime) -> dict:
    """Count only attributed attempts in the previous 24 hours, without DB writes.

    An incomplete/invalid read returns no ratios. Legacy aggregate records are
    explicitly omitted rather than attributing successes to an inferred source.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("History cutoff requires a timezone")
    now = now.astimezone(UTC)
    cutoff = now - timedelta(hours=24)
    result: dict = {"status": "ok", "hours": 24, "legacy_scans": 0, "sources": {}}
    url = config.settings.database_url
    if not url.startswith("sqlite:///") or url in {"sqlite:///", "sqlite:///:memory:"}:
        return {**result, "status": "unavailable"}
    try:
        path = Path(url.removeprefix("sqlite:///")).resolve()
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            rows = db.execute(
                "SELECT created_at,length(metrics),substr(metrics,1,?) FROM scan_runs "
                "WHERE julianday(created_at) BETWEEN julianday(?) AND julianday(?) "
                "ORDER BY id DESC LIMIT ?",
                (MAX_LENGTH + 1, cutoff.isoformat(), now.isoformat(), MAX_ROWS + 1),
            ).fetchall()
        if len(rows) > MAX_ROWS:
            # Never present a bounded prefix as a full 24-hour observation.
            raise ValueError("history limit")
        for created, size, raw in rows:
            observed = timestamp(created)
            if observed is None:
                raise ValueError("invalid scan timestamp")
            if observed < cutoff or observed > now:
                continue
            if size > MAX_LENGTH:
                raise ValueError("metrics limit")
            metrics = json.loads(raw)
            if not isinstance(metrics, dict):
                raise ValueError("invalid metrics")
            records = metrics.get("source_results")
            if records is None or records == {} and metrics.get("sources", 0):
                result["legacy_scans"] += 1
                continue
            if (
                not isinstance(records, dict)
                or type(metrics.get("sources")) is not int
                or len(records) != metrics.get("sources")
            ):
                raise ValueError("invalid source results")
            for key, record in records.items():
                if not isinstance(record, dict):
                    raise ValueError("invalid result")
                ended = timestamp(record.get("completed_at"))
                status, duration = record.get("status"), record.get("duration")
                if (
                    ended is None
                    or ended > observed
                    or status not in STATUSES
                    or type(duration) not in (int, float)
                    or not isinstance(duration, (int, float))
                    or not math.isfinite(duration)
                    or duration < 0
                ):
                    raise ValueError("invalid observation")
                if key not in config.companies or not cutoff <= ended <= now:
                    continue
                entry = result["sources"].setdefault(
                    key,
                    {
                        "counts": Counter(),
                        "durations": [],
                        "since": ended.isoformat(),
                        "latest": [],
                    },
                )
                entry["counts"][status] += 1
                entry["durations"].append(duration)
                entry["since"] = min(entry["since"], ended.isoformat())
                failures = metrics.get("failed", {})
                cause = (
                    failure_summary(failures.get(key)) if status in {"failed", "degraded"} else None
                )
                entry["latest"].append(
                    {"at": ended.isoformat(), "status": status, "failure": cause}
                )
                if status != "failed" and record.get("selection") is not None:
                    entry["latest"][-1]["selection"] = SelectionSummary.model_validate(
                        record["selection"]
                    ).model_dump(mode="json")
        for entry in result["sources"].values():
            durations = entry.pop("durations")
            entry["attempts"] = len(durations)
            entry["success_rate"] = round(100 * entry["counts"]["successful"] / len(durations), 1)
            entry["average_seconds"] = round(sum(durations) / len(durations), 1)
            entry["latest"] = sorted(entry["latest"], key=lambda r: r["at"], reverse=True)[:5]
        return result
    except (OSError, sqlite3.Error, ValueError, TypeError, AttributeError, OverflowError):
        return {"status": "unavailable", "hours": 24, "legacy_scans": 0, "sources": {}}
