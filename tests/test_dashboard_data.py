import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

import trading_radar.dashboard_data as dashboard
from trading_radar.models import Score
from trading_radar.monitoring import record_health
from trading_radar.storage import Repository

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)


def test_dashboard_includes_read_only_ninety_day_trends(dashboard_config, repo, job, tmp_path):
    job.first_seen = job.last_seen = NOW - timedelta(days=1)
    with repo.transaction():
        repo.upsert(job)
    before = fingerprints(repo)
    result = observation(dashboard_config, tmp_path)
    assert result["trends"]["status"] == "ok"
    assert result["trends"]["days"] == 90
    assert len(result["trends"]["daily"]) == 90
    assert result["trends"]["summary"]["new_jobs"] == 1
    assert fingerprints(repo) == before


def test_bad_scan_history_does_not_hide_current_jobs(dashboard_config, repo, job, tmp_path):
    with repo.transaction():
        repo.upsert(job)
        repo.db.execute(
            "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)", (NOW.isoformat(), "{bad")
        )
    before = fingerprints(repo)
    result = observation(dashboard_config, tmp_path)
    assert result["status"] == "ok"
    assert len(result["jobs"]) == 1
    assert result["trends"]["status"] == "error"
    assert result["trends"]["daily"] == []
    assert any(warning["code"] == "trends_unavailable" for warning in result["warnings"])
    assert fingerprints(repo) == before


def test_trends_failure_is_nonfatal(dashboard_config, tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("private details")

    monkeypatch.setattr(dashboard, "build_trends", unavailable)
    result = observation(dashboard_config, tmp_path)
    assert result["status"] == "ok"
    assert result["trends"]["error"]["code"] == "trends_unavailable"
    assert "private details" not in json.dumps(result)


@pytest.fixture
def dashboard_config(config, repo, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO companies(source,last_success,bootstrapped) VALUES('test',?,1)",
            ((NOW - timedelta(hours=1)).isoformat(),),
        )
    return config


def observation(config, tmp_path, **kwargs):
    return dashboard.build_dashboard_data(config, tmp_path / "history", now=NOW, **kwargs)


def fingerprints(repo):
    return {
        row[0]: hashlib.sha256(
            repr(
                [
                    tuple(record)
                    for record in repo.db.execute(f'SELECT * FROM "{row[0]}" ORDER BY rowid')
                ]
            ).encode()
        ).hexdigest()
        for row in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def test_complete_data_and_manual_fields_are_preserved(dashboard_config, repo, job, tmp_path):
    job.application_deadline = None
    job.description_text = "Application deadline: 2026-10-01 at 12:00 UTC. <script>bad()</script>"
    with repo.transaction():
        repo.upsert(job)
    repo.update_application(
        job.id,
        {
            "status": "Applied",
            "application_date": "2026-09-16",
            "recruiter": "Marie",
            "notes": "Private notes <b>text</b>",
            "next_action": "Follow up",
            "next_action_date": "2026-09-17",
        },
    )
    before = fingerprints(repo)
    result = observation(dashboard_config, tmp_path)
    assert result["status"] == "ok"
    assert fingerprints(repo) == before
    assert len(result["jobs"]) == 1
    row = result["jobs"][0]
    assert row["company"] == job.company
    assert row["score"] == job.score_breakdown.total
    assert row["score_breakdown"] == job.score_breakdown.model_dump(mode="json")
    assert row["description_text"] == job.description_text
    assert row["application"] == repo.application(job.id).model_dump(mode="json")
    assert row["deadline"] == {
        "precision": "instant",
        "day": "2026-10-01",
        "instant": "2026-10-01T12:00:00+00:00",
        "source": "description",
        "evidence": ["Application deadline: 2026-10-01 at 12:00 UTC"],
    }
    assert result["summary"]["applications_due"] == 1
    assert result["summary"]["applications_in_progress"] == 1
    assert result["summary"]["fresh_sources"] == 1
    assert result["facets"]["companies"] == [job.company]
    assert result["facets"]["sources"] == ["test"]
    assert result["monitoring"]["snapshots"] == []
    assert not (tmp_path / "history").exists()
    assert "raw_payload" not in row and "description" not in row
    json.dumps(result, allow_nan=False)


def test_zero_jobs_is_successful_empty_result(dashboard_config, tmp_path):
    result = observation(dashboard_config, tmp_path)
    assert result["status"] == "ok" and result["error"] is None
    assert result["jobs"] == [] and result["summary"]["total"] == 0


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,test",
        "file:///tmp/x",
        "//example.org/path",
        "https:///missing-host",
        "https://user:pass@example.org",
        "https://example.org:bad",
        "https://example.org:70000",
        "https://[invalid",
        "https://example.org/white space",
        "\nhttps://example.org",
        "https://example.org/\x00",
        "https://example.org\\evil",
        "https://example.org/\x7f",
        "",
    ],
)
def test_unsafe_urls_are_not_links(url):
    assert dashboard.safe_url(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/job?id=42&x=%20",
        "http://localhost:8000/path",
        "HTTPS://example.org/path",
        "https://[::1]:443/",
        "https://jobs.example.org/café",
    ],
)
def test_http_urls_are_preserved(url):
    assert dashboard.safe_url(url) == url


