"""Degree observations preserve employer conditions and never change eligibility."""

import html

import pytest

from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions


def observed(job, content, source="drw"):
    return job.model_copy(update={"source": source, "description": content})


@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize(
    ("excerpt", "levels"),
    [
        ("PhD or MSc in a quantitative discipline.", ["master", "doctorate"]),
        (
            "A bachelor’s, master’s, or PhD graduating in June 2027",
            ["bachelor", "master", "doctorate"],
        ),
        ("BS, MS, or PhD, preferably in STEM", ["bachelor", "master", "doctorate"]),
        ("Bachelor’s degree (or equivalent practical experience)", ["bachelor"]),
        ("B.S. in Computer Science or equivalent degree", ["bachelor"]),
        ("Advanced degree in mathematics", ["unspecified_level"]),
        ("PhD preferred, not required", ["doctorate"]),
        ("No degree required", ["unspecified_level"]),
    ],
)
def test_exact_conditions_preserved_without_minimum_inference(job, excerpt, levels, escaped):
    content = f"<p>What you bring to the team…</p><ul><li>{excerpt}</li></ul>"
    current = observed(job, html.escape(content) if escaped else content)
    before = current.model_dump()
    result = education_mentions(current)
    assert result == {
        "levels": levels,
        "evidence": [
            {"heading": "What you bring to the team…", "excerpt": excerpt, "levels": levels}
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize("source", ["imc", "drw"])
def test_list_boundaries_do_not_capture_company_or_other_sections(job, source):
    heading = "Your Skills &amp; Experience:" if source == "imc" else "Required Qualifications:"
    content = f"""<p>Our team includes PhDs.</p><p>{heading}</p>
    <ul><li>Bachelor's degree</li></ul><p>Benefits</p><ul><li>Master's tuition reimbursement</li></ul>
    <p>About us</p><ul><li>PhD researchers lead our firm</li></ul>"""
    result = education_mentions(observed(job, content, source))
    assert result["levels"] == ["bachelor"]
    assert len(result["evidence"]) == 1


@pytest.mark.parametrize(
    "content",
    [
        "<p>Requirements:</p><p>About us</p><ul><li>PhD</li></ul>",
        "<p>Requirements:</p>About us<ul><li>PhD</li></ul>",
        "<p>Unknown criteria</p><ul><li>PhD</li></ul>",
        "<p>Requirements: PhD</p>",
        "<script><p>Requirements:</p><ul><li>PhD</li></ul></script>",
        "<div hidden><p>Requirements:</p><ul><li>PhD</li></ul></div>",
        "<p>Requirements:</p><ul><li><script>PhD</script>Trading skills</li></ul>",
        "<p>Requirements:</p><ul><li>Degree " + "x" * 1500 + "</li></ul>",
    ],
)
def test_unrecognized_or_hidden_context_is_not_a_degree_requirement(job, content):
    assert education_mentions(observed(job, content)) == {"levels": [], "evidence": []}


def test_unreviewed_sources_and_plain_text_are_not_guessed(job):
    assert not education_mentions(
        observed(job, "<p>Requirements:</p><ul><li>PhD</li></ul>", "test")
    )["levels"]
    assert not education_mentions(observed(job, "Requirements: PhD"))["levels"]


@pytest.mark.parametrize(
    "text",
    [
        "Master trading tools",
        "A high degree of autonomy",
        "Ms. Smith leads training",
        "BSpline modelling",
    ],
)
def test_nonacademic_words_are_not_degree_levels(job, text):
    assert not education_mentions(observed(job, f"<p>Requirements:</p><ul><li>{text}</li></ul>"))[
        "levels"
    ]


def test_nested_formatting_and_duplicate_excerpt(job):
    result = education_mentions(
        observed(
            job,
            "<h3>Requirements</h3><ul><li><strong>PhD</strong> or MSc</li><li>PhD or MSc</li></ul>",
        )
    )
    assert result["levels"] == ["master", "doctorate"]
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["excerpt"] == "PhD or MSc"


def test_dashboard_observation_leaves_all_tables_and_scores_unchanged(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    current = observed(job, "<p>Requirements:</p><ul><li>PhD or MSc</li></ul>")
    with repo.transaction():
        repo.upsert(current)
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    assert data["status"] == "ok"
    assert data["jobs"][0]["education"]["levels"] == ["master", "doctorate"]
    assert data["jobs"][0]["score"] == current.score_breakdown.total
    assert list(repo.db.iterdump()) == before
