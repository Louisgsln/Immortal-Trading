import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from tests.test_telegram_control import FakeNotifier
from trading_radar import runtime_status
from trading_radar import telegram_control as control
from trading_radar import telegram_heartbeat as heartbeat
from trading_radar.config import Settings
from trading_radar.runtime_status import WatcherPulse
from trading_radar.telegram_jobs import units

NOW = datetime(2026, 10, 12, 11, tzinfo=UTC)  # 13:00 Paris


@pytest.fixture
def local(config, repo, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    config.settings.telegram_heartbeat_enabled = True
    store = control.ControlStore(tmp_path / "jobs.telegram.json", "owner")
    store.state.offset = 193
    store.state.digest_enabled = True
    store.save()
    heartbeat.load_state(heartbeat.heartbeat_path(config), "owner", NOW - timedelta(hours=1))
    return config, store


def check(local, notifier, now=NOW):
    config, store = local
    asyncio.run(heartbeat.check_heartbeat(config, notifier, store, now))


def test_each_slot_is_once_and_cursor_and_digest_untouched_after_restart(local):
    config, store = local
    before = store.path.read_bytes()
    notifier = FakeNotifier()
    check(local, notifier)
    check(local, notifier, NOW + timedelta(minutes=1))
    restored = control.ControlStore(store.path, "owner")
    check((config, restored), notifier, NOW + timedelta(minutes=2))
    assert len(notifier.sent) == 1 and "Radar ·" in notifier.sent[0]
    check((config, restored), notifier, NOW + timedelta(hours=5))
    assert len(notifier.sent) == 2 and store.path.read_bytes() == before
    assert units(notifier.sent[0]) < 4096
    state = json.loads(heartbeat.heartbeat_path(config).read_text())
    assert state["attempts"] == {"13:00": "2026-10-12", "18:00": "2026-10-12"}


def test_uncertain_delivery_is_not_retried(local):
    notifier = FakeNotifier(fail=True)
    check(local, notifier)
    check(local, notifier, NOW + timedelta(minutes=1))
    assert len(notifier.sent) == 1


def test_cannot_send_before_attempt_is_persisted(local, monkeypatch):
    notifier = FakeNotifier()

    def failed(*args):
        raise OSError("Disk unavailable")

    monkeypatch.setattr(heartbeat, "atomic_json", failed)
    with pytest.raises(OSError):
        check(local, notifier)
    assert not notifier.sent


@pytest.mark.parametrize("seconds,expected", [(-1, 0), (0, 1), (3599, 1), (3600, 0)])
def test_one_hour_catchup_window(local, seconds, expected):
    notifier = FakeNotifier()
    check(local, notifier, NOW + timedelta(seconds=seconds))
    assert len(notifier.sent) == expected


def test_activation_does_not_send_a_past_slot(local):
    config, store = local
    heartbeat.heartbeat_path(config).unlink()
    notifier = FakeNotifier()
    check(local, notifier, NOW + timedelta(minutes=1))
    assert not notifier.sent
    check(local, notifier, NOW + timedelta(hours=5))
    assert len(notifier.sent) == 1


def test_latest_slot_only_after_outage(local):
    config, _ = local
    config.settings.telegram_heartbeat_times = ["13:00", "13:30"]
    notifier = FakeNotifier()
    check(local, notifier, NOW + timedelta(minutes=40))
    check(local, notifier, NOW + timedelta(minutes=41))
    assert len(notifier.sent) == 1


def test_shared_digest_slot_does_not_duplicate_status(local):
    config, store = local
    config.settings.telegram_heartbeat_times = ["09:00", "13:00", "18:00"]
    store.state.digest_time = "13:00"
    store.state.digest_last_day = "2026-10-12"
    notifier = FakeNotifier()
    check(local, notifier)
    assert not notifier.sent
    check(local, notifier, NOW + timedelta(hours=5))
    assert len(notifier.sent) == 1


def test_wrong_destination_fails_closed(local):
    config, store = local
    store.state.binding = "different-owner"
    notifier = FakeNotifier()
    with pytest.raises(ValueError, match="destination"):
        check(local, notifier)
    assert not notifier.sent


def test_disabled_never_creates_or_reads_state(local, monkeypatch):
    config, _ = local
    config.settings.telegram_heartbeat_enabled = False
    monkeypatch.setattr(heartbeat, "load_state", lambda *args: pytest.fail("Read"))
    notifier = FakeNotifier()
    check(local, notifier)
    assert not notifier.sent


@pytest.mark.parametrize("clocks", [["24:00"], ["9:00"], ["13:00", "13:00"], ["13:00\n"], []])
def test_schedule_validation(clocks):
    with pytest.raises(ValidationError):
        Settings(telegram_heartbeat_times=clocks)


@pytest.mark.parametrize("value", [float("nan"), -1.0])
def test_invalid_persisted_state(value):
    with pytest.raises(ValidationError):
        heartbeat.HeartbeatState(binding="owner", not_before=value)


def test_clock_rollback_and_autumn_dst_overlap_do_not_duplicate(local):
    config, _ = local
    config.settings.telegram_heartbeat_times = ["02:30"]
    path = heartbeat.heartbeat_path(config)
    path.unlink()
    first = datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    heartbeat.load_state(path, "owner", first - timedelta(hours=1))
    notifier = FakeNotifier()
    check(local, notifier, first)
    check(local, notifier, first + timedelta(hours=1))
    check(local, notifier, first - timedelta(seconds=1))
    assert len(notifier.sent) == 1


def test_stopped_worker_is_not_reported_as_running(local, monkeypatch):
    config, _ = local
    report = runtime_status.runtime_report(config, now=NOW)
    report["watcher"] = {"status": "stopped", "at": NOW.isoformat()}
    monkeypatch.setattr(heartbeat, "runtime_report", lambda *args, **kwargs: report)
    notifier = FakeNotifier()
    check(local, notifier)
    assert "Radar · arrêté" in notifier.sent[0] and "Veille 24 h/24" not in notifier.sent[0]


def test_slow_health_check_cannot_make_current_pulse_appear_future(local, monkeypatch):
    config, _ = local
    pulse = WatcherPulse(config)
    monkeypatch.setattr(runtime_status, "utcnow", lambda: NOW)
    pulse.publish("waiting")
    original = runtime_status.check_health

    def slow(config, **kwargs):
        monkeypatch.setattr(runtime_status, "utcnow", lambda: NOW + timedelta(seconds=10))
        pulse.publish()
        return original(config, **kwargs)

    monkeypatch.setattr(runtime_status, "check_health", slow)
    report = runtime_status.runtime_report(config, now=NOW)
    assert report["watcher"]["status"] == "active" and report["watcher"]["age_seconds"] == 0


def test_daily_failure_does_not_block_heartbeat(local, monkeypatch):
    config, store = local

    async def daily(*args):
        raise RuntimeError("Unavailable")

    monkeypatch.setattr(control, "check_digest", daily)
    notifier = FakeNotifier()
    asyncio.run(control.check_scheduled_messages(config, notifier, store, NOW))
    assert len(notifier.sent) == 1


def test_listener_checks_schedules_before_failed_update_poll(config, repo, tmp_path, monkeypatch):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    config.settings.telegram_control_enabled = True
    notifier = FakeNotifier()
    notifier.token = "123:synthetic"
    monkeypatch.setattr(control.TelegramNotifier, "from_env", lambda: notifier)
    events = []

    async def scheduled(*args):
        events.append("scheduled")

    async def remote(_, method, payload):
        if method == "getMe":
            return {"username": "RadarBot"}
        if method == "getWebhookInfo":
            return {"url": ""}
        if method == "setMyCommands":
            return True
        events.append("poll")
        if events.count("poll") == 1:
            raise RuntimeError("Unavailable")
        raise asyncio.CancelledError

    async def no_sleep(_):
        pass

    monkeypatch.setattr(control, "check_scheduled_messages", scheduled)
    monkeypatch.setattr(control, "api", remote)
    monkeypatch.setattr(control.asyncio, "sleep", no_sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(control.run_control(config))
    assert events[:2] == ["scheduled", "poll"] and events.count("poll") == 2
