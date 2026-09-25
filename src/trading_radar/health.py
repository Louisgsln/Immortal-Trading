"""Local readiness inspection: one read-only SQLite snapshot, no migration or transport."""

import math
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_radar.audit import timestamp
from trading_radar.collection_diagnostics import (
    source_conflicts,
    source_listing_gaps,
    source_observation,
)
from trading_radar.config import Config
from trading_radar.models import utcnow
from trading_radar.storage import SCHEMA, SCHEMA_VERSION


def _schema(connection: sqlite3.Connection) -> list[tuple]:
    return connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()


def check_health(config: Config, max_age_hours: float = 24, now: datetime | None = None) -> dict:
    """Return readiness plus actionable warnings; never create a missing database."""
    if not math.isfinite(max_age_hours) or not 0 < max_age_hours <= 87600:
        raise ValueError("max_age_hours must be positive and at most 87600")
    now = now or utcnow()
    if now.tzinfo is None:
        raise ValueError("Health check time must have a timezone")
    now = now.astimezone(UTC)
    url = config.settings.database_url
    if not url.startswith("sqlite:///") or url in {"sqlite:///", "sqlite:///:memory:"}:
        raise ValueError("Health checks require a file-backed sqlite:/// database")
    path = Path(url.removeprefix("sqlite:///")).resolve()
    report: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "status": "healthy",
        "ready": True,
        "max_age_hours": max_age_hours,
        "database": {"status": "unchecked", "schema_version": None},
        "sources": [],
        "source_summary": {},
        "latest_scan": None,
        "alerts": {"unknown": 0, "sending": 0},
        "issues": [],
    }

    def issue(code: str, severity: str, source: str | None = None) -> None:
        report["issues"].append({"code": code, "severity": severity, "source": source})
        if severity == "critical":
            report["status"], report["ready"] = "critical", False
        elif report["status"] == "healthy":
            report["status"] = "degraded"

    if not path.is_file():
        report["database"]["status"] = "missing"
        issue("database_missing", "critical")
        return report
    try:
        with closing(
            sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
        ) as connection:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("BEGIN")
            if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                report["database"]["status"] = "corrupt"
                issue("database_integrity_failed", "critical")
                return report
            with closing(sqlite3.connect(":memory:")) as expected:
                expected.executescript(SCHEMA)
                matching_schema = _schema(connection) == _schema(expected)
            if not matching_schema:
                report["database"]["status"] = "incompatible"
                issue("database_schema_incompatible", "critical")
                return report
            version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            report["database"]["schema_version"] = version
            if version != SCHEMA_VERSION:
                report["database"]["status"] = "incompatible"
                issue("database_schema_incompatible", "critical")
                return report
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                report["database"]["status"] = "corrupt"
                issue("database_foreign_keys_failed", "critical")
                return report
            report["database"]["status"] = "ok"
            states = {
                row[0]: row[1:]
                for row in connection.execute(
                    "SELECT source,last_success,last_failure,consecutive_failures,last_count "
                    "FROM companies"
                )
            }
            conflicts = {
                key: source_conflicts(connection, key, state[0]) for key, state in states.items()
            }
            gaps = {
                key: source_listing_gaps(connection, key, state[0]) for key, state in states.items()
            }
            failure_messages = {
                key: source_observation(connection, key, state[1], "failed")
                for key, state in states.items()
            }
            latest = connection.execute(
                "SELECT created_at FROM scan_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            report["latest_scan"] = latest[0] if latest else None
            report["alerts"].update(
                dict(
                    connection.execute(
                        "SELECT status,COUNT(*) FROM alerts WHERE status IN ('unknown','sending') "
                        "GROUP BY status"
                    )
                )
            )
    except sqlite3.Error as exc:
        # Sanitized codes only: SQLite errors can include local paths or SQL contents.
        code = getattr(exc, "sqlite_errorcode", 0) or 0
        report["database"]["status"] = (
            "corrupt"
            if code & 0xFF in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}
            else "unreadable"
        )
        issue("database_" + report["database"]["status"], "critical")
        return report

    enabled = [(key, company) for key, company in config.companies.items() if company.enabled]
    if not enabled:
        issue("no_enabled_sources", "warning")
    for key, company in enabled:
        success_raw, failure_raw, failures, count = states.get(key, (None, None, 0, 0))
        success, failure = timestamp(success_raw), timestamp(failure_raw)
        invalid = any(
            raw is not None and (parsed is None or parsed > now)
            for raw, parsed in [(success_raw, success), (failure_raw, failure)]
        )
        age = (now - success).total_seconds() / 3600 if success and success <= now else None
        if invalid:
            status = "invalid_timestamp"
            issue("source_invalid_timestamp", "critical", key)
        elif (
            key == "nomura_campus"
            and failure
            and (success is None or failure >= success)
            and failure_messages.get(key)
            == "Nomura campus access restricted: CAPTCHA challenge; retry later"
        ):
            status = "access_restricted"
            issue("source_access_restricted", "warning", key)
        elif conflicts.get(key) and str(failure_messages.get(key, "")).startswith(
            "Collecte dégradée :"
        ):
            status = "collection_degraded"
        elif success is None:
            status = "never_scanned"
            issue("source_never_scanned", "critical", key)
        elif age is not None and age > max_age_hours:
            status = "stale"
            issue("source_stale", "critical", key)
        elif failure and failure >= success:
            status = "recent_failure"
            issue("source_recent_failure", "warning", key)
        elif gaps.get(key):
            status = "partial"
            issue("source_incomplete_listings", "warning", key)
        else:
            status = "fresh"
        report["sources"].append(
            {
                "source": key,
                "company": company.name,
                "status": status,
                "last_success": success_raw,
                "last_failure": failure_raw,
                "age_hours": round(age, 3) if age is not None else None,
                "consecutive_failures": failures,
                "last_snapshot_jobs": count,
                **({"collection_conflicts": conflicts[key]} if conflicts.get(key) else {}),
                **({"listing_gaps": gaps[key]} if gaps.get(key) else {}),
            }
        )
        if conflicts.get(key):
            issue("source_collection_conflicts", "warning", key)
    report["source_summary"] = dict(Counter(source["status"] for source in report["sources"]))
    if report["latest_scan"] is not None:
        scan_time = timestamp(report["latest_scan"])
        if scan_time is None or scan_time > now:
            issue("scan_invalid_timestamp", "warning")
    if any(report["alerts"].values()):
        issue("alerts_need_review", "warning")
    return report
