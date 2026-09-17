import json
import sqlite3
from contextlib import closing
from pathlib import Path

from typer.testing import CliRunner

from trading_radar.backups import create_backup, restore_backup
from trading_radar.cli import app


def table_contents(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("BEGIN")
        return {
            table: db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            for (table,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }


def test_retention_candidate_stays_restorable_with_application_and_alert_history(
    repo, job, tmp_path, monkeypatch
):
    source = Path(repo.db.execute("PRAGMA database_list").fetchone()[2]).resolve()
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
    repo.update_application(job.id, {"status": "Applied", "notes": "Entretien vendredi"})
    alert = repo.pending()[0]["id"]
    repo.set_alert(alert, "sending")
    repo.set_alert(alert, "unknown", "DeliveryUnknown")
    before = table_contents(source)
    archives = tmp_path / "archives"
    create_backup(source, archives / "older.zip")
    create_backup(source, archives / "newer.zip")
    archive_bytes = {path.name: path.read_bytes() for path in archives.iterdir()}
    # Planning must work without project configuration or the live Repository.
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "backup",
            "plan",
            str(archives),
            "--keep-latest",
            "1",
            "--keep-daily",
            "0",
            "--keep-weekly",
            "0",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["status"] == "ok" and plan["deletion_performed"] is False
    candidates = [entry for entry in plan["entries"] if entry["decision"] == "candidate"]
    assert len(candidates) == 1 and candidates[0]["name"] == "older.zip"
    assert plan["summary"]["candidate_bytes"] == len(archive_bytes["older.zip"])
    restored = tmp_path / "candidate-restored.db"
    restore_backup(archives / candidates[0]["name"], restored, protected=source)
    assert table_contents(restored) == before == table_contents(source)
    assert {path.name: path.read_bytes() for path in archives.iterdir()} == archive_bytes


def test_invalid_archive_blocks_candidates_without_modifying_any_archive(repo, tmp_path):
    source = Path(repo.db.execute("PRAGMA database_list").fetchone()[2]).resolve()
    archives = tmp_path / "archives"
    create_backup(source, archives / "valid-a.zip")
    create_backup(source, archives / "valid-b.zip")
    (archives / "broken.zip").write_bytes(b"truncated archive")
    before = {path.name: path.read_bytes() for path in archives.iterdir()}
    result = CliRunner().invoke(
        app,
        [
            "backup",
            "plan",
            str(archives),
            "--keep-latest",
            "1",
            "--keep-daily",
            "0",
            "--keep-weekly",
            "0",
            "--json",
        ],
    )
    assert result.exit_code == 1, result.output
    plan = json.loads(result.output)
    assert plan["status"] == "blocked"
    assert plan["summary"]["valid"] == 2 and plan["summary"]["invalid"] == 1
    assert plan["summary"]["candidates"] == plan["summary"]["candidate_bytes"] == 0
    assert not any(entry["decision"] == "candidate" for entry in plan["entries"])
    assert {path.name: path.read_bytes() for path in archives.iterdir()} == before
