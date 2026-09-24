import asyncio
import time
from datetime import timedelta

import httpx
import pytest

from trading_radar import telegram_control as control
from trading_radar.models import utcnow
from trading_radar.notifications import DeliveryUnknown, TelegramNotifier, format_message
from trading_radar.runtime_status import (
    WatcherPulse,
    atomic_json,
    format_status,
    pulse_path,
    runtime_report,
    watcher_status,
)


@pytest.fixture
def local_config(config, tmp_path, repo):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    config.settings.telegram_control_enabled = True
    config.settings.telegram_incident_notices_enabled = True
    return config


def update(identifier=1, text="/status", now=10000):
    return {
        "update_id": identifier,
        "message": {
            "date": now,
            "text": text,
            "chat": {"id": 456, "type": "private"},
            "from": {"id": 456, "is_bot": False},
        },
    }


class FakeNotifier:
    chat_id = "456"

    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    async def send_text(self, text):
        self.sent.append(text)
        if self.fail:
            raise DeliveryUnknown("synthetic")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("/status", "status"),
        ("/status@RadarBot", "status"),
        ("/status@radarbot", "status"),
        ("/start radar", "start"),
        ("/help", "help"),
        ("/status@OtherBot", None),
        ("hello /status", None),
        ("/stop", None),
        ("/status\n/stop", None),
        ("https://example.com", None),
    ],
)
def test_only_supported_commands(text, expected):
    assert control.command_from(update(text=text), "456", "RadarBot", 10000) == expected


@pytest.mark.parametrize(
    "area,field,value",
    [
        ("chat", "id", 789),
        ("chat", "id", "456"),
        ("chat", "type", "group"),
        ("chat", "type", "supergroup"),
        ("from", "id", 789),
        ("from", "is_bot", True),
        ("from", "is_bot", None),
        ("from", "id", True),
    ],
)
def test_other_senders_and_chats_cannot_request_status(area, field, value):
    item = update()
    item["message"][area][field] = value
    assert control.command_from(item, "456", "RadarBot", 10000) is None


@pytest.mark.parametrize("date", [True, "10000", 9699, 10001, None])
def test_old_future_or_invalid_messages_are_ignored(date):
    item = update()
    item["message"]["date"] = date
    assert control.command_from(item, "456", "RadarBot", 10000) is None


def test_command_replay_never_resends_after_uncertain_delivery(local_config, tmp_path):
    path = tmp_path / "cursor.json"
    store = control.ControlStore(path, "owner")
    notifier = FakeNotifier(fail=True)
    asyncio.run(
        control.process_updates([update()], local_config, notifier, store, "RadarBot", 10000)
    )
    assert len(notifier.sent) == 1 and store.state.offset == 2
    reloaded = control.ControlStore(path, "owner")
    asyncio.run(
        control.process_updates([update()], local_config, notifier, reloaded, "RadarBot", 10000)
    )
    assert len(notifier.sent) == 1


def test_untrusted_chat_is_consumed_without_reading_status(local_config, tmp_path, monkeypatch):
    item = update()
    item["message"]["chat"]["id"] = 999
    monkeypatch.setattr(control, "runtime_report", lambda _: pytest.fail("Read private data"))
    notifier = FakeNotifier()
    store = control.ControlStore(tmp_path / "state.json", "owner")
    asyncio.run(control.process_updates([item], local_config, notifier, store, "RadarBot", 10000))
    assert not notifier.sent and store.state.offset == 2


def test_cursor_write_failure_prevents_send(local_config, tmp_path, monkeypatch):
    notifier = FakeNotifier()
    store = control.ControlStore(tmp_path / "state.json", "owner")

    def fail():
        raise OSError("disk full")

    monkeypatch.setattr(store, "save", fail)
    with pytest.raises(OSError):
        asyncio.run(
            control.process_updates([update()], local_config, notifier, store, "RadarBot", 10000)
        )
    assert not notifier.sent


@pytest.mark.parametrize(
    "batch",
    [
        {},
        [None],
        [{"update_id": True}],
        [update(2), update(1)],
        [update(), update()],
        [{"update_id": -1}],
        [update()] * 101,
    ],
)
def test_bad_update_batches_do_not_advance_cursor(batch, local_config, tmp_path):
    notifier = FakeNotifier()
    store = control.ControlStore(tmp_path / "state.json", "owner")
    with pytest.raises(ValueError):
        asyncio.run(
            control.process_updates(batch, local_config, notifier, store, "RadarBot", 10000)
        )
    assert store.state.offset == 0 and not notifier.sent


