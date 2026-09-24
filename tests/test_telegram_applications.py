import asyncio
import copy
import json
import sqlite3
from datetime import UTC, datetime
from html import unescape
from xml.etree import ElementTree

import httpx
import pytest
from filelock import FileLock

from trading_radar import dashboard_applications as service
from trading_radar import telegram_control as control
from trading_radar.notifications import TelegramNotifier
from trading_radar.telegram_cards import (
    application_callback,
    application_keyboard,
    callback_job,
    format_alert,
)

TOKEN, CHAT = "123:test_token", "456"
NOW = datetime(2026, 9, 24, 23, 30, tzinfo=UTC)


@pytest.fixture
def seeded(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    with repo.transaction():
        repo.upsert(job)
    return config, repo, job


def query(job):
    return {
        "id": "callback-1",
        "data": application_callback(job.id, TOKEN, CHAT),
        "from": {"id": 456, "is_bot": False},
        "message": {
            "message_id": 42,
            "date": 1,
            "chat": {"id": 456, "type": "private"},
            "from": {"id": 123, "is_bot": True},
        },
    }


def notifier_calls(fail=False):
    calls = []

    def handler(request):
        calls.append((request.url.path.rsplit("/", 1)[-1], json.loads(request.content)))
        return httpx.Response(500 if fail else 200, json={"ok": not fail, "result": True})

    return TelegramNotifier(TOKEN, CHAT, transport=httpx.MockTransport(handler)), calls


def test_html_card_escapes_employer_text_and_remains_within_telegram_limit(job):
    job.title = '</b><a href="https://evil.example">&' * 100
    job.description_text = "🦊<&>" * 500
    card = format_alert(job, "new")
    root = ElementTree.fromstring("<root>" + card + "</root>")
    assert all(node.tag in {"root", "b", "i", "blockquote"} for node in root.iter())
    assert "</b><a" not in card
    assert len("".join(root.itertext()).encode("utf-16-le")) // 2 < 4096
    notifier, calls = notifier_calls()
    asyncio.run(notifier.send(job, "new"))
    assert calls[0][1]["parse_mode"] == "HTML"
    assert "<a href=" in unescape(card)


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://u:p@example.com",
        "https://[bad",
        "https://example.com/\nfoo",
        "file:///tmp/a",
    ],
)
def test_unsafe_apply_links_are_not_buttons(job, url):
    rows = application_keyboard(job.id, url, TOKEN, CHAT)["inline_keyboard"]
    assert not any("url" in button for row in rows for button in row)


def test_signed_callback_is_bound_to_bot_and_destination(job):
    value = application_callback(job.id, TOKEN, CHAT)
    assert len(value.encode()) <= 64
    assert callback_job(value, TOKEN, CHAT) == job.id
    assert callback_job(value, TOKEN, "789") is None
    assert callback_job(value, "123:other", CHAT) is None
    assert callback_job(value[:-1] + ("0" if value[-1] != "0" else "1"), TOKEN, CHAT) is None


def test_click_commits_date_history_and_keyboard_idempotently_during_scan(seeded):
    config, repo, job = seeded
    repo.update_application(job.id, {"notes": "Mon brouillon", "next_action": "Relancer"})
    original = service.read_application(config, job.id)
    notifier, calls = notifier_calls()
    with FileLock(repo.lock_path, timeout=0):
        for _ in range(2):
            asyncio.run(control.process_callback(query(job), config, notifier, NOW.timestamp()))
    current = service.read_application(config, job.id)
    assert current["application"]["status"] == "Applied"
    assert current["application"]["application_date"] == "2026-09-25"
    assert current["application"]["notes"] == "Mon brouillon"
    assert current["application"]["next_action"] == "Relancer"
    assert current["history_total"] == original["history_total"] + 1
    assert calls[0][0] == "answerCallbackQuery" and "✅ Postulé" in calls[0][1]["text"]
    assert calls[1][1]["reply_markup"]["inline_keyboard"][1][0]["text"] == "✅ Postulé"
    assert service.list_applications(config) == [current["application"]]
    with pytest.raises(service.ApplicationEditError, match="changé"):
        service.update_application(config, job.id, {"notes": "obsolete"}, original["revision"])


