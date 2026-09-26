"""Audited Deutsche Bank and Morgan Stanley sections without degree equivalence."""

import html
from xml.etree import ElementTree

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def observed(job, source, description):
    return job.model_copy(update={"source": source, "description": description})


@pytest.mark.parametrize(
    ("source", "heading"),
    [
        ("deutsche_bank", "Your key responsibilities:"),
        ("deutsche_bank", "Key Responsibilities"),
        ("deutsche_bank", "What You’ll Do"),
        ("morgan_stanley", "Responsibilities"),
        ("morgan_stanley", "Primary Responsibilities:"),
        ("morgan_stanley", "Key Responsibilities"),
        ("morgan_stanley", "What you'll do in the role:"),
        ("morgan_stanley", "What you’ll do :"),
    ],
)
def test_missions_preserve_limits_nested_items_and_employer_heading(job, source, heading):
    content = html.escape(
        f"<p>Our firm invests in its people.</p><p><b>{heading}</b></p>"
        "<ul><li>Price bonds within approved limits.</li>"
        "<li>Support traders <strong>under supervision</strong> on the desk.</li>"
        "<li>Monitor exposures:<ul><li>Escalate exceptions before execution.</li></ul></li>"
        "<li>Work with clients.</li></ul><p>Benefits</p><ul><li>Paid leave.</li></ul>"
    )
    current = observed(job, source, content)
    before = current.model_dump()
    assert mission_excerpts(current) == {
        "heading": heading,
        "excerpts": [
            "Price bonds within approved limits.",
            "Support traders under supervision on the desk.",
            "Monitor exposures: Escalate exceptions before execution.",
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    ("source", "heading"),
    [
        ("deutsche_bank", "Your skills and experience:"),
        ("deutsche_bank", "Skills You’ll Need"),
        ("deutsche_bank", "Skills That Will Help You Excel"),
        ("morgan_stanley", "Qualifications"),
        ("morgan_stanley", "Requirements"),
        ("morgan_stanley", "What you'll bring to the role:"),
        ("morgan_stanley", "Skills Desirable:"),
    ],
)
def test_qualifications_preserve_preferences_and_equivalent_experience(job, source, heading):
    excerpt = "Bachelor’s degree or equivalent work experience; Masters degree preferred."
    current = observed(
        job,
        source,
        f"<p>Our team includes PhDs.</p><h3>{heading}</h3><ul><li>{excerpt}</li>"
        "<li>MS Office and master trading tools.</li></ul>"
        "<p>Benefits</p><ul><li>Doctoral degree tuition support.</li></ul>",
    )
    before = current.model_dump()
    assert education_mentions(current) == {
        "levels": ["bachelor", "master"],
        "evidence": [{"heading": heading, "excerpt": excerpt, "levels": ["bachelor", "master"]}],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    ("excerpt", "levels"),
    [
        (
            "Recent undergraduate degree with a strong academic performance.",
            ["unspecified_level"],
        ),
        (
            "Educated to Degree level (Finance, Accounting, Economics, Engineering) from a good University or Business School",
            ["unspecified_level"],
        ),
        (
            "Educated to degree level (preferably in Finance, Economics, Quantitative Methods or a related discipline) or equivalent qualification and/or work experience",
            ["unspecified_level"],
        ),
        ("Educated to a degree level or equivalent work experience.", ["unspecified_level"]),
        ("Undergraduate degree, preferably a Bachelor's degree in mathematics.", ["bachelor"]),
        ("Accounting qualification: ACA, ACCA, CFA, FRM and/or MSc in Finance.", ["master"]),
        ("Ph.D. in Applied Mathematics, Statistics or Operations Research.", ["doctorate"]),
        ("A high degree of autonomy and undergraduate mentoring experience.", []),
        ("Educated clients about the degree of risk in their portfolio.", []),
        ("Degree-level attention to detail and a strong work ethic.", []),
    ],
)
def test_degree_level_is_not_assumed_from_education_or_professional_certifications(
    job, excerpt, levels
):
    current = observed(
        job, "deutsche_bank", f"<p>Your skills and experience</p><ul><li>{excerpt}</li></ul>"
    )
    result = education_mentions(current)
    assert result["levels"] == levels
    if levels:
        assert result["evidence"][0]["excerpt"] == excerpt


@pytest.mark.parametrize("source", ["deutsche_bank", "morgan_stanley"])
@pytest.mark.parametrize(
    "heading", ["What We Offer You", "Responsibilities and Qualifications", "Company Profile"]
)
def test_unaudited_sections_remain_outside_excerpts(job, source, heading):
    current = observed(job, source, f"<p>{heading}</p><ul><li>Trade bonds with a PhD.</li></ul>")
    assert mission_excerpts(current) is None
    assert not education_mentions(current)["evidence"]


@pytest.mark.parametrize(
    ("source", "mission", "qualification"),
    [
        ("deutsche_bank", "Your key responsibilities", "Skills You’ll Need"),
        ("morgan_stanley", "Primary Responsibilities", "Qualifications"),
    ],
)
def test_hidden_and_nonadjacent_lists_do_not_supply_evidence(job, source, mission, qualification):
    for gap in ["<ul hidden><li>Hidden</li></ul>", "<p>Example only, not the role.</p>"]:
        content = f"<p>{mission}</p>{gap}<ul><li>Trade bonds.</li></ul>"
        content += f"<p>{qualification}</p>{gap}<ul><li>Undergraduate degree.</li></ul>"
        current = observed(job, source, content)
        assert mission_excerpts(current) is None
        assert not education_mentions(current)["evidence"]


@pytest.mark.parametrize("source", ["deutsche_bank", "morgan_stanley"])
def test_two_mission_sections_keep_the_description_fallback(job, source):
    current = observed(
        job,
        source,
        "<p>What you'll do</p><ul><li>Trade bonds.</li></ul>"
        "<p>Key Responsibilities</p><ul><li>Manage risk.</li></ul>",
    )
    assert mission_excerpts(current) is None
    assert "Extrait de description" in format_alert(current, "new")


def test_unsupported_source_stays_unsupported(job):
    current = observed(
        job,
        "workday",
        "<p>Your key responsibilities</p><ul><li>Trade bonds.</li></ul>"
        "<p>Your skills and experience</p><ul><li>Undergraduate degree.</li></ul>",
    )
    assert mission_excerpts(current) is None
    assert not education_mentions(current)["evidence"]


@pytest.mark.parametrize("source", ["deutsche_bank", "morgan_stanley"])
def test_telegram_cards_remain_escaped_and_bounded(job, source):
    content = "<p>What you'll do</p><ul><li>" + html.escape("🦊<&>" * 200) + "</li></ul>"
    card = format_alert(observed(job, source, html.escape(content)), "new")
    assert "Missions · extraits" in card and "…" in card
    parsed = ElementTree.fromstring("<root>" + card + "</root>")
    assert len("".join(parsed.itertext()).encode("utf-16-le")) // 2 < 4096
    assert all(node.tag in {"root", "b", "i", "blockquote"} for node in parsed.iter())


def test_dashboard_preserves_scores_dates_and_application_tracking(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    current = observed(
        job,
        "deutsche_bank",
        html.escape(
            "<p>Your key responsibilities</p><ul><li>Trade &lt;/script&gt;&lt;img onerror=x&gt;</li></ul>"
            "<p>Your skills and experience</p><ul><li>Educated to degree level or equivalent experience.</li></ul>"
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