def test_command_burst_is_bounded(local_config, tmp_path):
    notifier = FakeNotifier()
    store = control.ControlStore(tmp_path / "state.json", "owner")
    asyncio.run(
        control.process_updates(
            [update(i, "/help") for i in range(1, 11)],
            local_config,
            notifier,
            store,
            "RadarBot",
            10000,
        )
    )
    assert len(notifier.sent) == 3 and store.state.offset == 11


def test_cursor_binding_and_corruption_fail_closed(tmp_path):
    path = tmp_path / "state.json"
    control.ControlStore(path, "first").save()
    with pytest.raises(ValueError):
        control.ControlStore(path, "second")
    path.write_text('{"offset": 5}')
    with pytest.raises(ValueError):
        control.ControlStore(path, "first")


def test_status_preserves_all_business_tables(local_config, repo, job):
    repo.upsert(job)
    before = list(repo.db.iterdump())
    report = runtime_report(local_config)
    assert report["watcher"]["status"] == "unknown"
    assert "activité non vérifiable" in format_status(report)
    assert "Base : accessible" in format_status(report)
    assert list(repo.db.iterdump()) == before


@pytest.mark.parametrize(
    "phase,age,status",
    [
        ("waiting", 10, "active"),
        ("scanning", 20, "active"),
        ("waiting", 91, "stale"),
        ("stopped", 2, "stopped"),
        ("waiting", -1, "unknown"),
        ("invalid", 2, "unknown"),
    ],
)
def test_pulse_freshness_is_distinct_from_source_freshness(local_config, phase, age, status):
    now = utcnow()
    atomic_json(
        pulse_path(local_config),
        {
            "version": 1,
            "phase": phase,
            "at": (now - timedelta(seconds=age)).isoformat(),
            "scan_started": (now - timedelta(seconds=40)).isoformat(),
        },
    )
    assert watcher_status(local_config, now)["status"] == status


def test_long_scan_and_clean_stop(local_config):
    now = utcnow()
    pulse = WatcherPulse(local_config)
    pulse.publish("scanning")
    pulse.value["scan_started"] = (now - timedelta(seconds=1900)).isoformat()
    pulse.publish()
    assert watcher_status(local_config)["status"] == "long_scan"

    async def lifetime():
        async with pulse:
            pulse.publish("waiting")
            assert watcher_status(local_config)["status"] == "active"
            await asyncio.sleep(0)

    asyncio.run(lifetime())
    assert watcher_status(local_config)["status"] == "stopped"


def test_incident_debounce_cooldown_recovery_and_restart(local_config, tmp_path):
    report = runtime_report(local_config)
    notifier = FakeNotifier()
    path = tmp_path / "notice.json"
    store = control.ControlStore(path, "owner")

    def tick(now):
        asyncio.run(control.check_incidents(local_config, notifier, store, report, now))

    tick(10000)
    tick(10119)
    assert not notifier.sent
    tick(10120)
    assert len(notifier.sent) == 1
    store = control.ControlStore(path, "owner")
    tick(14000)
    assert len(notifier.sent) == 1
    report["health"]["issues"] = []
    report["watcher"]["status"] = "active"
    tick(14001)
    tick(14121)
    assert len(notifier.sent) == 2 and "RETOUR À UN ÉTAT NORMAL" in notifier.sent[-1]


def test_uncertain_incident_is_not_retried(local_config, tmp_path):
    store = control.ControlStore(tmp_path / "notice.json", "owner")
    notifier = FakeNotifier(fail=True)
    report = runtime_report(local_config)
    for now in (10000, 10121, 20000):
        asyncio.run(control.check_incidents(local_config, notifier, store, report, now))
    assert len(notifier.sent) == 1


def test_incidents_disabled_means_no_send(local_config, tmp_path):
    local_config.settings.telegram_incident_notices_enabled = False
    notifier = FakeNotifier()
    store = control.ControlStore(tmp_path / "notice.json", "owner")
    asyncio.run(
        control.check_incidents(local_config, notifier, store, runtime_report(local_config), 10000)
    )
    assert not notifier.sent and not store.path.exists()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, text="invalid"),
        httpx.Response(200, json={"ok": False}),
        httpx.Response(200, json={"ok": True}),
    ],
)
def test_api_errors_do_not_expose_credentials(response):
    notifier = TelegramNotifier(
        "123:private", "456", transport=httpx.MockTransport(lambda _: response)
    )
    with pytest.raises(RuntimeError, match="Telegram API unavailable") as exc:
        asyncio.run(control.api(notifier, "getUpdates", {}))
    assert "private" not in str(exc.value)


