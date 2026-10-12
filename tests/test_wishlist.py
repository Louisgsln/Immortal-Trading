import asyncio
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_STORED, ZipFile

import pytest

from tests.test_dashboard_private_editor import private_editor  # noqa: F401
from tests.test_scanner import FakeNotifier, MemoryCollector, run
from tests.test_telegram_applications import CHAT, TOKEN, notifier_calls, query
from trading_radar import telegram_control as control
from trading_radar.backups import create_backup, restore_backup, verify_backup
from trading_radar.dashboard_applications import (
    ApplicationEditError,
    mark_applied,
    read_application,
)
from trading_radar.telegram_cards import callback_job, wishlist_callback
from trading_radar.telegram_catalogue import send_catalogue
from trading_radar.wishlist import list_wishlist, read_wishlist, set_wishlist, wishlist_path


@pytest.fixture
def seeded(config, repo, job):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    with repo.transaction():
        repo.upsert(job)
    return config, repo, job


def test_all_score_feed_keeps_bootstrap_silent_and_sends_zero_once(config, repo, raw):
    config.settings.telegram_all_new_jobs = True
    notifier = FakeNotifier()
    collector = MemoryCollector([raw])
    run(config, repo, {"test": collector}, notifier)
    zero = raw.model_copy(
        update={
            "title": "Senior Trading Operations Support",
            "external_id": "zero",
            "apply_url": "https://example.com/zero",
            "description": "Requires at least 10 years of experience.",
        }
    )
    collector.jobs.append(zero)
    result = run(config, repo, {"test": collector}, notifier)
    assert result.new == 1 and result.alerts == 1
    sent = repo.get(notifier.sent[0][0])
    assert sent.score_breakdown.total == 0 and sent.score_breakdown.exclusions
    run(config, repo, {"test": collector}, notifier)
    assert len(notifier.sent) == 1


def test_wishlist_membership_is_idempotent_and_never_changes_main_journal(seeded):
    config, repo, job = seeded
    before = read_application(config, job.id)
    empty = read_wishlist(config, job.id)
    assert not wishlist_path(Path(repo.db.execute("PRAGMA database_list").fetchone()[2])).exists()
    first = set_wishlist(config, job.id, True, actor="telegram")
    assert set_wishlist(config, job.id, True, actor="telegram") == first
    assert list_wishlist(config) == [
        {k: first[k] for k in ("job_id", "saved", "added_at", "revision")}
    ]
    with pytest.raises(ApplicationEditError) as error:
        set_wishlist(config, job.id, False, actor="dashboard", expected_revision=empty["revision"])
    assert error.value.status == 409
    removed = set_wishlist(
        config, job.id, False, actor="dashboard", expected_revision=first["revision"]
    )
    assert not removed["saved"] and removed["revision"] != empty["revision"]
    assert read_application(config, job.id) == before
    assert repo.db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 4


def test_applied_keeps_wishlist_notes_and_later_stages(seeded):
    config, repo, job = seeded
    repo.update_application(job.id, {"notes": "CV personnalisé", "next_action": "Relancer"})
    set_wishlist(config, job.id, True, actor="telegram")
    applied = mark_applied(config, job.id, datetime(2026, 10, 12, 23, 30, tzinfo=UTC))
    assert applied["application"]["application_date"] == "2026-10-13"
    assert applied["application"]["notes"] == "CV personnalisé"
    assert read_wishlist(config, job.id)["saved"]
    set_wishlist(config, job.id, False, actor="dashboard")
    assert read_application(config, job.id) == {
        k: v for k, v in applied.items() if k != "apply_url"
    }


