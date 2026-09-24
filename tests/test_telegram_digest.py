import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from tests.test_dashboard_data import fingerprints
from tests.test_telegram_control import FakeNotifier, update
from trading_radar import telegram_control as control
from trading_radar import telegram_digest as digest
from trading_radar.models import Score
from trading_radar.runtime_status import atomic_json
from trading_radar.telegram_jobs import units

NOW = datetime(2026, 9, 24, 7, tzinfo=UTC)  # 09:00 Paris


@pytest.fixture
def local(config, tmp_path, repo):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    return config


@pytest.fixture
def store(tmp_path):
    return control.ControlStore(tmp_path / "state.json", "owner")


def test_old_cursor_loads_without_enabling_digest(tmp_path):
    path = tmp_path / "old.json"
    atomic_json(path, {"binding": "owner", "offset": 19, "notified": ["issue"]})
    store = control.ControlStore(path, "owner")
    assert not store.state.digest_enabled and store.state.offset == 19
    store.save()
    assert control.ControlStore(path, "owner").state.notified == ["issue"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("digest_enabled", "true"),
        ("digest_time", "24:00"),
        ("digest_time", "9:00"),
        ("digest_time", "09:00\n"),
        ("digest_last_day", "2026-02-30"),
        ("digest_last_day", "20260924"),
        ("digest_not_before", -1.0),
        ("digest_not_before", float("nan")),
    ],
)
def test_invalid_schedule_fails_closed(field, value):
    with pytest.raises(ValidationError):
        control.ControlState(binding="owner", **{field: value})


@pytest.mark.parametrize(
    "day,expected",
    [
        (date(2026, 1, 15), 8),
        (date(2026, 7, 15), 7),
        (date(2026, 3, 29), 7),
        (date(2026, 10, 25), 8),
    ],
)
def test_nine_paris_follows_daylight_saving(day, expected):
    assert digest.scheduled(day, "09:00") == datetime(
        day.year, day.month, day.day, expected, tzinfo=UTC
    )


def test_dst_gap_and_overlap_have_one_explicit_instant():
    assert digest.scheduled(date(2026, 3, 29), "02:30") == datetime(2026, 3, 29, 1, 30, tzinfo=UTC)
    assert digest.scheduled(date(2026, 10, 25), "02:30") == datetime(
        2026, 10, 25, 0, 30, tzinfo=UTC
    )


@pytest.mark.parametrize("offset,expected_day", [(-1, 24), (0, 25), (1, 25)])
def test_activation_starts_at_next_future_slot(store, offset, expected_day):
    digest.enable_digest(store.state, "09:00", NOW + timedelta(seconds=offset))
    assert datetime.fromtimestamp(store.state.digest_not_before, UTC).day == expected_day
    assert store.state.digest_enabled


def test_disabled_digest_never_reads_or_sends(local, store, monkeypatch):
    monkeypatch.setattr(digest, "digest_message", lambda *a: pytest.fail("Read"))
    notifier = FakeNotifier()
    asyncio.run(digest.check_digest(local, notifier, store, NOW))
    assert not notifier.sent and not store.path.exists()


@pytest.mark.parametrize("fail", [False, True])
def test_one_attempt_per_day_survives_restart_and_uncertain_delivery(local, store, fail):
    digest.enable_digest(store.state, "09:00", NOW - timedelta(hours=1))
    notifier = FakeNotifier(fail=fail)
    before = NOW - timedelta(seconds=1)
    asyncio.run(digest.check_digest(local, notifier, store, before))
    assert not notifier.sent
    asyncio.run(digest.check_digest(local, notifier, store, NOW))
    assert len(notifier.sent) == 1 and store.state.digest_last_day == "2026-09-24"
    restored = control.ControlStore(store.path, "owner")
    asyncio.run(digest.check_digest(local, notifier, restored, NOW + timedelta(hours=1)))
    assert len(notifier.sent) == 1
    asyncio.run(digest.check_digest(local, notifier, restored, NOW + timedelta(days=1)))
    assert len(notifier.sent) == 2


@pytest.mark.parametrize("offset,expected", [(0, 1), (14399, 1), (14400, 0), (20000, 0)])
def test_four_hour_catchup_window(local, store, offset, expected):
    digest.enable_digest(store.state, None, NOW - timedelta(days=1))
    notifier = FakeNotifier()
    asyncio.run(digest.check_digest(local, notifier, store, NOW + timedelta(seconds=offset)))
    assert len(notifier.sent) == expected


def test_late_evening_catchup_crosses_midnight(local, store):
    digest.enable_digest(store.state, "23:30", NOW)
    notifier = FakeNotifier()
    after_midnight = datetime(2026, 9, 24, 23, tzinfo=UTC)  # 25 September, 01:00 Paris
    asyncio.run(digest.check_digest(local, notifier, store, after_midnight))
    assert len(notifier.sent) == 1 and store.state.digest_last_day == "2026-09-24"


def test_clock_rollback_and_schedule_change_cannot_duplicate_day(local, store):
    notifier = FakeNotifier()
    digest.enable_digest(store.state, None, NOW - timedelta(seconds=1))
    asyncio.run(digest.check_digest(local, notifier, store, NOW))
    digest.enable_digest(store.state, "10:00", NOW)
    asyncio.run(digest.check_digest(local, notifier, store, NOW + timedelta(hours=1)))
    asyncio.run(digest.check_digest(local, notifier, store, NOW - timedelta(days=1)))
    assert len(notifier.sent) == 1


