"""Explicit, immutable health snapshots stored separately from business SQLite data."""

import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_radar.config import Config
from trading_radar.health import check_health

FORMAT_VERSION = 1
MAX_REPORT_BYTES = 2 * 1024 * 1024
STATUSES = {"healthy", "degraded", "critical"}
ID_PATTERN = re.compile(r"\d{8}T\d{12}Z-[0-9a-f]{32}")
SOURCE_RANK = {
    "fresh": 0,
    "recent_failure": 1,
    "partial": 1,
    "collection_degraded": 1,
    "access_restricted": 1,
    "stale": 2,
    "never_scanned": 2,
    "invalid_timestamp": 2,
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Time must be an ISO 8601 timestamp with a timezone") from None
    if parsed.tzinfo is None:
        raise ValueError("Time must include a timezone")
    return parsed.astimezone(UTC)


def _validate_report(report: Any) -> None:
    if not isinstance(report, dict):
        raise ValueError("Invalid health report")
    if report.get("status") not in STATUSES or type(report.get("ready")) is not bool:
        raise ValueError("Invalid health status")
    if report["ready"] != (report["status"] != "critical"):
        raise ValueError("Inconsistent health status")
    parse_time(report.get("generated_at"))
    if (
        not isinstance(report.get("database"), dict)
        or not isinstance(report["database"].get("status"), str)
        or not isinstance(report.get("source_summary"), dict)
    ):
        raise ValueError("Invalid health database or source summary")
    if not isinstance(report.get("sources"), list) or not isinstance(report.get("issues"), list):
        raise ValueError("Invalid health details")
    names = set()
    for source in report["sources"]:
        if (
            not isinstance(source, dict)
            or not isinstance(source.get("source"), str)
            or source.get("status") not in SOURCE_RANK
            or source["source"] in names
        ):
            raise ValueError("Invalid source health")
        names.add(source["source"])
    for issue in report["issues"]:
        if not isinstance(issue, dict) or not isinstance(issue.get("code"), str):
            raise ValueError("Invalid health issue")


def _history_path(directory: Path, config: Config) -> Path:
    url = config.settings.database_url
    if not url.startswith("sqlite:///") or url in {"sqlite:///", "sqlite:///:memory:"}:
        raise ValueError("Monitoring requires a file-backed SQLite database")
    database = Path(url.removeprefix("sqlite:///")).resolve()
    root = directory.resolve()
    protected = [
        Path(str(database) + suffix).resolve()
        for suffix in ("", "-wal", "-shm", "-journal", ".lock")
    ]
    if any(root == path or path in root.parents for path in protected):
        raise ValueError("Health history must be separate from database files and locks")
    if root.exists() and not root.is_dir():
        raise ValueError("Health history must be a directory")
    return root


def record_health(
    config: Config,
    directory: Path = Path("data/health-history"),
    max_age_hours: float = 24,
    now: datetime | None = None,
) -> dict:
    """Record even critical health; never create or migrate the primary database."""
    root = _history_path(directory, config)
    if now is not None and now.tzinfo is None:
        raise ValueError("Monitoring time must include a timezone")
    report = check_health(config, max_age_hours=max_age_hours, now=now)
    _validate_report(report)
    instant = parse_time(report["generated_at"])
    identifier = instant.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex
    envelope = {
        "format_version": FORMAT_VERSION,
        "id": identifier,
        "recorded_at": instant.isoformat(),
        "report": report,
    }
    envelope["sha256"] = hashlib.sha256(_canonical(envelope)).hexdigest()
    encoded = _canonical(envelope)
    if len(encoded) > MAX_REPORT_BYTES:
        raise ValueError("Health report exceeds the archive size limit")
    root.mkdir(parents=True, exist_ok=True)
    # A hard link exposes only a fully flushed file and fails if the target exists.
    # This also works on Windows NTFS; no replace/rename overwrites another snapshot.
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".health-", suffix=".tmp", dir=root, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, root / f"{identifier}.json")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return envelope


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields in health snapshot")
        result[key] = value
    return result


