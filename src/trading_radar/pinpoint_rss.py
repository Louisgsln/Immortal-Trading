"""The verified Wolverine feed, with full descriptions and bounded parsing."""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Literal

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, Element, clean
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

FEED = "https://careers.wolve.com/jobs.rss"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"


class PinpointOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)
    max_feed_bytes: Literal[2000000] = 2000000


def field(node: ET.Element, tag: str) -> str:
    matches = node.findall(tag)
    if len(matches) != 1 or len(matches[0]) or not (matches[0].text or "").strip():
        raise SourceUnavailable("Pinpoint feed field missing or ambiguous")
    return (matches[0].text or "").strip()


def metadata(content: str, title: str) -> tuple[str, str, str]:
    root = Document(content).root
    children = [n for n in root.children if isinstance(n, Element) or n.strip()]
    if len(children) < 5 or any(not isinstance(n, Element) for n in children[:4]):
        raise SourceUnavailable("Pinpoint job header missing")
    header = [n for n in children[:4] if isinstance(n, Element)]
    if [n.tag for n in header] != ["h1", "p", "p", "p"] or clean(header[0]) != title:
        raise SourceUnavailable("Pinpoint description identity mismatch")
    # Metadata is plain, visible publisher markup. Reject hidden or styled headers.
    if any(n.attrs or n.tag not in {"h1", "p", "strong"} for h in header for n in h.walk()):
        raise SourceUnavailable("Pinpoint job header is not plain visible metadata")
    values = []
    for node, label in zip(
        header[1:], ["Department:", "Employment Type:", "Location:"], strict=True
    ):
        nodes = [n for n in node.children if isinstance(n, Element) or n.strip()]
        if (
            len(nodes) != 2
            or not isinstance(nodes[0], Element)
            or nodes[0].tag != "strong"
            or clean(nodes[0]) != label
            or not isinstance(nodes[1], str)
            or not nodes[1].strip()
        ):
            raise SourceUnavailable("Pinpoint job metadata changed")
        values.append(nodes[1].strip())
    if values[1] not in {"Full Time", "Part Time", "Contract", "Internship"}:
        raise SourceUnavailable("Pinpoint employment type changed")
    return values[0], values[1], values[2]


def parse_feed(text: str, source: str, config: Company, options: PinpointOptions) -> list[RawJob]:
    if len(text.encode("utf-8")) > options.max_feed_bytes or re.search(
        r"<!\s*(?:DOCTYPE|ENTITY)", text, re.I
    ):
        raise SourceUnavailable("Pinpoint feed exceeds safe XML bounds")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise SourceUnavailable("Invalid Pinpoint XML feed") from None
    channels = root.findall("channel")
    if root.tag != "rss" or root.attrib != {"version": "2.0"} or len(channels) != 1:
        raise SourceUnavailable("Pinpoint RSS channel missing or ambiguous")
    channel = channels[0]
    # The publisher's channel/GUID alias is metadata only; never request that host.
    if (
        field(channel, "title") != "Careers at Wolverine"
        or field(channel, "link") != "https://wolve.wolve.com/jobs"
    ):
        raise SourceUnavailable("Pinpoint employer identity changed")
    items = channel.findall("item")
    if len(items) > options.max_results_per_query:
        raise SourceUnavailable("Pinpoint feed result limit exceeded")
    seen: set[str] = set()
    jobs = []
    for item in items:
        title, url = field(item, "title"), field(item, "link")
        match = re.fullmatch(r"https://careers\.wolve\.com/jobs/([1-9][0-9]*)", url)
        if not match or field(item, "guid") != f"https://wolve.wolve.com/jobs/{match[1]}":
            raise SourceUnavailable("Pinpoint job URL identity mismatch")
        external_id = match[1]
        if external_id in seen:
            raise SourceUnavailable("Duplicate Pinpoint job identity")
        seen.add(external_id)
        try:
            published = parsedate_to_datetime(field(item, "pubDate"))
            if published.tzinfo is None:
                raise ValueError
            published = published.astimezone(UTC)
        except (ValueError, TypeError, OverflowError):
            raise SourceUnavailable("Invalid Pinpoint publication timestamp") from None
        content = field(item, CONTENT)
        department, employment, location = metadata(content, title)
        normalized = normalize_text(title)
        if not any(has(normalized, term) for term in options.title_terms) or any(
            has(normalized, term) for term in options.exclude_title_terms
        ):
            continue
        jobs.append(
            RawJob(
                company=config.name,
                title=title,
                external_id=external_id,
                source=source,
                source_type="official",
                source_url=url,
                apply_url=url,
                description=content,
                location=location,
                employment_type=employment,
                date_posted=published,
                raw_payload={"department": department},
            )
        )
    if len(jobs) > options.max_details:
        raise SourceUnavailable("Pinpoint selected-job limit exceeded")
    return jobs


class PinpointRSSCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if (config.name, config.tenant, config.career_url) != (
            "Wolverine Trading",
            "wolve",
            "https://careers.wolve.com/",
        ):
            raise ValueError("Use the verified Wolverine Pinpoint feed")
        self.source, self.config, self.http = source, config, http
        self.options = PinpointOptions(**config.options)

    async def collect(self) -> Collection:
        before = self.http.counts[self.source]
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                text = await self.http.get_text(FEED, self.config.request_interval, self.source)
                jobs = parse_feed(text, self.source, self.config, self.options)
        except TimeoutError:
            raise SourceUnavailable("Pinpoint scan time budget exceeded") from None
        # RSS membership and title filters cannot establish that absent jobs closed.
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
