import asyncio
import json
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from filelock import FileLock, Timeout
from typer.testing import CliRunner

from trading_radar.alerts import AlertDecision, AlertStatus
from trading_radar.cli import app
from trading_radar.notifications import DeliveryUnknown, TelegramNotifier
from trading_radar.reminders import queue_reminders
from trading_radar.scanner import deliver
from trading_radar.storage import Repository


@pytest.fixture
def alert(repo, job):
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
    return repo.pending()[0]["id"]


def uncertain(repo, alert, state="unknown"):
    repo.set_alert(alert, "sending")
    if state == "unknown":
        repo.set_alert(alert, "unknown", "DeliveryUnknown")
    return repo.get_alert(alert)


@pytest.mark.parametrize("state", ["unknown", "sending"])
@pytest.mark.parametrize(
    "decision,expected", [("received", "sent"), ("dismiss", "suppressed"), ("retry", "pending")]
)
def test_resolve_uncertain_alert(repo, alert, state, decision, expected):
    before = uncertain(repo, alert, state)
    result = repo.resolve_alert(
        alert, AlertDecision(decision), before["revision"], "Checked delivery manually"
    )
    assert result["status"] == expected
    assert result["attempts"] == before["attempts"] == 1
    assert result["sent_at"] is None
    assert result["last_error"] == before["last_error"]
    history = repo.alert_history(alert)
    assert history[-1]["actor"] == "operator"
    assert history[-1]["decision"] == decision
    assert history[-1]["before"]["status"] == state
    assert history[-1]["after"]["status"] == expected
    assert history[-1]["revision"] == result["revision"] > before["revision"]
    assert history[-1]["reason"] == "Checked delivery manually"


def test_system_history_and_attempt_count(repo, alert):
    assert repo.get_alert(alert)["revision"] == 0
    repo.set_alert(alert, "sending")
    repo.set_alert(alert, "pending", "RuntimeError")
    repo.set_alert(alert, "sending")
    repo.set_alert(alert, "sent")
    record = repo.get_alert(alert)
    assert record["attempts"] == 2 and record["sent_at"]
    history = repo.alert_history(alert)
    assert [h["decision"] for h in history] == ["sending", "pending", "sending", "sent"]
    assert all(h["actor"] == "system" and h["reason"] is None for h in history)
    assert history[1]["after"] == history[2]["before"]
    repo.set_alert(alert, "sent")
    assert repo.get_alert(alert) == record  # Identical transition is a no-op.


def test_pending_can_be_dismissed_without_attempt(repo, alert):
    result = repo.resolve_alert(alert, AlertDecision.DISMISS, 0, "No longer useful")
    assert result["status"] == "suppressed" and result["attempts"] == 0
    assert not repo.pending()


@pytest.mark.parametrize("state", ["pending", "sent", "suppressed"])
@pytest.mark.parametrize("decision", list(AlertDecision))
def test_invalid_operator_transitions_write_nothing(repo, alert, state, decision):
    if state == "pending" and decision == AlertDecision.DISMISS:
        return
    if state == "sent":
        repo.set_alert(alert, "sending")
        repo.set_alert(alert, "sent")
    elif state == "suppressed":
        repo.set_alert(alert, "suppressed")
    before = list(repo.db.iterdump())
    with pytest.raises(ValueError):
        repo.resolve_alert(alert, decision, repo.get_alert(alert)["revision"], "reason")
    assert list(repo.db.iterdump()) == before


@pytest.mark.parametrize("reason", ["", "   ", "x" * 2001])
def test_reason_required(repo, alert, reason):
    state = uncertain(repo, alert)
    before = list(repo.db.iterdump())
    with pytest.raises(ValueError):
        repo.resolve_alert(alert, AlertDecision.RETRY, state["revision"], reason)
    assert list(repo.db.iterdump()) == before


def test_stale_revision_even_after_return_to_same_state(repo, alert):
    old = uncertain(repo, alert)
    repo.resolve_alert(alert, AlertDecision.RETRY, old["revision"], "Checked not received")
    uncertain(repo, alert)
    assert repo.get_alert(alert)["status"] == old["status"]
    with pytest.raises(ValueError, match="changed since inspection"):
        repo.resolve_alert(alert, AlertDecision.RETRY, old["revision"], "Old view")


def test_lock_blocks_decision_during_scanner_run(repo, alert):
    old = uncertain(repo, alert)
    with FileLock(repo.lock_path), pytest.raises(Timeout):
        repo.resolve_alert(alert, AlertDecision.RECEIVED, old["revision"], "Seen")
    assert repo.get_alert(alert) == old


