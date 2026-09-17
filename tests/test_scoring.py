import json
from pathlib import Path

import pytest

from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def test_eight_reference_roles(config):
    rows = json.loads(Path("tests/fixtures/jobs.json").read_text())
    scores = [
        score_job(normalize(RawJob(**r, source="fixture")), config.keywords).score_breakdown.total
        for r in rows
    ]
    assert scores[:3] == [100, 100, 100]
    assert scores[3:6] == [0, 0, 0]
    assert all(s >= 85 for s in scores[6:])


@pytest.mark.parametrize(
    "title",
    [
        "Trading Operations Analyst",
        "Product Control Analyst",
        "Compliance Analyst",
        "VP Trading Analyst",
        "Senior Quantitative Trader",
        "IT Support",
        "Bernstein - Trading Application Support",
        "Operator Commodities Trading Associate",
        "Sales Analyst",
        "Software Engineer",
        "Equity Research Analyst",
        "Investment Bank Global Markets Legal",
        "Unified Global Markets APAC COO - Business Manager",
        "Trading Business Manager",
        "Lead Support Analyst - Low Latency Electronic Trading",
        "Electronic Execution Sales Trading Desk Head",
        "Risk, Credit Risk, Credit Risk (Global Markets), Analyst, Salt Lake City",
        "Risk-Credit Risk - Global Markets-Dallas-Analyst",
    ],
)
def test_exclusions_override_positive_description(raw, config, title):
    raw.title = title
    raw.description = "2027 graduate trading desk " + "FX markets Python derivatives " * 100
    result = score_job(normalize(raw), config.keywords)
    assert result.score_breakdown.total == 0


@pytest.mark.parametrize(
    "title",
    [
        "Sales & Trading Analyst 2027",
        "Structuring Graduate 2027",
        "Electronic Trading Analyst 2027",
        "Front Office Trading Systems Developer 2027",
        "Trading Support",
        "Credit Trading Analyst",
        "Credit Risk Trader",
    ],
)
def test_do_not_over_filter(raw, config, title):
    raw.title = title
    result = score_job(normalize(raw), config.keywords)
    assert not result.score_breakdown.exclusions
    assert result.score_breakdown.total >= 65


def test_boilerplate_year_is_not_start(raw, config):
    raw.title = "Trading Analyst"
    raw.description = "Copyright 2027. FX Python SQL."
    result = score_job(normalize(raw), config.keywords)
    assert result.score_breakdown.start == 7


def test_reporting_to_desk_head_is_not_senior(raw, config):
    raw.title = "Trading Analyst"
    raw.description = "Junior trading analyst reporting to the desk head. FX derivatives Python."
    scored = score_job(normalize(raw), config.keywords)
    assert not scored.score_breakdown.exclusions
    assert scored.score_breakdown.total >= 65


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "Senior Software Engineer"},
        {"employment_type": "Intern"},
        {"minimum_experience_years": 5},
        {"seniority_hint": "senior"},
    ],
)
def test_verified_trading_technology_does_not_override_exclusions(raw, config, changes):
    raw.title = "C++ Software Engineer"
    raw.role_hint = "trading_technology"
    for key, value in changes.items():
        setattr(raw, key, value)
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0


def test_trading_technology_hint_requires_technical_title(raw, config):
    raw.title = "Office Administrator"
    raw.role_hint = "trading_technology"
    scored = score_job(normalize(raw), config.keywords)
    assert scored.desk == ["NON_TRADING"] and scored.score_breakdown.total == 0


def test_old_payload_without_role_hint_remains_compatible(raw, config):
    old = raw.model_dump()
    old.pop("role_hint")
    restored = RawJob.model_validate(old)
    assert restored.role_hint is None
    assert (
        score_job(normalize(restored), config.keywords).score_breakdown
        == score_job(normalize(raw), config.keywords).score_breakdown
    )


def test_explicit_required_experience(raw, config):
    raw.description = "Requires 8 years experience."
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0
    raw.description = "Requires 3 years experience."
    assert score_job(normalize(raw), config.keywords).score_breakdown.junior == 0


