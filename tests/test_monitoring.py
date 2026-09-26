import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from typer.testing import CliRunner

from trading_radar import monitoring
from trading_radar.monitoring import compare_snapshots, history, read_snapshot, record_health
from trading_radar.monitoring_cli import app

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)


@pytest.fixture
def monitored(config, repo):
    path = repo.db.execute("PRAGMA database_list").fetchone()[2]
    config.settings.database_url = f"sqlite:///{path}"
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO companies(source,last_success) VALUES('test',?)",
            ((NOW - timedelta(hours=1)).isoformat(),),
        )
    return config


def test_healthy_snapshot_round_trip_and_business_data_unchanged(monitored, repo, job, tmp_path):
    with repo.transaction():
        repo.upsert(job)
    before = list(repo.db.iterdump())
    directory = tmp_path / "history"
    result = record_health(monitored, directory, now=NOW)
    assert result["report"]["status"] == "healthy"
    assert read_snapshot(directory, result["id"]) == result
    assert list(repo.db.iterdump()) == before
    assert len(list(directory.iterdir())) == 1


def test_missing_primary_database_is_archived_without_creation(config, tmp_path):
    database = tmp_path / "missing" / "jobs.db"
    config.settings.database_url = f"sqlite:///{database}"
    result = record_health(config, tmp_path / "history", now=NOW)
    assert result["report"]["status"] == "critical"
    assert result["report"]["database"]["status"] == "missing"
    assert not database.parent.exists()


def test_corrupt_primary_is_neither_migrated_nor_repaired(config, tmp_path):
    database = tmp_path / "broken.db"
    database.write_bytes(b"broken")
    config.settings.database_url = f"sqlite:///{database}"
    result = record_health(config, tmp_path / "history", now=NOW)
    assert result["report"]["status"] == "critical"
    assert database.read_bytes() == b"broken"


def test_concurrent_snapshots_are_unique_complete_and_immutable(monitored, tmp_path):
    directory = tmp_path / "history"
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: record_health(monitored, directory, now=NOW), range(20)))
    assert len({row["id"] for row in results}) == 20
    assert history(directory)["total"] == 20
    assert all(read_snapshot(directory, row["id"]) == row for row in results)
    assert not list(directory.glob("*.tmp"))


def test_collision_does_not_overwrite_existing_report(monitored, tmp_path, monkeypatch):
    identifier = monitoring.uuid.UUID(int=1)
    monkeypatch.setattr(monitoring.uuid, "uuid4", lambda: identifier)
    first = record_health(monitored, tmp_path, now=NOW)
    path = tmp_path / (first["id"] + ".json")
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        record_health(monitored, tmp_path, now=NOW)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


def test_publication_failure_leaves_no_partial_report(monitored, tmp_path, monkeypatch):
    def failure(*args):
        raise OSError("publication failed")

    monkeypatch.setattr(monitoring.os, "link", failure)
    directory = tmp_path / "history"
    with pytest.raises(OSError):
        record_health(monitored, directory, now=NOW)
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal", ".lock", ".lock/subdir"])
def test_archive_cannot_overlap_database_files(config, tmp_path, suffix):
    database = tmp_path / "jobs.db"
    config.settings.database_url = f"sqlite:///{database}"
    with pytest.raises(ValueError, match="separate"):
        record_health(config, tmp_path / ("jobs.db" + suffix), now=NOW)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("url", ["sqlite:///:memory:", "sqlite:///", "postgresql://example"])
def test_monitoring_rejects_nonfile_database(config, tmp_path, url):
    config.settings.database_url = url
    with pytest.raises(ValueError):
        record_health(config, tmp_path / "history", now=NOW)


