import asyncio
from types import SimpleNamespace

import httpx
import pytest

from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.http_cache import JSONCache

URL = "https://example.com/job/1"
VALIDATORS = {"etag": '"version-1"', "last-modified": "Mon, 14 Sep 2026 12:00:00 GMT"}


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)


def run_requests(responses, *, cache=None, sources=None, client_headers=None):
    requests = []
    responses = iter(responses)

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    async def run():
        http = HTTPClient(retries=0, transport=httpx.MockTransport(handler), json_cache=cache)
        if client_headers:
            http.client.headers.update(client_headers)
        results = []
        try:
            for source in sources or ["source"]:
                results.append(await http.get_conditional_json(URL, 0.1, source))
        finally:
            await http.close()
        return results, requests

    return asyncio.run(run())


def test_revalidate_across_clients_fetches_robots_again_and_copies_json():
    cache = JSONCache()
    first, first_requests = run_requests(
        [httpx.Response(200, json={"title": "Trader"}, headers=VALIDATORS)], cache=cache
    )
    first[0]["title"] = "mutated"
    second, requests = run_requests([httpx.Response(304)], cache=cache)
    assert second == [{"title": "Trader"}]
    assert [r.url.path for r in first_requests] == ["/robots.txt", "/job/1"]
    assert [r.url.path for r in requests] == ["/robots.txt", "/job/1"]
    assert requests[-1].headers["if-none-match"] == VALIDATORS["etag"]
    assert requests[-1].headers["if-modified-since"] == VALIDATORS["last-modified"]
    assert "if-none-match" not in requests[0].headers


@pytest.mark.parametrize("validator", ["etag", "last-modified"])
def test_single_validator(validator):
    cache = JSONCache()
    results, requests = run_requests(
        [
            httpx.Response(200, json={"v": 1}, headers={validator: VALIDATORS[validator]}),
            httpx.Response(304),
        ],
        cache=cache,
        sources=["s", "s"],
    )
    assert results == [{"v": 1}, {"v": 1}]
    assert ("if-none-match" in requests[-1].headers) == (validator == "etag")
    assert ("if-modified-since" in requests[-1].headers) == (validator == "last-modified")


def test_changed_200_replaces_body_and_validators():
    cache = JSONCache()
    results, requests = run_requests(
        [
            httpx.Response(200, json={"v": 1}, headers=VALIDATORS),
            httpx.Response(200, json={"v": 2}, headers={"etag": '"v2"'}),
            httpx.Response(304),
        ],
        cache=cache,
        sources=["s"] * 3,
    )
    assert results == [{"v": 1}, {"v": 2}, {"v": 2}]
    assert requests[-1].headers["if-none-match"] == '"v2"'
    assert "if-modified-since" not in requests[-1].headers


@pytest.mark.parametrize("status", [301, 401, 403, 404, 429, 500, 503])
def test_failure_never_serves_stale_and_evicts(status):
    cache = JSONCache()
    run_requests([httpx.Response(200, json={"v": 1}, headers=VALIDATORS)], cache=cache)
    with pytest.raises(SourceUnavailable):
        run_requests([httpx.Response(status)], cache=cache)
    assert cache.get("source", URL) is None


def test_transport_error_evicts():
    cache = JSONCache()
    cache.put("source", URL, b"{}", httpx.Headers(VALIDATORS))
    with pytest.raises(SourceUnavailable, match="transport"):
        run_requests([httpx.ConnectError("unavailable")], cache=cache)
    assert cache.get("source", URL) is None


@pytest.mark.parametrize("cache", [None, JSONCache()])
def test_unsolicited_304_fails(cache):
    with pytest.raises(SourceUnavailable, match="304"):
        run_requests([httpx.Response(304)], cache=cache)


def test_source_identity_is_part_of_key():
    cache = JSONCache()
    _, requests = run_requests(
        [httpx.Response(200, json={}, headers=VALIDATORS)] * 2,
        cache=cache,
        sources=["one", "two"],
    )
    assert "if-none-match" not in requests[-1].headers
    assert len(cache.entries) == 2


