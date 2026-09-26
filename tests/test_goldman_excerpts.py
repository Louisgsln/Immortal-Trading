"""Goldman section provenance, preserved conditions and presentation boundaries."""

import html
from xml.etree import ElementTree

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def observed(job, description, source="goldman_sachs"):
    return job.model_copy(update={"source": source, "description": description})


@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize(
    "heading",
    [
        "Responsibilities:",
        "KEY RESPONSIBILITIES",
        "Job Responsibilities",
        "Role Responsibilities",
        "Your Responsibilities:",
        "Principal Responsibilities",
        "General Responsibilities",
        "How You Will Fulfil Your Potential",
        "What You Will Do",
    ],
)
def test_missions_keep_first_three_complete_items(job, heading, escaped):
    content = f"""<p>Our firm brings together great minds.</p><h3>{heading}</h3>
    <ul><li>Support market making across rates products.</li>
    <li>Execute trades <strong>under supervision</strong> within trading limits.</li>
    <li>Monitor risk:<ul><li>Escalate exceptions before execution.</li></ul></li>
    <li>Collaborate with sales teams.</li></ul>
    <p>Basic Qualifications</p><ul><li>Master's degree preferred.</li></ul>"""
    current = observed(job, html.escape(content) if escaped else content)
    before = current.model_dump()
    assert mission_excerpts(current) == {
        "heading": heading,
        "excerpts": [
            "Support market making across rates products.",
            "Execute trades under supervision within trading limits.",
            "Monitor risk: Escalate exceptions before execution.",
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize(
    "heading",
    [
        "Qualifications",
        "BASIC QUALIFICATIONS",
        "Preferred Qualifications",
        "Required Qualifications:",
        "Required Qualifications and Skills",
        "Preferred Qualifications and Skills",
        "Basic Qualifications and Preferred Qualifications",
    ],
)
def test_degree_mentions_keep_employer_conditions_and_heading(job, heading, escaped):
    excerpt = "Bachelor’s degree or equivalent practical experience; Master’s or PhD preferred."
    content = f"""<p>Our team includes PhDs.</p><p><strong>{heading}</strong></p>
    <ul><li>{excerpt}</li><li>MS Office and a high degree of autonomy.</li></ul>
    <p>Benefits</p><ul><li>Master's tuition support.</li></ul>"""
    current = observed(job, html.escape(content) if escaped else content)
    before = current.model_dump()
    levels = ["bachelor", "master", "doctorate"]
    assert education_mentions(current) == {
        "levels": levels,
        "evidence": [{"heading": heading, "excerpt": excerpt, "levels": levels}],
    }
    assert current.model_dump() == before


def test_basic_and_preferred_qualifications_remain_separate(job):
    current = observed(
        job,
        "<h3>Basic Qualifications</h3><ul><li>Bachelor's degree or equivalent experience.</li></ul>"
        "<h3>Preferred Qualifications</h3><ul><li>PhD preferred, not required.</li></ul>",
    )
    result = education_mentions(current)
    assert result["levels"] == ["bachelor", "doctorate"]
    assert result["evidence"] == [
        {
            "heading": "Basic Qualifications",
            "excerpt": "Bachelor's degree or equivalent experience.",
            "levels": ["bachelor"],
        },
        {
            "heading": "Preferred Qualifications",
            "excerpt": "PhD preferred, not required.",
            "levels": ["doctorate"],
        },
    ]


@pytest.mark.parametrize(
    "excerpt,levels",
    [
        (
            "Excellent academic record (Bachelor or Master) in a relevant field such as computer science.",
            ["bachelor", "master"],
        ),
        ("Bachelor or master trading tools with practice.", ["bachelor"]),
        ("Master trading tools and MS Office.", []),
    ],
)
def test_parenthesized_degree_alternative_is_not_a_mastery_verb(job, excerpt, levels):
    current = observed(job, f"<h3>Basic Qualifications</h3><ul><li>{excerpt}</li></ul>")
    result = education_mentions(current)
    assert result["levels"] == levels
    if levels:
        assert result["evidence"][0]["excerpt"] == excerpt


@pytest.mark.parametrize(
    "heading",
    ["Responsibilities and Qualifications", "Responsibilities / Qualifications", "Your Impact"],
)
def test_mixed_or_unaudited_headings_do_not_become_missions_or_degrees(job, heading):
    current = observed(job, f"<h3>{heading}</h3><ul><li>Trade bonds with a PhD.</li></ul>")
    assert mission_excerpts(current) is None
    assert education_mentions(current) == {"levels": [], "evidence": []}


@pytest.mark.parametrize("source", ["goldman_campus", "test"])
def test_campus_and_other_sources_are_not_assumed_equivalent(job, source):
    current = observed(
        job,
        "<h3>Responsibilities</h3><ul><li>Trade bonds.</li></ul>"
        "<h3>Basic Qualifications</h3><ul><li>PhD</li></ul>",
        source,
    )
    assert mission_excerpts(current) is None
    assert not education_mentions(current)["levels"]


@pytest.mark.parametrize("second_heading", ["Responsibilities", "Key Responsibilities"])
def test_two_mission_sections_are_ambiguous(job, second_heading):
    content = "<h3>Responsibilities</h3><ul><li>Trade bonds.</li></ul>"
    content += f"<h3>{second_heading}</h3><ul><li>Manage risk.</li></ul>"
    assert mission_excerpts(observed(job, content)) is None


@pytest.mark.parametrize(
    "source,mission,qualification",
    [
        ("goldman_sachs", "Responsibilities", "Basic Qualifications"),
        ("drw", "Responsibilities", "Requirements"),
        ("imc", "Core Responsibilities", "Skills and Experience"),
    ],
)
@pytest.mark.parametrize(
    "hidden",
    [
        "<ul hidden><li>Hidden evidence</li></ul>",
        "<div hidden><ul><li>Hidden evidence</li></ul></div>",
        "<script>Hidden evidence</script>",
    ],
)
def test_hidden_content_cannot_supply_or_bridge_evidence(
    job, source, mission, qualification, hidden
):
    for heading, extract in [(mission, mission_excerpts), (qualification, education_mentions)]:
        content = f"<h3>{heading}</h3>{hidden}<ul><li>PhD researchers lead our company.</li></ul>"
        result = extract(observed(job, content, source))
        assert result is None or result == {"levels": [], "evidence": []}


def test_telegram_escapes_bounded_excerpts_and_retains_fallback(job):
    content = "<h3>Responsibilities</h3><ul><li>" + html.escape("🦊<&>" * 200) + "</li></ul>"
    current = observed(job, html.escape(content))
    card = format_alert(current, "new")
    assert "Missions · extraits" in card and "…" in card
    parsed = ElementTree.fromstring("<root>" + card + "</root>")
    assert len("".join(parsed.itertext()).encode("utf-16-le")) // 2 < 4096
    assert all(node.tag in {"root", "b", "i", "blockquote"} for node in parsed.iter())
    fallback = format_alert(observed(job, "Unstructured description"), "new")
    assert "Extrait de description" in fallback and "Missions · extraits" not in fallback


def test_dashboard_observations_leave_database_and_scores_unchanged(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    current = observed(
        job,
        html.escape(
            "<h3>Responsibilities</h3><ul><li>Trade &lt;/script&gt;&lt;img onerror=x&gt;</li></ul>"
            "<h3>Preferred Qualifications</h3><ul><li>PhD preferred, not required.</li></ul>"
        ),
    )
    with repo.transaction():
        repo.upsert(current)
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    assert data["jobs"][0]["missions"]["excerpts"] == ["Trade </script><img onerror=x>"]
    assert data["jobs"][0]["education"]["levels"] == ["doctorate"]
    assert data["jobs"][0]["score"] == current.score_breakdown.total
    assert "</script><img onerror=x>" not in render_dashboard(data)
    assert list(repo.db.iterdump()) == before
