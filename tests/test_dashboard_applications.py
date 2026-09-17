import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from filelock import FileLock

import trading_radar.dashboard_applications as service


@pytest.fixture
def seeded(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    with repo.transaction():
        repo.upsert(job)
    return config, repo, job


def snapshot(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def test_read_is_consistent_json_serializable_and_preserves_every_table(seeded):
    config, repo, job = seeded
    before = snapshot(repo)
    result = service.read_application(config, job.id)
    assert result["application"]["status"] == "New"
    assert len(result["revision"]) == 64
    assert result["history"] == []
    assert result["history_total"] == 0 and not result["history_truncated"]
    json.dumps(result, allow_nan=False)
    assert snapshot(repo) == before
    assert not Path(repo.lock_path).exists()


def test_updates_only_application_and_history_with_utc_timestamp(seeded):
    config, repo, job = seeded
    before = snapshot(repo)
    original = service.read_application(config, job.id)
    updated = service.update_application(
        config,
        job.id,
        {
            "status": "Applied",
            "application_date": "2026-09-17",
            "recruiter": "  Recruiter  ",
            "notes": "<script>text only</script>",
            "next_action": "Follow up",
            "next_action_date": "2026-09-20",
        },
        original["revision"],
    )
    assert updated["application"]["recruiter"] == "Recruiter"
    assert updated["revision"] != original["revision"]
    assert updated == service.read_application(config, job.id)
    history = updated["history"]
    assert len(history) == 1
    assert history[0]["before"] == original["application"]
    assert history[0]["after"] == updated["application"]
    assert datetime.fromisoformat(history[0]["changed_at"]).utcoffset().total_seconds() == 0
    after = snapshot(repo)
    assert {
        k: v for k, v in before.items() if k not in {"applications", "application_history"}
    } == {k: v for k, v in after.items() if k not in {"applications", "application_history"}}


def test_normalized_noop_does_not_create_history_or_change_revision(seeded):
    config, repo, job = seeded
    first = service.read_application(config, job.id)
    before = snapshot(repo)
    assert service.update_application(config, job.id, {"notes": "  "}, first["revision"]) == first
    assert snapshot(repo) == before


def test_stale_revision_cannot_overwrite_a_newer_edit(seeded):
    config, repo, job = seeded
    first = service.read_application(config, job.id)
    service.update_application(config, job.id, {"status": "Reviewing"}, first["revision"])
    before = snapshot(repo)
    with pytest.raises(service.ApplicationEditError) as error:
        service.update_application(config, job.id, {"status": "Applied"}, first["revision"])
    assert error.value.status == 409 and error.value.code == "conflict"
    assert snapshot(repo) == before


def test_cli_aba_change_invalidates_old_revision(seeded):
    config, repo, job = seeded
    first = service.read_application(config, job.id)
    repo.update_application(job.id, {"status": "Applied"})
    repo.update_application(job.id, {"status": "New"})
    current = service.read_application(config, job.id)
    assert current["application"] == first["application"]
    assert current["revision"] != first["revision"]
    with pytest.raises(service.ApplicationEditError, match="changé"):
        service.update_application(config, job.id, {"notes": "stale"}, first["revision"])
    assert repo.application(job.id).notes is None


def test_read_stays_on_one_snapshot_during_concurrent_cli_edit(seeded, monkeypatch):
    config, repo, job = seeded
    original = service.read_application(config, job.id)
    validate = service._validate_database

    def validate_then_edit(db):
        validate(db)
        repo.update_application(job.id, {"notes": "committed during the reader transaction"})

    monkeypatch.setattr(service, "_validate_database", validate_then_edit)
    assert service.read_application(config, job.id) == original
    assert repo.application(job.id).notes == "committed during the reader transaction"


def test_lock_contention_is_safe_and_nonblocking(seeded):
    config, repo, job = seeded
    original = service.read_application(config, job.id)
    before = snapshot(repo)
    with FileLock(repo.lock_path, timeout=0):
        with pytest.raises(service.ApplicationEditError) as error:
            service.update_application(config, job.id, {"notes": "busy"}, original["revision"])
        assert service.read_application(config, job.id) == original
    assert error.value.code == "busy" and error.value.status == 503
    assert str(Path(repo.lock_path)) not in str(error.value)
    assert snapshot(repo) == before


def test_sqlite_writer_contention_returns_busy(seeded):
    config, repo, job = seeded
    original = service.read_application(config, job.id)
    repo.db.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(service.ApplicationEditError) as error:
            service.update_application(config, job.id, {"notes": "busy"}, original["revision"])
        assert error.value.code == "busy"
    finally:
        repo.db.rollback()


def test_history_insert_failure_rolls_back_fields(seeded, monkeypatch):
    config, repo, job = seeded
    original = service.read_application(config, job.id)
    before = snapshot(repo)
    connect = sqlite3.connect

    class FailingConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql.startswith("INSERT INTO application_history"):
                raise sqlite3.OperationalError("private path secret")
            return super().execute(sql, parameters)

    monkeypatch.setattr(
        service.sqlite3, "connect", lambda *a, **kw: connect(*a, **kw, factory=FailingConnection)
    )
    with pytest.raises(service.ApplicationEditError) as error:
        service.update_application(config, job.id, {"status": "Applied"}, original["revision"])
    assert error.value.code == "unavailable"
    assert "private" not in str(error.value)
    assert snapshot(repo) == before


def test_commit_failure_rolls_back_fields_and_history(seeded, monkeypatch):
    config, repo, job = seeded
    original = service.read_application(config, job.id)
    before = snapshot(repo)
    connect = sqlite3.connect

    class FailingConnection(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("private commit failure")

    monkeypatch.setattr(
        service.sqlite3, "connect", lambda *a, **kw: connect(*a, **kw, factory=FailingConnection)
    )
    with pytest.raises(service.ApplicationEditError) as error:
        service.update_application(config, job.id, {"status": "Applied"}, original["revision"])
    assert error.value.code == "unavailable"
    assert "private" not in str(error.value)
    assert snapshot(repo) == before


def test_history_is_latest_fifty_in_chronological_order(seeded):
    config, repo, job = seeded
    for i in range(55):
        repo.update_application(job.id, {"notes": str(i)})
    result = service.read_application(config, job.id)
    assert result["history_total"] == 55 and result["history_truncated"]
    assert len(result["history"]) == 50
    assert [entry["id"] for entry in result["history"]] == list(range(6, 56))
    assert result["history"][0]["after"]["notes"] == "5"
    assert result["history"][-1]["after"] == result["application"]


@pytest.mark.parametrize("job_id", ["", "  ", "x" * 129, None, 7, True])
def test_invalid_job_id(config, job_id):
    with pytest.raises(service.ApplicationEditError) as error:
        service.read_application(config, job_id)
    assert error.value.status == 400


def test_missing_id_and_sql_injection_are_not_found(seeded):
    config, repo, job = seeded
    before = snapshot(repo)
    for job_id in ("missing", "' OR 1=1 --"):
        with pytest.raises(service.ApplicationEditError) as error:
            service.read_application(config, job_id)
        assert error.value.status == 404
    assert snapshot(repo) == before


@pytest.mark.parametrize("changes", [{}, {"job_id": "change"}, {"unknown": "value"}, [], None])
def test_invalid_changes_structure(seeded, changes):
    config, repo, job = seeded
    revision = service.read_application(config, job.id)["revision"]
    with pytest.raises(service.ApplicationEditError) as error:
        service.update_application(config, job.id, changes, revision)
    assert error.value.status == 400
    assert repo.application_history(job.id) == []


@pytest.mark.parametrize("revision", ["", "0" * 63, "g" * 64, None, 3])
def test_invalid_revision(seeded, revision):
    config, repo, job = seeded
    with pytest.raises(service.ApplicationEditError) as error:
        service.update_application(config, job.id, {"notes": "test"}, revision)
    assert error.value.status == 400


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "Unknown"},
        {"status": None},
        {"notes": 42},
        {"notes": True},
        {"notes": "x" * 20001},
        {"recruiter": "x" * 501},
        {"next_action": "x" * 2001},
        {"application_date": "2026-02-30"},
        {"application_date": "20260917"},
        {"application_date": "2026-09-17T12:00:00Z"},
        {"next_action_date": "2026-09-20"},
    ],
)
def test_field_validation_rejects_without_changes(seeded, changes):
    config, repo, job = seeded
    revision = service.read_application(config, job.id)["revision"]
    before = snapshot(repo)
    with pytest.raises(service.ApplicationEditError) as error:
        service.update_application(config, job.id, changes, revision)
    assert error.value.status == 422 and error.value.code == "invalid_application"
    assert snapshot(repo) == before


