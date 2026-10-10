"""Shared review criteria for validated offers; no database or delivery dependencies."""

from datetime import date, datetime, timedelta

from trading_radar.audit import timestamp
from trading_radar.display_time import PARIS

REVIEW_STATUSES = {"New", "Reviewing", "To Apply"}


def eligible(job: dict, sources: set[str], threshold: int, now: datetime) -> bool:
    first, last = timestamp(job["first_seen"]), timestamp(job["last_seen"])
    if (
        not job["is_active"]
        or job["is_expired"]
        or job["score"] < max(1, threshold)
        or job["application"]["status"] not in REVIEW_STATUSES
        or job["source"] not in sources
        or first is None
        or last is None
        or not first <= last <= now
        or now - last > timedelta(hours=24)
    ):
        return False
    deadline = job["deadline"]
    if deadline["precision"] == "instant":
        instant = timestamp(deadline["instant"])
        return instant is not None and instant > now
    if deadline["precision"] == "date":
        return date.fromisoformat(deadline["day"]) >= now.astimezone(PARIS).date()
    return deadline["precision"] == "unknown"
