"""Audited bank SuccessFactors tables; full public details, no absence closures."""

import asyncio
import re
from urllib.parse import unquote, urlencode, urljoin, urlsplit

from trading_radar.config import Company
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.scotiabank import markup
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason

SITES = {
    "SMBC": ("https://careersemea.smbcgroup.com", "en_GB", "SMBC"),
    "Nordea": ("https://careers.nordea.com", "en_US", "Nordea"),
}
PAGE_SIZE = 25


def job_url(value: str, root: str) -> tuple[str, str]:
    url = urljoin(root, value)
    p = urlsplit(url)
    m = re.fullmatch(r"/job/[^/]+/([1-9]\d*)/", p.path)
    decoded = unquote(unquote(p.path))
    if (
        p.scheme != "https"
        or p.netloc != urlsplit(root).netloc
        or not m
        or p.query
        or p.fragment
        or "\\" in decoded
        or any(s in {".", ".."} for s in decoded.split("/"))
    ):
        raise SourceUnavailable("SuccessFactors posting URL identity invalid")
    return url, m[1]


def listing(text: str, term: str, offset: int, limit: int, root: str) -> tuple[list[dict], int]:
    nodes = list(Document(text).root.walk())
    queries = [
        n.attrs.get("value", "") for n in nodes if n.tag == "input" and n.attrs.get("name") == "q"
    ]
    labels = [clean(n) for n in with_class(nodes, "paginationLabel")]
    rows = with_class(nodes, "data-row")
    empty = [n for n in nodes if n.attrs.get("id") == "noresults-message"]
    if not queries or set(queries) != {term}:
        raise SourceUnavailable("SuccessFactors search query changed")
    if not labels:
        if (
            offset == 0
            and not rows
            and len(empty) == 1
            and clean(empty[0]) == "Your search returned no results."
        ):
            return [], 0
        raise SourceUnavailable("SuccessFactors result count missing")
    if empty or len(set(labels)) != 1:
        raise SourceUnavailable("SuccessFactors result counts ambiguous")
    m = re.fullmatch(r"Results (\d+)\s*[–-]\s*(\d+) of (\d+)", labels[0])
    if not m:
        raise SourceUnavailable("SuccessFactors result count format changed")
    first, last, total = map(int, m.groups())
    if (
        not 0 < total <= limit
        or first != offset + 1
        or last != (total if root == SITES["Nordea"][0] else min(offset + PAGE_SIZE, total))
        or (root == SITES["Nordea"][0] and offset != 0)
        or len(rows) != last - first + 1
    ):
        raise SourceUnavailable("SuccessFactors catalogue incomplete or excessive")
    found = []
    seen = set()
    for row in rows:
        identities = {
            (job_url(n.attrs.get("href", ""), root), clean(n))
            for n in with_class(row.walk(), "jobTitle-link")
        }
        places = [
            clean(n)
            for n in row.walk()
            if n.tag == "td" and n.attrs.get("headers") == "hdrLocation"
        ]
        if len(identities) != 1 or len(places) != 1 or not places[0]:
            raise SourceUnavailable("SuccessFactors title or location missing")
        (url, identifier), title = identities.pop()
        if not title or identifier in seen:
            raise SourceUnavailable("SuccessFactors repeated or missing posting")
        seen.add(identifier)
        found.append(dict(id=identifier, url=url, title=title, location=places[0]))
    return found, total


def detail(text: str, row: dict, source: str, config: Company) -> RawJob | None:
    root, _, employer = SITES[config.name]
    nodes = list(Document(text).root.walk())
    titles = [clean(n).removeprefix("Title: ").strip() for n in nodes if n.tag == "h1"]
    canonicals = [
        n.attrs.get("href") for n in nodes if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    bodies = with_class(nodes, "jobdescription")
    if titles != [row["title"]] or len(canonicals) != 1 or len(bodies) != 1:
        raise SourceUnavailable("SuccessFactors listing/detail title or canonical changed")
    canonical, identifier = job_url(canonicals[0], root)
    if identifier != row["id"]:
        raise SourceUnavailable("SuccessFactors canonical posting identifier changed")
    body = markup(bodies[0])
    visible = clean(Document(body).root)
    if len(visible) < 200 or employer.casefold() not in visible.casefold():
        raise SourceUnavailable("SuccessFactors full employer description missing")
    # SMBC publishes talent-community registrations with internship titles.
    # They are explicitly not vacancies and must not become new-offer alerts.
    lowered = visible.casefold()
    if (
        "does not refer to a specific position" in lowered
        or "registration for our young talent community" in lowered
    ):
        return None
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        apply_url=canonical,
        source_url=canonical,
        location=row["location"],
        description=body,
        raw_payload={"listing": row},
    )


class SuccessFactorsPublicCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if (
            config.name not in SITES
            or config.career_url != SITES[config.name][0] + "/"
            or config.tenant
        ):
            raise ValueError("Use an audited employer-owned SuccessFactors recruitment site")
        self.source, self.config, self.http = source, config, http
        self.root, self.locale, _ = SITES[config.name]
        self.options = SearchOptions(**config.options)

    async def page(self, term: str, offset: int) -> str:
        return await self.http.get_text(
            self.root
            + "/search/?"
            + urlencode(
                dict(
                    q=term,
                    startrow=offset,
                    locale=self.locale,
                    sortColumn="referencedate",
                    sortDirection="desc",
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
            raise SourceUnavailable("SuccessFactors scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        candidates: dict[str, dict] = {}
        checks = []
        for term in self.options.search_terms:
            first, total = listing(
                await self.page(term, 0), term, 0, self.options.max_results_per_query, self.root
            )
            rows = first.copy()
            for offset in range(PAGE_SIZE, total if self.config.name != "Nordea" else 0, PAGE_SIZE):
                page, count = listing(
                    await self.page(term, offset),
                    term,
                    offset,
                    self.options.max_results_per_query,
                    self.root,
                )
                if count != total or {r["id"] for r in rows} & {r["id"] for r in page}:
                    raise SourceUnavailable("SuccessFactors pagination changed or repeated")
                rows.extend(page)
            if len(rows) != total:
                raise SourceUnavailable("SuccessFactors search incomplete")
            checks.append((term, first, total))
            for row in rows:
                if row["id"] in candidates and candidates[row["id"]] != row:
                    raise SourceUnavailable("SuccessFactors posting changed between searches")
                candidates[row["id"]] = row
        audit = SelectionAudit("search_results")
        selected = []
        for row in candidates.values():
            reason = rejection_reason(row["title"], self.options)
            if reason is None:
                selected.append(row)
            else:
                audit.record(reason, row["title"], row["id"])
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("SuccessFactors selected detail limit exceeded")
        jobs = []
        for row in selected:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            job = detail(text, row, self.source, self.config)
            if job is not None:
                audit.record(None, row["title"], row["id"])
                jobs.append(job)
            else:
                audit.record("talent_community", row["title"], row["id"])
        for term, first, total in checks:
            check, count = listing(
                await self.page(term, 0), term, 0, self.options.max_results_per_query, self.root
            )
            if count != total or sorted(first, key=lambda r: r["id"]) != sorted(
                check, key=lambda r: r["id"]
            ):
                raise SourceUnavailable("SuccessFactors catalogue changed during collection")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
