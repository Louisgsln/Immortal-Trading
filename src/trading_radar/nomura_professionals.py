"""Nomura's public SuccessFactors search, separate from its campus board."""

import asyncio
import html
import re
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlencode, urljoin, urlsplit

from trading_radar.config import Company
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

ROOT = "https://careers.nomura.com"
BOARD = ROOT + "/Nomura?locale=en_US"
SEARCH = ROOT + "/Nomura/search/"
PAGE_SIZE = 100


def job_url(value: str) -> tuple[str, str]:
    url = urljoin(ROOT, value)
    parts = urlsplit(url)
    match = re.fullmatch(r"/Nomura/job/[^/]+/(\d+)/", parts.path)
    if (
        parts.scheme != "https"
        or parts.netloc != "careers.nomura.com"
        or parts.query
        or parts.fragment
        or not match
    ):
        raise SourceUnavailable("invalid Nomura professional job URL")
    return url, match[1]


def parse_page(text: str, term: str, offset: int, limit: int) -> tuple[list[dict], int]:
    nodes = list(Document(text).root.walk())
    queries = [
        n.attrs.get("value", "") for n in nodes if n.tag == "input" and n.attrs.get("name") == "q"
    ]
    if not queries or set(queries) != {term}:
        raise SourceUnavailable("Nomura professional search query changed")
    labels = [clean(n) for n in with_class(nodes, "paginationLabel")]
    empty = [n for n in nodes if n.attrs.get("id") == "noresults-message"]
    rows = with_class(nodes, "data-row")
    if not labels:
        if (
            offset == 0
            and not rows
            and len(empty) == 1
            and clean(empty[0]) == "Your search returned no results."
        ):
            return [], 0
        raise SourceUnavailable("Nomura professional result count missing")
    if empty or len(set(labels)) != 1:
        raise SourceUnavailable("Nomura professional conflicting result counts")
    match = re.fullmatch(r"Results (\d+)\s*[–-]\s*(\d+) of (\d+)", labels[0])
    if not match:
        raise SourceUnavailable("Nomura professional pagination format changed")
    first, last, total = map(int, match.groups())
    if (
        not 0 < total <= limit
        or first != offset + 1
        or last != min(offset + PAGE_SIZE, total)
        or len(rows) != last - first + 1
    ):
        raise SourceUnavailable("Nomura professional incomplete or excessive page")
    found = []
    for row in rows:
        links = with_class(row.walk(), "jobTitle-link")
        identities = {(job_url(n.attrs.get("href", "")), clean(n)) for n in links}
        cells = {}
        for n in row.walk():
            if n.tag == "td" and n.attrs.get("headers") in {"hdrFacility", "hdrLocation"}:
                key = n.attrs["headers"]
                if key in cells:
                    raise SourceUnavailable("Nomura professional ambiguous listing metadata")
                cells[key] = clean(n)
        if len(identities) != 1 or not cells.get("hdrFacility") or not cells.get("hdrLocation"):
            raise SourceUnavailable("Nomura professional listing incomplete or ambiguous")
        (url, identifier), title = identities.pop()
        if not title:
            raise SourceUnavailable("Nomura professional title missing")
        found.append(
            dict(
                id=identifier,
                url=url,
                title=title,
                division=cells["hdrFacility"],
                location=cells["hdrLocation"],
            )
        )
    if len({r["id"] for r in found}) != len(found):
        raise SourceUnavailable("Nomura professional repeated listing")
    return found, total


GRADES = r"Assistant Vice President|Associate Vice President|Vice President|Executive Director|Managing Director|Director|Analyst|Associate|AVP|VP|ED|MD"


def role_metadata(text: str) -> tuple[dict, Literal["junior", "senior"] | None, int | None]:
    grades = re.findall(
        rf"\bCorporate Title\s*:?\s*((?:{GRADES})(?:\s*/\s*(?:{GRADES}))*)\b",
        text,
        re.IGNORECASE,
    )
    grade_text = normalize_text(" / ".join(grades))
    seniority: Literal["junior", "senior"] | None = None
    if any(has(grade_text, t) for t in ["vice president", "director", "avp", "vp", "ed", "md"]):
        seniority = "senior"
    elif has(grade_text, "analyst"):
        seniority = "junior"
    years = re.findall(
        r"\bExperience\s*:?\s*(\d+)\s*(?:[-–—]\s*\d+|\+)?\s*years?\b", text, re.IGNORECASE
    )
    minimum = max(map(int, years)) if years else None
    return {"corporate_titles": grades, "experience_minima": years}, seniority, minimum


