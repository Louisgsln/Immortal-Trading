"""Candidate calendar and employer conditions: evidence, conflicts, and useful alerts."""

import asyncio

import pytest
from test_scanner import FakeNotifier, MemoryCollector, run

from trading_radar.job_conditions import (
    authorization_evidence,
    conditions,
    deadline_label,
    material_changes,
    start_label,
)
from trading_radar.normalizer import normalize
from trading_radar.notifications import DeliveryUnknown
from trading_radar.scanner import deliver
from trading_radar.scoring import score_job
from trading_radar.start_dates import start_period
from trading_radar.telegram_cards import format_alert


@pytest.mark.parametrize(
    "start,months,points",
    [
        ("January 2027", [1], 15),
        ("October 2027", [10], 8),
        ("2027-10-01", [10], 8),
        ("1 février 2027", [2], 15),
        ("Q1 2027", [1, 2, 3], 15),
        ("Q4 2027", [10, 11, 12], 8),
        ("January to August 2027", list(range(1, 9)), 11),
    ],
)
def test_explicit_start_window_changes_priority_without_inventing_a_day(
    raw, config, start, months, points
):
    raw.expected_start_date = start
    job = score_job(normalize(raw), config.keywords)
    observed = start_period(job)
    assert observed["months"] == months and observed["precision"] == "months"
    assert job.score_breakdown.start == points
    assert job.expected_start_date == start


@pytest.mark.parametrize(
    "description",
    [
        "Start October 2027. FX trading desk.",
        "The successful applicant starts in October 2027.",
        "Prise de poste : octobre 2027.",
        "Début de mission : octobre 2027.",
    ],
)
def test_start_in_description_is_recognized(raw, config, description):
    raw.description = description
    assert score_job(normalize(raw), config.keywords).score_breakdown.start == 8


@pytest.mark.parametrize(
    "description",
    [
        "Début de mission : janvier 2027.",
        "Prise de poste : juin 2027.",
        "The successful applicant starts in March 2027.",
    ],
)
def test_preferred_description_start_scores_without_a_year_in_the_title(raw, config, description):
    raw.title = "Graduate FX Trader"
    raw.expected_start_date = None
    raw.description = description
    job = score_job(normalize(raw), config.keywords)
    assert start_period(job)["target_window"] == "preferred"
    assert job.score_breakdown.start == 15


@pytest.mark.parametrize(
    "description",
    [
        "Application deadline: October 2027.",
        "Graduation expected in October 2027.",
        "Copyright October 2027.",
        "<p hidden>Start October 2027.</p>",
        "<script>Start October 2027.</script>",
        "Previous start October 2027.",
        "Start applying by the application deadline in October 2027.",
    ],
)
def test_other_dates_and_hidden_text_do_not_become_candidate_start(raw, description):
    raw.title = "Graduate FX Trader"
    raw.description = description
    assert start_period(normalize(raw))["precision"] == "unknown"


@pytest.mark.parametrize(
    "start,description",
    [
        ("January 2027", "Start October 2026."),
        ("January 2027", "Start October 2027."),
        ("2027-13-01", ""),
        ("November to January 2027", ""),
    ],
)
def test_conflicting_or_invalid_start_periods_remain_uncertain(raw, config, start, description):
    raw.expected_start_date, raw.description = start, description
    job = score_job(normalize(raw), config.keywords)
    assert start_period(job)["precision"] == "conflict"
    assert job.score_breakdown.start == 7


def test_unrelated_following_dates_do_not_contaminate_valid_start(raw):
    raw.description = "Start January 2027. Copyright 2026. Application deadline: October 2026."
    assert start_period(normalize(raw))["months"] == [1]
    assert start_period(normalize(raw))["year"] == 2027


def test_authorization_preserves_negation_and_ignores_hidden_and_company_sponsorship(raw):
    raw.description = (
        "<p>Visa sponsorship is not available for this role.</p>"
        "<p>Applicants must be authorized to work in the United States.</p>"
        "<p hidden>Visa sponsorship available.</p>"
        "<p>Our firm sponsors a local charity.</p>"
    )
    evidence = authorization_evidence(normalize(raw))
    assert evidence == [
        "Visa sponsorship is not available for this role.",
        "Applicants must be authorized to work in the United States.",
    ]


@pytest.mark.parametrize(
    "changes,label",
    [
        ({"expected_start_date": "October 2027"}, "Date de début"),
        (
            {"description": "Applicants must be authorized to work in the US. FX trading desk."},
            "Visa / droit au travail",
        ),
        ({"minimum_experience_years": 2}, "Expérience requise"),
        ({"employment_type": "Permanent"}, "Contrat"),
        (
            {"description": "Application deadline: 2027-01-01 at 12:00 UTC. FX trading desk."},
            "Échéance",
        ),
    ],
)
def test_condition_changes_alert_once_then_remain_silent(config, repo, raw, changes, label):
    notifier = FakeNotifier()
    collector = MemoryCollector([raw])
    run(config, repo, {"test": collector}, notifier)
    collector.jobs = [raw.model_copy(update=changes)]
    changed = run(config, repo, {"test": collector}, notifier)
    assert changed.alerts == 1 and notifier.sent[-1][1] == "updated"
    run(config, repo, {"test": collector}, notifier)
    assert len(notifier.sent) == 1
    assert repo.db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1


