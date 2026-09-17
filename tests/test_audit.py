import json
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trading_radar.audit import audit_sources
from trading_radar.cli import app

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)


def setup_database(config, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"


@pytest.mark.parametrize(
    "success,failure,enabled,status",
    [
        (None, None, True, "never_scanned"),
        (-24, None, True, "fresh"),
        (-24.01, None, True, "stale"),
        (-1, -2, True, "fresh"),
        (-2, -1, True, "failed"),
        (None, -1, True, "failed"),
        (-1, -1, True, "failed"),
        (1, None, True, "unknown"),
        (-1, 1, True, "unknown"),
        ("bad timestamp", None, True, "unknown"),
        ("2026-09-17T10:00:00", None, True, "unknown"),
        (None, "bad timestamp", True, "unknown"),
        (None, -1, False, "disabled"),
        ("2026-09-17T12:00:00+02:00", None, True, "fresh"),
    ],
)
def test_source_status(config, repo, tmp_path, success, failure, enabled, status):
    setup_database(config, tmp_path)
    config.companies["test"].enabled = enabled

    def date(value):
        return (
            (NOW + timedelta(hours=value)).isoformat() if isinstance(value, (int, float)) else value
        )

    with repo.db:
        repo.db.execute(
            "INSERT INTO companies(source,last_success,last_failure) VALUES(?,?,?)",
            ("test", date(success), date(failure)),
        )
    report = audit_sources(config, now=NOW)
    assert report["summary"] == {status: 1}
    assert report["sources"][0]["status"] == status


def test_recent_source_does_not_refresh_old_jobs_or_write(config, repo, tmp_path, job):
    setup_database(config, tmp_path)
    with repo.transaction():
        repo.upsert(job)
        repo.mark_success("test", 0, 1)
        repo.db.execute("UPDATE companies SET last_success=?", (NOW.isoformat(),))
        repo.db.execute(
            "UPDATE job_sources SET last_seen=?", ((NOW - timedelta(days=2)).isoformat(),)
        )
        repo.db.execute("INSERT INTO companies(source) VALUES('removed')")
    before = list(repo.db.iterdump())
    report = audit_sources(config, now=NOW)
    source = report["sources"][0]
    assert source["status"] == "fresh"
    assert source["stored_jobs"] == source["not_recently_verified_jobs"] == 1
    assert source["recently_seen_jobs"] == source["last_snapshot_jobs"] == 0
    assert report["unconfigured_sources"] == ["removed"]
    assert list(repo.db.iterdump()) == before


def test_distinct_jobs_count_latest_source_observation(config, repo, tmp_path, job):
    setup_database(config, tmp_path)
    with repo.transaction():
        repo.upsert(job)
        repo.db.execute(
            "UPDATE job_sources SET last_seen=?", ((NOW - timedelta(days=2)).isoformat(),)
        )
        repo.db.execute(
            """INSERT INTO job_sources(source,identity,job_id,apply_url,last_seen)
            SELECT source,'another identity',job_id,apply_url,? FROM job_sources""",
            (NOW.isoformat(),),
        )
    source = audit_sources(config, now=NOW)["sources"][0]
    assert source["stored_jobs"] == source["recently_seen_jobs"] == 1
    assert source["not_recently_verified_jobs"] == 0


@pytest.mark.parametrize("seen", ["invalid", "2026-09-17T11:00:00", "2026-09-18T12:00:00+00:00"])
def test_invalid_job_observation_is_not_fresh(config, repo, tmp_path, job, seen):
    setup_database(config, tmp_path)
    with repo.transaction():
        repo.upsert(job)
        repo.db.execute("UPDATE job_sources SET last_seen=?", (seen,))
    assert audit_sources(config, now=NOW)["sources"][0]["not_recently_verified_jobs"] == 1


def test_missing_database_is_not_created(config, tmp_path):
    setup_database(config, tmp_path)
    assert audit_sources(config, now=NOW)["database"] == "not_created"
    assert not (tmp_path / "jobs.db").exists()


@pytest.mark.parametrize("age", [0, -1, float("nan"), float("inf"), 87601])
def test_invalid_threshold(config, age):
    with pytest.raises(ValueError):
        audit_sources(config, age, now=NOW)


@pytest.mark.parametrize("url", ["sqlite:///:memory:", "postgresql://localhost/jobs"])
def test_requires_file_database(config, url):
    config.settings.database_url = url
    with pytest.raises(ValueError):
        audit_sources(config)


def test_requires_aware_clock(config):
    with pytest.raises(ValueError):
        audit_sources(config, now=NOW.replace(tzinfo=None))


@pytest.fixture
def cli_environment(tmp_path, monkeypatch):
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/jobs.db")
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    return tmp_path


def test_cli_offline_without_notifier_or_database(cli_environment):
    result = CliRunner().invoke(app, ["audit", "--output", "reports/freshness.json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["database"] == "not_created"
    assert json.loads(Path("reports/freshness.json").read_text(encoding="utf-8")) == report
    assert not Path("data").exists()


@pytest.mark.parametrize("filename", ["jobs.db", "jobs.db-wal", "jobs.db-shm"])
def test_cli_cannot_overwrite_database(cli_environment, filename):
    Path("data").mkdir()
    target = Path("data") / filename
    target.write_bytes(b"unchanged")
    result = CliRunner().invoke(app, ["audit", "--output", str(target)])
    assert result.exit_code == 1
    assert target.read_bytes() == b"unchanged"


def test_cli_corrupt_database_fails_without_recreating(cli_environment):
    Path("data").mkdir()
    Path("data/jobs.db").write_bytes(b"not sqlite")
    result = CliRunner().invoke(app, ["audit"])
    assert result.exit_code == 1 and "DatabaseError" in result.output
    assert Path("data/jobs.db").read_bytes() == b"not sqlite"


def test_read_connection_rejects_writes(config, repo, tmp_path, monkeypatch):
    setup_database(config, tmp_path)
    connect = sqlite3.connect

    def checked_connect(*args, **kwargs):
        db = connect(*args, **kwargs)
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            db.execute("INSERT INTO companies(source) VALUES('must-not-write')")
        db.rollback()
        return db

    monkeypatch.setattr("trading_radar.audit.sqlite3.connect", checked_connect)
    assert audit_sources(config, now=NOW)["database"] == "read_only"
