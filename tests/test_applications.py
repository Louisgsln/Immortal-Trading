import csv
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from filelock import FileLock, Timeout
from typer.testing import CliRunner

from trading_radar.applications import ApplicationStatus
from trading_radar.cli import app
from trading_radar.export import export_csv
from trading_radar.storage import Repository


@pytest.fixture
def saved(repo, job):
    with repo.transaction():
        repo.upsert(job)
    return job


@pytest.mark.parametrize("status", list(ApplicationStatus))
def test_all_statuses_roundtrip(repo, saved, status):
    before = repo.get(saved.id).model_dump_json()
    result = repo.update_application(saved.id, {"status": status})
    assert result.status == status
    assert result.application_date is None  # Never invent an application date.
    assert repo.get(saved.id).model_dump_json() == before
    assert not repo.pending()


def test_edits_preserve_omitted_fields_and_history(repo, saved):
    first = repo.update_application(
        saved.id,
        {
            "status": "To Apply",
            "notes": "Vérifier le CV\nFX",
            "recruiter": "Public contact",
            "next_action": "Préparer le CV",
            "next_action_date": "2026-09-20",
        },
    )
    second = repo.update_application(
        saved.id, {"status": "Applied", "application_date": "2026-09-19"}
    )
    assert second.notes == first.notes and second.next_action == first.next_action
    history = repo.application_history(saved.id)
    assert len(history) == 2
    assert history[0]["before"]["status"] == "New"
    assert history[1]["before"] == history[0]["after"]
    assert history[1]["after"] == second.model_dump(mode="json")
    assert datetime.fromisoformat(history[0]["changed_at"]).tzinfo is not None
    repo.update_application(saved.id, {"status": "Applied"})
    assert len(repo.application_history(saved.id)) == 2
    cleared = repo.update_application(
        saved.id, {"notes": None, "next_action": None, "next_action_date": None}
    )
    assert cleared.notes is None and cleared.next_action_date is None
    assert cleared.recruiter == "Public contact"


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"job_id": "someone else"},
        {"score": 100},
        {"status": "Bogus"},
        {"status": None},
        {"application_date": "2026-02-30"},
        {"application_date": "17/09/2026"},
        {"application_date": "20260917"},
        {"application_date": 0},
        {"application_date": datetime(2026, 9, 17, tzinfo=UTC)},
        {"next_action_date": "2026-09-20"},
        {"notes": "x" * 20001},
    ],
)
def test_invalid_edits_write_nothing(repo, saved, changes):
    before = list(repo.db.iterdump())
    with pytest.raises(ValueError):
        repo.update_application(saved.id, changes)
    assert list(repo.db.iterdump()) == before


def test_unknown_job_and_lock_do_not_write(repo, saved):
    with pytest.raises(KeyError):
        repo.update_application("unknown", {"status": "Applied"})
    with FileLock(repo.lock_path, timeout=0), pytest.raises(Timeout):
        repo.update_application(saved.id, {"status": "Applied"})
    assert repo.application(saved.id).status == "New"
    assert not repo.application_history(saved.id)


