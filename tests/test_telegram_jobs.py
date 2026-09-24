import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from tests.test_dashboard_data import fingerprints
from tests.test_telegram_control import FakeNotifier, update
from trading_radar import telegram_control as control
from trading_radar import telegram_jobs as lists
from trading_radar.models import Score

NOW = datetime(2026, 9, 24, 12, tzinfo=UTC)


@pytest.fixture
def local(config, repo, tmp_path, job):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    job.first_seen = NOW - timedelta(hours=2)
    job.last_seen = NOW - timedelta(minutes=10)
    job.date_updated = job.last_seen
    job.score_breakdown = Score(trading=30, junior=20, start=15, front_office=15)
    job.description_text = "Trading role"
    job.application_deadline = None
    with repo.transaction():
        repo.upsert(job)
        repo.db.execute(
            "INSERT INTO companies(source,last_success,bootstrapped) VALUES('test',?,1)",
            ((NOW - timedelta(minutes=10)).isoformat(),),
        )
    return config


def save(repo, job, **changes):
    for field, value in changes.items():
        setattr(job, field, value)
    desired = job.model_copy(deep=True)
    with repo.transaction():
        repo.upsert(job)
        # Collection upserts intentionally preserve discovery and reopen jobs.
        # Seed historical/closed states explicitly for these read-only scenarios.
        repo.db.execute(
            "UPDATE jobs SET first_seen=?,is_active=?,payload=? WHERE id=?",
            (
                desired.first_seen.isoformat(),
                int(desired.is_active),
                desired.model_dump_json(),
                job.id,
            ),
        )


@pytest.mark.parametrize("mode", ["top", "new"])
def test_lists_include_complete_link_and_never_change_database(local, repo, job, mode):
    before = fingerprints(repo)
    text = lists.jobs_message(local, mode, NOW)
    assert "1 affichée(s) sur 1" in text
    assert job.apply_url in text and job.title in text
    assert "80/100" in text and "24/09 11:50 UTC" in text
    assert "Découverte par le radar ≠ date de publication" in text
    assert fingerprints(repo) == before


@pytest.mark.parametrize(
    "status",
    ["Applied", "Online Assessment", "Interview", "Offer", "Rejected", "Withdrawn", "Closed"],
)
def test_already_handled_applications_are_excluded(local, repo, job, status):
    repo.update_application(job.id, {"status": status})
    before = fingerprints(repo)
    assert "0 correspondance(s)" in lists.jobs_message(local, "top", NOW)
    assert fingerprints(repo) == before


@pytest.mark.parametrize("status", ["New", "Reviewing", "To Apply"])
def test_pending_review_statuses_are_included(local, repo, job, status):
    repo.update_application(job.id, {"status": status})
    assert "sur 1 correspondance(s)" in lists.jobs_message(local, "top", NOW)


@pytest.mark.parametrize(
    "changes",
    [
        {"is_active": False},
        {"is_expired": True},
        {"score_breakdown": Score(trading=30)},
        {"last_seen": NOW - timedelta(hours=25), "first_seen": NOW - timedelta(days=2)},
        {"last_seen": NOW + timedelta(seconds=1)},
        {"first_seen": NOW + timedelta(seconds=1)},
        {"application_deadline": NOW - timedelta(seconds=1)},
        {"application_deadline": NOW},
        {"description_text": "Application deadline: 2026-09-23"},
        {"description_text": "Application deadline: 2026-09-25. Application deadline: 2026-09-26"},
    ],
)
def test_ineligible_jobs_are_excluded(local, repo, job, changes):
    save(repo, job, **changes)
    assert "0 correspondance(s)" in lists.jobs_message(local, "top", NOW)


@pytest.mark.parametrize("source_state", ["failed", "stale", "disabled", "future"])
def test_unreliable_or_disabled_sources_are_excluded(local, repo, source_state):
    if source_state == "disabled":
        local.companies["test"].enabled = False
    else:
        with repo.transaction():
            if source_state == "failed":
                repo.db.execute("UPDATE companies SET last_failure=?", (NOW.isoformat(),))
            else:
                at = (
                    NOW + timedelta(seconds=1)
                    if source_state == "future"
                    else NOW - timedelta(hours=25)
                )
                repo.db.execute("UPDATE companies SET last_success=?", (at.isoformat(),))
    text = lists.jobs_message(local, "top", NOW)
    assert "0 correspondance(s)" in text
    if source_state != "disabled":
        assert "Sources en échec ou anciennes écartées" in text


def test_new_uses_discovery_not_republication_or_recent_refresh(local, repo, job):
    save(repo, job, first_seen=NOW - timedelta(hours=24, seconds=1), date_posted=NOW)
    assert "sur 0 correspondance(s)" in lists.jobs_message(local, "new", NOW)
    assert "sur 1 correspondance(s)" in lists.jobs_message(local, "top", NOW)
    save(repo, job, first_seen=NOW - timedelta(hours=24))
    assert "sur 1 correspondance(s)" in lists.jobs_message(local, "new", NOW)


