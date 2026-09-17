"""Anonymous public Goldman search and server-rendered job descriptions."""

import asyncio
import json
import re
from html.parser import HTMLParser
from typing import Literal

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

SEARCH_API = "https://api-higher.gs.com/gateway/api/v1/graphql"
QUERY = """query GetRoles($searchQueryInput: RoleSearchQueryInput!) {
  roleSearch(searchQueryInput: $searchQueryInput) {
    totalCount items {
      roleId corporateTitle jobTitle jobFunction
      locations { primary state country city }
      status division skills jobType { code description }
      externalSource { sourceId }
    }
  }
}"""

# RELEVANCE repeated an identical role across pages during live validation.
# The public UI also supports POSTED_DATE; retain duplicate/total checks with this sort.


class GoldmanOptions(SearchOptions):
    programme: Literal["professional", "campus"] = "professional"


class PageData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.active = dict(attrs).get("id") == "__NEXT_DATA__"

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def parse_role(html: str, identifier: str) -> dict:
    parser = PageData()
    parser.feed(html)
    try:
        role = json.loads("".join(parser.parts))["props"]["pageProps"]["role"]
        valid = (
            isinstance(role, dict)
            and role.get("externalSource", {}).get("sourceId") == identifier
            and isinstance(role.get("jobTitle"), str)
            and bool(role["jobTitle"].strip())
            and isinstance(role.get("descriptionHtml"), str)
            and bool(role["descriptionHtml"].strip())
            and isinstance(role.get("status"), str)
            and type(role.get("applyActive")) is bool
        )
        if not valid:
            raise ValueError
    except (ValueError, KeyError, TypeError, AttributeError):
        raise SourceUnavailable(
            "Goldman role data missing or mismatched; no snapshot committed"
        ) from None
    return role


class GoldmanCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        self.options = GoldmanOptions(**config.options)
        route = "campus" if self.options.programme == "campus" else "results"
        if config.career_url != f"https://higher.gs.com/{route}":
            raise ValueError("Use the public Goldman page matching the configured programme")
        self.source, self.config, self.http = source, config, http

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable(
                "Goldman scan time budget exceeded; no snapshot committed"
            ) from None

    async def _search(self, term: str) -> dict[str, dict]:
        rows: dict[str, dict] = {}
        expected, page_number = None, 0
        while expected is None or len(rows) < expected:
            payload = await self.http.post_search_json(
                SEARCH_API,
                {
                    "operationName": "GetRoles",
                    "query": QUERY,
                    "variables": {
                        "searchQueryInput": {
                            "page": {"pageSize": 20, "pageNumber": page_number},
                            "sort": {"sortStrategy": "POSTED_DATE", "sortOrder": "DESC"},
                            "filters": [],
                            "experiences": ["CAMPUS"]
                            if self.options.programme == "campus"
                            else ["EARLY_CAREER", "PROFESSIONAL"],
                            "searchTerm": term,
                        }
                    },
                },
                self.config.request_interval,
                self.source,
            )
            if not isinstance(payload, dict) or payload.get("errors"):
                raise SourceUnavailable("Goldman GraphQL search failed")
            data = payload.get("data")
            result = data.get("roleSearch") if isinstance(data, dict) else None
            if not isinstance(result, dict):
                raise SourceUnavailable("Goldman search data missing")
            total, page = result.get("totalCount"), result.get("items")
            if type(total) is not int or total < 0 or not isinstance(page, list):
                raise SourceUnavailable("invalid Goldman pagination metadata")
            if total > self.options.max_results_per_query:
                raise SourceUnavailable("Goldman query exceeds result limit; narrow scope")
            if expected is not None and total != expected:
                raise SourceUnavailable("Goldman total changed during pagination")
            expected = total
            if len(page) != min(20, expected - len(rows)):
                raise SourceUnavailable("Goldman returned a short or inconsistent page")
            for row in page:
                if (
                    not isinstance(row, dict)
                    or not isinstance(row.get("jobTitle"), str)
                    or not row["jobTitle"].strip()
                    or not isinstance(row.get("status"), str)
                ):
                    raise SourceUnavailable("malformed Goldman listing")
                external = row.get("externalSource")
                identifier = external.get("sourceId") if isinstance(external, dict) else None
                if not isinstance(identifier, str) or not re.fullmatch(r"[0-9]+", identifier):
                    raise SourceUnavailable("Goldman stable identifier missing")
                if identifier in rows:
                    raise SourceUnavailable("Goldman pagination repeated a posting")
                rows[identifier] = row
            page_number += 1
        return rows

    def selected(self, row: dict) -> bool:
        title = normalize_text(row["jobTitle"])
        return (
            row.get("status") == "POSTED"
            and "NOTICE_OF_FILING" not in str(row.get("roleId", ""))
            and (
                not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
            )
            and not any(has(title, t) for t in self.options.exclude_title_terms)
        )

    async def _detail(self, identifier: str, listing: dict) -> RawJob | None:
        url = f"https://higher.gs.com/roles/{identifier}"
        role = parse_role(
            await self.http.get_text(url, self.config.request_interval, self.source), identifier
        )
        if role.get("status") != "POSTED" or role.get("applyActive") is not True:
            return None
        locations = role.get("locations")
        if not isinstance(locations, list) or any(not isinstance(x, dict) for x in locations):
            raise SourceUnavailable("invalid Goldman locations")
        location = "; ".join(
            dict.fromkeys(
                ", ".join(
                    dict.fromkeys(
                        x
                        for x in (loc.get("city"), loc.get("state"), loc.get("country"))
                        if isinstance(x, str) and x
                    )
                )
                for loc in locations
            )
        )
        # No verified publication date in the observed contract. Never substitute first_seen.
        return RawJob(
            company=self.config.name,
            title=role["jobTitle"],
            source=self.source,
            source_type="official",
            external_id=identifier,
            apply_url=url,
            source_url=url,
            description=role["descriptionHtml"],
            location=location,
            raw_payload={"listing": listing, "detail": role},
        )

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        candidates: dict[str, dict] = {}
        for term in self.options.search_terms:
            candidates.update(await self._search(term))
        targets = {key: row for key, row in candidates.items() if self.selected(row)}
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Goldman detail limit exceeded; narrow scope")
        jobs = []
        for identifier, row in targets.items():
            job = await self._detail(identifier, row)
            if job is not None:
                jobs.append(job)
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