def test_history_failure_rolls_back_edit(repo, saved):
    repo.db.execute("""CREATE TRIGGER fail_history BEFORE INSERT ON application_history
        BEGIN SELECT RAISE(ABORT, 'test rollback'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        repo.update_application(saved.id, {"status": "Applied"})
    assert repo.application(saved.id).status == "New"


def test_tracking_survives_update_closure_and_reopen(repo, saved):
    expected = repo.update_application(saved.id, {"status": "Interview", "notes": "Preparation"})
    with repo.transaction():
        incoming = saved.model_copy(deep=True)
        incoming.description_text += " New source content"
        repo.upsert(incoming)
        repo.reconcile(saved.source, set(), 1)
    assert not repo.application_details(saved.id)["job_active"]
    assert repo.application(saved.id) == expected
    with repo.transaction():
        repo.upsert(saved.model_copy(deep=True))
    assert repo.application(saved.id) == expected
    assert repo.application_details(saved.id)["job_active"]
    repo.update_application(saved.id, {"status": "Closed"})
    assert repo.get(saved.id).is_active  # Application status is not source closure.


def test_due_filters_order_and_pagination(repo, saved):
    repo.update_application(saved.id, {"next_action": "Prepare", "next_action_date": "2026-09-20"})
    assert not repo.list_applications(due_before="2026-09-19")
    assert repo.list_applications(due_before="2026-09-20")[0]["job_id"] == saved.id
    assert not repo.list_applications(status=ApplicationStatus.APPLIED)
    assert not repo.list_applications(offset=1)
    with pytest.raises(ValueError):
        repo.list_applications(limit=0)
    with pytest.raises(ValueError):
        repo.list_applications(due_before="yesterday")


def test_export_tracking_sanitizes_spreadsheet_formulas(repo, saved, tmp_path):
    repo.update_application(
        saved.id,
        {
            "notes": "=1+1",
            "recruiter": "@contact",
            "next_action": "+formula",
            "next_action_date": "2026-09-20",
            "status": "Reviewing",
        },
    )
    target = tmp_path / "jobs.csv"
    export_csv(repo, target)
    with target.open(encoding="utf-8-sig", newline="") as f:
        row = next(csv.DictReader(f))
    assert row["job_id"] == saved.id and row["status"] == "Reviewing"
    assert row["notes"] == "'=1+1" and row["recruiter"] == "'@contact"
    assert row["next_action"] == "'+formula" and row["next_action_date"] == "2026-09-20"
    assert repo.application(saved.id).notes == "=1+1"


def test_migrate_version_two_keeps_tracking(repo, saved, tmp_path):
    with repo.db:
        repo.db.execute(
            "UPDATE applications SET status='Applied',notes='Existing note' WHERE job_id=?",
            (saved.id,),
        )
        repo.db.execute("DROP TABLE application_history")
        repo.db.execute("DELETE FROM schema_version WHERE version>=3")
    upgraded = Repository(f"sqlite:///{tmp_path / 'jobs.db'}")
    try:
        assert upgraded.application(saved.id).status == "Applied"
        assert upgraded.application(saved.id).notes == "Existing note"
        assert not upgraded.application_history(saved.id)
        assert upgraded.db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 4
    finally:
        upgraded.close()


@pytest.fixture
def cli_env(tmp_path, monkeypatch, job):
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/jobs.db")
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    repo = Repository("sqlite:///data/jobs.db")
    with repo.transaction():
        repo.upsert(job)
    repo.close()
    return job.id


def test_cli_tracking_workflow_without_telegram(cli_env):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "applications",
            "update",
            cli_env,
            "--status",
            "To Apply",
            "--notes",
            "Relire le CV",
            "--next-action",
            "Préparer",
            "--next-action-date",
            "2026-09-20",
        ],
    )
    assert result.exit_code == 0, result.output
    listed = runner.invoke(
        app, ["applications", "list", "--due-before", "2026-09-20", "--status", "To Apply"]
    )
    assert listed.exit_code == 0 and json.loads(listed.output)[0]["notes"] == "Relire le CV"
    shown = runner.invoke(app, ["applications", "show", cli_env])
    assert json.loads(shown.output)["job_active"]
    result = runner.invoke(
        app,
        [
            "applications",
            "update",
            cli_env,
            "--clear",
            "next_action",
            "--clear",
            "next_action_date",
        ],
    )
    assert result.exit_code == 0 and json.loads(result.output)["next_action"] is None
    history = runner.invoke(app, ["applications", "history", cli_env])
    assert len(json.loads(history.output)) == 2


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--status", "Nope"],
        ["--notes", "New", "--clear", "notes"],
        ["--next-action-date", "2026-09-20"],
        ["--application-date", "2026-02-30"],
    ],
)
def test_cli_rejects_invalid_patch(cli_env, args):
    result = CliRunner().invoke(app, ["applications", "update", cli_env, *args])
    assert result.exit_code != 0
    result = CliRunner().invoke(app, ["applications", "history", cli_env])
    assert json.loads(result.output) == []


def test_cli_unknown_and_locked_job(cli_env):
    runner = CliRunner()
    result = runner.invoke(app, ["applications", "show", "unknown"])
    assert result.exit_code == 1 and "Unknown job ID" in result.output
    with FileLock("data/jobs.db.lock"):
        result = runner.invoke(app, ["applications", "update", cli_env, "--status", "Applied"])
    assert result.exit_code == 1 and "busy" in result.output


def test_cli_demo_isolation(cli_env):
    result = CliRunner().invoke(app, ["applications", "list", "--demo"])
    assert result.exit_code == 0 and json.loads(result.output) == []
    result = CliRunner().invoke(app, ["applications", "show", cli_env])
    assert result.exit_code == 0
