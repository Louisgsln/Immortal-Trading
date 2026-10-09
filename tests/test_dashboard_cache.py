"""Description reuse must preserve fresh database reads and their validation."""

from datetime import timedelta

import pytest

from trading_radar import dashboard_data as dashboard


@pytest.fixture
def cached_jobs(config, repo, job, monkeypatch):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    dashboard._employer_details.cache_clear()
    calls = []
    original = dashboard.conditions

    def observe(current):
        calls.append(current.minimum_experience_years)
        return original(current)

    monkeypatch.setattr(dashboard, "conditions", observe)
    job.minimum_experience_years = 0
    with repo.transaction():
        repo.upsert(job)
    yield config, calls
    dashboard._employer_details.cache_clear()


def test_reuses_description_but_reads_current_dates_scores_and_application(cached_jobs, repo):
    config, calls = cached_jobs
    first = dashboard.read_jobs(config)[0]
    current = repo.get(first["id"])
    current.last_seen += timedelta(hours=1)
    current.date_updated = current.last_seen
    current.score_breakdown.reasons.append("New scoring observation")
    with repo.transaction():
        repo.db.execute(
            "UPDATE jobs SET payload=?,last_seen=? WHERE id=?",
            (current.model_dump_json(), current.last_seen.isoformat(), current.id),
        )
    repo.update_application(current.id, {"notes": "Fresh manual update"})
    second = dashboard.read_jobs(config)[0]
    assert calls == [0]
    assert second["last_seen"] == current.last_seen.isoformat()
    assert second["score_breakdown"]["reasons"][-1] == "New scoring observation"
    assert second["application"]["notes"] == "Fresh manual update"
    first["deadline"]["precision"] = "conflict"
    first["conditions"]["experience"]["minimum_years"] = 99
    third = dashboard.read_jobs(config)[0]
    assert third["deadline"]["precision"] != "conflict"
    assert third["experience"]["minimum_years"] == 0


def test_employer_statement_changes_invalidate_description_cache(cached_jobs, repo):
    config, calls = cached_jobs
    first = dashboard.read_jobs(config)[0]
    current = repo.get(first["id"])
    current.minimum_experience_years = 4
    current.expected_start_date = "January 2027"
    with repo.transaction():
        repo.db.execute(
            "UPDATE jobs SET payload=? WHERE id=?", (current.model_dump_json(), current.id)
        )
    second = dashboard.read_jobs(config)[0]
    assert calls == [0, 4]
    assert second["experience"]["minimum_years"] == 4
    assert second["conditions"]["start"]["year"] == 2027
    assert second["conditions"]["start"]["months"] == [1]


def test_cached_description_never_skips_current_row_integrity(cached_jobs, repo):
    config, _ = cached_jobs
    first = dashboard.read_jobs(config)[0]
    with repo.transaction():
        repo.db.execute("UPDATE jobs SET score=score+1 WHERE id=?", (first["id"],))
    with pytest.raises(dashboard.DashboardDataError, match="incohérentes"):
        dashboard.read_jobs(config)
