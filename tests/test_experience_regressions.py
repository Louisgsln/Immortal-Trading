"""Experience visibility must remain separate from ranking and eligibility."""

import pytest

from trading_radar.experience import experience_requirement
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def scored(config, description, **changes):
    values = {
        "company": "Example Employer",
        "source": "example",
        "source_type": "official",
        "title": "Quantitative Trader",
        "description": description,
        "apply_url": "https://example.org/jobs/1",
    }
    return score_job(normalize(RawJob(**(values | changes))), config.keywords)


def observe_unchanged(job):
    before = job.model_dump(mode="json")
    result = experience_requirement(job)
    assert job.model_dump(mode="json") == before
    return result


def test_floor_trader_junior_evidence_does_not_invent_zero_years(config):
    job = scored(
        config,
        "Prior trading or financial-markets experience is helpful but not required. "
        "Proficiency in Python is a plus.",
        company="DRW",
        source="drw",
        title="Floor Trader",
        seniority_hint="junior",
        employment_type="Full-time",
        expected_start_date="Summer 2027",
    )
    assert job.score_breakdown.total == 82
    assert job.score_breakdown.junior == 20
    assert observe_unchanged(job) == {"minimum_years": None, "category": "unspecified"}


def test_flow_numeric_requirement_is_visible_without_changing_trading_score(config):
    job = scored(
        config,
        "Minimum 3+ years of professional trading experience at a leading proprietary "
        "trading firm, market maker or crypto-native trading desk — this is not an "
        "entry-level or junior role.",
        company="Flow Traders",
        source="flow_traders",
        title="Digital Assets Trader",
    )
    before_score = job.score_breakdown.total
    assert job.score_breakdown.junior == 0
    assert observe_unchanged(job) == {"minimum_years": 3, "category": "over_2"}
    assert job.score_breakdown.total == before_score


@pytest.mark.parametrize(
    "description",
    [
        "This is not an entry-level or junior role.",
        "We are seeking an experienced trader with substantial market knowledge.",
        "Several years of trading experience are required.",
    ],
)
def test_non_numeric_seniority_is_not_reported_as_a_numeric_minimum(config, description):
    job = scored(config, description)
    assert observe_unchanged(job) == {"minimum_years": None, "category": "unspecified"}


def test_structured_zero_does_not_make_an_internship_eligible(config):
    job = scored(
        config,
        "0-2 years of financial markets experience.",
        title="Trainee - Global Markets Division",
        employment_type="Internship/Trainee",
        minimum_experience_years=0,
    )
    assert observe_unchanged(job) == {"minimum_years": 0, "category": "up_to_2"}
    assert job.score_breakdown.total == 0
    assert "internship or apprenticeship contract" in job.score_breakdown.exclusions


def test_structured_five_year_coding_record_remains_excluded(config):
    job = scored(
        config,
        "Skills You'll Need: 5+ year track record of solving challenging problems "
        "through coding with real metrics & impact in industry and/or academia.",
        title="Quantitative Developer | Trading Team",
        minimum_experience_years=5,
    )
    assert observe_unchanged(job) == {"minimum_years": 5, "category": "over_2"}
    assert job.score_breakdown.total == 0
    assert "requires at least 5 years of experience" in job.score_breakdown.exclusions


def test_unknown_covers_a_real_existing_parser_limitation(config):
    # Jump's stored phrase has a range but no requirement pattern recognized today.
    job = scored(
        config,
        "3–6 years in buy/sell-side research, prop trading, ETF/index research, "
        "or corporate actions analysis",
        title="Quantamental Research Analyst | Trading Team",
    )
    assert observe_unchanged(job) == {"minimum_years": None, "category": "unspecified"}
    assert job.score_breakdown.total == 0
    assert "research analyst" in job.score_breakdown.exclusions


def test_ideal_experience_is_not_promoted_to_required_minimum(config):
    job = scored(
        config,
        "Your skills and experience: ideally 7+ years’ experience in asset management "
        "or related passive investments field.",
    )
    assert observe_unchanged(job) == {"minimum_years": None, "category": "unspecified"}


def test_low_range_category_describes_lower_bound_not_experience_ceiling(config):
    job = scored(config, "At least 2-5+ years of experience in a production engineering role.")
    assert observe_unchanged(job) == {"minimum_years": 2, "category": "up_to_2"}
