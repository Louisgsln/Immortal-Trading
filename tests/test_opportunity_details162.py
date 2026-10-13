import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.test_ubs import config as ubs_config
from tests.test_ubs import detail
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.deadlines import resolve_deadline
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.opportunity_details import opportunity_details
from trading_radar.opportunity_facts import country_facts, start_facts
from trading_radar.scoring import score_job
from trading_radar.telegram_cards import format_alert
from trading_radar.ubs import parse_detail


def observed(description="", **kwargs):
    return normalize(
        RawJob(
            company="Synthetic",
            title="Trader",
            apply_url="https://example.com/job",
            source="fixture",
            description=description,
            **kwargs,
        )
    )


def test_official_ubs_crypto_experience_is_visible_without_invented_dates_or_years(config):
    raw = RawJob(**json.loads(Path("tests/fixtures/ubs-crypto162.json").read_text()))
    job = score_job(normalize(raw), config.keywords, settings=config.settings)
    before = job.model_dump()
    data = opportunity_details(job)
    assert data["location"]["label"] == "Singapour (SG)"
    assert data["experience"]["status"] == "qualitative"
    assert "Expérience préalable en actifs numériques ou desk eFX" in data["experience"]["label"]
    assert "DA native company" in data["experience"]["evidence"][0]
    assert data["experience"]["minimum_years"] is None
    assert data["start"]["status"] == data["deadline"]["status"] == "not_published"
    card = format_alert(job, "new")
    assert "📍 Singapour (SG)" in card and "Expérience préalable" in card
    assert card.count("Date non indiquée par l’employeur") == 2
    assert "Expérience : à vérifier" not in card
    assert job.model_dump() == before


@pytest.mark.parametrize("heading", ["Requirements", "Qualifications", "Your profile"])
def test_candidate_experience_qualifiers_are_kept_in_full(heading):
    text = "Previous experience in trading is preferred, not required."
    data = opportunity_details(
        observed(
            f"<h2>{heading}</h2><ul><li>{text}</li></ul><h2>About us</h2><p>50 years of company experience.</p>"
        )
    )
    assert data["experience"]["status"] == "qualitative"
    assert text in data["experience"]["evidence"][0]
    assert data["experience"]["minimum_years"] is None


@pytest.mark.parametrize(
    "body",
    [
        "<script>Previous experience in crypto</script>",
        "<span hidden>Previous experience in crypto</span>",
        "Strong focus on the client experience.",
    ],
)
def test_hidden_and_customer_experience_do_not_supply_candidate_requirements(body):
    data = opportunity_details(
        observed(
            f"<h2>Qualifications</h2><p>{body}</p><h2>About us</h2><p>Previous experience in trading.</p>"
        )
    )
    assert data["experience"]["status"] == "not_published"


@pytest.mark.parametrize(
    "text,day",
    [
        ("Start date: 14 September 2027.", "2027-09-14"),
        ("Prise de poste : 1 février 2027.", "2027-02-01"),
        ("Start: September 14, 2027.", "2027-09-14"),
    ],
)
def test_explicit_start_day_in_description_is_preserved(text, day):
    job = observed(text)
    facts = start_facts(job)
    assert facts["precision"] == "day"
    assert facts["windows"] == [{"from": day, "to": day}]


@pytest.mark.parametrize(
    "text",
    [
        "Graduating on 14 September 2027.",
        "Applications close 14 September 2027.",
        "Start between 14 and 16 September 2027.",
        "Start: 1 September 2027 or 15 September 2027.",
    ],
)
def test_graduation_application_and_alternative_days_never_invent_one_start_day(text):
    assert start_facts(observed(text))["precision"] != "day"


def test_invalid_named_calendar_day_is_a_conflict():
    assert start_facts(observed("Start date: 31 April 2027."))["precision"] == "conflict"


@pytest.mark.parametrize(
    "text",
    [
        "Date limite de candidature : 16 novembre 2027.",
        "Clôture des candidatures : 16 November 2027.",
        "Apply by November 16, 2027.",
    ],
)
def test_explicit_application_dates_in_french_and_english_keep_day_precision(text):
    data = resolve_deadline(observed(text))
    assert data.precision == "date" and data.day.isoformat() == "2027-11-16"
    assert data.instant is None


def test_missing_year_or_ambiguous_start_is_not_completed_from_current_time():
    job = observed("Applications close 16 November. Start date: 01/02/2027.")
    data = opportunity_details(job)
    assert data["deadline"]["status"] == "unrecognized"
    assert "16 November" in data["deadline"]["evidence"][0]
    assert data["start"]["status"] == "unrecognized"


def test_asap_and_rolling_are_reported_without_invented_dates():
    data = opportunity_details(
        observed("Start date: as soon as possible. Applications reviewed on a rolling basis.")
    )
    assert data["start"]["status"] == data["deadline"]["status"] == "qualitative"
    assert "Dès que possible" in data["start"]["label"]
    assert "fil de l’eau" in data["deadline"]["label"]


@pytest.mark.parametrize(
    "location,code",
    [
        ("Beijing, China", "CN"),
        ("Sao Paulo, Brazil", "BR"),
        ("Taipei", "TW"),
        ("Seoul, Korea, Republic of", "KR"),
        ("Canary Wharf, 1 Churchill Place", "GB"),
        ("Lisbonne, PT", "PT"),
        ("Kuala Lumpur Menara IMC", "MY"),
        ("Aarhus, Denmark", "DK"),
    ],
)
def test_published_cities_and_countries_are_recognized_without_identity_changes(location, code):
    job = observed(location=location)
    before = job.model_dump()
    assert country_facts(job)["countries"][0]["code"] == code
    assert job.model_dump() == before


def test_ubs_named_fields_are_kept_without_using_last_updated_as_start_or_deadline():
    data = detail()
    data["Jobdetails"]["JobDetailQuestions"].extend(
        [
            {"VerityZone": "formtext22", "AnswerValue": "Full Time ", "QuestionName": "Job Type"},
            {
                "VerityZone": "start",
                "AnswerValue": "14 September 2027",
                "QuestionName": "Start Date",
            },
            {
                "VerityZone": "closing",
                "AnswerValue": "16 November 2026",
                "QuestionName": "Application deadline",
            },
        ]
    )
    raw = parse_detail(data, {"reqid": "123"}, ubs_config(), "ubs")
    facts = opportunity_details(normalize(raw))
    assert facts["start"]["label"] == "14/09/2027"
    assert facts["deadline"]["label"].startswith("16/11/2026")
    assert "16-Sep-2026" not in raw.description


def test_cached_details_keep_real_source_verification_time(config, repo, raw, tmp_path):
    config.settings.database_url = "sqlite:///" + str(tmp_path / "jobs.db")
    first = normalize(raw)
    with repo.transaction():
        job, _ = repo.upsert(first)
    a = build_dashboard_data(config, history_dir=tmp_path / "history")
    next_job = normalize(raw)
    next_job.last_seen = first.last_seen + timedelta(seconds=1)
    with repo.transaction():
        updated, _ = repo.upsert(next_job)
    b = build_dashboard_data(
        config, history_dir=tmp_path / "history", now=datetime.now(UTC) + timedelta(seconds=2)
    )
    assert a["jobs"][0]["opportunity_details"]["verified_at"] == first.last_seen.isoformat()
    assert b["jobs"][0]["opportunity_details"]["verified_at"] == updated.last_seen.isoformat()
    assert a["jobs"][0]["id"] == b["jobs"][0]["id"]
    assert sum(b["opportunity_quality"]["fields"]["location"].values()) == 1
