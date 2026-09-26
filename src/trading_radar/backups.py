"""Offline SQLite snapshots and verified, non-overwriting recovery.

Never instantiate Repository here: opening a backup must not migrate its schema.
An archive is one immutable snapshot plus a manifest, published only after validation.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZIP_STORED, ZipFile

from filelock import FileLock

from trading_radar.storage import SCHEMA, SCHEMA_VERSION

DATABASE_MEMBER = "database.sqlite3"
MANIFEST_MEMBER = "manifest.json"
SIDECARS = ("-wal", "-shm", "-journal")


def database_path(url: str) -> Path:
    if not url.startswith("sqlite:///") or url == "sqlite:///:memory:":
        raise ValueError("Backups require a file-backed sqlite:/// database.")
    value = url.removeprefix("sqlite:///")
    if not value:
        raise ValueError("Database path is empty.")
    return Path(value).resolve()


def _read_only(path: Path) -> sqlite3.Connection:
    # mode=ro includes committed WAL content; immutable=1 would incorrectly ignore it.
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA trusted_schema=OFF")
    return connection


def _schema(connection: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()


def inspect_database(path: Path) -> dict[str, Any]:
    """Validate a standalone snapshot, without creating or migrating any tables."""
    with closing(_read_only(path)) as connection, closing(sqlite3.connect(":memory:")) as expected:
        expected.executescript(SCHEMA)
        if connection.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
            raise ValueError("Backup must be a standalone SQLite database in DELETE journal mode.")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed.")
        if _schema(connection) != _schema(expected):
            raise ValueError("Database schema does not match this application.")
        if (
            connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            != SCHEMA_VERSION
        ):
            raise ValueError("Unsupported database schema version; no migration was performed.")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("Database contains broken foreign keys.")
        tables = {
            name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            for kind, name, _, _ in _schema(expected)
            if kind == "table"
        }
    return {"schema_version": SCHEMA_VERSION, "tables": tables}


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _require_new(path: Path, *, database: bool = False) -> None:
    if os.path.lexists(path):
        raise ValueError("Destination already exists; overwriting is never allowed.")
    if database and any(os.path.lexists(str(path) + suffix) for suffix in SIDECARS):
        raise ValueError("Destination has SQLite sidecar files; choose a new path.")


def _protect_path(destination: Path, source: Path) -> None:
    protected = {
        source.resolve(),
        *(Path(str(source.resolve()) + suffix) for suffix in (*SIDECARS, ".lock", ".scan.lock")),
    }
    if any(
        destination.resolve() == path
        or (destination.exists() and path.exists() and destination.samefile(path))
        for path in protected
    ):
        raise ValueError("Destination overlaps the configured database or its sidecars.")


def _publish(staged: Path, destination: Path, *, database: bool = False) -> None:
    _require_new(destination, database=database)
    staged.chmod(0o600)
    with staged.open("r+b") as stream:
        os.fsync(stream.fileno())
    # Same-volume hard link publishes a complete file atomically and fails if another
    # process created the destination. Unlike replace(), it cannot overwrite a file.
    os.link(staged, destination)


def create_backup(source: Path, destination: Path) -> dict[str, Any]:
    """Take a consistent SQLite online backup, including committed WAL transactions."""
    source = source.resolve()
    _protect_path(destination, source)
    if not source.is_file():
        raise ValueError("Source database does not exist.")
    _require_new(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".radar-backup-", dir=destination.parent) as directory:
        snapshot = Path(directory) / DATABASE_MEMBER
        deadline = time.monotonic() + 30

        def progress(status: int, remaining: int, total: int) -> None:
            if time.monotonic() > deadline:
                raise ValueError(
                    "Snapshot exceeded 30 seconds; retry when database activity is lower."
                )

        with closing(_read_only(source)) as reader, closing(sqlite3.connect(snapshot)) as writer:
            reader.backup(writer, pages=256, progress=progress, sleep=0.05)
            writer.execute("PRAGMA journal_mode=DELETE")
        manifest = {
            "format_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "sqlite_bytes": snapshot.stat().st_size,
            "sha256": _digest(snapshot),
            **inspect_database(snapshot),
        }
        archive = Path(directory) / "backup.zip"
        with ZipFile(archive, "w", compression=ZIP_STORED) as bundle:
            bundle.write(snapshot, DATABASE_MEMBER)
            bundle.writestr(MANIFEST_MEMBER, json.dumps(manifest, ensure_ascii=False, indent=2))
        # Verify the actual archive, not only the source snapshot, before publication.
        verify_backup(archive)
        _publish(archive, destination)
    return manifest


def _unpack_verified(archive: Path, snapshot: Path) -> dict[str, Any]:
    with ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if sorted(entry.filename for entry in entries) != [DATABASE_MEMBER, MANIFEST_MEMBER]:
            raise ValueError("Backup must contain exactly database.sqlite3 and manifest.json.")
        if any(entry.compress_type != ZIP_STORED for entry in entries):
            raise ValueError("Unsupported compressed backup; expected the radar archive format.")
        if any(entry.flag_bits & 1 for entry in entries):
            raise ValueError("Encrypted ZIP entries are not supported.")
        if bundle.getinfo(MANIFEST_MEMBER).file_size > 65536:
            raise ValueError("Backup manifest is too large.")
        manifest = json.loads(bundle.read(MANIFEST_MEMBER))
        required = {
            "format_version",
            "created_at",
            "sqlite_bytes",
            "sha256",
            "schema_version",
            "tables",
        }
        if not isinstance(manifest, dict) or set(manifest) != required:
            raise ValueError("Invalid backup manifest.")
        if type(manifest["format_version"]) is not int or manifest["format_version"] != 1:
            raise ValueError("Unsupported backup format version.")
        try:
            created_at = datetime.fromisoformat(manifest["created_at"])
            if created_at.utcoffset() is None:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("Invalid backup creation timestamp.") from None
        if (
            type(manifest["sqlite_bytes"]) is not int
            or manifest["sqlite_bytes"] != bundle.getinfo(DATABASE_MEMBER).file_size
        ):
            raise ValueError("Database size does not match the manifest.")
        # Fixed output name, no ZipFile.extract: archive paths never choose a destination.
        with bundle.open(DATABASE_MEMBER) as reader, snapshot.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
    if _digest(snapshot) != manifest["sha256"]:
        raise ValueError("Database SHA-256 does not match the manifest.")
    actual = inspect_database(snapshot)
    if any(actual[key] != manifest[key] for key in actual):
        raise ValueError("Database contents do not match the manifest.")
    if any(Path(str(snapshot) + suffix).exists() for suffix in SIDECARS):
        raise ValueError("Backup database is not a standalone SQLite file.")
    return manifest


def verify_backup(archive: Path) -> dict[str, Any]:
    """Validate archive layout, digest, SQLite integrity, schema, relations and counts."""
    with TemporaryDirectory(prefix="radar-verify-") as directory:
        return _unpack_verified(archive, Path(directory) / DATABASE_MEMBER)


def restore_backup(archive: Path, destination: Path, *, protected: Path) -> dict[str, Any]:
    """Restore to a new file only; never select it as the active application database."""
    _protect_path(destination, protected)
    lock_path = Path(str(destination) + ".lock")
    # FileLock can truncate an existing lock file on POSIX. Check aliases before
    # acquiring it, including an archive whose filename happens to end in .lock.
    _protect_path(lock_path, protected)
    _protect_path(lock_path, archive)
    _require_new(destination, database=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(lock_path, timeout=0):
        _require_new(destination, database=True)
        with TemporaryDirectory(prefix=".radar-restore-", dir=destination.parent) as directory:
            snapshot = Path(directory) / DATABASE_MEMBER
            manifest = _unpack_verified(archive, snapshot)
            _publish(snapshot, destination, database=True)
    return manifest
