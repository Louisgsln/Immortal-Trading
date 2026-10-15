"""Read unresolved collection conflicts from the existing scan journal."""

import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from typing import Any

from pydantic import TypeAdapter

from trading_radar.models import CollectionConflict

_GAPS = TypeAdapter(list[str])
_CONFLICTS = TypeAdapter(list[CollectionConflict])


def source_observations(
    db: sqlite3.Connection, cutoffs: Mapping[str, str | None], field: str
) -> dict[str, Any]:
    """Read the latest observation per source in one journal traversal.

    Each source retains its own cutoff. A missing key never clears earlier
    evidence, whereas a present empty value does. Read newest rows first and
    stop once every requested source has an observation; never cache live state.
    """
    if field not in {"degraded", "listing_gaps", "failed"}:
        raise ValueError("Unknown collection observation")
    if not cutoffs:
        return {}
    since = {source: cutoff or "" for source, cutoff in cutoffs.items()}
    # Materialize the small request map once, rather than expanding the same
    # scan JSON once for each employer. One JSON parameter also avoids SQLite's
    # variable limit as the source inventory grows. CROSS JOIN preserves the
    # journal-first traversal and the indexed descending scan order.
    observations: dict[str, Any] = {}
    with closing(
        db.execute(
            "WITH requested AS MATERIALIZED ("
            " SELECT key AS source,value AS since FROM json_each(?)"
            ") SELECT entry.key,entry.value FROM scan_runs s"
            " CROSS JOIN json_each("
            " CASE WHEN json_valid(s.metrics) THEN s.metrics ELSE '{}' END, ?) entry"
            " JOIN requested r ON r.source=entry.key"
            " WHERE s.created_at>=? AND s.created_at>=r.since ORDER BY s.id DESC",
            (json.dumps(since), "$." + field, min(since.values())),
        )
    ) as rows:
        for source, value in rows:
            if source not in observations:
                observations[source] = value
                if len(observations) == len(since):
                    break
    return observations


def sources_conflicts(
    db: sqlite3.Connection, cutoffs: Mapping[str, str | None]
) -> dict[str, list[dict]]:
    observations = source_observations(db, cutoffs, "degraded")
    return {
        source: [
            conflict.model_dump(mode="json")
            for conflict in _CONFLICTS.validate_python(json.loads(observations[source]))
        ]
        if source in observations
        else []
        for source in cutoffs
    }


def sources_listing_gaps(
    db: sqlite3.Connection, cutoffs: Mapping[str, str | None]
) -> dict[str, list[str]]:
    observations = source_observations(db, cutoffs, "listing_gaps")
    return {
        source: _GAPS.validate_json(observations[source]) if observations.get(source) else []
        for source in cutoffs
    }


def source_observation(db: sqlite3.Connection, source: str, since: str | None, field: str):
    """Read only the newest source observation since its last relevant attempt."""
    if field not in {"listing_gaps", "failed"}:
        raise ValueError("Unknown collection observation")
    return source_observations(db, {source: since}, field).get(source)


def source_listing_gaps(db: sqlite3.Connection, source: str, last_success: str | None) -> list[str]:
    return sources_listing_gaps(db, {source: last_success})[source]


def source_conflicts(db: sqlite3.Connection, source: str, last_success: str | None) -> list[dict]:
    # A later clean scan resolves the quarantine. Unrelated scans and subsequent
    # transport failures must not erase the evidence of an unresolved conflict.
    return sources_conflicts(db, {source: last_success})[source]


def quarantined_sources(db: sqlite3.Connection) -> set[str]:
    cutoffs = dict(db.execute("SELECT source,last_success FROM companies"))
    return {source for source, conflicts in sources_conflicts(db, cutoffs).items() if conflicts}
