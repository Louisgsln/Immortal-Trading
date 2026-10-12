import asyncio
import itertools
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.test_telegram_control import FakeNotifier
from trading_radar import telegram_control as control
from trading_radar import telegram_digest as digest
from trading_radar.config import Company
from trading_radar.hsbc import SEARCH, parse_detail
from trading_radar.job_conditions import material_changes
from trading_radar.location_updates import location_change_key, location_label
from trading_radar.normalizer import normalize
from trading_radar.runtime_status import WatcherPulse, format_daily_status
from trading_radar.telegram_cards import format_alert
from trading_radar.telegram_jobs import units

ADDRESSES = ("Shenzhen, GD, CN", "Beijing, BJ, CN", "Shanghai, SH, CN")
NOW = datetime(2026, 10, 12, 7, tzinfo=UTC)


def hsbc_job():
    data = json.loads(Path("tests/fixtures/hsbc-location148.json").read_text())
    config = Company(name="HSBC", ats="hsbc", career_url=SEARCH)
    return normalize(parse_detail(data["detail"], data["row"], config, "hsbc_graduates"))


@pytest.mark.parametrize("order", list(itertools.permutations(ADDRESSES)))
def test_verified_hsbc_address_permutations_do_not_change_conditions_or_history(repo, order):
    job = hsbc_job()
    # This is the historical representation observed in production.
    original = job.model_copy(
        update={
            "location": "; ".join(ADDRESSES),
            "location_normalized": "shenzhen gd cn beijing bj cn shanghai sh cn",
        }
    )
    with repo.transaction():
        stored, event = repo.upsert(original)
    assert event == "new"
    before_versions = repo.db.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0]
    before_application = tuple(repo.db.execute("SELECT * FROM applications").fetchone())
    incoming = job.model_copy(
        update={
            "location": "; ".join(order),
            "location_normalized": " ".join(part.lower().replace(",", "") for part in order),
            "last_seen": stored.last_seen + timedelta(minutes=5),
        }
    )
    assert material_changes(stored, incoming) == []
    with repo.transaction():
        after, event = repo.upsert(incoming)
    assert (
        event == "unchanged" and after.id == stored.id and after.fingerprint == stored.fingerprint
    )
    assert after.first_seen == stored.first_seen and after.date_updated == stored.date_updated
    assert repo.db.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0] == before_versions
    assert tuple(repo.db.execute("SELECT * FROM applications").fetchone()) == before_application


@pytest.mark.parametrize(
    "location",
    [
        "Beijing, BJ, CN; Shanghai, SH, CN",
        "Beijing, BJ, CN; Shanghai, SH, CN; Shenzhen, GD, CN; Guangzhou, GD, CN",
        "Beijing, ZZ, CN; Shanghai, SH, CN; Shenzhen, GD, CN",
        "Beijing, BJ, US; Shanghai, SH, CN; Shenzhen, GD, CN",
        "Beijing, BJ, CN",
    ],
)
def test_real_city_region_country_changes_are_still_material(repo, location):
    before = hsbc_job()
    after = before.model_copy(
        update={"location": location, "location_normalized": location.lower()}
    )
    assert material_changes(before, after) == ["Localisation"]
    with repo.transaction():
        repo.upsert(before)
        stored, event = repo.upsert(after)
    assert event == "updated" and stored.id == before.id


def test_address_order_rule_is_scoped_and_alert_location_is_readable():
    job = hsbc_job()
    assert location_label(job) == "Beijing · Shanghai · Shenzhen · Chine"
    assert "📍 Beijing · Shanghai · Shenzhen · Chine" in format_alert(job, "updated")
    assert job.location == "Beijing, BJ, CN; Shanghai, SH, CN; Shenzhen, GD, CN"
    assert (
        location_change_key(job.model_copy(update={"source": "other"})) == job.location_normalized
    )


def test_real_title_or_deadline_change_is_not_absorbed_with_order_change():
    before = hsbc_job()
    after = before.model_copy(
        update={"location": "; ".join(reversed(ADDRESSES)), "title_normalized": "different role"}
    )
    assert material_changes(before, after) == ["Intitulé"]
    after = before.model_copy(
        update={"application_deadline": before.application_deadline + timedelta(days=1)}
    )
    assert "Échéance" in material_changes(before, after)


def report(status="active", fresh=74):
    return {
        "source_counts": {"enabled": 79, "employers": 67, "fresh": fresh},
        "watcher": {"status": status, "at": NOW.isoformat()},
        "health": {"database": {"status": "ok"}},
        "alerts_enabled": True,
        "threshold": 70,
    }


def test_daily_status_distinguishes_worker_activity_and_partial_coverage():
    text = format_daily_status(report())
    assert "Radar · actif" in text and "79 sources" in text and "74/79" in text
    assert "5 à surveiller" in text and "70/100" in text
    assert "Radar · actif" not in format_daily_status(report("stale"))
    assert "Fraîcheur des sources indisponible" in format_daily_status(report(fresh=None))


def test_no_offer_daily_digest_still_shows_heartbeat_and_survives_restarts(config, repo, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    pulse = WatcherPulse(config)
    pulse.publish("waiting")
    store = control.ControlStore(tmp_path / "control.json", "owner")
    store.state.offset = 193
    digest.enable_digest(store.state, "09:00", NOW - timedelta(hours=1))
    notifier = FakeNotifier()
    asyncio.run(digest.check_digest(config, notifier, store, NOW))
    assert len(notifier.sent) == 1 and "Radar ·" in notifier.sent[0]
    assert "Aucune offre vérifiée" in notifier.sent[0] and "sources" in notifier.sent[0]
    assert units(notifier.sent[0]) <= 4096 and store.state.offset == 193
    restored = control.ControlStore(store.path, "owner")
    asyncio.run(digest.check_digest(config, notifier, restored, NOW + timedelta(minutes=1)))
    assert len(notifier.sent) == 1 and restored.state.offset == 193


def test_daily_scheduler_does_not_read_disabled_incident_status(config, tmp_path, monkeypatch):
    config.settings.telegram_incident_notices_enabled = False
    store = control.ControlStore(tmp_path / "state.json", "owner")
    calls = []

    async def daily(*args):
        calls.append("daily")

    monkeypatch.setattr(control, "check_digest", daily)
    monkeypatch.setattr(
        control, "runtime_report", lambda *args: pytest.fail("Unneeded incident scan")
    )
    asyncio.run(control.check_scheduled_messages(config, FakeNotifier(), store, NOW))
    assert calls == ["daily"]


def test_daily_failure_cannot_block_incident_check(config, tmp_path, monkeypatch):
    config.settings.telegram_incident_notices_enabled = True
    store = control.ControlStore(tmp_path / "state.json", "owner")
    calls = []

    async def daily(*args):
        raise OSError("private details must not be logged")

    async def incidents(*args):
        calls.append("incident")

    monkeypatch.setattr(control, "check_digest", daily)
    monkeypatch.setattr(control, "check_incidents", incidents)
    monkeypatch.setattr(control, "runtime_report", lambda *args: report())
    asyncio.run(control.check_scheduled_messages(config, FakeNotifier(), store, NOW))
    assert calls == ["incident"]
