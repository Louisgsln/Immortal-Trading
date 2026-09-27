"""Marex's complete public listing, with a bounded selection of role details."""

import asyncio
import json
import re
from datetime import datetime
from urllib.parse import urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, Element, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.optiver_sections import description_html
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://www.marex.com"
SEARCH = ORIGIN + "/careers/career-opportunities"
_PATH = re.compile(r"/careers/career-opportunities/([a-f0-9]{14})-([a-z0-9-]+)")


def publication_metadata(nodes: list[Element]) -> list[dict]:
    """Decode the public page's JSON arguments, without evaluating JavaScript."""
    chunks = []
    for node in nodes:
        script = node.text().strip() if node.tag == "script" else ""
        if not script.startswith("self.__next_f.push("):
            continue
        match = re.fullmatch(r"self\.__next_f\.push\((.*)\);?", script, re.S)
        try:
            argument = json.loads(match[1]) if match else None
        except ValueError:
            raise SourceUnavailable("invalid Marex page data") from None
        if (
            not isinstance(argument, list)
            or len(argument) != 2
            or argument[0] != 1
            or not isinstance(argument[1], str)
        ):
            raise SourceUnavailable("unexpected Marex page data")
        chunks.append(argument[1])
    payload = "".join(chunks)
    starts = list(re.finditer(r'"jobs"\s*:\s*(?=\[)', payload))
    if len(starts) != 1:
        raise SourceUnavailable("Marex publication metadata missing or ambiguous")
    try:
        rows, _ = json.JSONDecoder().raw_decode(payload, starts[0].end())
    except ValueError:
        raise SourceUnavailable("invalid Marex publication metadata") from None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise SourceUnavailable("invalid Marex publication rows")
    return rows


def publication_date(value: object) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise SourceUnavailable("Marex publication timestamp lacks precision or timezone")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SourceUnavailable("invalid Marex publication timestamp") from None


def job_url(value: str) -> tuple[str, str]:
    parts = urlsplit(value)
    match = _PATH.fullmatch(parts.path)
    if (
        not match
        or (parts.scheme or parts.netloc)
        and (parts.scheme, parts.netloc) != ("https", "www.marex.com")
        or parts.query
        or parts.fragment
    ):
        raise SourceUnavailable("invalid Marex vacancy URL")
    return ORIGIN + parts.path, match[1]


def parse_listing(text: str, limit: int) -> list[dict[str, str]]:
    nodes = list(Document(text).root.walk())
    titles = [clean(n) for n in nodes if n.tag == "h1"]
    counts = [clean(n) for n in nodes if n.attrs.get("id") == "location-select"]
    match = (
        re.fullmatch(r"All Locations\s*\(\s*(\d+)\s*\)", counts[0]) if len(counts) == 1 else None
    )
    if titles != ["Career Opportunities"] or not match or int(match[1]) > limit:
        raise SourceUnavailable("Marex catalogue identity or bounded total missing")
    cards = with_class(nodes, "MuiCard-root")
    if len(cards) != int(match[1]):
        raise SourceUnavailable("Marex catalogue count does not match its cards")
    rows = []
    for card in cards:
        if card.tag != "a":
            raise SourceUnavailable("Marex vacancy link missing")
        url, ident = job_url(card.attrs.get("href", ""))
        children = list(card.walk())
        title = [clean(c) for c in children if c.tag == "h4"]
        location = [clean(c) for c in with_class(children, "MuiTypography-h6") if c.tag == "div"]
        metadata = [clean(c) for c in children if c.tag == "h6"]
        if (
            len(title) != 1
            or not title[0]
            or len(location) != 1
            or not location[0]
            or len(metadata) not in {1, 2}
            or any(not value for value in metadata)
        ):
            raise SourceUnavailable("incomplete Marex vacancy card")
        rows.append(
            dict(
                id=ident,
                url=url,
                title=title[0],
                location=location[0],
                employment=metadata[0],
                department=metadata[1] if len(metadata) == 2 else "",
            )
        )
    if len({r["id"] for r in rows}) != len(rows):
        raise SourceUnavailable("duplicate Marex vacancy identifier")
    publications = publication_metadata(nodes)
    if len(publications) != len(rows) or any(
        not isinstance(m.get("id"), str) for m in publications
    ):
        raise SourceUnavailable("Marex publication catalogue count mismatch")
    by_id = {m["id"]: m for m in publications}
    if len(by_id) != len(rows) or set(by_id) != {r["id"] for r in rows}:
        raise SourceUnavailable("Marex publication catalogue identity mismatch")
    for row in rows:
        meta = by_id[row["id"]]
        slug = row["url"].rsplit("/", 1)[1]
        if (
            meta.get("friendly_id") != slug
            or meta.get("url") != "https://marex.breezy.hr/p/" + slug
            or not isinstance(meta.get("name"), str)
            or " ".join(meta["name"].split()) != row["title"]
            or not isinstance(meta.get("company"), dict)
            or meta["company"].get("friendly_id") != "marex"
            or not isinstance(meta.get("location"), dict)
            or meta["location"].get("name") != row["location"]
            or not isinstance(meta.get("type"), dict)
            or meta["type"].get("name") != row["employment"]
        ):
            raise SourceUnavailable("Marex publication metadata identity mismatch")
        row["published"] = publication_date(meta.get("published_date")).isoformat()
    return sorted(rows, key=lambda r: r["id"])


