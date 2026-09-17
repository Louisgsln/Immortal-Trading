"""Verified, bounded backup inventory and retention advice. Never removes files."""

import hashlib
import os
import stat
import unicodedata
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from trading_radar.backups import verify_backup

MAX_ARCHIVES = 100
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024


def _safe_text(value: str) -> str:
    return "".join(
        "\ufffd" if unicodedata.category(char).startswith("C") else char for char in value
    )


def _linked(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _checked_stat(path: Path) -> os.stat_result:
    # Check the lexical ancestors before resolving: resolve() would hide aliases.
    for ancestor in reversed(path.parents):
        if _linked(ancestor.lstat()):
            raise ValueError("unsafe_archive_path")
    info = path.lstat()
    if _linked(info):
        raise ValueError("unsafe_archive_path")
    return info


def _signature(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("invalid_timestamp")
    return value.astimezone(UTC)


def plan_retention(
    directory: Path,
    *,
    keep_latest: int = 7,
    keep_daily: int = 14,
    keep_weekly: int = 8,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Inspect immediate ZIP children and return a conservative, read-only plan.

    Daily and weekly windows include the current UTC day and ISO week. Keep rules
    form a union, with timestamp descending and filename ascending as the tie break.
    Any invalid archive blocks all candidate advice. Files and the directory must
    remain stable throughout inspection; report labels never contain control chars.
    """
    for value, minimum, maximum in (
        (keep_latest, 1, 100),
        (keep_daily, 0, 365),
        (keep_weekly, 0, 104),
    ):
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError("invalid_retention_policy")
    timestamp = _utc(now if now is not None else datetime.now(UTC))
    directory = Path(directory).absolute()
    try:
        directory_stat = _checked_stat(directory)
        if not stat.S_ISDIR(directory_stat.st_mode):
            raise ValueError("invalid_backup_directory")
        paths = sorted(
            (path for path in directory.iterdir() if path.suffix.lower() == ".zip"),
            key=lambda path: path.name,
        )
    except (OSError, ValueError):
        raise ValueError("invalid_backup_directory") from None
    if len(paths) > MAX_ARCHIVES:
        raise ValueError("archive_count_limit")

    # Establish every size budget before opening even the first archive.
    snapshots: dict[Path, os.stat_result] = {}
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    for path in paths:
        entry: dict[str, Any] = {
            "name": _safe_text(path.name),
            "status": "invalid",
            "bytes": 0,
            "decision": "blocked",
            "reasons": ["invalid_archive"],
        }
        entries.append(entry)
        try:
            info = _checked_stat(path)
        except ValueError:
            entry["error"] = "unsafe_archive_path"
            continue
        except OSError:
            entry["error"] = "unreadable_archive"
            continue
        if not stat.S_ISREG(info.st_mode):
            entry["error"] = "non_regular_archive"
            continue
        entry["bytes"] = info.st_size
        if info.st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("archive_size_limit")
        total_bytes += info.st_size
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError("archive_total_size_limit")
        snapshots[path] = info

    dates: dict[int, datetime] = {}
    for index, (path, entry) in enumerate(zip(paths, entries, strict=True)):
        before = snapshots.get(path)
        if before is None:
            continue
        try:
            if _signature(_checked_stat(path)) != _signature(before):
                entry["error"] = "archive_changed"
                continue
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            manifest = verify_backup(path)
            if _signature(_checked_stat(path)) != _signature(before):
                entry["error"] = "archive_changed"
                continue
        except Exception:
            # Verification exceptions can include paths, manifest data or SQL.
            entry["error"] = "invalid_backup"
            continue
        try:
            created_at = _utc(datetime.fromisoformat(manifest["created_at"]))
        except (TypeError, ValueError, KeyError, OverflowError):
            entry["error"] = "invalid_created_at"
            continue
        if created_at > timestamp:
            entry["error"] = "future_created_at"
            continue
        dates[index] = created_at
        entry.update(status="valid", created_at=created_at.isoformat(), sha256=digest)

    # An archive already verified must also stay unchanged while later ones run.
    for index, (path, entry) in enumerate(zip(paths, entries, strict=True)):
        if entry["status"] != "valid":
            continue
        try:
            unchanged = _signature(_checked_stat(path)) == _signature(snapshots[path])
        except (OSError, ValueError):
            unchanged = False
        if not unchanged:
            dates.pop(index)
            entry.update(status="invalid", error="archive_changed")
            entry.pop("sha256", None)
            entry.pop("created_at", None)
    try:
        if _signature(_checked_stat(directory)) != _signature(directory_stat):
            raise ValueError("backup_directory_changed")
    except (OSError, ValueError):
        raise ValueError("backup_directory_changed") from None

    invalid = len(entries) - len(dates)
    ordered = sorted(
        sorted(dates, key=lambda index: paths[index].name), key=dates.__getitem__, reverse=True
    )
    daily_seen: set[date] = set()
    weekly_seen: set[date] = set()
    today = timestamp.date()
    monday = today - timedelta(days=today.weekday())
    for position, index in enumerate(ordered):
        entry = entries[index]
        if invalid:
            entry.update(decision="keep", reasons=["retained_due_to_incomplete_audit"])
            continue
        reasons = []
        created_day = dates[index].date()
        week = created_day - timedelta(days=created_day.weekday())
        if position < keep_latest:
            reasons.append("latest")
        if 0 <= (today - created_day).days < keep_daily and created_day not in daily_seen:
            reasons.append("daily")
            daily_seen.add(created_day)
        if 0 <= (monday - week).days < keep_weekly * 7 and week not in weekly_seen:
            reasons.append("weekly")
            weekly_seen.add(week)
        entry.update(
            decision="keep" if reasons else "candidate", reasons=reasons or ["outside_retention"]
        )
    # Valid archives are chronological; invalid entries follow, ordered by filename.
    report_entries = [entries[index] for index in ordered] + [
        entry for entry in entries if entry["status"] == "invalid"
    ]
    candidates = [entry for entry in entries if entry["decision"] == "candidate"]
    return {
        "format_version": 1,
        "generated_at": timestamp.isoformat(),
        "directory": _safe_text(str(directory)),
        "policy": {
            "keep_latest": keep_latest,
            "keep_daily": keep_daily,
            "keep_weekly": keep_weekly,
        },
        "status": "blocked" if invalid else "ok" if entries else "empty",
        "entries": report_entries,
        "summary": {
            "archives": len(entries),
            "valid": len(dates),
            "invalid": invalid,
            "kept": sum(entry["decision"] == "keep" for entry in entries),
            "candidates": len(candidates),
            "bytes_total": total_bytes,
            "candidate_bytes": sum(entry["bytes"] for entry in candidates),
        },
        "deletion_performed": False,
    }
