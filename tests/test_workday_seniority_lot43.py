import asyncio

import pytest

from trading_radar.config import Company
from trading_radar.http import SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.workday import WorkdayCollector, workday_seniority_hint

MS_POSTING = (
    "App-Dev-Team-Mgmt--Application-Development----Job-Level---Executive-Director_PT-JR043325"
)
CITI_ROLE = (
    "The Director on the EMEA Cash Electronic Execution Desk is a senior leadership role "
    "within the Equities Markets division, responsible for driving growth."
)


@pytest.mark.parametrize("grade", ["Vice President", "Director", "Managing Director"])
@pytest.mark.parametrize("separator", [" ", ": ", " – "])
def test_db_dedicated_grade_paragraph(grade, separator):
    assert (
        workday_seniority_hint(
            "deutsche_bank",
            "Deutsche Bank",
            "Trader",
            f"<p>Corporate Title{separator}<strong>{grade}</strong></p>",
            None,
        )
        == "senior"
    )


@pytest.mark.parametrize(
    "description",
    [
        "<p>Corporate Title Analyst</p>",
        "<p>Corporate Title Associate</p>",
        "<p>Reports to Corporate Title Vice President</p>",
        "<p>Corporate Title Vice President is your manager</p>",
        "<p>Previous Corporate Title Vice President</p>",
        "<p>Corporate Title Vice President or Analyst</p>",
        "Corporate Title Vice President",
        "<script>Corporate Title Vice President</script>",
    ],
)
def test_db_grade_requires_unambiguous_role_field(description):
    assert (
        workday_seniority_hint("deutsche_bank", "Deutsche Bank", "Trader", description, None)
        is None
    )


def test_contradictory_db_grades_reject_snapshot():
    with pytest.raises(SourceUnavailable, match="contradictory"):
        workday_seniority_hint(
            "deutsche_bank",
            "Deutsche Bank",
            "Trader",
            "<p>Corporate Title Analyst</p><p>Corporate Title Vice President</p>",
            None,
        )


@pytest.mark.parametrize(
    ("title", "posting_id", "expected"),
    [
        ("Algorithmic Trading Engineer - ED", MS_POSTING, "senior"),
        ("Algorithmic Trading Engineer – ED", MS_POSTING, "senior"),
        ("Algorithmic Trading Engineer", MS_POSTING, None),
        ("Trading Analyst - ED", "Trading-Analyst_JR1", None),
        ("Trading Analyst - ED", None, None),
        ("Trading Analyst - ED", {}, None),
        ("Trading Analyst - ED", "Reports-to-Executive-Director_JR1", None),
        ("ED Trading Analyst", MS_POSTING, None),
    ],
)
def test_ms_abbreviation_needs_matching_published_posting_identifier(title, posting_id, expected):
    assert (
        workday_seniority_hint(
            "morgan_stanley", "Morgan Stanley", title, "<p>Trading</p>", posting_id
        )
        == expected
    )


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        (f"<p>{CITI_ROLE}</p>", "senior"),
        (f"<p>Reports to: {CITI_ROLE}</p>", None),
        (f"<p>Previous role: {CITI_ROLE}</p>", None),
        (f"<blockquote>{CITI_ROLE}</blockquote>", None),
        (CITI_ROLE, None),
        ("<p>Work alongside the Director on the EMEA Cash Electronic Execution Desk.</p>", None),
    ],
)
def test_citi_direct_role_statement_is_distinct_from_colleagues(description, expected):
    assert (
        workday_seniority_hint(
            "citi", "Citi", "Electronic Execution Sales Trader", description, None
        )
        == expected
    )


@pytest.mark.parametrize(
    ("source", "company"),
    [
        ("other", "Deutsche Bank"),
        ("deutsche_bank", "Other"),
        ("citi", "Other"),
        ("morgan_stanley", "Other"),
    ],
)
def test_source_and_employer_identity_are_required(source, company):
    assert (
        workday_seniority_hint(
            source,
            company,
            "Trading Engineer - ED",
            f"<p>Corporate Title Vice President</p><p>{CITI_ROLE}</p>",
            MS_POSTING,
        )
        is None
    )


def test_recognized_grade_reaches_existing_senior_exclusion(raw, config):
    raw.title = "Trader"
    raw.description = "<p>Corporate Title Vice President</p><p>FX trading Python pricing</p>"
    raw.seniority_hint = workday_seniority_hint(
        "deutsche_bank", "Deutsche Bank", raw.title, raw.description, None
    )
    job = score_job(normalize(raw), config.keywords)
    assert job.seniority == "senior"
    assert job.score_breakdown.total == 0
    assert job.score_breakdown.exclusions


@pytest.mark.parametrize(
    "wrapper",
    ["<blockquote>{}</blockquote>", "<q>{}</q>", "<template>{}</template>", "<div hidden>{}</div>"],
)
@pytest.mark.parametrize(
    ("source", "company", "body"),
    [
        ("deutsche_bank", "Deutsche Bank", "Corporate Title Vice President"),
        ("citi", "Citi", CITI_ROLE),
    ],
)
def test_hidden_or_quoted_paragraphs_do_not_describe_the_current_role(
    wrapper, source, company, body
):
    assert (
        workday_seniority_hint(source, company, "Trader", wrapper.format(f"<p>{body}</p>"), None)
        is None
    )


@pytest.mark.parametrize(
    ("source", "company", "title", "body", "posting_id"),
    [
        ("deutsche_bank", "Deutsche Bank", "Trader", "Corporate Title Vice President", None),
        ("citi", "Citi", "Electronic Execution Sales Trader", CITI_ROLE, None),
        (
            "morgan_stanley",
            "Morgan Stanley",
            "Algorithmic Trading Engineer - ED",
            "Trading",
            MS_POSTING,
        ),
    ],
)
def test_workday_detail_carries_the_derived_grade_to_scoring(
    config, source, company, title, body, posting_id
):
    description = f"<p>{body}</p>"

    class HTTP:
        async def get_json(self, *args):
            return {
                "jobPostingInfo": {
                    "id": "posting-1",
                    "title": title,
                    "jobDescription": description,
                    "jobPostingId": posting_id,
                }
            }

    collector = WorkdayCollector(
        source,
        Company(
            name=company, ats="workday", career_url="https://demo.wd3.myworkdayjobs.com/External"
        ),
        HTTP(),
    )
    raw = asyncio.run(collector._detail("/job/London/Trading_JR1", {"title": title}))
    assert raw.seniority_hint == "senior"
    assert raw.description == description
    assert raw.minimum_experience_years is None
    scored = score_job(normalize(raw), config.keywords)
    assert scored.seniority == "senior" and scored.score_breakdown.total == 0