@pytest.mark.parametrize(
    "headers",
    [
        {"cache-control": "no-store"},
        {"cache-control": "public, No-Store=1"},
        {"cache-control": "private"},
        {"vary": "Accept-Encoding"},
        {"vary": "*"},
        {"set-cookie": "session=example"},
    ],
)
def test_noncacheable_response_replaces_old_entry(headers):
    cache = JSONCache()
    cache.put("source", URL, b"{}", httpx.Headers(VALIDATORS))
    result, _ = run_requests(
        [httpx.Response(200, json={"v": 2}, headers=VALIDATORS | headers)], cache=cache
    )
    assert result == [{"v": 2}] and cache.get("source", URL) is None


@pytest.mark.parametrize(
    "headers",
    [{"authorization": "Bearer dummy"}, {"cookie": "session=dummy"}, {"cache-control": "no-store"}],
)
def test_authenticated_or_no_store_request_bypasses_cache(headers):
    cache = JSONCache()
    cache.put("source", URL, b"{}", httpx.Headers(VALIDATORS))
    _, requests = run_requests(
        [httpx.Response(200, json={}, headers=VALIDATORS)], cache=cache, client_headers=headers
    )
    assert "if-none-match" not in requests[-1].headers
    assert cache.get("source", URL) is None


def test_no_cache_is_revalidated_normally():
    cache = JSONCache()
    result, requests = run_requests(
        [
            httpx.Response(200, json={}, headers=VALIDATORS | {"cache-control": "no-cache"}),
            httpx.Response(304),
        ],
        cache=cache,
        sources=["s", "s"],
    )
    assert result == [{}, {}] and "if-none-match" in requests[-1].headers


@pytest.mark.parametrize(
    "headers",
    [
        {"etag": '"different"'},
        {"last-modified": "different"},
        {"cache-control": "no-store"},
        {"vary": "*"},
    ],
)
def test_incompatible_304_fails_closed(headers):
    cache = JSONCache()
    cache.put("source", URL, b"{}", httpx.Headers(VALIDATORS))
    with pytest.raises(SourceUnavailable, match="metadata"):
        run_requests([httpx.Response(304, headers=headers)], cache=cache)
    assert cache.get("source", URL) is None


def test_invalid_json_replaces_no_data():
    cache = JSONCache()
    cache.put("source", URL, b"{}", httpx.Headers(VALIDATORS))
    with pytest.raises(SourceUnavailable, match="JSON"):
        run_requests([httpx.Response(200, text="challenge", headers=VALIDATORS)], cache=cache)
    assert cache.get("source", URL) is None


def test_no_validator_evicts_old_entry():
    cache = JSONCache()
    cache.put("source", URL, b"{}", httpx.Headers(VALIDATORS))
    run_requests([httpx.Response(200, json={})], cache=cache)
    assert cache.get("source", URL) is None


def test_ttl_304_does_not_extend_residence():
    now = [0.0]
    cache = JSONCache(ttl=10, clock=lambda: now[0])
    cache.put("source", URL, b"{}", httpx.Headers(VALIDATORS))
    now[0] = 9
    run_requests([httpx.Response(304)], cache=cache)
    now[0] = 10
    _, requests = run_requests([httpx.Response(200, json={}, headers=VALIDATORS)], cache=cache)
    assert "if-none-match" not in requests[-1].headers


def test_memory_bounds_and_lru():
    cache = JSONCache(max_entries=2, max_bytes=5, max_entry_bytes=3)
    headers = httpx.Headers(VALIDATORS)
    cache.put("s", "a", b"{}", headers)
    cache.put("s", "b", b"{}", headers)
    cache.get("s", "a")
    cache.put("s", "c", b"{}", headers)
    assert list(cache.entries) == [("s", "a"), ("s", "c")]
    cache.put("s", "c", b"1234", headers)
    assert cache.get("s", "c") is None and cache.size_bytes == 2
    cache.put("s", "d", b"123", headers)
    assert cache.size_bytes == 5
    cache.put("s", "e", b"123", headers)
    assert list(cache.entries) == [("s", "e")] and cache.size_bytes == 3


