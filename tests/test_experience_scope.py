"""Keep optional experience separate from mandatory applicant requirements."""

import pytest

from trading_radar.normalizer import normalize
from trading_radar.scoring import required_experience_years, score_job


@pytest.mark.parametrize(
    "text",
    [
        "At least 5 years of experience is preferred.",
        "Minimum of 5 years of professional experience is desirable.",
        "Requires 5 years of experience, preferred.",
        "Must have 5 years' experience is not required.",
        "At least 5 years of experience is not essential.",
        "Minimum 5 years experience is optional.",
        "At least 5+ years of institutional equity trading experience is preferred.",
        "Ideally 5+ years of experience.",
        "Ideally, 5+ years of experience.",
        "Ideally at least 5+ years of experience.",
        "Preferably minimum 5+ years of experience.",
        "Preferred Qualifications: Requires 5+ years of experience.",
        "Nice to have: Must have 5+ years of experience.",
        "Preferably 5 years of relevant experience required.",
        "Your skills and experience: ideally 3-7+ years of institutional equity trading "
        "experience; strong knowledge of US equity markets.",
        "Your skills and experience: ideally 7+ years’ experience in asset management "
        "or related passive investments field.",
    ],
)
def test_direct_preference_does_not_become_a_mandatory_minimum(text):
    assert required_experience_years(text) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Requires 5 years experience. Python is preferred.", [5]),
        ("5 years of experience, required.", [5]),
        ("Requires 5 years experience. Preferred Qualifications: Python.", [5]),
        ("Requires 5 years; Python experience is preferred.", [5]),
        ("Requires 5 years. Python experience is not required.", [5]),
        ("Requires 5 years, Python experience is preferred.", [5]),
        ("Requires 5 years and Python experience is preferred.", [5]),
        ("Requires 5 years experience, preferably in futures.", [5]),
        ("7+ years of experience, ideally in futures.", [7]),
        ("Ideally Python. 5+ years of experience.", [5]),
        ("Preferably Python; at least 5 years of experience.", [5]),
        ("Requires 2 years experience; ideally 5+ years of experience.", [2]),
        ("Ideally 5+ years of experience. Must have 3 years experience.", [3]),
        ("At least 5 years of experience is preferred. Requires 2 years experience.", [2]),
        ("At least 5 years of experience is not required. Requires 2 years experience.", [2]),
        (
            "You have at least 3 years of experience in financial markets, ideally gained "
            "within a structuring, pricing, trading or derivatives sales team. "
            "Proficiency in Python is a plus.",
            [3],
        ),
        (
            "Strong academic background, ideally in finance, economics or a quantitative "
            "discipline 5+ years of relevant experience with a proven track record "
            "of performance and established institutional client relationships.",
            [5],
        ),
    ],
)
def test_preference_scope_preserves_independent_requirements(text, expected):
    assert required_experience_years(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Undergraduate degree required. 5–10 years of experience trading softs and/or "
            "agricultural commodities. Experience in the dairy sector is preferred.",
            [5],
        ),
        (
            "Experience within a risk management or control discipline context are required. "
            "3+ years in the Financial Services / Banking industry Solid knowledge & experience.",
            [3],
        ),
    ],
)
def test_existing_global_experience_detection_remains_conservative(text, expected):
    # The optional-qualifier change does not relax existing numerical detections.
    # Interpreting these full qualifications requires a separate, broader review.
    assert required_experience_years(text) == expected


def test_preference_does_not_override_structured_employer_minimum(raw, config):
    raw.description = "Ideally 7+ years of experience."
    raw.minimum_experience_years = 5
    scored = score_job(normalize(raw), config.keywords)
    assert scored.score_breakdown.junior == 0
    assert "requires at least 5 years of experience" in scored.score_breakdown.exclusions


def test_optional_experience_preserves_junior_title_evidence(raw, config):
    raw.description = "At least 5 years of experience is preferred."
    scored = score_job(normalize(raw), config.keywords)
    assert scored.seniority == "junior"
    assert scored.score_breakdown.junior == 20
    assert "requires at least 5 years of experience" not in scored.score_breakdown.exclusions


def test_optional_experience_does_not_invent_junior_evidence(raw, config):
    raw.title = "Equity Trader"
    raw.description = "Ideally 3-7+ years of institutional equity trading experience."
    scored = score_job(normalize(raw), config.keywords)
    assert scored.seniority == "unknown"
    assert scored.score_breakdown.junior == 5
    assert "requires at least 5 years of experience" not in scored.score_breakdown.exclusions
