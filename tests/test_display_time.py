import csv
from datetime import UTC, datetime

import pytest

from trading_radar.display_time import export_paris, format_paris
from trading_radar.export import export_csv
from trading_radar.notifications import format_message
from trading_radar.telegram_cards import format_alert


@pytest.mark.parametrize(
    "instant,expected",
    [
        ("2026-09-26T19:11:55Z", "26/09/2026 · 21:11"),
        ("2026-12-26T19:11:55Z", "26/12/2026 · 20:11"),
        ("2026-09-26T23:30:00Z", "27/09/2026 · 01:30"),
        ("2026-03-29T00:30:00Z", "29/03/2026 · 01:30"),
        ("2026-03-29T01:30:00Z", "29/03/2026 · 03:30"),
        ("2026-10-25T00:30:00Z", "25/10/2026 · 02:30"),
        ("2026-10-25T01:30:00Z", "25/10/2026 · 02:30"),
    ],
)
def test_paris_time_handles_midnight_and_both_dst_transitions(instant, expected):
    assert format_paris(instant) == expected
    assert format_paris(datetime.fromisoformat(instant)) == expected


@pytest.mark.parametrize(
    "value", [None, "broken", "2026-09-26", "2026-09-26T12:00:00", "9999-12-31T23:00:00-02:00"]
)
def test_no_timezone_or_invalid_instant_does_not_invent_paris_time(value):
    assert format_paris(value) == "Non précisée"


def test_job_alerts_and_csv_use_same_paris_instant_without_changing_storage(repo, job, tmp_path):
    job.first_seen = job.last_seen = job.date_posted = job.application_deadline = datetime(
        2026, 9, 26, 23, 30, tzinfo=UTC
    )
    repo.upsert(job)
    before = list(repo.db.iterdump())
    expected = "27/09/2026 · 01:30"
    assert expected in format_alert(job, "new")
    assert expected in format_message(job, "new")
    destination = tmp_path / "jobs.csv"
    export_csv(repo, destination)
    with destination.open(encoding="utf-8-sig", newline="") as stream:
        row = next(csv.DictReader(stream))
    for key in ("date_posted", "first_seen", "deadline"):
        assert row[key] == "2026-09-27T01:30:00"
    assert list(repo.db.iterdump()) == before
    assert export_paris(None) == ""
