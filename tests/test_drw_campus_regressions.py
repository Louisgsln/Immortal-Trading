"""Independent DRW campus regression checks through the public board parser."""

from datetime import UTC, datetime

import pytest

from trading_radar.config import Company, load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job

FLOOR_REQUIREMENT = (
    "A bachelor's in economics, finance, mathematics, statistics, computer science "
    "or any related field and have an expected graduation date between "
    "December 2026 and June 2027"
)
ANALYST_REQUIREMENT = (
    "A bachelor's, master's, or PhD in mathematics, statistics, physics, engineering, "
    "computer science or related field graduating between December 2026 and June 2027"
)


def posting(*, title="Floor Trader", contract="Full-time", category=None, content=None):
    return {
        "id": 8207750,
        "internal_job_id": 3552394,
        "title": title,
        "company_name": "DRW ",
        "absolute_url": "https://job-boards.greenhouse.io/drweng/jobs/8207750",
        "location": {"name": "Chicago"},
        "metadata": [
            {"name": "Employment Type", "value": contract},
            {"name": "Target Start Date", "value": "Summer 2027"},
            {"name": "Website Job Category Filter", "value": category or ["Campus"]},
        ],
        "content": content
        or (
            "<p>Work on the Cboe trading floor and our trading desk.</p>"
            "<h2>What you bring to the team…</h2>"
            f"<ul><li>{FLOOR_REQUIREMENT}</li>"
            "<li>Prior trading or financial-markets experience is helpful but not required.</li>"
            "<li>Proficiency in Python is a plus.</li></ul>"
            "<p>DRW is a diversified trading firm.</p>"
        ),
        "first_published": "2026-09-16T18:00:49-04:00",
        "application_deadline": None,
    }


def parse(item):
    company = Company(name="DRW", ats="greenhouse_filtered", tenant="drweng")
    jobs = parse_board({"jobs": [item], "meta": {"total": 1}}, "drw", company, GreenhouseOptions())
    assert len(jobs) == 1
    return jobs[0]


def scored(item):
    return score_job(normalize(parse(item)), load_config().keywords)


def test_floor_trader_is_junior_without_title_keyword_or_invented_dates():
    raw = parse(posting())
    assert raw.seniority_hint == "junior"
    assert raw.employment_type == "Full-time"
    assert raw.expected_start_date == "Summer 2027"
    assert raw.date_posted == datetime(2026, 9, 16, 22, 0, 49, tzinfo=UTC)
    assert raw.application_deadline is None
    job = score_job(normalize(raw), load_config().keywords)
    assert job.score_breakdown.junior == 20
    assert job.score_breakdown.exclusions == []


def test_captured_analyst_graduating_wording_keeps_existing_title_based_juniority():
    item = posting(
        title="Quantitative Trading Analyst",
        content=f"<h2>What you bring to the team…</h2><ul><li>{ANALYST_REQUIREMENT}</li></ul>",
    )
    # This wording is deliberately outside the narrow Floor Trader inference.
    assert parse(item).seniority_hint is None
    assert scored(item).score_breakdown.junior == 20


def test_html_emphasis_does_not_erase_candidate_graduation_evidence():
    item = posting()
    item["content"] = item["content"].replace(
        "December 2026 and June 2027",
        "<strong>December 2026</strong> and <strong>June 2027</strong>",
    )
    assert parse(item).seniority_hint == "junior"


@pytest.mark.parametrize("contract", ["Regular", "Intern", "Temporary"])
def test_campus_graduation_does_not_infer_full_time_contract(contract):
    assert parse(posting(contract=contract)).seniority_hint is None


@pytest.mark.parametrize("category", [["Trading"], ["Technology"], ["Experienced"]])
def test_graduation_sentence_alone_does_not_override_employer_category(category):
    assert parse(posting(category=category)).seniority_hint is None


def test_missing_campus_metadata_preserves_existing_non_campus_parse():
    item = posting()
    item["metadata"] = item["metadata"][:2]
    assert parse(item).seniority_hint is None


@pytest.mark.parametrize(
    "title", ["Quantitative Trading Analyst Intern", "Floor Trader Internship"]
)
def test_full_time_intern_title_stays_excluded_despite_graduation(title):
    item = posting(title=title)
    assert parse(item).seniority_hint is None
    assert scored(item).score_breakdown.total == 0
    assert any("intern" in reason for reason in scored(item).score_breakdown.exclusions)


def test_internship_in_role_description_does_not_get_campus_junior_hint():
    item = posting()
    item["content"] = item["content"].replace(
        "<p>DRW is a diversified trading firm.</p>",
        "<h2>What to expect during the internship</h2><p>Ten weeks of projects.</p>"
        "<p>DRW is a diversified trading firm.</p>",
    )
    assert parse(item).seniority_hint is None


@pytest.mark.parametrize("title", ["Senior Floor Trader", "Vice President, Floor Trader"])
def test_campus_evidence_never_resurrects_explicit_senior_title(title):
    company = Company(name="DRW", ats="greenhouse_filtered", tenant="drweng")
    assert (
        parse_board(
            {"jobs": [posting(title=title)], "meta": {"total": 1}},
            "drw",
            company,
            GreenhouseOptions(),
        )
        == []
    )


def test_five_year_requirement_still_overrides_campus_compatibility():
    item = posting()
    item["content"] += "<p>Requires 5 years of experience.</p>"
    job = scored(item)
    assert job.score_breakdown.junior == 0
    assert "requires at least 5 years of experience" in job.score_breakdown.exclusions
    assert job.score_breakdown.total == 0


@pytest.mark.parametrize(
    "content",
    [
        "<h2>What you bring to the team…</h2><p>A genuine interest in financial markets.</p>",
        "<h2>About DRW</h2><p>Our campus programme welcomes graduates every year.</p>",
        "<h2>What you bring to the team…</h2><p>Work with students who have an "
        "expected graduation date between December 2026 and June 2027.</p>",
        "<h2>What you bring to the team…</h2><p>We do not require an "
        "expected graduation date between December 2026 and June 2027.</p>",
        "<h2>What you bring to the team…</h2><p>Your expected graduation date "
        "between December 2026 and June 2027 is not required.</p>",
        f"<h2>What you bring to the team…</h2><p>{FLOOR_REQUIREMENT} is not required.</p>",
    ],
)
def test_campus_metadata_does_not_turn_generic_or_negated_text_into_requirement(content):
    assert parse(posting(content=content)).seniority_hint is None
