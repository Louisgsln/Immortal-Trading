import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta, timezone

import pytest

import trading_radar.trends as trends

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)


@pytest.fixture
def trends_config(config, repo, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    return config


def observe(config, **kwargs):
    return trends.build_trends(config, now=NOW, **kwargs)


def seed(repo, job, timestamp="2026-09-17T12:00:00+00:00"):
    with repo.transaction():
        repo.upsert(job)
        repo.db.execute("DELETE FROM job_versions")
        repo.db.execute("UPDATE jobs SET first_seen=?", (timestamp,))


def version(repo, job, timestamp, event):
    repo.db.execute(
        "INSERT INTO job_versions(job_id,created_at,event,payload) VALUES(?,?,?,?)",
        (job.id, timestamp, event, "payload is deliberately not needed"),
    )


def scan(repo, timestamp, metrics=None):
    repo.db.execute(
        "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)",
        (timestamp, json.dumps(metrics if metrics is not None else {"failed": {}})),
    )


def fingerprint(repo):
    return {
        name: hashlib.sha256(
            repr([tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}"')]).encode()
        ).hexdigest()
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def test_empty_days_are_zero_filled_and_window_inclusive(trends_config):
    result = observe(trends_config, days=3)
    assert result["status"] == "ok" and result["error"] is None
    assert result["format_version"] == 1 and result["timezone"] == "UTC"
    assert result["window"] == {"start": "2026-09-15", "end": "2026-09-17"}
    assert [row["date"] for row in result["daily"]] == ["2026-09-15", "2026-09-16", "2026-09-17"]
    assert result["summary"] == dict.fromkeys(trends.COUNTERS, 0)
    assert len(trends.build_trends(trends_config, now=NOW)["daily"]) == 30
    json.dumps(result, allow_nan=False)


def test_events_scans_and_detection_are_independent(trends_config, repo, job):
    seed(repo, job, "2026-09-16T00:00:00+00:00")
    with repo.transaction():
        for event in ("new", "updated", "updated", "rescored", "closed", "reopened"):
            version(repo, job, "2026-09-17T11:00:00Z", event)
        scan(repo, "2026-09-17T10:00:00Z", {"failed": {"a": "error", "b": "error"}, "new": 999})
        scan(repo, "2026-09-17T12:00:00Z", {"failed": {"a": "repeated failure"}})
    before = fingerprint(repo)
    result = observe(trends_config, days=3)
    assert result["summary"] == {
        "new_jobs": 1,
        "updates": 2,
        "rescored": 1,
        "closed": 1,
        "reopened": 1,
        "scans": 2,
        "failed_sources": 3,
    }
    assert result["daily"][1]["new_jobs"] == 1
    assert result["daily"][2]["new_jobs"] == 0
    assert fingerprint(repo) == before


@pytest.mark.parametrize(
    "timestamp,expected",
    [
        ("2026-09-16T23:59:59Z", 0),
        ("2026-09-17T00:00:00Z", 1),
        ("2026-09-17T12:00:00Z", 1),
        ("2026-09-17T12:00:00.000001Z", 0),
        ("2026-09-18T00:00:00Z", 0),
        ("2026-09-17T00:30:00+02:00", 0),
        ("2026-09-16T23:30:00-01:00", 1),
    ],
)
def test_utc_boundaries_apply_to_all_tables(trends_config, repo, job, timestamp, expected):
    seed(repo, job, timestamp)
    with repo.transaction():
        version(repo, job, timestamp, "updated")
        scan(repo, timestamp, {"failed": {"a": "error"}})
    summary = observe(trends_config, days=1)["summary"]
    assert (
        summary["new_jobs"]
        == summary["updates"]
        == summary["scans"]
        == summary["failed_sources"]
        == expected
    )


def test_now_is_normalized_to_utc(trends_config):
    local = datetime(2026, 9, 18, 1, tzinfo=timezone(timedelta(hours=2)))
    result = trends.build_trends(trends_config, days=1, now=local)
    assert result["generated_at"] == "2026-09-17T23:00:00+00:00"
    assert result["daily"][0]["date"] == "2026-09-17"


@pytest.mark.parametrize("days", [0, -1, 366, 1.0, True, False, "30", None])
def test_invalid_day_counts_raise(config, days):
    with pytest.raises(ValueError, match="Days"):
        observe(config, days=days)


@pytest.mark.parametrize("days", [1, 365])
def test_day_count_limits(trends_config, days):
    assert len(observe(trends_config, days=days)["daily"]) == days


@pytest.mark.parametrize(
    "now", [datetime(2026, 9, 17), "2026-09-17", False, datetime.min.replace(tzinfo=UTC)]
)
def test_invalid_now_raises(config, now):
    with pytest.raises(ValueError):
        trends.build_trends(config, now=now)


def test_default_now_is_used(trends_config, monkeypatch):
    monkeypatch.setattr(trends, "utcnow", lambda: NOW)
    assert trends.build_trends(trends_config)["generated_at"] == NOW.isoformat()


@pytest.mark.parametrize(
    "table,column",
    [("jobs", "first_seen"), ("job_versions", "created_at"), ("scan_runs", "created_at")],
)
@pytest.mark.parametrize("timestamp", ["broken secret text", "2026-09-17T12:00:00", "", "x" * 65])
def test_malformed_timestamps_fail_without_partial_counts(
    trends_config, repo, job, table, column, timestamp
):
    seed(repo, job)
    with repo.transaction():
        version(repo, job, NOW.isoformat(), "updated")
        scan(repo, NOW.isoformat())
        repo.db.execute(f"UPDATE {table} SET {column}=?", (timestamp,))
    result = observe(trends_config)
    assert result["status"] == "error" and result["error"]["code"] == "invalid_data"
    assert result["daily"] == [] and result["summary"] == {}
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize(
    "raw",
    [
        "{bad",
        "[]",
        "{}",
        '{"failed":null}',
        '{"failed":[]}',
        '{"failed":{"a":2}}',
        '{"failed":{"": "error"}}',
        '{"failed":{},"failed":{"a":"error"}}',
        '{"failed":{},"sources":true}',
        '{"failed":{},"received":-1}',
        '{"failed":{},"new":1.5}',
        '{"failed":{},"duration":NaN}',
        '{"failed":{},"duration":Infinity}',
        '{"failed":{},"duration":-1}',
        '{"failed":{},"duration":false}',
    ],
)
def test_invalid_metrics_are_rejected_even_outside_window(trends_config, repo, raw):
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)", ("2000-01-01T00:00:00Z", raw)
        )
    assert observe(trends_config)["error"]["code"] == "invalid_data"


def test_unknown_version_event_is_not_silently_ignored(trends_config, repo, job):
    seed(repo, job)
    with repo.transaction():
        version(repo, job, "2000-01-01T00:00:00Z", "unsupported")
    assert observe(trends_config)["error"]["code"] == "invalid_data"


@pytest.mark.parametrize("table", ["jobs", "job_versions", "scan_runs"])
def test_explicit_table_limits(trends_config, repo, job, monkeypatch, table):
    seed(repo, job)
    with repo.transaction():
        if table == "job_versions":
            version(repo, job, NOW.isoformat(), "updated")
            version(repo, job, NOW.isoformat(), "closed")
        elif table == "scan_runs":
            scan(repo, NOW.isoformat())
            scan(repo, NOW.isoformat())
    monkeypatch.setattr(trends, "MAX_ROWS", 0 if table == "jobs" else 1)
    result = observe(trends_config)
    assert result["error"]["code"] == "limit_exceeded" and result["daily"] == []


def test_metrics_size_is_bounded(trends_config, repo, monkeypatch):
    with repo.transaction():
        scan(repo, NOW.isoformat())
    monkeypatch.setattr(trends, "MAX_METRICS_LENGTH", 2)
    assert observe(trends_config)["error"]["code"] == "limit_exceeded"


def test_missing_database_is_not_created(config, tmp_path):
    path = tmp_path / "missing" / "jobs.db"
    config.settings.database_url = f"sqlite:///{path}"
    assert observe(config)["error"]["code"] == "missing"
    assert not path.parent.exists()


@pytest.mark.parametrize(
    "url", ["sqlite:///:memory:", "sqlite:///", "postgres:///db", "sqlite:///bad\x00path"]
)
def test_invalid_database_configuration(config, url):
    config.settings.database_url = url
    assert observe(config)["error"]["code"] == "invalid_config"


@pytest.mark.parametrize(
    "content,code", [(b"not a sqlite database", "corrupt"), (b"", "incompatible")]
)
def test_invalid_database_bytes_are_preserved(config, tmp_path, content, code):
    path = tmp_path / "jobs.db"
    path.write_bytes(content)
    config.settings.database_url = f"sqlite:///{path}"
    assert observe(config)["error"]["code"] == code
    assert path.read_bytes() == content


@pytest.mark.parametrize("version_number", [None, 1, 3, 5])
def test_schema_version_is_not_migrated(trends_config, repo, version_number):
    with repo.transaction():
        repo.db.execute("DELETE FROM schema_version")
        if version_number is not None:
            repo.db.execute("INSERT INTO schema_version VALUES(?)", (version_number,))
    before = fingerprint(repo)
    assert observe(trends_config)["error"]["code"] == "incompatible"
    assert fingerprint(repo) == before


def test_missing_schema_object_is_not_recreated(trends_config, repo):
    with repo.transaction():
        repo.db.execute("DROP INDEX jobs_company")
    assert observe(trends_config)["error"]["code"] == "incompatible"
    assert (
        repo.db.execute("SELECT 1 FROM sqlite_master WHERE name='jobs_company'").fetchone() is None
    )


def test_foreign_key_corruption_is_reported(trends_config, repo):
    repo.db.execute("PRAGMA foreign_keys=OFF")
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO job_versions(job_id,created_at,event,payload) VALUES('missing',?,'new','{}')",
            (NOW.isoformat(),),
        )
    assert observe(trends_config)["error"]["code"] == "corrupt"


