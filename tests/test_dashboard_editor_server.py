"""The opt-in server accepts only intentional, protected local actions."""

import json
import re
import socket
from http.client import HTTPResponse
from threading import Thread

import httpx
import pytest
from filelock import FileLock
from typer.testing import CliRunner

from trading_radar import dashboard_cli, dashboard_editor
from trading_radar.cli import app
from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_editor import MAX_BODY_BYTES, create_editable_dashboard_server
from trading_radar.monitoring import history, read_snapshot


def rows(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


@pytest.fixture
def editor(repo, config, job, tmp_path):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    with repo.transaction():
        repo.upsert(job)
    server = create_editable_dashboard_server(config, tmp_path / "history", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert server.server_address[0] == "127.0.0.1"
        origin = f"http://127.0.0.1:{server.server_port}"
        with httpx.Client(base_url=origin, trust_env=False) as client:
            response = client.get("/")
            payload = json.loads(
                re.search(r'<script id="radar-data"[^>]*>(.*?)</script>', response.text, re.S)[1]
            )
            token = payload["editing"]["token"]
            yield client, {"X-Radar-Token": token, "Origin": origin}, f"/api/applications/{job.id}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_edit_save_history_noop_conflict_and_fresh_page(editor, repo):
    client, headers, path = editor
    before = rows(repo)
    initial = client.get(path, headers=headers).json()
    body = {
        "revision": initial["revision"],
        "changes": {"status": "To Apply", "notes": "À vérifier <script> & résumé"},
    }
    saved = client.post(path, headers=headers, json=body)
    assert saved.status_code == 200
    saved = saved.json()
    assert saved["application"]["notes"] == body["changes"]["notes"]
    assert saved["history_total"] == 1
    assert saved["history"][0]["before"]["status"] == "New"
    assert saved["revision"] != initial["revision"]
    body["revision"] = saved["revision"]
    noop = client.post(path, headers=headers, json=body).json()
    assert noop["revision"] == saved["revision"] and noop["history_total"] == 1
    body["revision"] = initial["revision"]
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
    html = client.get("/").text
    assert "À vérifier \\u003cscript\\u003e" in html
    assert '"status":"To Apply"' in html


def test_editor_headers_and_static_export_still_isolated(editor):
    client, headers, path = editor
    response = client.get("/")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert "connect-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert "connect-src &#x27;self&#x27;" in response.text
    assert "connect-src &#x27;none&#x27;" in render_dashboard({})
    assert client.head("/").content == b""
    assert client.get(path).status_code == 403
    assert client.get(path, headers={"X-Radar-Token": headers["X-Radar-Token"]}).status_code == 200


def test_live_application_snapshot_requires_session_and_reflects_telegram(editor, config, job):
    from trading_radar.dashboard_applications import mark_applied
    from trading_radar.models import utcnow

    client, headers, _ = editor
    assert client.get("/api/applications").status_code == 403
    assert (
        client.get(
            "/api/applications", headers=headers | {"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    before = client.get("/api/applications", headers=headers)
    assert before.json()["applications"][0]["status"] == "New"
    mark_applied(config, job.id, utcnow())
    after = client.get("/api/applications", headers=headers)
    assert after.json()["applications"][0]["status"] == "Applied"
    assert after.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "override",
    [
        {"X-Radar-Token": "wrong"},
        {"Origin": "null"},
        {"Origin": "https://evil.example"},
        {"Origin": "http://127.0.0.1:1"},
        {"Host": "evil.example"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_cross_site_requests_never_read_or_write(editor, repo, override):
    client, headers, path = editor
    before = rows(repo)
    bad = headers | override
    assert client.get(path, headers=bad).status_code == 403
    assert client.post(path, headers=bad, json={}).status_code == 403
    assert rows(repo) == before


def test_post_requires_origin_and_token(editor, repo):
    client, headers, path = editor
    before = rows(repo)
    for incomplete in (
        {},
        {"Origin": headers["Origin"]},
        {"X-Radar-Token": headers["X-Radar-Token"]},
    ):
        assert client.post(path, headers=incomplete, json={}).status_code == 403
    assert rows(repo) == before


@pytest.mark.parametrize(
    "request_body",
    [
        b'{"revision":"a","revision":"b","changes":{}}',
        b'{"revision":"a","changes":{"notes":"a","notes":"b"}}',
        b'{"revision":"a","changes":{"notes":NaN}}',
        b"[]",
        b"null",
        b"{}",
        b'{"revision":"a","changes":{},"extra":true}',
        b"\xff",
        b"{",
        b"[" * 1200,
    ],
)
def test_bad_json_envelopes_are_atomic(editor, repo, request_body):
    client, headers, path = editor
    before = rows(repo)
    response = client.post(
        path, headers=headers | {"Content-Type": "application/json"}, content=request_body
    )
    assert response.status_code == 400
    assert response.json()["status"] == "error"
    assert rows(repo) == before


@pytest.mark.parametrize(
    "content_type",
    ["text/plain", "application/x-www-form-urlencoded", "application/json; charset=latin1"],
)
def test_wrong_media_type_does_not_write(editor, repo, content_type):
    client, headers, path = editor
    before = rows(repo)
    assert (
        client.post(
            path, headers=headers | {"Content-Type": content_type}, content=b"{}"
        ).status_code
        == 415
    )
    assert rows(repo) == before


def test_oversized_body_and_compressed_body_rejected(editor, repo):
    client, headers, path = editor
    before = rows(repo)
    port = client.base_url.port
    request = (
        f"POST {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        f"Origin: {headers['Origin']}\r\nX-Radar-Token: {headers['X-Radar-Token']}\r\n"
        f"Content-Length: {MAX_BODY_BYTES + 1}\r\n"
        "Content-Type: application/json\r\n\r\n"
    )
    # Keep the upload open without sending its body: rejection must depend only
    # on the declared length. Sending a large body races the server's early close
    # and can reset the connection before Windows delivers its 413 response.
    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        connection.sendall(request.encode("ascii"))
        with HTTPResponse(connection) as response:
            response.begin()
            assert response.status == 413
            assert json.loads(response.read())["error"]["code"] == "too_large"
    assert rows(repo) == before
    assert (
        client.post(path, headers=headers | {"Content-Encoding": "gzip"}, json={}).status_code
        == 400
    )
    assert rows(repo) == before


def test_duplicate_headers_rejected(editor, repo):
    client, headers, path = editor
    before = rows(repo)
    for key, value in [
        ("Origin", headers["Origin"]),
        ("X-Radar-Token", headers["X-Radar-Token"]),
        ("Sec-Fetch-Site", "same-origin"),
    ]:
        request_headers = list(headers.items())
        if key == "Sec-Fetch-Site":
            request_headers.append((key, value))
        request_headers.append((key, value))
        assert client.post(path, headers=request_headers, json={}).status_code == 403
    assert rows(repo) == before


def test_validation_busy_and_missing_errors_are_safe(editor, repo):
    client, headers, path = editor
    revision = client.get(path, headers=headers).json()["revision"]
    before = rows(repo)
    response = client.post(
        path,
        headers=headers,
        json={"revision": revision, "changes": {"status": "PRIVATE_INVALID_STATUS"}},
    )
    assert response.status_code == 422 and "PRIVATE_INVALID_STATUS" not in response.text
    with FileLock(repo.lock_path, timeout=0):
        assert (
            client.post(
                path,
                headers=headers,
                json={"revision": revision, "changes": {"status": "To Apply"}},
            ).status_code
            == 503
        )
    assert client.get("/api/applications/missing", headers=headers).status_code == 404
    assert rows(repo) == before


@pytest.mark.parametrize(
    "path",
    [
        "/data/jobs.db",
        "/config/settings.yaml",
        "/api/applications/x?token=secret",
        "/api/applications/../../.env",
    ],
)
def test_no_directory_or_token_query_route(editor, path):
    client, headers, _ = editor
    assert client.get(path, headers=headers).status_code == 404


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "OPTIONS"])
def test_no_other_mutation_methods(editor, repo, method):
    client, headers, path = editor
    before = rows(repo)
    assert client.request(method, path, headers=headers).status_code == 405
    assert rows(repo) == before


def test_cli_edit_mode_is_explicit_and_closes_server(monkeypatch, config):
    class Server:
        closed = False

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            self.closed = True

    server = Server()
    calls = []
    monkeypatch.setattr(dashboard_cli, "load_config", lambda _: config)
    monkeypatch.setattr(
        dashboard_editor,
        "create_editable_dashboard_server",
        lambda *args: calls.append(args) or server,
    )
    result = CliRunner().invoke(app, ["dashboard", "serve", "--edit-applications"])
    assert result.exit_code == 0, result.output
    assert "Application editor" in result.output and server.closed and len(calls) == 1


def test_missing_database_never_created(config, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'missing.db'}"
    with pytest.raises(ValueError):
        create_editable_dashboard_server(config, port=0)
    assert not (tmp_path / "missing.db").exists()


@pytest.mark.parametrize("note", ["\ud800", "x" * 20_001])
def test_invalid_text_cannot_escape_validation(editor, repo, note):
    client, headers, path = editor
    before = rows(repo)
    revision = client.get(path, headers=headers).json()["revision"]
    body = json.dumps({"revision": revision, "changes": {"notes": note}}).encode("ascii")
    response = client.post(
        path, headers=headers | {"Content-Type": "application/json"}, content=body
    )
    assert response.status_code == 422
    assert rows(repo) == before


@pytest.mark.parametrize(
    "extra_headers,expected",
    [
        ("", 400),
        ("Content-Length: 2\r\nContent-Length: 2\r\n", 400),
        ("Transfer-Encoding: chunked\r\n", 400),
        ("Content-Length: -1\r\n", 400),
        ("Content-Length: 2\r\nHost: evil.example\r\n", 403),
    ],
)
def test_ambiguous_http_framing_never_writes(editor, repo, extra_headers, expected):
    client, headers, path = editor
    before = rows(repo)
    port = client.base_url.port
    request = (
        f"POST {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        f"Origin: {headers['Origin']}\r\nX-Radar-Token: {headers['X-Radar-Token']}\r\n"
        "Content-Type: application/json\r\n" + extra_headers + "\r\n{}"
    )
    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        connection.sendall(request.encode("ascii"))
        response = connection.recv(4096)
    assert response.startswith(f"HTTP/1.0 {expected}".encode())
    assert rows(repo) == before


@pytest.mark.parametrize("body", [b"x", b"x" * 8192])
def test_unauthorized_small_upload_gets_error_even_when_partial(editor, repo, body):
    client, headers, path = editor
    before = rows(repo)
    port = client.base_url.port
    request = (
        f"POST {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        f"Origin: {headers['Origin']}\r\nX-Radar-Token: incorrect\r\n"
        "Content-Length: 8192\r\nContent-Type: application/json\r\n\r\n"
    ).encode() + body
    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
        connection.sendall(request)
        with HTTPResponse(connection) as response:
            response.begin()
            assert response.status == 403
            assert json.loads(response.read())["error"]["code"] == "invalid_session"
    assert rows(repo) == before


def test_capture_health_updates_history_without_business_writes(editor, repo, tmp_path):
    client, headers, _ = editor
    before = rows(repo)
    directory = tmp_path / "history"
    with FileLock(repo.db.execute("PRAGMA database_list").fetchone()[2] + ".lock"):
        first = client.post("/api/health-snapshots", headers=headers, json={})
    assert first.status_code == 201
    assert first.headers["cache-control"] == "no-store"
    saved = first.json()
    assert saved["monitoring"]["total"] == 1
    assert saved["monitoring"]["latest_comparison"] is None
    archive = read_snapshot(directory, saved["snapshot"]["id"])
    assert saved["snapshot"]["recorded_at"] == archive["report"]["generated_at"]
    second = client.post("/api/health-snapshots", headers=headers, json={})
    assert second.status_code == 201
    comparison = second.json()["monitoring"]["latest_comparison"]
    assert comparison["previous_id"] == saved["snapshot"]["id"]
    assert comparison["source_changes"] == []
    assert rows(repo) == before
    assert history(directory)["total"] == 2
    assert saved["snapshot"]["id"] in client.get("/").text


@pytest.mark.parametrize(
    "override",
    [
        {"X-Radar-Token": "wrong"},
        {"Origin": "null"},
        {"Origin": "https://evil.example"},
        {"Host": "evil.example"},
        {"Sec-Fetch-Site": "cross-site"},
        {"X-Radar-Token": None},
        {"Origin": None},
    ],
)
def test_capture_health_requires_local_session(editor, repo, tmp_path, override):
    client, headers, _ = editor
    before = rows(repo)
    headers = {k: v for k, v in (headers | override).items() if v is not None}
    assert client.post("/api/health-snapshots", headers=headers, json={}).status_code == 403
    assert not (tmp_path / "history").exists()
    assert rows(repo) == before


@pytest.mark.parametrize(
    "body",
    [
        "[]",
        "null",
        "{",
        '{"directory":"../private"}',
        '{"max_age_hours":1}',
        '{"revision":"x","changes":{}}',
        '{"x":1,"x":2}',
        '{"x":NaN}',
    ],
)
def test_capture_health_accepts_no_configuration(editor, repo, tmp_path, body):
    client, headers, _ = editor
    before = rows(repo)
    response = client.post(
        "/api/health-snapshots",
        content=body,
        headers=headers | {"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert not (tmp_path / "history").exists()
    assert rows(repo) == before


@pytest.mark.parametrize(
    "method,expected",
    [("GET", 404), ("HEAD", 404), ("PUT", 405), ("PATCH", 405), ("DELETE", 405), ("OPTIONS", 405)],
)
def test_capture_health_only_explicit_post(editor, tmp_path, method, expected):
    client, headers, _ = editor
    assert client.request(method, "/api/health-snapshots", headers=headers).status_code == expected
    assert not (tmp_path / "history").exists()


@pytest.mark.parametrize("suffix", ["/", "?directory=elsewhere", "/extra"])
def test_capture_health_route_cannot_be_extended(editor, tmp_path, suffix):
    client, headers, _ = editor
    assert (
        client.post("/api/health-snapshots" + suffix, headers=headers, json={}).status_code == 404
    )
    assert not (tmp_path / "history").exists()


@pytest.mark.parametrize("failure", [OSError, ValueError])
def test_capture_health_failure_sanitized(editor, tmp_path, monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure("private path or credentials")

    monkeypatch.setattr(dashboard_editor, "record_health", fail)
    client, headers, _ = editor
    response = client.post("/api/health-snapshots", headers=headers, json={})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "health_capture_unavailable"
    assert "private" not in response.text
    assert not (tmp_path / "history").exists()


def test_capture_health_success_survives_unreadable_older_archive(editor, tmp_path):
    directory = tmp_path / "history"
    directory.mkdir()
    (directory / "broken.json").write_text("private contents", encoding="utf-8")
    client, headers, _ = editor
    response = client.post("/api/health-snapshots", headers=headers, json={})
    assert response.status_code == 201
    result = response.json()
    assert result["monitoring"]["status"] == "unavailable"
    assert "private" not in response.text and "broken.json" not in response.text
    assert read_snapshot(directory, result["snapshot"]["id"])
    assert len(list(directory.glob("*.json"))) == 2


def test_capture_health_records_critical_missing_database(editor, config, tmp_path):
    missing = tmp_path / "missing.db"
    config.settings.database_url = "sqlite:///" + str(missing)
    client, headers, _ = editor
    response = client.post("/api/health-snapshots", headers=headers, json={})
    assert response.status_code == 201
    result = response.json()
    archive = read_snapshot(tmp_path / "history", result["snapshot"]["id"])
    assert archive["report"]["status"] == "critical"
    assert not missing.exists()
