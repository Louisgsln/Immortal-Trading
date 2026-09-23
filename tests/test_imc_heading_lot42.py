import pytest

from trading_radar.experience import experience_requirement
from trading_radar.in_experience import candidate_in_experience_years
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


@pytest.mark.parametrize(
    "heading", ["What You Bring", "Your Skills and Experience", "Your Skills & Experience"]
)
def test_imc_heading_change_preserves_professional_minimum(raw, config, heading):
    raw.title = "Trading Engineer - Strategy"
    raw.description = (
        f"<h3>{heading}:</h3><p>Bachelor’s degree in Computer Science, Information Technology, "
        "or related field 3+ years in site reliability, systems engineering, or technical "
        "operations, ideally supporting high-performance or real-time systems "
        "A software-development mindset applied to automating operational problems (Python required)</p>"
    )
    job = normalize(raw)
    assert candidate_in_experience_years(job.description_text) == [3]
    scored = score_job(job, config.keywords)
    assert scored.score_breakdown.junior == 0
    assert scored.score_breakdown.total == 0
    assert "software role without embedded trading evidence" in scored.score_breakdown.exclusions
    assert experience_requirement(scored)["minimum_years"] == 3


@pytest.mark.parametrize(
    "qualification",
    [
        "Preferred: 3+ years in site reliability",
        "3+ years in site reliability preferred",
        "3+ years in site reliability or a PhD",
        "A degree or 3+ years in site reliability",
        "Contract duration 3+ years in site reliability",
        "About us: 3+ years in site reliability",
        "3+ years in an unknown activity",
        "6-3 years in site reliability",
    ],
)
def test_ampersand_heading_keeps_existing_scope_guards(qualification):
    assert candidate_in_experience_years("Your Skills & Experience: " + qualification) == []
