from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from trading_radar.config import Company, Settings, load_config
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.programmes import programme, programme_alertable, programme_company
from trading_radar.scoring import score_job


def make(title="FX Trading Off-cycle Internship 2027", **fields):
    return normalize(
        RawJob(
            company="Demo Bank",
            title=title,
            apply_url="https://example.com/jobs/1",
            source="test",
            description="Trading desk, FX, Python and derivatives.",
            **fields,
        )
    )


def policy(**updates):
    return Settings(include_internships=True, internship_alerts_enabled=True, **updates)


@pytest.mark.parametrize(
    "title,contract,formats",
    [
        ("Markets Off-cycle Analyst 2027", "Full time", ["off_cycle"]),
        ("Trading Off Cycle Intern 2027", "FULL_TIME", ["off_cycle"]),
        ("Stage Trading 6 mois 2027", "Stage", ["long"]),
        ("Quant Trading Intern 12 months 2027", None, ["long"]),
        ("Trading Summer Analyst 2027", "Full time", ["summer"]),
        ("Trading Internship 2027", "Internship / Trainee", []),
        ("Fixed Income Trading Desk Internship 2027", "Off-cycle internship", ["off_cycle"]),
        ("Trading Internship 2027", "Summer Internship", ["summer"]),
    ],
)
def test_programme_facts(title, contract, formats):
    observed = programme(make(title, employment_type=contract))
    assert observed["kind"] == "internship"
    assert observed["formats"] == formats
    assert observed["year"] == 2027
    assert observed["year_status"] == "confirmed"


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Graduate FX Trader 2027", "graduate"),
        ("V.I.E. FX Trader", "vie"),
        ("Trading Apprenticeship 2027", "apprenticeship"),
        ("Trading alternance 2027", "apprenticeship"),
        ("Trading Spring Insight Programme 2027", "discovery"),
        ("FX Trading Analyst", "unspecified"),
    ],
)
def test_other_programmes_remain_distinct(title, expected):
    assert programme(make(title))["kind"] == expected


@pytest.mark.parametrize(
    "title", ["Alternant FX Trader 2027", "Trading Spring Insight Programme 2027"]
)
def test_other_student_programmes_are_never_alerted(title):
    assert not programme_alertable(make(title), policy())


@pytest.mark.parametrize(
    "fields",
    [
        {"publication_day": "2027-01-01"},
        {"description": "Candidates graduate in 2027. Our company was founded in 2027."},
    ],
)
def test_unrelated_year_is_not_an_intake(fields):
    base = make("Trading Off-cycle Intern").model_copy(update=fields)
    if "description" in fields:
        base.description_text = fields["description"]
    assert programme(base)["year"] is None
    assert not programme_alertable(base, policy())


def test_explicit_candidate_start_and_duration():
    job = make("Trading Internship", expected_start_date="2027-02-01")
    job.description = job.description_text = "Internship duration: 6 months. Starts February 2027."
    assert programme(job)["formats"] == ["long"]
    assert programme_alertable(job, policy())


def test_previous_internship_duration_and_graduation_title_are_not_intake_facts():
    job = make("Trading Internship for students graduating in 2027")
    job.description = "Candidates must have completed an internship of 6 months."
    observed = programme(job)
    assert observed["year"] is None and not observed["formats"]
    assert not programme_alertable(job, policy())


def test_application_duration_is_not_the_stage_duration():
    job = make("Trading Internship 2027")
    job.description = "Application process duration: 6 months."
    assert not programme(job)["formats"]


def test_previous_sentence_does_not_hide_explicit_stage_duration():
    job = make("Trading Internship 2027")
    job.description = "Previous experience is welcome. Internship duration: 6 months."
    assert programme(job)["formats"] == ["long"]


@pytest.mark.parametrize(
    "duration,long",
    [("6-month", True), ("6–12 months", True), ("3-6 months", False), ("18 months", False)],
)
def test_duration_uses_the_minimum_and_supports_hyphens(duration, long):
    observed = programme(make("Trading Internship " + duration + " 2027"))
    assert ("long" in observed["formats"]) is long


