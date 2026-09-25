"""Read unresolved collection conflicts from the existing scan journal."""

import json
import sqlite3

from pydantic import TypeAdapter

from trading_radar.models import CollectionConflict


def source_observation(db: sqlite3.Connection, source: str, since: str | None, field: str):
    """Read only the newest source observation since its last relevant attempt."""
    if field not in {"listing_gaps", "failed"}:
        raise ValueError("Unknown collection observation")
    row = db.execute(
        "SELECT entry.value FROM scan_runs, "
        "json_each(CASE WHEN json_valid(metrics) THEN metrics ELSE '{}' END, ?) entry "
        "WHERE entry.key=? AND created_at>=? ORDER BY scan_runs.id DESC LIMIT 1",
        ("$." + field, source, since or ""),
    ).fetchone()
    return row[0] if row else None


def source_listing_gaps(db: sqlite3.Connection, source: str, last_success: str | None) -> list[str]:
    value = source_observation(db, source, last_success, "listing_gaps")
    return TypeAdapter(list[str]).validate_json(value) if value else []


def source_conflicts(db: sqlite3.Connection, source: str, last_success: str | None) -> list[dict]:
    # A later clean scan resolves the quarantine. Unrelated scans and subsequent
    # transport failures must not erase the evidence of an unresolved conflict.
    row = db.execute(
        "SELECT entry.value FROM scan_runs, "
        "json_each(CASE WHEN json_valid(metrics) THEN metrics ELSE '{}' END, '$.degraded') entry "
        "WHERE entry.key=? AND created_at>=? ORDER BY scan_runs.id DESC LIMIT 1",
        (source, last_success or ""),
    ).fetchone()
    if row is None:
        return []
    conflicts = TypeAdapter(list[CollectionConflict]).validate_python(json.loads(row[0]))
    return [conflict.model_dump(mode="json") for conflict in conflicts]


def quarantined_sources(db: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in db.execute("SELECT source,last_success FROM companies")
        if source_conflicts(db, row[0], row[1])
    }
