"""Jefferies campus vacancies, separate from its public events board."""

import asyncio
import html
import re
from urllib.parse import parse_qs, urljoin, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.description_sections import visible_text
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.morgan_stanley_campus import public_html
from trading_radar.normalizer import normalize_text
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason

ORIGIN = "https://jefferies.tal.net"
PREFIX = "/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/"
BOARD = ORIGIN + "/vx/lang-en-GB/mobile-0/appcentre-ext/brand-4/candidate/jobboard/vacancy/2/adv/"
ROUTE = "candidate/so/pm/1/pl/2/opp/"
CONTRACTS = {
    "Off-Cycle Internship",
    "Summer Internship",
    "Full Time",
    "Full Time Analyst",
    "Placement",
    "Spring Week",
}


class JefferiesCampusOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def public_nodes(body: str):
    nodes = list(Document(body).root.walk())
    if any(n.tag == "altcha-widget" or n.attrs.get("id") == "captcha-form" for n in nodes):
        raise SourceUnavailable("Jefferies campus access restricted: CAPTCHA challenge")
    return nodes


def canonical_detail(value: str, identifier: str) -> str:
    parts = urlsplit(urljoin(ORIGIN, value))
    match = re.fullmatch(
        re.escape(PREFIX)
        + r"(?:xf-[a-f0-9]+/)?"
        + re.escape(ROUTE)
        + r"([1-9][0-9]*)-([A-Za-z0-9-]+)/en-GB",
        parts.path,
    )
    if (
        parts.scheme != "https"
        or parts.netloc != "jefferies.tal.net"
        or parts.query
        or parts.fragment
        or not match
        or match[1] != identifier
    ):
        raise SourceUnavailable("Jefferies campus vacancy URL is invalid")
    return ORIGIN + PREFIX + ROUTE + match[1] + "-" + match[2] + "/en-GB"


def parse_board(body: str, offset: int, limit: int):
    nodes = public_nodes(body)
    headings = with_class(nodes, "job-board-title")
    counts = [
        re.fullmatch(r"([0-9]+) results? match!", clean(n))
        for n in nodes
        if n.tag == "h2" and n.attrs.get("role") == "alert"
    ]
    if (
        not headings
        or {clean(n) for n in headings} != {"Campus Opportunities"}
        or len(counts) != 1
        or not counts[0]
    ):
        raise SourceUnavailable("Jefferies campus board or count is invalid")
    total = int(counts[0][1])
    if total > limit:
        raise SourceUnavailable("Jefferies campus result limit exceeded")
    cards = with_class(nodes, "candidate-opp-tile")
    if len(cards) != min(50, max(0, total - offset)):
        raise SourceUnavailable("Jefferies campus page is incomplete")
    rows = []
    for card in cards:
        identifier = card.attrs.get("data-oppid", "")
        links = with_class(card.walk(), "subject")
        if not re.fullmatch(r"[1-9][0-9]*", identifier) or len(links) != 1 or links[0].tag != "a":
            raise SourceUnavailable("Jefferies campus card identity is invalid")
        title = clean(links[0])
        if not title or normalize_text(title) != normalize_text(card.attrs.get("data-title", "")):
            raise SourceUnavailable("Jefferies campus card title disagrees")
        rows.append(
            {
                "id": identifier,
                "title": title,
                "url": canonical_detail(links[0].attrs.get("href", ""), identifier),
            }
        )
    next_links = [n for n in nodes if n.tag == "a" and clean(n) == "Next page"]
    if offset + len(cards) < total:
        if len(next_links) != 1:
            raise SourceUnavailable("Jefferies campus next page is missing")
        target = urlsplit(urljoin(BOARD, next_links[0].attrs.get("href", "")))
        if (
            target.scheme != "https"
            or target.netloc != "jefferies.tal.net"
            or target.path != urlsplit(BOARD).path
            or target.fragment
            or parse_qs(target.query) != {"start": [str(offset + len(cards))]}
        ):
            raise SourceUnavailable("Jefferies campus next page is invalid")
    elif next_links:
        raise SourceUnavailable("Jefferies campus unexpected next page")
    return total, rows


