import asyncio
from datetime import timedelta

import httpx
import pytest

from tests.test_nomura import board, card, config, detail
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import utcnow
from trading_radar.nomura import SEARCH, NomuraCollector
from trading_radar.nomura_session import HOST, NomuraSession, load_session, save_session
from trading_radar.source_schedule import due_at


def state(now=None):
    return {
        "version": 1,
        "verified_at": (now or utcnow()).isoformat(),
        "user_agent": "TestPublicBrowser/1.0",
        "cookies": [
            {
                "name": "public_session",
                "value": "fixture-only",
                "domain": HOST,
                "path": "/",
                "expires": -1,
            }
        ],
    }


@pytest.mark.parametrize(
    "change",
    [
        {"verified_at": "not-a-date"},
        {"verified_at": "2026-09-27T01:00:00"},
        {"verified_at": (utcnow() - timedelta(hours=13)).isoformat()},
        {"verified_at": (utcnow() + timedelta(hours=1)).isoformat()},
        {"version": 2},
        {"cookies": []},
        {"user_agent": "x\r\nInjected: header"},
    ],
)
def test_invalid_session_rejected(change):
    data = state()
    data.update(change)
    with pytest.raises(SourceUnavailable):
        NomuraSession(data)


@pytest.mark.parametrize(
    "change",
    [
        {"domain": "tal.net"},
        {"domain": "evil.example"},
        {"path": "relative"},
        {"name": "x;evil"},
        {"value": "a;b=c"},
        {"value": "a\r\nb"},
        {"expires": True},
        {"expires": float("nan")},
        {"expires": 0},
    ],
)
def test_invalid_cookie_rejected(change):
    data = state()
    data["cookies"][0].update(change)
    with pytest.raises(SourceUnavailable):
        NomuraSession(data)


def test_cookie_path_expiry_and_host_limits():
    now = utcnow()
    data = state(now)
    data["cookies"] += [
        {"name": "scoped", "value": "value", "domain": HOST, "path": "/candidate", "expires": -1},
        {
            "name": "expired",
            "value": "value",
            "domain": HOST,
            "path": "/",
            "expires": now.timestamp() - 1,
        },
    ]
    session = NomuraSession(data, now)
    assert session.headers(SEARCH)["Cookie"] == "public_session=fixture-only"
    assert (
        session.headers("https://" + HOST + "/candidate/job")["Cookie"]
        == "scoped=value; public_session=fixture-only"
    )
    assert (
        session.headers("https://" + HOST + "/candidate-other")["Cookie"]
        == "public_session=fixture-only"
    )
    for url in [
        "http://" + HOST,
        "https://" + HOST + ".evil.example",
        "https://user@" + HOST,
        "https://" + HOST + ":443",
    ]:
        with pytest.raises(SourceUnavailable):
            session.headers(url)


def test_atomic_session_roundtrip_and_invalid_replacement(tmp_path):
    path = tmp_path / "session.json"
    data = state()
    save_session(path, data)
    assert load_session(path).headers(SEARCH)["Cookie"] == "public_session=fixture-only"
    original = path.read_bytes()
    with pytest.raises(SourceUnavailable):
        save_session(path, {})
    assert path.read_bytes() == original
    assert not list(tmp_path.glob(".nomura-session-*"))
    path.write_text("x" * 65537)
    with pytest.raises(SourceUnavailable):
        load_session(path)


def test_duplicate_cookie_and_expired_cookie_rejected():
    data = state()
    data["cookies"] *= 2
    with pytest.raises(SourceUnavailable):
        NomuraSession(data)
    data = state()
    data["cookies"][0]["expires"] = utcnow().timestamp() - 1
    with pytest.raises(SourceUnavailable):
        NomuraSession(data).headers(SEARCH)


def test_nomura_uses_local_session_only_for_public_pages(tmp_path, monkeypatch):
    path = tmp_path / "session.json"
    save_session(path, state())
    monkeypatch.setenv("NOMURA_SESSION_FILE", str(path))
    calls = []

    def handler(req):
        calls.append(req)
        if req.url.path == "/robots.txt":
            assert "cookie" not in req.headers
            return httpx.Response(404)
        assert req.headers["Cookie"] == "public_session=fixture-only"
        assert req.headers["User-Agent"] == "TestPublicBrowser/1.0"
        return httpx.Response(200, text=board([card()]) if str(req.url) == SEARCH else detail())

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            result = await NomuraCollector("nomura_campus", config(), http).collect()
            assert "cookie" not in http.client.headers
            assert http.client.headers["User-Agent"].startswith("TradingJobRadar/")
            assert "fixture-only" not in result.model_dump_json()
            assert len(result.jobs) == 1
        finally:
            await http.close()

    asyncio.run(run())
    assert len(calls) == 3


def test_missing_opt_in_file_never_issues_a_request(tmp_path, monkeypatch):
    monkeypatch.setenv("NOMURA_SESSION_FILE", str(tmp_path / "missing.json"))

    def handler(req):
        pytest.fail("Invalid local session must not be used")

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(SourceUnavailable, match="session unavailable"):
                await NomuraCollector("nomura_campus", config(), http).collect()
        finally:
            await http.close()

    asyncio.run(run())


def test_new_validation_triggers_only_one_recovery_attempt(tmp_path, monkeypatch):
    path = tmp_path / "session.json"
    now = utcnow()
    save_session(path, state(now))
    monkeypatch.setenv("NOMURA_SESSION_FILE", str(path))
    company = Company(name="Nomura", ats="nomura")
    failed = now - timedelta(minutes=5)
    status = {"last_failure": failed.isoformat(), "consecutive_failures": 8}
    assert due_at(company, status) == now
    status["last_failure"] = (now + timedelta(seconds=1)).isoformat()
    assert due_at(company, status) == now + timedelta(seconds=3601)
    status = {"last_success": now.isoformat(), "consecutive_failures": 0}
    assert due_at(company, status) == now + timedelta(minutes=5)


def test_invalid_or_unrelated_session_does_not_shorten_backoff(tmp_path, monkeypatch):
    path = tmp_path / "session.json"
    now = utcnow()
    monkeypatch.setenv("NOMURA_SESSION_FILE", str(path))
    status = {"last_failure": (now - timedelta(minutes=5)).isoformat(), "consecutive_failures": 8}
    company = Company(name="Nomura", ats="nomura")
    expected = now + timedelta(minutes=55)
    assert due_at(company, status) == expected
    path.write_text("not-json")
    assert due_at(company, status) == expected
    save_session(path, state(now))
    assert due_at(Company(name="Other", ats="ubs"), status) == expected
