"""HSBC's public programme finder and SuccessFactors emerging-talent pages."""

import asyncio
import html
import re
from datetime import UTC, datetime
from urllib.parse import urlencode, urlsplit, urlunsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, Element, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

SEARCH = "https://www.hsbc.com/careers/students-and-graduates/find-a-programme"
API = "https://www.hsbc.com/api/programmes/get-programmes"


def job_url(value: str) -> tuple[str, str]:
    parts = urlsplit(value)
    match = re.fullmatch(r"/emergingtalent/job/[^/]+/(\d+)/", parts.path)
    if (
        parts.scheme != "https"
        or parts.netloc != "apply.careers.hsbc.com"
        or parts.fragment
        or not match
    ):
        raise SourceUnavailable("invalid HSBC emerging-talent job URL")
    # Feed/campaign tracking does not form part of the employer's vacancy identity.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")), match[1]


def parse_cards(root: Element) -> list[dict]:
    result = []
    for card in with_class(root.walk(), "program-item"):
        links = with_class(card.walk(), "program-text__destination-link")
        if len(links) != 1:
            raise SourceUnavailable("HSBC programme link missing or ambiguous")
        url, identifier = job_url(links[0].attrs.get("href", ""))
        title = clean(links[0]).removesuffix(" (opens in new window)").strip()
        labels = {}
        for group in with_class(card.walk(), "program-text__group"):
            names = [n for n in group.walk() if n.tag == "dt"]
            values = [n for n in group.walk() if n.tag == "dd"]
            if len(names) != 1 or len(values) != 1 or clean(names[0]) in labels:
                raise SourceUnavailable("HSBC programme metadata ambiguous")
            labels[clean(names[0])] = clean(values[0])
        if not title or not labels.get("Programme type"):
            raise SourceUnavailable("HSBC programme title/type missing")
        start = labels.get("Start Date") or None
        if start:
            try:
                start = datetime.strptime(start, "%a %b %d, %Y").date().isoformat()
            except ValueError:
                raise SourceUnavailable("invalid HSBC programme start date") from None
        result.append(
            {
                "id": identifier,
                "url": url,
                "title": title,
                "start": start,
                "type": labels["Programme type"],
            }
        )
    return result


def parse_index(text: str, limit: int) -> tuple[list[dict], str, int, int, int]:
    roots = [
        n for n in Document(text).root.walk() if n.attrs.get("data-component") == "ProgramFinder"
    ]
    if len(roots) != 1:
        raise SourceUnavailable("HSBC programme finder missing")
    root = roots[0]
    settings = root.attrs.get("data-props-settings", "")
    if not re.fullmatch(r"[a-f0-9]{32}", settings):
        raise SourceUnavailable("invalid HSBC public settings identifier")
    try:
        skip, take, total = (
            int(root.attrs["data-props-" + key]) for key in ("skip", "take", "total-count")
        )
    except (KeyError, ValueError):
        raise SourceUnavailable("HSBC pagination metadata missing") from None
    rows = parse_cards(root)
    grids = with_class(root.walk(), "program-finder-grid")
    if (
        len(grids) != 1
        or not 0 <= total <= limit
        or not 1 <= take <= 100
        or len(rows) != min(skip, total)
        or skip <= 0
    ):
        raise SourceUnavailable("HSBC incomplete or excessive first page")
    count = sum(n.tag == "li" for n in grids[0].walk())
    return rows, settings, take, total, count


def utc_date(value: str) -> datetime:
    if not re.fullmatch(r"[A-Za-z]{3} [A-Za-z]{3} \d{2} \d{2}:\d{2}:\d{2} UTC \d{4}", value):
        raise SourceUnavailable("HSBC date lacks the expected UTC format")
    try:
        return datetime.strptime(value, "%a %b %d %H:%M:%S UTC %Y").replace(tzinfo=UTC)
    except ValueError:
        raise SourceUnavailable("invalid HSBC UTC date") from None


