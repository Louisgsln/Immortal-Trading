"""Scotiabank's public SuccessFactors search and complete job descriptions."""

import asyncio
import html
import re
from datetime import datetime
from urllib.parse import unquote, urlencode, urljoin, urlsplit

from trading_radar.config import Company
from trading_radar.html_page import Document, Element, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason

ROOT = "https://jobs.scotiabank.com"
PAGE_SIZE = 25


def job_url(value: str) -> tuple[str, str]:
    url = urljoin(ROOT, value)
    parts = urlsplit(url)
    # The global search also publishes MD Wealth postings under this observed
    # subsidiary path. Validate their IDs before applying the same title scope.
    match = re.fullmatch(r"/(?:(?:MD|Tangerine|JFL)/)?job/[^/]+/(\d+)/", parts.path)
    if (
        parts.scheme != "https"
        or parts.netloc != "jobs.scotiabank.com"
        or parts.query
        or parts.fragment
        or not match
        or "\\" in unquote(parts.path)
        or any(p in {".", ".."} for p in unquote(parts.path).split("/"))
    ):
        raise SourceUnavailable("Scotiabank job URL identity invalid")
    return url, match[1]


def parse_page(text: str, term: str, offset: int, limit: int) -> tuple[list[dict], int]:
    nodes = list(Document(text).root.walk())
    queries = [
        n.attrs.get("value", "") for n in nodes if n.tag == "input" and n.attrs.get("name") == "q"
    ]
    labels = [clean(n) for n in with_class(nodes, "paginationLabel")]
    rows = with_class(nodes, "data-row")
    empty = [n for n in nodes if n.attrs.get("id") == "noresults-message"]
    if not queries or set(queries) != {term}:
        raise SourceUnavailable("Scotiabank search query changed")
    if not labels:
        if (
            offset == 0
            and not rows
            and len(empty) == 1
            and clean(empty[0]) == "Your search returned no results."
        ):
            return [], 0
        raise SourceUnavailable("Scotiabank result count missing")
    if empty or len(set(labels)) != 1:
        raise SourceUnavailable("Scotiabank conflicting result counts")
    match = re.fullmatch(r"Results (\d+)\s*[–-]\s*(\d+) of (\d+)", labels[0])
    if not match:
        raise SourceUnavailable("Scotiabank result count format changed")
    first, last, total = map(int, match.groups())
    if (
        not 0 < total <= limit
        or first != offset + 1
        or last != min(offset + PAGE_SIZE, total)
        or len(rows) != last - first + 1
    ):
        raise SourceUnavailable("Scotiabank catalogue incomplete or excessive")
    found = []
    for row in rows:
        identities = {
            (job_url(n.attrs.get("href", "")), clean(n))
            for n in with_class(row.walk(), "jobTitle-link")
        }
        cells = {}
        for n in row.walk():
            if n.tag == "td" and n.attrs.get("headers") in {"hdrDate", "hdrLocation"}:
                key = n.attrs["headers"]
                if key in cells:
                    raise SourceUnavailable("Scotiabank listing metadata ambiguous")
                cells[key] = clean(n)
        if len(identities) != 1 or not cells.get("hdrLocation") or not cells.get("hdrDate"):
            raise SourceUnavailable("Scotiabank listing incomplete")
        (url, identifier), title = identities.pop()
        if not title:
            raise SourceUnavailable("Scotiabank listing title missing")
        try:
            posted = datetime.strptime(cells["hdrDate"], "%b %d, %Y").date()
        except ValueError:
            raise SourceUnavailable("Scotiabank posting calendar date invalid") from None
        found.append(
            dict(
                id=identifier,
                url=url,
                title=title,
                location=cells["hdrLocation"],
                posted=posted.isoformat(),
            )
        )
    if len({row["id"] for row in found}) != len(found):
        raise SourceUnavailable("Scotiabank repeated posting")
    return found, total


def markup(node: Element | str) -> str:
    if isinstance(node, str):
        return html.escape(node)
    if (
        node.tag in {"script", "style"}
        or "hidden" in node.attrs
        or node.attrs.get("aria-hidden") == "true"
    ):
        return ""
    children = "".join(markup(child) for child in node.children)
    if node.tag == "br":
        return "<br>"
    if node.tag in {"p", "div", "h2", "h3", "h4", "ul", "ol", "li", "strong", "b", "em"}:
        return "<" + node.tag + ">" + children + "</" + node.tag + ">"
    return children


def detail(text: str, row: dict, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    titles = [clean(n).removeprefix("Title: ").strip() for n in nodes if n.tag == "h1"]
    bodies = with_class(nodes, "jobdescription")
    if titles != [row["title"]] or len(bodies) != 1:
        raise SourceUnavailable("Scotiabank listing and detail identity changed")
    body = markup(bodies[0])
    visible = clean(Document(body).root)
    references = re.findall(r"\bRequisition ID:\s*(\d+)\b", visible)
    if len(references) != 1 or len(visible) < 200 or "Scotiabank" not in visible:
        raise SourceUnavailable("Scotiabank full employer description missing")
    return RawJob(
        company="Scotiabank",
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        apply_url=row["url"],
        source_url=row["url"],
        location=row["location"],
        description=body,
        publication_day=datetime.fromisoformat(row["posted"]).date(),
        raw_payload={"listing": row, "requisition_id": references[0]},
    )


class ScotiabankCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.name != "Scotiabank" or config.career_url != ROOT + "/" or config.tenant:
            raise ValueError("Use the verified Scotiabank public career site")
        self.source, self.config, self.http = source, config, http
        self.options = SearchOptions(**config.options)

    async def search(self, term: str, offset: int) -> str:
        return await self.http.get_text(
            ROOT
            + "/search/?"
            + urlencode(
                dict(q=term, sortColumn="referencedate", sortDirection="desc", startrow=offset)
            ),
            self.config.request_interval,
            self.source,
        )

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Scotiabank scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        candidates: dict[str, dict] = {}
        for term in self.options.search_terms:
            first, total = parse_page(
                await self.search(term, 0), term, 0, self.options.max_results_per_query
            )
            collected = {r["id"]: r for r in first}
            for offset in range(PAGE_SIZE, total, PAGE_SIZE):
                rows, count = parse_page(
                    await self.search(term, offset),
                    term,
                    offset,
                    self.options.max_results_per_query,
                )
                if count != total or any(r["id"] in collected for r in rows):
                    raise SourceUnavailable("Scotiabank pagination changed or repeated")
                collected.update({r["id"]: r for r in rows})
            check, count = parse_page(
                await self.search(term, 0), term, 0, self.options.max_results_per_query
            )
            if (
                count != total
                or sorted(first, key=lambda r: r["id"]) != sorted(check, key=lambda r: r["id"])
                or len(collected) != total
            ):
                raise SourceUnavailable("Scotiabank catalogue changed during pagination")
            for key, row in collected.items():
                if key in candidates and candidates[key] != row:
                    raise SourceUnavailable("Scotiabank posting changed between queries")
                candidates[key] = row
        audit = SelectionAudit("search_results")
        selected = []
        for row in candidates.values():
            reason = rejection_reason(row["title"], self.options)
            audit.record(reason, row["title"], row["id"])
            if reason is None:
                selected.append(row)
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("Scotiabank detail limit exceeded")
        jobs = []
        for row in selected:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(detail(text, row, self.source))
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
