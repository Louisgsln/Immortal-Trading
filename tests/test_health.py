import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from trading_radar.config import Company
from trading_radar.health import check_health
from trading_radar.health_cli import health

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)


@pytest.fixture
def health_config(config, repo):
    path = repo.db.execute("PRAGMA database_list").fetchone()[2]
    config.settings.database_url = f"sqlite:///{path}"
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO companies(source,last_success,bootstrapped) VALUES('test',?,1)",
            ((NOW - timedelta(hours=1)).isoformat(),),
        )
    return config


def source_state(repo, **changes):
    with repo.transaction():
        for column, value in changes.items():
            repo.db.execute(f"UPDATE companies SET {column}=? WHERE source='test'", (value,))


def codes(report):
    return {issue["code"] for issue in report["issues"]}


def test_empty_but_successfully_scanned_source_is_healthy(health_config):
    report = check_health(health_config, now=NOW)
    assert report["status"] == "healthy" and report["ready"]
    assert report["database"] == {"status": "ok", "schema_version": 4}
    assert report["sources"][0]["last_snapshot_jobs"] == 0
    assert report["source_summary"] == {"fresh": 1}
    assert not report["issues"]


def test_old_jobs_do_not_make_recent_source_stale(health_config, repo, job):
    job.last_seen = NOW - timedelta(days=365)
    with repo.transaction():
        repo.upsert(job)
    assert check_health(health_config, now=NOW)["status"] == "healthy"


def test_absent_database_does_not_create_parent_or_file(config, tmp_path):
    path = tmp_path / "missing" / "jobs.db"
    config.settings.database_url = f"sqlite:///{path}"
    report = check_health(config, now=NOW)
    assert report["status"] == "critical" and not report["ready"]
    assert codes(report) == {"database_missing"}
    assert not path.parent.exists()


@pytest.mark.parametrize("content", [b"not a database", b""])
def test_corrupt_or_empty_database_is_not_initialized(config, tmp_path, content):
    path = tmp_path / "jobs.db"
    path.write_bytes(content)
    config.settings.database_url = f"sqlite:///{path}"
    report = check_health(config, now=NOW)
    assert not report["ready"]
    assert report["database"]["status"] in {"corrupt", "incompatible"}
    assert path.read_bytes() == content


@pytest.mark.parametrize("version", [1, 3, 5, None])
def test_unsupported_schema_never_migrates(health_config, repo, version):
    with repo.transaction():
        repo.db.execute("DELETE FROM schema_version")
        if version is not None:
            repo.db.execute("INSERT INTO schema_version VALUES(?)", (version,))
    report = check_health(health_config, now=NOW)
    assert codes(report) == {"database_schema_incompatible"}
    assert repo.db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == version


def test_missing_table_detected_even_with_current_version(health_config, repo):
    with repo.transaction():
        repo.db.execute("DROP TABLE application_history")
    assert codes(check_health(health_config, now=NOW)) == {"database_schema_incompatible"}
    assert not repo.db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='application_history'"
    ).fetchone()


def test_broken_foreign_key_is_critical(health_config, repo):
    repo.db.execute("PRAGMA foreign_keys=OFF")
    with repo.transaction():
        repo.db.execute("INSERT INTO applications(job_id) VALUES('missing')")
    assert codes(check_health(health_config, now=NOW)) == {"database_foreign_keys_failed"}


def test_uninitialized_source_is_critical(health_config, repo):
    with repo.transaction():
        repo.db.execute("DELETE FROM companies")
    report = check_health(health_config, now=NOW)
    assert codes(report) == {"source_never_scanned"}
    assert not report["ready"]
    assert report["sources"][0]["age_hours"] is None


@pytest.mark.parametrize("age,expected", [(24, "fresh"), (24.0001, "stale"), (48, "stale")])
def test_source_age_boundary(health_config, repo, age, expected):
    source_state(repo, last_success=(NOW - timedelta(hours=age)).isoformat())
    report = check_health(health_config, now=NOW)
    assert report["sources"][0]["status"] == expected
    assert report["ready"] == (expected == "fresh")


def test_freshness_threshold_is_configurable(health_config, repo):
    source_state(repo, last_success=(NOW - timedelta(hours=36)).isoformat())
    assert not check_health(health_config, now=NOW)["ready"]
    assert check_health(health_config, max_age_hours=48, now=NOW)["ready"]


@pytest.mark.parametrize("column", ["last_success", "last_failure"])
@pytest.mark.parametrize("value", ["broken", "2026-09-17", "2027-01-01T00:00:00+00:00"])
def test_invalid_or_future_source_timestamp_is_critical(health_config, repo, column, value):
    source_state(repo, **{column: value})
    report = check_health(health_config, now=NOW)
    assert codes(report) == {"source_invalid_timestamp"}
    assert not report["ready"]


def test_failure_after_recent_success_degrades_then_becomes_critical(health_config, repo):
    source_state(repo, last_failure=NOW.isoformat(), consecutive_failures=1)
    report = check_health(health_config, now=NOW)
    assert report["status"] == "degraded" and report["ready"]
    assert codes(report) == {"source_recent_failure"}
    later = check_health(health_config, now=NOW + timedelta(days=1))
    assert later["status"] == "critical" and not later["ready"]


def test_old_failure_is_recovered(health_config, repo):
    source_state(repo, last_failure=(NOW - timedelta(days=2)).isoformat())
    assert check_health(health_config, now=NOW)["status"] == "healthy"


