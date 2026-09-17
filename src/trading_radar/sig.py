"""Susquehanna's public iCIMS/Jibe catalogue, with complete descriptions per page."""

import asyncio
import re
from urllib.parse import urlencode, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.greenhouse_filtered import instant
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text, plain_text
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://careers.sig.com"
SEARCH = ORIGIN + "/jobs"
API = ORIGIN + "/api/jobs"
EMPLOYER = "Susquehanna International Group, LLP"
PAGE_SIZE = 100
EXCLUDED_FUNCTIONS = {"Operations", "Sports Analytics"}
CATEGORIES = {
    "Experienced Professionals",
    "New Graduates",
    "Interns + Co-ops",
    "Student Discovery Program",
}


class SIGOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def parse_page(payload: object, page: int, limit: int) -> tuple[list[dict], int]:
    if not isinstance(payload, dict):
        raise SourceUnavailable("invalid SIG response")
    total, rows = payload.get("totalCount"), payload.get("jobs")
    if (
        type(total) is not int
        or not 0 <= total <= limit
        or type(payload.get("count")) is not int
        or payload.get("count") != total
        or not isinstance(rows, list)
        or len(rows) != min(PAGE_SIZE, max(0, total - (page - 1) * PAGE_SIZE))
    ):
        raise SourceUnavailable("SIG result count missing, excessive or incomplete")
    result = []
    for item in rows:
        if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
            raise SourceUnavailable("invalid SIG job wrapper")
        row = item["data"]
        identifier = row.get("req_id")
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(r"[1-9]\d*", identifier)
            or row.get("slug") != identifier
        ):
            raise SourceUnavailable("SIG job identity mismatch")
        if (
            row.get("client_code") != "sig"
            or row.get("hiring_organization") != EMPLOYER
            or row.get("language") != "en-us"
        ):
            raise SourceUnavailable("SIG employer or language mismatch")
        if not isinstance(row.get("title"), str) or not row["title"].strip():
            raise SourceUnavailable("SIG title missing")
        for flag in ["internal", "searchable", "applyable"]:
            if type(row.get(flag)) is not bool:
                raise SourceUnavailable("SIG visibility flag missing")
        categories = row.get("categories")
        if (
            not isinstance(categories, list)
            or len(categories) != 1
            or not isinstance(categories[0], dict)
            or categories[0].get("name") not in CATEGORIES
        ):
            raise SourceUnavailable("SIG category missing or changed")
        result.append(row)
    return result, total


def parse_job(row: dict, source: str, config: Company) -> RawJob:
    identifier = row["req_id"]
    target = row.get("apply_url")
    if not isinstance(target, str):
        raise SourceUnavailable("SIG public application target missing")
    parts = urlsplit(target)
    # Check the public link's reference without visiting its candidate login.
    if (
        (parts.scheme, parts.netloc, parts.path)
        != ("https", "careers-sig.icims.com", f"/jobs/{identifier}/login")
        or parts.query
        or parts.fragment
    ):
        raise SourceUnavailable("SIG application identity mismatch")
    if any(
        not isinstance(row.get(k), str) or not plain_text(row[k])
        for k in ["description", "qualifications"]
    ):
        raise SourceUnavailable("SIG description or candidate requirements missing")
    description = row["description"]
    if plain_text(row["qualifications"]) not in plain_text(description):
        description += "<h2>Requirements</h2>" + row["qualifications"]
    if any(
        not isinstance(row.get(k), str) or not row[k].strip() for k in ["city", "country"]
    ) or row.get("multipleLocations"):
        raise SourceUnavailable("SIG location missing or unsupported multi-location schema")
    places = [row["city"].strip()]
    if row.get("state"):
        if not isinstance(row["state"], str):
            raise SourceUnavailable("SIG state invalid")
        places.append(row["state"].strip())
    places.append(row["country"].strip())
    tags = row.get("tags3")
    if (
        not isinstance(tags, list)
        or not tags
        or any(
            not isinstance(t, str)
            or not re.fullmatch(r"(?:[A-Za-z]+ 20\d{2}|Immediate|Flexible) Start", t)
            for t in tags
        )
    ):
        raise SourceUnavailable("SIG target start metadata missing or changed")
    contract = row.get("employment_type")
    if contract is not None and (not isinstance(contract, str) or not contract.strip()):
        raise SourceUnavailable("SIG employment type invalid")
    category = row["categories"][0]["name"]
    # Internship category is stronger than an ambiguous ATS contract (e.g. PER_DIEM).
    if category == "Interns + Co-ops":
        contract = "Internship"
    url = f"{SEARCH}/{identifier}?lang=en-us"
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=identifier,
        title=row["title"].strip(),
        apply_url=url,
        source_url=url,
        location=", ".join(dict.fromkeys(places)),
        description=description,
        employment_type=contract,
        seniority_hint="junior" if category == "New Graduates" else None,
        expected_start_date=" / ".join(tags),
        date_posted=instant(row.get("posted_date")),
        # validThrough on the website appears to be generated expiry, not an application deadline.
        raw_payload={
            "category": category,
            "employment_type": row.get("employment_type"),
            "tags3": tags,
        },
    )


class SIGCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH:
            raise ValueError("Use the verified SIG public catalogue URL")
        self.source, self.config, self.http = source, config, http
        self.options = SIGOptions(**config.options)

    async def page(self, number: int) -> tuple[list[dict], int]:
        payload = await self.http.get_json(
            API + "?" + urlencode({"page": number, "limit": PAGE_SIZE}),
            self.config.request_interval,
            self.source,
        )
        return parse_page(payload, number, self.options.max_results_per_query)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("SIG scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        rows, total = await self.page(1)
        first = list(rows)
        number = 2
        while len(rows) < total:
            page, count = await self.page(number)
            if count != total:
                raise SourceUnavailable("SIG total changed during pagination")
            rows.extend(page)
            number += 1
        if len({r["req_id"] for r in rows}) != total:
            raise SourceUnavailable("SIG duplicate jobs or repeated page")
        check, count = await self.page(1)
        if count != total or check != first:
            raise SourceUnavailable("SIG board changed during pagination")
        jobs = []
        for row in rows:
            functions = row.get("tags1")
            if (
                not isinstance(functions, list)
                or not functions
                or any(not isinstance(v, str) or not v.strip() for v in functions)
            ):
                raise SourceUnavailable("SIG function metadata missing")
            if any(v in EXCLUDED_FUNCTIONS for v in functions):
                continue
            if (
                row["internal"]
                or not row["searchable"]
                or not row["applyable"]
                or row["categories"][0]["name"] == "Student Discovery Program"
            ):
                continue
            title = normalize_text(row["title"])
            if (
                self.options.title_terms
                and not any(has(title, t) for t in self.options.title_terms)
            ) or any(has(title, t) for t in self.options.exclude_title_terms):
                continue
            jobs.append(parse_job(row, self.source, self.config))
        if len(jobs) > self.options.max_details:
            raise SourceUnavailable("SIG selected-job limit exceeded")
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
