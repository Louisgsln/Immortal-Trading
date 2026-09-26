import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest

from trading_radar.config import Company
from trading_radar.models import Collection
from trading_radar.scanner import scan
from trading_radar.source_history import source_history

NOW = datetime(2026, 9, 26, 20, tzinfo=UTC)


@pytest.fixture(autouse=True)
def database(config, repo, tmp_path):
    config.settings.database_url = "sqlite:///" + (tmp_path / "jobs.db").as_posix()


def record(repo, status="successful", at=NOW, **changes):
    value = {"completed_at": at.isoformat(), "status": status, "duration": 2.5, **changes}
    metrics = {
        "sources": 1,
        "source_results": {"test": value},
        "failed": {"test": "HTTP 429 secret-url"},
    }
    repo.db.execute(
        "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)",
        (at.isoformat(), json.dumps(metrics)),
    )
    repo.db.commit()


def test_counts_cutoff_incidents_and_read_only(config, repo):
    for status in ("successful", "failed", "partial", "degraded"):
        record(repo, status)
    record(repo, at=NOW - timedelta(hours=25))
    record(repo, at=NOW + timedelta(seconds=1))
    repo.db.execute(
        "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)",
        (NOW.isoformat(), '{"sources": 1, "successful": 1}'),
    )
    repo.db.commit()
    before = repo.db.total_changes
    result = source_history(config, NOW)
    assert result["legacy_scans"] == 1
    observed = result["sources"]["test"]
    assert observed["attempts"] == 4 and observed["success_rate"] == 25
    assert observed["average_seconds"] == 2.5
    assert set(observed["counts"]) == {"successful", "failed", "partial", "degraded"}
    assert "secret-url" not in json.dumps(result)
    assert "rate_limited" in json.dumps(result)
    assert repo.db.total_changes == before


@pytest.mark.parametrize(
    "changes",
    [
        {"duration": -1},
        {"duration": float("nan")},
        {"duration": True},
        {"duration": "2"},
        {"status": "invented"},
        {"status": []},
        {"completed_at": "2026-09-26"},
        {"completed_at": (NOW + timedelta(seconds=1)).isoformat()},
    ],
)
def test_invalid_observation_never_returns_partial_ratios(config, repo, changes):
    record(repo)
    record(repo, **changes)
    result = source_history(config, NOW)
    assert result["status"] == "unavailable" and result["sources"] == {}


def test_bounded_read_and_latest_five(config, repo, monkeypatch):
    for minute in range(8):
        record(repo, at=NOW - timedelta(minutes=minute))
    result = source_history(config, NOW)["sources"]["test"]
    assert result["attempts"] == 8 and len(result["latest"]) == 5
    assert result["latest"][0]["at"] == NOW.isoformat()
    monkeypatch.setattr("trading_radar.source_history.MAX_ROWS", 3)
    assert source_history(config, NOW)["status"] == "unavailable"


def test_empty_legacy_and_unknown_sources(config, repo):
    assert source_history(config, NOW)["sources"] == {}
    record(repo)
    del config.companies["test"]
    assert source_history(config, NOW)["sources"] == {}


def test_scanner_records_attributed_success_failure_and_skips(config, repo, raw):
    class Collector:
        async def collect(self):
            return Collection(jobs=[raw], complete=False)

    class Failed:
        async def collect(self):
            raise ValueError("private")

    config.companies["failed"] = Company(name="Failed", ats="fixture", enabled=True)
    result = asyncio.run(scan(config, repo, collectors={"test": Collector(), "failed": Failed()}))
    assert result.source_results["test"]["status"] == "successful"
    assert result.source_results["failed"]["status"] == "failed"
    history = source_history(config, datetime.now(UTC))
    assert history["sources"]["test"]["attempts"] == 1
    assert history["sources"]["failed"]["success_rate"] == 0
    skipped = asyncio.run(scan(config, repo, due_only=True, collectors={"test": Collector()}))
    assert skipped.source_results == {} and skipped.sources == 0


def test_oversized_record_and_missing_database(config, repo, monkeypatch, tmp_path):
    record(repo)
    monkeypatch.setattr("trading_radar.source_history.MAX_LENGTH", 5)
    assert source_history(config, NOW)["status"] == "unavailable"
    config.settings.database_url = "sqlite:///" + (tmp_path / "missing.db").as_posix()
    assert source_history(config, NOW)["status"] == "unavailable"
    assert not (tmp_path / "missing.db").exists()
