import hashlib
import html
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from trading_radar.deadlines import aware_instant
from trading_radar.models import Job, RawJob, utcnow


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9+#]+", " ", value.lower().replace("&", " and ")).strip()


def has(text: str, term: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(normalize_text(term)) + r"(?!\w)", text))


class PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = PlainText()
    parser.feed(html.unescape(value))
    return " ".join(" ".join(parser.parts).split())


ALIASES = {
    "societe generale": "societe generale",
    "sg cib": "societe generale",
    "societe generale cib": "societe generale",
    "j p morgan": "jpmorgan",
    "jp morgan": "jpmorgan",
    "jpmorgan chase": "jpmorgan",
    "jpmorgan chase and co": "jpmorgan",
    "citigroup": "citi",
    "credit agricole": "credit agricole cib",
    "royal bank of canada": "rbc",
}


def company_key(value: str) -> str:
    key = normalize_text(value)
    return ALIASES.get(key, key)


LOCATIONS = [
    ("Paris", "FR", 1),
    ("London", "UK", 1),
    ("Frankfurt", "DE", 1),
    ("Zurich", "CH", 1),
    ("Geneva", "CH", 1),
    ("Amsterdam", "NL", 1),
    ("Luxembourg", "LU", 2),
    ("Dublin", "IE", 2),
    ("Milan", "IT", 2),
    ("Madrid", "ES", 2),
    ("Monaco", "MC", 2),
    ("New York", "US", 3),
    ("Chicago", "US", 3),
    ("Toronto", "CA", 3),
    ("Montreal", "CA", 3),
    ("Singapore", "SG", 3),
    ("Hong Kong", "HK", 3),
    ("Tokyo", "JP", 3),
    ("Dubai", "AE", 3),
    ("Abu Dhabi", "AE", 3),
    ("Sydney", "AU", 3),
]


def location_parts(value: str) -> tuple[str, str | None, str | None, int | None]:
    text = normalize_text(value).replace("geneve", "geneva").replace("zuerich", "zurich")
    matches = [(city, country, tier) for city, country, tier in LOCATIONS if has(text, city)]
    if len(matches) == 1:
        city, country, tier = matches[0]
        return f"{city}, {country}", city, country, tier
    # Preserve multiple locations rather than incorrectly collapsing into one city.
    if matches:
        return "; ".join(sorted(f"{c}, {co}" for c, co, _ in matches)), None, None, None
    return text, None, None, None


def canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise ValueError("Invalid public HTTP(S) job URL")
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
        and k.lower() not in {"source", "ref", "referrer", "fbclid", "gclid"}
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(sorted(query)),
            ""
            if parts.fragment == "top" or parts.fragment.startswith(":~:text=")
            else parts.fragment,
        )
    )


def digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def parse_date(value: object, now: datetime | None = None) -> datetime | None:
    if not value:
        return None
    now = now or datetime.now(UTC)
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        relative = re.fullmatch(r"(\d+)\s+(minute|hour|day)s? ago", text, re.I)
        if relative:
            return now - timedelta(**{relative[2].lower() + "s": int(relative[1])})
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            for fmt in ("%d %B %Y", "%d %b %Y", "%B %d, %Y"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None  # Ambiguous numeric dates stay unknown.
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def normalize(raw: RawJob, store_raw: bool = False) -> Job:
    company = company_key(raw.company)
    title = normalize_text(raw.title)
    loc, city, country, tier = location_parts(raw.location)
    url = canonical_url(raw.apply_url)
    fingerprint = (
        digest(company, raw.source, raw.external_id) if raw.external_id else digest(company, url)
    )
    payload = raw.model_dump()
    payload["apply_url"] = url
    payload["raw_payload"] = raw.raw_payload if store_raw else None
    payload["date_posted"] = parse_date(raw.date_posted)
    deadline = aware_instant(raw.application_deadline)
    payload["application_deadline"] = deadline
    return Job(
        **payload,
        id=str(uuid4()),
        fingerprint=fingerprint,
        company_normalized=company,
        title_normalized=title,
        description_text=plain_text(raw.description),
        location_normalized=loc,
        city=city,
        country=country,
        location_tier=tier,
        is_expired=bool(deadline and deadline < utcnow()),
    )
