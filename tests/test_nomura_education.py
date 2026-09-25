"""Nomura degree mentions use the bounded qualification field, not team biographies."""

import html

import pytest

from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions


def description(excerpt, *, requisition="", role="Role &amp; Responsibilities:"):
    return (
        "<p>Our team includes PhDs. Position Specifications: "
        "Corporate Title Analyst Functional Title Analyst Experience 1-3 years "
        f"Qualification {excerpt} {requisition} {role} "
        "Support trading. Benefits include Master's tuition.</p>"
    )


def observed(job, content):
    return job.model_copy(update={"source": "nomura_professionals", "description": content})


@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize(
    ("excerpt", "levels", "requisition", "role"),
    [
        (
            "Bachelor's or Master's degree (Good to have: CFA/FRM)",
            ["bachelor", "master"],
            "Requisition No. 13845",
            "Role &amp; Responsibilities:",
        ),
        (
            "Master’s, Phd, or equivalent degree program in CSE, mathematics, sciences, statistics",
            ["master", "doctorate"],
            "",
            "R ole &amp; Responsibilities:",
        ),
        ("PhD preferred, not required", ["doctorate"], "", "Role &amp; Responsibilities:"),
        ("No degree required", ["unspecified_level"], "", "Role &amp; Responsibilities:"),
        (
            "Bachelor's degree or equivalent practical experience",
            ["bachelor"],
            "",
            "Role &amp; Responsibilities:",
        ),
    ],
)
def test_exact_qualification_preserves_alternatives_and_conditions(
    job, excerpt, levels, requisition, role, escaped
):
    content = description(excerpt, requisition=requisition, role=role)
    current = observed(job, html.escape(content) if escaped else content)
    before = current.model_dump()
    assert education_mentions(current) == {
        "levels": levels,
        "evidence": [
            {
                "heading": "Position Specifications → Qualification",
                "excerpt": excerpt,
                "levels": levels,
            }
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    "content",
    [
        description("Tier 1 Engineering College Graduate / Post Graduate"),
        description("MBA with prior experience preferred"),
        description("Master trading tools and MS Excel"),
        description("CFA/FRM"),
        description("PhD").replace("Position Specifications:", "Requirements:"),
        description("PhD").replace("Role &amp; Responsibilities:", "Other duties:"),
        description("PhD").replace("Corporate Title Analyst", ""),
        description("PhD").replace("Experience 1-3 years", ""),
        description("PhD").replace("Qualification PhD", "Qualification PhD Qualification MSc"),
        description("PhD") + description("Master's degree"),
        description("PhD").replace("Position Specifications:", "Example Position Specifications:"),
        description("PhD").replace("Position Specifications:", "Optional Position Specifications:"),
        description("PhD", requisition="Requisition No. unknown"),
        description("PhD " + "x" * 1500),
        description("PhD").replace("Analyst Functional", "x" * 2100 + " Functional"),
        "<div hidden>" + description("PhD") + "</div>",
        "<script>" + description("PhD") + "</script>",
        description("<span hidden>PhD</span>Trading skills"),
        description("<script>PhD</script>Trading skills"),
    ],
)
def test_missing_ambiguous_hidden_or_unsupported_fields_are_not_guessed(job, content):
    assert education_mentions(observed(job, content)) == {"levels": [], "evidence": []}


def test_nomura_table_is_source_specific(job):
    content = description("PhD")
    for source in ("nomura_campus", "drw", "imc", "unknown"):
        assert not education_mentions(
            job.model_copy(update={"source": source, "description": content})
        )["levels"]


def test_dashboard_degree_observations_preserve_database(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    current = observed(job, description("Bachelor's or Master's degree"))
    with repo.transaction():
        repo.upsert(current)
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    assert data["jobs"][0]["education"]["levels"] == ["bachelor", "master"]
    assert data["jobs"][0]["score"] == current.score_breakdown.total
    assert list(repo.db.iterdump()) == before
