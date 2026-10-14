"""D. E. Shaw's public Next.js catalogue and employer-owned posting pages."""

import asyncio
import html
import json
import re

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import plain_text
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason

BOARD = "https://www.deshaw.com/careers"


class DeshawOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def page_props(text: str) -> dict:
    scripts = [n for n in Document(text).root.walk() if n.attrs.get("id") == "__NEXT_DATA__"]
    if len(scripts) != 1 or scripts[0].tag != "script":
        raise SourceUnavailable("D. E. Shaw public page data missing or ambiguous")
    try:
        value = json.loads(scripts[0].text())["props"]["pageProps"]
    except (ValueError, KeyError, TypeError):
        raise SourceUnavailable("D. E. Shaw public page data invalid") from None
    if not isinstance(value, dict):
        raise SourceUnavailable("D. E. Shaw page properties invalid")
    return value


def posting_url(data: dict) -> str:
    identifier, slug = data.get("id"), data.get("jobUrl")
    if (
        type(identifier) is not int
        or identifier <= 0
        or not isinstance(slug, str)
        or not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-" + str(identifier), slug)
    ):
        raise SourceUnavailable("D. E. Shaw posting URL identity invalid")
    return BOARD + "/" + slug.lower()


def listing(text: str, limit: int) -> list[dict]:
    props = page_props(text)
    if props.get("jobsFetchingError") is not False:
        raise SourceUnavailable("D. E. Shaw catalogue reports a fetching error")
    rows = []
    seen = set()
    for key in ["regularJobs", "internships"]:
        items = props.get(key)
        if not isinstance(items, list):
            raise SourceUnavailable("D. E. Shaw public catalogue missing")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
                raise SourceUnavailable("D. E. Shaw listing data invalid")
            data = item["data"]
            url = posting_url(data)
            title = data.get("displayName")
            meta = data.get("jobMetadata")
            if (
                not isinstance(title, str)
                or not title.strip()
                or type(item.get("id")) is not int
                or item.get("id") != data["id"]
                or item.get("displayName") != title
                or type(data.get("activeOnJobsListing")) is not bool
                or not isinstance(meta, dict)
                or type(meta.get("isExploratory")) is not bool
                or type(data.get("shouldHideJobForAdditionalInfoRequests")) is not bool
            ):
                raise SourceUnavailable("D. E. Shaw listing identity or visibility invalid")
            if url in seen:
                raise SourceUnavailable("D. E. Shaw repeated public posting")
            seen.add(url)
            rows.append(data)
    # internalJobs contains unpublished requisitions and is never consumed.
    if not rows or len(rows) > limit:
        raise SourceUnavailable("D. E. Shaw catalogue empty or exceeds limit")
    return rows


def description(data: dict) -> str:
    value = data.get("jobDescription")
    if not isinstance(value, dict):
        raise SourceUnavailable("D. E. Shaw description missing")
    intro = value.get("websiteDescription")
    responsibilities = value.get("responsibilitiesHtml") or value.get("responsibilities")
    requirements = value.get("peopleWeAreLookingFor")
    if isinstance(requirements, list):
        if not requirements or any(not isinstance(v, str) or not v.strip() for v in requirements):
            raise SourceUnavailable("D. E. Shaw requirements invalid")
        requirements = (
            "<ul>" + "".join("<li>" + html.escape(v) + "</li>" for v in requirements) + "</ul>"
        )
    elif requirements is None:
        requirements = value.get("peopleWeAreLookingForHtml") or value.get(
            "peopleWeAreLookingForStr"
        )
    sections = [
        ("The role", intro),
        ("Responsibilities", responsibilities),
        ("Requirements", requirements),
    ]
    if any(not isinstance(v, str) or not plain_text(v).strip() for _, v in sections):
        raise SourceUnavailable("D. E. Shaw full responsibilities or requirements missing")
    return "\n".join("<h2>" + label + "</h2>" + str(value) for label, value in sections)


def raw(data: dict, source: str) -> RawJob:
    meta = data["jobMetadata"]
    places, contract = meta.get("jobLocations"), meta.get("workStatus")
    if (
        not isinstance(places, list)
        or not places
        or any(
            not isinstance(p, dict) or not isinstance(p.get("name"), str) or not p["name"].strip()
            for p in places
        )
        or not isinstance(contract, str)
        or not contract.strip()
    ):
        raise SourceUnavailable("D. E. Shaw locations or contract missing")
    url = posting_url(data)
    return RawJob(
        company="D. E. Shaw",
        source=source,
        source_type="official",
        external_id=str(data["id"]),
        title=data["displayName"],
        apply_url=url,
        source_url=url,
        location="; ".join(dict.fromkeys(p["name"] for p in places)),
        employment_type=contract,
        description=description(data),
        # datePosted on the rendered detail is generated at request time. validToDate
        # has no verified application-deadline semantics. Neither becomes a date.
        raw_payload={"job": data},
    )


class DeshawCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.name != "D. E. Shaw" or config.career_url != BOARD or config.tenant:
            raise ValueError("Use the verified D. E. Shaw public catalogue")
        self.source, self.config, self.http = source, config, http
        self.options = DeshawOptions(**config.options)

    async def text(self, url: str) -> str:
        return await self.http.get_text(url, self.config.request_interval, self.source)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("D. E. Shaw scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        rows = listing(await self.text(BOARD), self.options.max_results_per_query)
        audit = SelectionAudit("public_catalogue")
        jobs: list[RawJob] = []
        for data in rows:
            if not data["activeOnJobsListing"] or data["shouldHideJobForAdditionalInfoRequests"]:
                audit.record("hidden_posting")
                continue
            if data["jobMetadata"]["isExploratory"]:
                audit.record("prospect_not_vacancy")
                continue
            reason = rejection_reason(data["displayName"], self.options)
            audit.record(reason, data["displayName"], str(data["id"]))
            if reason is not None:
                continue
            if len(jobs) >= self.options.max_details:
                raise SourceUnavailable("D. E. Shaw detail limit exceeded")
            expected = raw(data, self.source)
            detail = page_props(await self.text(expected.apply_url)).get("jobData")
            if not isinstance(detail, dict):
                raise SourceUnavailable("D. E. Shaw detail missing")
            # Compare every consumed job field and public visibility, ignoring only
            # rendering metadata such as videos or the synthetic datePosted.
            if (
                detail.get("activeOnJobsListing") is not True
                or detail.get("shouldHideJobForAdditionalInfoRequests") is not False
                or not isinstance(detail.get("jobMetadata"), dict)
                or detail["jobMetadata"].get("isExploratory") is not False
            ):
                raise SourceUnavailable("D. E. Shaw posting no longer public")
            actual = raw(detail, self.source)
            if actual.model_dump(exclude={"raw_payload"}) != expected.model_dump(
                exclude={"raw_payload"}
            ):
                raise SourceUnavailable("D. E. Shaw listing and detail changed")
            jobs.append(actual)
        check = listing(await self.text(BOARD), self.options.max_results_per_query)
        if sorted(rows, key=lambda d: d["id"]) != sorted(check, key=lambda d: d["id"]):
            raise SourceUnavailable("D. E. Shaw catalogue changed during collection")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
