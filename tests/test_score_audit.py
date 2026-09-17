import json

import pytest
from typer.testing import CliRunner

from trading_radar import cli, score_audit
from trading_radar.cli import app
from trading_radar.score_audit import build_score_audit
from trading_radar.scoring import score_job


def rows(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


@pytest.fixture
def audit_config(repo, config):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    return config


def test_preview_matches_recalculation_without_touching_database(audit_config, repo, job):
    job.score_breakdown.trading = 0
    with repo.transaction():
        repo.upsert(job)
    repo.update_application(job.id, {"notes": "PRIVATE_NOTE", "recruiter": "PRIVATE_CONTACT"})
    before = rows(repo)
    report = build_score_audit(audit_config)
    assert report["status"] == "ok" and report["read_only"] is True
    assert report["evaluated"] == report["changed"] == report["score_changed"] == 1
    assert report["changes"][0]["before"]["score"] == job.score_breakdown.total
    assert (
        report["changes"][0]["after"]["score"]
        == score_job(job, audit_config.keywords).score_breakdown.total
    )
    assert "PRIVATE_NOTE" not in json.dumps(report) and "PRIVATE_CONTACT" not in json.dumps(report)
    assert rows(repo) == before
    with repo.transaction():
        assert repo.update_scoring(job)
    assert build_score_audit(audit_config)["changed"] == 0


def test_explanation_only_change_and_inactive_counts(audit_config, repo, job):
    job.is_active = False
    job.score_breakdown.reasons.append("Obsolete explanation")
    with repo.transaction():
        repo.upsert(job)
    report = build_score_audit(audit_config)
    assert report["changed"] == 1 and report["score_changed"] == 0
    assert report["before"]["active"] == report["after"]["high_priority"] == 0


def test_empty_database_is_success(audit_config):
    report = build_score_audit(audit_config)
    assert report["status"] == "ok" and report["evaluated"] == report["changed"] == 0


def test_missing_database_is_never_created(config, tmp_path):
    target = tmp_path / "absent" / "missing.db"
    config.settings.database_url = f"sqlite:///{target}"
    report = build_score_audit(config)
    assert report["error"]["code"] == "missing" and not target.parent.exists()


@pytest.mark.parametrize(
    "url", ["sqlite:///:memory:", "sqlite:///", "postgres://host/db", "sqlite:///bad\0path"]
)
def test_invalid_database_configuration(config, url):
    config.settings.database_url = url
    assert build_score_audit(config)["error"]["code"] == "invalid_config"


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("UPDATE jobs SET score=999", "invalid_data"),
        ("UPDATE jobs SET payload='PRIVATE_INVALID_JSON'", "invalid_data"),
        ("INSERT INTO schema_version VALUES(99)", "incompatible"),
        ("CREATE TABLE unrelated(a TEXT)", "incompatible"),
    ],
)
def test_bad_database_returns_no_partial_comparison(audit_config, repo, job, mutation, code):
    with repo.transaction():
        repo.upsert(job)
        repo.db.execute(mutation)
    before = rows(repo)
    report = build_score_audit(audit_config)
    assert report["status"] == "error" and report["error"]["code"] == code
    assert report["changes"] == [] and report["before"] == {} and report["after"] == {}
    assert "PRIVATE_INVALID_JSON" not in json.dumps(report)
    assert rows(repo) == before


@pytest.mark.parametrize("limit,value", [("MAX_JOBS", 0), ("MAX_PAYLOAD", 10)])
def test_limits_refuse_partial_results(audit_config, repo, job, monkeypatch, limit, value):
    with repo.transaction():
        repo.upsert(job)
    monkeypatch.setattr(score_audit, limit, value)
    assert build_score_audit(audit_config)["error"]["code"] == "limit_exceeded"


def test_corrupt_file_safe_error(config, tmp_path):
    path = tmp_path / "broken.db"
    path.write_bytes(b"PRIVATE_NON_DATABASE")
    config.settings.database_url = f"sqlite:///{path}"
    report = build_score_audit(config)
    assert report["error"]["code"] == "corrupt"
    assert "PRIVATE" not in json.dumps(report)
    assert path.read_bytes() == b"PRIVATE_NON_DATABASE"


def test_read_error_does_not_leak_paths(audit_config, monkeypatch):
    def broken(*args):
        raise OSError("PRIVATE_PATH")

    monkeypatch.setattr(score_audit, "_read", broken)
    assert build_score_audit(audit_config)["error"]["code"] == "unreadable"
    assert "PRIVATE_PATH" not in json.dumps(build_score_audit(audit_config))


def test_wal_reader_remains_coherent_during_concurrent_update(audit_config, repo, job, monkeypatch):
    with repo.transaction():
        repo.upsert(job)
    original = score_audit._schema
    calls = 0

    def observe(db):
        nonlocal calls
        result = original(db)
        calls += 1
        if calls == 1:
            with repo.transaction():
                repo.db.execute("UPDATE jobs SET score=999")
        return result

    monkeypatch.setattr(score_audit, "_schema", observe)
    assert build_score_audit(audit_config)["status"] == "ok"
    monkeypatch.setattr(score_audit, "_schema", original)
    assert build_score_audit(audit_config)["status"] == "error"


def test_cli_dry_run_never_initializes_resources_or_writes_exports(
    audit_config, repo, job, monkeypatch, tmp_path
):
    with repo.transaction():
        repo.upsert(job)
    monkeypatch.setattr(cli, "load_config", lambda _: audit_config)

    def forbidden(*args):
        pytest.fail("Dry run must never open a writer or initialize notifier")

    monkeypatch.setattr(cli, "resources", forbidden)
    monkeypatch.setattr(cli, "export_csv", forbidden)
    monkeypatch.chdir(tmp_path)
    before = rows(repo)
    response = CliRunner().invoke(app, ["rescore", "--dry-run"])
    assert response.exit_code == 0, response.output
    assert json.loads(response.output)["evaluated"] == 1
    assert rows(repo) == before
    assert not (tmp_path / "data").exists()


def test_cli_demo_dry_run_uses_only_existing_demo(config, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "load_config", lambda _: config)
    monkeypatch.chdir(tmp_path)
    response = CliRunner().invoke(app, ["rescore", "--demo", "--dry-run"])
    assert response.exit_code == 1
    assert json.loads(response.output)["error"]["code"] == "missing"
    assert not (tmp_path / "data").exists()


def test_cli_invalid_configuration_safe_error(monkeypatch):
    def broken(*args):
        raise ValueError("PRIVATE_CONFIGURATION")

    monkeypatch.setattr(cli, "load_config", broken)
    response = CliRunner().invoke(app, ["rescore", "--dry-run"])
    assert response.exit_code == 1 and "PRIVATE_CONFIGURATION" not in response.output
    assert json.loads(response.output)["error"]["code"] == "invalid_configuration"
