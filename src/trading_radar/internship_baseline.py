"""Shared read-only proof of a validated internship reference snapshot."""

import sqlite3
from datetime import datetime

from trading_radar.audit import timestamp

MAX_LENGTH = 1_000_000


def observed_baselines(
    db: sqlite3.Connection, sources: set[str], cutoff: datetime, now: datetime
) -> dict[str, str]:
    """Stream positive proofs, ignoring invalid observations and unrelated history.

    A later failure does not erase a successful reference. There is no journal
    row-count ceiling and no migration; both scanner and dashboard use this rule.
    JSON guards also protect the reader from malformed or oversized old records.
    """
    if not sources or cutoff > now:
        return {}
    placeholders = ",".join("?" for _ in sources)
    rows = db.execute(
        "WITH observations AS ("
        " SELECT s.id,s.created_at,r.key AS source,"
        " CASE WHEN r.type='object' THEN r.value ELSE '{}' END AS record"
        " FROM scan_runs s,json_each("
        " CASE WHEN length(s.metrics)<=? AND json_valid(s.metrics) THEN"
        " CASE WHEN json_type(s.metrics,'$.source_results')='object'"
        " THEN json_extract(s.metrics,'$.source_results') ELSE '{}' END"
        " ELSE '{}' END) r"
        " WHERE julianday(s.created_at)>=julianday(?)"
        " AND julianday(s.created_at)<=julianday(?)"
        f" AND r.key IN ({placeholders})"
        ") SELECT created_at,source,json_extract(record,'$.completed_at') FROM observations"
        " WHERE json_type(record,'$.internship_baseline_complete')='true'"
        " AND json_extract(record,'$.status')='successful' ORDER BY id ASC",
        (MAX_LENGTH, cutoff.isoformat(), now.isoformat(), *sorted(sources)),
    )
    observed: dict[str, str] = {}
    for created, source, completed in rows:
        if source in observed:
            continue
        try:
            recorded_at = timestamp(created)
            completed_at = timestamp(completed)
        except OverflowError:
            continue
        if (
            recorded_at is not None
            and completed_at is not None
            and cutoff <= completed_at <= recorded_at <= now
        ):
            observed[source] = completed_at.isoformat()
            if len(observed) == len(sources):
                break
    return observed
