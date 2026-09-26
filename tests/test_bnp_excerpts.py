"""Audited BNP lists retain source wording and never change eligibility."""

import html
from xml.etree import ElementTree

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def observed(job, description, source="bnp_paribas"):
    return job.model_copy(update={"source": source, "description": description})


@pytest.mark.parametrize(
    "heading",
    [
        "Direct Responsibilities:",
        "Main Responsibilities:",
        "Principal Role Accountabilities",
        "Your Main Activities Are",
        "What you will do",
    ],
)
def test_mission_items_keep_conditions_and_nested_details(job, heading):
    current = observed(
        job,
        html.escape(
            f"<p>About BNP Paribas</p><p><strong>{heading}</strong></p><ul>"
            "<li>Produce daily risk reports under supervision.</li>"
            "<li>Price derivatives <b>within desk limits</b> and escalate exceptions.</li>"
            "<li>Improve models:<ul><li>Validate changes before use.</li></ul></li>"
            "<li>Meet clients.</li></ul>"
            "<p>Contributing Responsibilities</p><ul><li>Mentor colleagues.</li></ul>"
        ),
    )
    before = current.model_dump()
    assert mission_excerpts(current) == {
        "heading": heading,
        "excerpts": [
            "Produce daily risk reports under supervision.",
            "Price derivatives within desk limits and escalate exceptions.",
            "Improve models: Validate changes before use.",
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    "heading",
    [
        "Profile and Skills to Success",
        "To be considered for the placement, you will:",
        "What is required for you to succeed?",
        "Your profile",
        "Essential:",
        "Technical & Behavioral Competencies",
        "Requirements:",
    ],
)
def test_qualification_lists_keep_preferences_equivalents_and_disciplines(job, heading):
    excerpt = "Bachelor’s or Master’s Degree in Finance, Mathematics, Engineering, or equivalent experience."
    current = observed(
        job,
        f"<p>About us</p><ul><li>Our team includes PhDs.</li></ul>"
        f"<h3>{heading}</h3><ul><li>{excerpt}</li><li>MS Office and master trading tools.</li></ul>"
        "<p>Benefits</p><ul><li>Doctoral degree tuition support.</li></ul>",
    )
    assert education_mentions(current) == {
        "levels": ["bachelor", "master"],
        "evidence": [
            {"heading": heading, "excerpt": excerpt, "levels": ["bachelor", "master"]},
        ],
    }


@pytest.mark.parametrize(
    "excerpt,levels",
    [
        ("Master in Engineering or Finance", ["master"]),
        ("Master’s Degree Financial Mathematics or Stochastic Calculation", ["master"]),
        (
            "Apply as a recent graduate, final year undergraduate, or master’s student in any discipline;",
            ["master"],
        ),
        (
            "A university degree in a relevant field (Economics, Finance, Business Administration, etc.)",
            ["unspecified_level"],
        ),
        (
            "BTech/MTech/PhD from an Indian institute, or Masters/PhD from a foreign institution, with a preference for Mathematics/Computer Science oriented degrees",
            ["master", "doctorate"],
        ),
        (
            "BTech or MTech from a reputed institution, or a PhD in another Science or engineering field",
            ["doctorate"],
        ),
    ],
)
def test_audited_degree_forms_preserve_alternatives_without_equivalence(job, excerpt, levels):
    current = observed(job, f"<p>Profile and Skills to Success</p><ul><li>{excerpt}</li></ul>")
    result = education_mentions(current)
    assert result["levels"] == levels
    assert result["evidence"][0]["excerpt"] == excerpt


def test_conditional_programme_tracks_are_not_substituted_for_common_missions(job):
    current = observed(
        job,
        "<p>What you will do</p><p>Depending on your placement:</p>"
        "<p>As a Sales Analyst, you will:</p><ul><li>Work with clients.</li></ul>"
        "<p>As a Trading Analyst, you will:</p><ul><li>Manage trading risk.</li></ul>",
    )
    assert mission_excerpts(current) is None
    assert "Extrait de description" in format_alert(current, "new")


@pytest.mark.parametrize(
    "content",
    [
        "<p>Direct Responsibilities</p><ul><li>Trade bonds.</li></ul>" * 2,
        "<p>Direct Responsibilities</p><ul><li>Trade bonds.</li></ul><p>Main Responsibilities</p><ul><li>Manage risk.</li></ul>",
        "<p>Direct Responsibilities</p><ul><li>" + "x" * 1501 + "</li></ul>",
        "<p>Direct Responsibilities</p><ul><li hidden>Trade bonds.</li></ul>",
        "<p>What you will do</p><p>Only for some placements:</p><ul><li>Trade bonds.</li></ul>",
    ],
)
def test_ambiguous_missions_keep_full_description_fallback(job, content):
    assert mission_excerpts(observed(job, content)) is None


@pytest.mark.parametrize(
    "content",
    [
        "<p>Profile and Skills to Success</p><p>Bachelor degree.</p>",
        "<p>Requirements</p><p>For example:</p><ul><li>Bachelor degree.</li></ul>",
        "<p>Requirements</p><ul><li>" + "Master degree " + "x" * 1500 + "</li></ul>",
        "<p>Requirements</p><ul><li>Apply as a penultimate or final year undergraduate in any discipline.</li></ul>",
        "<p>Requirements</p><ul><li>BTech or MTech with relevant experience.</li></ul>",
        "<p>Requirements</p><ul><li>Master trading tools and MS Office.</li></ul>",
    ],
)
def test_no_degree_inferred_from_unrecognized_formats_or_training(job, content):
    assert education_mentions(observed(job, content)) == {"levels": [], "evidence": []}


@pytest.mark.parametrize("wrapper", ["<div hidden>{}</div>", "<template>{}</template>"])
def test_hidden_sections_are_not_evidence(job, wrapper):
    content = "<p>Direct Responsibilities</p><ul><li>Trade bonds.</li></ul><p>Your profile</p><ul><li>Master degree.</li></ul>"
    current = observed(job, wrapper.format(content))
    assert mission_excerpts(current) is None
    assert not education_mentions(current)["evidence"]


@pytest.mark.parametrize("source", ["workday", "bnp_campus", "citi"])
def test_source_specific_rules_do_not_expand_other_employers(job, source):
    current = observed(
        job,
        "<p>Direct Responsibilities</p><ul><li>Trade bonds.</li></ul>"
        "<p>Requirements</p><ul><li>Master in Finance</li></ul>",
        source,
    )
    assert mission_excerpts(current) is None
    assert not education_mentions(current)["evidence"]


def test_master_in_form_stays_scoped_even_with_a_supported_heading(job):
    current = observed(
        job, "<p>Requirements</p><ul><li>Master in Finance</li></ul>", "morgan_stanley"
    )
    assert not education_mentions(current)["evidence"]


def test_telegram_escaping_and_message_limit(job):
    current = observed(
        job,
        html.escape(
            "<p>Direct Responsibilities</p><ul><li>" + html.escape("🦊<&>" * 200) + "</li></ul>"
        ),
    )
    card = format_alert(current, "new")
    parsed = ElementTree.fromstring("<root>" + card + "</root>")
    assert "Missions · extraits" in card and "…" in card
    assert len("".join(parsed.itertext()).encode("utf-16-le")) // 2 < 4096
    assert all(node.tag in {"root", "b", "i", "blockquote"} for node in parsed.iter())


def test_dashboard_preserves_scores_dates_and_applied_status(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    current = observed(
        job,
        html.escape(
            "<p>What you will do</p><ul><li>Trade &lt;/script&gt;&lt;img onerror=x&gt;</li></ul>"
            "<p>Profile and Skills to Success</p><ul><li>Master in Engineering or Finance</li></ul>"
        ),
    )
    with repo.transaction():
        repo.upsert(current)
    repo.update_application(current.id, {"status": "Applied", "notes": "Follow up next week"})
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    result = data["jobs"][0]
    assert result["missions"]["excerpts"] == ["Trade </script><img onerror=x>"]
    assert result["education"]["levels"] == ["master"]
    assert result["score"] == current.score_breakdown.total
    assert result["application"]["status"] == "Applied"
    assert result["first_seen"] == current.first_seen.isoformat()
    assert "</script><img onerror=x>" not in render_dashboard(data)
    assert list(repo.db.iterdump()) == before
