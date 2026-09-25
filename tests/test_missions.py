"""Section provenance, exact employer wording and safe presentation of missions."""

import html
from xml.etree import ElementTree

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def observed(job, content, source="drw"):
    return job.model_copy(update={"source": source, "description": content})


@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize(
    ("source", "heading"),
    [
        ("drw", "Responsibilities:"),
        ("drw", "Key Responsibilities"),
        ("drw", "Core Responsibilities:"),
        ("drw", "What you’ll be working on:"),
        ("drw", "What You'll Do"),
        ("drw", "How you will make an impact…"),
        ("drw", "What you would do"),
        ("drw", "What you will do:"),
        ("drw", "What you’ll do in this role:"),
        ("imc", "Your Core Responsibilities"),
        ("imc", "Core Responsibilities"),
        ("imc", "Key Responsibilities"),
        ("imc", "YOUR CORE RESPONSIBILTIES"),
    ],
)
def test_audited_lists_keep_first_three_complete_items(job, source, heading, escaped):
    items = [
        "Trade <strong>only</strong> within limits.",
        "Research or support execution.",
        "Do not take overnight risk.",
        "Report to the desk.",
    ]
    content = f"<p>Our purpose is opportunity.</p><h3>{heading}</h3><ul>"
    content += "".join(f"<li>{item}</li>" for item in items)
    content += "</ul><p>Requirements</p><ul><li>Five years experience</li></ul>"
    current = observed(job, html.escape(content) if escaped else content, source)
    before = current.model_dump()
    assert mission_excerpts(current) == {
        "heading": heading,
        "excerpts": [
            "Trade only within limits.",
            "Research or support execution.",
            "Do not take overnight risk.",
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    "content",
    [
        "Responsibilities: Trade bonds",
        "<p>Requirements</p><ul><li>Trading experience</li></ul>",
        "<p>Responsibilities</p><p>Benefits</p><ul><li>Insurance</li></ul>",
        "<p>Responsibilities</p>About us<ul><li>Traders worldwide</li></ul>",
        "<div hidden><p>Responsibilities</p><ul><li>Trade</li></ul></div>",
        "<script><p>Responsibilities</p><ul><li>Trade</li></ul></script>",
        "<p>Responsibilities</p><ul><li><script>Trade</script></li></ul>",
        "<p>Responsibilities</p><ul><li>" + "x" * 1501 + "</li></ul>",
        "<p>Responsibilities</p><ul><li>Trade</li></ul>" * 2,
        "<p>Responsibilities</p><ul></ul>",
    ],
)
def test_ambiguous_unbounded_hidden_or_unrecognized_sections_fall_back(job, content):
    assert mission_excerpts(observed(job, content)) is None


def test_source_boundaries_and_nested_conditions(job):
    content = "<p>Responsibilities</p><ul><li>Execute within limits:<ul><li>Only liquid instruments</li></ul></li></ul>"
    assert mission_excerpts(observed(job, content, "test")) is None
    assert mission_excerpts(observed(job, content, "imc")) is None
    assert mission_excerpts(observed(job, content))["excerpts"] == [
        "Execute within limits: Only liquid instruments"
    ]


@pytest.mark.parametrize(
    ("start", "body", "end", "excerpts"),
    [
        (
            "Purpose of the Job",
            "Lend client securities\nwithin the agreed risk framework.",
            "Environment of the Job",
            ["Lend client securities within the agreed risk framework."],
        ),
        (
            "Les grandes lignes :",
            "* Pricing des produits Repo\n* Outils d’aide à la décision\n* Monitoring des P&L\n* Réconciliation",
            "Profil recherché :",
            ["Pricing des produits Repo", "Outils d’aide à la décision", "Monitoring des P&L"],
        ),
        (
            "In this role you will:",
            "* Identify opportunities\nwithin client mandates\n* Provide coverage",
            "To be successful in this role you should meet the following requirements:",
            ["Identify opportunities within client mandates", "Provide coverage"],
        ),
    ],
)
def test_hsbc_bounded_sections_remove_marketing_and_qualifications(job, start, body, end, excerpts):
    content = (
        f"<p>Opening up a world of opportunity\n{start}\n{body}\n{end}\nFive years experience</p>"
    )
    assert mission_excerpts(observed(job, content, "hsbc_professionals")) == {
        "heading": start,
        "excerpts": excerpts,
    }


@pytest.mark.parametrize(
    "body",
    [
        "Purpose of the Job\nTrade",  # Missing closing boundary.
        "Purpose of the Job\nEnvironment of the Job",  # Empty.
        "Environment of the Job\nPurpose of the Job\nTrade",  # Reversed.
        "Purpose of the Job\nTrade\nPurpose of the Job\nTrade\nEnvironment of the Job",
        "Purpose of the Job\nTrade\nEnvironment of the Job\nEnvironment of the Job",
        "Les grandes lignes :\nOur team\n* Trade\nProfil recherché :",  # Unreviewed prose.
        "Purpose of the Job\nTrade\nEnvironment of the Job\nLes grandes lignes :\n* Trade\nProfil recherché :",
    ],
)
def test_hsbc_requires_unambiguous_complete_boundaries(job, body):
    assert mission_excerpts(observed(job, f"<p>{body}</p>", "hsbc_professionals")) is None


def test_telegram_uses_missions_and_explicit_fallback(job):
    current = observed(job, "<p>Responsibilities</p><ul><li>Trade &amp; hedge</li></ul>")
    card = format_alert(current, "new")
    assert "Missions · extraits" in card and "• Trade &amp; hedge" in card
    assert job.description_text[:50] not in card
    fallback = format_alert(job, "new")
    assert "Extrait de description" in fallback and "Missions · extraits" not in fallback


def test_telegram_limits_and_escapes_mission_text_in_utf16(job):
    text = "🦊<&>" * 200
    content = "<p>Responsibilities</p><ul>" + f"<li>{html.escape(text)}</li>" * 3 + "</ul>"
    current = observed(job, html.escape(content)).model_copy(
        update={
            "title": "🦊" * 300,
            "company": "🦊" * 200,
            "location_normalized": "🦊" * 200,
            "expected_start_date": "🦊" * 200,
        }
    )
    card = format_alert(current, "new")
    root = ElementTree.fromstring("<root>" + card + "</root>")
    assert all(node.tag in {"root", "b", "i", "blockquote"} for node in root.iter())
    assert len("".join(root.itertext()).encode("utf-16-le")) // 2 < 4096
    assert card.count("• ") == 3 and card.count("…") >= 3


def test_dashboard_adds_safe_detached_missions_without_writes(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    content = (
        "<p>Responsibilities</p><ul><li>Trade &lt;/script&gt;&lt;img onerror=alert(1)&gt;</li></ul>"
    )
    current = observed(job, html.escape(content))
    with repo.transaction():
        repo.upsert(current)
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    assert data["jobs"][0]["missions"]["excerpts"] == ["Trade </script><img onerror=alert(1)>"]
    assert data["jobs"][0]["score"] == current.score_breakdown.total
    page = render_dashboard(data)
    assert "</script><img onerror=alert(1)>" not in page
    assert list(repo.db.iterdump()) == before
