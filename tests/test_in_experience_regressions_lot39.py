"""Independent regressions from the 814-job, read-only lot 38 audit."""

import pytest

from trading_radar.experience import experience_requirement
from trading_radar.in_experience import candidate_in_experience_years
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import required_experience_years, score_job

# These four different texts cover seven stored offers: four Optiver locations
# share the same qualification. No private database is needed to run these tests.
REAL_QUALIFICATIONS = [
    pytest.param(
        "Skills You’ll Need: Bachelor’s in Finance, Economics, Mathematics, or a "
        "related quantitative field 3–6 years in buy/sell-side research, prop trading, "
        "ETF/index research, or corporate actions analysis High attention to details "
        "and apply to identify information that market might have missed",
        3,
        id="jump-26e2a615-research-analyst",
    ),
    pytest.param(
        "What You Bring: Bachelor’s degree in Computer Science, Information Technology, "
        "or related field 3+ years in site reliability, systems engineering, or "
        "technical operations, ideally supporting high-performance or real-time "
        "systems A software-development mindset applied to automating operational "
        "problems (Python required)",
        3,
        id="imc-602f0bbe-strategy-engineer",
    ),
    pytest.param(
        "Your skills and experience • 7+ years in FPGA (Verilog/VHDL) or low-latency "
        "C++ development. • Expert in C++17/20/23, Linux system programming, concurrency.",
        7,
        id="ubs-54c636ec-algo-developer",
    ),
    pytest.param(
        "Who you are Hold a bachelor’s degree (required) Deep understanding of financial "
        "instruments, trading exchanges and markets Possess a high aptitude with "
        "mathematics Excellent communicator and team player Strong relationship-builder "
        "across traders, brokers, and exchange personnel. 3+ years in options trading, "
        "market making, floor brokerage, or exchange operations. Preferred: Prior "
        "listed options market-making experience. Series 57 active and in good standing.",
        3,
        id="optiver-four-sso-floor-trader-locations",
    ),
]


def make_job(description, **changes):
    values = {
        "company": "Example Employer",
        "source": "example",
        "source_type": "official",
        "title": "Trading Analyst",
        "description": description,
        "apply_url": "https://example.org/jobs/lot39",
    }
    return normalize(RawJob(**(values | changes)))


@pytest.mark.parametrize(("description", "minimum"), REAL_QUALIFICATIONS)
def test_audited_qualifications_reach_parser_and_readonly_dashboard(description, minimum):
    assert candidate_in_experience_years(description) == [minimum]
    assert required_experience_years(description) == [minimum]
    job = make_job(description)
    before = job.model_dump(mode="json")
    assert experience_requirement(job) == {"minimum_years": minimum, "category": "over_2"}
    assert job.model_dump(mode="json") == before


@pytest.mark.parametrize(
    ("number", "minimum", "category"),
    [("0–2", 0, "up_to_2"), ("2—5", 2, "up_to_2"), ("3-6", 3, "over_2")],
)
def test_numeric_lower_bound_is_not_replaced_by_upper_bound(number, minimum, category):
    description = f"Who you are: {number} years in options trading."
    assert required_experience_years(description) == [minimum]
    assert experience_requirement(make_job(description)) == {
        "minimum_years": minimum,
        "category": category,
    }


@pytest.mark.parametrize(
    "description",
    [
        "Preferred Qualifications: 3+ years in options trading.",
        "Who you are: Preferred: 3+ years in options trading.",
        "Who you are: Ideally 3+ years in options trading.",
        "Who you are: 3+ years in options trading is preferred.",
        "Who you are: 3+ years in options trading would be desirable.",
        "Who you are: 3+ years in options trading is not required.",
        "Who you are: 3+ years in options trading is not needed.",
        "Who you are: 3+ years in options trading is optional.",
        "Who you are: Up to 3+ years in options trading.",
        "Who you are: At most 3+ years in options trading.",
        "Who you are: Candidates without 3+ years in options trading are welcome.",
        "Who you are: You do not need 3+ years in options trading.",
        "Who you are: No need for 3+ years in options trading.",
        "Who you are: A degree or 3+ years in options trading.",
        "Who you are: 3+ years in options trading or a master's degree.",
        "Who you are: 3+ years in options trading; or a master's degree.",
        "Who you are: 3+ years in options trading or no experience with a PhD.",
        "Who you are: 3+ years in options trading may be waived.",
        "About us: Our firm has 3+ years in options trading.",
        "Who you are: Our firm has 3+ years in options trading.",
        "Who you are: The firm has 3+ years in options trading.",
        "Who you are: The team has 3+ years in options trading.",
        "Who you are: We have 3+ years in options trading.",
        "Who you are: 6–3 years in options trading.",
        "Who you are: 103+ years in options trading.",
        "Who you are: 1.3+ years in options trading.",
        "Who you are: -3+ years in options trading.",
        "Who you are: 3–5.5 years in options trading.",
        "Who you are: 3 years in options trading.",
        "3–6 years in buy/sell-side research, prop trading, ETF/index research, "
        "or corporate actions analysis",
    ],
)
def test_optional_alternative_business_and_invalid_durations_remain_unspecified(description):
    assert candidate_in_experience_years(description) == []
    assert required_experience_years(description) == []
    assert experience_requirement(make_job(description)) == {
        "minimum_years": None,
        "category": "unspecified",
    }