def test_wishlist_callback_is_destination_and_action_bound(seeded):
    config, repo, job = seeded
    signed = wishlist_callback(job.id, TOKEN, CHAT)
    assert len(signed.encode()) <= 64
    assert callback_job(signed, TOKEN, CHAT, action="wl") == job.id
    assert callback_job(signed, TOKEN, CHAT) is None
    assert callback_job(signed, TOKEN, "999", action="wl") is None
    assert callback_job(signed, "123:other", CHAT, action="wl") is None
    notifier, calls = notifier_calls()
    item = query(job)
    item["data"] = signed
    for _ in range(2):
        asyncio.run(control.process_callback(item, config, notifier, datetime.now(UTC).timestamp()))
    assert read_application(config, job.id)["application"]["status"] == "New"
    assert read_wishlist(config, job.id)["saved"]
    assert calls[1][1]["reply_markup"]["inline_keyboard"][2][0]["text"].startswith("⭐ Dans")


def test_private_api_sync_csrf_conflict_remove_and_apply(private_editor, config, repo, job):  # noqa: F811
    client, headers, app_path, _ = private_editor
    wish_path = app_path.replace("applications", "wishlist")
    current = client.get(wish_path, headers=headers).json()
    body = {"revision": current["revision"], "saved": True}
    assert (
        client.post(
            wish_path, headers={k: v for k, v in headers.items() if k != "X-Radar-Token"}, json=body
        ).status_code
        == 403
    )
    saved = client.post(wish_path, headers=headers, json=body)
    assert saved.status_code == 200
    assert client.post(wish_path, headers=headers, json=body).status_code == 409
    assert (
        client.get("/api/applications", headers=headers).json()["wishlist"][0]["job_id"] == job.id
    )
    applied = client.post(app_path + "/applied", headers=headers, json={}).json()
    assert applied["application"]["status"] == "Applied"
    assert list_wishlist(config)
    removed = client.post(
        wish_path, headers=headers, json={"revision": saved.json()["revision"], "saved": False}
    )
    assert removed.status_code == 200 and not list_wishlist(config)
    assert client.get(app_path, headers=headers).json()["application"]["status"] == "Applied"


def test_backups_restore_wishlist_and_history_with_legacy_schema_preserved(seeded, tmp_path):
    config, repo, job = seeded
    set_wishlist(config, job.id, True, actor="telegram")
    archive = tmp_path / "wish.zip"
    source = Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    manifest = create_backup(source, archive)
    assert manifest["format_version"] == 2 and manifest["schema_version"] == 4
    assert verify_backup(archive) == manifest
    restored = tmp_path / "restore.db"
    assert restore_backup(archive, restored, protected=source) == manifest
    with closing(sqlite3.connect(wishlist_path(restored))) as db:
        assert db.execute("SELECT job_id FROM wishlist").fetchone()[0] == job.id
        assert db.execute("SELECT COUNT(*) FROM wishlist_history").fetchone()[0] == 1
    with pytest.raises(ValueError):
        restore_backup(archive, source, protected=source)
    with ZipFile(archive) as bundle:
        members = {name: bundle.read(name) for name in bundle.namelist()}
    members["wishlist.sqlite3"] += b"tamper"
    invalid = tmp_path / "tamper.zip"
    with ZipFile(invalid, "w", compression=ZIP_STORED) as bundle:
        for name, value in members.items():
            bundle.writestr(name, value)
    with pytest.raises(ValueError):
        verify_backup(invalid)


def test_archive_cards_include_zero_and_do_not_replay_alerts(seeded):
    config, repo, job = seeded
    low = job.model_copy(
        deep=True,
        update={
            "id": str(uuid4()),
            "fingerprint": uuid4().hex,
            "title": "Senior trading",
            "external_id": "zero",
            "apply_url": "https://example.com/zero",
        },
    )
    low.score_breakdown.exclusions = ["senior"]
    with repo.transaction():
        low, _ = repo.upsert(low)
    before = repo.db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    notifier, calls = notifier_calls()
    asyncio.run(send_catalogue(config, notifier, 1))
    cards = [
        payload
        for method, payload in calls
        if method == "sendMessage" and payload.get("parse_mode") == "HTML"
    ]
    assert len(cards) == 2 and any("Priorité · 0/100" in card["text"] for card in cards)
    assert all(len(card["reply_markup"]["inline_keyboard"]) == 3 for card in cards)
    assert repo.db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == before
