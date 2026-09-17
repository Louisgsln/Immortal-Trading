"""Synthetic public API contracts: no live requests or copied job descriptions."""

import asyncio
import json
from copy import deepcopy

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.goldman import GoldmanCollector, parse_role
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.oracle import OracleCollector, oracle_base


def config(ats, **options):
    return Company(
        name="Demo Bank",
        ats=ats,
        request_interval=0.1,
        career_url="https://higher.gs.com/results"
        if ats == "goldman"
        else "https://demo.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/",
        options=options,
    )


def run(ats, handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def execute():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("demo", config(ats, **options), http).collect()
        finally:
            await http.close()

    return asyncio.run(execute())


def gs_row(i="123", title="Rates Trading Analyst"):
    return {
        "roleId": f"{i}_GS_EARLY_CAREER",
        "jobTitle": title,
        "status": "POSTED",
        "externalSource": {"sourceId": i},
    }


def gs_page(rows, total=None):
    return {
        "data": {"roleSearch": {"totalCount": len(rows) if total is None else total, "items": rows}}
    }


def gs_role(i="123"):
    return {
        **gs_row(i),
        "descriptionHtml": "<p>Trade rates. Requirements: Python, 0-2 years.</p>",
        "applyActive": True,
        "locations": [
            {"city": "London", "country": "United Kingdom"},
            {"city": "Paris", "country": "France"},
        ],
    }


def gs_html(role):
    return (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps({"props": {"pageProps": {"role": role}}})
        + "</script>"
    )


def test_goldman_search_detail_union_and_unknown_dates(monkeypatch):
    queries, details = [], []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method == "POST":
            query = json.loads(req.content)
            assert "mutation" not in query["query"]
            value = query["variables"]["searchQueryInput"]
            assert value["experiences"] == ["EARLY_CAREER", "PROFESSIONAL"]
            assert value["sort"] == {"sortStrategy": "POSTED_DATE", "sortOrder": "DESC"}
            queries.append(value["searchTerm"])
            return httpx.Response(
                200, json=gs_page([gs_row(), gs_row("124", "Trading Operations Analyst")])
            )
        details.append(req.url.path)
        return httpx.Response(200, text=gs_html(gs_role()))

    result = run("goldman", handler, monkeypatch, search_terms=["trading", "rates"])
    assert queries == ["trading", "rates"] and details == ["/roles/123"]
    assert not result.complete and result.requests == 5
    job = result.jobs[0]
    assert job.external_id == "123" and job.apply_url == "https://higher.gs.com/roles/123"
    assert "Python" in job.description and job.location == "London, United Kingdom; Paris, France"
    assert job.date_posted is None and job.expected_start_date is None


def test_goldman_page_numbers(monkeypatch):
    pages = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        page = json.loads(req.content)["variables"]["searchQueryInput"]["page"]["pageNumber"]
        pages.append(page)
        return httpx.Response(
            200,
            json=gs_page(
                [
                    gs_row(str(i), "Trading Operations")
                    for i in range(page * 20, min(page * 20 + 20, 23))
                ],
                23,
            ),
        )

    assert not run("goldman", handler, monkeypatch).jobs
    assert pages == [0, 1]


def test_campus_search_uses_own_category_and_ignores_scheduling_date(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method == "POST":
            value = json.loads(req.content)["variables"]["searchQueryInput"]
            assert value["experiences"] == ["CAMPUS"]
            return httpx.Response(
                200,
                json=gs_page(
                    [{**gs_row(), "roleId": "123_GS_CAMPUS", "startDate": "2026-08-18T00:00:00Z"}]
                ),
            )
        return httpx.Response(200, text=gs_html(gs_role()))

    async def execute():
        co = config("goldman", programme="campus")
        co.career_url = "https://higher.gs.com/campus"
        http = HTTPClient(transport=httpx.MockTransport(handler))
        try:
            return await GoldmanCollector("campus", co, http).collect()
        finally:
            await http.close()

    result = asyncio.run(execute())
    assert result.jobs[0].date_posted is None
    assert result.jobs[0].expected_start_date is None
    assert result.jobs[0].source == "campus" and not result.complete


def test_campus_requires_matching_public_root():
    with pytest.raises(ValueError, match="matching"):
        GoldmanCollector("campus", config("goldman", programme="campus"), None)


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"errors": [{"message": "Unavailable"}], **gs_page([])}, "GraphQL"),
        ({"data": []}, "data missing"),
        (gs_page([], 1), "short"),
        (gs_page([], 2000), "result limit"),
        (gs_page([gs_row(), gs_row()]), "repeated"),
        (gs_page([{**gs_row(), "externalSource": {"sourceId": "../1"}}]), "identifier"),
        (gs_page([{**gs_row(), "jobTitle": ""}]), "malformed"),
        (gs_page([{**gs_row(), "status": None}]), "malformed"),
        (gs_page([], True), "metadata"),
    ],
)
def test_goldman_bad_search(monkeypatch, payload, match):
    def handler(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, json=payload)
        )

    with pytest.raises(SourceUnavailable, match=match):
        run("goldman", handler, monkeypatch)


@pytest.mark.parametrize(
    "html",
    [
        "<html>Challenge</html>",
        gs_html(None),
        gs_html({}),
        gs_html(gs_role("456")),
        gs_html({**gs_role(), "applyActive": None}),
    ],
)
def test_goldman_missing_or_wrong_detail(html):
    with pytest.raises(SourceUnavailable, match="role data"):
        parse_role(html, "123")


