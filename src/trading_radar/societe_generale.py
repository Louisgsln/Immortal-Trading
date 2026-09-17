"""SG's public French/English directories and public job pages, without OAuth."""

import asyncio
import html
import json
import re
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, Element, clean
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://careers.societegenerale.com"
DIRECTORIES = {
    "fr": ORIGIN + "/fr/Technical/toutes-les-offres",
    "en": ORIGIN + "/en/Technical/all-job-offers",
}


def job_url(value: str) -> tuple[str, str, str]:
    url = urljoin(ORIGIN, value)
    parts = urlsplit(url)
    match = re.fullmatch(
        r"/(offres-d-emploi|en/job-offers)/[A-Za-z0-9_-]+-([A-Z0-9]{8})-(fr|en)", parts.path
    )
    if (
        parts.scheme != "https"
        or parts.netloc != "careers.societegenerale.com"
        or parts.query
        or parts.fragment
        or not match
        or (match[1] == "offres-d-emploi") != (match[3] == "fr")
    ):
        raise SourceUnavailable("invalid SG public job URL")
    return url, match[2], match[3]


def directory(text: str, language: str, maximum: int) -> dict[str, dict]:
    nodes = list(Document(text).root.walk())
    counts = []
    for node in nodes:
        if node.tag == "span" and "text-extra-large" in node.attrs.get("class", "").split():
            match = re.fullmatch(r"([\d\s]+)\s*offre\(s\)", clean(node))
            if match:
                counts.append(int(re.sub(r"\s", "", match[1])))
    if len(counts) != 1:
        raise SourceUnavailable("SG directory advertised count missing or ambiguous")
    if counts[0] > maximum:
        raise SourceUnavailable("SG directory result limit exceeded")
    rows: dict[str, dict] = {}
    for node in nodes:
        if "data-offer-id" not in node.attrs:
            continue
        identifier = node.attrs["data-offer-id"]
        links = [n for n in node.walk() if n.tag == "a" and "href" in n.attrs]
        if len(links) != 1:
            raise SourceUnavailable("SG directory card missing or ambiguous")
        url, actual, locale = job_url(links[0].attrs["href"])
        title = clean(links[0])
        if actual != identifier or locale != language or not title or identifier in rows:
            raise SourceUnavailable("SG directory identity, language or duplicate mismatch")
        rows[identifier] = {"id": identifier, "title": title, "url": url, "language": locale}
    if len(rows) != counts[0]:
        raise SourceUnavailable("SG directory incomplete: count differs from job cards")
    return rows


def sg_date(value: str, language: str = "en") -> datetime:
    pattern = "%d/%m/%Y" if language == "fr" else "%Y/%m/%d"
    try:
        return datetime.strptime(value, pattern).replace(tzinfo=UTC)
    except (ValueError, TypeError):
        raise SourceUnavailable("invalid SG date") from None


