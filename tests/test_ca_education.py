"""Retained CA field provenance, literal degree mentions and scan transitions."""

import asyncio
import html

import pytest

from trading_radar.ca_cib import EDUCATION_FIELD, SEARCH, parse_detail
from trading_radar.config import Company
from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.http import SourceUnavailable
from trading_radar.models import Collection
from trading_radar.normalizer import normalize
from trading_radar.scanner import scan
from trading_radar.scoring import score_job
from trading_radar.telegram_cards import format_alert

SOURCE = "credit_agricole_cib"
LABEL = "Minimal education level"
ROW = {
    "id": "123",
    "reference": "2026-123",
    "title": "Trading Analyst",
    "url": "https://jobs.ca-cib.com/offre-de-emploi/emploi-trading-analyst_123.aspx",
}
COMPANY = Company(name="Crédit Agricole CIB", ats="ca_cib", career_url=SEARCH, enabled=True)


def field(value, label=LABEL):
    return f'<h3>{html.escape(label)}</h3><p id="{EDUCATION_FIELD}">{html.escape(value)}</p>'


def collect(block):
    fields = {
        "fldjobdescription_jobtitle": ROW["title"],
        "fldjobdescription_description1": "Trading FX on a front office desk. Python.",
        "fldjobdescription_contract": "Permanent",
        "fldlocation_joblocation": "London",
        "fldlocation_location_geographicalareacollection": "Europe, UK",
        "fldapplicantcriteria_experiencelevel": "0-2 years",
    }
    page = (
        '<h1 class="ts-offer-page__title">Trading Analyst</h1>'
        '<div class="ts-offer-page__reference"><h3>Reference</h3>2026-123</div>'
        + "".join(f'<p id="{key}">{value}</p>' for key, value in fields.items())
        + block
    )
    return parse_detail(page, ROW, COMPANY, SOURCE)


@pytest.mark.parametrize(
    "value,levels",
    [
        ("Bachelor Degree / BSc Degree or equivalent", ["bachelor"]),
        ("Bac + 5 / M2 et plus", ["bac_plus_5"]),
        ("Postgraduate degree – MA/MSc/PhD/Doctorate or equivalent", ["master", "doctorate"]),
        (
            "Bachelor's or Master's degree preferred; equivalent experience accepted.",
            ["bachelor", "master"],
        ),
        ("No Bachelor's degree required; experience accepted.", ["bachelor"]),
        ("Bac+4/5, diplôme en cours accepté.", ["bac_plus_4", "bac_plus_5"]),
        ("Bac + 50", []),
        ("Bac+4/6", []),
        ("M2 ou grande école", []),
        ("Master data management skills", []),
    ],
)
def test_only_literal_mentions_with_complete_alternatives_survive_without_raw_storage(
    value, levels
):
    current = normalize(collect(field(value)))
    assert current.raw_payload is None
    result = education_mentions(current)
    assert result["levels"] == levels
    assert result["evidence"] == (
        [{"heading": LABEL, "excerpt": value, "levels": levels}] if levels else []
    )


@pytest.mark.parametrize("label", [LABEL, "Niveau d'études minimum", "Niveau d’études minimum"])
def test_verified_labels_are_preserved_exactly(label):
    result = education_mentions(normalize(collect(field("Bac + 5 / M2 et plus", label))))
    assert result["evidence"][0]["heading"] == label


@pytest.mark.parametrize(
    "block",
    [
        f'<p id="{EDUCATION_FIELD}">Bachelor Degree</p>',
        field("Bachelor Degree", "Preferred skills"),
        field("Bachelor Degree").replace("h3", "h2"),
        field("Bachelor Degree").replace("</h3>", "</h3>Optional: "),
        field("Bachelor Degree").replace("</h3>", "</h3><p>Optional:</p>"),
        field("Bachelor Degree").replace("<h3>", "<h3 hidden>"),
        field("Bachelor Degree").replace("<p id=", "<p hidden id="),
        field("Bachelor Degree").replace("Bachelor Degree", "<b>Bachelor Degree</b>"),
        "<div hidden>" + field("Bachelor Degree") + "</div>",
        '<div aria-hidden="true">' + field("Bachelor Degree") + "</div>",
        '<div style="display: none">' + field("Bachelor Degree") + "</div>",
        '<div style="visibility: hidden">' + field("Bachelor Degree") + "</div>",
        "<template>" + field("Bachelor Degree") + "</template>",
    ],
)
def test_unsupported_or_hidden_provenance_keeps_the_description_without_education(block):
    raw = collect(block)
    assert "Bachelor" in raw.description
    assert "data-ca-field" not in raw.description
    assert not education_mentions(normalize(raw))["evidence"]


