"""Public Rothschild student catalogue, full pagination and employer descriptions."""

import asyncio
import re
from urllib.parse import urljoin, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.morgan_stanley_campus import public_html
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions
from trading_radar.snapshot_retry import SnapshotChanged, stable_listing

ROOT = "https://www.rothschildandco.com"
PATH = "/en/careers/students-and-graduates/opportunities/"
BOARD = ROOT + PATH
PAGE_SIZE = 50


class RothschildOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def job_url(value: str) -> str:
    url = urljoin(BOARD, value)
    p = urlsplit(url)
    if (
        p.scheme != "https"
        or p.netloc != "www.rothschildandco.com"
        or p.query
        or p.fragment
        or not re.fullmatch(re.escape(PATH) + r"[a-z0-9-]+/", p.path)
    ):
        raise SourceUnavailable("invalid Rothschild student detail URL")
    return url


def parse_page(text: str, page: int, limit: int) -> tuple[list[dict], int]:
    nodes = list(Document(text).root.walk())
    headings = [clean(n) for n in nodes if n.tag == "h1"]
    counts = with_class(nodes, "uid-listings-total-results")
    pages = with_class(nodes, "uid-listings-pagination-results")
    lists = [n for n in nodes if n.attrs.get("id") == "uid-listings-result-list"]
    if (
        headings != ["Opportunities for students and graduates"]
        or len(counts) != 1
        or len(lists) != 1
    ):
        raise SourceUnavailable("Rothschild student catalogue markers missing or ambiguous")
    match = re.fullmatch(r"Results (\d+) to (\d+) of (\d+)", clean(counts[0]))
    if not match:
        raise SourceUnavailable("Rothschild student result range missing")
    first, last, total = map(int, match.groups())
    offset = (page - 1) * PAGE_SIZE
    cards = with_class(lists[0].walk(), "event-listing-item")
    if (
        not 0 < total <= limit
        or first != offset + 1
        or last != min(offset + PAGE_SIZE, total)
        or len(cards) != last - first + 1
        or len(pages) != 1
        or clean(pages[0]) != f"Page {page} of {(total + PAGE_SIZE - 1) // PAGE_SIZE}"
    ):
        raise SourceUnavailable("Rothschild student incomplete or excessive page")
    rows = []
    for card in cards:
        titles = with_class(card.walk(), "roths-career-office-event-card-title")
        locations = with_class(card.walk(), "roths-career-office-event-card-detail")
        links = [n for n in card.walk() if n.tag == "a" and clean(n) == "Learn more"]
        if len(titles) != 1 or not clean(titles[0]) or len(links) != 1 or not locations:
            raise SourceUnavailable("Rothschild student listing metadata missing")
        rows.append(
            {
                "title": clean(titles[0]),
                "location": "; ".join(clean(n) for n in locations),
                "url": job_url(links[0].attrs.get("href", "")),
            }
        )
    if len({r["url"] for r in rows}) != len(rows):
        raise SourceUnavailable("Rothschild student repeated listing")
    return rows, total


def parse_detail(text: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    main = [n for n in nodes if n.tag == "main" and n.attrs.get("id") == "main"]
    titles = [clean(n) for n in nodes if n.tag == "h1"]
    bodies = with_class(main[0].walk(), "wysiwyg") if len(main) == 1 else []
    if titles != [row["title"]] or not bodies or any(not clean(n) for n in bodies):
        raise SourceUnavailable("Rothschild student title or full description missing")
    links = {
        n.attrs.get("href", "")
        for n in main[0].walk()
        if n.tag == "a" and clean(n).casefold().rstrip(" :") == "apply now"
    }
    if len(links) != 1:
        raise SourceUnavailable("Rothschild student application link missing or ambiguous")
    url = links.pop()
    p = urlsplit(url)
    match = re.fullmatch(r"/vx/lang-en-GB/appcentre-1/candidate/postings/([1-9][0-9]{0,9})", p.path)
    if not match:
        match = re.fullmatch(
            r"/vx/appcentre-ext/brand-4/spa-1/candidate/so/pm/1/pl/2/opp/([1-9][0-9]{0,9})-[A-Za-z0-9_-]+/en-GB",
            p.path,
        )
    if (
        p.scheme != "https"
        or p.netloc != "rothschildandco.tal.net"
        or p.query
        or p.fragment
        or not match
    ):
        raise SourceUnavailable("Rothschild student application identity changed")
    description = "\n".join(public_html(n) for n in bodies)
    if len(" ".join(clean(n) for n in bodies)) < 100:
        raise SourceUnavailable("Rothschild student description incomplete")
    facts = " ".join(clean(n) for n in bodies)
    contract = re.search(
        r"\bProgramme:\s*(Long Term Internship|Summer Internship|Off[- ]Cycle Internship|Internship|Graduate|Apprenticeship|Early Insight)\b",
        facts,
    )
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=match[1],
        title=row["title"],
        description=description,
        location=row["location"],
        apply_url=url,
        source_url=row["url"],
        employment_type=contract[1] if contract else None,
    )


class RothschildCampusCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.name != "Rothschild & Co" or config.career_url != BOARD:
            raise ValueError("Use the verified Rothschild public student catalogue")
        self.source, self.config, self.http = source, config, http
        self.options = RothschildOptions(**config.options)

    async def page(self, number: int):
        text = await self.http.get_text(
            BOARD + f"?page={number}", self.config.request_interval, self.source
        )
        return parse_page(text, number, self.options.max_results_per_query)

    async def _list(self):
        initial, total = await self.page(1)
        found = {row["url"]: row for row in initial}
        for page in range(2, (total + PAGE_SIZE - 1) // PAGE_SIZE + 1):
            rows, current = await self.page(page)
            if current != total or any(row["url"] in found for row in rows):
                raise SnapshotChanged("Rothschild student catalogue changed during pagination")
            found.update({row["url"]: row for row in rows})
        if len(found) != total or await self.page(1) != (initial, total):
            raise SnapshotChanged("Rothschild student first page changed during pagination")
        return found

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Rothschild student scan time budget exceeded") from None

    async def _collect(self):
        before = self.http.counts[self.source]
        found = await stable_listing(self._list, self.source)
        selected = []
        for row in found.values():
            title = normalize_text(row["title"])
            if (
                not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
            ) and not any(has(title, t) for t in self.options.exclude_title_terms):
                selected.append(row)
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("Rothschild student detail limit exceeded")
        jobs = []
        for row in selected:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        if len({j.external_id for j in jobs}) != len(jobs):
            raise SourceUnavailable("Rothschild student conflicting application identities")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
        )
