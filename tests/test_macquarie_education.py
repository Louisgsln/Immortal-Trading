"""Whole Macquarie requirement sections retain provenance through normal scans."""

import asyncio
import html

import pytest

from trading_radar.config import Company
from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.http import SourceUnavailable
from trading_radar.macquarie import DETAIL, SEARCH, parse_detail
from trading_radar.models import Collection
from trading_radar.normalizer import normalize
from trading_radar.scanner import scan
from trading_radar.scoring import score_job
from trading_radar.telegram_cards import format_alert

COMPANY = Company(name="Macquarie", ats="macquarie", career_url=SEARCH, enabled=True)
ROW = {"id": "123", "title": "Trading Analyst", "url": DETAIL + "?jobId=123"}


def field(value, label="", cls=""):
    return (
        f'<div class="article__content__view__field {cls}">'
        + (f'<div class="article__content__view__field__label">{label}</div>' if label else "")
        + f'<div class="article__content__view__field__value">{value}</div></div>'
    )


def page(values, *, role="Trade FX and derivatives. Python."):
    return (
        '<h2 class="title--11">Trading Analyst</h2><article class="article__content__fields">'
        + field("123", "Job ID", "field--jobcategory")
        + field("London", cls="field--location")
        + field("Permanent - Full time, Junior", cls="field--employmentterm")
        + field("26-Sep-2026", "Date", "field--date")
        + '</article><section class="section--without--border--top">'
        + "<article><h3>What role will you play?</h3>"
        + field(role)
        + "</article><article><h3>What you offer</h3>"
        + "".join(field(value) for value in values)
        + "</article></section>"
    )


def collect(text):
    return parse_detail(text, ROW, COMPANY, "macquarie")


@pytest.mark.parametrize(
    "value,levels",
    [
        ("Undergraduate or Masters students graduating in June 2027.", ["master"]),
        ("Bachelor’s or master's degree preferred.", ["bachelor", "master"]),
        ("A quantitative degree is preferred, but not required.", ["unspecified_level"]),
        ("Postgraduate degree in a quantitative discipline.", ["unspecified_level"]),
        ("Tertiary qualification, ideally in a quantitative discipline.", ["unspecified_level"]),
        ("A degree in Computer Science is an advantage.", ["unspecified_level"]),
        ("No PhD required; equivalent work experience accepted.", ["doctorate"]),
        ("Strong academic background in financial markets.", []),
        ("Master data skills and 5 years trading experience.", []),
        ("Bac+5 ou M2", []),
    ],
)
def test_whole_section_preserves_preference_and_alternative_across_fields(value, levels):
    alternative = "Alternatively, relevant professional experience will be considered."
    current = normalize(collect(page([html.escape(value), alternative])))
    assert current.raw_payload is None
    result = education_mentions(current)
    assert result["levels"] == levels
    assert result["evidence"] == (
        [{"heading": "What you offer", "excerpt": value + " " + alternative, "levels": levels}]
        if levels
        else []
    )


def test_bullets_and_multiple_fields_stay_together():
    current = normalize(
        collect(
            page(
                [
                    "<ul><li>Bachelor's degree preferred.</li><li>English fluent.</li></ul>",
                    "Or equivalent experience.",
                ]
            )
        )
    )
    assert (
        education_mentions(current)["evidence"][0]["excerpt"]
        == "Bachelor's degree preferred. English fluent. Or equivalent experience."
    )


def test_audited_keyboard_instruction_is_not_part_of_employer_requirements():
    text = page(["Bachelor Degree", "Or equivalent experience."]).replace(
        "What you offer</h3>",
        "What you offer</h3><span>Press space or enter keys to toggle section visibility</span>",
    )
    result = education_mentions(normalize(collect(text)))
    assert result["evidence"][0]["excerpt"] == "Bachelor Degree Or equivalent experience."


@pytest.mark.parametrize(
    "change",
    [
        "hidden_section",
        "hidden_ancestor",
        "aria_hidden",
        "css_hidden",
        "hidden_value",
        "hidden_heading",
        "template",
        "subheading",
        "outside_conditions",
        "interleaved_conditions",
    ],
)
def test_ambiguous_or_hidden_requirements_have_no_provenance(change):
    text = page(["Bachelor Degree", "Or equivalent experience."])
    if change == "hidden_section":
        text = text.replace("<article><h3>What you offer", "<article hidden><h3>What you offer")
    elif change == "hidden_ancestor":
        text = "<div hidden>" + text + "</div>"
    elif change == "aria_hidden":
        text = '<div aria-hidden="true">' + text + "</div>"
    elif change == "css_hidden":
        text = '<div style="display: none">' + text + "</div>"
    elif change == "hidden_value":
        text = text.replace("Bachelor Degree", "<span hidden>Bachelor Degree</span>")
    elif change == "hidden_heading":
        text = text.replace("<h3>What you offer", "<h3 hidden>What you offer")
    elif change == "template":
        text = "<template>" + text + "</template>"
    elif change == "subheading":
        text = text.replace("Bachelor Degree", "<h4>Preferred</h4>Bachelor Degree")
    elif change == "outside_conditions":
        text = text.replace(
            "What you offer</h3>", "What you offer</h3><p>Optional requirements:</p>"
        )
    else:
        text = text.replace(
            field("Or equivalent experience."), "<p>Or:</p>" + field("Or equivalent experience.")
        )
    raw = collect(text)
    assert "data-macquarie-section" not in raw.description
    assert not education_mentions(normalize(raw))["evidence"]