@pytest.mark.parametrize(
    "kwargs", [{"max_entries": 0}, {"max_bytes": 0}, {"max_entry_bytes": 0}, {"ttl": 0}]
)
def test_bad_bounds(kwargs):
    with pytest.raises(ValueError):
        JSONCache(**kwargs)


def test_robots_recheck_denies_previously_cached_body():
    cache = JSONCache()
    cache.put("s", URL, b"{}", httpx.Headers(VALIDATORS))
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nDisallow: /")

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), json_cache=cache)
        try:
            with pytest.raises(SourceUnavailable, match="robots"):
                await http.get_conditional_json(URL, 0.1, "s")
        finally:
            await http.close()

    asyncio.run(run())
    assert paths == ["/robots.txt"] and cache.get("s", URL) is None


def test_304_requests_obey_crawl_delay(monkeypatch):
    now, calls = [100.0], []
    monkeypatch.setattr("trading_radar.http.time", SimpleNamespace(monotonic=lambda: now[0]))

    async def advance(delay):
        now[0] += delay

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", advance)

    def handler(request):
        calls.append((request.url.path, now[0]))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\nCrawl-delay: 5")
        return httpx.Response(304)

    async def run():
        cache = JSONCache()
        cache.put("s", URL, b"{}", httpx.Headers(VALIDATORS))
        http = HTTPClient(transport=httpx.MockTransport(handler), json_cache=cache)
        try:
            assert await http.get_conditional_json(URL, 2, "s") == {}
            assert await http.get_conditional_json(URL, 2, "s") == {}
        finally:
            await http.close()

    asyncio.run(run())
    assert calls == [("/robots.txt", 100), ("/job/1", 105), ("/job/1", 110)]


def test_expiry_during_request_rejects_304():
    now = [0.0]
    cache = JSONCache(ttl=10, clock=lambda: now[0])
    cache.put("s", URL, b"{}", httpx.Headers(VALIDATORS))

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        now[0] = 10
        return httpx.Response(304)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), json_cache=cache)
        try:
            with pytest.raises(SourceUnavailable, match="valid cached"):
                await http.get_conditional_json(URL, 0.1, "s")
        finally:
            await http.close()

    asyncio.run(run())
    assert cache.size_bytes == 0


def test_cookie_from_robots_prevents_revalidation_and_storage():
    cache = JSONCache()
    cache.put("s", URL, b"{}", httpx.Headers(VALIDATORS))

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"set-cookie": "session=test; Path=/"})
        assert "cookie" in request.headers
        assert "if-none-match" not in request.headers
        return httpx.Response(200, json={"new": True}, headers=VALIDATORS)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), json_cache=cache)
        try:
            assert await http.get_conditional_json(URL, 0.1, "s") == {"new": True}
        finally:
            await http.close()

    asyncio.run(run())
    assert cache.get("s", URL) is None


@pytest.mark.parametrize(
    "source,url,headers",
    [
        ("s" * 257, URL, VALIDATORS),
        ("s", "https://example.com/" + "a" * 4096, VALIDATORS),
        ("s", URL, {"etag": "a" * 513}),
        ("s", URL, {"last-modified": "a" * 513}),
    ],
)
def test_cache_metadata_is_bounded(source, url, headers):
    cache = JSONCache()
    cache.put(source, url, b"{}", httpx.Headers(headers))
    assert len(cache.entries) == 0 and cache.size_bytes == 0


def test_disabled_cache_never_sends_conditionals():
    _, requests = run_requests(
        [httpx.Response(200, json={}, headers=VALIDATORS)] * 2,
        sources=["s", "s"],
    )
    assert all("if-none-match" not in request.headers for request in requests)
