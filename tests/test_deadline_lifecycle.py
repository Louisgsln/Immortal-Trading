from datetime import UTC, datetime, timedelta

import pytest

from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.deadlines import deadline_status, extract_deadline

NOW = datetime(2026, 10, 5, 22, 0, tzinfo=UTC)  # Midnight in Paris.


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Application deadline: 2026-10-05.", "expired"),
        ("Application deadline: 2026-10-06.", "upcoming"),
        ("Application deadline: 2026-10-05 22:00 UTC.", "expired"),
        ("Application deadline: 2026-10-05 22:01 UTC.", "upcoming"),
        ("Application deadline: 2026-02-30.", "conflict"),
        ("Publication date: 2026-10-01.", "unknown"),
    ],
)
def test_shared_deadline_state_and_paris_day_boundary(text, expected):
    assert deadline_status(extract_deadline(text), NOW) == expected


def test_naive_observation_is_rejected():
    with pytest.raises(ValueError):
        deadline_status(extract_deadline(""), NOW.replace(tzinfo=None))


def test_dashboard_uses_observation_time_without_closing_or_mutating_job(
    config, repo, job, tmp_path
):
    config.settings.database_url = "sqlite:///" + str(tmp_path / "jobs.db")
    job.description_text = "Application deadline: 2026-10-05."
    with repo.transaction():
        repo.upsert(job)
    before = list(repo.db.iterdump())
    previous = build_dashboard_data(config, tmp_path / "history", now=NOW - timedelta(minutes=1))
    current = build_dashboard_data(config, tmp_path / "history", now=NOW)
    assert previous["summary"]["high_priority"] == 1
    assert current["summary"]["high_priority"] == 0
    assert current["summary"]["active"] == 1
    assert current["jobs"][0]["is_expired"]
    assert current["jobs"][0]["deadline"]["status"] == "expired"
    assert repo.get(job.id).is_active and not repo.get(job.id).is_expired
    assert list(repo.db.iterdump()) == before


def test_stats_exclude_inactive_and_textually_expired_priorities(repo, job, monkeypatch):
    monkeypatch.setattr("trading_radar.storage.utcnow", lambda: NOW)
    job.description_text = "Application deadline: 2026-10-05."
    with repo.transaction():
        repo.upsert(job)
    assert repo.stats()["high_priority"] == 0
    job.description_text = "Application deadline: 2026-10-06."
    with repo.transaction():
        repo.upsert(job)
    assert repo.stats()["high_priority"] == 1
    with repo.transaction():
        repo.reconcile(job.source, set(), 1)
    assert repo.stats()["high_priority"] == 0


def test_empty_stats_are_zero(repo):
    assert {key: repo.stats()[key] for key in ("total", "active", "high_priority")} == {
        "total": 0,
        "active": 0,
        "high_priority": 0,
    }
