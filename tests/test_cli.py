import shutil
from pathlib import Path

from typer.testing import CliRunner

from trading_radar.cli import app


def test_cli_demo_roundtrip(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    shutil.copytree(root / "tests/fixtures", tmp_path / "tests/fixtures")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    first = runner.invoke(app, ["scan", "--demo"])
    assert first.exit_code == 0, first.output
    assert '"new": 8' in first.output
    second = runner.invoke(app, ["scan", "--demo"])
    assert second.exit_code == 0 and '"new": 0' in second.output
    listed = runner.invoke(app, ["list", "--demo", "--min-score", "85"])
    assert listed.exit_code == 0 and "Demo Bank" in listed.output
    assert (tmp_path / "data/demo.csv").exists()
    assert not (tmp_path / "data/jobs.db").exists()
    stats = runner.invoke(app, ["stats", "--demo"])
    assert stats.exit_code == 0 and '"total": 8' in stats.output
    rescored = runner.invoke(app, ["rescore", "--demo"])
    assert rescored.exit_code == 0 and '"rescored": 0' in rescored.output


def test_doctor_offline(tmp_path, monkeypatch):
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALERTS_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/test.db")
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 0 and '"database": "ok"' in result.output
    assert '"disabled"' in result.output and "HTTP 403" in result.output


def test_no_enabled_source_returns_failure(tmp_path, monkeypatch):
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    (tmp_path / "config/companies.yaml").write_text("companies: {}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALERTS_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/test.db")
    result = CliRunner().invoke(app, ["scan"])
    assert result.exit_code == 2
