"""Audited UBS field boundaries and complete academic qualification evidence."""

import html

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def observed(job, description, source="ubs_professionals"):
    return job.model_copy(update={"source": source, "description": description})


def qualification(body, heading="Your skills and experience", next_heading="About us"):
    return f"<h2>{heading}</h2>{body}<h2>{next_heading}</h2>Our team includes PhDs."


@pytest.mark.parametrize("breaks", ["<br>", "<br/>", "<br />\n", "\n"])
def test_bullets_keep_degree_preferences_alternatives_and_section_boundaries(job, breaks):
    body = breaks.join(
        [
            "• Bachelor's degree (or equivalent) in Finance or a related field",
            "• Master's degree preferred, not required",
            "• Proficient in MS Office; master trading tools",
        ]
    )
    current = observed(
        job,
        html.escape(
            "<h2>Key responsibilities</h2>Doctoral degree tuition support." + qualification(body)
        ),
    )
    before = current.model_dump()
    assert education_mentions(current) == {
        "levels": ["bachelor", "master"],
        "evidence": [
            {
                "heading": "Your skills and experience",
                "excerpt": "Bachelor's degree (or equivalent) in Finance or a related field",
                "levels": ["bachelor"],
            },
            {
                "heading": "Your skills and experience",
                "excerpt": "Master's degree preferred, not required",
                "levels": ["master"],
            },
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    "body,levels",
    [
        ("Degree in Finance or equivalent", ["unspecified_level"]),
        ("University degree, CFA would be a plus", ["unspecified_level"]),
        ("Completed law degree and Swiss bar admission", ["unspecified_level"]),
        ("A graduate degree with a financial background", ["unspecified_level"]),
        (
            "Ideally a bachelor's degree in science, technology, engineering or mathematics",
            ["bachelor"],
        ),
        ("Bachelor’s/master’s degree in finance and/or legal background", ["bachelor", "master"]),
        ("Degree in Computer Science (PhD preferred but not a pre-requisite)", ["doctorate"]),
        (
            "Bachelor's degree required; CFA designation, MBA, or other relevant professional credentials are considered a plus",
            ["bachelor"],
        ),
    ],
)
def test_degree_evidence_never_infers_equivalence_or_minimum(job, body, levels):
    result = education_mentions(observed(job, qualification("•" + body)))
    assert result["levels"] == levels
    assert result["evidence"] == [
        {"heading": "Your skills and experience", "excerpt": body, "levels": levels}
    ]


def test_preface_is_retained_with_qualification_and_inline_markup(job):
    current = observed(
        job,
        qualification(
            "Preferred qualifications, not mandatory:<br/><br/>"
            "• A <strong>Bachelor’s</strong> degree or equivalent experience<br/>• A <font>Master’s degree</font> is a plus"
        ),
    )
    result = education_mentions(current)
    assert (
        result["evidence"][0]["excerpt"]
        == "Preferred qualifications, not mandatory: A Bachelor’s degree or equivalent experience"
    )
    assert (
        result["evidence"][1]["excerpt"]
        == "Preferred qualifications, not mandatory: A Master’s degree is a plus"
    )


@pytest.mark.parametrize(
    "description",
    [
        "<h2>Your skills and experience</h2>• Bachelor degree",
        qualification("• Bachelor degree", next_heading="Benefits"),
        qualification("• Bachelor degree") * 2,
        qualification("• Bachelor degree", heading="Example: Your skills and experience"),
        qualification("• Bachelor degree").replace("h2", "h3"),
        "<div>" + qualification("• Bachelor degree") + "</div>",
        qualification("Bachelor degree"),
        qualification("• Bachelor degree<br/>or equivalent professional experience"),
        qualification("• Bachelor degree<br/>• "),
        qualification("• Bachelor degree<br/><ul><li>or equivalent experience</li></ul>"),
        qualification("• Bachelor degree<br/><div>or equivalent experience</div>"),
        qualification("• High degree of integrity<br/>• MS Office and master trading tools"),
        qualification("• Bachelor's degree " + "x" * 1500),
        qualification("• Bachelor degree").replace("<h2>About us", "<h2 hidden>About us"),
    ],
)
def test_unrecognized_or_ambiguous_sections_stay_in_full_description(job, description):
    assert education_mentions(observed(job, description)) == {"levels": [], "evidence": []}


@pytest.mark.parametrize("tag", ["script", "style", "template", "noscript", "span hidden"])
def test_hidden_content_is_never_degree_evidence(job, tag):
    content = qualification(
        f"<{tag}>• Doctoral degree<br/></{tag.split()[0]}>• Bachelor's degree or equivalent"
    )
    result = education_mentions(observed(job, content))
    assert result["levels"] == ["bachelor"]
    assert result["evidence"][0]["excerpt"] == "Bachelor's degree or equivalent"


def test_hidden_headings_are_not_qualifications(job):
    content = qualification("• Bachelor degree").replace(
        "<h2>Your skills", "<h2 hidden>Your skills"
    )
    assert not education_mentions(observed(job, content))["evidence"]


@pytest.mark.parametrize("source", ["ubs", "ubs_campus", "workday", "deutsche_bank"])
def test_ubs_field_rules_remain_scoped_to_professional_source(job, source):
    assert not education_mentions(
        observed(job, qualification("• University degree, CFA a plus"), source)
    )["evidence"]


def test_repeated_evidence_is_not_duplicated(job):
    result = education_mentions(
        observed(
            job,
            qualification("• Bachelor degree or equivalent<br/>• Bachelor degree or equivalent"),
        )
    )
    assert result["levels"] == ["bachelor"]
    assert len(result["evidence"]) == 1


def test_dashboard_preserves_scores_dates_applications_and_telegram(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    original = observed(job, "<h2>Key responsibilities</h2>• Trade bonds")
    current = observed(
        job,
        original.description
        + html.escape(qualification("• University degree in &lt;/script&gt;&lt;img onerror=x&gt;")),
    )
    assert format_alert(current, "new") == format_alert(original, "new")
    assert mission_excerpts(current) is None
    with repo.transaction():
        repo.upsert(current)
    repo.update_application(current.id, {"status": "Applied", "notes": "Follow up next week"})
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    result = data["jobs"][0]
    assert result["education"]["levels"] == ["unspecified_level"]
    assert (
        result["education"]["evidence"][0]["excerpt"]
        == "University degree in </script><img onerror=x>"
    )
    assert result["score"] == current.score_breakdown.total
    assert result["application"]["status"] == "Applied"
    assert result["first_seen"] == current.first_seen.isoformat()
    assert "</script><img onerror=x>" not in render_dashboard(data)
    assert list(repo.db.iterdump()) == before
