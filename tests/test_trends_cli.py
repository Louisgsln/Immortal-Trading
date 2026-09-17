import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from trading_radar import trends_cli
from trading_radar.cli import app
from trading_radar.notifications import TelegramNotifier

RUNNER = CliRunner()


@pytest.mark.parametrize("days", [1, 30, 365])
def test_command_passes_options_and_emits_only_json(config, monkeypatch, days):
    seen = []
    report = {"status": "ok", "error": None, "days": days, "label": "Évolution"}

    def load(directory):
        assert directory == Path("custom-config")
        return config

    def build(supplied, *, days):
        assert supplied is config
        seen.append(days)
        return report

    monkeypatch.setattr(trends_cli, "load_config", load)
    monkeypatch.setattr(trends_cli, "build_trends", build)
    result = RUNNER.invoke(app, ["trends", "--config-dir", "custom-config", "--days", str(days)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == report
    assert "Évolution" in result.stdout
    assert not result.stderr
    assert seen == [days]


def test_default_window_is_thirty_days(config, monkeypatch):
    seen = []
    monkeypatch.setattr(trends_cli, "load_config", lambda _: config)

    def build(supplied, *, days):
        seen.append(days)
        return {"status": "ok", "days": days}

    monkeypatch.setattr(trends_cli, "build_trends", build)
    result = RUNNER.invoke(app, ["trends"])
    assert result.exit_code == 0, result.output
    assert seen == [30]


@pytest.mark.parametrize("days", ["0", "-1", "366", "1.5", "invalid"])
def test_invalid_window_is_rejected_before_configuration(monkeypatch, days):
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid CLI arguments must not read configuration or the database")

    monkeypatch.setattr(trends_cli, "load_config", unexpected)
    monkeypatch.setattr(trends_cli, "build_trends", unexpected)
    result = RUNNER.invoke(app, ["trends", "--days", days])
    assert result.exit_code == 2


def test_business_error_is_json_and_exit_one(config, monkeypatch):
    report = {"status": "error", "error": {"code": "missing", "message": "Base absente."}}
    monkeypatch.setattr(trends_cli, "load_config", lambda _: config)
    monkeypatch.setattr(trends_cli, "build_trends", lambda *args, **kwargs: report)
    result = RUNNER.invoke(app, ["trends"])
    assert result.exit_code == 1
    assert json.loads(result.stdout) == report
    assert not result.stderr


@pytest.mark.parametrize(
    "failure",
    [OSError, ValueError, KeyError, TypeError, yaml.YAMLError],
)
def test_configuration_errors_do_not_leak_details(monkeypatch, failure):
    def broken(_):
        raise failure("private-token-and-local-path")

    monkeypatch.setattr(trends_cli, "load_config", broken)
    result = RUNNER.invoke(app, ["trends"])
    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert report["status"] == "error"
    assert report["error"]["code"] == "invalid_configuration"
    assert "private-token" not in result.output
    assert not result.stderr


@pytest.mark.parametrize("settings", ["database_url: [", "- secret-setting", "timeout: -1"])
def test_real_malformed_configuration_fails_cleanly(tmp_path, monkeypatch, settings):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALERTS_ENABLED", raising=False)
    (tmp_path / "settings.yaml").write_text(settings, encoding="utf-8")
    (tmp_path / "companies.yaml").write_text("companies: {}", encoding="utf-8")
    (tmp_path / "keywords.yaml").write_text("{}", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = RUNNER.invoke(app, ["trends", "--config-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "invalid_configuration"
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_missing_configuration_directory_is_not_created(tmp_path):
    destination = tmp_path / "absent-config"
    result = RUNNER.invoke(app, ["trends", "--config-dir", str(destination)])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "invalid_configuration"
    assert not destination.exists()


def test_missing_database_remains_missing(config, tmp_path, monkeypatch):
    destination = tmp_path / "absent-data" / "jobs.db"
    config.settings.database_url = f"sqlite:///{destination}"
    monkeypatch.setattr(trends_cli, "load_config", lambda _: config)
    result = RUNNER.invoke(app, ["trends"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["status"] == "error"
    assert not destination.parent.exists()


def test_real_report_preserves_database_and_never_initializes_notifications(
    config, repo, job, monkeypatch
):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    job.first_seen = job.last_seen = datetime.now(UTC)
    with repo.transaction():
        repo.upsert(job)
    before = list(repo.db.iterdump())
    monkeypatch.setattr(trends_cli, "load_config", lambda _: config)

    def forbidden(*args, **kwargs):
        pytest.fail("The trends command must not initialize notification transports")

    monkeypatch.setattr(TelegramNotifier, "from_env", forbidden)
    result = RUNNER.invoke(app, ["trends", "--days", "1"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "ok"
    assert report["timezone"] == "UTC"
    assert report["days"] == 1
    assert len(report["daily"]) == 1
    assert report["summary"]["new_jobs"] == 1
    assert report["daily"][0]["new_jobs"] == 1
    assert list(repo.db.iterdump()) == before
