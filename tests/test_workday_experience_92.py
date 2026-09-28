"""Scoped professional requirements must not treat team history as experience."""

import pytest

from trading_radar.config import load_config
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.workday import workday_minimum_experience

CASES = [
    (
        "pimco",
        "PIMCO",
        "REQUIREMENTS",
        "8+ years of experience in a fixed income trading capacity (investment grade preferred)",
        8,
    ),
    (
        "td",
        "TD",
        "Qualifications",
        "Minimum five years experience in financial markets in a trading capacity across a breadth of interest rate products",
        5,
    ),
]


@pytest.mark.parametrize("source,company,heading,clause,years", CASES)
def test_explicit_professional_minimum_excludes_experienced_role(
    source, company, heading, clause, years
):
    description = f"<p><b>{heading}</b></p><ul><li>{clause}</li></ul>"
    minimum = workday_minimum_experience(source, company, description)
    assert minimum == years
    raw = RawJob(
        source=source,
        company=company,
        title="Trader",
        apply_url="https://example.org/job",
        description=description,
        minimum_experience_years=minimum,
    )
    job = score_job(normalize(raw), load_config().keywords)
    assert job.score_breakdown.total == 0
    assert "requires at least 5 years of experience" in job.score_breakdown.exclusions


@pytest.mark.parametrize("source,company,heading,clause,years", CASES)
@pytest.mark.parametrize(
    "variant",
    [
        "hidden",
        "script",
        "no-heading",
        "team",
        "negated",
        "preferred",
        "other-employer",
        "other-source",
    ],
)
def test_only_visible_matching_candidate_requirement_is_evidence(
    source, company, heading, clause, years, variant
):
    if variant == "team":
        clause = "Our team has " + clause
    if variant == "negated":
        clause = "Not required: " + clause
    if variant == "preferred":
        clause += ", preferred but not required"
    description = f"<p>{heading}</p><ul><li>{clause}</li></ul>"
    if variant == "hidden":
        description = "<div hidden>" + description + "</div>"
    if variant == "script":
        description = "<script>" + description + "</script>"
    if variant == "no-heading":
        description = f"<p>{clause}</p>"
    if variant == "other-employer":
        company = "Other"
    if variant == "other-source":
        source = "old-source"
    assert workday_minimum_experience(source, company, description) is None
