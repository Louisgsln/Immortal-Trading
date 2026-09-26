"""Paris presentation only; stored instants and elapsed-time checks stay in UTC."""

from datetime import datetime
from zoneinfo import ZoneInfo

from trading_radar.audit import timestamp

PARIS = ZoneInfo("Europe/Paris")


def paris_time(value: datetime | str | None) -> datetime | None:
    try:
        parsed = timestamp(value.isoformat() if isinstance(value, datetime) else value)
        return parsed.astimezone(PARIS) if parsed else None
    except (ValueError, OverflowError):
        return None


def format_paris(value: datetime | str | None, *, unknown: str = "Non précisée") -> str:
    local = paris_time(value)
    if local is None:
        return unknown
    return f"{local:%d/%m/%Y · %H:%M}"


def export_paris(value: datetime | None) -> str:
    local = paris_time(value)
    return local.replace(tzinfo=None).isoformat() if local else ""