def test_employer_structured_experience_overrides_junior_title(raw, config):
    raw.minimum_experience_years = 6
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0
    raw.minimum_experience_years = 3
    assert score_job(normalize(raw), config.keywords).score_breakdown.junior == 0
    raw.minimum_experience_years = 0
    assert score_job(normalize(raw), config.keywords).score_breakdown.junior == 20


def test_employer_seniority_used_without_overriding_explicit_experience(raw, config):
    raw.title = "Precious Metals Trading"
    raw.seniority_hint = "senior"
    job = score_job(normalize(raw), config.keywords)
    assert job.score_breakdown.total == 0 and job.seniority == "senior"
    raw.seniority_hint = "junior"
    job = score_job(normalize(raw), config.keywords)
    assert job.score_breakdown.junior == 20 and job.seniority == "junior"
    raw.minimum_experience_years = 6
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0
    raw.minimum_experience_years = None
    raw.title = "VP Trading Analyst"
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0


@pytest.mark.parametrize(
    "description",
    [
        "Have 3+ years of analyst experience in commodity analysis or trading",
        "5+ years of analyst experience in power markets",
        "We are looking to hire an experienced Options Trader",
    ],
)
def test_real_experienced_hire_phrasing(raw, config, description):
    raw.description = description
    assert score_job(normalize(raw), config.keywords).score_breakdown.junior == 0


def test_repetition_does_not_raise_score(raw, config):
    first = score_job(normalize(raw), config.keywords).score_breakdown.total
    raw.description *= 50
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == first


def test_assets_are_not_fx_only(raw, config):
    raw.description = "Options, repo, credit, energy, equities, digital assets, rates and macro"
    result = score_job(normalize(raw), config.keywords)
    assert {
        "OPTIONS",
        "REPO",
        "CREDIT",
        "COMMODITIES",
        "EQUITIES",
        "CRYPTO",
        "RATES",
        "MACRO",
    } <= set(result.asset_class)


def test_urgency_keeps_fit_score(job):
    fit = job.score_breakdown.total
    assert job.urgency() == fit + 5
    assert job.score_breakdown.total == fit


@pytest.mark.parametrize(
    "title",
    [
        "Markets Sales and Trading Summer Analyst 2027",
        "Quant Trader Internship",
        "FX Trading Intern",
        "Trading Graduate Apprenticeship",
        "2027 London FICC Sales and Trading Seasonal/OffCycle",
        "Stage - Assistant Trader FX",
    ],
)
def test_internships_do_not_look_like_fulltime_graduates(raw, config, title):
    raw.title = title
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0


def test_vie_retained(raw, config):
    raw.title = "VIE Trading Analyst 2027"
    assert score_job(normalize(raw), config.keywords).score_breakdown.total >= 85


@pytest.mark.parametrize(
    "contract", ["Internship/Trainee", "Stage", "Internship Programme", "Apprenticeship"]
)
def test_internship_contract_overrides_junior_trading_title(raw, config, contract):
    raw.title = "Junior Trading Analyst 2027"
    raw.employment_type = contract
    score = score_job(normalize(raw), config.keywords).score_breakdown
    assert score.total == 0
    assert "internship or apprenticeship contract" in score.exclusions


@pytest.mark.parametrize("contract", ["Graduate Programme", "VIE", "Permanent", "Trainee"])
def test_graduate_and_vie_contracts_are_not_internships(raw, config, contract):
    raw.employment_type = contract
    assert score_job(normalize(raw), config.keywords).score_breakdown.total >= 85


def test_dotted_vie_and_french_structuring(raw, config):
    raw.title = "V.I.E. Trading Analyst 2027"
    job = score_job(normalize(raw), config.keywords)
    assert job.programme_type == "VIE" and job.score_breakdown.junior == 20
    raw.title = "Ingénieur Structuration Pre-Trade"
    job = score_job(normalize(raw), config.keywords)
    assert "STRUCTURING" in job.desk and job.score_breakdown.trading == 22


def test_conflicting_start_years_are_explained(raw, config):
    raw.title = "Markets Sales and Trading Full Time Analyst 2027"
    raw.description = "Our program starts in the Summer of 2026. FX Python SQL."
    score = score_job(normalize(raw), config.keywords).score_breakdown
    assert score.start == 7
    assert any("Conflicting" in reason for reason in score.reasons)