def test_top_and_new_have_distinct_stable_order_and_at_most_five_results(local, repo, job):
    for index in range(1, 7):
        other = job.model_copy(deep=True)
        other.id = other.fingerprint = f"other-{index}"
        other.external_id = None
        other.title = other.title_normalized = f"Role {index}"
        other.apply_url = f"https://example.com/job/{index}"
        other.score_breakdown.start = index + 5
        other.first_seen = NOW - timedelta(hours=1, minutes=index)
        save(repo, other)
    top = lists.jobs_message(local, "top", NOW)
    new = lists.jobs_message(local, "new", NOW)
    assert "5 affichée(s) sur 7" in top and "5 affichée(s) sur 7" in new
    assert top.index(job.title) < top.index("Role 6") < top.index("Role 5")
    assert new.index("Role 1") < new.index("Role 2") and job.title not in new
    assert "Role 1" not in top
    assert top == lists.jobs_message(local, "top", NOW)


def test_utf16_limit_never_cuts_a_link_or_leaks_private_notes(local, repo, job):
    for index in range(7):
        other = job.model_copy(deep=True)
        other.id = other.fingerprint = f"large-{index}"
        other.external_id = None
        other.company = other.company_normalized = "🚀" * 300
        other.title = other.title_normalized = "🚀" * 1000
        other.location = other.location_normalized = "🚀" * 1000
        other.apply_url = "https://example.com/" + "a" * 675 + str(index)
        save(repo, other)
        repo.update_application(other.id, {"notes": "PRIVATE SECRET"})
    text = lists.jobs_message(local, "top", NOW)
    assert lists.units(text) <= 4096
    assert "PRIVATE SECRET" not in text and "sur 8 correspondance(s)" in text
    assert "https://example.com/" + "a" * 675 in text


def test_long_and_unsafe_links_are_not_truncated_or_rendered(local, repo, job):
    save(repo, job, apply_url="https://example.com/" + "x" * 1000, source_url="javascript:bad")
    text = lists.jobs_message(local, "top", NOW)
    assert "Lien indisponible ici" in text and "https://example.com/" not in text
    save(repo, job, apply_url="javascript:bad", source_url="https://employer.example/job")
    text = lists.jobs_message(local, "top", NOW)
    assert "javascript:" not in text and "https://employer.example/job" in text


@pytest.mark.parametrize("minimum", [0, None, 3])
def test_experience_is_displayed_without_inventing_eligibility(local, repo, job, minimum):
    save(repo, job, minimum_experience_years=minimum)
    text = lists.jobs_message(local, "top", NOW)
    expected = "minimum inconnu" if minimum is None else f"minimum reconnu {minimum} an(s)"
    assert expected in text


@pytest.mark.parametrize(
    "description,deadline,expected",
    [
        ("Trading", NOW + timedelta(hours=1), "24/09/2026 13:00 UTC"),
        ("Application deadline: 2026-09-24", None, "2026-09-24 (heure/fuseau inconnus)"),
    ],
)
def test_deadline_precision_is_preserved(local, repo, job, description, deadline, expected):
    save(repo, job, description_text=description, application_deadline=deadline)
    assert expected in lists.jobs_message(local, "top", NOW)


def test_missing_database_does_not_create_one(local, tmp_path):
    missing = tmp_path / "missing.db"
    local.settings.database_url = f"sqlite:///{missing}"
    assert "Offres indisponibles" in lists.jobs_message(local, "top", NOW)
    assert not missing.exists()


def test_corrupt_record_does_not_leak_data_or_return_partial_list(local, repo):
    with repo.transaction():
        repo.db.execute("UPDATE jobs SET payload='private corrupt record'")
    text = lists.jobs_message(local, "top", NOW)
    assert "Offres indisponibles" in text and "private" not in text


def test_health_changes_between_observations_fail_closed(local, monkeypatch):
    monkeypatch.setattr(
        lists, "check_health", lambda *a, **k: {"database": {"status": "unreadable"}}
    )
    assert "fraîcheur des sources ne peut pas" in lists.jobs_message(local, "top", NOW)


@pytest.mark.parametrize("command", ["top", "new"])
def test_private_command_dispatch_and_unauthorized_read_protection(
    local, tmp_path, monkeypatch, command
):
    calls = []

    def reply(config, mode):
        calls.append(mode)
        return "synthetic list"

    monkeypatch.setattr(control, "jobs_message", reply)
    store = control.ControlStore(tmp_path / "commands.json", "test")
    notifier = FakeNotifier()
    foreign = update(1, f"/{command}")
    foreign["message"]["from"]["id"] = 999
    valid = update(2, f"/{command}@RadarBot")
    asyncio.run(
        control.process_updates([foreign, valid], local, notifier, store, "RadarBot", 10000)
    )
    assert calls == [command] and notifier.sent == ["synthetic list"]
    asyncio.run(control.process_updates([valid], local, notifier, store, "RadarBot", 10000))
    assert calls == [command]


def test_bad_time_and_mode_rejected(local):
    with pytest.raises(ValueError, match="timezone"):
        lists.jobs_message(local, "top", datetime(2026, 9, 24))
    with pytest.raises(ValueError, match="Unknown"):
        lists.jobs_message(local, "invalid", NOW)
