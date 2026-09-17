import asyncio
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trading_radar.applications import Application, ApplicationStatus
from trading_radar.cli import app
from trading_radar.deadlines import aware_instant, extract_deadline, resolve_deadline
from trading_radar.models import Collection
from trading_radar.normalizer import normalize
from trading_radar.notifications import DeliveryUnknown, format_message
from trading_radar.reminders import deadline_plan, queue_reminders, reminder_plans
from trading_radar.scanner import deliver, scan
from trading_radar.storage import Repository
from trading_radar.vendor import map_row

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Application Deadline: Friday, October 30, 2026 – 23:59 HKT", "2026-10-30T15:59:00+00:00"),
        (
            "Application Deadline Please apply before 11:55pm, Wednesday 30 September 2026 (SGT)",
            "2026-09-30T15:55:00+00:00",
        ),
        (
            "Applications close at 17:00 CEST on 20 September 2026, and assessments finish later. Applications close on 20 September 2026.",
            "2026-09-20T15:00:00+00:00",
        ),
        ("Closing date: 2026-10-30 at 12:00 UTC", "2026-10-30T12:00:00+00:00"),
        ("Application deadline: October 30th, 2026 12:00am GMT", "2026-10-30T00:00:00+00:00"),
        ("Application deadline: 30 October 2026 12:00pm CET", "2026-10-30T11:00:00+00:00"),
        ("Application deadline: 2026-10-30 01:00 +08:00", "2026-10-29T17:00:00+00:00"),
        ("Application deadline: 2026-10-30 23:00 -04:00", "2026-10-31T03:00:00+00:00"),
    ],
)
def test_explicit_deadlines(text, expected):
    result = extract_deadline(text)
    assert result.precision == "instant"
    assert result.instant.isoformat() == expected
    assert result.evidence


@pytest.mark.parametrize(
    "text",
    [
        "The application deadline will be 31 October 2026.",
        "Application deadline: 1st December 2026",
        "Application deadline: 30 October 2026 23:59",
        "Application deadline: 30 October 2026 23:59 CST",
        "Application deadline: 30 October 2026 23:59 UTC+08:00",
    ],
)
def test_date_only_never_invents_time_or_timezone(text):
    result = extract_deadline(text)
    assert result.precision == "date" and result.day and result.instant is None


@pytest.mark.parametrize(
    "text",
    [
        "We encourage you to apply by September 30th.",
        "Applications closes 30 October, 23:59 HKT.",
        "Application Deadline: 1st deadline: July 22 2nd deadline: August 13",
        "Application deadline: Monday 1st December.",
        "Start date: 1 December 2026. Publication date: 1 October 2026.",
        "Application deadline: 01/02/2027",
        "Previous application deadline: 2026-10-30 23:00 UTC",
        "No application deadline: 2026-10-30 23:00 UTC",
        "Closing date if we receive a high volume of applications.",
    ],
)
def test_ambiguous_or_unrelated_text_stays_unknown(text):
    assert extract_deadline(text).precision == "unknown"


@pytest.mark.parametrize(
    "text",
    [
        "Application deadline: 30 February 2026 23:00 UTC",
        "Application deadline: Monday 30 October 2026 23:00 UTC",
        "Application deadline: 2026-10-30 25:00 UTC",
        "Application deadline: 2026-10-30 00:30pm UTC",
        "Application deadline: 2026-10-30 23:00 +15:00",
        "Application deadline: 2026-10-30 23:00 +14:30",
        "Application deadline: 2026-10-30 23:00 +01:99",
        "Application deadline: 2026-10-30 23:00 UTC. Applications close 2026-11-01 23:00 UTC.",
        "Application deadline: 2026-10-30 23:00 UTC. Applications close 2026-10-30 22:00 UTC.",
        "Application deadline: 2026-10-30 or 2026-11-01",
        "Applications close at 17:00 CEST on 20 September 2026 (UTC)",
    ],
)
def test_contradictions_are_not_remindable(text):
    assert extract_deadline(text).precision == "conflict"


def test_structured_agreement_and_conflicts(job):
    job.description_text = "Application deadline: 2026-10-30 23:00 UTC"
    job.application_deadline = datetime(2026, 10, 30, 23, tzinfo=UTC)
    assert resolve_deadline(job).precision == "instant"
    job.application_deadline += timedelta(hours=1)
    assert resolve_deadline(job).precision == "conflict"
    job.description_text = "Application deadline: 2026-10-29"
    assert resolve_deadline(job).precision == "conflict"
    job.application_deadline = datetime(2026, 10, 29)
    assert resolve_deadline(job).precision == "conflict"


