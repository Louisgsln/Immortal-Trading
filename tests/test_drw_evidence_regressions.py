"""Independent score-level checks for bounded DRW company-text filtering."""

import pytest

from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job

# These complete passages are independently verified in the lot32 DRW capture.
HEADQUARTERS = (
    "Headquartered in Chicago with offices throughout the U.S., Canada, Europe, and Asia, "
    "we trade a variety of asset classes including Fixed Income, ETFs, Equities, FX, "
    "Commodities and Energy across all major global markets. We have also leveraged our "
    "expertise and technology to expand into three non-traditional strategies: real estate, "
    "venture capital and cryptoassets."
)
PREDICTION_INTRO = (
    "DRW is a major Chicago-based proprietary trading firm founded in 1992 by Don Wilson, "
    "specializing in diversified, technology-driven market-making and quantitative trading "
    "across asset classes including fixed income, options, derivatives, commodities, energy, "
    "equities, FX, and cryptocurrency."
)


def candidate(description, **changes):
    values = {
        "company": "DRW",
        "source": "drw",
        "source_type": "official",
        "title": "Floor Trader",
        "description": description,
        "apply_url": "https://job-boards.greenhouse.io/drweng/jobs/8207750",
        "employment_type": "Full-time",
        "seniority_hint": "junior",
        "expected_start_date": "Summer 2027",
    }
    return normalize(RawJob(**(values | changes)))


@pytest.mark.parametrize("paragraph", [HEADQUARTERS, PREDICTION_INTRO])
def test_company_paragraph_alone_is_not_candidate_asset_or_profile_evidence(config, paragraph):
    job = candidate("Develop tools in Python. " + paragraph)
    original_description = job.description
    original_text = job.description_text
    scored = score_job(job, config.keywords)
    assert scored.asset_class == ["UNKNOWN"]
    assert scored.score_breakdown.matched_keywords == ["python"]
    assert scored.score_breakdown.asset == 0
    assert scored.score_breakdown.profile_fit == 2
    assert scored.score_breakdown.total == 82
    assert scored.score_breakdown.junior == 20
    assert scored.score_breakdown.start == scored.score_breakdown.front_office == 15
    assert scored.description == original_description
    assert scored.description_text == original_text


@pytest.mark.parametrize("paragraph", [HEADQUARTERS, PREDICTION_INTRO])
@pytest.mark.parametrize("position", ["before", "after"])
def test_role_evidence_survives_on_either_side_of_company_paragraph(config, paragraph, position):
    role = "Trade FX options and equities. Use Python for derivatives pricing."
    content = role + " " + paragraph if position == "before" else paragraph + " " + role
    scored = score_job(candidate(content), config.keywords)
    assert scored.asset_class == ["FX", "EQUITIES", "OPTIONS", "CROSS_ASSET"]
    assert scored.score_breakdown.matched_keywords == ["python", "derivatives", "fx", "pricing"]
    assert scored.score_breakdown.asset == 10
    assert scored.score_breakdown.profile_fit == 8


def test_asset_in_title_remains_evidence_when_description_only_has_company_text(config):
    scored = score_job(candidate(HEADQUARTERS, title="FX Trader"), config.keywords)
    assert scored.asset_class == ["FX"]
    assert scored.score_breakdown.matched_keywords == ["fx"]


def test_prediction_market_role_keeps_options_mentioned_in_its_requirements(config):
    role = "Required Qualifications: Experience with prediction markets or options."
    scored = score_job(candidate(PREDICTION_INTRO + " " + role), config.keywords)
    assert scored.asset_class == ["OPTIONS"]
    assert "fx" not in scored.score_breakdown.matched_keywords
    assert "CROSS_ASSET" not in scored.asset_class


@pytest.mark.parametrize(
    "changes",
    [
        {"company": "Other Firm"},
        {"source": "other_source"},
        {"source_type": "aggregator"},
    ],
)
def test_other_employer_or_source_keeps_unchanged_evidence_rules(config, changes):
    scored = score_job(candidate(HEADQUARTERS, **changes), config.keywords)
    assert scored.asset_class == ["FX", "EQUITIES", "COMMODITIES"]
    assert scored.score_breakdown.matched_keywords == ["fx"]


def test_inconsistent_normalized_employer_does_not_enable_specific_filter(config):
    job = candidate(HEADQUARTERS)
    job.company_normalized = "other firm"
    scored = score_job(job, config.keywords)
    assert "FX" in scored.asset_class
    assert "fx" in scored.score_breakdown.matched_keywords


def test_similar_role_specific_sentence_is_not_a_recognized_company_signature(config):
    content = HEADQUARTERS.replace("we trade a variety", "this role trades a variety")
    scored = score_job(candidate(content), config.keywords)
    assert scored.asset_class == ["FX", "EQUITIES", "COMMODITIES"]
    assert scored.score_breakdown.matched_keywords == ["fx"]


def test_only_asset_and_profile_views_change_front_office_logic_is_preserved(config):
    # Existing FO scoring sees 'global markets' in the complete source text.
    scored = score_job(candidate(HEADQUARTERS, title="Markets Analyst"), config.keywords)
    assert scored.score_breakdown.trading == 18
    assert scored.score_breakdown.front_office == 15
    assert scored.score_breakdown.junior == 20
    assert scored.score_breakdown.start == 15
    assert scored.asset_class == ["UNKNOWN"]


@pytest.mark.parametrize("paragraph", [HEADQUARTERS, PREDICTION_INTRO])
def test_required_experience_after_company_paragraph_still_excludes(config, paragraph):
    job = candidate(paragraph + " Requires 5 years of experience.")
    scored = score_job(job, config.keywords)
    assert scored.score_breakdown.total == 0
    assert scored.score_breakdown.junior == 0
    assert "requires at least 5 years of experience" in scored.score_breakdown.exclusions


def test_senior_title_and_intern_contract_exclusions_remain_independent(config):
    senior = score_job(candidate(HEADQUARTERS, title="Senior Floor Trader"), config.keywords)
    internship = score_job(candidate(HEADQUARTERS, employment_type="Intern"), config.keywords)
    assert senior.score_breakdown.total == internship.score_breakdown.total == 0
    assert "senior title" in senior.score_breakdown.exclusions
    assert "internship or apprenticeship contract" in internship.score_breakdown.exclusions


def test_explicit_start_after_company_paragraph_is_still_read(config):
    job = candidate(HEADQUARTERS + " Expected start in September 2027.")
    job.expected_start_date = None
    scored = score_job(job, config.keywords)
    assert scored.score_breakdown.start == 15
    assert scored.expected_start_date is None
