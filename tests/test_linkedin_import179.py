"""Pasted offers remain distinct from verified feeds, with tracking and replay safety."""

import asyncio
from datetime import datetime

import pytest

from tests.test_telegram_control import FakeNotifier, update
from trading_radar import telegram_control as control
from trading_radar.dashboard_data import read_jobs
from trading_radar.linkedin_import import (
    SOURCE,
    ImportRejected,
    import_offer,
    parse_offer,
    posting_url,
)
from trading_radar.normalizer import normalize
from trading_radar.runtime_status import runtime_report
from trading_radar.scoring import score_job
from trading_radar.telegram_cards import format_alert
from trading_radar.wishlist import read_wishlist, set_wishlist

BODY = (
    "Entreprise: Bank of America\n"
    "Poste: Global Markets Sales and Trading 2027 Off-Cycle Analyst\n"
    "Lieu: Milan, Italie\n"
    "Lien: https://fr.linkedin.com/jobs/view/global-markets-off-cycle-1234567890/?trackingId=x\n"
    "Description: Off-cycle internship in Sales and Trading.\n"
    "Start date: January 2027. Six-month internship.\n"
    "Requirements: students with Python skills."
)


@pytest.fixture
def local(config, repo, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    config.settings.include_internships = True
    return config


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/jobs/view/1234567890/",
        "https://linkedin.com/jobs/view/1234567890?trk=test",
        "https://uk.linkedin.com/jobs/view/global-markets-1234567890/?trk=test",
    ],
)
def test_public_posting_links_keep_exact_id_and_strip_tracking(url):
    assert posting_url(url) == ("https://www.linkedin.com/jobs/view/1234567890", "1234567890")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com.evil.test/jobs/view/1234567890",
        "https://user@www.linkedin.com/jobs/view/1234567890",
        "https://www.linkedin.com:443/jobs/view/1234567890",
        "http://www.linkedin.com/jobs/view/1234567890",
        "https://www.linkedin.com/jobs/search/?currentJobId=1234567890",
        "https://www.linkedin.com/jobs/view/other-1234567890/#anything",
        "https://www.linkedin.com/jobs/view/0123456789",
        "https://www.linkedin.com/jobs/view/1234567890%2felsewhere",
        "https://www.linkedin.com/jobs/view/1234567890?x=\nsecret",
        "https://www.linkedin.com/jobs/view/1234567890?x=\u202e",
        "https://www.linkedin.com\\@evil.test/jobs/view/1234567890",
    ],
)
def test_unsafe_or_non_posting_links_are_rejected(url):
    with pytest.raises(ImportRejected):
        posting_url(url)


def test_paste_keeps_all_description_and_never_invents_employer_fields():
    raw = parse_offer(BODY)
    assert raw.source == SOURCE and raw.source_type == "aggregator"
    assert raw.location == "Milan, Italie"
    assert raw.date_posted is raw.application_deadline is raw.expected_start_date is None
    assert raw.minimum_experience_years is None
    assert "Requirements: students with Python skills." in raw.description
    assert "Start date: January 2027." in raw.description


@pytest.mark.parametrize(
    "body",
    [
        "",
        "x" * 12001,
        BODY.replace("Entreprise: Bank of America", "Entreprise:"),
        BODY.replace("Poste:", "Unrecognized:"),
        BODY.replace("Lieu: Milan, Italie\n", ""),
        BODY.replace("Poste:", "Entreprise: Other\nPoste:"),
        BODY + "\x00",
    ],
)
def test_incomplete_or_ambiguous_paste_is_rejected_before_storage(body):
    with pytest.raises(ImportRejected):
        parse_offer(body)


