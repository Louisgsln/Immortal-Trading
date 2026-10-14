"""CFM's public SuccessFactors tile catalogue and employer-owned details."""

import asyncio
import re
from urllib.parse import unquote, urlencode, urljoin, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.description_sections import normalize_heading, visible_text
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.scotiabank import markup
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason

ROOT = "https://jobs.cfm.com"
PAGE_SIZE = 25


class CFMOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def job_url(value: str) -> tuple[str, str]:
    url = urljoin(ROOT, value)
    p = urlsplit(url)
    m = re.fullmatch(r"/job/[^/]+/([1-9]\d*)/", p.path)
    if (
        p.scheme != "https"
        or p.netloc != "jobs.cfm.com"
        or not m
        or p.query
        or p.fragment
        or "\\" in unquote(p.path)
        or any(s in {".", ".."} for s in unquote(p.path).split("/"))
    ):
        raise SourceUnavailable("CFM posting URL identity invalid")
    return url, m[1]


def listing(text: str, offset: int, limit: int) -> tuple[list[dict], int]:
    nodes = list(Document(text).root.walk())
    queries = [
        n.attrs.get("value", "") for n in nodes if n.tag == "input" and n.attrs.get("name") == "q"
    ]
    if not queries or set(queries) != {""}:
        raise SourceUnavailable("CFM public catalogue query changed")
    roots = [n for n in nodes if n.attrs.get("id") == "job-tile-list"]
    empty = [n for n in nodes if n.attrs.get("id") == "noresults-message"]
    # The employer publishes an explicit zero count; a blank/challenge page is
    # never evidence of an empty catalogue.
    if not roots:
        if (
            offset == 0
            and len(empty) == 1
            and clean(empty[0])
            == (
                "The 0 most recent jobs posted by Capital Fund Management are listed below for your convenience."
            )
        ):
            return [], 0
        raise SourceUnavailable("CFM catalogue or explicit zero count missing")
    labels = {clean(n) for n in nodes if re.fullmatch(r"Showing \d+ to \d+ of \d+ Jobs", clean(n))}
    if len(roots) != 1 or empty or len(labels) != 1:
        raise SourceUnavailable("CFM catalogue counts ambiguous")
    label = re.fullmatch(r"Showing (\d+) to (\d+) of (\d+) Jobs", labels.pop())
    assert label is not None
    first, last, total = map(int, label.groups())
    root = roots[0]
    rows = [n for n in with_class(root.walk(), "job-tile") if n.tag == "li"]
    if (
        not 0 < total <= limit
        or first != offset + 1
        or last != min(offset + PAGE_SIZE, total)
        or len(rows) != last - first + 1
        or root.attrs.get("data-per-page") != str(PAGE_SIZE)
        or root.attrs.get("data-record-returned") != str(len(rows))
    ):
        raise SourceUnavailable("CFM catalogue incomplete or excessive")
    result = []
    seen = set()
    for row in rows:
        url, identifier = job_url(row.attrs.get("data-url", ""))
        identities = {
            (job_url(n.attrs.get("href", "")), clean(n))
            for n in with_class(row.walk(), "jobTitle-link")
        }
        if len(identities) != 1 or identifier in seen:
            raise SourceUnavailable("CFM catalogue identity mismatch or duplicate")
        (linked_url, linked_id), title = identities.pop()
        if linked_url != url or linked_id != identifier or not title:
            raise SourceUnavailable("CFM catalogue title or URL changed")
        places = [
            clean(n)
            for n in row.walk()
            if n.attrs.get("id") == f"job-{identifier}-desktop-section-location-value"
        ]
        departments = [
            clean(n)
            for n in row.walk()
            if n.attrs.get("id") == f"job-{identifier}-desktop-section-dept-value"
        ]
        if len(places) != 1 or not places[0] or len(departments) != 1 or not departments[0]:
            raise SourceUnavailable("CFM location or department missing")
        seen.add(identifier)
        result.append(
            dict(id=identifier, url=url, title=title, location=places[0], department=departments[0])
        )
    return result, total


def detail(text: str, row: dict, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    titles = [clean(n) for n in nodes if n.tag == "h1"]
    canonicals = [
        n.attrs.get("href") for n in nodes if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    bodies = with_class(nodes, "jobdescription")
    if titles != [row["title"]] or canonicals != [row["url"]] or len(bodies) != 1:
        raise SourceUnavailable("CFM listing and detail identity changed")
    # CFM publishes both heading-based and bold paragraph section labels.
    # Check sanitized visible markup so hidden labels cannot validate a stub.
    description = markup(bodies[0])
    body = Document(description).root
    visible = normalize_heading(visible_text(body))
    labels = {
        normalize_heading(visible_text(n))
        for n in body.walk()
        if n.tag in {"h2", "h3", "h4", "p", "strong", "b"}
    }
    roles = labels & {"your role", "about the role"}
    requirements = labels & {
        "your skills",
        "qualifications / required skills",
        "skillset requirements/qualifications",
    }
    if not visible.startswith("about cfm ") or len(roles) != 1 or len(requirements) != 1:
        raise SourceUnavailable("CFM full employer description missing")
    role, skills = roles.pop(), requirements.pop()
    start = visible.index(role) + len(role)
    end = visible.index(skills)
    following = visible[end + len(skills) :]
    following = re.split(r"\bequal opportunities statement\b|\bfollow us\b", following)[0]
    if end <= start or len(visible[start:end].strip()) < 80 or len(following.strip()) < 40:
        raise SourceUnavailable("CFM role or requirements section incomplete")
    return RawJob(
        company="Capital Fund Management",
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        apply_url=row["url"],
        source_url=row["url"],
        location=row["location"],
        description=description,
        raw_payload={"listing": row},
    )


class CFMCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if (
            config.name != "Capital Fund Management"
            or config.career_url != ROOT + "/"
            or config.tenant
        ):
            raise ValueError("Use the verified CFM public recruitment site")
        self.source, self.config, self.http = source, config, http
        self.options = CFMOptions(**config.options)

    async def page(self, offset: int) -> str:
        return await self.http.get_text(
            ROOT
            + "/search/?"
            + urlencode(
                dict(
                    q="",
                    sortColumn="referencedate",
                    sortDirection="desc",
                    startrow=offset,
                    locale="en_US",
                )
            ),
            self.config.request_interval,
            self.source,
        )

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("CFM scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        first, total = listing(await self.page(0), 0, self.options.max_results_per_query)
        candidates = {r["id"]: r for r in first}
        for offset in range(PAGE_SIZE, total, PAGE_SIZE):
            rows, count = listing(
                await self.page(offset), offset, self.options.max_results_per_query
            )
            if count != total or any(r["id"] in candidates for r in rows):
                raise SourceUnavailable("CFM pagination changed or repeated")
            candidates.update({r["id"]: r for r in rows})
        if len(candidates) != total:
            raise SourceUnavailable("CFM catalogue incomplete")
        audit = SelectionAudit("public_catalogue")
        selected = []
        for row in candidates.values():
            reason = rejection_reason(row["title"], self.options)
            audit.record(reason, row["title"], row["id"])
            if reason is None:
                selected.append(row)
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("CFM detail limit exceeded")
        jobs = []
        for row in selected:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(detail(text, row, self.source))
        check, count = listing(await self.page(0), 0, self.options.max_results_per_query)
        if count != total or sorted(first, key=lambda r: r["id"]) != sorted(
            check, key=lambda r: r["id"]
        ):
            raise SourceUnavailable("CFM catalogue changed during collection")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