@pytest.mark.parametrize("value", [None, "2026-10-30", "2026-10-30T23:00:00", "tomorrow", 123])
def test_unzoned_structured_deadlines_are_not_instants(value):
    assert aware_instant(value) is None


def test_normalizer_and_vendor_do_not_invent_timezone(raw):
    raw.application_deadline = datetime(2020, 1, 1)
    job = normalize(raw)
    assert job.application_deadline is None and not job.is_expired
    row = {
        "title": "Trader",
        "company": "Bank",
        "apply_url": "https://example.com/job",
        "application_deadline": "2026-10-30",
    }
    assert map_row(row, "test", True).application_deadline is None
    row["application_deadline"] = "2026-10-30T23:00:00+08:00"
    assert map_row(row, "test", True).application_deadline == datetime(2026, 10, 30, 15, tzinfo=UTC)


@pytest.fixture
def timely(job, repo, monkeypatch):
    job.application_deadline = NOW + timedelta(days=7)
    job.last_seen = NOW
    with repo.transaction():
        repo.upsert(job)
    monkeypatch.setattr("trading_radar.reminders.utcnow", lambda: NOW)
    monkeypatch.setattr("trading_radar.scanner.utcnow", lambda: NOW)
    return job


@pytest.mark.parametrize(
    "seconds,stage",
    [
        (7 * 86400 + 1, None),
        (7 * 86400, 7),
        (3 * 86400 + 1, 7),
        (3 * 86400, 3),
        (86401, 3),
        (86400, 1),
        (1, 1),
        (0, None),
        (-1, None),
    ],
)
def test_reminder_window_boundaries(timely, seconds, stage):
    timely.application_deadline = NOW + timedelta(seconds=seconds)
    plan = deadline_plan(timely, Application(job_id=timely.id), now=NOW)
    assert plan["stage_days"] == stage
    assert plan["eligible"] == (stage is not None)


@pytest.mark.parametrize("status", list(ApplicationStatus))
def test_application_status_controls_reminder(timely, status):
    plan = deadline_plan(timely, Application(job_id=timely.id, status=status), now=NOW)
    assert plan["eligible"] == (status.value in {"New", "Reviewing", "To Apply"})


def test_application_date_blocks_even_if_status_was_reset(timely):
    assert not deadline_plan(
        timely, Application(job_id=timely.id, application_date="2026-09-16"), now=NOW
    )["eligible"]


@pytest.mark.parametrize("age,eligible", [(24, True), (24.001, False), (-1, False)])
def test_freshness_boundary(timely, age, eligible):
    timely.last_seen = NOW - timedelta(hours=age)
    assert deadline_plan(timely, Application(job_id=timely.id), now=NOW)["eligible"] == eligible


class FakeNotifier:
    def __init__(self, error=None):
        self.error, self.sent = error, []

    async def send(self, job, event):
        if self.error:
            raise self.error
        self.sent.append((job, event))


def test_queue_idempotence_and_delivery(timely, repo):
    assert queue_reminders(repo, 70) == 1
    assert queue_reminders(repo, 70) == 0
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70, reminders_enabled=True)) == 1
    assert notifier.sent[0][1] == "deadline_j7"
    assert "APPLICATION DEADLINE" in format_message(*notifier.sent[0])
    assert queue_reminders(repo, 70) == 0
    assert reminder_plans(repo)[0]["reason"] == "delivery_sent"


@pytest.mark.parametrize(
    "change", ["applied", "date", "closed", "stale", "score", "removed", "changed", "window"]
)
def test_revalidate_pending_before_delivery(timely, repo, change):
    queue_reminders(repo, 70)
    if change == "applied":
        repo.update_application(timely.id, {"status": "Applied"})
    elif change == "date":
        repo.update_application(timely.id, {"application_date": "2026-09-16"})
    else:
        if change == "closed":
            timely.is_active = False
        elif change == "stale":
            timely.last_seen = NOW - timedelta(days=2)
        elif change == "score":
            timely.score_breakdown.exclusions = ["test"]
        elif change == "removed":
            timely.application_deadline = None
        elif change == "changed":
            timely.application_deadline += timedelta(hours=1)
        elif change == "window":
            timely.application_deadline = NOW + timedelta(days=1)
        with repo.transaction():
            repo._write(timely)
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70, reminders_enabled=True)) == 0
    assert not notifier.sent
    assert repo.db.execute("SELECT status FROM alerts").fetchone()[0] == "suppressed"


