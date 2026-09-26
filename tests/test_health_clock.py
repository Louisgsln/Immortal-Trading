"""Commit during observation must not look like a corrupt future timestamp."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from trading_radar import dashboard_data, health, monitoring

START = datetime(2026, 9, 26, 10, tzinfo=UTC)
AFTER = START + timedelta(seconds=5)


@pytest.fixture
def live_config(config, repo):
    path = repo.db.execute("PRAGMA database_list").fetchone()[2]
    config.settings.database_url = f"sqlite:///{path}"
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO companies(source,last_success,bootstrapped) VALUES('test',?,1)",
            ((START - timedelta(hours=1)).isoformat(),),
        )
    return config


def commit(repo, event, at):
    with repo.transaction():
        if event == "scan":
            repo.db.execute(
                "INSERT INTO scan_runs(created_at,metrics) VALUES(?, '{}')", (at.isoformat(),)
            )
        else:
            column = "last_success" if event == "success" else "last_failure"
            repo.db.execute(f"UPDATE companies SET {column}=?", (at.isoformat(),))


def writer_before_snapshot(monkeypatch, repo, event):
    clock = [START]
    original = sqlite3.connect
    committed = []

    def connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        if kwargs.get("uri") and not committed:
            commit(repo, event, AFTER)
            committed.append(True)
            clock[0] = AFTER
        return connection

    monkeypatch.setattr(health, "utcnow", lambda: clock[0])
    monkeypatch.setattr(health.sqlite3, "connect", connect)
    return committed


@pytest.mark.parametrize("event", ["success", "failure", "scan"])
@pytest.mark.parametrize("explicit", [False, True])
def test_commit_before_health_snapshot_uses_live_clock_but_preserves_explicit_time(
    live_config, repo, monkeypatch, event, explicit
):
    committed = writer_before_snapshot(monkeypatch, repo, event)
    result = health.check_health(live_config, now=START if explicit else None)
    assert committed == [True]
    expected_time = START if explicit else AFTER
    assert result["generated_at"] == expected_time.isoformat()
    codes = {i["code"] for i in result["issues"]}
    invalid = "scan_invalid_timestamp" if event == "scan" else "source_invalid_timestamp"
    assert (invalid in codes) is explicit
    if not explicit:
        assert result["source_summary"] == {"recent_failure" if event == "failure" else "fresh": 1}


@pytest.mark.parametrize("event", ["success", "failure", "scan"])
def test_real_future_times_are_still_rejected(live_config, repo, monkeypatch, event):
    commit(repo, event, AFTER + timedelta(hours=1))
    monkeypatch.setattr(health, "utcnow", lambda: AFTER)
    before = list(repo.db.iterdump())
    result = health.check_health(live_config)
    expected = "scan_invalid_timestamp" if event == "scan" else "source_invalid_timestamp"
    assert expected in {i["code"] for i in result["issues"]}
    assert list(repo.db.iterdump()) == before


def test_late_commit_does_not_change_the_pinned_health_snapshot(live_config, repo, monkeypatch):
    original = sqlite3.connect
    changed = []
    clock = [START]

    def connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        if kwargs.get("uri"):

            def on_query(sql):
                if sql.startswith("SELECT source,last_success"):
                    commit(repo, "failure", AFTER)
                    clock[0] = AFTER
                    changed.append(True)

            connection.set_trace_callback(on_query)
        return connection

    monkeypatch.setattr(health.sqlite3, "connect", connect)
    monkeypatch.setattr(health, "utcnow", lambda: clock[0])
    result = health.check_health(live_config)
    assert changed == [True]
    assert result["sources"][0]["last_failure"] is None
    assert result["source_summary"] == {"fresh": 1}
    assert result["generated_at"] == AFTER.isoformat()


@pytest.mark.parametrize("event", ["success", "failure"])
@pytest.mark.parametrize("explicit", [False, True])
def test_dashboard_handles_commit_during_jobs_read(
    live_config, repo, tmp_path, monkeypatch, event, explicit
):
    clock = [START]
    read = dashboard_data.read_jobs

    def read_with_commit(config):
        jobs = read(config)
        commit(repo, event, AFTER)
        clock[0] = AFTER
        return jobs

    monkeypatch.setattr(dashboard_data, "read_jobs", read_with_commit)
    monkeypatch.setattr(dashboard_data, "utcnow", lambda: clock[0])
    monkeypatch.setattr(health, "utcnow", lambda: clock[0])
    result = dashboard_data.build_dashboard_data(
        live_config, tmp_path / "history", now=START if explicit else None
    )
    expected = (
        "invalid_timestamp" if explicit else "recent_failure" if event == "failure" else "fresh"
    )
    assert result["health"]["source_summary"] == {expected: 1}
    assert result["summary"]["fresh_sources"] == (expected == "fresh")
    assert result["generated_at"] == START.isoformat()
    assert not (tmp_path / "history").exists()


def test_archive_uses_health_observation_time_and_roundtrips(
    live_config, repo, tmp_path, monkeypatch
):
    writer_before_snapshot(monkeypatch, repo, "success")
    # A live archive must not turn its own start time into an explicit health cutoff.
    envelope = monitoring.record_health(live_config, tmp_path / "history")
    assert envelope["report"]["source_summary"] == {"fresh": 1}
    assert envelope["recorded_at"] == envelope["report"]["generated_at"] == AFTER.isoformat()
    assert monitoring.read_snapshot(tmp_path / "history", envelope["id"]) == envelope
