import asyncio
import copy
import json

import httpx
import pytest

from tests.test_reliability_lot93 import CITI, REF, SITES, URL, FakeHTTP, detail, search
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.workday import WorkdayCollector
from trading_radar.workday_recovery import public_reference_title


def collect(monkeypatch, alter=None, rows=23):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    company = Company(
        name="Bank",
        ats="workday",
        career_url="https://demo.wd3.myworkdayjobs.com/External",
        request_interval=0.1,
        options={"verify_listing_snapshot": True, "applied_facets": {"family": ["one"]}},
    )
    offsets = []
    first = {
        "total": rows,
        "jobPostings": [
            {"title": "Operations Analyst", "externalPath": f"/job/Paris/{i}", "postedOn": "Today"}
            for i in range(min(rows, 20))
        ],
    }

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        body = json.loads(request.content)
        assert body["appliedFacets"] == {"family": ["one"]}
        offset = body["offset"]
        offsets.append(offset)
        if offset == 0:
            payload = copy.deepcopy(first)
            if len(offsets) > 1 and alter:
                alter(payload)
        else:
            payload = {
                "total": 0,
                "jobPostings": [
                    {"title": "Operations Analyst", "externalPath": f"/job/Paris/{i}"}
                    for i in range(offset, rows)
                ],
            }
        return httpx.Response(200, json=payload)

    async def run():
        h = HTTPClient(retries=0, transport=httpx.MockTransport(handler))
        try:
            return await WorkdayCollector("demo", company, h).collect()
        finally:
            await h.close()

    return asyncio.run(run()), offsets


def test_paginated_query_rechecks_first_page_with_same_scope(monkeypatch):
    result, offsets = collect(monkeypatch)
    assert offsets == [0, 20, 0] and result.scope_complete and not result.complete


def test_single_page_does_not_add_a_redundant_request(monkeypatch):
    _, offsets = collect(monkeypatch, rows=12)
    assert offsets == [0]


@pytest.mark.parametrize(
    "alter",
    [
        lambda p: p.update(total=24),
        lambda p: p["jobPostings"][0].update(externalPath="/job/Paris/other"),
        lambda p: p["jobPostings"][0].update(title="Trading Analyst"),
        lambda p: p["jobPostings"].pop(),
        lambda p: p.update(jobPostings="invalid"),
        lambda p: p.update(total=True),
        lambda p: p["jobPostings"].__setitem__(0, None),
    ],
)
def test_changed_or_invalid_first_page_aborts_snapshot(monkeypatch, alter):
    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, alter)


def test_reordering_and_display_only_posting_age_do_not_fail(monkeypatch):
    def alter(p):
        p["jobPostings"].reverse()
        for row in p["jobPostings"]:
            row["postedOn"] = "Yesterday"

    result, offsets = collect(monkeypatch, alter)
    assert result.scope_complete and offsets == [0, 20, 0]


def test_citi_campus_reference_has_same_exact_public_identity_checks():
    http = FakeHTTP({CITI + "/search-jobs?k=" + REF: search(), URL: detail()})
    result = asyncio.run(public_reference_title("citi_campus", SITES["citi"], REF, http, 2))
    assert result == "Operations Analyst" and len(http.calls) == 2
    other = FakeHTTP({})
    assert (
        asyncio.run(public_reference_title("citi_campus", SITES["citi"] + "x", REF, other, 2))
        is None
    )
    assert not other.calls