@pytest.mark.parametrize(
    "error,status", [(DeliveryUnknown(), "unknown"), (RuntimeError(), "pending")]
)
def test_uncertain_delivery_is_not_retried(timely, repo, error, status):
    queue_reminders(repo, 70)
    notifier = FakeNotifier(error)
    asyncio.run(deliver(repo, notifier, 70, reminders_enabled=True))
    assert repo.db.execute("SELECT status FROM alerts").fetchone()[0] == status
    notifier.error = None
    asyncio.run(deliver(repo, notifier, 70, reminders_enabled=True))
    assert len(notifier.sent) == (1 if status == "pending" else 0)


def test_disabled_reminders_do_not_deliver_existing_queue(timely, repo):
    queue_reminders(repo, 70)
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70)) == 0
    assert len(repo.pending()) == 1


def test_crash_after_marking_sending_never_replays(timely, repo):
    queue_reminders(repo, 70)
    repo.set_alert(repo.pending()[0]["id"], "sending")
    assert queue_reminders(repo, 70) == 0
    assert reminder_plans(repo)[0]["reason"] == "delivery_sending"


def test_new_deadline_has_new_identity(timely, repo):
    queue_reminders(repo, 70)
    old = repo.pending()[0]["event_key"]
    timely.application_deadline -= timedelta(hours=1)
    with repo.transaction():
        repo._write(timely)
    assert queue_reminders(repo, 70) == 1
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70, reminders_enabled=True)) == 1
    assert repo.alert_status(old) == "suppressed"


def test_extracted_deadline_sent_without_modifying_job(timely, repo):
    timely.application_deadline = None
    timely.description_text = "Application deadline: 2026-09-20 17:00 UTC"
    with repo.transaction():
        repo._write(timely)
    queue_reminders(repo, 70)
    notifier = FakeNotifier()
    asyncio.run(deliver(repo, notifier, 70, reminders_enabled=True))
    assert notifier.sent[0][0].application_deadline == datetime(2026, 9, 20, 17, tzinfo=UTC)
    assert repo.get(timely.id).application_deadline is None


@pytest.mark.parametrize(
    "alerts,reminders", [(False, False), (False, True), (True, False), (True, True)]
)
def test_scanner_gates_and_silent_bootstrap(config, repo, raw, monkeypatch, alerts, reminders):
    config.settings.alerts_enabled = alerts
    config.settings.deadline_reminders_enabled = reminders
    raw.application_deadline = datetime.now(UTC) + timedelta(days=2)

    class Collector:
        async def collect(self):
            return Collection(jobs=[raw])

    notifier = FakeNotifier()

    async def run():
        return await scan(config, repo, collectors={"test": Collector()}, notifier=notifier)

    asyncio.run(run())
    assert not notifier.sent and not repo.pending()
    asyncio.run(run())
    assert len(notifier.sent) == (1 if alerts and reminders else 0)
    asyncio.run(run())
    assert len(notifier.sent) == (1 if alerts and reminders else 0)


def test_cli_previews_are_offline_and_do_not_queue(tmp_path, monkeypatch, job):
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/jobs.db")
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setattr("trading_radar.deadline_cli.utcnow", lambda: NOW)
    monkeypatch.setattr("trading_radar.reminders.utcnow", lambda: NOW)
    repo = Repository("sqlite:///data/jobs.db")
    job.last_seen = NOW
    job.application_deadline = NOW + timedelta(days=2)
    with repo.transaction():
        repo.upsert(job)
    before = list(repo.db.iterdump())
    runner = CliRunner()
    listed = runner.invoke(app, ["deadlines", "list", "--days", "7"])
    assert listed.exit_code == 0, listed.output
    assert json.loads(listed.output)["returned"] == 1
    preview = runner.invoke(app, ["deadlines", "reminders"])
    assert preview.exit_code == 0 and json.loads(preview.output)["eligible"] == 1
    assert list(repo.db.iterdump()) == before
    job.score_breakdown.exclusions = ["not relevant"]
    with repo.transaction():
        repo._write(job)
    result = json.loads(runner.invoke(app, ["deadlines", "list", "--min-score", "0"]).output)
    assert result["returned"] == 1
    assert result["deadlines"][0]["reason"] == "below_score_threshold"
    job.application_deadline = NOW - timedelta(hours=1)
    with repo.transaction():
        repo._write(job)
    assert json.loads(runner.invoke(app, ["deadlines", "list"]).output)["returned"] == 0
    assert (
        json.loads(runner.invoke(app, ["deadlines", "list", "--include-expired"]).output)[
            "returned"
        ]
        == 1
    )
    assert (
        json.loads(runner.invoke(app, ["deadlines", "list", "--demo"]).output)["stored_jobs"] == 0
    )
    repo.close()
