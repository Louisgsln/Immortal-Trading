import asyncio
import json
from pathlib import Path

import httpx
import pytest

from trading_radar.collectors import PublicATSCollector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable


@pytest.mark.parametrize("ats", ["greenhouse", "lever", "ashby"])
def test_public_ats_fixture(ats):
    payload = json.loads(Path(f"tests/fixtures/{ats}.json").read_text())

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, json=payload)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler))
        co = Company(name="Test", ats=ats, tenant="test", request_interval=0.1)
        try:
            result = await PublicATSCollector("test", co, http).collect()
            assert result.complete and len(result.jobs) == 1
            assert result.requests == 2
            assert result.jobs[0].company == "Test"
            if ats == "greenhouse":
                assert result.jobs[0].date_posted is None
        finally:
            await http.close()

    asyncio.run(run())


def test_retry_and_robots(monkeypatch):
    calls = []

    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        calls.append(str(request.url))
        return (
            httpx.Response(429, headers={"Retry-After": "1"})
            if len(calls) == 1
            else httpx.Response(200, json={"jobs": []})
        )

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler))
        try:
            assert await http.get_json("https://example.com/jobs", 0.1, "test") == {"jobs": []}
            assert len(calls) == 2
            with pytest.raises(SourceUnavailable, match="robots"):
                await http.get_json("https://example.com/private", 0.1, "test")
            assert len(calls) == 2
        finally:
            await http.close()

    asyncio.run(run())


@pytest.mark.parametrize("status", [301, 401, 403])
def test_access_restrictions_are_not_retried(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(SourceUnavailable):
                await http.get_json("https://example.com/jobs", 0.1, "test")
            assert len(calls) == 1
        finally:
            await http.close()

    asyncio.run(run())


def test_lever_pagination(monkeypatch):
    row = json.loads(Path("tests/fixtures/lever.json").read_text())[0]

    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        start = int(request.url.params["skip"])
        return httpx.Response(
            200, json=[{**row, "id": str(i)} for i in range(start, 100 if start == 0 else 101)]
        )

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler))
        try:
            result = await PublicATSCollector(
                "test", Company(name="Test", ats="lever", tenant="test"), http
            ).collect()
            assert len(result.jobs) == 101 and result.complete
        finally:
            await http.close()

    asyncio.run(run())
