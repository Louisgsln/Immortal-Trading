"""BNP Paribas public HTML search form and JobPosting structured data."""

import asyncio
import json
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlencode, urljoin, urlsplit

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, CollectionConflict, RawJob
from trading_radar.normalizer import canonical_url, has, normalize_text, parse_date
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://group.bnpparibas"
SEARCH = ORIGIN + "/emploi-carriere/toutes-offres-emploi"


def job_url(value: str) -> str:
    url = urljoin(ORIGIN, value)
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.netloc != "group.bnpparibas"
        or parts.query
        or parts.fragment
        or not re.fullmatch(r"/emploi-carriere/offre-emploi/[a-zA-Z0-9_-]+", unquote(parts.path))
    ):
        raise SourceUnavailable("invalid BNP public job URL")
    return url


class SearchPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.query: str | None = None
        self.page: int | None = None
        self.totals: list[int] = []
        self.rows: list[dict] = []
        self.card: dict | None = None
        self.in_title = False
        self.in_total = False
        self.total_text = ""

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        classes = attr.get("class", "").split()
        if tag == "input" and attr.get("name") == "form[q]":
            self.query = attr.get("value", "")
        if "pagination" in classes and "data-page" in attr:
            value = attr["data-page"]
            if not value or not value.isdigit():
                raise SourceUnavailable("invalid BNP page number")
            self.page = int(value)
        if tag == "button" and "show-results-mobile" in classes:
            self.in_total, self.total_text = True, ""
        if tag == "article" and "card-offer" in classes:
            if self.card is not None:
                raise SourceUnavailable("nested BNP listing")
            self.card = {"title": "", "url": ""}
        if self.card is not None:
            if tag == "a" and "card-link" in classes:
                self.card["url"] = job_url(attr.get("href", ""))
            if tag == "h3":
                self.in_title = True

    def handle_data(self, data):
        if self.in_total:
            self.total_text += data
        if self.in_title and self.card is not None:
            self.card["title"] += data

    def handle_endtag(self, tag):
        if tag == "button" and self.in_total:
            match = re.search(r"\(([\d\s\u00a0\u202f]+)\)", self.total_text)
            if not match:
                raise SourceUnavailable("BNP result count missing")
            self.totals.append(int(re.sub(r"\s", "", match[1])))
            self.in_total = False
        if tag == "h3":
            self.in_title = False
        if tag == "article" and self.card is not None:
            self.card["title"] = " ".join(self.card["title"].split())
            if not self.card["title"] or not self.card["url"]:
                raise SourceUnavailable("incomplete BNP listing")
            self.rows.append(self.card)
            self.card = None


class JobData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts: list[str] = []
        self.records: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.active = dict(attrs).get("type") == "application/ld+json"
            self.parts = []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            try:
                value = json.loads("".join(self.parts))
            except ValueError:
                raise SourceUnavailable("invalid BNP structured data") from None
            self.add(value)
            self.active = False

    def add(self, value):
        if isinstance(value, list):
            for entry in value:
                self.add(entry)
        elif isinstance(value, dict):
            if value.get("@type") == "JobPosting":
                self.records.append(value)
            if "@graph" in value:
                self.add(value["@graph"])