def parse_detail(text: str, listing: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    records = []
    for node in nodes:
        if node.tag == "script" and node.attrs.get("type") == "application/ld+json":
            try:
                value = json.loads(node.text())
            except ValueError:
                raise SourceUnavailable("invalid SG structured data") from None
            if isinstance(value, dict) and value.get("@type") == "JobPosting":
                records.append(value)
    if len(records) != 1:
        raise SourceUnavailable("SG job detail missing or ambiguous")
    info = records[0]
    identifier = info.get("identifier")
    if not isinstance(identifier, dict) or identifier.get("value") != listing["id"]:
        raise SourceUnavailable("SG detail identifier mismatch")
    canonicals = [
        n.attrs.get("href") for n in nodes if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    if canonicals != [listing["url"]]:
        raise SourceUnavailable("SG detail canonical URL mismatch")
    titles = [n for n in nodes if n.tag == "h1" and n.attrs.get("id") == "offerTitle"]
    if len(titles) != 1 or not clean(titles[0]):
        raise SourceUnavailable("SG job title missing")
    sections = [
        n for n in nodes if n.tag == "section" and n.attrs.get("id", "").startswith("job-detail-")
    ]
    ids = [n.attrs["id"] for n in sections]
    if (
        len(ids) != len(set(ids))
        or not {"job-detail-description", "job-detail-profile"} <= set(ids)
        or any(not n.text(without_headings=True).strip() for n in sections)
    ):
        raise SourceUnavailable("SG responsibilities or requirements missing")
    # Capture only explicit header labels; unrelated dates in prose are not metadata.
    labels = {}
    wanted = {"reference", "date de debut", "start date", "date de publication", "publication date"}
    for node in nodes:
        if node.tag != "div":
            continue
        spans = [n for n in node.children if isinstance(n, Element) and n.tag == "span"]
        if len(spans) == 1:
            label = normalize_text(clean(spans[0]))
            if label in wanted:
                value = " ".join(n.strip() for n in node.children if isinstance(n, str)).strip()
                if label in labels or not value:
                    raise SourceUnavailable("SG header metadata missing or ambiguous")
                labels[label] = value
    if labels.get("reference") != listing["id"]:
        raise SourceUnavailable("SG visible reference mismatch")
    publication = info.get("datePosted")
    if not isinstance(publication, str):
        raise SourceUnavailable("SG publication date missing")
    posted = sg_date(publication)
    visible = labels.get("date de publication") or labels.get("publication date")
    if visible is not None and sg_date(visible, listing["language"]) != posted:
        raise SourceUnavailable("SG publication dates disagree")
    start = labels.get("date de debut") or labels.get("start date")
    if start and re.fullmatch(r"[\d/]+", start):
        start = sg_date(start, listing["language"]).date().isoformat()
    if start and len(start) > 100:
        raise SourceUnavailable("invalid SG start-date text")
    location = info.get("jobLocation")
    locations = [location] if isinstance(location, dict) else location
    if not isinstance(locations, list) or not locations:
        raise SourceUnavailable("SG location missing")
    places = []
    for item in locations:
        address = item.get("address") if isinstance(item, dict) else None
        if not isinstance(address, dict):
            raise SourceUnavailable("invalid SG location")
        country = address.get("addressCountry")
        country = country.get("name") if isinstance(country, dict) else country
        parts = [address.get("addressLocality"), address.get("addressRegion"), country]
        place = ", ".join(dict.fromkeys(x for x in parts if isinstance(x, str) and x))
        if not place:
            raise SourceUnavailable("empty SG location")
        places.append(place)
    # The visible h1 is the job title; JSON-LD title also appends the business unit/location.
    # validThrough contradicted the visible start date and is NOT treated as a deadline.
    return RawJob(
        company=config.name,
        title=clean(titles[0]),
        source=source,
        source_type="official",
        external_id=listing["id"],
        apply_url=listing["url"],
        source_url=listing["url"],
        description="\n".join("<p>" + html.escape(clean(n)) + "</p>" for n in sections),
        location="; ".join(dict.fromkeys(places)),
        date_posted=posted,
        expected_start_date=start,
        employment_type=info.get("employmentType"),
        raw_payload={"structured": info, "labels": labels, "language": listing["language"]},
    )


class SGOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


class SocieteGeneraleCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != DIRECTORIES["fr"]:
            raise ValueError("Use the verified SG public French directory root")
        self.source, self.config, self.http = source, config, http
        self.options = SGOptions(**config.options)

    def selected(self, title: str) -> bool:
        title = normalize_text(title)
        return (
            not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
        ) and not any(has(title, t) for t in self.options.exclude_title_terms)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("SG scan time budget exceeded; no snapshot committed") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        rows: dict[str, dict] = {}
        for language, url in DIRECTORIES.items():
            text = await self.http.get_text(url, self.config.request_interval, self.source)
            # English wins consistently when the employer reference exists in both languages.
            rows.update(directory(text, language, self.options.max_results_per_query))
        targets = [row for row in rows.values() if self.selected(row["title"])]
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("SG detail limit exceeded; narrow title scope")
        jobs = []
        for row in targets:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
