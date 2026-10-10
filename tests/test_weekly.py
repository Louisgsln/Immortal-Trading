from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from trading_radar.weekly import weekly_report

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)


def posting(**updates):
    return {
        "company": "Trading Firm",
        "source": "firm",
        "score": 85,
        "first_seen": (NOW - timedelta(days=2)).isoformat(),
        "last_seen": NOW.isoformat(),
        "is_active": True,
        "is_expired": False,
        "score_breakdown": {"exclusions": []},
        "application": {"status": "New"},
        "deadline": {"precision": "unknown"},
        **updates,
    }


HEALTH = {"sources": [{"source": "firm", "status": "fresh"}]}


def test_funnel_distinguishes_high_score_from_ready_and_preserves_input():
    jobs = [
        posting(),
        posting(score=60),
        posting(score=0, score_breakdown={"exclusions": ["senior"]}),
        posting(internship_alert={"status": "blocked"}),
        posting(source="stale"),
        posting(application={"status": "Applied"}),
    ]
    before = deepcopy(jobs)
    report = weekly_report(jobs, HEALTH, 70, NOW)
    assert (report["discovered"], report["score70"], report["ready"]) == (6, 4, 1)
    assert report["blocked"] == {
        "score_below_threshold": 1,
        "excluded": 1,
        "internship_conditions": 1,
        "source_not_fresh": 1,
        "tracking_or_verification": 1,
    }
    assert report["ready"] + sum(report["blocked"].values()) == report["discovered"]
    assert report["companies"] == [
        {"company": "Trading Firm", "discovered": 6, "score70": 4, "ready": 1}
    ]
    assert jobs == before


def test_window_includes_boundary_excludes_old_future_and_invalid():
    jobs = [
        posting(first_seen=(NOW - timedelta(days=7)).isoformat()),
        posting(first_seen=(NOW - timedelta(days=7, seconds=1)).isoformat()),
        posting(first_seen=(NOW + timedelta(seconds=1)).isoformat()),
        posting(first_seen="bad"),
    ]
    assert weekly_report(jobs, HEALTH, 70, NOW)["discovered"] == 1


def test_unknown_health_and_stale_job_do_not_claim_ready():
    assert weekly_report([posting()], {}, 70, NOW)["blocked"] == {"source_not_fresh": 1}
    assert (
        weekly_report(
            [posting(last_seen=(NOW - timedelta(hours=25)).isoformat())], HEALTH, 70, NOW
        )["ready"]
        == 0
    )


def test_expiration_inactivity_and_stage_eligible():
    report = weekly_report(
        [
            posting(is_expired=True),
            posting(is_active=False),
            posting(internship_alert={"status": "eligible"}),
        ],
        HEALTH,
        70,
        NOW,
    )
    assert report["blocked"] == {"expired": 1, "inactive": 1}
    assert report["ready"] == 1


def test_naive_time_refused():
    with pytest.raises(ValueError):
        weekly_report([], HEALTH, 70, NOW.replace(tzinfo=None))