def test_goldman_closed_and_filing_ignored(monkeypatch):
    role = gs_role()
    role["applyActive"] = False

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method == "POST":
            return httpx.Response(
                200,
                json=gs_page(
                    [gs_row(), {**gs_row("124"), "roleId": "124_GS_NOTICE_OF_FILING_LCA"}]
                ),
            )
        assert req.url.path == "/roles/123"
        return httpx.Response(200, text=gs_html(role))

    result = run("goldman", handler, monkeypatch)
    assert not result.jobs and not result.complete


def oracle_page(rows, total=None):
    return {
        "items": [
            {"TotalJobsCount": len(rows) if total is None else total, "requisitionList": rows}
        ]
    }


def oracle_row(i=123, title="Rates Trading Analyst"):
    return {
        "Id": i,
        "Title": title,
        "PrimaryLocation": "London, United Kingdom",
        "PostedDate": "2026-09-01",
    }


def test_oracle_full_description_and_finder_pagination(monkeypatch):
    offsets = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert req.method == "GET" and req.url.params["onlyData"] == "true"
        finder = req.url.params["finder"]
        if req.url.path.endswith("recruitingCEJobRequisitions"):
            assert "siteNumber=CX_1001,limit=25,offset=" in finder
            assert "offset" not in req.url.params
            offset = int(finder.split("offset=")[1].split(",")[0])
            offsets.append(offset)
            rows = [oracle_row()] if offset == 0 else [oracle_row(124, "Trading Operations")]
            return httpx.Response(200, json=oracle_page(rows, 2))
        assert finder == "ById;Id=123"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        **oracle_row(),
                        "ShortDescriptionStr": "short",
                        "ExternalDescriptionStr": "<p>Overview</p>",
                        "ExternalResponsibilitiesStr": "<p>Trade rates</p>",
                        "ExternalQualificationsStr": "<p>Python, 0-2 years</p>",
                    }
                ]
            },
        )

    result = run("oracle", handler, monkeypatch)
    assert offsets == [0, 1] and len(result.jobs) == 1 and not result.complete
    job = result.jobs[0]
    assert (
        "Overview" in job.description
        and "Trade rates" in job.description
        and "Python" in job.description
    )
    assert job.date_posted.isoformat() == "2026-09-01T00:00:00+00:00"
    assert job.apply_url.endswith("/CX_1001/job/123")


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"items": []}, "envelope"),
        (oracle_page([], 1), "inconsistent"),
        (oracle_page([], 2000), "result limit"),
        (oracle_page([oracle_row(), oracle_row()]), "repeated"),
        (oracle_page([{**oracle_row(), "Id": "../1"}]), "identifier"),
        ({"items": [{"requisitionList": []}]}, "metadata"),
    ],
)
def test_oracle_bad_search(monkeypatch, payload, match):
    def handler(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, json=payload)
        )

    with pytest.raises(SourceUnavailable, match=match):
        run("oracle", handler, monkeypatch)


@pytest.mark.parametrize(
    "detail",
    [
        {"items": []},
        {"items": [oracle_row()]},
        {"items": [{**oracle_row(999), "ExternalDescriptionStr": "Desc"}]},
    ],
)
def test_oracle_bad_detail(monkeypatch, detail):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200,
            json=oracle_page([oracle_row()])
            if req.url.path.endswith("recruitingCEJobRequisitions")
            else detail,
        )

    with pytest.raises(SourceUnavailable, match="detail"):
        run("oracle", handler, monkeypatch)


@pytest.mark.parametrize("ats", ["goldman", "oracle"])
def test_restricted_access_stops_without_retry(ats, monkeypatch):
    requests = []

    def handler(req):
        requests.append(req)
        return httpx.Response(403)

    with pytest.raises(SourceUnavailable, match="403"):
        run(ats, handler, monkeypatch)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/hcmUI/CandidateExperience/en/sites/CX_1/",
        "https://demo.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/?token=x",
        "https://demo.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/../../workers",
        "http://demo.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/",
    ],
)
def test_oracle_rejects_nonpublic_roots(url):
    with pytest.raises(ValueError):
        oracle_base(url)


def test_invalid_collector_configuration():
    with pytest.raises(ValueError):
        GoldmanCollector("demo", config("oracle"), None)
    with pytest.raises(ValueError):
        OracleCollector("demo", config("oracle", search_terms=["trading,offset=0"]), None)


@pytest.mark.parametrize("ats", ["goldman", "oracle"])
def test_detail_budget_before_fetch(ats, monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        payload = (
            gs_page([gs_row(), gs_row("124")])
            if ats == "goldman"
            else oracle_page([oracle_row(), oracle_row(124)])
        )
        return httpx.Response(200, json=payload)

    with pytest.raises(SourceUnavailable, match="detail limit"):
        run(ats, handler, monkeypatch, max_details=1)


@pytest.mark.parametrize("ats", ["goldman", "oracle"])
def test_changed_total_aborts(ats, monkeypatch):
    count = 0

    def handler(req):
        nonlocal count
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        count += 1
        if ats == "goldman":
            payload = gs_page(
                [gs_row(str(i), "Trading Operations") for i in range(20)], 21 if count == 1 else 22
            )
        else:
            payload = oracle_page([oracle_row(123, "Trading Operations")], 2 if count == 1 else 3)
        return httpx.Response(200, json=deepcopy(payload))

    with pytest.raises(SourceUnavailable, match="total changed"):
        run(ats, handler, monkeypatch)
