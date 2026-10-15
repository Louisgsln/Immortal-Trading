"""Trexquant's public paginated search API with complete employer Markdown details."""

import asyncio
import re
from datetime import date

from pydantic import Field

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason
from trading_radar.workable_public import detail

BOARD = "https://apply.workable.com/trexquant/"
API = "https://apply.workable.com/api/v3/accounts/trexquant/jobs"
ACCOUNT = "2d380e5f-7505-405c-875b-70c7a63de0a8"
CONTRACTS = {"full": "Full-time", "contract": "Contract", "other": "Other", None: "—"}


class WorkableAPIOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def rows(payload: object, maximum: int) -> tuple[list[dict], int, str | None]:
    if (
        not isinstance(payload, dict)
        or type(payload.get("total")) is not int
        or not 0 <= payload["total"] <= maximum
        or not isinstance(payload.get("results"), list)
    ):
        raise SourceUnavailable("Workable API public search metadata changed")
    # The public API omits nextPage on the last page. The collector still
    # requires the exact declared total, so a missing cursor cannot truncate it.
    token = payload.get("nextPage")
    if token is not None and (not isinstance(token, str) or not token or len(token) > 1024):
        raise SourceUnavailable("Workable API pagination cursor changed")
    result = payload["results"]
    if len(result) > 10 or (token is not None and not result):
        raise SourceUnavailable("Workable API incomplete or excessive page")
    for row in result:
        if (
            not isinstance(row, dict)
            or type(row.get("id")) is not int
            or row["id"] <= 0
            or not isinstance(row.get("shortcode"), str)
            or not re.fullmatch(r"[A-F0-9]{10}", row["shortcode"])
            or not isinstance(row.get("title"), str)
            or not row["title"].strip()
            or row.get("accountUid") != ACCOUNT
            or type(row.get("isInternal")) is not bool
            or row.get("state") != "published"
            or row.get("approvalStatus") != "approved"
        ):
            raise SourceUnavailable("Workable API posting identity or publication changed")
    return result, payload["total"], token


def facts(row: dict) -> dict[str, str]:
    contract = row.get("type")
    if (contract is not None and not isinstance(contract, str)) or contract not in CONTRACTS:
        raise SourceUnavailable("Workable API contract missing or changed")
    departments = row.get("department")
    if not isinstance(departments, list) or any(
        not isinstance(d, str) or not d.strip() for d in departments
    ):
        raise SourceUnavailable("Workable API department missing")
    published = row.get("published")
    if not isinstance(published, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T[0-9:.]+Z", published
    ):
        raise SourceUnavailable("Workable API published date missing")
    try:
        posted = date.fromisoformat(published[:10]).isoformat()
    except ValueError:
        raise SourceUnavailable("Workable API publication day invalid") from None
    place = row.get("location")
    if (
        not isinstance(place, dict)
        or not isinstance(place.get("country"), str)
        or not place["country"].strip()
        or (place.get("city") is not None and not isinstance(place["city"], str))
        or type(row.get("remote")) is not bool
        or row.get("workplace") not in {"on_site", "hybrid", "remote"}
    ):
        raise SourceUnavailable("Workable API location missing or changed")
    location = ", ".join(s for s in [place.get("city"), place["country"]] if s)
    if row["workplace"] == "hybrid":
        location += " (Hybrid)"
    elif row["workplace"] == "remote":
        location += " (Remote)"
    return dict(
        id=row["shortcode"],
        title=row["title"].strip(),
        location=location,
        contract=CONTRACTS[contract],
        department=departments[-1] if departments else "",
        posted=posted,
        detail=BOARD + "jobs/view/" + row["shortcode"] + ".md",
    )


class WorkableAPICollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if (
            config.name != "Trexquant Investment"
            or config.tenant != "trexquant"
            or config.career_url != BOARD
        ):
            raise ValueError("Use the audited Trexquant public recruitment site")
        self.source, self.config, self.http = source, config, http
        self.options = WorkableAPIOptions(**config.options)
        if self.options.search_terms:
            raise ValueError("Trexquant public API consumes the whole catalogue")

    async def page(self, token: str | None = None):
        body = {"query": ""}
        if token:
            body["token"] = token
        return await self.http.post_search_json(
            API, body, self.config.request_interval, self.source
        )

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Workable API scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        first = await self.page()
        current = first
        candidates: dict[str, dict] = {}
        expected = None
        seen_tokens = set()
        while True:
            page, total, token = rows(current, self.options.max_results_per_query)
            if expected is not None and total != expected:
                raise SourceUnavailable("Workable API total changed during pagination")
            expected = total
            for row in page:
                key = row["shortcode"]
                if key in candidates:
                    raise SourceUnavailable("Workable API pagination repeated posting")
                candidates[key] = row
            if len(candidates) > total:
                raise SourceUnavailable("Workable API search exceeded announced total")
            if token is None:
                break
            if token in seen_tokens:
                raise SourceUnavailable("Workable API pagination repeated cursor")
            seen_tokens.add(token)
            current = await self.page(token)
        if len(candidates) != expected:
            raise SourceUnavailable("Workable API public catalogue incomplete")
        audit = SelectionAudit("public_catalogue")
        selected = []
        for row in candidates.values():
            reason = (
                "internal" if row["isInternal"] else rejection_reason(row["title"], self.options)
            )
            audit.record(reason, row["title"], row["shortcode"])
            if reason is None:
                selected.append(row)
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("Workable API selected detail limit exceeded")
        jobs: list[RawJob] = []
        for row in selected:
            f = facts(row)
            text = await self.http.get_text(f["detail"], self.config.request_interval, self.source)
            job = detail(text, f, self.source, self.config)
            if job is not None:
                jobs.append(job)
        check = await self.page()
        a, total, _ = rows(first, self.options.max_results_per_query)
        b, count, _ = rows(check, self.options.max_results_per_query)
        if total != count or sorted(a, key=lambda r: r["shortcode"]) != sorted(
            b, key=lambda r: r["shortcode"]
        ):
            raise SourceUnavailable("Workable API first page changed during scan")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
