"""Associate targeting must override attractive trading keywords, not Analyst alternatives."""

import asyncio
from datetime import timedelta

import pytest

from trading_radar.applications import Application
from trading_radar.models import Collection, Score, utcnow
from trading_radar.normalizer import normalize
from trading_radar.reminders import deadline_plan
from trading_radar.scanner import deliver, scan
from trading_radar.scoring import ASSOCIATE_EXCLUSION, score_job


@pytest.mark.parametrize(
    "title",
    [
        "Associate, Securities Lending Trader",
        "Associate Trader",
        "Trading Associates",
        "CMBS trader - Associate",
        "New Associate - Trading 2027",
        "Graduate Associate Trader",
        "Associate Trading Analyst",
        "Associate, Trading Analyst",
        "Trading Associate Director",
    ],
)
@pytest.mark.parametrize("hint", [None, "junior"])
def test_associate_is_excluded_even_with_junior_signals(raw, config, title, hint):
    raw.title = title
    raw.seniority_hint = hint
    raw.minimum_experience_years = 0
    raw.description = "Junior analyst opportunities on a trading desk. FX Python SQL pricing 2027."
    job = score_job(normalize(raw), config.keywords)
    assert ASSOCIATE_EXCLUSION in job.score_breakdown.exclusions
    assert job.score_breakdown.total == job.score_breakdown.junior == 0
    assert job.minimum_experience_years == 0  # No experience invented from a grade.


@pytest.mark.parametrize(
    "title",
    [
        "Trading Analyst/Associate",
        "Trading Analyst / Associate",
        "Trading Associate/Analyst",
        "Trading Analyst or Associate",
        "Trading Associate OR Analyst",
        "Trading Analyst & Associate",
        "Trading Analyst &amp; Associate",
        "Trading Analyst and Associate",
        "Trading Analyst | Associate",
        "Trading Analyst",
        "Junior Trader",
    ],
)
def test_explicit_analyst_alternatives_are_retained(raw, config, title):
    raw.title = title
    raw.description = "Front office trading desk. FX Python SQL pricing."
    job = score_job(normalize(raw), config.keywords)
    assert ASSOCIATE_EXCLUSION not in job.score_breakdown.exclusions
    assert job.score_breakdown.junior == 20
    assert job.score_breakdown.total >= 70


@pytest.mark.parametrize("change", ["senior", "experience", "internship"])
def test_mixed_grade_does_not_bypass_other_exclusions(raw, config, change):
    raw.title = "Trading Analyst/Associate"
    if change == "senior":
        raw.title += " / Vice President"
    elif change == "experience":
        raw.minimum_experience_years = 5
    else:
        raw.employment_type = "Internship"
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0


def test_body_and_word_fragments_do_not_exclude_analyst(raw, config):
    raw.title = "Trading Analyst"
    raw.description = "Work alongside Associate traders and the trading association."
    assert (
        ASSOCIATE_EXCLUSION
        not in score_job(normalize(raw), config.keywords).score_breakdown.exclusions
    )


@pytest.mark.parametrize("threshold", [0, 70])
def test_rescore_preserves_followup_and_suppresses_old_pending_alert(repo, raw, config, threshold):
    raw.title = "Associate, Securities Lending Trader"
    job = normalize(raw)
    job.score_breakdown = Score(
        trading=30, junior=8, start=7, front_office=15, asset=10, profile_fit=10
    )
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
    repo.update_application(job.id, {"status": "Applied", "notes": "Keep my application"})
    before = repo.get(job.id)
    application = repo.application(job.id)
    alert_id = repo.pending()[0]["id"]
    updated = score_job(before.model_copy(deep=True), config.keywords)
    with repo.transaction():
        assert repo.update_scoring(updated)
        assert not repo.update_scoring(score_job(repo.get(job.id), config.keywords))
    assert repo.application(job.id) == application
    for field in ("first_seen", "last_seen", "date_updated", "is_active"):
        assert getattr(repo.get(job.id), field) == getattr(before, field)

    class NoDelivery:
        async def send(self, *_):
            raise AssertionError("An excluded Associate must not be sent")

    assert asyncio.run(deliver(repo, NoDelivery(), threshold)) == 0
    assert repo.get_alert(alert_id)["status"] == "suppressed"


def test_excluded_grade_cannot_receive_a_deadline_reminder_at_zero_threshold(raw, config):
    raw.title = "Associate Trader"
    raw.application_deadline = utcnow() + timedelta(hours=12)
    job = score_job(normalize(raw), config.keywords)
    assert not deadline_plan(job, Application(job_id=job.id), min_score=0)["eligible"]


@pytest.mark.parametrize(
    "title,expected", [("Associate Trader", 0), ("Trading Analyst/Associate", 1)]
)
def test_new_scan_does_not_queue_excluded_grade_even_at_zero_threshold(
    repo, raw, config, title, expected
):
    class Collector:
        jobs = [raw]

        async def collect(self):
            return Collection(jobs=self.jobs, complete=True)

    class Notifier:
        sent = 0

        async def send(self, *_):
            self.sent += 1

    collector, notifier = Collector(), Notifier()
    config.settings.alert_min_score = 0
    asyncio.run(scan(config, repo, collectors={"test": collector}, notifier=notifier))
    collector.jobs = [
        raw,
        raw.model_copy(
            update={
                "title": title,
                "external_id": "new-grade",
                "apply_url": "https://example.com/new-grade",
            }
        ),
    ]
    result = asyncio.run(scan(config, repo, collectors={"test": collector}, notifier=notifier))
    assert result.new == 1
    assert result.alerts == notifier.sent == expected
    assert repo.db.execute("SELECT count(*) FROM alerts").fetchone()[0] == expected