@pytest.mark.parametrize(
    "title",
    [
        "Global Markets Trainee - FX & Rates Macro Financial Institution Sales (One Year Contract)",
        "Global Markets Trainee - Debt Capital Markets (One Year Contract)",
    ],
)
def test_credit_agricole_programme_duration_does_not_override_structured_zero(title, config):
    description = (
        "Trainee program is one year to begin with and possible for extension up to "
        "2 years in total, subject to performance and business needs. At the end of the "
        "program, you will be considered for a permanent role based on your performance "
        "and business needs."
    )
    assert candidate_in_experience_years(description) == []
    assert required_experience_years(description) == []
    job = score_job(
        make_job(
            description,
            title=title,
            employment_type="Internship/Trainee",
            minimum_experience_years=0,
        ),
        config.keywords,
    )
    assert experience_requirement(job) == {"minimum_years": 0, "category": "up_to_2"}
    assert job.score_breakdown.total == 0
    assert "internship or apprenticeship contract" in job.score_breakdown.exclusions


@pytest.mark.parametrize(
    ("description", "minimum"),
    [
        (
            "Qualifications: 10+ years relevant experience, 5+ years in Risk & Controls "
            "roles, 5+ years of direct or indirect managerial experience.",
            10,
        ),
        (
            "Qualifications: 8+ years of professional experience. Proven track record "
            "delivering complex, large-scale cross-functional programs with at least "
            "2 years in AI/GenAI or digital transformation.",
            8,
        ),
    ],
    ids=["citi-total-ten", "nomura-total-eight"],
)
def test_existing_higher_requirements_are_preserved(description, minimum):
    assert max(required_experience_years(description)) == minimum
    assert experience_requirement(make_job(description)) == {
        "minimum_years": minimum,
        "category": "over_2",
    }


@pytest.mark.parametrize(("years", "domain"), [(2, "industry"), (5, "industry and/or academia")])
def test_track_record_stays_out_of_scope_and_structured_value_remains_authoritative(years, domain):
    description = (
        f"Skills You’ll Need: {years}+ year track record of solving challenging problems "
        f"through coding with real metrics & impact in {domain}."
    )
    assert candidate_in_experience_years(description) == []
    assert required_experience_years(description) == []
    assert experience_requirement(make_job(description))["minimum_years"] is None
    assert experience_requirement(make_job(description, minimum_experience_years=years)) == {
        "minimum_years": years,
        "category": "up_to_2" if years <= 2 else "over_2",
    }


@pytest.mark.parametrize(
    ("title", "description", "exclusion"),
    [
        (
            "Quantamental Research Analyst | Trading Team",
            "Skills You’ll Need: 3–6 years in buy/sell-side research, prop trading, "
            "ETF/index research, or corporate actions analysis.",
            "research analyst",
        ),
        (
            "Trading Engineer - Strategy",
            "What You Bring: 3+ years in site reliability, systems engineering, "
            "or technical operations, ideally supporting high-performance or real-time systems.",
            "software role without embedded trading evidence",
        ),
    ],
)
def test_correcting_experience_does_not_remove_independent_role_exclusions(
    title, description, exclusion, config
):
    job = score_job(make_job(description, title=title), config.keywords)
    assert job.score_breakdown.total == 0
    assert job.score_breakdown.junior == 0
    assert exclusion in job.score_breakdown.exclusions
    assert "Explicit experience requirement exceeds 2 years" in job.score_breakdown.reasons


def test_structured_requirement_stronger_than_new_textual_minimum_is_preserved(config):
    job = score_job(
        make_job("Who you are: 3+ years in options trading.", minimum_experience_years=7),
        config.keywords,
    )
    assert experience_requirement(job) == {"minimum_years": 7, "category": "over_2"}
    assert job.score_breakdown.total == 0
    assert "requires at least 5 years of experience" in job.score_breakdown.exclusions
