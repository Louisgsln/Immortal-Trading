"""Live consultation reads committed changes, with no transport or business writes."""

import json
import re
from pathlib import Path
from threading import Thread

import httpx
import pytest
from typer.testing import CliRunner

from trading_radar import dashboard, dashboard_cli
from trading_radar.cli import app


def page_data(response):
    assert response.status_code == 200
    match = re.search(
        r'<script id="radar-data" type="application/json">(.*?)</script>', response.text
    )
    assert match
    return json.loads(match[1])


@pytest.fixture
def live(config, repo, tmp_path, monkeypatch):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    state = tmp_path / "jobs.telegram.json"
    state.write_text('{"offset":12345}')
    before_state = state.read_bytes()

    def no_notifier():
        pytest.fail("A dashboard must never initialize notification transport")

    monkeypatch.setattr("trading_radar.notifications.TelegramNotifier.from_env", no_notifier)
    server = dashboard.create_live_dashboard_server(config, tmp_path / "health", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert server.server_address[0] == "127.0.0.1"
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            yield client
        assert state.read_bytes() == before_state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_live_reads_new_committed_jobs_without_writing(live, repo, job):
    first = page_data(live.get("/"))
    assert first["live"] is True and first["summary"]["total"] == 0
    with repo.transaction():
        repo.upsert(job)
    before = list(repo.db.iterdump())
    response = live.get("/index.html")
    second = page_data(response)
    assert second["summary"]["total"] == 1 and second["jobs"][0]["id"] == job.id
    assert first["generated_at"] != second["generated_at"]
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert live.head("/").status_code == 200
    assert live.post("/", content=b"change").status_code == 405
    assert live.get("/data/jobs.db").status_code == 404
    assert live.get("/", headers={"Host": "public.example"}).status_code == 403
    assert list(repo.db.iterdump()) == before


def test_live_read_failure_returns_safe_503_and_recovers(live, repo, monkeypatch):
    original = dashboard.build_dashboard_data
    before = list(repo.db.iterdump())

    def unavailable(*args, **kwargs):
        raise OSError("/private/data/secret.db synthetic-password")

    monkeypatch.setattr(dashboard, "build_dashboard_data", unavailable)
    response = live.get("/")
    assert response.status_code == 503
    assert "secret.db" not in response.text and "synthetic-password" not in response.text
    monkeypatch.setattr(dashboard, "build_dashboard_data", original)
    assert page_data(live.get("/"))["live"] is True
    assert list(repo.db.iterdump()) == before


def test_live_startup_never_creates_a_missing_database(config, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'missing' / 'jobs.db'}"
    with pytest.raises(ValueError, match="unavailable"):
        dashboard.create_live_dashboard_server(config, port=0)
    assert not (tmp_path / "missing").exists()


def test_cli_live_uses_dynamic_reader_and_closes(monkeypatch, config):
    class Server:
        closed = False

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            self.closed = True

    server, calls = Server(), []
    monkeypatch.setattr(dashboard_cli, "load_config", lambda directory: config)
    monkeypatch.setattr(
        dashboard_cli,
        "create_live_dashboard_server",
        lambda current, history, port: calls.append((current, history, port)) or server,
    )
    result = CliRunner().invoke(app, ["dashboard", "serve", "--live", "--port", "8765"])
    assert result.exit_code == 0 and "Live dashboard" in result.output
    assert server.closed and calls == [(config, Path("data/health-history"), 8765)]


def test_live_and_editing_cannot_be_combined(monkeypatch):
    monkeypatch.setattr(dashboard_cli, "load_config", lambda *_: pytest.fail("Invalid mode"))
    result = CliRunner().invoke(app, ["dashboard", "serve", "--live", "--edit-applications"])
    assert result.exit_code == 1