def test_failed_persistence_prevents_delivery(local, store, monkeypatch):
    digest.enable_digest(store.state, None, NOW - timedelta(hours=1))
    notifier = FakeNotifier()

    def fail():
        raise OSError("disk full")

    monkeypatch.setattr(store, "save", fail)
    with pytest.raises(OSError):
        asyncio.run(digest.check_digest(local, notifier, store, NOW))
    assert not notifier.sent


@pytest.mark.parametrize(
    "text,expected",
    [
        ("/digest", "digest"),
        ("/digest_on", "digest_on"),
        ("/digest_on 19:00", "digest_on 19:00"),
        ("/digest_on@RadarBot 09:30", "digest_on 09:30"),
        ("/digest_on 25:00", "digest_usage"),
        ("/digest_off 19:00", "digest_usage"),
        ("/digest_on 9h", "digest_usage"),
        ("/digest_on 09:00\n/status", None),
        ("/digest_on@OtherBot 09:00", None),
    ],
)
def test_digest_command_arguments(text, expected):
    assert control.command_from(update(text=text), "456", "RadarBot", 10000) == expected


def test_private_activation_disable_and_preview_preserve_business_tables(local, store, repo):
    notifier = FakeNotifier()
    before = fingerprints(repo)
    now = int(NOW.timestamp())
    for index, command in enumerate(["/digest_on 19:00", "/digest", "/digest_off"], 1):
        asyncio.run(
            control.process_updates(
                [update(index, command, now)], local, notifier, store, "RadarBot", now
            )
        )
    assert not store.state.digest_enabled and store.state.digest_time == "19:00"
    assert "activé" in notifier.sent[0] and "APERÇU À LA DEMANDE" in notifier.sent[1]
    assert "désactivé" in notifier.sent[2] and store.state.digest_last_day is None
    assert fingerprints(repo) == before


def test_unauthorized_activation_is_ignored(local, store):
    item = update(text="/digest_on 09:00")
    item["message"]["from"]["id"] = 999
    notifier = FakeNotifier()
    asyncio.run(control.process_updates([item], local, notifier, store, "RadarBot", 10000))
    assert not store.state.digest_enabled and not notifier.sent


def test_digest_length_privacy_and_complete_links(local, store, repo, job):
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO companies(source,last_success,bootstrapped) VALUES('test',?,1)",
            ((NOW - timedelta(minutes=1)).isoformat(),),
        )
        for index in range(6):
            candidate = job.model_copy(deep=True)
            candidate.id = candidate.fingerprint = f"large-{index}"
            candidate.external_id = str(index)
            candidate.title = candidate.title_normalized = "🚀" * 2000
            candidate.apply_url = "https://example.com/" + "x" * 675 + str(index)
            candidate.first_seen = candidate.last_seen = NOW - timedelta(minutes=10)
            candidate.score_breakdown = Score(trading=30, junior=20, start=15, front_office=15)
            repo.upsert(candidate)
    repo.update_application(candidate.id, {"notes": "PRIVATE NOTE"})
    now = int(NOW.timestamp())
    notifier = FakeNotifier()
    before = fingerprints(repo)
    asyncio.run(
        control.process_updates(
            [update(1, "/digest", now)], local, notifier, store, "RadarBot", now
        )
    )
    text = notifier.sent[0]
    assert units(text) <= 4096 and "PRIVATE NOTE" not in text
    assert "Sources à jour : 1/1" in text and "sur 6 correspondance(s)" in text
    assert "https://example.com/" + "x" * 675 + "0" in text
    assert fingerprints(repo) == before


def test_missing_database_produces_explicit_digest_problem(local, tmp_path):
    local.settings.database_url = f"sqlite:///{tmp_path / 'missing.db'}"
    text = digest.digest_message(local, NOW)
    assert "Offres indisponibles" in text and "État des sources indisponible" in text
    assert not (tmp_path / "missing.db").exists()


def test_listener_checks_schedule_without_incoming_commands(local, monkeypatch):
    local.settings.telegram_control_enabled = True
    local.settings.telegram_incident_notices_enabled = False
    notifier = FakeNotifier()
    notifier.token = "123:synthetic"
    monkeypatch.setattr(control.TelegramNotifier, "from_env", lambda: notifier)
    checked = []
    polls = []

    async def remote(_, method, payload):
        if method == "getMe":
            return {"username": "RadarBot"}
        if method == "getWebhookInfo":
            return {"url": ""}
        if method == "setMyCommands":
            assert {"digest", "digest_on", "digest_off"} <= {
                c["command"] for c in payload["commands"]
            }
            return True
        polls.append(payload)
        if len(polls) > 1:
            raise asyncio.CancelledError
        return []

    async def check(config, notifier, store, now):
        checked.append(now)

    monkeypatch.setattr(control, "api", remote)
    monkeypatch.setattr(control, "check_digest", check)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(control.run_control(local))
    assert len(checked) == 1 and checked[0].tzinfo == UTC


def test_invalid_time_does_not_change_preferences(local, store):
    notifier = FakeNotifier()
    asyncio.run(
        control.process_updates(
            [update(text="/digest_on 27:00")], local, notifier, store, "RadarBot", 10000
        )
    )
    assert not store.state.digest_enabled and "Exemple" in notifier.sent[0]
