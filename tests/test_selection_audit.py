"""Observed filter coverage reconciles without expanding searches or exposing hidden posts."""

import pytest
from test_employer_expansion_95_97 import gh_row
from test_scanner import run

from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.models import Collection, SelectionSummary, utcnow
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason
from trading_radar.source_history import source_history


def test_title_rejection_reports_exact_reason_and_retains_grade_preferences():
    options = SearchOptions()
    assert rejection_reason("Graduate FX Trader", options) is None
    assert rejection_reason("Trading Analyst / Associate", options) is None
    assert rejection_reason("Senior FX Trader", options) == "excluded_title:senior"
    assert rejection_reason("Desk Analyst", options) == "no_title_match"


def test_greenhouse_catalogue_counts_include_prospects_without_displaying_them():
    config = load_config().companies["engineers_gate"]
    selected = gh_row("engineers_gate")
    rejected = gh_row(
        "engineers_gate",
        id=124,
        absolute_url=selected["absolute_url"].replace("123", "124"),
        title="Office Administrator",
    )
    prospect = gh_row(
        "engineers_gate",
        id=125,
        absolute_url=selected["absolute_url"].replace("123", "125"),
        title="Confidential prospect",
        internal_job_id=None,
    )
    audit = SelectionAudit("public_catalogue")
    jobs = parse_board(
        {"meta": {"total": 3}, "jobs": [selected, rejected, prospect]},
        "engineers_gate",
        config,
        GreenhouseOptions(**config.options),
        audit,
    )
    summary = audit.summary()
    assert len(jobs) == summary.selected == 1
    assert summary.examined == 3 and summary.rejected == {"no_title_match": 1, "prospect": 1}
    assert "Confidential" not in summary.model_dump_json()


def test_sample_limit_does_not_limit_rejection_counts():
    audit = SelectionAudit("search_results")
    for index in range(100):
        audit.record("no_title_match", f"Office Administrator {index}", str(index))
    summary = audit.summary()
    assert summary.examined == 100 and len(summary.samples) == 30


def test_invalid_selection_counts_rejected():
    with pytest.raises(ValueError):
        SelectionSummary(scope="search_results", examined=3, selected=2)


def test_scanner_and_read_only_history_preserve_observed_selection(config, repo, raw):
    selection = SelectionSummary(
        scope="search_results", examined=3, selected=1, rejected={"no_title_match": 2}
    )
    archived = Collection(jobs=[raw], selection=selection).model_dump_json()
    assert Collection.model_validate_json(archived).selection == selection

    class Collector:
        async def collect(self):
            return Collection(jobs=[raw], selection=selection)

    metrics = run(config, repo, {"test": Collector()})
    assert metrics.source_results["test"]["selection"] == selection.model_dump()
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    before = repo.db.total_changes
    result = source_history(config, utcnow())
    assert result["sources"]["test"]["latest"][0]["selection"] == selection.model_dump()
    assert repo.db.total_changes == before
