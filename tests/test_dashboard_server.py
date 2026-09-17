"""The local preview serves a single snapshot and exposes no writable endpoint."""

from threading import Thread

import httpx
import pytest
from typer.testing import CliRunner

from trading_radar import dashboard_cli
from trading_radar.cli import app
from trading_radar.dashboard import create_dashboard_server


@pytest.fixture
def preview():
    server = create_dashboard_server("<!doctype html><p>Local snapshot</p>", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert server.server_address[0] == "127.0.0.1"
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            yield client
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_preview_only_serves_snapshot_and_protective_headers(preview):
    response = preview.get("/")
    assert response.status_code == 200
    assert "Local snapshot" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    policy = response.headers["content-security-policy"]
    assert "connect-src 'none'" in policy and "frame-ancestors 'none'" in policy
    assert "unsafe-inline" not in policy
    head = preview.head("/index.html")
    assert head.status_code == 200 and not head.content


@pytest.mark.parametrize(
    "path", ["/config/settings.yaml", "/data/jobs.db", "/../.env", "/api/jobs"]
)
def test_preview_never_serves_directory_contents(preview, path):
    assert preview.get(path).status_code == 404


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def test_preview_refuses_write_methods(preview, method):
    assert preview.request(method, "/", content=b"change something").status_code == 405


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "attacker.example"},
        {"Origin": "https://attacker.example"},
        {"Origin": "null"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_preview_rejects_foreign_host_and_cross_site_reads(preview, headers):
    assert preview.get("/", headers=headers).status_code == 403


def test_cli_serve_builds_once_and_closes_on_interrupt(monkeypatch, config):
    reads = []

    class Server:
        closed = False

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            self.closed = True

    server = Server()
    monkeypatch.setattr(dashboard_cli, "load_config", lambda directory: config)
    monkeypatch.setattr(
        dashboard_cli, "build_dashboard_data", lambda *a, **k: reads.append(1) or {}
    )
    monkeypatch.setattr(dashboard_cli, "render_dashboard", lambda data: "snapshot")
    monkeypatch.setattr(dashboard_cli, "create_dashboard_server", lambda *a: server)
    result = CliRunner().invoke(app, ["dashboard", "serve", "--port", "8765"])
    assert result.exit_code == 0, result.output
    assert "127.0.0.1:8765" in result.output and server.closed and reads == [1]


def test_cli_serve_rejects_busy_port_cleanly(monkeypatch, config):
    def busy(*args):
        raise OSError("Private path or machine information must not leak")

    monkeypatch.setattr(dashboard_cli, "load_config", lambda directory: config)
    monkeypatch.setattr(dashboard_cli, "build_dashboard_data", lambda *a, **k: {})
    monkeypatch.setattr(dashboard_cli, "render_dashboard", lambda data: "snapshot")
    monkeypatch.setattr(dashboard_cli, "create_dashboard_server", busy)
    result = CliRunner().invoke(app, ["dashboard", "serve"])
    assert result.exit_code == 1
    assert "Private path" not in result.output
