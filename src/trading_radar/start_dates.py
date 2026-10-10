"""Explicit candidate start periods; no dates inferred from publication or graduation."""

import re
import unicodedata
from datetime import date

from trading_radar.internship_start_evidence import candidate_start_text
from trading_radar.models import Job
from trading_radar.normalizer import normalize_text

MONTHS = {
    "january": 1,
    "janvier": 1,
    "jan": 1,
    "february": 2,
    "fevrier": 2,
    "feb": 2,
    "march": 3,
    "mars": 3,
    "mar": 3,
    "april": 4,
    "avril": 4,
    "apr": 4,
    "may": 5,
    "mai": 5,
    "june": 6,
    "juin": 6,
    "jun": 6,
    "july": 7,
    "juillet": 7,
    "jul": 7,
    "august": 8,
    "aout": 8,
    "aug": 8,
    "september": 9,
    "septembre": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "octobre": 10,
    "oct": 10,
    "november": 11,
    "novembre": 11,
    "nov": 11,
    "december": 12,
    "decembre": 12,
    "dec": 12,
}
MONTH = r"(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")"
PERIOD = re.compile(
    rf"\b(?P<first>{MONTH})(?:\s+(?P<separator>to|through|and|a|et|or)\s+(?P<last>{MONTH}))?"
    r"\s+(?:\d{1,2}\s+)?(?P<year>20\d{2})\b"
)
LABEL = re.compile(
    r"\b(?:start(?:s|ing)?(?: date)?|commenc(?:e|es|ing)|joining(?: us)?|"
    r"debut(?: de mission| de contrat)?|prise de poste)\b[^.;!?\n]{0,120}",
    re.I,
)
TARGET_MONTHS = {1, 2, 3, 4, 6, 7, 8, 9}


def _periods(text: str) -> list[tuple[int, tuple[int, ...]]]:
    periods: list[tuple[int, tuple[int, ...]]] = []
    for match in re.finditer(r"\b20\d{2}-\d{2}-\d{2}\b", text):
        try:
            parsed = date.fromisoformat(match[0])
        except ValueError:
            periods.append((int(match[0][:4]), ()))
            continue
        periods.append((parsed.year, (parsed.month,)))
    alternatives = re.sub(rf"\b({MONTH})\s*/\s*({MONTH})\b", r"\1 or \2", text, flags=re.I)
    normalized = normalize_text(alternatives)
    for match in PERIOD.finditer(normalized):
        first = MONTHS[match["first"]]
        last = MONTHS[match["last"]] if match["last"] else first
        if match["separator"] == "or":
            periods.append((int(match["year"]), tuple(sorted({first, last}))))
        elif last < first:
            periods.append((int(match["year"]), ()))
        else:
            periods.append((int(match["year"]), tuple(range(first, last + 1))))
    for match in re.finditer(r"\bq([1-4])\s+(20\d{2})\b", normalized):
        first = (int(match[1]) - 1) * 3 + 1
        periods.append((int(match[2]), tuple(range(first, first + 3))))
    return periods


def start_period(job: Job) -> dict:
    structured = (job.expected_start_date or "").strip()
    # Keep punctuation for ISO dates, but normalize accents in labels.
    description = candidate_start_text(job)
    description = unicodedata.normalize("NFKD", description).encode("ascii", "ignore").decode()
    chunks = []
    for match in LABEL.finditer(description):
        prefix = description[max(0, match.start() - 40) : match.start()]
        if re.search(r"\b(?:no|not|previous|original|old|example)\s*$", prefix, re.I):
            continue
        chunk = re.split(
            r"\b(?:application|deadline|closing|graduation|copyright)\b",
            match[0],
            maxsplit=1,
            flags=re.I,
        )[0]
        chunks.append(chunk)
    statements = ([structured] if structured else []) + chunks
    periods = [period for statement in statements for period in _periods(statement)]
    years = {year for year, _ in periods}
    title_years = {int(y) for y in re.findall(r"\b20\d{2}\b", job.title)}
    stated_years = {
        int(y) for statement in statements for y in re.findall(r"\b20\d{2}\b", statement)
    }
    years |= stated_years
    conflict = len(years) > 1 or bool(title_years and years and years - title_years)
    months = sorted({month for _, values in periods for month in values})
    if any(not values for _, values in periods):
        conflict = True
    month_groups = [
        {month for _, values in _periods(statement) for month in values} for statement in statements
    ]
    month_groups = [group for group in month_groups if group]
    if month_groups and not conflict:
        consistent_months = set.intersection(*month_groups)
        if not consistent_months:
            conflict = True
        else:
            months = sorted(consistent_months)
    year = next(iter(years)) if len(years) == 1 else None
    return {
        "precision": "conflict"
        if conflict
        else "months"
        if months
        else "year"
        if years
        else "unknown",
        "year": year,
        "months": months,
        "target_window": (
            "unknown"
            if conflict or year != 2027 or not months
            else "preferred"
            if set(months) <= TARGET_MONTHS
            else "outside"
            if not set(months) & TARGET_MONTHS
            else "mixed"
        ),
        "evidence": list(dict.fromkeys(statement.strip() for statement in statements))[:8],
    }
