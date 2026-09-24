"""Offline source freshness, using a read-only SQLite connection."""

import math
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_radar.collection_diagnostics import source_conflicts
from trading_radar.config import Config
from trading_radar.models import utcnow


def timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else None


def audit_sources(config: Config, max_age_hours: float = 24, now: datetime | None = None) -> dict:
    if not math.isfinite(max_age_hours) or not 0 < max_age_hours <= 87600:
        raise ValueError("max_age_hours must be positive and at most 87600")
    now = now or utcnow()
    if now.tzinfo is None:
        raise ValueError("Audit time must have a timezone")
    now = now.astimezone(UTC)
    cutoff = now - timedelta(hours=max_age_hours)
    url = config.settings.database_url
    if not url.startswith("sqlite:///") or url == "sqlite:///:memory:":
        raise ValueError("Audit requires a file-backed sqlite:/// database")
    path = Path(url.removeprefix("sqlite:///")).resolve()
    states = {}
    conflicts = {}
    observations: dict[str, dict[str, datetime | None]] = defaultdict(dict)
    if path.exists():
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN")
            states = {r["source"]: dict(r) for r in db.execute("SELECT * FROM companies")}
            conflicts = {
                key: source_conflicts(db, key, state.get("last_success"))
                for key, state in states.items()
            }
            for row in db.execute("SELECT source, job_id, last_seen FROM job_sources"):
                seen = timestamp(row["last_seen"])
                by_job = observations[row["source"]]
                previous = by_job.get(row["job_id"])
                by_job[row["job_id"]] = (
                    max(previous, seen) if previous and seen else previous or seen
                )
        finally:
            db.close()
    sources = []
    for key, co in config.companies.items():
        state = states.get(key, {})
        success, failure = (
            timestamp(state.get("last_success")),
            timestamp(state.get("last_failure")),
        )
        invalid = any(
            state.get(k) is not None and (parsed is None or parsed > now)
            for k, parsed in [("last_success", success), ("last_failure", failure)]
        )
        age = (now - success).total_seconds() / 3600 if success and success <= now else None
        status = (
            "disabled"
            if not co.enabled
            else "unknown"
            if invalid
            else "failed"
            if failure and (not success or failure >= success)
            else "never_scanned"
            if not success
            else "stale"
            if success < cutoff
            else "fresh"
        )
        dates = list(observations[key].values())
        fresh = sum(seen is not None and cutoff <= seen <= now for seen in dates)
        sources.append(
            {
                "source": key,
                "company": co.name,
                "connector": co.ats,
                "enabled": co.enabled,
                "status": status,
                "last_success": state.get("last_success"),
                "last_failure": state.get("last_failure"),
                "age_hours": round(age, 3) if age is not None else None,
                "configured_scan_interval_seconds": co.scan_interval,
                "average_scan_seconds": state.get("average_response_time"),
                "last_snapshot_jobs": state.get("last_count", 0),
                "stored_jobs": len(dates),
                "recently_seen_jobs": fresh,
                "not_recently_verified_jobs": len(dates) - fresh,
                **({"collection_conflicts": conflicts[key]} if conflicts.get(key) else {}),
                "search_terms": co.options.get(
                    "search_terms", ["trading"] if co.ats == "workday" else []
                ),
                **({"notes": co.notes} if not co.enabled else {}),
            }
        )
    return {
        "generated_at": now.isoformat(),
        "max_age_hours": max_age_hours,
        "database": "read_only" if path.exists() else "not_created",
        "summary": dict(Counter(s["status"] for s in sources)),
        "interpretation": "Freshness measures observations, not whether a job remains open. Configured intervals do not imply a running watcher.",
        "sources": sources,
        "unconfigured_sources": sorted(set(states) - set(config.companies)),
    }
