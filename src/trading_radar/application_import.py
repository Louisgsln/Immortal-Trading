"""Preview and atomically import reviewed tracking edits; no application submission."""

import hashlib
import json
import sqlite3
from pathlib import Path

from filelock import FileLock

from trading_radar.applications import Application
from trading_radar.backups import create_backup, database_path
from trading_radar.config import Config
from trading_radar.score_audit import job_snapshot
from trading_radar.storage import Repository


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def read_import(path: Path) -> tuple[list[dict], str]:
    with path.open("rb") as stream:
        content = stream.read(2_000_001)
    if len(content) > 2_000_000:
        raise ValueError("Import exceeds size limit")
    payload = json.loads(content, object_pairs_hook=_unique_object)
    if (
        not isinstance(payload, dict)
        or set(payload) != {"format_version", "applications"}
        or type(payload["format_version"]) is not int
        or payload["format_version"] != 1
        or not isinstance(payload["applications"], list)
        or not 1 <= len(payload["applications"]) <= 1000
    ):
        raise ValueError("Invalid application import")
    seen = set()
    for item in payload["applications"]:
        if (
            not isinstance(item, dict)
            or "job_id" not in item
            or len(item) < 2
            or set(item) - set(Application.model_fields)
            or not isinstance(item["job_id"], str)
            or not 1 <= len(item["job_id"]) <= 128
            or any(value is not None and not isinstance(value, str) for value in item.values())
        ):
            raise ValueError("Invalid tracking edit")
        for value in item.values():
            if value is not None:
                value.encode("utf-8")
        if item["job_id"] in seen:
            raise ValueError("Duplicate job ID")
        seen.add(item["job_id"])
    return payload["applications"], hashlib.sha256(content).hexdigest()


def _plan(db: sqlite3.Connection, edits: list[dict], digest: str) -> dict:
    entries = []
    for edit in edits:
        row = db.execute(
            "SELECT a.* FROM applications a JOIN jobs j ON j.id=a.job_id WHERE a.job_id=?",
            (edit["job_id"],),
        ).fetchone()
        if row is None:
            raise ValueError("Unknown job ID")
        keys = list(Application.model_fields)
        previous = Application.model_validate(dict(zip(keys, row, strict=True)))
        updated = Application.model_validate(previous.model_dump() | edit)
        before, after = previous.model_dump(mode="json"), updated.model_dump(mode="json")
        entries.append(
            {
                "job_id": previous.job_id,
                "changes": sorted(key for key in before if before[key] != after[key]),
                "before": before,
                "after": after,
            }
        )
    token = hashlib.sha256(
        json.dumps({"file_sha256": digest, "entries": entries}, sort_keys=True).encode()
    ).hexdigest()
    return {
        "read_only": True,
        "preview_token": token,
        "records": len(entries),
        "changed": sum(bool(entry["changes"]) for entry in entries),
        "entries": entries,
    }


def preview_import(config: Config, path: Path) -> dict:
    edits, digest = read_import(path)
    with job_snapshot(config) as db:
        return _plan(db, edits, digest)


def apply_import(config: Config, path: Path, expected: str, backup: Path) -> dict:
    edits, digest = read_import(path)
    database = database_path(config.settings.database_url)
    with FileLock(str(database) + ".lock", timeout=0):
        with job_snapshot(config) as db:
            plan = _plan(db, edits, digest)
        if expected != plan["preview_token"]:
            raise ValueError("Tracking or input changed; preview again")
        if not plan["changed"]:
            return {**plan, "read_only": False, "backup": None}
        manifest = create_backup(database, backup)
        repo = Repository(config.settings.database_url, existing_only=True)
        try:
            with repo.transaction():
                repo.db.execute("BEGIN IMMEDIATE")
                current = _plan(repo.db, edits, digest)
                if current["preview_token"] != expected:
                    raise ValueError("Tracking changed; preview again")
                for entry in current["entries"]:
                    if entry["changes"]:
                        repo.record_application_update(
                            entry["job_id"],
                            {key: entry["after"][key] for key in entry["changes"]},
                        )
        finally:
            repo.close()
        return {
            **plan,
            "read_only": False,
            "backup": str(backup.resolve()),
            "backup_sha256": manifest["sha256"],
        }
