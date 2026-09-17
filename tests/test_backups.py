import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from filelock import FileLock, Timeout
from typer.testing import CliRunner

from trading_radar import backups
from trading_radar.backups import (
    DATABASE_MEMBER,
    MANIFEST_MEMBER,
    create_backup,
    database_path,
    restore_backup,
    verify_backup,
)
from trading_radar.cli import app
from trading_radar.notifications import TelegramNotifier
from trading_radar.storage import Repository


def source_path(repo):
    return Path(repo.db.execute("PRAGMA database_list").fetchone()[2])


def rows(connection):
    return {
        name: connection.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
        for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


@pytest.fixture
def populated(repo, job):
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
        repo.mark_success("test", 1, 0.1)
    repo.update_application(job.id, {"status": "Applied", "notes": "Entretien — électricité"})
    alert = repo.pending()[0]["id"]
    repo.set_alert(alert, "sending")
    repo.set_alert(alert, "unknown", "DeliveryUnknown")
    return repo


@pytest.fixture
def archive(populated, tmp_path):
    destination = tmp_path / "backup.zip"
    create_backup(source_path(populated), destination)
    return destination


def rewrite(archive, *, change=None, database=None, extra=None, compression=0):
    with ZipFile(archive) as bundle:
        manifest = json.loads(bundle.read(MANIFEST_MEMBER))
        content = bundle.read(DATABASE_MEMBER)
    if database is not None:
        content = database
        manifest["sha256"] = hashlib.sha256(content).hexdigest()
        manifest["sqlite_bytes"] = len(content)
    if change:
        change(manifest)
    with ZipFile(archive, "w", compression=compression) as bundle:
        bundle.writestr(DATABASE_MEMBER, content)
        bundle.writestr(MANIFEST_MEMBER, json.dumps(manifest))
        if extra:
            bundle.writestr(extra, "extra")


def test_roundtrip_preserves_committed_wal_and_every_table(populated, tmp_path):
    source = source_path(populated)
    assert Path(str(source) + "-wal").stat().st_size > 0
    # Independent connection reads rows as tuples for an exact comparison.
    with closing(sqlite3.connect(source)) as reader:
        before = rows(reader)
    destination = tmp_path / "copies" / "backup.zip"
    manifest = create_backup(source, destination)
    assert manifest["tables"]["jobs"] == 1
    assert manifest["tables"]["application_history"] == 1
    assert manifest["tables"]["alert_history"] == 2
    assert verify_backup(destination) == manifest
    restored = tmp_path / "restored" / "jobs.db"
    assert restore_backup(destination, restored, protected=source) == manifest
    with (
        closing(sqlite3.connect(restored)) as recovered,
        closing(sqlite3.connect(source)) as original,
    ):
        assert rows(recovered) == rows(original) == before
        assert recovered.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        assert original.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    # The application can open the restored copy, with user notes and uncertain state intact.
    recovered_repo = Repository(f"sqlite:///{restored}")
    try:
        assert recovered_repo.get_alert(1)["status"] == "unknown"
        assert recovered_repo.application_history(next(iter(before["jobs"]))[0])
    finally:
        recovered_repo.close()


def test_uncommitted_writes_are_excluded(populated, tmp_path):
    populated.db.execute("UPDATE applications SET notes='not committed'")
    try:
        artifact = tmp_path / "backup.zip"
        create_backup(source_path(populated), artifact)
        restored = tmp_path / "recovered.db"
        restore_backup(artifact, restored, protected=source_path(populated))
        with closing(sqlite3.connect(restored)) as reader:
            assert reader.execute("SELECT notes FROM applications").fetchone()[0] != "not committed"
    finally:
        populated.db.rollback()


def test_snapshot_does_not_block_on_application_writer_lock(repo, tmp_path):
    with FileLock(repo.lock_path, timeout=0):
        create_backup(source_path(repo), tmp_path / "backup.zip")


@pytest.mark.parametrize("url", ["postgresql://localhost/db", "sqlite:///:memory:", "sqlite:///"])
def test_reject_non_file_databases(url):
    with pytest.raises(ValueError):
        database_path(url)


def test_missing_database_is_not_created(tmp_path):
    source = tmp_path / "missing.db"
    with pytest.raises(ValueError, match="does not exist"):
        create_backup(source, tmp_path / "backup.zip")
    assert not source.exists()


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal", ".lock"])
def test_backup_cannot_target_source_or_sidecars(repo, suffix):
    source = source_path(repo)
    with pytest.raises(ValueError, match="overlaps"):
        create_backup(source, Path(str(source) + suffix))


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal", ".lock"])
def test_restore_protects_configured_database_even_if_missing(archive, tmp_path, suffix):
    protected = tmp_path / "absent.db"
    with pytest.raises(ValueError, match="overlaps"):
        restore_backup(archive, Path(str(protected) + suffix), protected=protected)
    assert not protected.exists()


@pytest.mark.parametrize("operation", ["create", "restore"])
def test_never_overwrites_existing_file(repo, archive, tmp_path, operation):
    target = tmp_path / "keep.db"
    target.write_bytes(b"keep this")
    with pytest.raises(ValueError, match="already exists"):
        if operation == "create":
            create_backup(source_path(repo), target)
        else:
            restore_backup(archive, target, protected=source_path(repo))
    assert target.read_bytes() == b"keep this"


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_restore_rejects_orphan_sidecars(repo, archive, tmp_path, suffix):
    target = tmp_path / "recovered.db"
    Path(str(target) + suffix).write_bytes(b"unrelated")
    with pytest.raises(ValueError, match="sidecar"):
        restore_backup(archive, target, protected=source_path(repo))
    assert not target.exists()


def test_restore_respects_writer_lock(repo, archive, tmp_path):
    target = tmp_path / "recovered.db"
    with FileLock(str(target) + ".lock", timeout=0), pytest.raises(Timeout):
        restore_backup(archive, target, protected=source_path(repo))
    assert not target.exists()


def test_restore_lock_cannot_modify_archive(archive, tmp_path):
    target = tmp_path / "recovered.db"
    lock_named_archive = Path(str(target) + ".lock")
    archive.rename(lock_named_archive)
    before = lock_named_archive.read_bytes()
    with pytest.raises(ValueError, match="overlaps"):
        restore_backup(lock_named_archive, target, protected=tmp_path / "other.db")
    assert lock_named_archive.read_bytes() == before


def test_restore_lock_cannot_modify_active_database(repo, archive, tmp_path):
    target = tmp_path / "recovered.db"
    os.link(source_path(repo), Path(str(target) + ".lock"))
    before = source_path(repo).read_bytes()
    with pytest.raises(ValueError, match="overlaps"):
        restore_backup(archive, target, protected=source_path(repo))
    assert source_path(repo).read_bytes() == before


def test_restore_lock_cannot_modify_hardlinked_archive(archive, tmp_path):
    target = tmp_path / "recovered.db"
    os.link(archive, Path(str(target) + ".lock"))
    before = archive.read_bytes()
    with pytest.raises(ValueError, match="overlaps"):
        restore_backup(archive, target, protected=tmp_path / "other.db")
    assert archive.read_bytes() == before


def test_restored_file_publication_race_does_not_overwrite(repo, archive, tmp_path, monkeypatch):
    target = tmp_path / "recovered.db"
    original = os.link

    def race(source, destination):
        destination.write_bytes(b"other process")
        original(source, destination)

    monkeypatch.setattr(backups.os, "link", race)
    with pytest.raises(FileExistsError):
        restore_backup(archive, target, protected=source_path(repo))
    assert target.read_bytes() == b"other process"
    assert not list(tmp_path.glob(".radar-restore-*"))


@pytest.mark.parametrize("version", [3, 5])
def test_unsupported_schema_is_not_migrated(repo, tmp_path, version):
    with repo.db:
        repo.db.execute("DELETE FROM schema_version")
        repo.db.execute("INSERT INTO schema_version VALUES(?)", (version,))
    before = list(repo.db.iterdump())
    with pytest.raises(ValueError, match="schema version"):
        create_backup(source_path(repo), tmp_path / "backup.zip")
    assert list(repo.db.iterdump()) == before
    assert not (tmp_path / "backup.zip").exists()
    assert not list(tmp_path.glob(".radar-backup-*"))


@pytest.mark.parametrize("mutation", ["DROP TABLE application_history", "CREATE TABLE extra(x)"])
def test_incomplete_or_unexpected_schema_rejected(repo, tmp_path, mutation):
    repo.db.execute(mutation)
    with pytest.raises(ValueError, match="schema does not match"):
        create_backup(source_path(repo), tmp_path / "backup.zip")


def test_foreign_key_corruption_rejected(repo, tmp_path):
    repo.db.execute("PRAGMA foreign_keys=OFF")
    with repo.db:
        repo.db.execute("INSERT INTO applications(job_id) VALUES('missing')")
    with pytest.raises(ValueError, match="foreign keys"):
        create_backup(source_path(repo), tmp_path / "backup.zip")


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda m: m.update(sha256="0" * 64), "SHA-256"),
        (lambda m: m.update(sqlite_bytes=1), "size"),
        (lambda m: m["tables"].update(jobs=999), "contents"),
        (lambda m: m.update(schema_version=5), "contents"),
        (lambda m: m.update(format_version=2), "format version"),
        (lambda m: m.update(format_version=True), "format version"),
        (lambda m: m.update(created_at="2026-01-01"), "timestamp"),
        (lambda m: m.update(created_at={}), "timestamp"),
        (lambda m: m.pop("tables"), "manifest"),
    ],
)
def test_bad_manifests_never_restore(archive, tmp_path, change, match):
    rewrite(archive, change=change)
    target = tmp_path / "restored.db"
    with pytest.raises(ValueError, match=match):
        restore_backup(archive, target, protected=tmp_path / "other.db")
    assert not target.exists()
    assert not list(tmp_path.glob(".radar-restore-*"))