@pytest.mark.parametrize("operator", [False, True])
def test_history_failure_rolls_back_state(repo, alert, operator):
    old = uncertain(repo, alert) if operator else repo.get_alert(alert)
    repo.db.execute("""CREATE TRIGGER reject_history BEFORE INSERT ON alert_history
        BEGIN SELECT RAISE(ABORT,'test rollback'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        if operator:
            repo.resolve_alert(alert, AlertDecision.RETRY, old["revision"], "Reason")
        else:
            repo.set_alert(alert, "sending")
    assert repo.get_alert(alert) == old


def test_invalid_system_transition_and_unknown_id(repo, alert):
    with pytest.raises(ValueError):
        repo.set_alert(alert, "sent")
    with pytest.raises(KeyError):
        repo.get_alert(9999)
    with pytest.raises(KeyError):
        repo.resolve_alert(9999, AlertDecision.RETRY, 0, "Reason")


def test_filters_pagination_and_read_only_inspection(repo, alert, job):
    first = alert
    uncertain(repo, first)
    with repo.transaction():
        repo.enqueue(job, "updated")
    second = repo.pending()[0]["id"]
    before = list(repo.db.iterdump())
    assert repo.list_alerts()["matching"] == 1
    assert repo.list_alerts()["alerts"][0]["id"] == first
    assert repo.list_alerts(AlertStatus.PENDING)["alerts"][0]["id"] == second
    assert repo.list_alerts(all_states=True, limit=1, offset=1)["alerts"][0]["id"] == second
    assert repo.list_alerts()["summary"] == {"pending": 1, "unknown": 1}
    assert repo.alert_details(first)["application_status"] == "New"
    assert repo.alert_history(first)
    assert list(repo.db.iterdump()) == before
    with pytest.raises(ValueError):
        repo.list_alerts(AlertStatus.PENDING, all_states=True)
    with pytest.raises(ValueError):
        repo.list_alerts(limit=0)


class FakeNotifier:
    def __init__(self):
        self.sent = []

    async def send(self, job, event):
        self.sent.append((job.id, event))


def test_retry_only_queues_then_deliver_rechecks_job(repo, alert, job):
    old = uncertain(repo, alert)
    repo.resolve_alert(alert, AlertDecision.RETRY, old["revision"], "Checked not received")
    assert repo.get_alert(alert)["attempts"] == 1
    job.is_active = False
    with repo.transaction():
        repo._write(job)
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70)) == 0
    assert not notifier.sent and repo.get_alert(alert)["status"] == "suppressed"
    assert repo.get_alert(alert)["attempts"] == 1


def test_retry_runs_once_and_keeps_operator_history(repo, alert):
    old = uncertain(repo, alert)
    repo.resolve_alert(alert, AlertDecision.RETRY, old["revision"], "Checked not received")
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70)) == 1
    assert asyncio.run(deliver(repo, notifier, 70)) == 0
    assert len(notifier.sent) == 1
    assert repo.get_alert(alert)["attempts"] == 2
    assert [r["actor"] for r in repo.alert_history(alert)] == [
        "system",
        "system",
        "operator",
        "system",
        "system",
    ]


def test_retry_deadline_still_obeys_application_and_enablement(repo, job):
    job.last_seen = datetime.now(UTC)
    job.application_deadline = job.last_seen + timedelta(days=2)
    with repo.transaction():
        repo.upsert(job)
    assert queue_reminders(repo, 70) == 1
    identifier = repo.pending()[0]["id"]
    old = uncertain(repo, identifier)
    repo.resolve_alert(identifier, AlertDecision.RETRY, old["revision"], "Checked not received")
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70, reminders_enabled=False)) == 0
    assert len(repo.pending()) == 1
    repo.update_application(job.id, {"status": "Applied"})
    assert asyncio.run(deliver(repo, notifier, 70, reminders_enabled=True)) == 0
    assert repo.get_alert(identifier)["status"] == "suppressed"
    assert not notifier.sent


def test_failed_success_commit_leaves_sending_and_does_not_replay(repo, alert):
    repo.db.execute("""CREATE TRIGGER reject_sent_history BEFORE INSERT ON alert_history
        WHEN NEW.decision='sent' BEGIN SELECT RAISE(ABORT,'test rollback'); END""")
    notifier = FakeNotifier()
    with pytest.raises(sqlite3.IntegrityError):
        asyncio.run(deliver(repo, notifier, 70))
    assert len(notifier.sent) == 1 and repo.get_alert(alert)["status"] == "sending"
    assert asyncio.run(deliver(repo, notifier, 70)) == 0


@pytest.mark.parametrize("payload", [{}, [], None, {"ok": "true"}, {"ok": 1}])
def test_malformed_telegram_ack_is_unknown(job, payload):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(DeliveryUnknown):
        asyncio.run(TelegramNotifier("123:test_token", "456", transport).send(job, "new"))


@pytest.mark.parametrize("status", [201, 204, 302, 500, 503])
def test_ambiguous_http_ack_is_unknown(job, status):
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    with pytest.raises(DeliveryUnknown):
        asyncio.run(TelegramNotifier("123:test_token", "456", transport).send(job, "new"))


@pytest.mark.parametrize(
    "status,payload", [(200, {"ok": False}), (400, {"ok": False}), (429, {"ok": False})]
)
def test_explicit_rejection_remains_retryable(job, status, payload):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=payload))
    with pytest.raises(RuntimeError) as exc:
        asyncio.run(TelegramNotifier("123:test_token", "456", transport).send(job, "new"))
    assert not isinstance(exc.value, DeliveryUnknown)
    assert "test_token" not in str(exc.value)


def test_migrate_v3_preserves_legacy_alerts_without_invented_history(repo, alert, tmp_path):
    with repo.db:
        repo.db.execute(
            "UPDATE alerts SET status='unknown',attempts=6,last_error='DeliveryUnknown' WHERE id=?",
            (alert,),
        )
        repo.db.execute("DROP TABLE alert_history")
        repo.db.execute("DELETE FROM schema_version WHERE version=4")
    upgraded = Repository(f"sqlite:///{tmp_path / 'jobs.db'}")
    try:
        old = upgraded.get_alert(alert)
        assert old["status"] == "unknown" and old["attempts"] == 6 and old["revision"] == 0
        assert not upgraded.alert_history(alert)
        assert upgraded.db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 4
        upgraded.resolve_alert(alert, AlertDecision.RECEIVED, 0, "Verified legacy delivery")
        assert upgraded.get_alert(alert)["attempts"] == 6
    finally:
        upgraded.close()


def test_newer_schema_is_rejected_before_any_migration(repo, tmp_path):
    with repo.db:
        repo.db.execute("INSERT INTO schema_version VALUES(99)")
        repo.db.execute("DROP TABLE alert_history")
    before = list(repo.db.iterdump())
    with pytest.raises(ValueError, match="newer"):
        Repository(f"sqlite:///{tmp_path / 'jobs.db'}")
    assert list(repo.db.iterdump()) == before


@pytest.fixture
def cli_env(tmp_path, monkeypatch, job):
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/jobs.db")
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    repo = Repository("sqlite:///data/jobs.db")
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
    alert = repo.pending()[0]["id"]
    old = uncertain(repo, alert)
    repo.close()
    return old


def test_cli_workflow_without_telegram(cli_env):
    runner = CliRunner()
    identifier = str(cli_env["id"])
    listing = runner.invoke(app, ["alerts", "list"])
    assert listing.exit_code == 0 and json.loads(listing.output)["matching"] == 1
    result = runner.invoke(app, ["alerts", "show", identifier])
    assert result.exit_code == 0 and json.loads(result.output)["revision"] == cli_env["revision"]
    result = runner.invoke(
        app,
        [
            "alerts",
            "resolve",
            identifier,
            "--decision",
            "received",
            "--revision",
            str(cli_env["revision"]),
            "--reason",
            "Vu dans Telegram",
        ],
    )
    assert result.exit_code == 0 and json.loads(result.output)["status"] == "sent"
    history = runner.invoke(app, ["alerts", "history", identifier])
    assert json.loads(history.output)[-1]["reason"] == "Vu dans Telegram"
    assert json.loads(runner.invoke(app, ["alerts", "list"]).output)["matching"] == 0
    assert json.loads(runner.invoke(app, ["alerts", "list", "--all"]).output)["matching"] == 1
    assert (
        json.loads(runner.invoke(app, ["alerts", "list", "--all", "--demo"]).output)["matching"]
        == 0
    )


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--decision", "invalid"],
        ["--decision", "retry", "--revision", "0", "--reason", "Old view"],
        ["--decision", "retry", "--revision", "2", "--reason", " "],
    ],
)
def test_cli_bad_resolution_keeps_state(cli_env, args):
    result = CliRunner().invoke(app, ["alerts", "resolve", str(cli_env["id"]), *args])
    assert result.exit_code != 0
    state = json.loads(CliRunner().invoke(app, ["alerts", "show", str(cli_env["id"])]).output)
    assert state["status"] == "unknown" and state["revision"] == cli_env["revision"]


def test_cli_unknown_id_and_busy_writer(cli_env):
    runner = CliRunner()
    result = runner.invoke(app, ["alerts", "show", "9999"])
    assert result.exit_code == 1 and "Unknown alert ID" in result.output
    with FileLock("data/jobs.db.lock"):
        result = runner.invoke(
            app,
            [
                "alerts",
                "resolve",
                str(cli_env["id"]),
                "--decision",
                "dismiss",
                "--revision",
                str(cli_env["revision"]),
                "--reason",
                "Reason",
            ],
        )
    assert result.exit_code == 1 and "busy" in result.output