@pytest.mark.parametrize(
    "title,start",
    [
        ("Trading Off-cycle Intern 2027", "2028-01-01"),
        ("Trading Off-cycle Intern 2027 / 2028", None),
        ("Trading Summer Off-cycle Intern 2027", None),
    ],
)
def test_conflicts_fail_closed(title, start):
    job = make(title, expected_start_date=start)
    assert programme(job)["issues"]
    assert not programme_alertable(job, policy())
    assert score_job(job, load_config().keywords, settings=policy()).score_breakdown.total == 0


def test_employer_summer_contract_cannot_override_a_conflicting_off_cycle_title():
    job = make(employment_type="Summer Internship")
    assert programme(job)["issues"] and not programme_alertable(job, policy())
    assert score_job(job, load_config().keywords, settings=policy()).score_breakdown.total == 0


@pytest.mark.parametrize(
    "title",
    [
        "Trading Summer Intern 2027",
        "Trading Off-cycle Intern 2026",
        "Trading Off-cycle Intern 2028",
    ],
)
def test_outside_requested_scope_excluded(title):
    job = score_job(make(title), load_config().keywords, settings=policy())
    assert job.score_breakdown.total == 0
    assert not programme_alertable(job, policy())


@pytest.mark.parametrize("title", ["Trading Internship 2027", "Trading Off-cycle Intern"])
def test_unconfirmed_format_or_year_visible_but_not_alerted(title):
    job = score_job(make(title), load_config().keywords, settings=policy())
    assert job.score_breakdown.total >= 70
    assert not programme_alertable(job, policy())


def test_off_cycle_policy_does_not_override_associate_or_seniority():
    for title in [
        "Trading Off-cycle Associate Intern 2027",
        "Senior Trading Off-cycle Intern 2027",
    ]:
        assert (
            score_job(make(title), load_config().keywords, settings=policy()).score_breakdown.total
            == 0
        )
    job = make(minimum_experience_years=5)
    assert score_job(job, load_config().keywords, settings=policy()).score_breakdown.total == 0


def test_scoring_opt_in_preserves_full_time_and_default_stage_exclusion():
    keywords = load_config().keywords
    stage = make(employment_type="Internship")
    assert score_job(stage.model_copy(deep=True), keywords).score_breakdown.total == 0
    assert score_job(stage, keywords, settings=policy()).score_breakdown.total >= 70
    regular = make("Graduate FX Trader 2027")
    before = score_job(regular.model_copy(deep=True), keywords)
    after = score_job(regular.model_copy(deep=True), keywords, settings=policy())
    assert before.model_dump() == after.model_dump()


def test_sig_contradictory_category_stays_excluded():
    job = make(
        "Quantitative Trader New Graduate 2027", employment_type="INTERN", seniority_hint="junior"
    )
    job.source = "sig"
    assert programme(job)["issues"]
    assert score_job(job, load_config().keywords, settings=policy()).score_breakdown.total == 0


def test_options_expand_stages_without_mutating_original_or_other_exclusions():
    co = Company(
        name="Bank",
        ats="fixture",
        options={
            "exclude_title_terms": ["internship", "stage", "alternance", "operations", "senior"]
        },
    )
    assert programme_company(co, Settings()) is co
    expanded = programme_company(co, policy())
    assert expanded.options["exclude_title_terms"] == ["alternance", "operations", "senior"]
    assert co.options["exclude_title_terms"][0] == "internship"


def test_baseline_requires_timezone_and_preserves_aware_time():
    with pytest.raises(ValidationError):
        Settings(internship_baseline_at="2026-10-06T20:00:00")
    assert Settings(
        internship_baseline_at="2026-10-06T20:00:00Z"
    ).internship_baseline_at == datetime(2026, 10, 6, 20, tzinfo=UTC)
