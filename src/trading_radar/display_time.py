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
    offset = local.strftime("%z")
    hours, minutes = int(offset[1:3]), int(offset[3:5])
    zone = f"UTC{offset[0]}{hours}" + (f":{minutes:02}" if minutes else "")
    return f"{local:%d/%m/%Y · %H:%M} · Paris ({zone})"


def export_paris(value: datetime | None) -> str:
    local = paris_time(value)
    return local.isoformat() if local else ""