@pytest.mark.parametrize("writing", [False, True])
def test_missing_database_does_not_create_files(config, tmp_path, writing):
    config.settings.database_url = f"sqlite:///{tmp_path / 'absent' / 'db.sqlite'}"
    with pytest.raises(service.ApplicationEditError):
        if writing:
            service.update_application(config, "job", {"status": "New"}, "0" * 64)
        else:
            service.read_application(config, "job")
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize(
    "url", ["sqlite:///:memory:", "sqlite:///", "postgresql://private", "sqlite:///bad\x00path"]
)
def test_invalid_database_config(config, url):
    config.settings.database_url = url
    with pytest.raises(service.ApplicationEditError) as error:
        service.read_application(config, "job")
    assert error.value.code == "invalid_config" and error.value.status == 400
    assert "private" not in str(error.value)


@pytest.mark.parametrize(
    "mutation", ["DELETE FROM schema_version WHERE version=4", "CREATE TABLE extra(value TEXT)"]
)
def test_schema_drift_refused_without_migration(seeded, mutation):
    config, repo, job = seeded
    with repo.transaction():
        repo.db.execute(mutation)
    before = snapshot(repo)
    with pytest.raises(service.ApplicationEditError) as error:
        service.update_application(config, job.id, {"notes": "test"}, "0" * 64)
    assert error.value.code == "incompatible"
    assert snapshot(repo) == before


