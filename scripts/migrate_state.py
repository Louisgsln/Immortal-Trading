"""Offline, verified migration of business data, Telegram state and source configuration.

Run export only after ALL source writers (including Dashboard edits) have stopped.
Archives contain private data, but never dotenv files or Telegram credentials.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_STORED, ZipFile

from filelock import FileLock

from trading_radar.backups import create_backup, restore_backup, verify_backup
from trading_radar.config import load_config
from trading_radar.telegram_control import ControlState
from trading_radar.telegram_heartbeat import HeartbeatState

CONFIG_FILES = ("settings.yaml", "companies.yaml", "keywords.yaml")
MAX_BYTES = 2 * 1024**3
MAX_MEMBERS = 10000
RECEIPT = "migration-receipt.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def allowed(name: str) -> bool:
    return name in {
        "database.zip",
        "data/jobs.telegram.json",
        "data/jobs.heartbeat.json",
        *("config/" + name for name in CONFIG_FILES),
    } or bool(re.fullmatch(r"data/health-history/[A-Za-z0-9_.-]+\.json", name))


def validate_state(root: Path) -> str:
    state = ControlState.model_validate_json((root / "data/jobs.telegram.json").read_bytes())
    if not re.fullmatch(r"[a-f0-9]{64}", state.binding):
        raise ValueError("Invalid Telegram binding")
    heartbeat = root / "data/jobs.heartbeat.json"
    if heartbeat.exists():
        pulse = HeartbeatState.model_validate_json(heartbeat.read_bytes())
        if pulse.binding != state.binding:
            raise ValueError("Telegram and heartbeat destinations differ")
    config = load_config(root / "config")
    if not any(company.enabled for company in config.companies.values()):
        raise ValueError("No enabled sources in exported configuration")
    return state.binding


def _unpack(archive: Path, root: Path) -> dict:
    with ZipFile(archive) as bundle:
        infos = bundle.infolist()
        names = [info.filename for info in infos]
        if (
            len(names) != len(set(names))
            or len(names) > MAX_MEMBERS
            or set(names) - {"manifest.json"} != {name for name in names if allowed(name)}
            or "manifest.json" not in names
            or any(info.flag_bits & 1 or info.is_dir() for info in infos)
            or sum(info.file_size for info in infos) > MAX_BYTES
            or bundle.getinfo("manifest.json").file_size > 2 * 1024**2
        ):
            raise ValueError("Invalid migration archive layout")
        manifest = json.loads(bundle.read("manifest.json"))
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"format_version", "id", "created_at", "files"}
            or manifest["format_version"] != 1
            or not re.fullmatch(r"[a-f0-9]{32}", manifest["id"])
            or not isinstance(manifest["files"], dict)
            or set(manifest["files"]) != set(names) - {"manifest.json"}
            or not {
                "database.zip",
                "data/jobs.telegram.json",
                *("config/" + f for f in CONFIG_FILES),
            }
            <= set(names)
        ):
            raise ValueError("Invalid migration manifest")
        if datetime.fromisoformat(manifest["created_at"]).utcoffset() is None:
            raise ValueError("Migration timestamp must include a timezone")
        for name, details in manifest["files"].items():
            if (
                not isinstance(details, dict)
                or set(details) != {"bytes", "sha256"}
                or type(details["bytes"]) is not int
                or details["bytes"] != bundle.getinfo(name).file_size
                or not re.fullmatch(r"[a-f0-9]{64}", details["sha256"])
            ):
                raise ValueError("Invalid migration file metadata")
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with bundle.open(name) as source, path.open("xb") as target:
                shutil.copyfileobj(source, target)
            path.chmod(0o600)
            if digest(path) != details["sha256"]:
                raise ValueError("Migration checksum mismatch")
    with ZipFile(root / "database.zip") as database:
        if sum(info.file_size for info in database.infolist()) > MAX_BYTES:
            raise ValueError("Nested database backup exceeds migration size limit")
    verify_backup(root / "database.zip")
    validate_state(root)
    return manifest


def verify(archive: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="radar-migration-verify-") as temporary:
        return _unpack(archive, Path(temporary))


def export(source: Path, config_dir: Path, archive: Path, *, source_stopped: bool) -> dict:
    if not source_stopped:
        raise ValueError("Stop all source writers before exporting")
    if source.is_symlink() or not source.is_file() or archive.exists() or archive.is_symlink():
        raise ValueError("Existing database and new archive required")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as locks, tempfile.TemporaryDirectory(dir=archive.parent) as temporary:
        for path in (
            Path(str(source) + ".lock"),
            source.with_suffix(".watch.json.lock"),
            source.with_suffix(".telegram.json.lock"),
            source.with_suffix(".heartbeat.json.lock"),
            source.with_suffix(".cloud-backups.json.lock"),
        ):
            locks.enter_context(FileLock(str(path), timeout=0))
        root = Path(temporary)
        create_backup(source, root / "database.zip")
        files = {"database.zip": root / "database.zip"}
        for name in CONFIG_FILES:
            files["config/" + name] = config_dir / name
        for suffix in (".telegram.json", ".heartbeat.json"):
            path = source.with_suffix(suffix)
            if suffix == ".telegram.json" or path.exists():
                files["data/jobs" + suffix] = path
        history = source.parent / "health-history"
        if history.is_symlink():
            raise ValueError("Symlinked history is not portable")
        if history.is_dir():
            files.update(
                {
                    "data/health-history/" + p.name: p
                    for p in history.iterdir()
                    if p.suffix == ".json"
                }
            )
        if any(
            not allowed(name) or path.is_symlink() or not path.is_file()
            for name, path in files.items()
        ):
            raise ValueError("Invalid portable state file")
        manifest = {
            "format_version": 1,
            "id": uuid4().hex,
            "created_at": datetime.now(UTC).isoformat(),
            "files": {
                name: {"bytes": path.stat().st_size, "sha256": digest(path)}
                for name, path in files.items()
            },
        }
        staged = root / "migration.zip"
        with ZipFile(staged, "w", compression=ZIP_STORED) as bundle:
            for name, path in files.items():
                bundle.write(path, name)
            bundle.writestr("manifest.json", json.dumps(manifest, separators=(",", ":")))
        if verify(staged) != manifest:
            raise ValueError("Migration verification mismatch")
        staged.chmod(0o600)
        with staged.open("rb") as stream:
            os.fsync(stream.fileno())
        os.link(staged, archive)  # Atomic, never replaces another archive.
        return manifest


def restore(archive: Path, destination: Path) -> dict:
    if os.path.lexists(destination):
        raise ValueError("Restore requires a NEW destination directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(destination) + ".restore.lock", timeout=0):
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            root = Path(temporary)
            manifest = _unpack(archive, root)
            restore_backup(root / "database.zip", root / "data/jobs.db", protected=archive)
            receipt = {
                "format_version": 1,
                "activation_id": manifest["id"],
                "archive_sha256": digest(archive),
                "telegram_binding": validate_state(root),
                "restored_at": datetime.now(UTC).isoformat(),
            }
            (root / "data" / RECEIPT).write_text(json.dumps(receipt), encoding="utf-8")
            (root / "data" / RECEIPT).chmod(0o600)
            destination.mkdir(mode=0o700)  # Exclusive creation, never reuse a partial restore.
            try:
                for name in ("config", "data"):
                    (root / name).rename(destination / name)
            except BaseException:
                shutil.rmtree(destination)
                raise
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("export")
    create.add_argument("database", type=Path)
    create.add_argument("archive", type=Path)
    create.add_argument("--config-dir", type=Path, default=Path("config"))
    create.add_argument("--source-stopped", action="store_true")
    check = commands.add_parser("verify")
    check.add_argument("archive", type=Path)
    recover = commands.add_parser("restore")
    recover.add_argument("archive", type=Path)
    recover.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "export":
            result = export(
                args.database, args.config_dir, args.archive, source_stopped=args.source_stopped
            )
        elif args.command == "verify":
            result = verify(args.archive)
        else:
            result = restore(args.archive, args.destination)
        # Do not print cursor, binding, private paths, credentials or notes.
        print(
            json.dumps(
                {
                    "status": "ok",
                    "operation": args.command,
                    "activation_id": result.get("activation_id", result.get("id")),
                }
            )
        )
        return 0
    except Exception as error:
        print(
            json.dumps({"status": "blocked", "error_type": type(error).__name__}), file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