def test_unsafe_stored_links_are_removed(dashboard_config, repo, job, tmp_path):
    with repo.transaction():
        repo.upsert(job)
    job.apply_url = "javascript:alert(1)"
    job.source_url = "file:///private"
    with repo.transaction():
        repo._write(job)
    row = observation(dashboard_config, tmp_path)["jobs"][0]
    assert row["apply_url"] is None and row["source_url"] is None


def test_missing_database_and_parent_are_not_created(config, tmp_path):
    path = tmp_path / "absent" / "jobs.db"
    config.settings.database_url = f"sqlite:///{path}"
    result = observation(config, tmp_path)
    assert result["status"] == "error" and result["error"]["code"] == "missing"
    assert result["health"]["status"] == "critical"
    assert not path.parent.exists()


@pytest.mark.parametrize("content,code", [(b"not sqlite", "corrupt"), (b"", "incompatible")])
def test_invalid_database_is_not_modified(config, tmp_path, content, code):
    path = tmp_path / "jobs.db"
    path.write_bytes(content)
    config.settings.database_url = f"sqlite:///{path}"
    result = observation(config, tmp_path)
    assert result["error"]["code"] == code
    assert path.read_bytes() == content


@pytest.mark.parametrize("version", [1, 3, 5, None])
def test_unsupported_schema_is_not_migrated(dashboard_config, repo, tmp_path, version):
    with repo.transaction():
        repo.db.execute("DELETE FROM schema_version")
        if version is not None:
            repo.db.execute("INSERT INTO schema_version VALUES(?)", (version,))
    before = fingerprints(repo)
    result = observation(dashboard_config, tmp_path)
    assert result["error"]["code"] == "incompatible"
    assert fingerprints(repo) == before


def test_missing_schema_objects_are_not_recreated(dashboard_config, repo, tmp_path):
    with repo.transaction():
        repo.db.execute("DROP TABLE alert_history")
    assert observation(dashboard_config, tmp_path)["error"]["code"] == "incompatible"
    assert (
        repo.db.execute("SELECT name FROM sqlite_master WHERE name='alert_history'").fetchall()
        == []
    )


@pytest.mark.parametrize(
    "change",
    [
        "UPDATE jobs SET payload='{}'",
        "UPDATE jobs SET score=101",
        "UPDATE jobs SET is_active=2",
        "DELETE FROM applications",
        "UPDATE applications SET status='invented'",
        "UPDATE applications SET next_action_date='bad'",
    ],
)
def test_invalid_business_records_fail_explicitly(dashboard_config, repo, job, tmp_path, change):
    with repo.transaction():
        repo.upsert(job)
        repo.db.execute(change)
    result = observation(dashboard_config, tmp_path)
    assert result["status"] == "error" and result["error"]["code"] == "invalid_data"
    assert result["jobs"] == []


def test_orphan_records_fail_integrity_check(dashboard_config, repo, tmp_path):
    repo.db.execute("PRAGMA foreign_keys=OFF")
    with repo.transaction():
        repo.db.execute("INSERT INTO applications(job_id) VALUES('missing')")
    assert observation(dashboard_config, tmp_path)["error"]["code"] == "corrupt"


def test_bound_is_explicit_instead_of_silent_truncation(
    dashboard_config, repo, job, tmp_path, monkeypatch
):
    with repo.transaction():
        repo.upsert(job)
    monkeypatch.setattr(dashboard, "MAX_JOBS", 0)
    result = observation(dashboard_config, tmp_path)
    assert result["error"]["code"] == "limit_exceeded"
    assert result["jobs"] == []


def test_counts_use_active_jobs_and_keep_closed_records(dashboard_config, repo, job, tmp_path):
    jobs = []
    for index, active in enumerate([True, False, True]):
        entry = job.model_copy(deep=True)
        entry.id = f"job-{index}"
        entry.fingerprint = f"fingerprint-{index}"
        entry.external_id = f"external-{index}"
        entry.apply_url = f"https://example.org/job/{index}"
        entry.is_active = active
        entry.score_breakdown = Score(trading=30, junior=20, start=15, front_office=15)
        if index == 2:
            entry.score_breakdown.exclusions = ["Experienced position"]
        jobs.append(entry)
    with repo.transaction():
        for entry in jobs:
            repo.upsert(entry)
    result = observation(dashboard_config, tmp_path)
    assert result["summary"]["total"] == 3
    assert result["summary"]["active"] == 2
    assert result["summary"]["high_priority"] == 1
    assert result["summary"]["relevant"] == 1
    assert result["jobs"][-1]["score"] == 0
    assert result["jobs"][-1]["score_breakdown"]["exclusions"] == ["Experienced position"]


