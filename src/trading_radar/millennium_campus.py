"""Anonymous Millennium campus search and public JobPosting detail pages."""

import asyncio
import html
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from trading_radar.config import Company
from trading_radar.html_page import Document
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions
from trading_radar.snapshot_retry import SnapshotChanged, stable_listing

ROOT = "https://campusjobs.mlp.com"
BOARD = ROOT + "/careers?domain=mlp.com&microsite=campus-site"
API = ROOT + "/api/apply/v2/jobs"
PAGE_SIZE = 10


def job_url(value: object, identifier: str) -> str:
    if not isinstance(value, str):
        raise SourceUnavailable("Millennium campus job URL missing")
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or parts.netloc not in {"campusjobs.mlp.com", "mlp.eightfold.ai"}
        or parts.fragment
        or not re.fullmatch(
            r"/careers/job/" + re.escape(identifier) + r"(?:-[a-zA-Z0-9_-]+)?", parts.path
        )
        or (
            parts.query
            and parse_qs(parts.query, keep_blank_values=True)
            not in (
                {"domain": ["mlp.com"]},
                {"domain": ["mlp.com"], "microsite": ["campus-site"]},
            )
        )
    ):
        raise SourceUnavailable("Millennium campus job URL identity mismatch")
    return ROOT + "/careers/job/" + identifier + "?domain=mlp.com&microsite=campus-site"


def position(row: object) -> dict:
    if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] <= 0:
        raise SourceUnavailable("Millennium campus position identity missing")
    if row.get("isPrivate") is not False or row.get("type") != "ATS":
        raise SourceUnavailable("Millennium campus position is not a public ATS job")
    identifier = str(row["id"])
    if (
        not isinstance(row.get("name"), str)
        or not row["name"].strip()
        or row.get("posting_name") != row["name"]
        or not isinstance(row.get("ats_job_id"), str)
        or not row["ats_job_id"].strip()
        or not isinstance(row.get("locations"), list)
        or not row["locations"]
        or any(not isinstance(p, str) or not p.strip() for p in row["locations"])
        or "business_unit" not in row
        or (row["business_unit"] is not None and not isinstance(row["business_unit"], str))
    ):
        raise SourceUnavailable("Millennium campus title, reference or locations missing")
    return {
        "id": identifier,
        "title": row["name"],
        "ats_id": row["ats_job_id"],
        "business_unit": row["business_unit"],
        "locations": list(dict.fromkeys(row["locations"])),
        "url": job_url(row.get("canonicalPositionUrl"), identifier),
    }


def public_data(data: object) -> dict:
    if (
        not isinstance(data, dict)
        or data.get("domain") != "mlp.com"
        or data.get("isUserAuthenticated") is not False
    ):
        raise SourceUnavailable("Millennium anonymous public response missing")
    return data


def parse_page(payload: object, term: str, offset: int, limit: int) -> tuple[list[dict], int]:
    data = public_data(payload)
    query = data.get("query")
    if not isinstance(query, dict) or query.get("query") != term or query.get("location") != "":
        raise SourceUnavailable("Millennium campus search scope changed")
    total, rows = data.get("count"), data.get("positions")
    if (
        type(total) is not int
        or not 0 <= total <= limit
        or not isinstance(rows, list)
        or offset > total
        or len(rows) != min(PAGE_SIZE, total - offset)
    ):
        raise SourceUnavailable("Millennium campus incomplete or excessive page")
    parsed = [position(row) for row in rows]
    if len({r["id"] for r in parsed}) != len(parsed):
        raise SourceUnavailable("Millennium campus repeated position")
    return parsed, total


def parse_detail(text: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    embedded = [n for n in nodes if n.tag == "code" and n.attrs.get("id") == "smartApplyData"]
    schemas = [
        n for n in nodes if n.tag == "script" and n.attrs.get("type") == "application/ld+json"
    ]
    if len(embedded) != 1 or len(schemas) != 1:
        raise SourceUnavailable("Millennium campus detail metadata missing or ambiguous")
    try:
        data = public_data(json.loads(embedded[0].text()))
        schema = json.loads(schemas[0].text())
    except ValueError:
        raise SourceUnavailable("invalid Millennium campus detail JSON") from None
    if (
        data.get("isFallback") is not False
        or data.get("singleview") is not True
        or str(data.get("pid")) != row["id"]
        or not isinstance(data.get("positions"), list)
        or len(data["positions"]) != 1
        or position(data["positions"][0]) != row
    ):
        raise SourceUnavailable("Millennium campus detail identity changed or unavailable")
    if (
        not isinstance(schema, dict)
        or schema.get("@type") != "JobPosting"
        or not isinstance(schema.get("hiringOrganization"), dict)
        or schema["hiringOrganization"].get("name") != "Millennium"
        or schema.get("title") != row["title"]
        or not isinstance(schema.get("description"), str)
        or not schema["description"].strip()
        or not isinstance(schema.get("employmentType"), str)
        or not schema["employmentType"].strip()
    ):
        raise SourceUnavailable("Millennium campus JobPosting incomplete or mismatched")
    url = job_url(schema.get("url"), row["id"])
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        apply_url=url,
        source_url=url,
        description="<p>" + html.escape(schema["description"]) + "</p>",
        location="; ".join(row["locations"]),
        employment_type=schema["employmentType"],
        # Platform timestamps are not confirmed publication/deadline instants.
        raw_payload={
            "ats_job_id": row["ats_id"],
            "business_unit": row["business_unit"],
            "datePosted": schema.get("datePosted"),
            "validThrough": schema.get("validThrough"),
        },
    )


class MillenniumCampusCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.name != "Millennium" or config.career_url != BOARD:
            raise ValueError("Use the verified Millennium campus board")
        self.source, self.config, self.http = source, config, http
        self.options = SearchOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Millennium campus scan time budget exceeded") from None

    async def page(self, term: str, offset: int) -> tuple[list[dict], int]:
        query = urlencode(
            {
                "domain": "mlp.com",
                "microsite": "campus-site",
                "query": term,
                "start": offset,
                "num": PAGE_SIZE,
            }
        )
        data = await self.http.get_json(
            API + "?" + query, self.config.request_interval, self.source
        )
        return parse_page(data, term, offset, self.options.max_results_per_query)

    async def _list(self) -> dict[str, dict]:
        found: dict[str, dict] = {}
        for term in self.options.search_terms:
            initial, total = await self.page(term, 0)
            rows = {r["id"]: r for r in initial}
            while len(rows) < total:
                batch, current = await self.page(term, len(rows))
                if current != total:
                    raise SnapshotChanged("Millennium campus total changed during pagination")
                for row in batch:
                    if row["id"] in rows:
                        raise SnapshotChanged("Millennium campus repeated page")
                    rows[row["id"]] = row
            if await self.page(term, 0) != (initial, total):
                raise SnapshotChanged("Millennium campus search changed during pagination")
            for identifier, row in rows.items():
                if identifier in found and found[identifier] != row:
                    raise SourceUnavailable("Millennium campus conflicting search results")
                found[identifier] = row
        return found

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        found = await stable_listing(self._list, self.source)
        selected = []
        for row in found.values():
            title = normalize_text(row["title"])
            if (
                not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
            ) and not any(has(title, t) for t in self.options.exclude_title_terms):
                selected.append(row)
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("Millennium campus detail limit exceeded")
        jobs = []
        for row in selected:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
        )