def test_duplicate_field_remains_a_collection_error():
    with pytest.raises(SourceUnavailable, match="duplicate detail field"):
        collect(field("Bachelor Degree") + field("Master's degree"))


@pytest.mark.parametrize(
    "change", ["duplicate", "wrong_field", "wrong_label", "wrapped", "hidden", "nested", "too_long"]
)
def test_persisted_description_requires_one_bounded_verified_field(change):
    current = normalize(collect(field("Bachelor Degree")))
    description = current.description
    if change == "duplicate":
        description += description
    elif change == "wrong_field":
        description = description.replace(EDUCATION_FIELD, "fldjobdescription_description1")
    elif change == "wrong_label":
        description = description.replace(LABEL, "Optional education")
    elif change == "wrapped":
        description = "<div>" + description + "</div>"
    elif change == "hidden":
        description = description.replace("data-ca-field=", "hidden data-ca-field=")
    elif change == "nested":
        description = description.replace("Bachelor Degree", "<b>Bachelor Degree</b>")
    else:
        description = description.replace("Bachelor Degree", "Bachelor Degree " + "x" * 1500)
    current.description = description
    assert not education_mentions(current)["evidence"]


@pytest.mark.parametrize("source", ["societe_generale", "nomura_professionals", "citi", "ca_cib"])
def test_field_provenance_is_source_scoped(source):
    current = normalize(collect(field("Bachelor Degree")))
    current.source = source
    assert not education_mentions(current)["evidence"]


def test_refresh_preserves_scores_history_applications_alerts_and_publication(
    config, repo, tmp_path
):
    new_raw = collect(field("Bachelor Degree / BSc Degree or equivalent"))
    old_raw = collect(f'<p id="{EDUCATION_FIELD}">Bachelor Degree / BSc Degree or equivalent</p>')
    old = score_job(normalize(old_raw), config.keywords)
    current = score_job(normalize(new_raw), config.keywords)
    assert old.description_text == current.description_text
    assert old.score_breakdown == current.score_breakdown
    assert old.date_posted is current.date_posted is None
    assert old.experience_evidence == current.experience_evidence
    assert format_alert(old, "new") == format_alert(current, "new")
    with repo.transaction():
        repo.upsert(old)
    repo.update_application(old.id, {"status": "Applied", "notes": "Synthetic follow-up"})
    config.companies = {SOURCE: COMPANY}
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
        metrics = asyncio.run(scan(config, repo, collectors={SOURCE: Saved()}))
        assert not metrics.failed
        assert metrics.new == metrics.updated == metrics.closed == metrics.alerts == 0
    stored = repo.get(old.id)
    assert stored.first_seen == old.first_seen
    assert stored.date_updated == old.date_updated
    assert stored.raw_payload is None
    for name, rows in before.items():
        assert [tuple(row) for row in repo.db.execute("SELECT * FROM " + name)] == rows
    snapshot = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    assert data["jobs"][0]["education"]["levels"] == ["bachelor"]
    assert data["jobs"][0]["application"]["status"] == "Applied"
    assert list(repo.db.iterdump()) == snapshot


def test_field_cannot_introduce_active_markup_into_dashboard(config, repo, tmp_path):
    current = score_job(
        normalize(collect(field("Bachelor Degree & </script><img onerror=x>"))), config.keywords
    )
    with repo.transaction():
        repo.upsert(current)
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    rendered = render_dashboard(build_dashboard_data(config, tmp_path / "history"))
    assert "</script><img onerror=x>" not in rendered
