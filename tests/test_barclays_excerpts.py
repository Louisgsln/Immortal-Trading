"""Barclays list and inline qualification boundaries, without eligibility changes."""

import html
from xml.etree import ElementTree

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def observed(job, description, source="barclays"):
    return job.model_copy(update={"source": source, "description": description})


def qualification(body, tag="p", prefix="", heading="Who we're looking for"):
    return f"<{tag}>{prefix}<b>{heading}</b><br/>{body}</{tag}>"


@pytest.mark.parametrize(
    "tag,prefix",
    [
        ("p", ""),
        ("p", "<br/>"),
        ("div", ""),
        ("p", "<b>Markets</b><br/>Our team includes PhDs.<br/><br/>"),
    ],
)
def test_inline_qualification_keeps_full_conditions_and_container_boundary(job, tag, prefix):
    body = (
        "To be considered, you must be pursuing an undergraduate degree with anticipated "
        "completion between December 2026 - June 2027.<br/><br/>"
        "Ideally, you have a GPA of 3.2.<br/><span>Declare any visa sponsorship needs.</span>"
    )
    current = observed(
        job, html.escape(qualification(body, tag, prefix) + "<p>Benefits: Masters tuition.</p>")
    )
    before = current.model_dump()
    assert education_mentions(current) == {
        "levels": ["unspecified_level"],
        "evidence": [
            {
                "heading": "Who we're looking for",
                "excerpt": "To be considered, you must be pursuing an undergraduate degree with anticipated completion between December 2026 - June 2027. Ideally, you have a GPA of 3.2. Declare any visa sponsorship needs.",
                "levels": ["unspecified_level"],
            }
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    "body",
    [
        "You must be motivated and curious with a degree or expected degree, in any area.",
        "You must be in your penultimate or final year of your degree, in any discipline.",
        "You must be pursuing a post-graduate degree with graduation in June 2028.",
        "A postgraduate degree is preferred, or equivalent experience.",
    ],
)
def test_barclays_degree_variants_do_not_infer_level_or_completed_degree(job, body):
    result = education_mentions(
        observed(job, qualification(body, heading="Who we’re looking for:"))
    )
    assert result["levels"] == ["unspecified_level"]
    assert result["evidence"][0]["excerpt"] == body


def test_list_and_inline_evidence_preserve_alternatives_and_preferences(job):
    current = observed(
        job,
        "<p>Essential Skills/Basic Qualifications:</p><ul>"
        "<li>Bachelor’s degree or educational equivalent (LLB or equivalent)</li></ul>"
        + qualification("Masters degree preferred, not required; equivalent experience accepted."),
    )
    result = education_mentions(current)
    assert set(result["levels"]) == {"bachelor", "master"}
    assert {e["heading"] for e in result["evidence"]} == {
        "Who we're looking for",
        "Essential Skills/Basic Qualifications:",
    }
    assert result["evidence"][0]["excerpt"].endswith(
        "not required; equivalent experience accepted."
    )
    assert result["evidence"][1]["excerpt"].endswith("(LLB or equivalent)")


@pytest.mark.parametrize(
    "content",
    [
        "<p>Who we're looking for<br/>Bachelor degree.</p>",
        "<p>For example: <b>Who we're looking for</b><br/>Bachelor degree.</p>",
        "<p><b>Who we're looking for</b> Bachelor degree.</p>",
        "<p><b>Who we're looking for</b></p><p>Bachelor degree.</p>",
        qualification("Bachelor degree.<br/><b>Benefits</b><br/>Doctorate tuition."),
        qualification("<div>Bachelor degree.</div>"),
        qualification("Bachelor degree.") * 2,
        qualification("Bachelor degree.") + "<p><b>Who we're looking for</b></p>",
        qualification("Bachelor degree." + "x" * 1500),
        qualification("A high degree of initiative; master trading tools and MS Office."),
        qualification("A university student or recent graduate."),
        "<p>Essential Skills/Basic Qualifications:</p><p>Context</p><ul><li>Bachelor degree.</li></ul>",
    ],
)
def test_unrecognized_or_ambiguous_education_is_not_inferred(job, content):
    assert education_mentions(observed(job, content)) == {"levels": [], "evidence": []}


@pytest.mark.parametrize(
    "wrapper", ["<div hidden>{}</div>", "<template>{}</template>", "<noscript>{}</noscript>"]
)
def test_hidden_qualifications_are_not_evidence(job, wrapper):
    hidden = wrapper.format(qualification("Bachelor degree."))
    assert not education_mentions(observed(job, hidden))["evidence"]
    result = education_mentions(observed(job, hidden + qualification("Masters degree preferred.")))
    assert result["levels"] == ["master"]


def test_missions_select_common_accountabilities_and_keep_full_items(job):
    current = observed(
        job,
        "<p><b>Accountabilities</b></p><ul>"
        "<li>Price bonds within approved limits.</li>"
        "<li>Monitor markets and <strong>escalate</strong> unusual exposures.</li>"
        "<li>Manage risk:<ul><li>Follow desk limits.</li></ul></li>"
        "<li>Prepare reports.</li></ul>"
        "<p>As a Trading analyst, you may:</p><ul><li>Trade derivatives.</li></ul>"
        "<p>Analyst Expectations</p><ul><li>Lead teams.</li></ul>",
    )
    assert mission_excerpts(current) == {
        "heading": "Accountabilities",
        "excerpts": [
            "Price bonds within approved limits.",
            "Monitor markets and escalate unusual exposures.",
            "Manage risk: Follow desk limits.",
        ],
    }


@pytest.mark.parametrize(
    "content",
    [
        "<p>Accountabilities</p><ul><li>Trade bonds.</li></ul>" * 2,
        "<p>Accountabilities</p><ul><li>" + "x" * 1501 + "</li></ul>",
        "<p>Accountabilities</p><ul><li hidden>Trade bonds.</li></ul>",
        "<p>Analyst Expectations</p><ul><li>Lead teams.</li></ul>",
    ],
)
def test_mission_fallback_when_unrecognized(job, content):
    current = observed(job, content)
    assert mission_excerpts(current) is None
    assert "Extrait de description" in format_alert(current, "new")


@pytest.mark.parametrize("source", ["workday", "barclays_campus", "citi"])
def test_inline_rules_are_scoped_to_audited_source(job, source):
    current = observed(
        job,
        qualification("Bachelor degree.") + "<p>Accountabilities</p><ul><li>Trade bonds.</li></ul>",
        source,
    )
    assert not education_mentions(current)["evidence"]
    assert mission_excerpts(current) is None


def test_telegram_escaping_and_limit(job):
    current = observed(
        job,
        html.escape("<p>Accountabilities</p><ul><li>" + html.escape("🦊<&>" * 200) + "</li></ul>"),
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
            "<p>Accountabilities</p><ul><li>Trade &lt;/script&gt;&lt;img onerror=x&gt;</li></ul>"
            + qualification("A degree or expected degree, in any area.")
        ),
    )
    with repo.transaction():
        repo.upsert(current)
    repo.update_application(current.id, {"status": "Applied", "notes": "Follow up next week"})
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    result = data["jobs"][0]
    assert result["missions"]["excerpts"] == ["Trade </script><img onerror=x>"]
    assert result["education"]["levels"] == ["unspecified_level"]
    assert result["score"] == current.score_breakdown.total
    assert result["application"]["status"] == "Applied"
    assert result["first_seen"] == current.first_seen.isoformat()
    assert "</script><img onerror=x>" not in render_dashboard(data)
    assert list(repo.db.iterdump()) == before
