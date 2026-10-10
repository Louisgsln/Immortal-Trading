"""Bank of America's public student catalogue and matching employer job pages."""

import asyncio
import html
import json
import re
from datetime import datetime
from urllib.parse import urlencode, urljoin, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.description_sections import visible_text
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import normalize_text
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason

ORIGIN = "https://careers.bankofamerica.com"
BOARD = ORIGIN + "/en-us/students/job-search"
SEARCH = ORIGIN + "/services/campusjobssearchservlet"
PAGE_SIZE = 50
CONTRACTS = {"Off-cycle internship", "Summer internship", "Industrial placement", "Full time"}


class BofACampusOptions(SearchOptions):
    # The public campus catalogue is enumerated, without keyword partitions.
    search_terms: list[str] = Field(default_factory=list, max_length=0)
    max_results_per_query: int = Field(default=500, ge=1, le=1999)


def text_field(row: dict, key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SourceUnavailable("Bank of America campus field is missing: " + key)
    return value


def detail_url(value: str, identifier: str) -> str:
    parts = urlsplit(urljoin(ORIGIN, value))
    if (
        parts.scheme != "https"
        or parts.netloc != "careers.bankofamerica.com"
        or parts.query
        or parts.fragment
        or not re.fullmatch(
            r"/en-us/students/job-detail/" + re.escape(identifier) + r"/[a-z0-9-]+",
            parts.path,
        )
    ):
        raise SourceUnavailable("Bank of America campus detail URL is invalid")
    return ORIGIN + parts.path


def apply_url(value: str, identifier: str) -> str:
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or parts.netloc != "bankcampuscareers.tal.net"
        or parts.query
        or parts.fragment
        or not re.fullmatch(
            r"/vx/mobile-0/brand-(?:0|4)/candidate/so/pm/1/pl/1/opp/"
            + re.escape(identifier)
            + r"-[A-Za-z0-9-]+/en-GB",
            parts.path,
        )
    ):
        raise SourceUnavailable("Bank of America campus application URL is invalid")
    return value


def posting_day(value: str):
    try:
        # Audited en-US employer field; indexedDate is not a publication date.
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        raise SourceUnavailable("Bank of America campus publication day is invalid") from None


def closing_day(value: str):
    try:
        # A calendar day, never an invented midnight UTC timestamp.
        return datetime.strptime(value, "%b %d, %Y").date()
    except ValueError:
        raise SourceUnavailable("Bank of America campus closing day is invalid") from None


def listing_identity(row: dict) -> str:
    identifier = text_field(row, "jobRequisitionId")
    if not re.fullmatch(r"[1-9][0-9]*", identifier):
        raise SourceUnavailable("Bank of America campus requisition ID is invalid")
    text_field(row, "postingTitle")
    text_field(row, "location")
    detail_url(text_field(row, "jcrURL"), identifier)
    apply_url(text_field(row, "externalUrl"), identifier)
    if text_field(row, "timeType") not in CONTRACTS or row.get("jobSubFamily") != row["timeType"]:
        raise SourceUnavailable("Bank of America campus programme type is invalid")
    return identifier


