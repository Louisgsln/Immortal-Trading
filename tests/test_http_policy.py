import asyncio
from types import SimpleNamespace

import httpx
import pytest

import trading_radar.http as http_module
from trading_radar.http import HTTPClient, SourceUnavailable


@pytest.mark.parametrize(
    "policy,path,allowed",
    [
        ("Disallow: /\nAllow: /careers", "/careers?query=trading", True),
        ("Disallow: /\nAllow: /careers", "/api/private", False),
        ("Allow: /careers\nDisallow: /careers/private", "/careers/private/1", False),
        ("Disallow: /\nAllow: /$", "/", True),
        ("Disallow: /\nAllow: /$", "/other", False),
        ("Allow: /careers\nDisallow: /*?token=", "/careers?token=x", False),
        ("Disallow: /same\nAllow: /same", "/same", True),
        ("Disallow: /caf%C3%A9", "/caf%C3%A9", False),
        ("Disallow: /private", "/%70rivate", False),
        ("Disallow: /Careers", "/careers", True),
    ],
)
def test_robot_rules_before_any_endpoint_request(monkeypatch, policy, path, allowed):
    calls = []

    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    def handler(req):
        calls.append(req.url.path)
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\n" + policy)
        return httpx.Response(200, text="public data")

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            if allowed:
                assert (
                    await http.get_text("https://example.com" + path, 0.1, "test") == "public data"
                )
            else:
                with pytest.raises(SourceUnavailable, match="robots policy disallows"):
                    await http.get_text("https://example.com" + path, 0.1, "test")
            assert len(calls) == (2 if allowed else 1)
        finally:
            await http.close()

    asyncio.run(run())


def test_specific_agent_merged_groups_crawl_delay_and_cache():
    calls = []
    policy = (
        "User-agent: *\nDisallow: /\n\n"
        "User-agent: TradingJobRadar\nDisallow: /private\nCrawl-delay: 3.5\n\n"
        "User-agent: tradingjobradar\nDisallow: /secret\n"
    )

    async def request(url, interval, source, **kwargs):
        calls.append((url, interval))
        return httpx.Response(200, text=policy if url.endswith("robots.txt") else "ok")

    async def run():
        http = HTTPClient()
        http._request = request
        try:
            assert await http.get_text("https://example.com/careers", 2, "test") == "ok"
            for path in ["/private", "/secret"]:
                with pytest.raises(SourceUnavailable, match="robots"):
                    await http.get_text("https://example.com" + path, 2, "test")
            assert calls == [
                ("https://example.com/robots.txt", 2),
                ("https://example.com/careers", 3.5),
            ]
        finally:
            await http.close()

    asyncio.run(run())


def test_new_crawl_delay_applies_to_first_page_after_robots(monkeypatch):
    now, calls = [100.0], []
    monkeypatch.setattr(http_module, "time", SimpleNamespace(monotonic=lambda: now[0]))

    async def advance(delay):
        now[0] += delay

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", advance)

    def handler(req):
        calls.append((req.url.path, now[0]))
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nCrawl-delay: 5\nAllow: /")
        return httpx.Response(200, text="ok")

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            await http.get_text("https://example.com/first", 2, "test")
            await http.get_text("https://example.com/second", 2, "test")
            assert calls == [("/robots.txt", 100.0), ("/first", 105.0), ("/second", 110.0)]
        finally:
            await http.close()

    asyncio.run(run())


@pytest.mark.parametrize("status", [301, 401, 403, 429, 500])
def test_unavailable_policy_never_fetches_endpoint(status):
    calls = []

    def handler(req):
        calls.append(req.url.path)
        return httpx.Response(status)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            with pytest.raises(SourceUnavailable):
                await http.get_text("https://example.com/careers", 0.1, "test")
            assert calls == ["/robots.txt"]
        finally:
            await http.close()

    asyncio.run(run())