def test_naive_time_and_invalid_threshold_do_not_create_archive(monitored, tmp_path):
    directory = tmp_path / "history"
    with pytest.raises(ValueError):
        record_health(monitored, directory, now=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        record_health(monitored, directory, max_age_hours=float("nan"), now=NOW)
    assert not directory.exists()


def test_threshold_change_is_visible_in_comparison(monitored, tmp_path):
    first = record_health(monitored, tmp_path, now=NOW)
    second = record_health(monitored, tmp_path, max_age_hours=0.5, now=NOW + timedelta(seconds=1))
    comparison = compare_snapshots(first, second)
    assert comparison["regressed"]
    assert not comparison["same_freshness_threshold"]
    assert comparison["source_changes"] == [
        {"source": "test", "before": "fresh", "after": "stale", "change": "regressed"}
    ]


def test_missing_database_does_not_imply_sources_removed(monitored, tmp_path):
    previous = record_health(monitored, tmp_path / "history", now=NOW)
    monitored.settings.database_url = f"sqlite:///{tmp_path / 'missing.db'}"
    current = record_health(monitored, tmp_path / "history", now=NOW + timedelta(seconds=1))
    comparison = compare_snapshots(previous, current)
    assert comparison["regressed"]
    assert not comparison["sources_comparable"]
    assert comparison["source_changes"] == []


def test_history_filter_pagination_and_global_comparison(monitored, repo, tmp_path):
    first = record_health(monitored, tmp_path, now=NOW)
    with repo.transaction():
        repo.db.execute("UPDATE companies SET last_failure=?", (NOW.isoformat(),))
    second = record_health(monitored, tmp_path, now=NOW + timedelta(hours=1))
    third = record_health(monitored, tmp_path, now=NOW + timedelta(days=2))
    all_rows = history(tmp_path, limit=1, offset=1)
    assert all_rows["total"] == all_rows["matching"] == 3
    assert all_rows["snapshots"][0]["id"] == second["id"]
    assert all_rows["latest_comparison"]["current_id"] == third["id"]
    filtered = history(tmp_path, status="healthy", since=NOW.isoformat(), until=NOW.isoformat())
    assert filtered["matching"] == 1 and filtered["snapshots"][0]["id"] == first["id"]
    assert filtered["latest_comparison"] == all_rows["latest_comparison"]


def test_source_addition_removal_and_recovery_are_distinct(monitored, tmp_path):
    previous = record_health(monitored, tmp_path, now=NOW)
    current = json.loads(json.dumps(previous))
    previous["report"]["sources"] = [
        {"source": "a", "status": "stale"},
        {"source": "b", "status": "fresh"},
        {"source": "d", "status": "stale"},
    ]
    current["report"]["sources"] = [
        {"source": "a", "status": "fresh"},
        {"source": "c", "status": "fresh"},
        {"source": "d", "status": "never_scanned"},
    ]
    changes = compare_snapshots(previous, current)["source_changes"]
    assert [row["change"] for row in changes] == ["improved", "removed", "added", "changed"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": "bogus"},
        {"limit": 0},
        {"limit": 201},
        {"offset": -1},
        {"since": "2026-09-17"},
        {"until": "invalid"},
        {"since": "2026-09-18T00:00:00Z", "until": "2026-09-17T00:00:00Z"},
    ],
)
def test_invalid_history_filters(tmp_path, kwargs):
    with pytest.raises(ValueError):
        history(tmp_path, **kwargs)


def test_missing_history_does_not_create_directory(tmp_path):
    directory = tmp_path / "missing"
    assert history(directory)["total"] == 0
    assert not directory.exists()


@pytest.mark.parametrize("identifier", ["../jobs", "..", "bad", "/absolute", "a/b"])
def test_identifiers_cannot_escape_archive(tmp_path, identifier):
    with pytest.raises(ValueError):
        read_snapshot(tmp_path, identifier)


@pytest.mark.parametrize(
    "mutation",
    [
        "checksum",
        "version",
        "id",
        "timestamp",
        "ready",
        "json",
        "extra",
        "size",
        "duplicate",
        "database",
    ],
)
def test_corruption_is_not_silently_skipped_even_by_filters(monitored, tmp_path, mutation):
    snapshot = record_health(monitored, tmp_path, now=NOW)
    path = tmp_path / (snapshot["id"] + ".json")
    if mutation == "json":
        path.write_text("{broken", encoding="utf-8")
    elif mutation == "size":
        path.write_bytes(b" " * (monitoring.MAX_REPORT_BYTES + 1))
    elif mutation == "duplicate":
        path.write_text('{"id":"x","id":"y"}', encoding="utf-8")
    else:
        if mutation == "checksum":
            snapshot["sha256"] = "bad"
        elif mutation == "version":
            snapshot["format_version"] = 2
        elif mutation == "id":
            snapshot["id"] += "a"
        elif mutation == "timestamp":
            snapshot["recorded_at"] = (NOW + timedelta(days=1)).isoformat()
        elif mutation == "ready":
            snapshot["report"]["ready"] = False
        elif mutation == "database":
            snapshot["report"]["database"] = []
        elif mutation == "extra":
            snapshot["unexpected"] = True
        if mutation != "checksum":
            payload = {key: value for key, value in snapshot.items() if key != "sha256"}
            snapshot["sha256"] = hashlib.sha256(monitoring._canonical(payload)).hexdigest()
        path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(ValueError):
        read_snapshot(tmp_path, path.stem)
    with pytest.raises(ValueError):
        history(tmp_path, status="critical")