def parse_detail(text: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    canonical = [
        n.attrs.get("href", "")
        for n in nodes
        if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    if len(canonical) != 1:
        raise SourceUnavailable("HSBC canonical URL missing")
    url, identifier = job_url(canonical[0])
    if identifier != row["id"]:
        raise SourceUnavailable("HSBC detail identity mismatch")
    shells = with_class(nodes, "jobDisplayShell")
    if len(shells) != 1 or not shells[0].attrs.get("itemtype", "").endswith("/JobPosting"):
        raise SourceUnavailable("HSBC JobPosting missing")
    nodes = list(shells[0].walk())
    props = {}
    for node in nodes:
        key = node.attrs.get("itemprop")
        if key in {"title", "datePosted", "validThrough"}:
            if key in props:
                raise SourceUnavailable("HSBC duplicate job metadata")
            props[key] = node.attrs.get("content") or clean(node)
    description = with_class(nodes, "jobdescription")
    if (
        len(description) != 1
        or not description[0].text(without_headings=True).strip()
        or props.get("title") != row["title"]
    ):
        raise SourceUnavailable("HSBC title mismatch or description missing")
    places = []
    for address in [n for n in nodes if n.attrs.get("itemprop") == "address"]:
        values = {}
        for node in address.walk():
            key = node.attrs.get("itemprop")
            if key in {"addressLocality", "addressRegion", "addressCountry"}:
                if key in values:
                    raise SourceUnavailable("HSBC conflicting address metadata")
                values[key] = node.attrs.get("content") or clean(node)
        if not values.get("addressLocality") or not values.get("addressCountry"):
            raise SourceUnavailable("HSBC incomplete address")
        places.append(
            ", ".join(
                dict.fromkeys(
                    values[key]
                    for key in ("addressLocality", "addressRegion", "addressCountry")
                    if values.get(key)
                )
            )
        )
    if not places or not props.get("datePosted"):
        raise SourceUnavailable("HSBC location/publication missing")
    applications = [
        n
        for n in nodes
        if n.tag == "a"
        and n.attrs.get("href", "").split("?")[0] == f"/talentcommunity/apply/{identifier}/"
    ]
    if not applications:
        raise SourceUnavailable("HSBC active application link missing")
    posted = utc_date(props["datePosted"])
    deadline = utc_date(props["validThrough"]) if props.get("validThrough") else None
    if deadline and deadline < posted:
        raise SourceUnavailable("HSBC deadline predates publication")
    return RawJob(
        company=config.name,
        title=props["title"],
        source=source,
        source_type="official",
        external_id=identifier,
        source_url=url,
        apply_url=url,
        description="<p>" + html.escape(clean(description[0])) + "</p>",
        location="; ".join(dict.fromkeys(places)),
        date_posted=posted,
        application_deadline=deadline,
        expected_start_date=row["start"],
        employment_type=row["type"],
        raw_payload={"metadata": props, "locations": places, "programme": row},
    )


class HSBCOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


class HSBCCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH:
            raise ValueError("Use the verified HSBC programme finder URL")
        self.source, self.config, self.http = source, config, http
        self.options = HSBCOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("HSBC scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        text = await self.http.get_text(SEARCH, self.config.request_interval, self.source)
        initial, settings, take, total, count = parse_index(
            text, self.options.max_results_per_query
        )
        rows = {row["id"]: row for row in initial}
        if len(rows) != len(initial):
            raise SourceUnavailable("HSBC duplicate programme on first page")
        while len(rows) < total:
            query = urlencode({"skip": len(rows), "take": take, "count": count, "s": settings})
            payload = await self.http.get_json(
                API + "?" + query, self.config.request_interval, self.source
            )
            if (
                not isinstance(payload, list)
                or not payload
                or any(not isinstance(item, str) for item in payload)
            ):
                raise SourceUnavailable("invalid HSBC programme page")
            batch = []
            for item in payload:
                root = Document(item).root
                cards = parse_cards(root)
                if len(cards) != 1 and not (not cards and with_class(root.walk(), "content-card")):
                    raise SourceUnavailable("HSBC unknown programme fragment")
                batch.extend(cards)
                count += sum(n.tag == "li" for n in root.walk())
            if not batch or len(batch) > min(take, total - len(rows)):
                raise SourceUnavailable("HSBC empty or excessive programme page")
            for row in batch:
                if row["id"] in rows:
                    raise SourceUnavailable("HSBC repeated programme between pages")
                rows[row["id"]] = row
        # The fragment API omits totals: recheck the public catalogue after pagination.
        text = await self.http.get_text(SEARCH, self.config.request_interval, self.source)
        again, new_settings, new_take, new_total, _ = parse_index(
            text, self.options.max_results_per_query
        )
        if (again, new_settings, new_take, new_total) != (initial, settings, take, total):
            raise SourceUnavailable("HSBC catalogue changed during pagination")
        selected = []
        for row in rows.values():
            title = normalize_text(row["title"])
            if (
                not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
            ) and not any(has(title, t) for t in self.options.exclude_title_terms):
                selected.append(row)
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("HSBC detail limit exceeded")
        jobs = []
        for row in selected:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