def parse_detail(text: str, row: dict[str, str], config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    if [clean(n) for n in nodes if n.tag == "h1"] != ["Career opportunities", row["title"]]:
        raise SourceUnavailable("Marex detail title mismatch")
    expected_apply = "https://marex.breezy.hr/p/" + row["url"].rsplit("/", 1)[1]
    links = [n for n in nodes if n.tag == "a" and "Apply to this position" in clean(n)]
    if len(links) != 1 or links[0].attrs.get("href") != expected_apply:
        raise SourceUnavailable("Marex application identity mismatch")
    containers = [n for n in nodes if any(child is links[0] for child in n.children)]
    if len(containers) != 1:
        raise SourceUnavailable("Marex detail boundary missing")
    children = [c for c in containers[0].children if isinstance(c, Element)]
    if len(children) != 3 or [c.tag for c in children] != ["div", "div", "a"]:
        raise SourceUnavailable("Marex detail structure changed")
    header, body, _ = children
    if [clean(n) for n in header.walk() if n.tag == "h1"] != ["Career opportunities", row["title"]]:
        raise SourceUnavailable("Marex detail header missing")
    fields = [clean(n).rstrip(" ,") for n in header.walk() if n.tag == "p"]
    if fields != [row["location"], row["department"], row["employment"]]:
        raise SourceUnavailable("Marex card/detail metadata mismatch")
    description = description_html(body)
    if len(clean(Document(description).root)) < 100:
        raise SourceUnavailable("Marex full description missing")
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        apply_url=expected_apply,
        source_url=row["url"],
        location=row["location"],
        employment_type=row["employment"],
        description=description,
        date_posted=publication_date(row["published"]),
        raw_payload={"card": row},
    )


class MarexOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


class MarexCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH or config.tenant != "marex":
            raise ValueError("Use the verified Marex public careers catalogue and tenant")
        self.source, self.config, self.http = source, config, http
        self.options = MarexOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Marex scan time budget exceeded") from None

    async def listing(self) -> list[dict[str, str]]:
        text = await self.http.get_text(SEARCH, self.config.request_interval, self.source)
        return parse_listing(text, self.options.max_results_per_query)

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        rows = await self.listing()
        targets = [
            row
            for row in rows
            if (
                not self.options.title_terms
                or any(has(normalize_text(row["title"]), t) for t in self.options.title_terms)
            )
            and not any(
                has(normalize_text(row["title"]), t) for t in self.options.exclude_title_terms
            )
        ]
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Marex detail limit exceeded")
        jobs = []
        for row in targets:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        if await self.listing() != rows:
            raise SourceUnavailable("Marex catalogue changed during detail collection")
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