def test_source_reference_database_cannot_be_modified(config, tmp_path, monkeypatch):
    source = tmp_path / "sources" / "database.db"
    source.parent.mkdir()
    source.write_bytes(b"reference")
    config.settings.database_url = f"sqlite:///{source}"
    with pytest.raises(service.ApplicationEditError) as error:
        service.update_application(config, "job", {"status": "New"}, "0" * 64)
    assert error.value.code == "protected_database"
    assert source.read_bytes() == b"reference"
    assert not Path(str(source) + ".lock").exists()


@pytest.mark.parametrize("target,value", [("status", "Invalid"), ("application_date", "yesterday")])
def test_malformed_existing_application_fails_safely(seeded, target, value):
    config, repo, job = seeded
    with repo.transaction():
        repo.db.execute(f"UPDATE applications SET {target}=?", (value,))
    with pytest.raises(service.ApplicationEditError) as error:
        service.read_application(config, job.id)
    assert error.value.code == "invalid_data"


@pytest.mark.parametrize(
    "column,value",
    [
        ("changed_at", "2026-09-17"),
        ("before_payload", "bad json"),
        ("after_payload", '{"job_id":"other"}'),
    ],
)
def test_malformed_history_fails_safely(seeded, column, value):
    config, repo, job = seeded
    repo.update_application(job.id, {"notes": "one"})
    with repo.transaction():
        repo.db.execute(f"UPDATE application_history SET {column}=?", (value,))
    with pytest.raises(service.ApplicationEditError) as error:
        service.read_application(config, job.id)
    assert error.value.code == "invalid_data"


def test_foreign_key_corruption_fails(seeded):
    config, repo, job = seeded
    repo.db.execute("PRAGMA foreign_keys=OFF")
    with repo.transaction():
        repo.db.execute("UPDATE applications SET job_id='orphan'")
    with pytest.raises(service.ApplicationEditError) as error:
        service.read_application(config, job.id)
    assert error.value.code == "corrupt"


def test_corrupt_file_returns_safe_error(config, tmp_path):
    path = tmp_path / "private.db"
    path.write_bytes(b"not a sqlite database")
    config.settings.database_url = f"sqlite:///{path}"
    with pytest.raises(service.ApplicationEditError) as error:
        service.read_application(config, "job")
    assert error.value.code == "corrupt"
    assert "private" not in str(error.value)
