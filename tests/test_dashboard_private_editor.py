"""Private HTTPS gateway/session contract, with a synthetic SQLite database."""

import json
import re
from threading import Thread

import httpx
import pytest

from tests.test_dashboard_editor_server import rows
from trading_radar.dashboard_editor import create_editable_dashboard_server
from trading_radar.dashboard_private import PrivateDashboardAccess, PrivateSessions

ACCESS = PrivateDashboardAccess("https://dashboard.example.com", "/" + "A" * 43 + "/", "B" * 43)


@pytest.fixture
def private_editor(config, repo, job, tmp_path):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    with repo.transaction():
        repo.upsert(job)
    server = create_editable_dashboard_server(
        config, tmp_path / "history", 0, private_access=ACCESS
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            gateway = {"X-Radar-Gateway": ACCESS.gateway_secret}
            response = client.get("/", headers=gateway)
            assert response.status_code == 200
            data = json.loads(
                re.search(r'<script id="radar-data"[^>]*>(.*?)</script>', response.text, re.S)[1]
            )
            cookie = response.headers["set-cookie"].split(";", 1)[0]
            headers = gateway | {
                "Cookie": cookie,
                "X-Radar-Token": data["editing"]["token"],
                "Origin": ACCESS.origin,
                "Sec-Fetch-Site": "same-origin",
            }
            yield client, headers, "/api/applications/" + job.id, response
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_private_editor_updates_only_application_rows_with_revision(private_editor, repo):
    client, headers, path, response = private_editor
    assert all(
        value in response.headers["set-cookie"]
        for value in ["Secure", "HttpOnly", "SameSite=Strict", "Path=" + ACCESS.prefix]
    )
    before = rows(repo)
    current = client.get(path, headers=headers).json()
    body = {
        "revision": current["revision"],
        "changes": {
            "status": "To Apply",
            "notes": "Téléphone",
            "next_action": "Préparer CV",
            "next_action_date": "2027-01-12",
        },
    }
    saved = client.post(path, headers=headers, json=body)
    assert saved.status_code == 200 and saved.json()["history_total"] == 1
    assert client.post(path, headers=headers, json=body).status_code == 409
    after = rows(repo)
    assert {
        k: v
        for k, v in before.items()
        if k not in {"applications", "application_history", "sqlite_sequence"}
    } == {
        k: v
        for k, v in after.items()
        if k not in {"applications", "application_history", "sqlite_sequence"}
    }
    assert client.post("/api/health-snapshots", headers=headers, json={}).status_code == 404


@pytest.mark.parametrize("removed", ["X-Radar-Gateway", "Cookie", "X-Radar-Token", "Origin"])
def test_private_post_requires_gateway_cookie_token_and_exact_origin(private_editor, repo, removed):
    client, headers, path, _ = private_editor
    before = rows(repo)
    headers = {k: v for k, v in headers.items() if k != removed}
    assert client.post(path, headers=headers, json={}).status_code == 403
    assert rows(repo) == before


@pytest.mark.parametrize(
    "override",
    [
        {"Origin": "https://evil.example.com"},
        {"X-Radar-Gateway": "wrong"},
        {"Sec-Fetch-Site": "cross-site"},
        {"Cookie": "radar_session=bad"},
        {"X-Radar-Token": "wrong"},
    ],
)
def test_private_editor_rejects_cross_site_and_forged_sessions(private_editor, repo, override):
    client, headers, path, _ = private_editor
    before = rows(repo)
    assert client.get(path, headers=headers | override).status_code == 403
    assert client.post(path, headers=headers | override, json={}).status_code == 403
    assert rows(repo) == before


def test_ordinary_loopback_is_not_private_editor_auth(private_editor):
    client, headers, path, _ = private_editor
    assert client.get("/").status_code == 403
    assert client.get("/healthz").json() == {"status": "ok"}
    assert (
        client.get(
            "/", headers={"X-Radar-Gateway": ACCESS.gateway_secret, "Sec-Fetch-Site": "cross-site"}
        ).status_code
        == 200
    )
    other = client.get("/", headers={"X-Radar-Gateway": ACCESS.gateway_secret})
    csrf = json.loads(
        re.search(r'<script id="radar-data"[^>]*>(.*?)</script>', other.text, re.S)[1]
    )["editing"]["token"]
    assert client.get(path, headers=headers | {"X-Radar-Token": csrf}).status_code == 403


def test_session_expiry_and_restart_fail_closed(monkeypatch):
    from email.message import Message

    sessions = PrivateSessions(ACCESS)
    value = sessions.mint()
    headers = Message()
    headers["Cookie"] = "radar_session=" + value
    assert sessions.read(headers) == value
    assert PrivateSessions(ACCESS).read(headers) is None
    monkeypatch.setattr(
        "trading_radar.dashboard_private.time.time", lambda: int(value.split(".")[1]) + 1
    )
    assert sessions.read(headers) is None


def test_remote_application_edit_does_not_wait_for_network_collection_lease(private_editor, repo):
    from filelock import FileLock

    client, headers, path, _ = private_editor
    current = client.get(path, headers=headers).json()
    with FileLock(repo.lock_path, timeout=0):
        response = client.post(
            path,
            headers=headers,
            json={"revision": current["revision"], "changes": {"status": "Reviewing"}},
        )
    assert response.status_code == 200
    assert response.json()["application"]["status"] == "Reviewing"
