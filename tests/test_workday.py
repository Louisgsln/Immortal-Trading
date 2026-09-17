import asyncio
import json
from pathlib import Path

import httpx
import pytest

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.workday import WorkdayCollector, WorkdayOptions, external_path, workday_base


@pytest.fixture
def workday_config():
    return Company(
        name="Demo Bank",
        ats="workday",
        tenant="demo",
        career_url="https://demo.wd3.myworkdayjobs.com/en-US/External",
        request_interval=0.1,
    )


def fixture(name):
    return json.loads(Path(f"tests/fixtures/workday_{name}.json").read_text())


def execute(config, handler, monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await WorkdayCollector("demo", config, http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_search_details_and_scope(workday_config, monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            body = json.loads(request.content)
            assert body == {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "trading"}
            return httpx.Response(200, json=fixture("search"))
        return httpx.Response(200, json=fixture("detail"))

    result = execute(workday_config, handler, monkeypatch)
    assert len(result.jobs) == 1 and not result.complete
    job = result.jobs[0]
    assert job.external_id == "stable-public-posting-id"
    assert job.location == "London, United Kingdom; Paris, France"
    assert (
        job.apply_url == "https://demo.wd3.myworkdayjobs.com/External/job/London/Trading-Analyst_R1"
    )
    assert job.date_posted.isoformat() == "2026-09-01T00:00:00+00:00"
    assert job.expected_start_date is None
    assert "Python" in job.description and result.requests == 3


def test_pagination_zero_total_after_first_page(workday_config, monkeypatch):
    offsets = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            offset = json.loads(request.content)["offset"]
            offsets.append(offset)
            rows = [
                {"title": "Trading Operations Analyst", "externalPath": f"/job/Paris/R{i}"}
                for i in range(offset, min(offset + 20, 23))
            ]
            return httpx.Response(
                200, json={"total": 23 if offset == 0 else 0, "jobPostings": rows}
            )
        raise AssertionError("Excluded titles should not fetch details")

    result = execute(workday_config, handler, monkeypatch)
    assert offsets == [0, 20] and not result.jobs and not result.complete


@pytest.mark.parametrize(
    "payload,error",
    [
        ({"total": 2000, "jobPostings": []}, "result limit"),
        ({"total": 20, "jobPostings": []}, "short"),
        ({"jobPostings": []}, "metadata"),
        (
            {"total": 1, "jobPostings": [{"title": "Trader", "externalPath": "//evil.test/steal"}]},
            "path",
        ),
    ],
)
def test_bad_snapshots_fail(workday_config, monkeypatch, payload, error):
    def handler(request):
        return (
            httpx.Response(404)
            if request.url.path == "/robots.txt"
            else httpx.Response(200, json=payload)
        )

    with pytest.raises(SourceUnavailable, match=error):
        execute(workday_config, handler, monkeypatch)


def test_detail_failure_never_returns_successful_snapshot(workday_config, monkeypatch):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return (
            httpx.Response(200, json=fixture("search"))
            if request.method == "POST"
            else httpx.Response(404)
        )

    with pytest.raises(SourceUnavailable, match="404"):
        execute(workday_config, handler, monkeypatch)


def test_duplicate_pages_fail(workday_config, monkeypatch):
    rows = [{"title": "Trader", "externalPath": f"/job/Paris/R{i}"} for i in range(20)]

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, json={"total": 40, "jobPostings": rows})

    with pytest.raises(SourceUnavailable, match="repeated"):
        execute(workday_config, handler, monkeypatch)


def test_cross_query_dedup(workday_config, monkeypatch):
    workday_config.options = {"search_terms": ["trading", "trader"]}
    details = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            return httpx.Response(200, json=fixture("search"))
        details.append(request)
        return httpx.Response(200, json=fixture("detail"))

    assert len(execute(workday_config, handler, monkeypatch).jobs) == 1
    assert len(details) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://demo.wd3.myworkdayjobs.com/External",
        "https://demo.wd3.myworkdayjobs.com.evil.test/External",
        "https://localhost/External",
        "https://demo.wd3.myworkdayjobs.com/External/login",
        "https://demo.wd3.myworkdayjobs.com/../External",
    ],
)
def test_validate_workday_url(workday_config, url):
    workday_config.career_url = url
    with pytest.raises(ValueError):
        workday_base(workday_config)


@pytest.mark.parametrize(
    "path", ["/job/../login", "/job/%2e%2e/login", "/job/a?next=evil", "/job/a\\b"]
)
def test_validate_paths(path):
    with pytest.raises(SourceUnavailable):
        external_path(path)


def test_options_strict():
    with pytest.raises(ValueError):
        WorkdayOptions(proxies="anything")
    with pytest.raises(ValueError):
        WorkdayOptions(search_terms=[""])


def test_cross_query_changed_title_aborts_before_details(workday_config, monkeypatch):
    workday_config.options = {"search_terms": ["trading", "structuring"]}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert request.method == "POST", "No details before consistency validation"
        payload = fixture("search")
        if json.loads(request.content)["searchText"] == "structuring":
            payload["jobPostings"][0]["title"] = "Trading Operations Analyst"
        return httpx.Response(200, json=payload)

    with pytest.raises(SourceUnavailable, match="title changed"):
        execute(workday_config, handler, monkeypatch)