def parse_detail(html: str, url: str, config: Company, source: str) -> RawJob:
    parser = JobData()
    parser.feed(html)
    if len(parser.records) != 1:
        raise SourceUnavailable("BNP job detail missing or ambiguous")
    info = parser.records[0]
    identifier = info.get("identifier")
    identifier = identifier.get("value") if isinstance(identifier, dict) else None
    title, description = info.get("title"), info.get("description")
    if (
        not isinstance(identifier, (str, int))
        or isinstance(identifier, bool)
        or not str(identifier).strip()
        or not isinstance(title, str)
        or not title.strip()
        or not isinstance(description, str)
        or not description.strip()
        or not isinstance(info.get("url"), str)
        or canonical_url(job_url(info["url"])) != canonical_url(url)
    ):
        raise SourceUnavailable("incomplete or mismatched BNP job detail")
    locations = info.get("jobLocation")
    if isinstance(locations, dict):
        locations = [locations]
    if not isinstance(locations, list) or not locations:
        raise SourceUnavailable("BNP job location missing")
    labels = []
    for loc in locations:
        address = loc.get("address") if isinstance(loc, dict) else None
        if not isinstance(address, dict):
            raise SourceUnavailable("invalid BNP job address")
        country = address.get("addressCountry")
        if isinstance(country, dict):
            country = country.get("name")
        labels.append(
            ", ".join(
                dict.fromkeys(
                    x
                    for x in (address.get("addressLocality"), address.get("addressRegion"), country)
                    if isinstance(x, str) and x
                )
            )
        )
    posted = parse_date(info.get("datePosted"))
    if info.get("datePosted") and posted is None:
        raise SourceUnavailable("invalid BNP publication date")
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=str(identifier),
        title=title,
        description=description,
        apply_url=url,
        source_url=url,
        location="; ".join(dict.fromkeys(labels)),
        date_posted=posted,
        employment_type=info.get("employmentType"),
        raw_payload=info,
    )


class BNPCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH:
            raise ValueError("Use the BNP public French-language search root")
        self.source, self.config, self.http = source, config, http
        self.options = SearchOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable(
                "BNP scan time budget exceeded; no snapshot committed"
            ) from None

    async def _search(self, term: str) -> dict[str, dict]:
        rows: dict[str, dict] = {}
        expected, page = None, 1
        while expected is None or len(rows) < expected:
            # The head rel=next drops the search query. Keep the verified GET form fields.
            url = SEARCH + "?" + urlencode({"form[q]": term, "page": page})
            parser = SearchPage()
            parser.feed(await self.http.get_text(url, self.config.request_interval, self.source))
            if (
                parser.query != term
                or not parser.totals
                or len(set(parser.totals)) != 1
                or parser.card is not None
            ):
                raise SourceUnavailable("BNP search scope or result count missing")
            total = parser.totals[0]
            if total > self.options.max_results_per_query:
                raise SourceUnavailable("BNP query exceeds result limit; narrow scope")
            if expected is not None and total != expected:
                raise SourceUnavailable("BNP total changed during pagination")
            expected = total
            if (parser.page is None and (page != 1 or total > 10)) or (
                parser.page is not None and parser.page != page
            ):
                raise SourceUnavailable("BNP page number mismatch")
            if len(parser.rows) != min(10, expected - len(rows)):
                raise SourceUnavailable("BNP returned a short or inconsistent page")
            for row in parser.rows:
                if row["url"] in rows:
                    raise SourceUnavailable("BNP pagination repeated a posting")
                rows[row["url"]] = row
            page += 1
        return rows

    def selected(self, title: str) -> bool:
        title = normalize_text(title)
        return (
            not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
        ) and not any(has(title, t) for t in self.options.exclude_title_terms)

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        candidates: dict[str, dict] = {}
        for term in self.options.search_terms:
            candidates.update(await self._search(term))
        targets = {url: row for url, row in candidates.items() if self.selected(row["title"])}
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("BNP detail limit exceeded; narrow scope")
        groups: dict[str, list[RawJob]] = {}
        for url in targets:
            html = await self.http.get_text(url, self.config.request_interval, self.source)
            job = parse_detail(html, url, self.config, self.source)
            key = str(job.external_id)
            groups.setdefault(key, []).append(job)
        jobs = []
        conflicts = []
        ignored = {"apply_url", "source_url", "raw_payload"}
        for key, aliases in sorted(groups.items()):
            baseline = aliases[0].model_dump(exclude=ignored)
            fields = sorted(
                {
                    field
                    for alias in aliases[1:]
                    for field, value in alias.model_dump(exclude=ignored).items()
                    if value != baseline[field]
                }
            )
            if fields:
                conflicts.append(
                    CollectionConflict(
                        external_id=key,
                        urls=sorted({alias.apply_url for alias in aliases}),
                        fields=fields,
                    )
                )
            else:
                # Identical aliases must not alternate URLs on every scan.
                jobs.append(min(aliases, key=lambda item: item.apply_url))
        return Collection(
            jobs=jobs,
            complete=False,
            requests=self.http.counts[self.source] - before,
            conflicts=conflicts,
        )
