"""Read internship rollout evidence without collecting or changing alert state."""

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from trading_radar.config import Config
from trading_radar.internship_baseline import observed_baselines


def internship_coverage(config: Config, now: datetime) -> dict:
    enabled = {key: company for key, company in config.companies.items() if company.enabled}
    cutoff = config.settings.internship_baseline_at
    result: dict = {
        "status": "ok" if config.settings.include_internships else "disabled",
        "baseline_at": cutoff.isoformat() if cutoff else None,
        "enabled_sources": len(enabled),
        "validated_sources": 0,
        "sources": {},
    }
    if not config.settings.include_internships:
        return result
    if cutoff is None:
        # The scanner accepts an explicitly prevalidated deployment in this mode.
        # Do not invent an observed baseline date or a completed source inventory.
        result["sources"] = {
            key: {"status": "prevalidated", "validated_at": None} for key in enabled
        }
        return result
    url = config.settings.database_url
    try:
        if not url.startswith("sqlite:///") or url in {"sqlite:///", "sqlite:///:memory:"}:
            raise ValueError("File-backed database required")
        path = Path(url.removeprefix("sqlite:///")).resolve()
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            observed = observed_baselines(db, set(enabled), cutoff, now)
        result["sources"] = {
            key: {"status": "validated", "validated_at": observed[key]}
            if key in observed
            else {"status": "pending", "validated_at": None}
            for key in enabled
        }
        result["validated_sources"] = len(observed)
    except (OSError, ValueError, TypeError, sqlite3.Error, RecursionError):
        result["status"] = "unavailable"
    return result