def test_french_notification_unknown_values_and_utf16_limit(job):
    job.minimum_experience_years = 0
    text = format_message(job, "new")
    assert "NOUVELLE OFFRE" in text and "minimum reconnu 0 an(s)" in text
    assert "Échéance : Non précisée" in text and job.apply_url in text
    assert "publication" not in text.lower().split("Début :")[-1][:30]
    job.title = "🚀" * 1000
    job.description_text = "🚀" * 10000
    assert len(format_message(job, "updated").encode("utf-16-le")) <= 8000


def test_send_text_rejects_oversize_before_transport():
    notifier = TelegramNotifier(
        "123:private", "456", transport=httpx.MockTransport(lambda _: pytest.fail("Network"))
    )
    with pytest.raises(ValueError):
        asyncio.run(notifier.send_text("🚀" * 2049))


def test_listener_registers_private_menu_and_resumes_cursor(local_config, monkeypatch):
    notifier = FakeNotifier()
    notifier.token = "123:synthetic"
    monkeypatch.setattr(control.TelegramNotifier, "from_env", lambda: notifier)
    calls = []

    async def remote(_, method, payload):
        calls.append((method, payload))
        if method == "getMe":
            return {"username": "RadarBot"}
        if method == "getWebhookInfo":
            return {"url": ""}
        if method == "setMyCommands":
            return True
        if len([c for c in calls if c[0] == "getUpdates"]) == 1:
            return [update(now=int(time.time()))]
        raise asyncio.CancelledError

    monkeypatch.setattr(control, "api", remote)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(control.run_control(local_config))
    assert len(notifier.sent) == 1 and "ÉTAT DU RADAR" in notifier.sent[0]
    menu = next(payload for method, payload in calls if method == "setMyCommands")
    assert menu["scope"] == {"type": "chat", "chat_id": "456"}
    assert calls[-1][1]["offset"] == 2
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(control.run_control(local_config))
    assert calls[-1][1]["offset"] == 2 and len(notifier.sent) == 1


def test_existing_webhook_is_not_deleted(local_config, monkeypatch):
    notifier = FakeNotifier()
    notifier.token = "123:synthetic"
    monkeypatch.setattr(control.TelegramNotifier, "from_env", lambda: notifier)
    calls = []

    async def remote(_, method, payload):
        calls.append(method)
        return {"username": "RadarBot"} if method == "getMe" else {"url": "https://example.com"}

    monkeypatch.setattr(control, "api", remote)
    with pytest.raises(ValueError, match="webhook"):
        asyncio.run(control.run_control(local_config))
    assert calls == ["getMe", "getWebhookInfo"] and not notifier.sent


def test_disabled_control_never_contacts_telegram(local_config, monkeypatch):
    local_config.settings.telegram_control_enabled = False
    monkeypatch.setattr(control.TelegramNotifier, "from_env", lambda: pytest.fail("Transport"))
    with pytest.raises(ValueError, match="disabled"):
        asyncio.run(control.run_control(local_config))


@pytest.mark.parametrize("chat_id", ["-100456", "@somegroup", "0"])
def test_control_requires_private_destination(local_config, monkeypatch, chat_id):
    notifier = FakeNotifier()
    notifier.chat_id = chat_id
    monkeypatch.setattr(control.TelegramNotifier, "from_env", lambda: notifier)
    with pytest.raises(ValueError, match="private numeric"):
        asyncio.run(control.run_control(local_config))


def test_pulse_ticks_while_scan_is_awaiting(local_config, monkeypatch):
    original = asyncio.wait_for

    async def fast_tick(awaitable, timeout):
        return await original(awaitable, min(timeout, 0.01))

    monkeypatch.setattr(asyncio, "wait_for", fast_tick)

    async def scenario():
        async with WatcherPulse(local_config) as pulse:
            pulse.publish("scanning")
            before = watcher_status(local_config)["at"]
            await asyncio.sleep(0.04)
            after = watcher_status(local_config)
            assert after["phase"] == "scanning" and after["at"] > before

    asyncio.run(scenario())
