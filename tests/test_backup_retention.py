import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from trading_radar import backup_retention
from trading_radar.backup_retention import plan_retention
from trading_radar.backups import DATABASE_MEMBER, MANIFEST_MEMBER, create_backup

NOW = datetime(2026, 1, 5, 12, tzinfo=UTC)


@pytest.fixture
def archives(repo, tmp_path):
    source = Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    original = tmp_path / "original.zip"
    create_backup(source, original)
    with ZipFile(original) as archive:
        manifest = json.loads(archive.read(MANIFEST_MEMBER))
        database = archive.read(DATABASE_MEMBER)
    directory = tmp_path / "archives"
    directory.mkdir()

    def add(name, timestamp, *, schema=None):
        changed = dict(manifest, created_at=timestamp)
        if schema is not None:
            changed["schema_version"] = schema
        path = directory / name
        with ZipFile(path, "w") as archive:
            archive.writestr(MANIFEST_MEMBER, json.dumps(changed))
            archive.writestr(DATABASE_MEMBER, database)
        return path

    return directory, add


def decisions(report):
    return {entry["name"]: entry["decision"] for entry in report["entries"]}


def test_union_of_daily_weekly_latest_uses_iso_year_and_utc(archives):
    directory, add = archives
    add("today.zip", "2026-01-05T10:00:00+00:00")
    add("today-older.zip", "2026-01-05T09:00:00+00:00")
    add("utc-sunday.zip", "2026-01-05T01:00:00+02:00")
    add("last-week-older.zip", "2026-01-03T12:00:00+00:00")
    add("year-boundary.zip", "2025-12-28T12:00:00+00:00")
    add("outside.zip", "2025-12-21T12:00:00+00:00")
    report = plan_retention(directory, keep_latest=1, keep_daily=2, keep_weekly=3, now=NOW)
    assert report["status"] == "ok"
    assert decisions(report) == {
        "today.zip": "keep",
        "today-older.zip": "candidate",
        "utc-sunday.zip": "keep",
        "last-week-older.zip": "candidate",
        "year-boundary.zip": "keep",
        "outside.zip": "candidate",
    }
    assert report["entries"][0]["reasons"] == ["latest", "daily", "weekly"]
    sunday = next(entry for entry in report["entries"] if entry["name"] == "utc-sunday.zip")
    assert sunday["created_at"] == "2026-01-04T23:00:00+00:00"
    assert report["summary"]["kept"] == report["summary"]["candidates"] == 3


def test_filename_tie_break_and_readonly_fingerprints(archives):
    directory, add = archives
    for name in ("z.zip", "a.ZIP", "b.Zip"):
        add(name, "2026-01-04T12:00:00Z")
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    report = plan_retention(directory, keep_latest=1, keep_daily=0, keep_weekly=0, now=NOW)
    assert list(decisions(report)) == ["a.ZIP", "b.Zip", "z.zip"]
    assert decisions(report) == {"a.ZIP": "keep", "b.Zip": "candidate", "z.zip": "candidate"}
    assert report["deletion_performed"] is False
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before
    for entry in report["entries"]:
        assert entry["sha256"] == hashlib.sha256(before[entry["name"]]).hexdigest()
    assert report["summary"]["candidate_bytes"] == len(before["b.Zip"]) + len(before["z.zip"])


