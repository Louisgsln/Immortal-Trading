"""ENGIE's public sitemap and job pages, without its robots-disallowed search API."""

import asyncio
import re
from datetime import date
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.optiver_sections import description_html
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://jobs.engie.com"
SEARCH = ORIGIN + "/sitemap.xml"
_PATH = re.compile(r"/job/[^/]+/(\d+)(?:-([a-z]{2}_[A-Z]{2}))?/")


def allowed_job_url(url: str) -> bool:
    parts = urlsplit(url)
    decoded = unquote(parts.path)
    return bool(
        (parts.scheme, parts.netloc) == ("https", "jobs.engie.com")
        and not parts.query
        and not parts.fragment
        and _PATH.fullmatch(parts.path)
        and _PATH.fullmatch(decoded)
        and "\\" not in decoded
        and not any(ord(c) < 32 for c in decoded)
        and not any(p in {".", ".."} for p in decoded.split("/"))
    )


def parse_sitemap(text: str, limit: int) -> list[str]:
    if len(text) > 2_000_000 or re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.I):
        raise SourceUnavailable("unsafe or oversized ENGIE sitemap")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        raise SourceUnavailable("invalid ENGIE sitemap") from None
    namespace = root.tag.removesuffix("urlset")
    if (
        namespace
        not in {
            "{http://www.google.com/schemas/sitemap/0.9}",
            "{http://www.sitemaps.org/schemas/sitemap/0.9}",
        }
        or root.tag != namespace + "urlset"
        or not 1 <= len(root) <= limit
    ):
        raise SourceUnavailable("ENGIE sitemap identity or bounded count missing")
    urls = []
    seen = set()
    for row in root:
        locs = row.findall(namespace + "loc")
        if row.tag != namespace + "url" or len(locs) != 1 or not locs[0].text:
            raise SourceUnavailable("ENGIE sitemap location missing")
        url = locs[0].text
        parts = urlsplit(url)
        if (
            (parts.scheme, parts.netloc) != ("https", "jobs.engie.com")
            or parts.query
            or parts.fragment
            or url in seen
        ):
            raise SourceUnavailable("ENGIE sitemap foreign or duplicate URL")
        seen.add(url)
        if parts.path.startswith("/job/"):
            if not allowed_job_url(url):
                raise SourceUnavailable("invalid ENGIE sitemap job URL")
            urls.append(url)
        # Branded subboards such as /grdf/job/ are outside this trading scope.
    if not urls:
        raise SourceUnavailable("ENGIE sitemap contains no job pages")
    return sorted(urls)


def parse_detail(text: str, url: str, config: Company, source: str) -> RawJob:
    match = _PATH.fullmatch(urlsplit(url).path) if allowed_job_url(url) else None
    if not match or match[2] != "en_US":
        raise SourceUnavailable("ENGIE detail language or identity unsupported")
    ident = match[1]
    nodes = list(Document(text).root.walk())
    canonical = [n.attrs.get("href", "") for n in nodes if n.attrs.get("rel") == "canonical"]
    if (
        len(canonical) != 1
        or not allowed_job_url(canonical[0])
        or urlsplit(canonical[0]).path.rsplit("/", 2)[1] != ident + "-en_US"
    ):
        raise SourceUnavailable("ENGIE canonical identifier mismatch")
    shells = with_class(nodes, "jobDisplayShell")
    if len(shells) != 1 or shells[0].attrs.get("itemtype") != "http://schema.org/JobPosting":
        raise SourceUnavailable("ENGIE job page missing")
    nodes = list(shells[0].walk())
    tokens = with_class(nodes, "joblayouttoken")
    values = [clean(n) for n in tokens]
    titles = [clean(n) for n in nodes if n.attrs.get("itemprop") == "title"]
    if (
        len(tokens) != 18
        or titles != [values[0]]
        or not values[0]
        or values[2] != "Requisition ID: " + ident
        or not values[1].startswith("Posting Start Date: ")
    ):
        raise SourceUnavailable("ENGIE detail layout or requisition mismatch")
    if (
        not all(values[i] for i in range(3, 8))
        or values[8]
        or values[10]
        or not values[11].startswith("Business Unit: ")
        or values[13] != "Legal Entity: " + values[4]
    ):
        raise SourceUnavailable("ENGIE detail metadata boundaries changed")
    dates = re.fullmatch(r"Posting Start Date: (\d{1,2})/(\d{1,2})/(\d{2})", values[1])
    try:
        published = date(2000 + int(dates[3]), int(dates[1]), int(dates[2])) if dates else None
    except ValueError:
        raise SourceUnavailable("invalid ENGIE publication day") from None
    if published is None:
        raise SourceUnavailable("ENGIE publication day missing")
    descriptions = [
        n for n in tokens[9].walk() if n.tag == "span" and n.attrs.get("lang") == "en-US"
    ]
    if len(descriptions) != 1 or len(clean(descriptions[0])) < 100:
        raise SourceUnavailable("ENGIE full description missing")
    expected_apply = f"/talentcommunity/apply/{ident}/?locale=en_US"
    links = [n.attrs.get("href") for n in with_class(nodes, "unify-apply-now")]
    if not links or any(link != expected_apply for link in links):
        raise SourceUnavailable("ENGIE application identifier mismatch")
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=ident,
        title=values[0],
        source_url=canonical[0],
        apply_url=canonical[0],
        location=values[3],
        employment_type=values[6] + " / " + values[7],
        description=description_html(descriptions[0]),
        publication_day=published,
        raw_payload={
            "legal_entity": values[4],
            "department": values[5],
            "publication_label": values[1],
        },
    )


class EngieOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)
    max_results_per_query: int = Field(default=5000, ge=1, le=10000)


class EngieCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH or config.tenant != "engie":
            raise ValueError("Use the verified ENGIE public sitemap and tenant")
        self.source, self.config, self.http = source, config, http
        self.options = EngieOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("ENGIE scan time budget exceeded") from None

    async def listing(self) -> list[str]:
        text = await self.http.get_text(SEARCH, self.config.request_interval, self.source)
        return parse_sitemap(text, self.options.max_results_per_query)

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        urls = await self.listing()
        targets = []
        for url in urls:
            title = normalize_text(unquote(urlsplit(url).path.split("/")[2]))
            if any(has(title, t) for t in self.options.title_terms) and not any(
                has(title, t) for t in self.options.exclude_title_terms
            ):
                targets.append(url)
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("ENGIE detail limit exceeded")
        jobs: dict[str, RawJob] = {}
        for url in targets:
            resolved, text = await self.http.get_career_page(
                url, self.config.request_interval, self.source, allowed_job_url
            )
            locale = _PATH.fullmatch(urlsplit(resolved).path)
            if not locale or not locale[2]:
                raise SourceUnavailable("ENGIE migrated vacancy identifier missing")
            if locale[2] != "en_US":
                continue  # Translation variants are not additional vacancies.
            job = parse_detail(text, resolved, self.config, self.source)
            title = normalize_text(job.title)
            if not any(has(title, t) for t in self.options.title_terms) or any(
                has(title, t) for t in self.options.exclude_title_terms
            ):
                continue  # Recheck the actual title, not just its sitemap slug.
            if locale[1] in jobs and jobs[locale[1]] != job:
                raise SourceUnavailable("conflicting ENGIE vacancy translations")
            jobs[locale[1]] = job
        if await self.listing() != urls:
            raise SourceUnavailable("ENGIE sitemap changed during collection")
        return Collection(
            jobs=list(jobs.values()),
            complete=False,
            requests=self.http.counts[self.source] - before,
        )
