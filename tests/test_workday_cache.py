import asyncio
import json
from pathlib import Path

import httpx
import pytest

from trading_radar.config import Company
from trading_radar.http import HTTPClient
from trading_radar.http_cache import JSONCache
from trading_radar.search_scope import SearchOptions
from trading_radar.workday import WorkdayCollector, WorkdayOptions


@pytest.mark.parametrize("enabled", [False, True])
def test_workday_cache_only_details_opt_in_across_scans(monkeypatch, enabled):
    requests = []
    details = 0
    config = Company(
        name="Demo",
        ats="workday",
        tenant="demo",
        career_url="https://demo.wd3.myworkdayjobs.com/External",
        request_interval=0.1,
        options={"conditional_details": enabled},
    )

    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    def handler(request):
        nonlocal details
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            assert "if-none-match" not in request.headers
            return httpx.Response(
                200, json=json.loads(Path("tests/fixtures/workday_search.json").read_text())
            )
        details += 1
        if details == 2 and enabled:
            assert request.headers["if-none-match"] == '"same"'
            return httpx.Response(304)
        assert "if-none-match" not in request.headers
        return httpx.Response(
            200,
            json=json.loads(Path("tests/fixtures/workday_detail.json").read_text()),
            headers={"etag": '"same"'},
        )

    async def run():
        cache = JSONCache()
        collections = []
        for _ in range(2):
            http = HTTPClient(transport=httpx.MockTransport(handler), json_cache=cache)
            try:
                collections.append(await WorkdayCollector("demo", config, http).collect())
            finally:
                await http.close()
        return collections, cache

    collections, cache = asyncio.run(run())
    assert collections[0].jobs[0].model_dump() == collections[1].jobs[0].model_dump()
    assert all(not collection.complete and collection.requests == 3 for collection in collections)
    assert len(requests) == 6
    assert len(cache.entries) == int(enabled)


def test_workday_cache_option_is_strict_and_not_shared_with_other_adapters():
    assert WorkdayOptions().conditional_details is False
    with pytest.raises(ValueError):
        WorkdayOptions(conditional_details="true")
    with pytest.raises(ValueError):
        SearchOptions(conditional_details=True)
