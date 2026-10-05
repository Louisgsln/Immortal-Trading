import json
from uuid import uuid4

import pytest
from filelock import FileLock, Timeout
from typer.testing import CliRunner

from trading_radar.application_import import apply_import, preview_import, read_import
from trading_radar.backups import verify_backup
from trading_radar.cli import app
from trading_radar.storage import Repository


@pytest.fixture
def saved(config, repo, job, tmp_path):
    config.settings.database_url = "sqlite:///" + str(tmp_path / "jobs.db")
    other = job.model_copy(
        update={
            "id": str(uuid4()),
            "fingerprint": "other",
            "external_id": "other",
            "apply_url": job.apply_url + "-other",
        }
    )
    with repo.transaction():
        repo.upsert(job)
        repo.upsert(other)
    return job, other


def input_file(tmp_path, edits):
    path = tmp_path / "tracking.json"
    path.write_text(json.dumps({"format_version": 1, "applications": edits}), encoding="utf-8")
    return path


def test_preview_and_apply_preserve_omissions_history_facts_and_verified_backup(
    config, repo, saved, tmp_path
):
    first, second = saved
    repo.update_application(first.id, {"notes": "Keep these notes"})
    facts = [job.model_dump_json() for job in repo.list_jobs()]
    path = input_file(
        tmp_path,
        [
            {"job_id": first.id, "status": "Applied"},
            {"job_id": second.id, "next_action": "Review", "next_action_date": "2026-10-10"},
        ],
    )
    before = list(repo.db.iterdump())
    plan = preview_import(config, path)
    assert plan["changed"] == 2 and plan["read_only"]
    assert list(repo.db.iterdump()) == before
    backup = tmp_path / "reviewed-backup.zip"
    result = apply_import(config, path, plan["preview_token"], backup)
    assert result["changed"] == 2 and not result["read_only"]
    assert verify_backup(backup)["sha256"] == result["backup_sha256"]
    assert repo.application(first.id).notes == "Keep these notes"
    assert repo.application(first.id).application_date is None
    assert len(repo.application_history(first.id)) == 2
    assert len(repo.application_history(second.id)) == 1
    assert [job.model_dump_json() for job in repo.list_jobs()] == facts
    assert not repo.pending()
    noop = preview_import(config, path)
    assert noop["changed"] == 0
    assert apply_import(config, path, noop["preview_token"], backup)["backup"] is None
    assert len(repo.application_history(second.id)) == 1


@pytest.mark.parametrize("change_input", [False, True])
def test_stale_preview_refuses_to_overwrite_new_edits(config, repo, saved, tmp_path, change_input):
    first, _ = saved
    path = input_file(tmp_path, [{"job_id": first.id, "status": "Applied"}])
    plan = preview_import(config, path)
    if change_input:
        input_file(tmp_path, [{"job_id": first.id, "status": "Rejected"}])
    else:
        repo.update_application(first.id, {"notes": "Edited after preview"})
    before = list(repo.db.iterdump())
    with pytest.raises(ValueError, match="preview again"):
        apply_import(config, path, plan["preview_token"], tmp_path / "backup.zip")
    assert list(repo.db.iterdump()) == before
    assert not (tmp_path / "backup.zip").exists()


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "Unknown"},
        {"status": None},
        {"application_date": "2026-02-30"},
        {"next_action_date": "2026-10-10"},
        {"score": 100},
        {"notes": {"secret": "value"}},
    ],
)
def test_invalid_late_row_never_commits_an_earlier_row(config, repo, saved, tmp_path, bad):
    first, second = saved
    path = input_file(
        tmp_path, [{"job_id": first.id, "status": "Applied"}, {"job_id": second.id, **bad}]
    )
    before = list(repo.db.iterdump())
    with pytest.raises(ValueError):
        preview_import(config, path)
    assert list(repo.db.iterdump()) == before


def test_batch_failure_rolls_back_all_edits_and_history(config, repo, saved, tmp_path, monkeypatch):
    first, second = saved
    path = input_file(
        tmp_path,
        [{"job_id": first.id, "status": "Applied"}, {"job_id": second.id, "status": "Applied"}],
    )
    plan = preview_import(config, path)
    before = list(repo.db.iterdump())
    original = Repository.record_application_update

    def fail_second(self, job_id, changes):
        if job_id == second.id:
            raise ValueError("Synthetic failure")
        return original(self, job_id, changes)

    monkeypatch.setattr(Repository, "record_application_update", fail_second)
    with pytest.raises(ValueError):
        apply_import(config, path, plan["preview_token"], tmp_path / "backup.zip")
    assert list(repo.db.iterdump()) == before
    assert verify_backup(tmp_path / "backup.zip")


def test_busy_writer_and_failed_backup_commit_nothing(config, repo, saved, tmp_path):
    first, _ = saved
    path = input_file(tmp_path, [{"job_id": first.id, "status": "Applied"}])
    plan = preview_import(config, path)
    before = list(repo.db.iterdump())
    with FileLock(repo.lock_path), pytest.raises(Timeout):
        apply_import(config, path, plan["preview_token"], tmp_path / "backup.zip")
    with pytest.raises(ValueError):
        apply_import(config, path, plan["preview_token"], path)
    assert list(repo.db.iterdump()) == before


def test_missing_database_and_duplicate_id_are_rejected(config, repo, saved, tmp_path):
    first, _ = saved
    edit = {"job_id": first.id, "status": "Applied"}
    path = input_file(tmp_path, [edit, edit])
    with pytest.raises(ValueError):
        read_import(path)
    path = input_file(tmp_path, [edit])
    config.settings.database_url = "sqlite:///" + str(tmp_path / "absent.db")
    for action in (
        lambda: preview_import(config, path),
        lambda: apply_import(config, path, "old", tmp_path / "backup.zip"),
    ):
        with pytest.raises(ValueError):
            action()
    assert not (tmp_path / "absent.db").exists()


def test_json_duplicate_keys_and_large_files_are_rejected(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text('{"format_version":1,"format_version":1,"applications":[]}')
    with pytest.raises(ValueError, match="Duplicate"):
        read_import(path)
    path.write_bytes(b" " * 2_000_001)
    with pytest.raises(ValueError, match="size limit"):
        read_import(path)


def test_cli_defaults_to_preview_and_errors_hide_imported_private_text(
    config, repo, saved, tmp_path, monkeypatch
):
    monkeypatch.setattr("trading_radar.application_cli.load_config", lambda _: config)
    monkeypatch.setattr(
        "trading_radar.http.HTTPClient.__init__", lambda *a, **kw: pytest.fail("Network")
    )
    first, _ = saved
    path = input_file(tmp_path, [{"job_id": first.id, "status": "Applied"}])
    runner = CliRunner()
    before = list(repo.db.iterdump())
    result = runner.invoke(app, ["applications", "import", str(path)])
    assert result.exit_code == 0 and json.loads(result.stdout)["read_only"]
    assert runner.invoke(app, ["applications", "import", str(path), "--apply"]).exit_code != 0
    input_file(tmp_path, [{"job_id": first.id, "status": "private-secret"}])
    failure = runner.invoke(app, ["applications", "import", str(path)])
    assert failure.exit_code != 0 and "private-secret" not in failure.output
    assert list(repo.db.iterdump()) == before