def test_wal_uncheckpointed_data_is_read_only(trends_config, repo, job, monkeypatch, tmp_path):
    repo.db.execute("PRAGMA wal_autocheckpoint=0")
    seed(repo, job)
    paths = [tmp_path / "jobs.db", tmp_path / "jobs.db-wal"]
    before = {path: path.read_bytes() for path in paths}
    calls, statements = [], []
    real_connect = sqlite3.connect

    def connect(database, *args, **kwargs):
        calls.append(str(database))
        connection = real_connect(database, *args, **kwargs)
        if "mode=ro" in str(database):
            connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect)
    assert observe(trends_config)["summary"]["new_jobs"] == 1
    assert {path: path.read_bytes() for path in paths} == before
    assert all(call == ":memory:" or "mode=ro" in call for call in calls)
    assert "PRAGMA query_only=ON" in statements and "BEGIN" in statements
    assert not any("payload" in query for query in statements if query.startswith("SELECT"))


def test_all_tables_share_snapshot_despite_concurrent_commit(trends_config, repo, job, monkeypatch):
    seed(repo, job)
    original = trends._schema
    written = False

    def schema(db):
        nonlocal written
        result = original(db)
        if not written:
            with repo.transaction():
                version(repo, job, NOW.isoformat(), "updated")
                scan(repo, NOW.isoformat())
            written = True
        return result

    monkeypatch.setattr(trends, "_schema", schema)
    first = observe(trends_config)["summary"]
    second = observe(trends_config)["summary"]
    assert first["new_jobs"] == 1 and first["updates"] == first["scans"] == 0
    assert second["updates"] == second["scans"] == 1


def test_unreadable_database_error_is_sanitized(trends_config, monkeypatch):
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("private /secret/path token")

    monkeypatch.setattr(sqlite3, "connect", fail)
    result = observe(trends_config)
    assert result["error"]["code"] == "unreadable"
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("timestamp", ["0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00"])
def test_timestamp_timezone_overflow_is_safe_error(trends_config, repo, job, timestamp):
    seed(repo, job, timestamp)
    assert observe(trends_config)["error"]["code"] == "invalid_data"


@pytest.mark.parametrize("raw", ['{"failed":{},"future_metric":NaN}', b'{"failed":{}}'])
def test_scan_metrics_requires_strict_json_text(trends_config, repo, raw):
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)", (NOW.isoformat(), raw)
        )
    assert observe(trends_config)["error"]["code"] == "invalid_data"


def test_scan_counter_totals_do_not_overflow(trends_config, repo):
    with repo.transaction():
        scan(repo, NOW.isoformat(), {"failed": {}, "received": 2**128, "duration": 0})
    assert observe(trends_config)["summary"]["scans"] == 1
