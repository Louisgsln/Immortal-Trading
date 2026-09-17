import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trading_radar.cli import app


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "config", tmp_path / "config")
    shutil.copytree(root / "tests/fixtures", tmp_path / "tests/fixtures")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/active.db")
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")

    def prohibited(*args, **kwargs):
        pytest.fail("Preview must not construct a notifier or open normal CLI resources")

    monkeypatch.setattr("trading_radar.cli.TelegramNotifier.from_env", prohibited)
    monkeypatch.setattr("trading_radar.cli.resources", prohibited)
    return tmp_path


def test_demo_preview_repeated_without_creating_database_or_exports(workspace):
    reports = []
    for _ in range(2):
        result = CliRunner().invoke(app, ["scan", "--demo", "--dry-run"])
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        assert report["status"] == "ok"
        assert report["read_only"] and report["ephemeral_new_ids"]
        assert report["metrics"]["new"] == 8
        assert len(report["changes"]) == 8
        assert all(change["before_score"] is None for change in report["changes"])
        reports.append(report)
    assert not (workspace / "data").exists()
    assert {c["id"] for c in reports[0]["changes"]}.isdisjoint(
        c["id"] for c in reports[1]["changes"]
    )


def test_no_matching_source_is_json_error_and_does_not_create_database(workspace):
    result = CliRunner().invoke(app, ["scan", "--dry-run", "--source", "absent"])
    assert result.exit_code == 2, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "error"
    assert report["error"]["code"] == "no_sources"
    assert report["changes"] == []
    assert not (workspace / "data").exists()


@pytest.mark.parametrize("status,exit_code", [("ok", 0), ("incomplete", 1), ("error", 1)])
def test_preview_routes_filters_and_returns_structured_status(
    workspace, monkeypatch, status, exit_code
):
    async def preview(config, **kwargs):
        assert config.settings.alerts_enabled
        assert kwargs == {"company": "Flow Traders", "source": "flow_traders", "collectors": None}
        return {
            "status": status,
            "read_only": True,
            "changes": [],
            "metrics": {"sources": 1} if status != "error" else None,
            "error": None,
        }

    monkeypatch.setattr("trading_radar.scan_preview.preview_scan", preview)
    result = CliRunner().invoke(
        app, ["scan", "--dry-run", "--company", "Flow Traders", "--source", "flow_traders"]
    )
    assert result.exit_code == exit_code, result.output
    assert json.loads(result.stdout)["status"] == status
    assert not (workspace / "data").exists()


def test_configuration_error_is_sanitized_json(workspace, monkeypatch):
    def fail(*args):
        raise ValueError("private-configuration-secret")

    monkeypatch.setattr("trading_radar.cli.runtime_config", fail)
    result = CliRunner().invoke(app, ["scan", "--dry-run"])
    assert result.exit_code == 1
    assert "private-configuration-secret" not in result.output
    report = json.loads(result.stdout)
    assert report["error"]["code"] == "invalid_configuration"
    assert report["read_only"] and report["changes"] == []