def test_symlink_snapshot_rejected(monitored, tmp_path, monkeypatch):
    snapshot = record_health(monitored, tmp_path, now=NOW)
    # Avoid Windows symlink privilege requirements while exercising the policy branch.
    monkeypatch.setattr(type(tmp_path), "is_symlink", lambda self: True)
    with pytest.raises(ValueError, match="symbolic"):
        read_snapshot(tmp_path, snapshot["id"])


def test_cli_critical_is_archived_before_exit_one(config, tmp_path, monkeypatch):
    config.settings.database_url = f"sqlite:///{tmp_path / 'missing.db'}"
    monkeypatch.setattr("trading_radar.monitoring_cli.load_config", lambda _: config)
    directory = tmp_path / "history"
    result = CliRunner().invoke(app, ["record", "--history-dir", str(directory)])
    assert result.exit_code == 1, result.output
    snapshot = json.loads(result.output)
    assert snapshot["report"]["status"] == "critical"
    shown = CliRunner().invoke(app, ["show", snapshot["id"], "--history-dir", str(directory)])
    assert shown.exit_code == 0 and json.loads(shown.output) == snapshot
    listed = CliRunner().invoke(app, ["history", "--history-dir", str(directory)])
    assert listed.exit_code == 0 and json.loads(listed.output)["total"] == 1
    assert not (tmp_path / "missing.db").exists()


def test_cli_healthy_exit_zero(monitored, tmp_path, monkeypatch):
    monkeypatch.setattr("trading_radar.monitoring_cli.load_config", lambda _: monitored)
    monkeypatch.setattr("trading_radar.health.utcnow", lambda: NOW)
    result = CliRunner().invoke(app, ["record", "--history-dir", str(tmp_path / "history")])
    assert result.exit_code == 0, result.output


def test_cli_error_is_sanitized_and_exit_two(tmp_path, monkeypatch):
    def failure(_):
        raise ValueError("private local path and credentials")

    monkeypatch.setattr("trading_radar.monitoring_cli.load_config", failure)
    result = CliRunner().invoke(app, ["record", "--history-dir", str(tmp_path)])
    assert result.exit_code == 2
    assert json.loads(result.output) == {"error": "monitoring_failed", "error_type": "ValueError"}
    assert "private" not in result.output


def test_temp_files_are_not_reported(monitored, tmp_path):
    record_health(monitored, tmp_path, now=NOW)
    (tmp_path / ".health-interrupted.tmp").write_bytes(b"partial")
    assert history(tmp_path)["total"] == 1


@pytest.mark.parametrize(
    "before,after",
    [
        ("partial", "collection_degraded"),
        ("collection_degraded", "access_restricted"),
        ("access_restricted", "recent_failure"),
    ],
)
def test_warning_diagnostic_change_is_not_a_recovery(monitored, tmp_path, before, after):
    previous = record_health(monitored, tmp_path, now=NOW)
    current = record_health(monitored, tmp_path, now=NOW + timedelta(seconds=1))
    previous["report"]["sources"][0]["status"] = before
    current["report"]["sources"][0]["status"] = after
    assert compare_snapshots(previous, current)["source_changes"] == [
        {"source": "test", "before": before, "after": after, "change": "changed"}
    ]


def test_unknown_source_status_still_cannot_be_archived(monitored, tmp_path, monkeypatch):
    report = monitoring.check_health(monitored, now=NOW)
    report["sources"][0]["status"] = "invented"
    monkeypatch.setattr(monitoring, "check_health", lambda *args, **kwargs: report)
    with pytest.raises(ValueError, match="Invalid source health"):
        record_health(monitored, tmp_path / "history", now=NOW)
    assert not (tmp_path / "history").exists()