@pytest.mark.parametrize("broken", ["corrupt", "schema", "future", "naive", "bad-date"])
def test_any_invalid_archive_blocks_all_candidate_advice(archives, broken):
    directory, add = archives
    add("old.zip", "2025-01-01T00:00:00Z")
    add("recent.zip", "2026-01-04T00:00:00Z")
    if broken == "corrupt":
        (directory / "broken.zip").write_bytes(b"PRIVATE contents not a ZIP")
    elif broken == "schema":
        add("broken.zip", "2026-01-04T00:00:00Z", schema=999)
    else:
        timestamp = {
            "future": "2026-01-06T00:00:00Z",
            "naive": "2026-01-04T00:00:00",
            "bad-date": "PRIVATE",
        }[broken]
        add("broken.zip", timestamp)
    report = plan_retention(directory, keep_latest=1, keep_daily=0, keep_weekly=0, now=NOW)
    assert report["status"] == "blocked"
    assert report["summary"]["candidates"] == report["summary"]["candidate_bytes"] == 0
    assert report["summary"]["valid"] == report["summary"]["kept"] == 2
    assert report["summary"]["invalid"] == 1
    for entry in report["entries"][:2]:
        assert entry["reasons"] == ["retained_due_to_incomplete_audit"]
        assert entry["decision"] == "keep"
    assert report["entries"][-1]["decision"] == "blocked"
    assert "PRIVATE" not in json.dumps(report)


def test_empty_and_nested_archives_are_not_opened(tmp_path, monkeypatch):
    nested = tmp_path / "subdirectory"
    nested.mkdir()
    (nested / "nested.zip").write_bytes(b"not an archive")
    (tmp_path / "notes.txt").write_text("ignored")
    monkeypatch.setattr(backup_retention, "verify_backup", lambda _: pytest.fail("must not verify"))
    report = plan_retention(tmp_path, now=NOW)
    assert report["status"] == "empty"
    assert report["entries"] == []
    assert all(value == 0 for value in report["summary"].values())


@pytest.mark.parametrize(
    "policy",
    [
        {"keep_latest": 0},
        {"keep_latest": 101},
        {"keep_latest": True},
        {"keep_daily": -1},
        {"keep_daily": 366},
        {"keep_daily": 1.0},
        {"keep_weekly": -1},
        {"keep_weekly": 105},
        {"keep_weekly": "1"},
    ],
)
def test_policy_bounds(tmp_path, policy):
    with pytest.raises(ValueError, match="^invalid_retention_policy$"):
        plan_retention(tmp_path, now=NOW, **policy)


@pytest.mark.parametrize("value", [datetime(2026, 1, 1), "PRIVATE"])
def test_invalid_clock_is_rejected(tmp_path, value):
    with pytest.raises(ValueError, match="^invalid_timestamp$"):
        plan_retention(tmp_path, now=value)


@pytest.mark.parametrize("kind", ["absent", "file"])
def test_invalid_directory_has_safe_error(tmp_path, kind):
    path = tmp_path / "PRIVATE"
    if kind == "file":
        path.write_text("private")
    with pytest.raises(ValueError, match="^invalid_backup_directory$"):
        plan_retention(path, now=NOW)


@pytest.mark.parametrize("limit", ["count", "file", "total"])
def test_budgets_are_checked_before_any_verification(tmp_path, monkeypatch, limit):
    for name in ("a.zip", "b.zip"):
        (tmp_path / name).write_bytes(b"12345")
    key, value, error = {
        "count": ("MAX_ARCHIVES", 1, "archive_count_limit"),
        "file": ("MAX_ARCHIVE_BYTES", 4, "archive_size_limit"),
        "total": ("MAX_TOTAL_BYTES", 9, "archive_total_size_limit"),
    }[limit]
    monkeypatch.setattr(backup_retention, key, value)
    monkeypatch.setattr(backup_retention, "verify_backup", lambda _: pytest.fail("must not verify"))
    with pytest.raises(ValueError, match=f"^{error}$"):
        plan_retention(tmp_path, now=NOW)


def test_nonregular_zip_entry_blocks_plan(archives):
    directory, add = archives
    add("valid.zip", "2026-01-04T00:00:00Z")
    (directory / "folder.zip").mkdir()
    report = plan_retention(directory, now=NOW)
    assert report["status"] == "blocked"
    assert report["entries"][-1]["error"] == "non_regular_archive"


