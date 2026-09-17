"""Conservative, evidence-backed deadlines derived without changing observations."""

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, timezone

from trading_radar.models import Job

MONTHS = {
    name.lower(): i
    for i, name in enumerate(
        "January February March April May June July August September October November December".split(),
        1,
    )
}
DAY = r"\d{1,2}(?:st|nd|rd|th)?"
MONTH = "(?:" + "|".join(MONTHS) + ")"
WEEKDAY = r"(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?"
DATE = (
    WEEKDAY + rf"(?:\d{{4}}-\d{{2}}-\d{{2}}|{DAY}\s+{MONTH}\s+\d{{4}}|{MONTH}\s+{DAY},?\s+\d{{4}})"
)
TIME = r"\d{1,2}:\d{2}\s*(?:am|pm)?"
ZONE = r"(?:UTC|GMT|HKT|SGT|CET|CEST|[+-]\d{2}:\d{2})(?![\w:+-])"
LABEL = re.compile(r"\b(?:application deadline|applications? closes?|closing date)\b", re.I)
DATE_FIRST = re.compile(rf"(?:\s*[:\-]?\s*)(?:(?:will be|is|on)\s+)?(?P<date>{DATE})(?!\w)", re.I)
TIME_FIRST = re.compile(
    rf"\s*:?\s*(?:please apply before|at)\s+(?P<time>{TIME})\s*(?P<zone>{ZONE})?"
    rf"\s*,?\s*(?:on\s+)?(?P<date>{DATE})(?!\w)",
    re.I,
)
TIME_SUFFIX = re.compile(rf"^[\s,\-–—�]*(?:at\s+)?(?P<time>{TIME})\s*\(?(?P<zone>{ZONE})\)?", re.I)
ZONE_SUFFIX = re.compile(rf"^\s*\(?(?P<zone>{ZONE})\)?", re.I)


@dataclass
class Deadline:
    precision: str = "unknown"
    day: date | None = None
    instant: datetime | None = None
    source: str = "description"
    evidence: list[str] = field(default_factory=list)


def aware_instant(value: object) -> datetime | None:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(UTC)


def explicit_day(text: str) -> date:
    weekday = re.match(
        r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+", text, re.I
    )
    if weekday:
        text = text[weekday.end() :]
    text = re.sub(r"(\d)(?:st|nd|rd|th)\b", r"\1", text, flags=re.I).replace(",", "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        result = date.fromisoformat(text)
    else:
        parts = text.lower().split()
        day, month, year = (parts[1], parts[0], parts[2]) if parts[0] in MONTHS else parts
        result = date(int(year), MONTHS[month], int(day))
    if weekday and result.weekday() != [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ].index(weekday[1].lower()):
        raise ValueError("Weekday contradicts date")
    return result


def explicit_instant(day: date, time: str, zone: str) -> datetime:
    clock = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(am|pm)?", time, re.I)
    assert clock is not None
    hour, minute = int(clock[1]), int(clock[2])
    if clock[3]:
        if not 1 <= hour <= 12:
            raise ValueError("Invalid 12-hour time")
        hour = hour % 12 + (12 if clock[3].lower() == "pm" else 0)
    offsets = {"UTC": 0, "GMT": 0, "HKT": 480, "SGT": 480, "CET": 60, "CEST": 120}
    if zone.upper() in offsets:
        offset = offsets[zone.upper()]
    else:
        hours, minutes = int(zone[1:3]), int(zone[4:6])
        if hours > 14 or minutes > 59 or (hours == 14 and minutes):
            raise ValueError("Invalid timezone offset")
        offset = (1 if zone[0] == "+" else -1) * (hours * 60 + minutes)
    return datetime(
        day.year, day.month, day.day, hour, minute, tzinfo=timezone(timedelta(minutes=offset))
    ).astimezone(UTC)


def extract_deadline(text: str) -> Deadline:
    candidates = []
    evidence = []
    for label in LABEL.finditer(text):
        prefix = text[max(0, label.start() - 35) : label.start()]
        if re.search(r"\b(?:no|not|previous|original|old|example)\s*$", prefix, re.I):
            continue
        body = text[label.end() : label.end() + 180]
        match = DATE_FIRST.match(body) or TIME_FIRST.match(body)
        if not match:
            continue
        snippet = text[label.start() : label.end() + match.end()]
        try:
            day = explicit_day(match["date"])
            clock, zone = match.groupdict().get("time"), match.groupdict().get("zone")
            suffix = (
                TIME_SUFFIX.match(body[match.end() :])
                if not clock
                else ZONE_SUFFIX.match(body[match.end() :])
            )
            if suffix:
                if (
                    clock
                    and zone
                    and explicit_instant(day, clock, zone)
                    != explicit_instant(day, clock, suffix["zone"])
                ):
                    return Deadline(
                        "conflict",
                        evidence=[snippet + body[match.end() : match.end() + suffix.end()]],
                    )
                clock = clock or suffix.groupdict().get("time")
                zone = zone or suffix["zone"]
                snippet += body[match.end() : match.end() + suffix.end()]
            tail = body[match.end() + (suffix.end() if suffix else 0) :]
            if re.match(r"\s*(?:or\b|to\b|through\b|/)", tail, re.I):
                return Deadline("conflict", evidence=[snippet + tail[:60]])
            instant = explicit_instant(day, clock, zone) if clock and zone else None
        except (ValueError, KeyError):
            return Deadline("conflict", evidence=[snippet])
        candidates.append((day, instant))
        evidence.append(snippet)
    if not candidates:
        return Deadline()
    days = {d for d, _ in candidates}
    instants = {t for _, t in candidates if t is not None}
    if len(days) != 1 or len(instants) > 1:
        return Deadline("conflict", evidence=evidence)
    instant = next(iter(instants), None)
    return Deadline("instant" if instant else "date", next(iter(days)), instant, evidence=evidence)


def resolve_deadline(job: Job) -> Deadline:
    result = extract_deadline(job.description_text)
    structured = job.application_deadline
    if structured is None:
        return result
    if structured.tzinfo is None:
        return Deadline(
            "conflict", source="structured", evidence=["Structured deadline lacks timezone"]
        )
    instant = structured.astimezone(UTC)
    if result.precision == "conflict" or (result.instant and result.instant != instant):
        return Deadline(
            "conflict",
            source="structured+description",
            evidence=[structured.isoformat(), *result.evidence],
        )
    if result.day and not result.instant and result.day != structured.date():
        return Deadline(
            "conflict",
            source="structured+description",
            evidence=[structured.isoformat(), *result.evidence],
        )
    return Deadline(
        "instant",
        result.day or structured.date(),
        instant,
        "structured",
        [structured.isoformat(), *result.evidence],
    )