def parse_detail(body: str, row: dict, source: str, company: Company) -> RawJob:
    identifier = listing_identity(row)
    url = detail_url(row["jcrURL"], identifier)
    application = apply_url(row["externalUrl"], identifier)
    nodes = list(Document(body).root.walk())
    markers = [n.attrs.get("content") for n in nodes if n.attrs.get("name") == "job-source"]
    paths = [n.attrs.get("content") for n in nodes if n.attrs.get("name") == "job-path"]
    headings = with_class(nodes, "job-description-body__title")
    if (
        markers != ["campus"]
        or paths != [urlsplit(url).path]
        or len(headings) != 1
        or headings[0].tag != "h1"
        or normalize_text(clean(headings[0])) != normalize_text(row["postingTitle"])
    ):
        raise SourceUnavailable("Bank of America campus detail identity disagrees")
    postings = []
    try:
        for node in nodes:
            if node.tag == "script" and node.attrs.get("type") == "application/ld+json":
                value = json.loads("".join(c for c in node.children if isinstance(c, str)))
                if isinstance(value, dict) and value.get("@type") == "JobPosting":
                    postings.append(value)
    except (ValueError, TypeError):
        raise SourceUnavailable("Bank of America campus structured data is invalid") from None
    if len(postings) != 1:
        raise SourceUnavailable("Bank of America campus requires one JobPosting")
    job = postings[0]
    identity = job.get("identifier")
    employer = job.get("hiringOrganization")
    if (
        not isinstance(identity, dict)
        or identity.get("name") != "Job_Requisition_ID"
        or identity.get("value") != identifier
        or not isinstance(employer, dict)
        or employer.get("name") != "Bank of America"
        or company.name != "Bank of America"
        or normalize_text(html.unescape(text_field(job, "title")))
        != normalize_text(row["postingTitle"])
        or job.get("employmentType") != row["timeType"].upper().replace(" ", "_")
    ):
        raise SourceUnavailable("Bank of America campus structured identity disagrees")
    description = text_field(job, "description")
    if normalize_text(visible_text(Document(description).root)) != normalize_text(
        visible_text(Document(text_field(row, "jobDescriptionExternal")).root)
    ):
        raise SourceUnavailable("Bank of America campus description changed")
    locations = job.get("jobLocation")
    if not isinstance(locations, list) or not locations:
        raise SourceUnavailable("Bank of America campus locations are missing")
    observed = []
    for location in locations:
        address = location.get("address") if isinstance(location, dict) else None
        if not isinstance(address, dict):
            raise SourceUnavailable("Bank of America campus address is invalid")
        observed.append(
            text_field(address, "addressLocality") + ", " + text_field(address, "addressCountry")
        )
    # The display location abbreviates US states (e.g. New York, NY).
    # Compare the employer's city/country fields rather than that display string.
    primary = text_field(row, "city") + ", " + text_field(row, "country")
    if normalize_text(primary) not in {normalize_text(v) for v in observed}:
        raise SourceUnavailable("Bank of America campus listing location disagrees")
    links = {n.attrs.get("href") for n in nodes if n.tag == "a"}
    if application not in links:
        raise SourceUnavailable("Bank of America campus application link is missing")
    published = posting_day(text_field(job, "datePosted"))
    if published != posting_day(text_field(row, "postedDate")):
        raise SourceUnavailable("Bank of America campus publication day disagrees")
    closing = row.get("applyByDate")
    if closing is not None and not isinstance(closing, str):
        raise SourceUnavailable("Bank of America campus closing day is invalid")
    displayed = {
        clean(n)[len("Apply by ") :]
        for n in with_class(nodes, "posted-date")
        if clean(n).startswith("Apply by ")
    }
    if displayed != ({closing} if closing else set()):
        raise SourceUnavailable("Bank of America campus closing day disagrees")
    if closing:
        description += "<p>Application deadline: " + closing_day(closing).isoformat() + ".</p>"
    description += "<p>Employer programme type: " + html.escape(row["timeType"]) + ".</p>"
    return RawJob(
        company=company.name,
        title=row["postingTitle"],
        source=source,
        source_type="official",
        external_id=identifier,
        apply_url=application,
        source_url=url,
        description=description,
        location="; ".join(dict.fromkeys(observed)),
        employment_type=row["timeType"],
        publication_day=published,
        raw_payload={"listing": row, "job_posting": job},
    )


class BofACampusCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url.rstrip("/") != BOARD or config.name != "Bank of America":
            raise ValueError("Only the official Bank of America student catalogue is supported")
        self.source, self.config, self.http = source, config, http
        self.options = BofACampusOptions(**config.options)

    async def page(self, start: int):
        # Employer servlet uses exclusive END, not page length, for `rows`.
        url = (
            SEARCH
            + "?"
            + urlencode({"search": "getAllJobs", "start": start, "rows": start + PAGE_SIZE})
        )
        payload = await self.http.get_json(url, self.config.request_interval, self.source)
        if not isinstance(payload, dict) or type(payload.get("totalMatches")) is not int:
            raise SourceUnavailable("Bank of America campus pagination metadata is invalid")
        total, rows = payload["totalMatches"], payload.get("jobsList")
        if not 0 <= total <= self.options.max_results_per_query or not isinstance(rows, list):
            raise SourceUnavailable("Bank of America campus result limit or list is invalid")
        if len(rows) != min(PAGE_SIZE, max(0, total - start)):
            raise SourceUnavailable("Bank of America campus page is incomplete")
        if any(not isinstance(row, dict) for row in rows):
            raise SourceUnavailable("Bank of America campus listing is invalid")
        return total, rows

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Bank of America campus scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        total, first = await self.page(0)
        rows = list(first)
        for start in range(PAGE_SIZE, total, PAGE_SIZE):
            count, page = await self.page(start)
            if count != total:
                raise SourceUnavailable("Bank of America campus total changed during pagination")
            rows.extend(page)
        identities = [listing_identity(row) for row in rows]
        if len(set(identities)) != total:
            raise SourceUnavailable("Bank of America campus pagination repeated a posting")
        audit = SelectionAudit("public_catalogue")
        targets = []
        for row, identifier in zip(rows, identities, strict=True):
            reason = rejection_reason(row["postingTitle"], self.options)
            audit.record(reason, row["postingTitle"], identifier)
            if reason is None:
                targets.append(row)
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Bank of America campus detail limit exceeded")
        jobs = []
        for row in targets:
            url = detail_url(row["jcrURL"], row["jobRequisitionId"])
            body = await self.http.get_text(url, self.config.request_interval, self.source)
            try:
                jobs.append(parse_detail(body, row, self.source, self.config))
            except SourceUnavailable as exc:
                raise SourceUnavailable(
                    "Requisition " + row["jobRequisitionId"] + ": " + str(exc)
                ) from None
        count, recheck = await self.page(0)
        if count != total or recheck != first:
            raise SourceUnavailable("Bank of America campus catalogue changed; retry next scan")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