def test_raw_reformatting_does_not_alert(raw, config):
    raw.expected_start_date = "2027-01-01"
    old = score_job(normalize(raw), config.keywords)
    raw.expected_start_date = "1 January 2027"
    new = score_job(normalize(raw), config.keywords)
    assert material_changes(old, new) == []


def test_content_change_crossing_threshold_alerts_but_recalculation_does_not(config, repo, raw):
    config.settings.alert_min_score = 90
    raw.title = "Graduate FX Trader"
    raw.expected_start_date = "October 2027"
    raw.description = "FX trading desk."
    collector = MemoryCollector([raw])
    notifier = FakeNotifier()
    run(config, repo, {"test": collector}, notifier)
    raw.description += " Python, SQL, pricing, quantitative, derivatives."
    run(config, repo, {"test": collector}, notifier)
    assert notifier.sent == [(repo.list_jobs()[0].id, "updated")]
    run(config, repo, {"test": collector}, notifier)
    assert len(notifier.sent) == 1


def test_expired_textual_deadline_never_sends_new_opportunity(config, repo, raw):
    config.settings.bootstrap_silent = False
    raw.description += " Application deadline: 2020-01-01."
    notifier = FakeNotifier()
    assert run(config, repo, {"test": MemoryCollector([raw])}, notifier).new == 1
    assert not notifier.sent and not repo.pending()


def test_delayed_update_explains_change(config, repo, raw):
    run(config, repo, {"test": MemoryCollector([raw])})
    raw.expected_start_date = "October 2027"
    run(config, repo, {"test": MemoryCollector([raw])})

    class CapturingNotifier:
        sent = []

        async def send(self, job, event):
            self.sent.append(format_alert(job, event))

    notifier = CapturingNotifier()
    asyncio.run(deliver(repo, notifier, 70))
    assert "Date de début" in notifier.sent[0]
    assert "notification_changes" not in repo.list_jobs()[0].model_dump()


def test_pending_updates_coalesce_and_cancelled_change_is_suppressed(config, repo, raw):
    collector = MemoryCollector([raw])
    run(config, repo, {"test": collector})
    raw.expected_start_date = "October 2027"
    run(config, repo, {"test": collector})
    raw.expected_start_date = "November 2027"
    run(config, repo, {"test": collector})
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70)) == 1
    assert len(notifier.sent) == 1
    raw.expected_start_date = "October 2027"
    run(config, repo, {"test": collector})
    raw.expected_start_date = "November 2027"
    run(config, repo, {"test": collector})
    assert asyncio.run(deliver(repo, notifier, 70)) == 0
    assert len(notifier.sent) == 1
    assert not repo.pending()


def test_pending_new_opportunity_absorbs_intermediate_update(config, repo, raw):
    config.settings.bootstrap_silent = False
    collector = MemoryCollector([raw])
    run(config, repo, {"test": collector})
    raw.expected_start_date = "October 2027"
    run(config, repo, {"test": collector})
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70)) == 1
    assert notifier.sent[0][1] == "new" and len(notifier.sent) == 1


def test_retry_of_coalesced_update_preserves_all_undelivered_changes(config, repo, raw):
    collector = MemoryCollector([raw])
    run(config, repo, {"test": collector})
    raw.expected_start_date = "October 2027"
    run(config, repo, {"test": collector})
    raw.description += " Visa sponsorship is not available for this role."
    run(config, repo, {"test": collector})

    class RetryingNotifier:
        failed = False
        cards = []

        async def send(self, job, event):
            if not self.failed:
                self.failed = True
                raise RuntimeError("Known failure before delivery")
            self.cards.append(format_alert(job, event))

    notifier = RetryingNotifier()
    assert asyncio.run(deliver(repo, notifier, 70)) == 0
    assert len(repo.pending()) == 1
    assert asyncio.run(deliver(repo, notifier, 70)) == 1
    assert "Date de début" in notifier.cards[0]
    assert "Visa / droit au travail" in notifier.cards[0]
    assert not repo.pending()


def test_uncertain_coalesced_update_is_never_automatically_resent(config, repo, raw):
    collector = MemoryCollector([raw])
    run(config, repo, {"test": collector})
    for start in ("October 2027", "November 2027"):
        raw.expected_start_date = start
        run(config, repo, {"test": collector})

    class UnknownNotifier:
        calls = 0

        async def send(self, job, event):
            self.calls += 1
            raise DeliveryUnknown()

    notifier = UnknownNotifier()
    assert asyncio.run(deliver(repo, notifier, 70)) == 0
    assert [row[0] for row in repo.db.execute("SELECT status FROM alerts ORDER BY id")] == [
        "unknown",
        "suppressed",
    ]
    assert asyncio.run(deliver(repo, notifier, 70)) == 0
    assert notifier.calls == 1


def test_conditions_observation_preserves_job(raw):
    job = normalize(raw)
    original = job.model_dump_json()
    assert conditions(job)["authorization"]["evidence"] == []
    assert job.model_dump_json() == original


def test_cards_show_recognized_text_dates_without_inventing_a_time(raw):
    raw.title = "Graduate FX Trader"
    raw.description = "Start October 2027. Application deadline: 2027-01-01."
    job = normalize(raw)
    assert start_label(job) == "Start October 2027"
    assert deadline_label(job) == "01/01/2027 · heure non précisée"
    card = format_alert(job, "updated")
    assert "Start October 2027" in card and "01/01/2027" in card
