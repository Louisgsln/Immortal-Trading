"""Display/filter facts only. Never rewrite job identities or infer missing dates."""

import calendar
import re
from datetime import date

from trading_radar.description_sections import visible_text
from trading_radar.html_page import Document
from trading_radar.models import Job
from trading_radar.normalizer import LOCATIONS, has, normalize_text
from trading_radar.start_dates import start_period

COUNTRIES = {
    "FR": ("France", ["france"]),
    "GB": ("Royaume-Uni", ["united kingdom", "uk", "great britain", "england", "royaume uni"]),
    "DE": ("Allemagne", ["germany", "deutschland", "allemagne"]),
    "CH": ("Suisse", ["switzerland", "suisse"]),
    "NL": ("Pays-Bas", ["netherlands", "pays bas"]),
    "LU": ("Luxembourg", ["luxembourg"]),
    "IE": ("Irlande", ["ireland", "irlande"]),
    "IT": ("Italie", ["italy", "italie"]),
    "ES": ("Espagne", ["spain", "espagne"]),
    "MC": ("Monaco", ["monaco"]),
    "US": ("États-Unis", ["united states", "usa", "etats unis"]),
    "CA": ("Canada", ["canada"]),
    "HK": ("Hong Kong", ["hong kong"]),
    "SG": ("Singapour", ["singapore", "singapour"]),
    "JP": ("Japon", ["japan", "japon"]),
    "AU": ("Australie", ["australia", "australie"]),
    "IN": ("Inde", ["india", "inde"]),
    "AE": ("Émirats arabes unis", ["united arab emirates", "uae"]),
    "TR": ("Turquie", ["turkey", "turkiye", "turquie"]),
    "PL": ("Pologne", ["poland", "pologne"]),
    "SE": ("Suède", ["sweden", "suede"]),
    "ZA": ("Afrique du Sud", ["south africa"]),
}
CITY_COUNTRIES = {
    normalize_text(city): "GB" if code == "UK" else code for city, code, _ in LOCATIONS
}
CITY_COUNTRIES.update(
    {
        "istanbul": "TR",
        "warsaw": "PL",
        "tokyo": "JP",
        "sydney": "AU",
        "melbourne": "AU",
        "toronto": "CA",
        "montreal": "CA",
        "mumbai": "IN",
        "bangalore": "IN",
        "bengaluru": "IN",
        "stockholm": "SE",
        "johannesburg": "ZA",
    }
)
NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "onze": 11,
    "douze": 12,
}
NUMBER = r"(?:\d{1,2}|" + "|".join(NUMBERS) + r")"
DURATION = re.compile(
    rf"\b(?P<low>{NUMBER})(?:\s*(?:[-–]|to|through|a)\s*(?P<high>{NUMBER}))?\s*[- ]?\s*(?:months?|mois)\b",
    re.I,
)
LABEL = re.compile(
    rf"\b(?:internship|stage|placement|duration|duree|programme|program)\b[^.;!?\n\d]{{0,65}}{NUMBER}(?:\s*(?:[-–]|to|through|a)\s*{NUMBER})?\s*[- ]?\s*(?:months?|mois)\b",
    re.I,
)


def country_facts(job: Job) -> dict:
    codes = set()
    for piece in re.split(r"[;|]", job.location):
        text = normalize_text(piece)
        stated = {
            code
            for code, (_, aliases) in COUNTRIES.items()
            if any(has(text, alias) for alias in aliases)
        }
        codes |= stated or {code for city, code in CITY_COUNTRIES.items() if has(text, city)}
    return {
        "countries": [
            {"code": code, "label": COUNTRIES[code][0]}
            for code in sorted(codes)
            if code in COUNTRIES
        ],
        "evidence": job.location,
        "precision": "recognized" if codes else "unknown",
    }


def duration_facts(job: Job) -> dict:
    text = visible_text(Document(job.description).root)
    # Normalize accents but retain punctuation separating statements.
    import unicodedata

    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    statements = [job.title, job.employment_type or ""]
    for match in LABEL.finditer(text):
        prefix = re.split(r"[.;!?\n]", text[max(0, match.start() - 80) : match.start()])[-1]
        if re.search(
            r"\b(?:completed|previous|prior|past|another|other|experience|effectue|precedent|application|recruitment|assessment|selection|visa)\b",
            normalize_text(prefix + " " + match[0]),
        ):
            continue
        statements.append(match[0])
    ranges, evidence = [], []
    for statement in statements:
        for match in DURATION.finditer(statement):

            def number(value):
                return int(value) if value.isdigit() else NUMBERS[value.lower()]

            low, high = number(match["low"]), number(match["high"] or match["low"])
            if not 1 <= low <= high <= 24:
                return {
                    "precision": "conflict",
                    "min_months": None,
                    "max_months": None,
                    "evidence": [statement],
                }
            ranges.append((low, high))
            evidence.append(statement.strip())
    low = max(r[0] for r in ranges) if ranges else None
    high = min(r[1] for r in ranges) if ranges else None
    conflict = low is not None and high is not None and low > high
    return {
        "precision": "conflict" if conflict else "months" if ranges else "unknown",
        "min_months": None if conflict else low,
        "max_months": None if conflict else high,
        "evidence": list(dict.fromkeys(evidence))[:8],
    }


def start_facts(job: Job) -> dict:
    observed = start_period(job)
    windows = []
    if observed["precision"] in {"months", "year"}:
        year = observed["year"]
        for month in observed["months"] or range(1, 13):
            windows.append(
                {
                    "from": date(year, month, 1).isoformat(),
                    "to": date(year, month, calendar.monthrange(year, month)[1]).isoformat(),
                }
            )
        try:
            exact = date.fromisoformat(job.expected_start_date or "")
        except ValueError:
            pass
        else:
            observed["precision"] = "day"
            windows = [{"from": exact.isoformat(), "to": exact.isoformat()}]
    return {**observed, "windows": windows}
