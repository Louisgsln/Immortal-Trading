"""A public masked State Street row must not hide other verified vacancies."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from tests.test_workday_restarts177 import execute, row
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.workday import WorkdayCollector


def test_state_street_collects_valid_details_and_keeps_masked_reference_visible(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"total": 2, "jobPostings": [{"bulletFields": ["R-794329"]}, row(1)]},
            )
        detail = json.loads(Path("tests/fixtures/workday_detail.json").read_text())
        detail["jobPostingInfo"]["title"] = "Trading Analyst"
        return httpx.Response(200, json=detail)

    async def collect():
        company = Company(
            name="State Street",
            ats="workday",
            career_url="https://statestreet.wd1.myworkdayjobs.com/Global",
        )
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await WorkdayCollector("state_street", company, http).collect()
        finally:
            await http.close()

    result = asyncio.run(collect())
    assert len(result.jobs) == 1 and result.jobs[0].external_id == "stable-public-posting-id"
    assert result.listing_gaps == ["R-794329"] and not result.complete
    assert not result.withdrawn and not result.conflicts
    assert len([request for request in requests if request.method == "GET"]) == 2
    assert not any("R-794329" in str(request.url) for request in requests)


@pytest.mark.parametrize(
    "placeholder",
    [
        {"bulletFields": ["R794329"]},
        {"bulletFields": ["R-7943290"]},
        {"bulletFields": ["R-79432"]},
        {"bulletFields": [" R-794329"]},
        {"bulletFields": ["R-794329", "other"]},
        {"bulletFields": ["R-794329"], "unknown": True},
        {"bulletFields": [794329]},
    ],
)
def test_state_street_placeholder_keeps_strict_shape(monkeypatch, placeholder):
    with pytest.raises(SourceUnavailable, match="malformed"):
        execute(
            monkeypatch,
            lambda _: httpx.Response(200, json={"total": 1, "jobPostings": [placeholder]}),
            source="state_street",
        )


def test_state_street_placeholder_does_not_weaken_other_sources(monkeypatch):
    with pytest.raises(SourceUnavailable, match="malformed"):
        execute(
            monkeypatch,
            lambda _: httpx.Response(
                200, json={"total": 1, "jobPostings": [{"bulletFields": ["R-794329"]}]}
            ),
            source="bank_of_america",
        )