def parse_detail(body: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = public_nodes(body)
    headings = [n for n in nodes if n.tag == "h1" and "section" in n.attrs.get("class", "").split()]
    if len(headings) != 1 or normalize_text(clean(headings[0])) != normalize_text(row["title"]):
        raise SourceUnavailable("Jefferies campus detail title disagrees")
    fields = {}
    for group in with_class(nodes, "form-group"):
        labels, values = (
            with_class(group.walk(), "hform_lbl_text"),
            with_class(group.walk(), "form-control-static"),
        )
        if len(labels) != 1 or len(values) != 1:
            raise SourceUnavailable("Jefferies campus public field is malformed")
        key = clean(labels[0])
        if key in fields:
            raise SourceUnavailable("Jefferies campus public field is repeated")
        fields[key] = values[0]
    required = {
        "Opportunity ID",
        "Location",
        "Region",
        "Business unit(s)",
        "Program type",
        "Job description",
    }
    if not required <= fields.keys() or any(not visible_text(fields[k]).strip() for k in required):
        raise SourceUnavailable("Jefferies campus public detail is incomplete")
    if clean(fields["Opportunity ID"]) != row["id"]:
        raise SourceUnavailable("Jefferies campus detail requisition disagrees")
    contract = clean(fields["Program type"])
    if contract not in CONTRACTS:
        raise SourceUnavailable("Jefferies campus programme type is unknown")
    targets = []
    for node in nodes:
        if node.tag != "form":
            continue
        parts = urlsplit(node.attrs.get("action", ""))
        match = re.search(re.escape(ROUTE) + r"([1-9][0-9]*)/apply/en-GB$", parts.path)
        if match:
            if parts.scheme != "https" or parts.netloc != "jefferies.tal.net":
                raise SourceUnavailable("Jefferies campus application target is invalid")
            targets.append(match[1])
    if targets != [row["id"]]:
        raise SourceUnavailable("Jefferies campus application identity disagrees")
    description = public_html(fields["Job description"])
    for key in ["Program type", "Business unit(s)", "Region"]:
        description += (
            f"<p><strong>{html.escape(key)}:</strong> {html.escape(clean(fields[key]))}</p>"
        )
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        title=row["title"],
        external_id=row["id"],
        apply_url=row["url"],
        source_url=row["url"],
        description=description,
        location=clean(fields["Location"]),
        employment_type=contract,
    )


class JefferiesCampusCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != BOARD or config.name != "Jefferies":
            raise ValueError("Only the verified Jefferies Campus Opportunities board is supported")
        self.source, self.config, self.http = source, config, http
        self.options = JefferiesCampusOptions(**config.options)

    async def fetch(self, url: str) -> str:
        return await self.http.get_text(url, self.config.request_interval, self.source)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Jefferies campus scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        total, first = parse_board(await self.fetch(BOARD), 0, self.options.max_results_per_query)
        rows = list(first)
        for start in range(50, total, 50):
            count, page = parse_board(
                await self.fetch(BOARD + "?start=" + str(start)),
                start,
                self.options.max_results_per_query,
            )
            if count != total:
                raise SourceUnavailable("Jefferies campus total changed during pagination")
            rows.extend(page)
        if len({r["id"] for r in rows}) != total:
            raise SourceUnavailable("Jefferies campus pagination repeated a posting")
        audit, targets = SelectionAudit("public_catalogue"), []
        for row in rows:
            reason = rejection_reason(row["title"], self.options)
            audit.record(reason, row["title"], row["id"])
            if reason is None:
                targets.append(row)
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Jefferies campus detail limit exceeded")
        jobs = []
        for row in targets:
            try:
                jobs.append(
                    parse_detail(await self.fetch(row["url"]), row, self.config, self.source)
                )
            except SourceUnavailable as exc:
                raise SourceUnavailable("Requisition " + row["id"] + ": " + str(exc)) from None
        count, recheck = parse_board(await self.fetch(BOARD), 0, self.options.max_results_per_query)
        if count != total or recheck != first:
            raise SourceUnavailable("Jefferies campus catalogue changed; retry next scan")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