def test_corrupt_sqlite_with_matching_checksum_is_rejected(archive, tmp_path):
    rewrite(archive, database=b"not a sqlite database")
    with pytest.raises(sqlite3.DatabaseError):
        restore_backup(archive, tmp_path / "restored.db", protected=tmp_path / "other.db")
    assert not (tmp_path / "restored.db").exists()


@pytest.mark.parametrize("extra", ["../escape.db", "unexpected.txt", "database.sqlite3"])
def test_unexpected_archive_members_rejected(archive, tmp_path, extra):
    if extra == DATABASE_MEMBER:
        with pytest.warns(UserWarning):
            rewrite(archive, extra=extra)
    else:
        rewrite(archive, extra=extra)
    with pytest.raises(ValueError, match="exactly"):
        verify_backup(archive)
    assert not (tmp_path.parent / "escape.db").exists()


def test_compressed_archives_rejected(archive):
    rewrite(archive, compression=ZIP_DEFLATED)
    with pytest.raises(ValueError, match="compressed"):
        verify_backup(archive)


def test_oversized_manifest_rejected(archive):
    rewrite(archive, change=lambda m: m.update(created_at="x" * 70000))
    with pytest.raises(ValueError, match="too large"):
        verify_backup(archive)


def test_publication_race_does_not_overwrite(repo, tmp_path, monkeypatch):
    target = tmp_path / "backup.zip"
    original = os.link

    def race(source, destination):
        destination.write_bytes(b"other process")
        original(source, destination)

    monkeypatch.setattr(backups.os, "link", race)
    with pytest.raises(FileExistsError):
        create_backup(source_path(repo), target)
    assert target.read_bytes() == b"other process"
    assert not list(tmp_path.glob(".radar-backup-*"))


