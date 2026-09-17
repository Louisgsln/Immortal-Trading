"""CLI contract for the read-only retention audit; policy tests live with its engine."""

import json
import sqlite3
from pathlib import Path
from zipfile import BadZipFile, LargeZipFile

import pytest
from typer.testing import CliRunner

from trading_radar import backup_cli, cli


@pytest.fixture
def report(tmp_path):
    return {
        "format_version": 1,
        "generated_at": "2026-09-17T12:00:00+00:00",
        "directory": str(tmp_path),
        "policy": {"keep_latest": 7, "keep_daily": 14, "keep_weekly": 8},
        "status": "ok",
        "entries": [
            {
                "name": "latest.zip",
                "status": "valid",
                "created_at": "2026-09-17T10:00:00+00:00",
                "bytes": 100,
                "sha256": "a" * 64,
                "decision": "keep",
                "reasons": ["latest", "daily", "weekly"],
            },
            {
                "name": "old.zip",
                "status": "valid",
                "created_at": "2025-01-01T10:00:00+00:00",
                "bytes": 90,
                "sha256": "b" * 64,
                "decision": "candidate",
                "reasons": ["outside_retention"],
            },
        ],
        "summary": {
            "archives": 2,
            "valid": 2,
            "invalid": 0,
            "kept": 1,
            "candidates": 1,
            "bytes_total": 190,
            "candidate_bytes": 90,
        },
        "deletion_performed": False,
    }


def test_json_preserves_complete_engine_report_and_default_policy(report, tmp_path, monkeypatch):
    calls = []

    def audit(directory, **policy):
        calls.append((directory, policy))
        return report

    monkeypatch.setattr(backup_cli, "plan_retention", audit)
    result = CliRunner().invoke(cli.app, ["backup", "plan", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == report
    assert result.stderr == ""
    assert calls == [(tmp_path, {"keep_latest": 7, "keep_daily": 14, "keep_weekly": 8})]


def test_human_report_names_candidates_and_reasons(report, tmp_path, monkeypatch):
    monkeypatch.setattr(backup_cli, "plan_retention", lambda *a, **kw: report)
    result = CliRunner().invoke(cli.app, ["backup", "plan", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "candidates: 1" in result.stdout
    assert "candidate bytes: 90" in result.stdout
    assert 'candidate: "old.zip" (outside_retention)' in result.stdout
    assert 'keep: "latest.zip" (latest, daily, weekly)' in result.stdout
    assert "No file was deleted or moved" in result.stdout


def test_custom_policy_passed_without_config_database_or_network(report, tmp_path, monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        raise AssertionError("Retention planning must stay offline and independent of config")

    def audit(directory, **policy):
        calls.append((directory, policy))
        return report

    monkeypatch.setattr(backup_cli, "plan_retention", audit)
    monkeypatch.setattr(backup_cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "Repository", forbidden)
    monkeypatch.setattr(cli.HTTPClient, "__init__", forbidden)
    monkeypatch.setattr(cli.TelegramNotifier, "from_env", forbidden)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    result = CliRunner().invoke(
        cli.app,
        [
            "backup",
            "plan",
            ".",
            "--keep-latest",
            "1",
            "--keep-daily",
            "0",
            "--keep-weekly",
            "104",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls == [(Path("."), {"keep_latest": 1, "keep_daily": 0, "keep_weekly": 104})]


@pytest.mark.parametrize("json_output", [True, False])
def test_blocked_report_is_printed_with_failure_exit(report, tmp_path, monkeypatch, json_output):
    report["status"] = "blocked"
    report["entries"][1].update(
        status="invalid", decision="blocked", reasons=["invalid_archive"], error="invalid_backup"
    )
    report["summary"].update(valid=1, invalid=1, candidates=0, candidate_bytes=0)
    monkeypatch.setattr(backup_cli, "plan_retention", lambda *a, **kw: report)
    args = ["backup", "plan", str(tmp_path)] + (["--json"] if json_output else [])
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 1
    if json_output:
        assert json.loads(result.stdout) == report
    else:
        assert 'blocked: "old.zip" (invalid_archive)' in result.stdout
        assert "candidates: 0" in result.stdout
    assert result.stderr == ""


def test_empty_report_is_successful(report, tmp_path, monkeypatch):
    report.update(status="empty", entries=[])
    report["summary"] = dict.fromkeys(report["summary"], 0)
    monkeypatch.setattr(backup_cli, "plan_retention", lambda *a, **kw: report)
    result = CliRunner().invoke(cli.app, ["backup", "plan", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == report


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--keep-latest", "0"),
        ("--keep-latest", "101"),
        ("--keep-daily", "-1"),
        ("--keep-daily", "366"),
        ("--keep-weekly", "-1"),
        ("--keep-weekly", "105"),
        ("--apply", None),
    ],
)
def test_invalid_or_mutating_option_never_calls_engine(option, value, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid CLI options must fail before opening any directory")

    monkeypatch.setattr(backup_cli, "plan_retention", forbidden)
    args = ["backup", "plan", str(tmp_path), option] + ([] if value is None else [value])
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 2


@pytest.mark.parametrize(
    "exception", [ValueError, OSError, PermissionError, sqlite3.Error, BadZipFile, LargeZipFile]
)
def test_fatal_error_is_sanitized_without_traceback(exception, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise exception("private-token-from-exception")

    monkeypatch.setattr(backup_cli, "plan_retention", fail)
    result = CliRunner().invoke(cli.app, ["backup", "plan", str(tmp_path), "--json"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert f"Backup retention audit failed ({exception.__name__})." in result.stderr
    assert "private-token" not in result.output
    assert "Traceback" not in result.output


def test_human_output_escapes_control_characters_in_filenames(report, tmp_path, monkeypatch):
    report["entries"][1]["name"] = "old\n\x1b[31m.zip"
    monkeypatch.setattr(backup_cli, "plan_retention", lambda *a, **kw: report)
    result = CliRunner().invoke(cli.app, ["backup", "plan", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert '"old\\n\\u001b[31m.zip"' in result.stdout
    assert "old\n" not in result.stdout