def test_import_is_idempotent_and_preserves_tracking_wishlist_and_alerts(local, repo):
    imported, created = import_offer(local, BODY)
    assert created
    repo.update_application(imported.id, {"status": "Applied", "notes": "My private note"})
    set_wishlist(local, imported.id, True, actor="telegram")
    tables = [
        "applications",
        "application_history",
        "alerts",
        "alert_history",
        "companies",
        "scan_runs",
    ]
    before = {t: [tuple(r) for r in repo.db.execute(f"SELECT * FROM {t}")] for t in tables}
    again, created = import_offer(local, BODY.replace("January 2027", "February 2027"))
    assert not created and again.model_dump() == imported.model_dump()
    assert read_wishlist(local, imported.id)["saved"]
    assert {t: [tuple(r) for r in repo.db.execute(f"SELECT * FROM {t}")] for t in tables} == before
    assert repo.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1


def test_paste_cannot_refresh_or_reopen_matching_official_offer(local, repo):
    official = score_job(
        normalize(
            parse_offer(BODY).model_copy(
                update={
                    "source": "test",
                    "source_type": "official",
                    "external_id": "official-1",
                    "apply_url": "https://bank.example/jobs/official-1",
                }
            )
        ),
        local.keywords,
    )
    with repo.transaction():
        repo.upsert(official)
        official.is_active = False
        repo._write(official)
    before = official.model_dump()
    returned, created = import_offer(local, BODY)
    assert not created and returned.model_dump() == before
    assert repo.get(official.id).model_dump() == before
    assert (
        repo.db.execute("SELECT COUNT(*) FROM job_sources WHERE source=?", (SOURCE,)).fetchone()[0]
        == 0
    )


def test_different_company_for_existing_linkedin_id_is_rejected(local, repo):
    imported, _ = import_offer(local, BODY)
    with pytest.raises(ImportRejected, match="autre employeur"):
        import_offer(local, BODY.replace("Bank of America", "Other Bank"))
    assert repo.get(imported.id).company == "Bank of America"
    assert repo.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1


def test_manual_import_is_visible_but_never_inflates_monitored_source_count(local, repo):
    imported, _ = import_offer(local, BODY)
    shown = read_jobs(local)[0]
    assert shown["manual_import"] and shown["opportunity_details"]["verified_at"] is None
    assert shown["description_text"]
    report = runtime_report(local)
    assert report["source_counts"]["enabled"] == report["source_counts"]["employers"] == 1
    assert SOURCE not in {s["source"] for s in report["source_inventory"]}
    assert "import manuel" in format_alert(imported, "catalogue")
    assert "ouverture à confirmer" in format_alert(imported, "manual_import")


class ImportNotifier(FakeNotifier):
    token = "123:test"


def test_telegram_import_has_buttons_and_consumed_cursor_prevents_replay(local, repo, tmp_path):
    notifier = ImportNotifier()
    store = control.ControlStore(tmp_path / "cursor.json", "owner")
    now = int(datetime.now().timestamp())
    item = update(text="/linkedin@RadarBot\n" + BODY, now=now)
    asyncio.run(control.process_updates([item], local, notifier, store, "RadarBot", now))
    assert store.state.offset == 2 and len(notifier.sent) == 2
    buttons = notifier.options[-1]["reply_markup"]["inline_keyboard"]
    assert any("souhaits" in b["text"] for row in buttons for b in row)
    count = repo.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    reloaded = control.ControlStore(store.path, "owner")
    asyncio.run(control.process_updates([item], local, notifier, reloaded, "RadarBot", now))
    assert len(notifier.sent) == 2 and count == 1


@pytest.mark.parametrize("mutation", ["other_chat", "other_bot", "old", "non_owner"])
def test_unauthorized_import_never_creates_jobs(local, repo, tmp_path, mutation):
    item = update(text="/linkedin\n" + BODY)
    if mutation == "other_chat":
        item["message"]["chat"]["id"] = 999
    elif mutation == "other_bot":
        item["message"]["text"] = "/linkedin@OtherBot\n" + BODY
    elif mutation == "old":
        item["message"]["date"] = 9000
    else:
        item["message"]["from"]["id"] = 999
    notifier = ImportNotifier()
    store = control.ControlStore(tmp_path / "cursor.json", "owner")
    asyncio.run(control.process_updates([item], local, notifier, store, "RadarBot", 10000))
    assert not notifier.sent
    assert repo.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
