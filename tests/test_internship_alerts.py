from datetime import UTC, datetime, timedelta

import pytest

from tests.test_dashboard_data import fingerprints
from tests.test_internship_coverage import record
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.internship_alerts import alert_criteria
from trading_radar.models import Score
from trading_radar.normalizer import normalize
from trading_radar.programmes import programme_alertable

NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)


@pytest.fixture
def stage(config, repo, raw):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    config.settings.include_internships = True
    config.settings.internship_alerts_enabled = True
    config.settings.internship_baseline_at = None
    config.settings.internship_target_year = 2027
    config.settings.internship_formats = ["off_cycle", "long"]
    config.settings.alert_min_score = 70
    raw.title = "2027 FX Trading Off-cycle Internship"
    raw.employment_type = "Internship"
    raw.description = "Duration: 6 months. Python, derivatives trading."
    raw.expected_start_date = "March 2027"
    raw.application_deadline = None
    job = normalize(raw)
    job.score_breakdown = Score(trading=30, junior=20, start=15, front_office=15)
    return config, job


def observe(stage, repo, tmp_path):
    config, job = stage
    with repo.transaction():
        repo.upsert(job)
    before = fingerprints(repo)
    result = build_dashboard_data(config, tmp_path / "history", now=NOW)
    assert result["status"] == "ok"
    assert fingerprints(repo) == before
    return result


def codes(result):
    return {reason["code"] for reason in result["jobs"][0]["internship_alert"]["reasons"]}


def test_criteria_explain_future_alerts_without_claiming_or_sending_one(stage, repo, tmp_path):
    result = observe(stage, repo, tmp_path)
    criteria = result["jobs"][0]["internship_alert"]
    assert criteria["status"] == "eligible" and criteria["reasons"] == []
    assert criteria["reference_status"] == "prevalidated"
    assert result["internship_summary"]["formats"] == {"off_cycle": 1, "long": 1}
    assert result["internship_summary"]["criteria_met"] == 1
    assert not repo.pending()
    assert repo.db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0


@pytest.mark.parametrize(
    "title,start,description,expected",
    [
        ("2027 Trading Summer Internship", None, "", "summer_excluded"),
        ("Trading Off-cycle Internship", None, "", "year_unconfirmed"),
        ("2027 Trading Internship", None, "", "format_unconfirmed"),
        ("2026 Trading Off-cycle Internship", "March 2026", "", "year_outside_scope"),
        ("2027 Trading Off-cycle Internship", "March 2026", "", "programme_conflict"),
        ("2027 Trading Summer Off-cycle Internship", None, "", "programme_conflict"),
    ],
)
def test_programme_blockers_match_the_actual_alert_policy(
    stage, repo, tmp_path, title, start, description, expected
):
    config, job = stage
    job.title = title
    from trading_radar.normalizer import normalize_text

    job.title_normalized = normalize_text(title)
    job.expected_start_date = start
    job.description = job.description_text = description
    result = observe(stage, repo, tmp_path)
    assert result["jobs"][0]["internship_alert"]["status"] == "blocked"
    assert expected in codes(result)
    assert not programme_alertable(job, config.settings)


@pytest.mark.parametrize(
    "flag,reason",
    [
        ("include_internships", "internships_disabled"),
        ("internship_alerts_enabled", "internship_alerts_disabled"),
        ("alerts_enabled", "alerts_disabled"),
    ],
)
def test_disabled_configuration_is_explained_without_changing_it(
    stage, repo, tmp_path, flag, reason
):
    setattr(stage[0].settings, flag, False)
    result = observe(stage, repo, tmp_path)
    assert reason in codes(result)
    assert getattr(stage[0].settings, flag) is False


