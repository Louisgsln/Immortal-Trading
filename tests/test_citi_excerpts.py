"""Citi excerpts preserve responsibilities, alternatives and source boundaries."""

import html
from xml.etree import ElementTree

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def citi(job, description, source="citi"):
    return job.model_copy(update={"source": source, "description": description})


@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize("heading", ["Responsibilities:", "Key Responsibilities", "What you’ll do"])
def test_missions_preserve_nested_conditions_and_first_three_items(job, heading, escaped):
    content = f"""<p>Our purpose and values.</p><p><b>{heading}</b></p>
    <ul><li>Support trading book risk management.</li>
    <li>Develop pricing tools <strong>under supervision</strong> within trading limits.</li>
    <li>Monitor exposures:<ul><li>Escalate exceptions before execution.</li></ul></li>
    <li>Collaborate with sales.</li></ul>
    <p>Education:</p><ul><li>Master’s degree preferred.</li></ul>"""
    current = citi(job, html.escape(content) if escaped else content)
    before = current.model_dump()
    assert mission_excerpts(current) == {
        "heading": heading,
        "excerpts": [
            "Support trading book risk management.",
            "Develop pricing tools under supervision within trading limits.",
            "Monitor exposures: Escalate exceptions before execution.",
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize("heading", ["Education:", "Qualifications", "Recommended Qualifications:"])
def test_degree_evidence_keeps_alternatives_and_preferences(job, heading, escaped):
    content = f"""<p>Our team includes PhDs.</p><h3>{heading}</h3>
    <ul><li>Bachelor’s degree/University degree or equivalent experience</li>
    <li>Master’s degree preferred</li><li>MS Office proficiency.</li></ul>
    <p>Benefits</p><ul><li>Doctoral degree tuition support.</li></ul>"""
    current = citi(job, html.escape(content) if escaped else content)
    before = current.model_dump()
    assert education_mentions(current) == {
        "levels": ["bachelor", "master"],
        "evidence": [
            {
                "heading": heading,
                "excerpt": "Bachelor’s degree/University degree or equivalent experience",
                "levels": ["bachelor"],
            },
            {
                "heading": heading,
                "excerpt": "Master’s degree preferred",
                "levels": ["master"],
            },
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    ("excerpt", "levels"),
    [
        ("Bachelor’s/University degree", ["bachelor"]),
        ("Bachelor’s/University degree, Master’s degree preferred", ["bachelor", "master"]),
        ("University degree preferred.", ["unspecified_level"]),
        ("Juris Doctorate or equivalent law degree", ["doctorate"]),
        ("Advanced degree, CPA and / or CFA a big plus;", []),
        ("Students completing their six-month internship requirement.", []),
    ],
)
def test_no_unstated_degree_level_is_inferred(job, excerpt, levels):
    current = citi(job, f"<p>Education:</p><ul><li>{excerpt}</li></ul>")
    result = education_mentions(current)
    assert result["levels"] == levels
    if levels:
        assert result["evidence"][0]["excerpt"] == excerpt


@pytest.mark.parametrize(
    "heading",
    ["What we can offer you", "Responsibilities and Qualifications", "Most Relevant Skills"],
)
def test_unaudited_or_mixed_sections_are_not_reinterpreted(job, heading):
    current = citi(job, f"<h3>{heading}</h3><ul><li>Trade bonds with a PhD.</li></ul>")
    assert mission_excerpts(current) is None
    assert education_mentions(current) == {"levels": [], "evidence": []}


def test_recommended_and_education_headings_keep_their_own_context(job):
    current = citi(
        job,
        "<p>Recommended Qualifications:</p><ul><li>Master’s degree preferred</li></ul>"
        "<p>Education:</p><ul><li>Bachelor’s degree or equivalent experience</li></ul>",
    )
    assert [item["heading"] for item in education_mentions(current)["evidence"]] == [
        "Recommended Qualifications:",
        "Education:",
    ]


@pytest.mark.parametrize("source", ["citi_campus", "workday", "test"])
def test_citi_templates_do_not_enable_unaudited_sources(job, source):
    current = citi(
        job,
        "<p>Responsibilities:</p><ul><li>Trade bonds.</li></ul>"
        "<p>Education:</p><ul><li>PhD preferred.</li></ul>",
        source,
    )
    assert mission_excerpts(current) is None
    assert not education_mentions(current)["evidence"]


@pytest.mark.parametrize("hidden", ["<ul hidden><li>PhD</li></ul>", "<div hidden>PhD</div>"])
def test_hidden_lists_cannot_bridge_to_unlabelled_lists(job, hidden):
    current = citi(
        job,
        f"<p>Responsibilities:</p>{hidden}<ul><li>Trade bonds.</li></ul>"
        f"<p>Education:</p>{hidden}<ul><li>PhD preferred.</li></ul>",
    )
    assert mission_excerpts(current) is None
    assert not education_mentions(current)["evidence"]


@pytest.mark.parametrize(
    "content",
    [
        "<p>Responsibilities:</p><ul><li>Trade bonds.</li></ul>"
        "<p>What you’ll do</p><ul><li>Manage risk.</li></ul>",
        "<p>Responsibilities:</p><p>Optional example, not the role.</p><ul><li>Trade.</li></ul>",
        "<p>Responsibilities: Trade bonds and manage risk.</p>",
        "<p>Responsibilities:</p><ul><li>" + "x" * 1501 + "</li></ul>",
    ],
)
def test_ambiguous_unstructured_or_overlong_missions_keep_fallback(job, content):
    current = citi(job, content)
    assert mission_excerpts(current) is None
    card = format_alert(current, "new")
    assert "Extrait de description" in card and "Missions · extraits" not in card


def test_telegram_escapes_and_bounds_citi_excerpts(job):
    content = "<p>Responsibilities:</p><ul><li>" + html.escape("🦊<&>" * 200) + "</li></ul>"
    current = citi(job, html.escape(content))
    card = format_alert(current, "new")
    assert "Missions · extraits" in card and "…" in card
    parsed = ElementTree.fromstring("<root>" + card + "</root>")
    assert len("".join(parsed.itertext()).encode("utf-16-le")) // 2 < 4096
    assert all(node.tag in {"root", "b", "i", "blockquote"} for node in parsed.iter())


def test_dashboard_adds_evidence_without_changing_stored_jobs_or_applications(
    config, repo, job, tmp_path
):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    current = citi(
        job,
        html.escape(
            "<p>Responsibilities:</p><ul><li>Trade &lt;/script&gt;&lt;img onerror=x&gt;</li></ul>"
            "<p>Education:</p><ul><li>Bachelor’s degree or equivalent experience</li>"
            "<li>Master’s degree preferred</li></ul>"
        ),
    )
    with repo.transaction():
        repo.upsert(current)
    repo.update_application(current.id, {"status": "Applied", "notes": "Keep my follow-up"})
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    result = data["jobs"][0]
    assert result["missions"]["excerpts"] == ["Trade </script><img onerror=x>"]
    assert result["education"]["levels"] == ["bachelor", "master"]
    assert result["score"] == current.score_breakdown.total
    assert result["application"]["status"] == "Applied"
    assert "</script><img onerror=x>" not in render_dashboard(data)
    assert list(repo.db.iterdump()) == before