def posted_date(value: str) -> datetime:
    if not re.fullmatch(r"[A-Za-z]{3} [A-Za-z]{3} \d{2} \d{2}:\d{2}:\d{2} UTC \d{4}", value):
        raise SourceUnavailable("Nomura publication lacks expected UTC format")
    try:
        return datetime.strptime(value, "%a %b %d %H:%M:%S UTC %Y").replace(tzinfo=UTC)
    except ValueError:
        raise SourceUnavailable("invalid Nomura publication date") from None


def parse_detail(text: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    canonical = [
        n.attrs.get("href", "")
        for n in nodes
        if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    if len(canonical) != 1 or job_url(canonical[0])[1] != row["id"]:
        raise SourceUnavailable("Nomura professional detail identity mismatch")
    shells = with_class(nodes, "jobDisplayShell")
    if len(shells) != 1 or not shells[0].attrs.get("itemtype", "").endswith("/JobPosting"):
        raise SourceUnavailable("Nomura professional JobPosting missing")
    nodes = list(shells[0].walk())
    props = {}
    for node in nodes:
        key = node.attrs.get("itemprop")
        if key in {"title", "datePosted", "validThrough", "hiringOrganization"}:
            if key in props:
                raise SourceUnavailable("Nomura professional duplicate detail metadata")
            props[key] = node.attrs.get("content") or clean(node)
    descriptions = with_class(nodes, "jobdescription")
    if (
        props.get("title") != row["title"]
        or props.get("hiringOrganization") != "Nomura Holdings, inc."
        or not props.get("datePosted")
        or len(descriptions) != 1
        or not clean(descriptions[0])
    ):
        raise SourceUnavailable("Nomura professional title, employer or description missing")
    addresses = [n for n in nodes if n.attrs.get("itemprop") == "address"]
    if not addresses or not all(
        any(
            n.attrs.get("itemprop") in {"streetAddress", "addressLocality"}
            and n.attrs.get("content", "").strip()
            for n in address.walk()
        )
        for address in addresses
    ):
        raise SourceUnavailable("Nomura professional address missing")
    apply_links = [
        n.attrs.get("href", "")
        for n in nodes
        if n.tag == "a" and "apply" in n.attrs.get("class", "").split()
    ]
    if not apply_links or any(
        urlsplit(urljoin(ROOT, link)).netloc != "careers.nomura.com"
        or urlsplit(urljoin(ROOT, link)).scheme != "https"
        or urlsplit(link).path != f"/talentcommunity/apply/{row['id']}/"
        for link in apply_links
    ):
        raise SourceUnavailable("Nomura professional application identity missing or changed")
    description = clean(descriptions[0])
    evidence, seniority, years = role_metadata(description)
    contract = re.search(
        r"\bJob Title\s*:\s*[^.\[\]]{0,150}\[(\d+[- ]month Fixed Term Contract)\]",
        description,
        re.IGNORECASE,
    )
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        apply_url=job_url(canonical[0])[0],
        source_url=row["url"],
        location=row["location"],
        description="<p>" + html.escape(description) + "</p>",
        date_posted=posted_date(props["datePosted"]),
        seniority_hint=seniority,
        minimum_experience_years=years,
        employment_type=contract[1] if contract else None,
        # validThrough is publication expiry, not a confirmed candidate deadline.
        raw_payload={"division": row["division"], "metadata": props, **evidence},
    )


class NomuraProfessionalsCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.name != "Nomura" or config.career_url != BOARD:
            raise ValueError("Use the verified Nomura professional portal")
        self.source, self.config, self.http = source, config, http
        self.options = SearchOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Nomura professional scan time budget exceeded") from None

    async def page(self, term: str, offset: int) -> tuple[list[dict], int]:
        query = urlencode({"q": term, "startrow": offset})
        text = await self.http.get_text(
            SEARCH + "?" + query, self.config.request_interval, self.source
        )
        return parse_page(text, term, offset, self.options.max_results_per_query)

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        found: dict[str, dict] = {}
        for term in self.options.search_terms:
            initial, total = await self.page(term, 0)
            rows = {r["id"]: r for r in initial}
            while len(rows) < total:
                batch, current = await self.page(term, len(rows))
                if current != total:
                    raise SourceUnavailable("Nomura professional total changed")
                for row in batch:
                    if row["id"] in rows:
                        raise SourceUnavailable("Nomura professional repeated page")
                    rows[row["id"]] = row
            if await self.page(term, 0) != (initial, total):
                raise SourceUnavailable("Nomura professional catalogue changed during pagination")
            for identifier, row in rows.items():
                if identifier in found and found[identifier] != row:
                    raise SourceUnavailable("Nomura professional conflicting search results")
                found[identifier] = row
        targets = []
        for row in found.values():
            if row["division"] == "Operations":
                continue
            title = normalize_text(row["title"])
            if (
                not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
            ) and not any(has(title, t) for t in self.options.exclude_title_terms):
                targets.append(row)
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Nomura professional detail limit exceeded")
        jobs = []
        for row in targets:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