def test_monitoring_archives_are_read_without_recording(dashboard_config, tmp_path):
    root = tmp_path / "history"
    for day in range(12):
        record_health(dashboard_config, root, now=NOW + timedelta(days=day))
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    result = observation(dashboard_config, tmp_path)
    assert result["monitoring"]["status"] == "ok"
    assert result["monitoring"]["total"] == 12
    assert len(result["monitoring"]["snapshots"]) == 10
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before


def test_broken_monitoring_is_nonfatal(dashboard_config, repo, job, tmp_path):
    with repo.transaction():
        repo.upsert(job)
    (tmp_path / "history").mkdir()
    (tmp_path / "history" / "broken.json").write_text("{}")
    result = observation(dashboard_config, tmp_path)
    assert result["status"] == "ok" and len(result["jobs"]) == 1
    assert result["monitoring"]["status"] == "unavailable"
    assert result["warnings"][0]["code"] == "monitoring_unavailable"


def test_health_failure_is_explicit_and_nonfatal(dashboard_config, tmp_path, monkeypatch):
    def failure(*args, **kwargs):
        raise OSError("private filesystem path")

    monkeypatch.setattr(dashboard, "check_health", failure)
    result = observation(dashboard_config, tmp_path)
    assert result["status"] == "ok" and result["health"]["status"] == "unavailable"
    assert "private filesystem" not in json.dumps(result)


@pytest.mark.parametrize(
    "url", ["sqlite:///:memory:", "postgresql://user:secret@host/db", "sqlite:///"]
)
def test_invalid_configuration_is_safe(config, tmp_path, url):
    config.settings.database_url = url
    result = observation(config, tmp_path)
    assert result["error"]["code"] == "invalid_config"
    assert "secret" not in json.dumps(result)


def test_reads_wal_without_repository_or_migrations(
    dashboard_config, repo, job, tmp_path, monkeypatch
):
    with repo.transaction():
        repo.upsert(job)
    before = fingerprints(repo)

    def forbidden(*args, **kwargs):
        raise AssertionError("Dashboard must not construct Repository")

    monkeypatch.setattr(Repository, "__init__", forbidden)
    real_connect = sqlite3.connect
    accesses = []
    statements = []

    def connect(database, *args, **kwargs):
        connection = real_connect(database, *args, **kwargs)
        if database != ":memory:":
            accesses.append((database, kwargs))
            connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect)
    result = observation(dashboard_config, tmp_path)
    assert result["jobs"][0]["id"] == job.id
    assert all("?mode=ro" in name and kwargs["uri"] for name, kwargs in accesses)
    assert "PRAGMA query_only=ON" in statements and "BEGIN" in statements
    assert not any(sql.startswith(("UPDATE", "INSERT", "DELETE", "CREATE")) for sql in statements)
    assert fingerprints(repo) == before


def test_jobs_and_applications_share_a_snapshot(dashboard_config, repo, job, tmp_path, monkeypatch):
    with repo.transaction():
        repo.upsert(job)
    real_job = dashboard._job

    def concurrent_update(row):
        # The writer commits while the reader's transaction remains open in WAL mode.
        repo.update_application(job.id, {"notes": "committed during read"})
        return real_job(row)

    monkeypatch.setattr(dashboard, "_job", concurrent_update)
    result = observation(dashboard_config, tmp_path)
    assert result["jobs"][0]["application"]["notes"] is None
    assert repo.application(job.id).notes == "committed during read"


def test_naive_dashboard_time_is_rejected(dashboard_config):
    with pytest.raises(ValueError, match="timezone"):
        dashboard.build_dashboard_data(dashboard_config, now=NOW.replace(tzinfo=None))


def test_unreadable_database_errors_hide_filesystem_details(
    dashboard_config, tmp_path, monkeypatch
):
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("Access denied to private database path")

    monkeypatch.setattr(sqlite3, "connect", fail)
    result = observation(dashboard_config, tmp_path)
    assert result["error"]["code"] == "unreadable"
    assert "private database path" not in json.dumps(result)


def test_invalid_filesystem_path_is_controlled(config, tmp_path):
    config.settings.database_url = "sqlite:///invalid\x00path"
    result = observation(config, tmp_path)
    assert result["error"]["code"] == "invalid_config"


def test_naive_stored_timestamps_are_invalid(dashboard_config, repo, job, tmp_path):
    job.first_seen = job.first_seen.replace(tzinfo=None)
    with repo.transaction():
        repo.upsert(job)
    assert observation(dashboard_config, tmp_path)["error"]["code"] == "invalid_data"
