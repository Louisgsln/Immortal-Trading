"""Nomura's public campus vacancy board, distinct from its events and professional boards."""

import asyncio
import html
import re
from urllib.parse import urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://nomuracampus.tal.net"
SEARCH = (
    ORIGIN
    + "/vx/lang-en-GB/mobile-0/appcentre-ext/brand-4/xf-3348347fc789/candidate/jobboard/vacancy/1/adv/"
)
ROUTE = "/candidate/so/pm/1/pl/1/opp/"


def job_url(value: str) -> tuple[str, str]:
    parts = urlsplit(value)
    match = re.fullmatch(
        r"(?:/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/xf-[a-f0-9]+)?"
        + ROUTE
        + r"(\d+)-([A-Za-z0-9-]+)/en-GB",
        parts.path,
    )
    if (
        parts.scheme != "https"
        or parts.netloc != "nomuracampus.tal.net"
        or parts.query
        or parts.fragment
        or not match
    ):
        raise SourceUnavailable("invalid Nomura campus vacancy URL")
    # This context-free route was verified publicly; no per-page form tokens are retained.
    return ORIGIN + ROUTE + match[1] + "-" + match[2] + "/en-GB", match[1]


def parse_board(text: str, limit: int) -> list[dict]:
    nodes = list(Document(text).root.walk())
    counts = [
        re.fullmatch(r"(\d+) results? match!", clean(n))
        for n in nodes
        if n.tag == "h2" and n.attrs.get("role") == "alert"
    ]
    if len(counts) != 1 or not counts[0] or int(counts[0][1]) > limit:
        raise SourceUnavailable("Nomura campus result count missing or excessive")
    tables = with_class(nodes, "solr_search_list")
    if len(tables) != 1:
        raise SourceUnavailable("Nomura campus vacancy table missing")
    heads = [clean(n) for n in tables[0].walk() if n.tag == "thead"]
    if heads != ["Title Location Application Deadline"]:
        raise SourceUnavailable("Nomura campus table columns changed")
    rows = []
    for tr in with_class(tables[0].walk(), "details_row"):
        links = with_class(tr.walk(), "subject")
        cells = [n for n in tr.walk() if n.tag == "td"]
        if len(links) != 1 or len(cells) != 3 or not clean(links[0]) or not clean(cells[1]):
            raise SourceUnavailable("Nomura campus card incomplete")
        url, identifier = job_url(links[0].attrs.get("href", ""))
        if tr.attrs.get("data-oppid") != identifier or " ".join(
            tr.attrs.get("data-title", "").split()
        ) != clean(links[0]):
            raise SourceUnavailable("Nomura campus card identity mismatch")
        rows.append(
            {
                "id": identifier,
                "url": url,
                "title": clean(links[0]),
                "location": clean(cells[1]),
                "deadline_text": clean(cells[2]),
            }
        )
    # The observed board returns every result in one table. Fail if pagination appears.
    if len(rows) != int(counts[0][1]) or len({r["id"] for r in rows}) != len(rows):
        raise SourceUnavailable("Nomura campus incomplete or duplicate board")
    return rows


def parse_detail(text: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    titles = [n for n in nodes if n.tag == "h1" and "section" in n.attrs.get("class", "").split()]
    if len(titles) != 1 or clean(titles[0]) != row["title"]:
        raise SourceUnavailable("Nomura campus detail title mismatch")
    # Validate the public application form target as identity evidence, but never submit it.
    ids = []
    for node in nodes:
        if node.tag == "form":
            parts = urlsplit(node.attrs.get("action", ""))
            match = re.search(re.escape(ROUTE) + r"(\d+)/apply/en-GB$", parts.path)
            if match:
                if parts.scheme != "https" or parts.netloc != "nomuracampus.tal.net":
                    raise SourceUnavailable("Nomura application target outside public host")
                ids.append(match[1])
    if ids != [row["id"]]:
        raise SourceUnavailable("Nomura campus detail reference mismatch")
    fields = {}
    for group in with_class(nodes, "form-group"):
        labels = with_class(group.walk(), "hform_lbl_text")
        values = with_class(group.walk(), "form-control-static")
        if len(labels) != 1 or len(values) != 1:
            raise SourceUnavailable("Nomura campus field ambiguous")
        label = clean(labels[0])
        if label in fields:
            raise SourceUnavailable("Nomura campus duplicate field")
        fields[label] = clean(values[0])
    if any(
        not fields.get(key) for key in ["Job description", "Location", "Program type", "Division"]
    ):
        raise SourceUnavailable("Nomura campus description or programme metadata missing")
    if fields["Location"] != row["location"]:
        raise SourceUnavailable("Nomura campus detail location mismatch")
    return RawJob(
        company=config.name,
        title=row["title"],
        source=source,
        source_type="official",
        external_id=row["id"],
        apply_url=row["url"],
        source_url=row["url"],
        description="<p>" + html.escape(fields["Job description"]) + "</p>",
        location=fields["Location"],
        employment_type=fields["Program type"],
        # The table deadline has no timezone. Keep source evidence without inventing an instant.
        raw_payload={"fields": fields, "deadline_text": row["deadline_text"]},
    )


class NomuraOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


class NomuraCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH:
            raise ValueError("Use the verified Nomura campus vacancy board URL")
        self.source, self.config, self.http = source, config, http
        self.options = NomuraOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Nomura campus scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        text = await self.http.get_text(SEARCH, self.config.request_interval, self.source)
        rows = parse_board(text, self.options.max_results_per_query)
        targets = []
        for row in rows:
            title = normalize_text(row["title"])
            if (
                not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
            ) and not any(has(title, t) for t in self.options.exclude_title_terms):
                targets.append(row)
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Nomura campus detail limit exceeded")
        jobs = []
        for row in targets:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