def test_duplicate_requirements_are_a_collection_error():
    text = page(["Bachelor Degree"]).replace(
        "</section>",
        "<article><h3>What you offer</h3>" + field("Master's degree") + "</article></section>",
    )
    with pytest.raises(SourceUnavailable, match="requirements missing"):
        collect(text)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate",
        "wrong_heading",
        "nested",
        "hidden",
        "inline",
        "outside_text",
        "unlabelled",
        "oversized",
    ],
)
def test_persisted_section_requires_bounded_complete_plain_paragraphs(change):
    current = normalize(collect(page(["Bachelor Degree"])))
    description = current.description
    if change == "duplicate":
        description += description
    elif change == "wrong_heading":
        description = description.replace("What you offer", "What role will you play?")
    elif change == "nested":
        description = "<div>" + description + "</div>"
    elif change == "hidden":
        description = description.replace("<section ", "<section hidden ")
    elif change == "inline":
        description = description.replace("Bachelor Degree", "<b>Bachelor Degree</b>")
    elif change == "outside_text":
        description = description.replace("</section>", "Or other conditions</section>")
    elif change == "unlabelled":
        description = "<p>Bachelor Degree</p>"
    else:
        description = description.replace("Bachelor Degree", "Bachelor Degree " + "x" * 1500)
    current.description = description
    assert not education_mentions(current)["evidence"]


@pytest.mark.parametrize(
    "source", ["mac", "credit_agricole_cib", "societe_generale", "morgan_stanley"]
)
def test_section_and_special_degree_wording_are_source_scoped(source):
    current = normalize(collect(page(["Tertiary qualification."])))
    current.source = source
    assert not education_mentions(current)["evidence"]


def test_non_requirements_degree_does_not_leak_into_candidate_criteria():
    current = normalize(
        collect(page(["Strong trading track record."], role="Mentor Masters students."))
    )
    assert not education_mentions(current)["evidence"]


def test_refresh_preserves_experience_scores_history_and_applied_tracking(config, repo, tmp_path):
    new_raw = collect(
        page(
            [
                "5 years of experience in sales trading. Proven ability to work independently. A degree in Finance is preferred.",
                "Or equivalent academic background.",
            ]
        )
    )
    old_raw = new_raw.model_copy(
        update={
            "description": new_raw.description.replace(
                '<section data-macquarie-section="What you offer">', ""
            ).replace("</section>", "")
        }
    )
    old = score_job(normalize(old_raw), config.keywords)
    current = score_job(normalize(new_raw), config.keywords)
    assert old.description_text == current.description_text
    assert old.score_breakdown == current.score_breakdown
    assert old.minimum_experience_years == current.minimum_experience_years == 5
    assert old.experience_evidence == current.experience_evidence
    assert old.date_posted is current.date_posted is None
    assert format_alert(old, "new") == format_alert(current, "new")
    with repo.transaction():
        repo.upsert(old)
    repo.update_application(old.id, {"status": "Applied", "notes": "Synthetic follow-up"})
    config.companies = {"macquarie": COMPANY}
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    config.settings.alerts_enabled = False
    protected = [
        "applications",
        "application_history",
        "alerts",
        "alert_history",
        "score_history",
        "job_versions",
    ]
    before = {
        name: [tuple(row) for row in repo.db.execute("SELECT * FROM " + name)] for name in protected
    }

    class Saved:
        async def collect(self):
            return Collection(jobs=[new_raw], complete=False)

    for _ in range(2):
        result = asyncio.run(scan(config, repo, collectors={"macquarie": Saved()}))
        assert (
            not result.failed
            and result.new == result.updated == result.closed == result.alerts == 0
        )
    stored = repo.get(old.id)
    assert stored.first_seen == old.first_seen and stored.date_updated == old.date_updated
    assert stored.raw_payload is None
    for name, rows in before.items():
        assert [tuple(row) for row in repo.db.execute("SELECT * FROM " + name)] == rows
    snapshot = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    assert data["jobs"][0]["education"]["levels"] == ["unspecified_level"]
    assert data["jobs"][0]["application"]["status"] == "Applied"
    assert list(repo.db.iterdump()) == snapshot


def test_markup_from_employer_cannot_escape_dashboard_data(config, repo, tmp_path):
    current = score_job(
        normalize(collect(page([html.escape("Bachelor Degree & </script><img onerror=x>")]))),
        config.keywords,
    )
    with repo.transaction():
        repo.upsert(current)
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    assert "</script><img onerror=x>" not in render_dashboard(
        build_dashboard_data(config, tmp_path / "history")
    )
