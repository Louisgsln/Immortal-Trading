"""Private startup and concurrent consultation never wait for a large snapshot."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock, Thread

import httpx
import pytest

from tests.test_dashboard_editor_server import rows
from tests.test_dashboard_private_editor import ACCESS
from trading_radar import dashboard_editor as editor
from trading_radar.dashboard import render_dashboard


def data(response):
    assert response.status_code == 200
    return json.loads(re.search(r'<script id="radar-data"[^>]*>(.*?)</script>', response.text)[1])


@pytest.fixture
def progressive(config, repo, job, tmp_path, monkeypatch):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    with repo.transaction():
        repo.upsert(job)
    control = tmp_path / "jobs.telegram.json"
    control.write_text('{"offset":12345}')
    before_control = control.read_bytes()
    original = editor.build_dashboard_data

    def forbidden(*args, **kwargs):
        pytest.fail("The shell and startup must not build a snapshot")

    monkeypatch.setattr(editor, "build_dashboard_data", forbidden)
    monkeypatch.setattr(
        "trading_radar.notifications.TelegramNotifier.from_env",
        lambda: pytest.fail("A Dashboard cannot initialize Telegram transport"),
    )
    server = editor.create_editable_dashboard_server(
        config, tmp_path / "history", 0, private_access=ACCESS, progressive=True
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            response = client.get("/", headers={"X-Radar-Gateway": ACCESS.gateway_secret})
            initial = data(response)
            assert initial["status"] == "loading" and initial["jobs"] == []
            assert "summary" not in initial and job.id not in response.text
            assert 'data-loading="true"' in response.text
            assert len(response.content) < 256 * 1024
            headers = {
                "X-Radar-Gateway": ACCESS.gateway_secret,
                "Cookie": response.headers["set-cookie"].split(";", 1)[0],
                "X-Radar-Token": initial["editing"]["token"],
                "Origin": ACCESS.origin,
                "Sec-Fetch-Site": "same-origin",
            }
            assert client.head("/index.html", headers=headers).status_code == 200
            monkeypatch.setattr(editor, "build_dashboard_data", original)
            yield client, headers, job.id
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert control.read_bytes() == before_control


def test_complete_snapshot_reads_latest_tracking_without_writes(progressive, repo):
    client, headers, job_id = progressive
    before = rows(repo)
    first = client.get("/api/snapshot", headers=headers)
    assert first.status_code == 200 and first.json()["summary"]["total"] == 1
    assert first.json()["jobs"][0]["id"] == job_id
    assert first.json()["live"] is True and "editing" not in first.json()
    assert rows(repo) == before
    repo.update_application(job_id, {"status": "To Apply", "notes": "Recent mobile edit"})
    before = rows(repo)
    second = client.get("/api/snapshot", headers=headers)
    assert second.json()["jobs"][0]["application"]["notes"] == "Recent mobile edit"
    assert first.json()["generated_at"] != second.json()["generated_at"]
    assert second.headers["cache-control"] == "no-store"
    assert rows(repo) == before


@pytest.mark.parametrize("missing", ["X-Radar-Gateway", "Cookie", "X-Radar-Token"])
@pytest.mark.parametrize("endpoint", ["/api/snapshot", "/api/services"])
def test_snapshot_requires_gateway_session_and_token(progressive, repo, missing, endpoint):
    client, headers, _ = progressive
    before = rows(repo)
    assert (
        client.get(endpoint, headers={k: v for k, v in headers.items() if k != missing}).status_code
        == 403
    )
    assert rows(repo) == before


@pytest.mark.parametrize(
    "override",
    [
        {"Origin": "https://other.example"},
        {"Sec-Fetch-Site": "cross-site"},
        {"X-Radar-Token": "wrong"},
        {"Cookie": "radar_session=forged"},
    ],
)
@pytest.mark.parametrize("endpoint", ["/api/snapshot", "/api/services"])
def test_snapshot_rejects_forged_or_cross_site_access(progressive, override, endpoint):
    client, headers, _ = progressive
    assert client.get(endpoint, headers=headers | override).status_code == 403


def test_snapshot_failure_is_safe_and_recoverable(progressive, repo, monkeypatch):
    client, headers, _ = progressive
    original = editor.build_dashboard_data
    before = rows(repo)

    def unavailable(*args, **kwargs):
        raise OSError("/private/secret.db password")

    monkeypatch.setattr(editor, "build_dashboard_data", unavailable)
    response = client.get("/api/snapshot", headers=headers)
    assert response.status_code == 503 and response.json()["error"]["code"] == "unavailable"
    assert "secret.db" not in response.text and "password" not in response.text
    monkeypatch.setattr(editor, "build_dashboard_data", original)
    assert client.get("/api/snapshot", headers=headers).status_code == 200
    assert rows(repo) == before


def test_invalid_business_row_never_returns_a_partial_list(progressive, repo):
    client, headers, job_id = progressive
    with repo.transaction():
        repo.db.execute("UPDATE jobs SET score=score+1 WHERE id=?", (job_id,))
    before = rows(repo)
    response = client.get("/api/snapshot", headers=headers)
    assert response.status_code == 503 and "jobs" not in response.json()
    assert rows(repo) == before


def test_slow_snapshots_do_not_block_shell_health_or_mobile_edits(progressive, monkeypatch):
    client, headers, job_id = progressive
    original = editor.build_dashboard_data
    started, release = Event(), Event()
    lock = Lock()
    active = peak = 0

    def slow(*args, **kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            started.set()
            assert release.wait(10)
            return original(*args, **kwargs)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(editor, "build_dashboard_data", slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(client.get, "/api/snapshot", headers=headers, timeout=15)
        second = None
        try:
            assert started.wait(5)
            second = pool.submit(client.get, "/api/snapshot", headers=headers, timeout=15)
            assert data(client.get("/", headers=headers, timeout=3))["status"] == "loading"
            assert client.get("/healthz", timeout=3).status_code == 200
            path = "/api/applications/" + job_id
            current = client.get(path, headers=headers, timeout=3).json()
            assert (
                client.post(
                    path,
                    headers=headers,
                    json={
                        "revision": current["revision"],
                        "changes": {"notes": "Updated during load"},
                    },
                    timeout=3,
                ).status_code
                == 200
            )
        finally:
            release.set()
        assert first.result().json()["jobs"][0]["application"]["notes"] == "Updated during load"
        assert second is not None and second.result().status_code == 200
    assert peak == 1


def test_static_exports_remain_complete_and_do_not_enter_loading_mode():
    html = render_dashboard({"format_version": 1, "status": "ok", "jobs": [{"id": "one"}]})
    assert 'data-loading="false"' in html
    assert data(type("Response", (), {"status_code": 200, "text": html})())["jobs"] == [
        {"id": "one"}
    ]


def test_progressive_mode_cannot_be_enabled_without_private_gateway(config):
    with pytest.raises(ValueError, match="private HTTPS"):
        editor.create_editable_dashboard_server(config, port=0, progressive=True)


def test_service_pulse_stays_live_without_reading_full_snapshot(
    progressive, config, repo, monkeypatch
):
    from trading_radar.runtime_status import WatcherPulse

    client, headers, _ = progressive

    def forbidden(*args, **kwargs):
        pytest.fail("A service pulse must not rebuild jobs or historical health")

    monkeypatch.setattr(editor, "build_dashboard_data", forbidden)
    monkeypatch.setattr(editor, "check_health", forbidden)
    pulse = WatcherPulse(config)
    pulse.publish("scanning")
    before = rows(repo)
    first = client.get("/api/services", headers=headers)
    assert first.status_code == 200
    assert first.json()["services"]["watcher"]["status"] == "active"
    assert first.json()["services"]["watcher"]["phase"] == "scanning"
    assert not any(
        field in first.json()["services"]["digest"] for field in ["offset", "binding", "token"]
    )
    pulse.publish("stopped")
    second = client.get("/api/services", headers=headers)
    assert second.json()["services"]["watcher"]["status"] == "stopped"
    assert second.headers["cache-control"] == "no-store"
    assert rows(repo) == before


def test_private_cli_enables_progressive_loading(config, monkeypatch):
    from typer.testing import CliRunner

    from trading_radar import dashboard_cli
    from trading_radar.cli import app
    from trading_radar.dashboard_private import PrivateDashboardAccess

    class Server:
        closed = False

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            self.closed = True

    server, calls = Server(), []
    monkeypatch.setattr(dashboard_cli, "load_config", lambda _: config)
    monkeypatch.setattr(PrivateDashboardAccess, "from_env", lambda: ACCESS)
    monkeypatch.setattr(
        editor, "create_editable_dashboard_server", lambda *a, **kw: calls.append(kw) or server
    )
    result = CliRunner().invoke(app, ["dashboard", "serve", "--private-editor"])
    assert result.exit_code == 0 and server.closed
    assert calls == [{"private_access": ACCESS, "progressive": True}]
