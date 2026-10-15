"""Journal batching preserves per-source quarantine, gaps and recovery evidence."""

import json
import sqlite3

import pytest

from trading_radar.collection_diagnostics import (
    quarantined_sources,
    source_observations,
    sources_conflicts,
    sources_listing_gaps,
)

EARLY = "2026-10-14T10:00:00+00:00"
LATE = "2026-10-15T10:00:00+00:00"
CONFLICT = {"external_id": "123", "urls": ["https://example.com/123"], "fields": ["title"]}


def append(db, metrics, when=EARLY):
    raw = json.dumps(metrics) if isinstance(metrics, dict) else metrics
    db.execute("INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)", (when, raw))
    db.commit()


def legacy(db, cutoffs, field):
    observations = {}
    for source, cutoff in cutoffs.items():
        row = db.execute(
            "SELECT entry.value FROM scan_runs,"
            " json_each(CASE WHEN json_valid(metrics) THEN metrics ELSE '{}' END, ?) entry"
            " WHERE entry.key=? AND created_at>=? ORDER BY scan_runs.id DESC LIMIT 1",
            ("$." + field, source, cutoff or ""),
        ).fetchone()
        if row is not None:
            observations[source] = row[0]
    return observations


@pytest.mark.parametrize("field", ["degraded", "listing_gaps", "failed"])
def test_batch_matches_individual_cutoffs_missing_keys_and_invalid_json(repo, field):
    append(repo.db, {field: {"older": ["old"], "no-success": ["kept"], "cleared": ["old"]}})
    append(repo.db, "not-json", LATE)
    append(repo.db, {field: {"unrelated": []}}, LATE)
    append(repo.db, {field: {"cleared": []}}, LATE)
    cutoffs = {"older": LATE, "no-success": None, "cleared": EARLY, "absent": ""}
    expected = legacy(repo.db, cutoffs, field)
    assert source_observations(repo.db, cutoffs, field) == expected
    assert expected == {"no-success": '["kept"]', "cleared": "[]"}


@pytest.mark.parametrize("field", ["degraded", "listing_gaps", "failed"])
@pytest.mark.parametrize("value", [None, [], {}, "", 0, False, "access restricted: HTTP 403"])
def test_present_values_are_preserved_including_null_and_empty(repo, field, value):
    append(repo.db, {field: {"test": ["previous"]}})
    append(repo.db, {field: {"test": value}}, LATE)
    cutoffs = {"test": None}
    assert source_observations(repo.db, cutoffs, field) == legacy(repo.db, cutoffs, field)


@pytest.mark.parametrize("field", ["degraded", "listing_gaps", "failed"])
def test_latest_scan_id_wins_and_duplicate_keys_keep_first_observation(repo, field):
    append(repo.db, {field: {"test": "later timestamp"}}, LATE)
    append(repo.db, '{"' + field + '":{"test":"first","test":"duplicate"}}', EARLY)
    cutoffs = {"test": None}
    assert source_observations(repo.db, cutoffs, field) == {"test": "first"}
    assert source_observations(repo.db, cutoffs, field) == legacy(repo.db, cutoffs, field)


def test_json_request_map_handles_source_names_without_sql_or_path_interpolation(repo):
    names = ["bank.us", 'campus["uk"]', "banque-école", "'); DROP TABLE jobs; --"]
    append(repo.db, {"failed": dict.fromkeys(names, "HTTP 403")})
    cutoffs = dict.fromkeys(names)
    assert source_observations(repo.db, cutoffs, "failed") == dict.fromkeys(names, "HTTP 403")
    assert repo.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_hundreds_of_sources_use_one_read_and_no_writes(repo):
    cutoffs = {f"source-{i}": EARLY for i in range(1200)}
    append(repo.db, {"listing_gaps": {source: [] for source in cutoffs}})
    statements = []
    before = repo.db.total_changes
    repo.db.set_trace_callback(statements.append)
    try:
        assert sources_listing_gaps(repo.db, cutoffs) == {source: [] for source in cutoffs}
    finally:
        repo.db.set_trace_callback(None)
    assert len(statements) == 1
    assert repo.db.total_changes == before


def test_empty_inventory_never_reads_journal_and_invalid_field_is_rejected(repo):
    statements = []
    repo.db.set_trace_callback(statements.append)
    try:
        assert source_observations(repo.db, {}, "failed") == {}
        assert sources_conflicts(repo.db, {}) == {}
        assert sources_listing_gaps(repo.db, {}) == {}
        with pytest.raises(ValueError, match="Unknown collection observation"):
            source_observations(repo.db, {}, "arbitrary")
    finally:
        repo.db.set_trace_callback(None)
    assert not statements


def test_conflicts_survive_unrelated_scans_and_failure_then_clear_on_clean_commit(repo):
    repo.db.execute("INSERT INTO companies(source,last_success) VALUES('test',?)", (EARLY,))
    append(repo.db, {"degraded": {"test": [CONFLICT]}})
    append(repo.db, {"failed": {"test": "transport failure"}}, LATE)
    append(repo.db, {"degraded": {"unrelated": []}}, LATE)
    assert sources_conflicts(repo.db, {"test": EARLY}) == {"test": [CONFLICT]}
    assert quarantined_sources(repo.db) == {"test"}
    append(repo.db, {"degraded": {"test": []}}, LATE)
    assert sources_conflicts(repo.db, {"test": EARLY}) == {"test": []}
    assert not quarantined_sources(repo.db)


@pytest.mark.parametrize("value", [None, "not-json", ["invalid conflict"], {}])
def test_malformed_present_conflicts_cannot_erase_quarantine_silently(repo, value):
    append(repo.db, {"degraded": {"test": value}})
    with pytest.raises((TypeError, ValueError)):
        sources_conflicts(repo.db, {"test": None})


def test_read_only_snapshot_stays_consistent_while_next_read_sees_new_commit(repo):
    append(repo.db, {"listing_gaps": {"test": ["missing details"]}})
    path = repo.db.execute("PRAGMA database_list").fetchone()[2]
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as reader:
        reader.execute("PRAGMA query_only=ON")
        reader.execute("BEGIN")
        assert sources_listing_gaps(reader, {"test": None}) == {"test": ["missing details"]}
        append(repo.db, {"listing_gaps": {"test": []}}, LATE)
        assert sources_listing_gaps(reader, {"test": None}) == {"test": ["missing details"]}
        reader.rollback()
        assert sources_listing_gaps(reader, {"test": None}) == {"test": []}
