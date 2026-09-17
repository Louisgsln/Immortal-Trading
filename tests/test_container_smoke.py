"""Local workflow checks; only Docker CI validates the actual runtime image."""

import importlib.util
import json
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "smoke_container", PROJECT / "scripts/smoke_container.py"
)
assert SPEC and SPEC.loader
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def test_isolated_smoke_preserves_operator_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///must-not-be-created.db")
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "synthetic-unusable-token")
    report = smoke.run_smoke(PROJECT, tmp_path, local=True)
    assert report["status"] == "ok"
    assert report["mode"] == "local_workflow_only"
    assert report["synthetic_jobs"] == 8
    assert report["preview_new_jobs"] == 8
    assert report["identical_tables"] == 11
    assert report["health_snapshots"] == 1
    assert report["dashboard_jobs"] == 8
    assert report["trends_scans"] == 2
    assert report["retention_verified"] == 1
    assert report["table_counts"]["application_history"] == 1
    assert report["table_counts"]["alert_history"] == 2
    assert report["table_counts"]["alerts"] == 1
    work = Path(report["directory"])
    assert work.parent == tmp_path
    assert json.loads((work / "report.json").read_text(encoding="utf-8")) == report
    assert not (work / "must-not-be-created.db").exists()


def test_container_smoke_refuses_root_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke.os, "getuid", lambda: 0, raising=False)
    with pytest.raises(RuntimeError, match="unprivileged"):
        smoke.run_smoke(PROJECT, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_snapshot_refuses_a_missing_database(tmp_path):
    import sqlite3

    missing = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        smoke.snapshot(missing)
    assert not missing.exists()