def test_copy_timeout_leaves_no_archive(repo, tmp_path, monkeypatch):
    ticks = iter([0, 31])
    monkeypatch.setattr(backups.time, "monotonic", lambda: next(ticks))
    target = tmp_path / "backup.zip"
    with pytest.raises(ValueError, match="30 seconds"):
        create_backup(source_path(repo), target)
    assert not target.exists()


def test_cli_roundtrip_never_initializes_notifier(populated, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Backup commands must not initialize notifications")

    monkeypatch.setattr(TelegramNotifier, "from_env", forbidden)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{source_path(populated)}")
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    runner = CliRunner()
    archive = tmp_path / "cli.zip"
    restored = tmp_path / "cli.db"
    for arguments in (
        ["backup", "create", str(archive)],
        ["backup", "verify", str(archive)],
        ["backup", "restore", str(archive), str(restored)],
    ):
        result = runner.invoke(app, arguments)
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["manifest"]["tables"]["jobs"] == 1


def test_cli_verify_needs_no_configuration(archive, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["backup", "verify", str(archive)])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("content", [b"not zip", b"PK\x03\x04"])
def test_cli_corrupted_archive_exits_cleanly(tmp_path, content):
    artifact = tmp_path / "broken.zip"
    artifact.write_bytes(content)
    result = CliRunner().invoke(app, ["backup", "verify", str(artifact)])
    assert result.exit_code == 1
    assert "Backup operation failed" in result.output
    assert "Traceback" not in result.output