def test_reference_and_configuration_are_live_despite_cached_employer_facts(stage, repo, tmp_path):
    config, _ = stage
    config.settings.internship_baseline_at = NOW - timedelta(days=1)
    assert "reference_pending" in codes(observe(stage, repo, tmp_path))
    record(repo, at=NOW - timedelta(hours=1))
    assert observe(stage, repo, tmp_path)["jobs"][0]["internship_alert"]["status"] == "eligible"
    config.settings.alert_min_score = 85
    assert "score_below_threshold" in codes(observe(stage, repo, tmp_path))
    config.settings.alert_min_score = 70
    config.companies["test"].enabled = False
    assert "source_disabled" in codes(observe(stage, repo, tmp_path))


def test_expired_deadline_and_radar_exclusions_remain_blockers(stage, repo, tmp_path):
    _, job = stage
    job.application_deadline = NOW - timedelta(seconds=1)
    job.score_breakdown.exclusions = ["Outside target roles"]
    result = observe(stage, repo, tmp_path)
    assert {"expired", "excluded"} <= codes(result)
    assert result["internship_summary"]["available"] == 0


def test_current_inactive_state_is_read_without_caching_it(stage, repo, tmp_path):
    _, job = stage
    result = observe(stage, repo, tmp_path)
    serialized = result["jobs"][0]
    serialized["is_active"] = False
    criteria = alert_criteria(
        serialized, stage[0], result["internship_coverage"], {"status": "fresh"}
    )
    assert "inactive" in {reason["code"] for reason in criteria["reasons"]}
    assert criteria["status"] == "blocked"


def test_missing_proof_is_unavailable_and_conflicts_block(stage, repo, tmp_path):
    result = observe(stage, repo, tmp_path)
    job = result["jobs"][0]
    criteria = alert_criteria(job, stage[0], {"status": "unavailable"}, {"status": "fresh"})
    assert criteria["status"] == "unavailable"
    assert [reason["code"] for reason in criteria["reasons"]] == ["reference_unavailable"]
    criteria = alert_criteria(
        job,
        stage[0],
        result["internship_coverage"],
        {
            "status": "collection_degraded",
            "collection_conflicts": [{"fields": ["title"]}],
        },
    )
    assert criteria["status"] == "blocked" and criteria["warnings"]
    assert "source_conflicts" in {reason["code"] for reason in criteria["reasons"]}


@pytest.mark.parametrize("status", ["partial", "recent_failure", "stale"])
def test_transport_or_listing_warning_is_separate_from_confirmed_criteria(
    stage, repo, tmp_path, status
):
    result = observe(stage, repo, tmp_path)
    criteria = alert_criteria(
        result["jobs"][0], stage[0], result["internship_coverage"], {"status": status}
    )
    assert criteria["status"] == "eligible" and criteria["warnings"]
    assert criteria["source_status"] == status


def test_existing_expired_flag_is_not_ignored_by_the_alert_explanation(stage, repo, tmp_path):
    result = observe(stage, repo, tmp_path)
    criteria = alert_criteria(
        result["jobs"][0], stage[0], result["internship_coverage"], {}, stored_expired=True
    )
    assert "marked_expired" in {reason["code"] for reason in criteria["reasons"]}
    assert criteria["status"] == "blocked"


def test_dashboard_advertises_radar_policy_without_enabling_its_own_notifications(
    stage, repo, tmp_path, monkeypatch
):
    config, _ = stage
    config.settings.alerts_enabled = False
    monkeypatch.setenv("DASHBOARD_RADAR_ALERTS_ENABLED", "true")
    result = observe(stage, repo, tmp_path)
    assert result["internship_scope"]["radar_alerts_enabled"] is True
    assert result["jobs"][0]["internship_alert"]["status"] == "eligible"
    assert result["internship_summary"]["criteria_met"] == 1
    assert config.settings.alerts_enabled is False and not repo.pending()
    monkeypatch.setenv("DASHBOARD_RADAR_ALERTS_ENABLED", "false")
    assert "alerts_disabled" in codes(observe(stage, repo, tmp_path))
    assert config.settings.alerts_enabled is False
