"""Public Workday CXS search + detail adapter, scoped and bounded.

CXS is the JSON interface used by public career pages, not Workday's authenticated
HR API. A POST here submits a search, never an application.
"""

import html
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from pydantic import Field, field_validator

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text, parse_date
from trading_radar.search_scope import SearchOptions


class WorkdayOptions(SearchOptions):
    conditional_details: bool = Field(default=False, strict=True)
    applied_facets: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("applied_facets", mode="before")
    @classmethod
    def validate_facets(cls, value: object) -> dict[str, list[str]]:
        if type(value) is not dict or len(value) > 5:
            raise ValueError("Workday applied facets must be a dictionary with at most 5 facets")
        facets: dict[str, list[str]] = {}
        for key, identifiers in value.items():
            if type(key) is not str or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,63}", key):
                raise ValueError(
                    "Workday facet names must be ASCII identifiers of 1 to 64 characters"
                )
            if type(identifiers) is not list or not 1 <= len(identifiers) <= 10:
                raise ValueError("Each Workday facet must contain 1 to 10 identifier strings")
            for identifier in identifiers:
                if (
                    type(identifier) is not str
                    or not identifier.strip()
                    or len(identifier) > 128
                    or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in identifier)
                ):
                    raise ValueError(
                        "Workday facet identifiers must be nonempty strings of at most 128 "
                        "characters without control characters"
                    )
            if len(set(identifiers)) != len(identifiers):
                raise ValueError("Workday facet identifiers must be unique within each facet")
            facets[key] = list(identifiers)
        return facets


