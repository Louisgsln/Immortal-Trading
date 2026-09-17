"""Daily local activity from one bounded, read-only SQLite observation."""

import json
import math
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trading_radar.config import Config
from trading_radar.models import utcnow
from trading_radar.storage import SCHEMA, SCHEMA_VERSION

MAX_ROWS = 100_000
MAX_METRICS_LENGTH = 1_000_000
COUNTERS = ("new_jobs", "updates", "rescored", "closed", "reopened", "scans", "failed_sources")
EVENTS = {"updated": "updates", "rescored": "rescored", "closed": "closed", "reopened": "reopened"}
MESSAGES = {
    "missing": "La base locale est absente. Effectuez une collecte pour disposer d’un historique.",
    "incompatible": "Le schéma de la base est incompatible avec cette version des statistiques.",
    "corrupt": "La base a échoué au contrôle d’intégrité. Vérifiez une sauvegarde.",
    "unreadable": "L’historique local ne peut pas être lu pour le moment.",
    "invalid_data": "L’historique contient une date, un événement ou des métriques incohérents.",
    "limit_exceeded": "L’historique dépasse une limite de lecture. Aucun résultat partiel n’est affiché.",
    "invalid_config": "Les statistiques nécessitent une base SQLite locale sur disque.",
}


class TrendsError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(MESSAGES[code])


def _schema(db: sqlite3.Connection) -> list[tuple]:
    return list(
        db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        )
    )


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise TrendsError("invalid_data")
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise TrendsError("invalid_data")
    return instant.astimezone(UTC)


def _object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise TrendsError("invalid_data")
        result[key] = value
    return result


def _failed_sources(raw: str) -> int:
    if not isinstance(raw, str):
        raise TrendsError("invalid_data")

    def reject_constant(value: str) -> None:
        raise TrendsError("invalid_data")

    metrics = json.loads(raw, object_pairs_hook=_object, parse_constant=reject_constant)
    if not isinstance(metrics, dict) or not isinstance(metrics.get("failed"), dict):
        raise TrendsError("invalid_data")
    if any(
        not source.strip() or not isinstance(message, str)
        for source, message in metrics["failed"].items()
    ):
        raise TrendsError("invalid_data")
    for key in (
        "sources",
        "successful",
        "requests",
        "received",
        "new",
        "updated",
        "closed",
        "relevant",
        "high_priority",
        "alerts",
    ):
        if key in metrics and (type(metrics[key]) is not int or metrics[key] < 0):
            raise TrendsError("invalid_data")
    if "duration" in metrics and (
        type(metrics["duration"]) not in (int, float)
        or not math.isfinite(metrics["duration"])
        or metrics["duration"] < 0
    ):
        raise TrendsError("invalid_data")
    return len(metrics["failed"])


def _read(config: Config, instant: datetime, daily: dict[str, dict]) -> None:
    url = config.settings.database_url
    if (
        not url.startswith("sqlite:///")
        or url in {"sqlite:///", "sqlite:///:memory:"}
        or "\x00" in url
    ):
        raise TrendsError("invalid_config")
    path = Path(url.removeprefix("sqlite:///")).resolve()
    if not path.is_file():
        raise TrendsError("missing")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        if list(db.execute("PRAGMA quick_check")) != [("ok",)]:
            raise TrendsError("corrupt")
        with closing(sqlite3.connect(":memory:")) as expected:
            expected.executescript(SCHEMA)
            if _schema(db) != _schema(expected):
                raise TrendsError("incompatible")
        if db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] != SCHEMA_VERSION:
            raise TrendsError("incompatible")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise TrendsError("corrupt")
        for table in ("jobs", "job_versions", "scan_runs"):
            if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > MAX_ROWS:
                raise TrendsError("limit_exceeded")

        def bucket(timestamp: str) -> dict | None:
            observed = _timestamp(timestamp)
            return daily.get(observed.date().isoformat()) if observed <= instant else None

        for (timestamp,) in db.execute("SELECT first_seen FROM jobs"):
            if (row := bucket(timestamp)) is not None:
                row["new_jobs"] += 1
        for timestamp, event in db.execute("SELECT created_at,event FROM job_versions"):
            row = bucket(timestamp)
            if event not in {*EVENTS, "new"}:
                raise TrendsError("invalid_data")
            if row is not None and event in EVENTS:
                row[EVENTS[event]] += 1
        for timestamp, size, raw in db.execute(
            "SELECT created_at,length(metrics),substr(metrics,1,?) FROM scan_runs",
            (MAX_METRICS_LENGTH + 1,),
        ):
            if not isinstance(size, int) or size > MAX_METRICS_LENGTH:
                raise TrendsError("limit_exceeded")
            failed = _failed_sources(raw)
            if (row := bucket(timestamp)) is not None:
                row["scans"] += 1
                row["failed_sources"] += failed


def build_trends(config: Config, days: int = 30, now: datetime | None = None) -> dict:
    """Count detections and stored events by UTC day, never publication dates.

    Invalid arguments raise ValueError. Unusable histories return an explicit error,
    with no partial daily rows or zero summary masquerading as a successful reading.
    All three tables share one SQLite transaction. Every read table is capped at
    MAX_ROWS, including older rows whose dates still need validation.
    """
    if type(days) is not int or not 1 <= days <= 365:
        raise ValueError("Days must be an integer between 1 and 365")
    instant = now if now is not None else utcnow()
    if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Statistics time must include a timezone")
    try:
        instant = instant.astimezone(UTC)
        start = instant.date() - timedelta(days=days - 1)
    except (ValueError, OverflowError):
        raise ValueError("Statistics time is outside the supported calendar") from None
    daily = {
        (start + timedelta(days=index)).isoformat(): {
            "date": (start + timedelta(days=index)).isoformat(),
            **dict.fromkeys(COUNTERS, 0),
        }
        for index in range(days)
    }
    result: dict[str, Any] = {
        "format_version": 1,
        "status": "ok",
        "error": None,
        "generated_at": instant.isoformat(),
        "timezone": "UTC",
        "days": days,
        "window": {"start": start.isoformat(), "end": instant.date().isoformat()},
        "daily": [],
        "summary": {},
    }
    code = None
    try:
        _read(config, instant, daily)
    except TrendsError as exc:
        code = exc.code
    except sqlite3.Error as exc:
        sqlite_code = getattr(exc, "sqlite_errorcode", 0) or 0
        code = (
            "corrupt"
            if sqlite_code & 0xFF in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}
            else "unreadable"
        )
    except (ValueError, TypeError, OverflowError, RecursionError):
        code = "invalid_data"
    except OSError:
        code = "unreadable"
    if code:
        result.update(status="error", error={"code": code, "message": MESSAGES[code]})
    else:
        result["daily"] = list(daily.values())
        result["summary"] = {key: sum(row[key] for row in daily.values()) for key in COUNTERS}
    return result