@pytest.mark.parametrize(
    "status", ["Applied", "Interview", "Offer", "Rejected", "Withdrawn", "Closed"]
)
def test_click_never_regresses_tracking_or_changes_existing_date(seeded, status):
    config, repo, job = seeded
    repo.update_application(job.id, {"status": status, "application_date": "2026-09-01"})
    before = service.read_application(config, job.id)
    service.mark_applied(config, job.id, NOW)
    assert service.read_application(config, job.id) == before


@pytest.mark.parametrize(
    "area,field,value",
    [
        ("from", "id", 789),
        ("from", "is_bot", True),
        ("from", "id", "456"),
        ("chat", "type", "group"),
        ("chat", "id", 789),
        ("author", "id", 999),
        ("author", "is_bot", False),
        ("message", "date", 0),
        ("message", "message_id", True),
        ("message", "forward_origin", {}),
        ("message", "via_bot", {}),
    ],
)
def test_untrusted_callbacks_cannot_read_or_write(seeded, monkeypatch, area, field, value):
    config, repo, job = seeded
    item = query(job)
    target = {
        "from": item["from"],
        "chat": item["message"]["chat"],
        "author": item["message"]["from"],
        "message": item["message"],
    }[area]
    target[field] = value
    monkeypatch.setattr(
        control, "mark_applied", lambda *args: pytest.fail("Unauthorized DB access")
    )
    notifier, calls = notifier_calls()
    asyncio.run(control.process_callback(item, config, notifier, NOW.timestamp()))
    assert calls == []


def test_tampered_and_missing_jobs_are_acknowledged_without_false_success(seeded):
    config, repo, job = seeded
    notifier, calls = notifier_calls()
    bad = query(job)
    bad["data"] = "ap:invalid"
    asyncio.run(control.process_callback(bad, config, notifier, NOW.timestamp()))
    missing = copy.deepcopy(job)
    missing.id = "00000000-0000-0000-0000-000000000000"
    asyncio.run(control.process_callback(query(missing), config, notifier, NOW.timestamp()))
    assert all(method == "answerCallbackQuery" and body["show_alert"] for method, body in calls)
    assert service.read_application(config, job.id)["application"]["status"] == "New"


def test_sqlite_writer_contention_never_acknowledges_success(seeded):
    config, repo, job = seeded
    notifier, calls = notifier_calls()
    repo.db.execute("BEGIN IMMEDIATE")
    try:
        asyncio.run(control.process_callback(query(job), config, notifier, NOW.timestamp()))
    finally:
        repo.db.rollback()
    assert len(calls) == 1 and calls[0][1]["show_alert"]
    assert "Réessayez" in calls[0][1]["text"]
    assert repo.application(job.id).status == "New"


def test_ambiguous_ack_does_not_replay_or_duplicate_history(seeded, tmp_path):
    config, repo, job = seeded
    notifier, calls = notifier_calls(fail=True)
    store = control.ControlStore(tmp_path / "control.json", "test")
    update = {"update_id": 1, "callback_query": query(job)}
    for _ in range(2):
        asyncio.run(
            control.process_updates([update], config, notifier, store, "TestBot", NOW.timestamp())
        )
    assert service.read_application(config, job.id)["history_total"] == 1
    assert len(calls) == 2 and store.state.offset == 2


def test_failed_cursor_save_prevents_application_write(seeded, tmp_path, monkeypatch):
    config, repo, job = seeded
    store = control.ControlStore(tmp_path / "control.json", "test")

    def fail():
        raise OSError("disk unavailable")

    monkeypatch.setattr(store, "save", fail)
    notifier, calls = notifier_calls()
    with pytest.raises(OSError):
        asyncio.run(
            control.process_updates(
                [{"update_id": 1, "callback_query": query(job)}],
                config,
                notifier,
                store,
                "TestBot",
                NOW.timestamp(),
            )
        )
    assert not calls and repo.application(job.id).status == "New"


def test_history_failure_rolls_back_status(seeded, monkeypatch):
    config, repo, job = seeded
    original = service._snapshot
    count = 0

    def snapshot(db, identifier):
        nonlocal count
        count += 1
        if count == 2:
            raise sqlite3.OperationalError("synthetic failure before commit")
        return original(db, identifier)

    monkeypatch.setattr(service, "_snapshot", snapshot)
    with pytest.raises(service.ApplicationEditError):
        service.mark_applied(config, job.id, NOW)
    assert repo.application(job.id).status == "New"
    assert repo.db.execute("SELECT COUNT(*) FROM application_history").fetchone()[0] == 0
