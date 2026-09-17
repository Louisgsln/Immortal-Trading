"""Independent qualification regressions from the nine-case lot 28 review.

Descriptions are short qualification excerpts; scoring examples retain only the
evidence needed for the audited components, without relying on a local database.
"""

import pytest

from trading_radar.normalizer import normalize
from trading_radar.scoring import required_experience_years, score_job

DESIRABLE = (
    "Experience Desirable: 1+ years of relevant experience in banking, preferably "
    "in Project Finance and Digital Infrastructure"
)
ADDITIVE = (
    "Bachelor's degree in Computer Science, Engineering, Mathematics or related "
    "discipline or its foreign equivalent plus 7 years of progressive experience "
    "developing software applications. Relevant technical experience may substitute "
    "for education"
)


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(DESIRABLE, [], id="direct-desirable-experience"),
        pytest.param(
            "PREFERRED QUALIFICATIONS Minimum of 1 year work experience in Equities",
            [],
            id="preferred-qualifications-minimum",
        ),
        pytest.param(
            "Preferred Qualifications • At least 2 years of experience in Operations "
            "or related field",
            [],
            id="preferred-qualifications-bullet",
        ),
        pytest.param(
            "Advanced degree in Computer Science (or equivalent work experience). "
            "Minimum 2 years of relevant professional experience",
            [2],
            id="degree-alternative-independent-minimum",
        ),
        pytest.param(
            "Minimum 8 years of experience along with bachelor’s degree in the "
            "related field or equivalent experience.",
            [8],
            id="minimum-along-with-degree",
        ),
        pytest.param(
            "Qualifications: 10+ years of experience in a related role. "
            "Education: Bachelor’s degree/University degree or equivalent experience",
            [10],
            id="qualifications-before-education",
        ),
        pytest.param(ADDITIVE, [7], id="degree-plus-experience"),
        pytest.param(
            "Strong academic background, ideally in finance, economics or a "
            "quantitative discipline 5+ years of relevant experience",
            [5],
            id="preferred-discipline-preserves-five",
        ),
        pytest.param(
            "You have at least 3 years of experience in financial markets, ideally "
            "gained within a structuring, pricing, trading or derivatives sales team.",
            [3],
            id="preferred-team-preserves-three",
        ),
    ],
)
def test_audited_qualification_interpretation(text, expected):
    assert required_experience_years(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Education Desirable: Masters degree. 5+ years of experience.", [5]),
        ("Education Desirable: Masters degree 5+ years of experience.", [5]),
        ("Experience Desirable: Python. Requires 3 years experience.", [3]),
        ("Experience Desirable: Python; requires 3 years experience.", [3]),
        (DESIRABLE + ". Requires 3 years experience.", [3]),
        ("Requires 5 years experience. " + DESIRABLE, [5]),
        ("Bachelor's degree or equivalent work experience. Requires 8 years experience.", [8]),
        ("Requires 5 years experience. Technical experience may substitute for education.", [5]),
        (
            "Bachelor's degree plus excellent communication skills. "
            "Our firm has 25+ years of experience.",
            [],
        ),
        ("Bachelor's degree. Our firm has a history spanning 7 years.", []),
    ],
)
def test_independent_qualifiers_do_not_change_unrelated_requirements(text, expected):
    assert required_experience_years(text) == expected


@pytest.mark.parametrize(
    "alternative",
    [
        "MSc with no prior experience",
        "an MBA with no prior experience",
        "M.Sc. with no prior experience",
    ],
)
def test_second_degree_pathway_does_not_create_a_universal_minimum(alternative):
    text = "Bachelor's degree plus 7 years of experience, or " + alternative + "."
    assert required_experience_years(text) == []


def test_additional_seven_years_excludes_the_audited_technology_role(raw, config):
    raw.title = "Quant Developer | Trading Strategies | Experienced Hire"
    # These are the same scoring signals as the archived role, reduced to avoid
    # copying the employer's full posting into a fixture.
    evidence = "Quantitative trading, C#, equity derivatives, market making. "
    raw.description = evidence
    before = score_job(normalize(raw), config.keywords).score_breakdown
    assert before.total == 65
    assert before.junior == 5
    assert not before.exclusions

    raw.description = evidence + ADDITIVE
    after = score_job(normalize(raw), config.keywords).score_breakdown
    assert after.total == 0
    assert after.junior == 0
    assert after.exclusions == ["requires at least 5 years of experience"]
    assert "Explicit experience requirement exceeds 2 years" in after.reasons
    assert after.trading == before.trading
    assert after.front_office == before.front_office


def test_desirable_experience_preserves_the_audited_analyst_score(raw, config):
    raw.title = "Analyst - Sales, Secondary Loan Trading & Credit Risk Insurance Distribution"
    raw.minimum_experience_years = 0
    raw.description = "<p>0-2 years</p><p>" + DESIRABLE + "</p>"
    scored = score_job(normalize(raw), config.keywords)
    assert required_experience_years(scored.description_text) == []
    assert scored.minimum_experience_years == 0
    assert scored.score_breakdown.total == 82
    assert scored.score_breakdown.junior == 20
    assert not scored.score_breakdown.exclusions
    assert not any("experience requirement" in reason for reason in scored.score_breakdown.reasons)


@pytest.mark.parametrize("minimum, excluded", [(3, False), (5, True)])
def test_structured_employer_minimum_survives_text_preference(raw, config, minimum, excluded):
    raw.description = DESIRABLE
    raw.minimum_experience_years = minimum
    score = score_job(normalize(raw), config.keywords).score_breakdown
    assert score.junior == 0
    assert "Explicit experience requirement exceeds 2 years" in score.reasons
    assert ("requires at least 5 years of experience" in score.exclusions) is excluded
    assert (score.total == 0) is excluded


@pytest.mark.parametrize("title", ["Office Administrator", "Senior Quantitative Trader"])
def test_desirable_qualification_does_not_override_other_role_exclusions(raw, config, title):
    raw.title = title
    raw.description = DESIRABLE
    assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0


def test_preference_does_not_invent_a_junior_classification(raw, config):
    raw.title = "Equity Trader"
    raw.description = DESIRABLE
    scored = score_job(normalize(raw), config.keywords)
    assert scored.minimum_experience_years is None
    assert scored.seniority == "unknown"
    assert scored.score_breakdown.junior == 5