def make_symlink(target, link, *, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError:
        pytest.skip("Creating symlinks requires privileges on this host")


def test_symlink_archive_is_not_followed(archives):
    directory, add = archives
    target = add("valid.zip", "2026-01-04T00:00:00Z")
    make_symlink(target, directory / "alias.zip")
    report = plan_retention(directory, now=NOW)
    assert report["status"] == "blocked"
    assert report["entries"][-1]["error"] == "unsafe_archive_path"


def test_symlink_ancestor_is_not_resolved_before_checking(archives, tmp_path):
    directory, _ = archives
    link = tmp_path / "alias"
    make_symlink(directory, link, directory=True)
    (directory / "sub").mkdir()
    for path in (link, link / "sub", link / "sub" / ".."):
        with pytest.raises(ValueError, match="^invalid_backup_directory$"):
            plan_retention(path, now=NOW)


def test_windows_reparse_attribute_is_rejected(monkeypatch, tmp_path):
    original = Path.lstat

    class JunctionStat:
        st_mode = 0o040755
        st_file_attributes = 0x400

    monkeypatch.setattr(
        Path, "lstat", lambda path: JunctionStat() if path == tmp_path else original(path)
    )
    with pytest.raises(ValueError, match="^invalid_backup_directory$"):
        plan_retention(tmp_path, now=NOW)


def test_changed_archive_is_not_trusted(archives, monkeypatch):
    directory, add = archives
    path = add("valid.zip", "2026-01-04T00:00:00Z")
    original = backup_retention.verify_backup

    def changing(archive):
        result = original(archive)
        with archive.open("ab") as stream:
            stream.write(b"changed")
        return result

    monkeypatch.setattr(backup_retention, "verify_backup", changing)
    report = plan_retention(directory, now=NOW)
    assert report["status"] == "blocked"
    assert report["entries"][0]["error"] == "archive_changed"
    assert "sha256" not in report["entries"][0]
    assert path.exists()


def test_earlier_verified_archive_change_blocks_plan(archives, monkeypatch):
    directory, add = archives
    first = add("a.zip", "2026-01-04T00:00:00Z")
    add("b.zip", "2026-01-03T00:00:00Z")
    original = backup_retention.verify_backup

    def changing(archive):
        result = original(archive)
        if archive.name == "b.zip":
            with first.open("ab") as stream:
                stream.write(b"changed")
        return result

    monkeypatch.setattr(backup_retention, "verify_backup", changing)
    report = plan_retention(directory, now=NOW)
    assert report["status"] == "blocked"
    assert report["summary"]["candidates"] == 0
    assert report["entries"][-1]["error"] == "archive_changed"


def test_new_archive_during_audit_invalidates_inventory(archives, monkeypatch):
    directory, add = archives
    add("a.zip", "2026-01-04T00:00:00Z")
    original = backup_retention.verify_backup

    def changing(archive):
        result = original(archive)
        (directory / "new.zip").write_bytes(b"new")
        return result

    monkeypatch.setattr(backup_retention, "verify_backup", changing)
    with pytest.raises(ValueError, match="^backup_directory_changed$"):
        plan_retention(directory, now=NOW)


def test_exception_details_are_never_exposed(archives, monkeypatch):
    directory, add = archives
    add("valid.zip", "2026-01-04T00:00:00Z")

    def fail(_):
        raise RuntimeError("PRIVATE credentials and paths")

    monkeypatch.setattr(backup_retention, "verify_backup", fail)
    report = plan_retention(directory, now=NOW)
    assert "PRIVATE" not in json.dumps(report)
    assert report["entries"][0]["error"] == "invalid_backup"


def test_control_characters_in_labels_are_sanitized(archives):
    if os.name == "nt":
        # Windows rejects control characters in filenames, so exercise the same
        # sanitizer directly; POSIX can cover the complete inventory path.
        assert backup_retention._safe_text("x\x1b[31m\n.zip") == "x\ufffd[31m\ufffd.zip"
        return
    directory, add = archives
    add("unsafe\n.zip", "2026-01-04T00:00:00Z")
    report = plan_retention(directory, now=NOW)
    assert report["entries"][0]["name"] == "unsafe\ufffd.zip"
