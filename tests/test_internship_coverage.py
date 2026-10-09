import json
from datetime import UTC, datetime, timedelta

import pytest

from trading_radar.config import Company
from trading_radar.internship_coverage import internship_coverage

NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)


@pytest.fixture
def rollout(config, repo):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    config.settings.include_internships = True
    config.settings.internship_baseline_at = NOW - timedelta(days=1)
    config.companies["disabled"] = Company(name="Disabled", ats="fixture", enabled=False)
    return config


def record(repo, *, source="test", at=NOW, completed=None, status="successful", marker=True):
    repo.db.execute(
        "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)",
        (
            at.isoformat(),
            json.dumps(
                {
                    "source_results": {
                        source: {
                            "completed_at": (completed or at).isoformat(),
                            "status": status,
                            "internship_baseline_complete": marker,
                        }
                    }
                }
            ),
        ),
    )
    repo.db.commit()


def test_validated_reference_is_observed_and_never_resets_after_failure(rollout, repo):
    record(repo, at=NOW - timedelta(hours=2))
    record(repo, status="failed", marker=False)
    before = repo.db.total_changes
    result = internship_coverage(rollout, NOW)
    assert result["validated_sources"] == result["enabled_sources"] == 1
    assert result["sources"] == {
        "test": {
            "status": "validated",
            "validated_at": (NOW - timedelta(hours=2)).isoformat(),
        }
    }
    assert repo.db.total_changes == before


@pytest.mark.parametrize(
    "status,marker",
    [
        ("failed", True),
        ("partial", True),
        ("degraded", True),
        ("successful", False),
        ("successful", 1),
        ("successful", "true"),
    ],
)
def test_partial_failed_or_coerced_marker_does_not_claim_readiness(rollout, repo, status, marker):
    record(repo, status=status, marker=marker)
    assert internship_coverage(rollout, NOW)["sources"]["test"]["status"] == "pending"


def test_disabled_sources_old_and_future_records_do_not_count(rollout, repo):
    record(repo, source="disabled")
    record(repo, at=NOW - timedelta(days=2))
    record(repo, at=NOW + timedelta(seconds=1))
    record(repo, completed=NOW + timedelta(seconds=1))
    result = internship_coverage(rollout, NOW)
    assert result["validated_sources"] == 0
    assert set(result["sources"]) == {"test"}


def test_unset_baseline_is_explicit_prevalidation_without_fictional_observation(rollout):
    rollout.settings.internship_baseline_at = None
    result = internship_coverage(rollout, NOW)
    assert result["validated_sources"] == 0
    assert result["sources"]["test"] == {"status": "prevalidated", "validated_at": None}


def test_missing_database_is_not_created(rollout, tmp_path):
    path = tmp_path / "absent" / "jobs.db"
    rollout.settings.database_url = f"sqlite:///{path}"
    assert internship_coverage(rollout, NOW)["status"] == "unavailable"
    assert not path.parent.exists()


def test_invalid_observations_do_not_erase_or_manufacture_valid_evidence(rollout, repo):
    for raw in [
        "{bad",
        "[]",
        '{"source_results":{"test":"bad"}}',
        '{"source_results":{"test":true}}',
        '{"source_results":[]}',
    ]:
        repo.db.execute(
            "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)", (NOW.isoformat(), raw)
        )
    repo.db.commit()
    assert internship_coverage(rollout, NOW)["sources"]["test"]["status"] == "pending"
    record(repo)
    assert internship_coverage(rollout, NOW)["sources"]["test"]["status"] == "validated"


def test_reference_survives_a_journal_larger_than_the_previous_row_limit(rollout, repo):
    repo.db.executemany(
        "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)",
        [(NOW.isoformat(), '{"source_results":{"test":{"status":"failed"}}}')] * 10001,
    )
    record(repo)
    before = repo.db.total_changes
    assert internship_coverage(rollout, NOW)["validated_sources"] == 1
    assert repo.db.total_changes == before


def test_timezones_and_scanner_share_the_same_reference_rule(rollout, repo):
    from trading_radar.internship_baseline import observed_baselines
    from trading_radar.scanner import internship_baselined

    # Lexicographical ISO-string comparisons would incorrectly include this old scan.
    old = "2026-10-06T13:00:00+02:00"
    raw = json.dumps(
        {
            "source_results": {
                "test": {
                    "status": "successful",
                    "internship_baseline_complete": True,
                    "completed_at": old,
                }
            }
        }
    )
    repo.db.execute("INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)", (old, raw))
    repo.db.commit()
    assert not observed_baselines(repo.db, {"test"}, rollout.settings.internship_baseline_at, NOW)
    assert not internship_baselined(repo, "test", rollout.settings)
    record(repo, status="failed", marker=True)
    record(repo, completed=NOW + timedelta(seconds=1))
    assert internship_coverage(rollout, NOW)["validated_sources"] == 0
    record(repo, at=NOW - timedelta(hours=1))
    assert internship_baselined(repo, "test", rollout.settings)
    assert internship_coverage(rollout, NOW)["validated_sources"] == 1


@pytest.mark.parametrize("completed", [None, True, 1, {}, [], "0001-01-01T00:00:00+14:00"])
def test_invalid_or_out_of_range_completion_never_interrupts_the_reader(rollout, repo, completed):
    raw = json.dumps(
        {
            "source_results": {
                "test": {
                    "status": "successful",
                    "internship_baseline_complete": True,
                    "completed_at": completed,
                }
            }
        }
    )
    repo.db.execute("INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)", (NOW.isoformat(), raw))
    repo.db.commit()
    assert internship_coverage(rollout, NOW)["sources"]["test"]["status"] == "pending"
    record(repo)
    assert internship_coverage(rollout, NOW)["sources"]["test"]["status"] == "validated"


def test_disabled_rollout_never_reads_the_database(rollout):
    rollout.settings.include_internships = False
    rollout.settings.database_url = "invalid"
    assert internship_coverage(rollout, NOW)["status"] == "disabled"
