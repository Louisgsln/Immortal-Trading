"""Public Oracle Candidate Experience adapter; JPMorgan remains unvalidated live."""

import asyncio
import re
from urllib.parse import urlencode, urlsplit

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text, parse_date
from trading_radar.search_scope import SearchOptions


def oracle_base(url: str) -> tuple[str, str, str]:
    parts = urlsplit(url)
    host = re.fullmatch(r"[a-z0-9-]+\.fa(?:\.[a-z0-9-]+)?\.oraclecloud\.com", parts.netloc)
    path = re.fullmatch(r"/hcmUI/CandidateExperience/en/sites/([A-Za-z0-9_-]+)/?", parts.path)
    if parts.scheme != "https" or not host or not path or parts.query or parts.fragment:
        raise ValueError("Use a public Oracle Candidate Experience site root")
    return url.rstrip("/"), f"https://{parts.netloc}/hcmRestApi/resources/latest", path[1]


class OracleCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        self.source, self.config, self.http = source, config, http
        self.site, self.api, self.site_number = oracle_base(config.career_url)
        self.options = SearchOptions(**config.options)
        if any(re.search(r"[,;]", t) for t in self.options.search_terms):
            raise ValueError("Oracle search terms cannot contain finder separators")

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable(
                "Oracle scan time budget exceeded; no snapshot committed"
            ) from None

    async def fetch(self, resource: str, finder: str, **params):
        query = urlencode({"onlyData": "true", "finder": finder, **params})
        return await self.http.get_json(
            f"{self.api}/{resource}?{query}", self.config.request_interval, self.source
        )

    async def _search(self, term: str) -> dict[str, dict]:
        rows: dict[str, dict] = {}
        expected, offset = None, 0
        while expected is None or offset < expected:
            payload = await self.fetch(
                "recruitingCEJobRequisitions",
                f"findReqs;siteNumber={self.site_number},limit=25,offset={offset},keyword={term}",
                expand="requisitionList",
            )
            items = payload.get("items") if isinstance(payload, dict) else None
            if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
                raise SourceUnavailable("Oracle search envelope missing")
            total, page = items[0].get("TotalJobsCount"), items[0].get("requisitionList")
            if type(total) is not int or total < 0 or not isinstance(page, list):
                raise SourceUnavailable("invalid Oracle pagination metadata")
            if total > self.options.max_results_per_query:
                raise SourceUnavailable("Oracle query exceeds result limit; narrow scope")
            if expected is not None and total != expected:
                raise SourceUnavailable("Oracle total changed during pagination")
            expected = total
            if (not page and offset < expected) or len(page) > min(25, expected - offset):
                raise SourceUnavailable("Oracle returned an inconsistent page")
            for row in page:
                if (
                    not isinstance(row, dict)
                    or not isinstance(row.get("Title"), str)
                    or not row["Title"].strip()
                ):
                    raise SourceUnavailable("malformed Oracle listing")
                identifier = str(row.get("Id") or row.get("RequisitionNumber") or "")
                if not re.fullmatch(r"[0-9]+", identifier):
                    raise SourceUnavailable("Oracle stable identifier missing")
                if identifier in rows:
                    raise SourceUnavailable("Oracle pagination repeated a posting")
                rows[identifier] = row
            offset += len(page)
        return rows

    def selected(self, title: str) -> bool:
        title = normalize_text(title)
        return (
            not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
        ) and not any(has(title, t) for t in self.options.exclude_title_terms)

    async def _detail(self, identifier: str, listing: dict) -> RawJob:
        payload = await self.fetch("recruitingCEJobRequisitionDetails", f"ById;Id={identifier}")
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
            raise SourceUnavailable("Oracle detail missing; no snapshot committed")
        info = items[0]
        actual = str(info.get("Id") or info.get("RequisitionNumber") or "")
        description = "\n".join(
            info[key]
            for key in (
                "ExternalDescriptionStr",
                "ExternalResponsibilitiesStr",
                "ExternalQualificationsStr",
            )
            if isinstance(info.get(key), str) and info[key].strip()
        )
        if actual != identifier or not description:
            raise SourceUnavailable("Oracle detail incomplete or mismatched")
        url = f"{self.site}/job/{identifier}"
        return RawJob(
            company=self.config.name,
            source=self.source,
            source_type="official",
            title=info.get("Title") or listing["Title"],
            external_id=identifier,
            apply_url=url,
            source_url=url,
            description=description,
            location=info.get("PrimaryLocation") or listing.get("PrimaryLocation") or "",
            date_posted=parse_date(info.get("PostedDate") or listing.get("PostedDate")),
            raw_payload={"listing": listing, "detail": info},
        )

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        candidates: dict[str, dict] = {}
        for term in self.options.search_terms:
            candidates.update(await self._search(term))
        targets = {key: row for key, row in candidates.items() if self.selected(row["Title"])}
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Oracle detail limit exceeded; narrow scope")
        jobs = [await self._detail(key, row) for key, row in targets.items()]
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