def workday_base(config: Company) -> tuple[str, str]:
    parts = urlsplit(config.career_url)
    host = re.fullmatch(r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com", parts.netloc)
    segments = parts.path.strip("/").split("/")
    if segments and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", segments[0]):
        segments = segments[1:]
    if (
        parts.scheme != "https"
        or not host
        or parts.query
        or parts.fragment
        or len(segments) != 1
        or not re.fullmatch(r"[A-Za-z0-9_-]+", segments[0])
    ):
        raise ValueError("Use a public Workday HTTPS career site root")
    tenant = host[1]
    if config.tenant and tenant != config.tenant:
        raise ValueError("Workday tenant differs from career URL")
    root = f"https://{parts.netloc}"
    return f"{root}/{segments[0]}", f"{root}/wday/cxs/{tenant}/{segments[0]}"


def external_path(value: object) -> str:
    if not isinstance(value, str):
        raise SourceUnavailable("Workday job path is missing")
    parsed = urlsplit(value)
    decoded = unquote(value)
    if (
        not value.startswith("/job/")
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or "\\" in decoded
        or any(p in {".", ".."} for p in decoded.split("/"))
    ):
        raise SourceUnavailable("invalid Workday job path")
    return value


def comparable_title(value: str) -> str:
    """Ignore presentation differences without erasing punctuation or non-Latin text."""
    return " ".join(unicodedata.normalize("NFKC", html.unescape(value)).casefold().split())


def optional_text(record: dict, field: str) -> str | None:
    value = record.get(field)
    if value is not None and not isinstance(value, str):
        raise SourceUnavailable(f"invalid Workday {field}; no snapshot committed")
    return value


class WorkdayCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        self.source, self.config, self.http = source, config, http
        self.site, self.api = workday_base(config)
        self.options = WorkdayOptions(**config.options)

    async def collect(self) -> Collection:
        import asyncio

        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable(
                "Workday scan time budget exceeded; no snapshot committed"
            ) from None

    async def _search(self, term: str) -> dict[str, dict]:
        rows: dict[str, dict] = {}
        offset, expected = 0, None
        while expected is None or offset < expected:
            payload = await self.http.post_search_json(
                self.api + "/jobs",
                {
                    "appliedFacets": {
                        key: list(identifiers)
                        for key, identifiers in self.options.applied_facets.items()
                    },
                    "limit": 20,
                    "offset": offset,
                    "searchText": term,
                },
                self.config.request_interval,
                self.source,
            )
            if not isinstance(payload, dict):
                raise SourceUnavailable("invalid Workday search response")
            total, page = payload.get("total"), payload.get("jobPostings")
            if type(total) is not int or total < 0 or not isinstance(page, list):
                raise SourceUnavailable("invalid Workday pagination metadata")
            if total > self.options.max_results_per_query:
                raise SourceUnavailable("Workday query exceeds result limit; narrow search scope")
            # Observed CXS contract: subsequent pages report total=0 even with results.
            if expected is not None and total not in {0, expected}:
                raise SourceUnavailable("Workday total changed during pagination; retry next scan")
            if expected is None:
                expected = total
            if len(page) != min(20, expected - offset):
                raise SourceUnavailable("Workday returned a short or inconsistent page")
            for row in page:
                if (
                    not isinstance(row, dict)
                    or not isinstance(row.get("title"), str)
                    or not row["title"].strip()
                ):
                    raise SourceUnavailable("malformed Workday listing")
                path = external_path(row.get("externalPath"))
                if path in rows:
                    raise SourceUnavailable("Workday pagination repeated a posting")
                rows[path] = row
            offset += len(page)
        return rows

    def selected(self, title: str) -> bool:
        title = normalize_text(title)
        return (
            not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
        ) and not any(has(title, term) for term in self.options.exclude_title_terms)

    async def _detail(self, path: str, listing: dict) -> RawJob:
        get_json = (
            self.http.get_conditional_json
            if self.options.conditional_details
            else self.http.get_json
        )
        payload = await get_json(self.api + path, self.config.request_interval, self.source)
        info = payload.get("jobPostingInfo") if isinstance(payload, dict) else None
        if not isinstance(info, dict):
            raise SourceUnavailable("Workday detail is incomplete; no snapshot committed")
        title = optional_text(info, "title")
        description = optional_text(info, "jobDescription")
        if not title or not title.strip() or not description or not description.strip():
            raise SourceUnavailable("Workday detail is incomplete; no snapshot committed")
        # Cache measurement can read a detail alone with an empty listing. Normal
        # collection always supplies a nonempty title validated by _search.
        listed_title = optional_text(listing, "title")
        if listed_title is not None and comparable_title(title) != comparable_title(listed_title):
            raise SourceUnavailable(
                "Workday title changed between listing and detail; retry next scan"
            )
        locations = [optional_text(info, "location")]
        listing_location = optional_text(listing, "locationsText")
        additional = info.get("additionalLocations")
        if additional is None:
            additional = []
        if not isinstance(additional, list):
            raise SourceUnavailable("invalid Workday additional locations")
        for location in additional:
            descriptor = location.get("descriptor") if isinstance(location, dict) else location
            if not isinstance(descriptor, str):
                raise SourceUnavailable("invalid Workday additional location descriptor")
            locations.append(descriptor)
        loc = "; ".join(dict.fromkeys(x for x in locations if isinstance(x, str) and x))
        identifiers = [optional_text(info, field) for field in ("id", "jobReqId")]
        identifier = next((value for value in identifiers if value and value.strip()), None)
        if not identifier:
            raise SourceUnavailable("Workday detail missing stable identifier")
        start_date = optional_text(info, "startDate")
        time_type = optional_text(info, "timeType")
        # startDate is posting publication, NOT candidate employment start.
        # endDate is a date-only posting expiry; keep unknown here until semantics are verified.
        return RawJob(
            company=self.config.name,
            title=title,
            external_id=identifier,
            source=self.source,
            source_type="official",
            apply_url=self.site + path,
            source_url=self.site + path,
            description=description,
            location=loc or listing_location or "",
            date_posted=parse_date(start_date),
            employment_type=time_type,
            raw_payload={"listing": listing, "detail": info},
        )

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        candidates: dict[str, dict] = {}
        for term in self.options.search_terms:
            for path, row in (await self._search(term)).items():
                if path in candidates and comparable_title(
                    candidates[path]["title"]
                ) != comparable_title(row["title"]):
                    raise SourceUnavailable(
                        "Workday title changed between queries; retry next scan"
                    )
                candidates[path] = row
        targets = {path: row for path, row in candidates.items() if self.selected(row["title"])}
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Workday detail limit exceeded; narrow search scope")
        jobs: list[RawJob] = []
        identifiers: set[str | None] = set()
        for path, row in targets.items():
            job = await self._detail(path, row)
            if job.external_id in identifiers:
                # Distinct paths are not known aliases. Importing both would overwrite
                # the same stable identity with an order-dependent URL and content.
                raise SourceUnavailable(
                    "Workday detail identifier repeated across paths; no snapshot committed"
                )
            identifiers.add(job.external_id)
            jobs.append(job)
        # Searches and title filters are partial inventories. Never infer closure from absence.
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