def test_disabled_and_unconfigured_sources_do_not_break_health(health_config, repo):
    health_config.companies["disabled"] = Company(name="Disabled", ats="fixture", enabled=False)
    with repo.transaction():
        repo.db.execute("INSERT INTO companies(source) VALUES('removed')")
    report = check_health(health_config, now=NOW)
    assert report["status"] == "healthy"
    assert len(report["sources"]) == 1


def test_no_enabled_sources_is_explicitly_degraded(health_config):
    health_config.companies["test"].enabled = False
    report = check_health(health_config, now=NOW)
    assert report["status"] == "degraded" and report["ready"]
    assert codes(report) == {"no_enabled_sources"}


@pytest.mark.parametrize("status", ["pending", "sent", "suppressed", "unknown", "sending"])
def test_alert_state_summary_never_sends_or_changes_data(health_config, repo, job, status):
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
        repo.db.execute("UPDATE alerts SET status=?", (status,))
    before = list(repo.db.iterdump())
    report = check_health(health_config, now=NOW)
    assert list(repo.db.iterdump()) == before
    if status in {"unknown", "sending"}:
        assert report["status"] == "degraded" and report["ready"]
        assert report["alerts"][status] == 1
        assert codes(report) == {"alerts_need_review"}
    else:
        assert report["status"] == "healthy"


def test_wal_committed_source_updates_are_visible(health_config, repo):
    repo.db.execute("PRAGMA wal_autocheckpoint=0")
    source_state(repo, last_success=(NOW - timedelta(days=3)).isoformat())
    path = Path(health_config.settings.database_url.removeprefix("sqlite:///"))
    assert Path(str(path) + "-wal").is_file()
    assert codes(check_health(health_config, now=NOW)) == {"source_stale"}


def test_uncommitted_source_changes_are_not_visible(health_config, repo):
    repo.db.execute("UPDATE companies SET last_success=NULL")
    try:
        assert check_health(health_config, now=NOW)["status"] == "healthy"
    finally:
        repo.db.rollback()


def test_metrics_use_one_snapshot_during_concurrent_commit(health_config, repo, monkeypatch):
    original_connect = sqlite3.connect
    changed = []

    def connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        if kwargs.get("uri"):

            def on_query(sql):
                if sql.startswith("SELECT source,last_success"):
                    source_state(repo, last_success=(NOW - timedelta(days=3)).isoformat())
                    changed.append(True)

            connection.set_trace_callback(on_query)
        return connection

    monkeypatch.setattr("trading_radar.health.sqlite3.connect", connect)
    report = check_health(health_config, now=NOW)
    assert changed == [True]
    assert report["status"] == "healthy"
    monkeypatch.undo()
    assert check_health(health_config, now=NOW)["status"] == "critical"


def test_last_completed_scan_exposed_without_metrics(health_config, repo):
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)", (NOW.isoformat(), "private")
        )
    report = check_health(health_config, now=NOW)
    assert report["latest_scan"] == NOW.isoformat()
    assert "private" not in json.dumps(report)


@pytest.mark.parametrize("value", ["broken", "2027-01-01T00:00:00+00:00"])
def test_invalid_latest_scan_warns(health_config, repo, value):
    with repo.transaction():
        repo.db.execute("INSERT INTO scan_runs(created_at,metrics) VALUES(?, '{}')", (value,))
    assert codes(check_health(health_config, now=NOW)) == {"scan_invalid_timestamp"}


@pytest.mark.parametrize("threshold", [0, -1, float("nan"), float("inf"), 87601])
def test_invalid_threshold_rejected(health_config, threshold):
    with pytest.raises(ValueError, match="max_age_hours"):
        check_health(health_config, threshold)


@pytest.mark.parametrize("url", ["sqlite:///", "sqlite:///:memory:", "postgres://db"])
def test_invalid_database_configuration_rejected(config, url):
    config.settings.database_url = url
    with pytest.raises(ValueError, match="file-backed"):
        check_health(config)


def test_naive_check_time_rejected(health_config):
    with pytest.raises(ValueError, match="timezone"):
        check_health(health_config, now=datetime(2026, 9, 17))


def test_database_read_error_sanitized(health_config, monkeypatch):
    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError("secret-path-and-credentials")

    monkeypatch.setattr("trading_radar.health.sqlite3.connect", unavailable)
    report = check_health(health_config, now=NOW)
    assert codes(report) == {"database_unreadable"}
    assert "secret" not in json.dumps(report)


@pytest.mark.parametrize("state,exit_code", [("healthy", 0), ("degraded", 0), ("critical", 1)])
def test_cli_json_and_exit_status(config, monkeypatch, state, exit_code):
    app = typer.Typer()
    app.command()(health)
    monkeypatch.setattr("trading_radar.health_cli.load_config", lambda _: config)
    received = []

    def inspect(cfg, max_age_hours):
        received.append((cfg, max_age_hours))
        return {"status": state, "ready": state != "critical"}

    monkeypatch.setattr("trading_radar.health_cli.check_health", inspect)
    result = CliRunner().invoke(app, ["--max-age-hours", "12"])
    assert result.exit_code == exit_code
    assert json.loads(result.stdout)["status"] == state
    assert received == [(config, 12)]


def test_cli_bad_configuration_is_json_without_details(monkeypatch):
    app = typer.Typer()
    app.command()(health)

    def invalid(_):
        raise ValueError("secret configuration")

    monkeypatch.setattr("trading_radar.health_cli.load_config", invalid)
    result = CliRunner().invoke(app)
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"] == "invalid_configuration"
    assert "secret" not in result.stdout
