"""Verified Deutsche Bank student catalogue, separate from professional Workday."""

import asyncio
import json
import re
from urllib.parse import urlencode, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, clean
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.morgan_stanley_campus import public_html
from trading_radar.normalizer import normalize_text
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason

BOARD = "https://careers.db.com/students-graduates/search-programmes/index?language_id=1"
API = "https://api-deutschebank.beesite.de"


class DBCampusOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def position(row: object) -> dict:
    if not isinstance(row, dict) or not isinstance(row.get("MatchedObjectDescriptor"), dict):
        raise SourceUnavailable("Deutsche Bank campus descriptor missing")
    info = row["MatchedObjectDescriptor"]
    identifier = row.get("MatchedObjectId")
    if (
        not isinstance(identifier, str)
        or not re.fullmatch(r"[1-9][0-9]{0,9}", identifier)
        or info.get("PositionID") != identifier
        or not isinstance(info.get("PositionTitle"), str)
        or not info["PositionTitle"].strip()
    ):
        raise SourceUnavailable("Deutsche Bank campus identity changed")
    url = info.get("PositionURI")
    if not isinstance(url, str):
        raise SourceUnavailable("Deutsche Bank campus application URL missing")
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.netloc != "db.recsolu.com"
        or not re.fullmatch(r"/external/requisitions/[A-Za-z0-9_-]{16,80}", parts.path)
        or parts.query
        or parts.fragment
        or info.get("ApplyURI") != [url]
    ):
        raise SourceUnavailable("Deutsche Bank campus application identity mismatch")
    locations = info.get("PositionLocation")
    levels = info.get("CareerLevel")
    if (
        not isinstance(locations, list)
        or not locations
        or any(
            not isinstance(loc, dict)
            or any(
                not isinstance(loc.get(k), str) or not loc[k].strip()
                for k in ("CityName", "CountryName", "CountryCode")
            )
            for loc in locations
        )
        or not isinstance(levels, list)
        or not levels
        or any(
            not isinstance(level, dict)
            or not isinstance(level.get("Name"), str)
            or not level["Name"].strip()
            for level in levels
        )
    ):
        raise SourceUnavailable("Deutsche Bank campus location or career level missing")
    year = info.get("PositionHiringYear")
    if year not in (None, "") and (not isinstance(year, str) or not re.fullmatch(r"20\d{2}", year)):
        raise SourceUnavailable("Deutsche Bank campus hiring year changed")
    return {
        "id": identifier,
        "title": " ".join(info["PositionTitle"].split()),
        "apply_url": url,
        "location": "; ".join(
            dict.fromkeys(loc["CityName"] + ", " + loc["CountryName"] for loc in locations)
        ),
        "level": "; ".join(level["Name"] for level in levels),
        "hiring_year": year,
    }


def catalogue(payload: object, limit: int) -> list[dict]:
    if not isinstance(payload, dict) or payload.get("LanguageCode") != "EN":
        raise SourceUnavailable("Deutsche Bank campus response language changed")
    result = payload.get("SearchResult")
    if not isinstance(result, dict):
        raise SourceUnavailable("Deutsche Bank campus search envelope missing")
    total, count, rows = (
        result.get("SearchResultCountAll"),
        result.get("SearchResultCount"),
        result.get("SearchResultItems"),
    )
    if (
        type(total) is not int
        or not 0 <= total <= limit
        or type(count) is not int
        or count != total
        or not isinstance(rows, list)
        or len(rows) != total
    ):
        raise SourceUnavailable("Deutsche Bank campus catalogue incomplete or excessive")
    parsed = [position(row) for row in rows]
    if (
        len({row["id"] for row in parsed}) != total
        or len({row["apply_url"] for row in parsed}) != total
    ):
        raise SourceUnavailable("Deutsche Bank campus duplicate identities")
    return parsed


def detail(payload: object, row: dict, source: str, company: Company) -> RawJob:
    if (
        not isinstance(payload, dict)
        or payload.get("apply_uri") != row["apply_url"]
        or not isinstance(payload.get("html"), str)
    ):
        raise SourceUnavailable("Deutsche Bank campus detail application identity changed")
    nodes = list(Document(payload["html"]).root.walk())
    bodies = [n for n in nodes if n.attrs.get("id") == "db-jobad"]
    titles = [n for n in nodes if n.tag == "h1"]
    if (
        len(bodies) != 1
        or len(titles) != 1
        or clean(titles[0]) != row["title"]
        or len(clean(bodies[0])) < len(row["title"]) + 100
    ):
        raise SourceUnavailable("Deutsche Bank campus full description or title mismatch")
    return RawJob(
        company=company.name,
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        description=public_html(bodies[0]),
        apply_url=row["apply_url"],
        source_url=API + "/jobhtml/" + row["id"] + ".json",
        location=row["location"],
        employment_type=row["level"],
        seniority_hint="junior"
        if normalize_text(row["level"]) == "analyst graduate programme"
        else None,
        raw_payload={"career_level": row["level"], "published_hiring_year": row["hiring_year"]},
    )


class DBCampusCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.name != "Deutsche Bank" or config.career_url != BOARD:
            raise ValueError("Use the verified Deutsche Bank public student board")
        self.source, self.config, self.http = source, config, http
        self.options = DBCampusOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Deutsche Bank campus scan time budget exceeded") from None

    async def _list(self) -> list[dict]:
        # The employer frontend grows CountItem from FirstItem=1 on load more.
        request = {
            "LanguageCode": "EN",
            "SearchParameters": {"FirstItem": 1, "CountItem": self.options.max_results_per_query},
            "SearchCriteria": [],
        }
        url = (
            API
            + "/graduatesearch/?"
            + urlencode({"data": json.dumps(request, separators=(",", ":"))})
        )
        return catalogue(
            await self.http.get_json(url, self.config.request_interval, self.source),
            self.options.max_results_per_query,
        )

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        first = await self._list()
        audit = SelectionAudit("public_catalogue")
        selected = []
        for row in first:
            reason = rejection_reason(row["title"], self.options)
            audit.record(reason, row["title"], row["id"])
            if reason is None:
                selected.append(row)
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("Deutsche Bank campus detail limit exceeded")
        jobs = [
            detail(
                await self.http.get_json(
                    API + "/jobhtml/" + row["id"] + ".json",
                    self.config.request_interval,
                    self.source,
                ),
                row,
                self.source,
                self.config,
            )
            for row in selected
        ]
        if await self._list() != first:
            raise SourceUnavailable("Deutsche Bank campus catalogue changed during collection")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
