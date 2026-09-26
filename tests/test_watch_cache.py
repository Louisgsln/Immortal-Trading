"""Cache lifecycle across scans; no real watcher or network is started."""

import asyncio

import httpx
from typer.testing import CliRunner

from trading_radar import cli, scanner
from trading_radar.http import HTTPClient
from trading_radar.http_cache import JSONCache
from trading_radar.models import Collection, ScanMetrics


def test_watch_passes_one_cache_to_successive_scans(config, repo, monkeypatch, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    caches = []

    async def watch_sources(*args, **kwargs):
        for _ in range(2):
            caches.append(kwargs["json_cache"])
            yield ScanMetrics()

    monkeypatch.setattr(cli, "resources", lambda directory: (config, repo, None))
    monkeypatch.setattr(cli, "watch_sources", watch_sources)
    result = CliRunner().invoke(cli.app, ["watch"])
    assert result.exit_code == 0, result.output
    assert len(caches) == 2 and caches[0] is caches[1]
    assert isinstance(caches[0], JSONCache)


def test_scans_revalidate_robots_with_fresh_clients_and_shared_cache(config, repo, monkeypatch):
    cache = JSONCache()
    requests = []
    clients = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if request.headers.get("If-None-Match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, json={"value": "current"}, headers={"ETag": '"v1"'})

    def http(*args, **kwargs):
        client = HTTPClient(*args, transport=httpx.MockTransport(respond), **kwargs)
        clients.append(client)
        return client

    class Collector:
        def __init__(self, http):
            self.http = http

        async def collect(self):
            value = await self.http.get_conditional_json("https://example.com/detail", 0, "test")
            assert value == {"value": "current"}
            return Collection(jobs=[], complete=False)

    monkeypatch.setattr(scanner, "HTTPClient", http)
    monkeypatch.setattr(scanner, "build_collector", lambda key, company, http: Collector(http))
    for _ in range(2):
        result = asyncio.run(scanner.scan(config, repo, json_cache=cache))
        assert not result.failed
    assert len(clients) == 2 and clients[0] is not clients[1]
    assert all(client.client.is_closed for client in clients)
    assert [request.url.path for request in requests] == [
        "/robots.txt",
        "/detail",
        "/robots.txt",
        "/detail",
    ]
    assert "If-None-Match" not in requests[1].headers
    assert requests[3].headers["If-None-Match"] == '"v1"'
