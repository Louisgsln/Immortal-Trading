"""Optiver's public website API and server-rendered vacancy descriptions."""

import asyncio
import html
import json
import re
from urllib.parse import urlencode, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, Element, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://www.optiver.com"
SEARCH = ORIGIN + "/join-us/jobs"
API = ORIGIN + "/en/api/v1/jobs"
PAGE_SIZE = 16


def job_url(value: str) -> str:
    parts = urlsplit(value)
    if (
        (parts.scheme or parts.netloc)
        and (parts.scheme, parts.netloc) != ("https", "www.optiver.com")
        or parts.query
        or parts.fragment
        or not re.fullmatch(r"/join-us/jobs/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+/", parts.path)
    ):
        raise SourceUnavailable("invalid Optiver vacancy URL")
    return ORIGIN + parts.path


def parse_page(payload: object, offset: int, limit: int) -> tuple[list[dict], int]:
    if not isinstance(payload, dict):
        raise SourceUnavailable("invalid Optiver response")
    total, rows = payload.get("totalCount"), payload.get("items")
    if (
        type(total) is not int
        or not 0 <= total <= limit
        or not isinstance(rows, list)
        or len(rows) != min(PAGE_SIZE, max(0, total - offset))
    ):
        raise SourceUnavailable("Optiver result count missing, excessive or incomplete")
    result = []
    for row in rows:
        if not isinstance(row, dict) or any(
            not isinstance(row.get(k), str) or not row[k].strip()
            for k in ("title", "location", "experience", "domain", "href")
        ):
            raise SourceUnavailable("incomplete Optiver vacancy card")
        if type(row.get("componentID")) is not int or row["componentID"] <= 0:
            raise SourceUnavailable("missing Optiver card identifier")
        if row["experience"] not in {"Experienced", "Graduate", "Early Careers", "Internship"}:
            raise SourceUnavailable("unknown Optiver experience level")
        result.append({**row, "title": row["title"].strip(), "url": job_url(row["href"])})
    return result, total


def parse_detail(text: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    titles = [clean(n) for n in nodes if n.tag == "h1"]
    identifiers = [
        n.attrs.get("content", "")
        for n in nodes
        if n.tag == "meta" and n.attrs.get("name") == "jobid"
    ]
    canonical = [
        n.attrs.get("href", "")
        for n in nodes
        if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    if (
        titles != [row["title"]]
        or len(identifiers) != 1
        or not re.fullmatch(r"[0-9]+", identifiers[0])
    ):
        raise SourceUnavailable("Optiver detail title or job identifier missing")
    if len(canonical) != 1 or job_url(canonical[0]) != row["url"]:
        raise SourceUnavailable("Optiver detail canonical URL mismatch")
    postings = []
    for n in nodes:
        if n.tag == "script" and n.attrs.get("type") == "application/ld+json":
            try:
                item = json.loads(n.text())
            except ValueError:
                raise SourceUnavailable("invalid Optiver structured metadata") from None
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                postings.append(item)
    if len(postings) != 1:
        raise SourceUnavailable("Optiver JobPosting metadata missing")
    posting = postings[0]
    if (
        posting.get("title", "").strip() != row["title"]
        or not isinstance(posting.get("url"), str)
        or job_url(posting["url"]) != row["url"]
        or posting.get("hiringOrganization", {}).get("name") != "Optiver"
        or posting.get("jobLocation", {}).get("name") != row["location"]
    ):
        raise SourceUnavailable("Optiver structured identity mismatch")
    fields = {}
    for n in nodes:
        children = [c for c in n.children if isinstance(c, Element)]
        if len(children) == 2 and all(c.tag == "p" for c in children):
            label, value = map(clean, children)
            if label in {"Level", "Location", "Department"}:
                if label in fields:
                    raise SourceUnavailable("duplicate Optiver detail metadata")
                fields[label] = value
    if fields != {
        "Level": row["experience"],
        "Location": row["location"],
        "Department": row["domain"],
    }:
        raise SourceUnavailable("Optiver card/detail metadata mismatch")
    descriptions = with_class(nodes, "rich-text-section")
    if len(descriptions) != 1 or not clean(descriptions[0]):
        raise SourceUnavailable("Optiver full description missing")
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=identifiers[0],
        title=row["title"],
        apply_url=row["url"],
        source_url=row["url"],
        location=row["location"],
        description="<p>" + html.escape(clean(descriptions[0])) + "</p>",
        employment_type="Internship" if row["experience"] == "Internship" else None,
        seniority_hint="junior" if row["experience"] in {"Graduate", "Early Careers"} else None,
        # Date-only publication metadata and dates inside prose remain evidence, not invented UTC instants.
        raw_payload={"card": row, "metadata": posting},
    )


class OptiverOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


class OptiverCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH:
            raise ValueError("Use the verified Optiver public careers URL")
        self.source, self.config, self.http = source, config, http
        self.options = OptiverOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Optiver scan time budget exceeded") from None

    async def page(self, offset: int) -> tuple[list[dict], int]:
        payload = await self.http.get_json(
            API + "?" + urlencode({"from": offset, "size": PAGE_SIZE}),
            self.config.request_interval,
            self.source,
        )
        return parse_page(payload, offset, self.options.max_results_per_query)

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        rows, total = await self.page(0)
        first = list(rows)
        while len(rows) < total:
            page, page_total = await self.page(len(rows))
            if page_total != total:
                raise SourceUnavailable("Optiver total changed during pagination")
            rows.extend(page)
        if len({r["componentID"] for r in rows}) != total or len({r["url"] for r in rows}) != total:
            raise SourceUnavailable("Optiver duplicate cards or repeated page")
        # Detect a shifting newest-first listing before fetching details.
        check, check_total = await self.page(0)
        if check_total != total or check != first:
            raise SourceUnavailable("Optiver board changed during pagination")
        targets = [
            r
            for r in rows
            if (
                not self.options.title_terms
                or any(has(normalize_text(r["title"]), t) for t in self.options.title_terms)
            )
            and not any(
                has(normalize_text(r["title"]), t) for t in self.options.exclude_title_terms
            )
        ]
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Optiver detail limit exceeded")
        jobs = []
        for row in targets:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        if len({j.external_id for j in jobs}) != len(jobs):
            raise SourceUnavailable("Optiver duplicate vacancy identifier")
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
