"""Jump excerpts keep duties, candidate qualifications and benefits separate."""

import html
from xml.etree import ElementTree

import pytest

from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def observed(job, content):
    return job.model_copy(update={"source": "jump_trading", "description": content})


@pytest.mark.parametrize("heading", ["Skills You’ll Need:", "Skills you will need:"])
@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize(
    ("excerpt", "levels"),
    [
        ("Master or PhD degree in applied mathematics", ["master", "doctorate"]),
        ("Bachelor, Masters or PhD in Computer Science", ["bachelor", "master", "doctorate"]),
        ("PhD preferred, not required", ["doctorate"]),
        ("Bachelor's degree or equivalent practical experience", ["bachelor"]),
    ],
)
def test_qualifications_keep_complete_alternatives(job, heading, escaped, excerpt, levels):
    content = (
        "<p>Our team includes PhDs.</p><p>What You'll Do:</p><ul><li>Trade bonds</li></ul>"
        f"<p>{heading}</p><ul><li>{excerpt}</li></ul>"
        "<p>Benefits</p><ul><li>Master's tuition reimbursement</li></ul>"
    )
    current = observed(job, html.escape(content) if escaped else content)
    before = current.model_dump()
    assert education_mentions(current) == {
        "levels": levels,
        "evidence": [{"heading": heading, "excerpt": excerpt, "levels": levels}],
    }
    assert mission_excerpts(current)["excerpts"] == ["Trade bonds"]
    assert current.model_dump() == before


@pytest.mark.parametrize(
    "content",
    [
        "<p>What You'll Do:</p><p>Benefits</p><ul><li>Insurance</li></ul>",
        "<p>What You'll Do:</p>Our team<ul><li>Trade</li></ul>",
        "<p>What You'll Do:</p><ul><li>Trade</li></ul>" * 2,
        "<div hidden><p>What You'll Do:</p><ul><li>Trade</li></ul></div>",
        "<p>What You'll Do:</p><ul><li>" + "x" * 1501 + "</li></ul>",
        "<p>Skills You'll Need:</p><ul><li>Trading experience</li></ul>",
        "What You'll Do: Trade bonds",
    ],
)
def test_unrecognized_or_ambiguous_missions_keep_telegram_fallback(job, content):
    current = observed(job, content)
    assert mission_excerpts(current) is None
    assert "Extrait de description" in format_alert(current, "new")


@pytest.mark.parametrize(
    "content",
    [
        "<p>Ideal candidates will have:</p><ul><li>PhD</li></ul>",
        "<p>Skills You'll Need:</p><p>Benefits</p><ul><li>PhD</li></ul>",
        "<div hidden><p>Skills You'll Need:</p><ul><li>PhD</li></ul></div>",
        "<p>Skills You'll Need:</p><ul><li>Master or MS Excel</li></ul>",
    ],
)
def test_unreviewed_qualification_context_is_not_guessed(job, content):
    assert not education_mentions(observed(job, content))["levels"]


def test_nested_project_list_and_card_truncation(job):
    items = ["Only within limits: " + "🦊<&>" * 70, "Research signals", "Support execution"]
    content = "<p>What You'll Do:</p><ul><li>Contribute to one or more projects:<ul>"
    content += "".join(f"<li>{html.escape(item)}</li>" for item in items)
    content += "</ul></li></ul>"
    current = observed(job, html.escape(content))
    assert mission_excerpts(current)["excerpts"] == [
        "Contribute to one or more projects: " + " ".join(items)
    ]
    card = format_alert(current, "new")
    rendered = "".join(ElementTree.fromstring("<root>" + card + "</root>").itertext())
    assert "Missions · extraits" in rendered and "…" in rendered
    assert len(rendered.encode("utf-16-le")) // 2 < 4096


def test_jump_dashboard_keeps_scores_and_tables(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    content = (
        "<p>What You'll Do:</p><ul><li>Trade within limits</li></ul>"
        "<p>Skills You'll Need:</p><ul><li>Master or PhD degree</li></ul>"
    )
    current = observed(job, content)
    with repo.transaction():
        repo.upsert(current)
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    assert data["jobs"][0]["missions"]["excerpts"] == ["Trade within limits"]
    assert data["jobs"][0]["education"]["levels"] == ["master", "doctorate"]
    assert data["jobs"][0]["score"] == current.score_breakdown.total
    assert list(repo.db.iterdump()) == before