def read_snapshot(directory: Path, identifier: str) -> dict:
    if not ID_PATTERN.fullmatch(identifier):
        raise ValueError("Invalid health snapshot identifier")
    path = directory / f"{identifier}.json"
    if path.is_symlink():
        raise ValueError("Health snapshots must not be symbolic links")
    with path.open("rb") as stream:
        raw = stream.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("Health snapshot exceeds the archive size limit")
    try:
        snapshot = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(snapshot, dict) or set(snapshot) != {
            "format_version",
            "id",
            "recorded_at",
            "report",
            "sha256",
        }:
            raise ValueError("Invalid health snapshot envelope")
        if (
            type(snapshot["format_version"]) is not int
            or snapshot["format_version"] != FORMAT_VERSION
        ):
            raise ValueError("Unsupported health snapshot format")
        if snapshot["id"] != identifier:
            raise ValueError("Health snapshot identifier does not match its filename")
        checksum = snapshot["sha256"]
        payload = {key: value for key, value in snapshot.items() if key != "sha256"}
        if checksum != hashlib.sha256(_canonical(payload)).hexdigest():
            raise ValueError("Health snapshot checksum mismatch")
        instant = parse_time(snapshot["recorded_at"])
        if not identifier.startswith(instant.strftime("%Y%m%dT%H%M%S%fZ") + "-"):
            raise ValueError("Health snapshot timestamp does not match its identifier")
        _validate_report(snapshot["report"])
        if parse_time(snapshot["report"]["generated_at"]) != instant:
            raise ValueError("Health report and archive timestamps differ")
    except (TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid health snapshot contents") from exc
    return snapshot


def compare_snapshots(previous: dict, current: dict) -> dict:
    """Compare observations, explicitly distinguish added/removed source coverage."""
    before, after = previous["report"], current["report"]
    rank = {"healthy": 0, "degraded": 1, "critical": 2}
    sources_comparable = all(
        report.get("database", {}).get("status") == "ok" for report in (before, after)
    )
    old = (
        {source["source"]: source["status"] for source in before["sources"]}
        if sources_comparable
        else {}
    )
    new = (
        {source["source"]: source["status"] for source in after["sources"]}
        if sources_comparable
        else {}
    )
    changes = []
    for source in sorted(old.keys() | new.keys()):
        if old.get(source) == new.get(source):
            continue
        if source not in old:
            change = "added"
        elif source not in new:
            change = "removed"
        else:
            delta = SOURCE_RANK[new[source]] - SOURCE_RANK[old[source]]
            change = "regressed" if delta > 0 else "improved" if delta < 0 else "changed"
        changes.append(
            {
                "source": source,
                "before": old.get(source),
                "after": new.get(source),
                "change": change,
            }
        )
    return {
        "previous_id": previous["id"],
        "current_id": current["id"],
        "before": before["status"],
        "after": after["status"],
        "regressed": rank[after["status"]] > rank[before["status"]],
        "sources_comparable": sources_comparable,
        "same_freshness_threshold": before.get("max_age_hours") == after.get("max_age_hours"),
        "source_changes": changes,
    }


def history(
    directory: Path = Path("data/health-history"),
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    if status is not None and status not in STATUSES:
        raise ValueError("Status must be healthy, degraded or critical")
    if not 1 <= limit <= 200 or offset < 0:
        raise ValueError("Limit must be 1..200 and offset must be nonnegative")
    start, end = parse_time(since) if since else None, parse_time(until) if until else None
    if start and end and start > end:
        raise ValueError("Since must not be after until")
    if directory.exists() and not directory.is_dir():
        raise ValueError("Health history must be a directory")
    snapshots = []
    # Validate every published JSON, including rows excluded by a filter. Never hide corruption.
    for path in directory.glob("*.json"):
        snapshots.append(read_snapshot(directory, path.stem))
    snapshots.sort(key=lambda row: (row["recorded_at"], row["id"]), reverse=True)
    comparison = compare_snapshots(snapshots[1], snapshots[0]) if len(snapshots) > 1 else None
    matching = [
        row
        for row in snapshots
        if (
            (status is None or row["report"]["status"] == status)
            and (start is None or parse_time(row["recorded_at"]) >= start)
            and (end is None or parse_time(row["recorded_at"]) <= end)
        )
    ]
    rows = [
        {
            "id": row["id"],
            "recorded_at": row["recorded_at"],
            "status": row["report"]["status"],
            "ready": row["report"]["ready"],
            "source_summary": row["report"].get("source_summary", {}),
            "issues": row["report"]["issues"],
        }
        for row in matching[offset : offset + limit]
    ]
    return {
        "total": len(snapshots),
        "matching": len(matching),
        "limit": limit,
        "offset": offset,
        "snapshots": rows,
        "latest_comparison": comparison,
    }
