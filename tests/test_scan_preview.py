import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from trading_radar import scan_preview
from trading_radar.config import Company
from trading_radar.models import Collection
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


class MemoryCollector:
    def __init__(self, jobs, *, complete=True, error=False):
        self.jobs = jobs
        self.complete = complete
        self.error = error
        self.calls = 0

    async def collect(self):
        self.calls += 1
        if self.error:
            raise ValueError("private-password-do-not-expose")
        return Collection(jobs=self.jobs, complete=self.complete)


def rows(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def configure(config, repo):
    path = Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    config.settings.database_url = f"sqlite:///{path}"
    config.settings.deadline_reminders_enabled = True
    return path


def run(config, collector, **kwargs):
    return asyncio.run(scan_preview.preview_scan(config, collectors={"test": collector}, **kwargs))


def test_existing_wal_database_all_tables_and_config_preserved(config, repo, job, raw):
    configure(config, repo)
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
        repo.mark_success("test", 1, 0.1)
    repo.update_application(job.id, {"status": "Applied", "notes": "Private application notes"})
    before = rows(repo)
    settings = config.model_dump()
    changed = raw.model_copy(update={"title": "Graduate FX Trading Analyst 2027"})
    result = run(config, MemoryCollector([changed]))
    assert result["status"] == "ok"
    assert result["metrics"]["updated"] == 1
    assert result["metrics"]["alerts"] == 0
    assert result["changes"][0]["event"] == "updated"
    assert result["changes"][0]["id"] == job.id
    assert result["changes"][0]["before_score"] == job.score_breakdown.total
    assert result["changes"][0]["before_active"] is True
    assert rows(repo) == before
    assert config.model_dump() == settings
    assert "Private application notes" not in json.dumps(result)


def test_missing_database_preview_does_not_create_source_parent(config, raw, tmp_path):
    directory = tmp_path / "absent" / "source"
    config.settings.database_url = f"sqlite:///{directory / 'jobs.db'}"
    result = run(config, MemoryCollector([raw]))
    assert result["status"] == "ok"
    assert result["read_only"] and result["ephemeral_new_ids"]
    assert result["metrics"]["new"] == 1
    change = result["changes"][0]
    assert change["event"] == "new"
    assert change["before_score"] is None and change["before_active"] is None
    assert change["after_active"] is True
    assert change["changed_fields"] == []
    assert not directory.parent.exists()


@pytest.mark.parametrize(
    "url", ["postgresql://secret@host/db", "sqlite:///:memory:", "sqlite:///", "invalid"]
)
def test_invalid_database_url_never_collects(config, url):
    config.settings.database_url = url
    collector = MemoryCollector([])
    result = run(config, collector)
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_config"
    assert collector.calls == 0
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("kind", ["corrupt", "directory", "schema"])
def test_invalid_snapshot_fails_closed(config, tmp_path, repo, kind):
    path = tmp_path / "invalid.db"
    if kind == "corrupt":
        path.write_text("private-password-do-not-expose")
    elif kind == "directory":
        path.mkdir()
    else:
        path = configure(config, repo)
        repo.db.execute("CREATE TABLE unexpected(value)")
        repo.db.commit()
    config.settings.database_url = f"sqlite:///{path}"
    collector = MemoryCollector([])
    result = run(config, collector)
    assert result["status"] == "error"
    assert result["error"]["code"] == "snapshot_failed"
    assert result["metrics"] is None and result["changes"] == []
    assert collector.calls == 0
    assert "private-password" not in json.dumps(result)


def test_failed_source_does_not_change_existing_state(config, repo, job):
    configure(config, repo)
    with repo.transaction():
        repo.upsert(job)
        repo.mark_success("test", 1, 0.1)
    before = rows(repo)
    result = run(config, MemoryCollector([], error=True))
    assert result["status"] == "incomplete"
    assert result["metrics"]["failed"] == {"test": "ValueError"}
    assert result["changes"] == []
    assert rows(repo) == before
    assert "private-password" not in json.dumps(result)


def test_failure_isolated_from_successful_source(config, repo, raw):
    configure(config, repo)
    config.companies["broken"] = Company(name="Broken", ats="fixture", enabled=True)
    before = rows(repo)
    result = asyncio.run(
        scan_preview.preview_scan(
            config,
            collectors={"test": MemoryCollector([raw]), "broken": MemoryCollector([], error=True)},
        )
    )
    assert result["status"] == "incomplete"
    assert result["metrics"]["successful"] == 1
    assert result["metrics"]["new"] == 1
    assert len(result["changes"]) == 1
    assert rows(repo) == before


@pytest.mark.parametrize("complete", [False, True])
def test_only_complete_snapshot_can_preview_closure(config, repo, raw, job, complete):
    configure(config, repo)
    keeper = raw.model_copy(
        update={"external_id": "keeper", "apply_url": "https://example.com/keeper"}
    )
    with repo.transaction():
        repo.upsert(job)
        repo.upsert(score_job(normalize(keeper), config.keywords))
        repo.mark_success("test", 2, 0.1)
        repo.db.execute("UPDATE job_sources SET missing_count=1 WHERE job_id=?", (job.id,))
    before = rows(repo)
    result = run(config, MemoryCollector([keeper], complete=complete))
    assert result["status"] == "ok"
    assert result["metrics"]["closed"] == int(complete)
    closed = [change for change in result["changes"] if change["event"] == "closed"]
    assert len(closed) == int(complete)
    if complete:
        assert closed[0]["id"] == job.id
        assert closed[0]["before_active"] is True and closed[0]["after_active"] is False
        assert closed[0]["changed_fields"] == ["is_active"]
    assert rows(repo) == before


def test_unexpected_empty_snapshot_does_not_preview_closure(config, repo, job):
    configure(config, repo)
    with repo.transaction():
        repo.upsert(job)
        repo.mark_success("test", 1, 0.1)
    before = rows(repo)
    result = run(config, MemoryCollector([]))
    assert result["status"] == "incomplete"
    assert result["changes"] == []
    assert rows(repo) == before


def test_due_only_uses_copied_source_state(config, repo, raw):
    configure(config, repo)
    with repo.transaction():
        repo.mark_success("test", 0, 0.1)
    before = rows(repo)
    collector = MemoryCollector([raw])
    result = run(config, collector, due_only=True)
    assert result["status"] == "ok"
    assert result["metrics"]["sources"] == 0
    assert collector.calls == 0
    assert rows(repo) == before


@pytest.mark.parametrize("when", ["before", "after", "events"])
def test_limits_discard_entire_report(config, repo, raw, job, monkeypatch, when):
    configure(config, repo)
    if when == "before":
        with repo.transaction():
            repo.upsert(job)
    monkeypatch.setattr(scan_preview, "MAX_CHANGES" if when == "events" else "MAX_JOBS", 0)
    before = rows(repo)
    collector = MemoryCollector([raw])
    result = run(config, collector)
    assert result["status"] == "error"
    assert result["error"]["code"] == "limit_exceeded"
    assert result["metrics"] is None and result["changes"] == []
    assert collector.calls == (0 if when == "before" else 1)
    assert rows(repo) == before


@pytest.mark.parametrize("error", [False, True])
def test_temporary_database_and_locks_cleaned(config, repo, raw, monkeypatch, error):
    configure(config, repo)
    paths = []
    original = scan_preview.scan

    async def observe(cloned, target, **kwargs):
        paths.append(Path(cloned.settings.database_url.removeprefix("sqlite:///")))
        assert target is not repo
        assert not cloned.settings.alerts_enabled
        assert not cloned.settings.deadline_reminders_enabled
        if error:
            raise RuntimeError("private-password-do-not-expose")
        return await original(cloned, target, **kwargs)

    monkeypatch.setattr(scan_preview, "scan", observe)
    result = run(config, MemoryCollector([raw]))
    assert result["status"] == ("error" if error else "ok")
    assert paths and all(not path.parent.exists() for path in paths)
    assert "private-password" not in json.dumps(result)


def test_filters_forwarded_to_normal_scanner(config, repo, raw, monkeypatch):
    configure(config, repo)
    config.companies["second"] = Company(name="Other", ats="fixture", enabled=True)
    observed = []

    def build(key, company, http):
        observed.append(key)
        return MemoryCollector([raw])

    monkeypatch.setattr("trading_radar.scanner.build_collector", build)
    result = asyncio.run(scan_preview.preview_scan(config, company="Demo Bank", source="test"))
    assert result["status"] == "ok"
    assert observed == ["test"]


@pytest.mark.parametrize("fault", ["payload", "score", "active", "identifier", "oversize"])
def test_incoherent_stored_job_prevents_collection(config, repo, job, monkeypatch, fault):
    configure(config, repo)
    with repo.transaction():
        repo.upsert(job)
        if fault == "payload":
            repo.db.execute("UPDATE jobs SET payload='invalid json'")
        elif fault == "score":
            repo.db.execute("UPDATE jobs SET score=-1")
        elif fault == "active":
            repo.db.execute("UPDATE jobs SET is_active=2")
        elif fault == "identifier":
            value = job.model_copy(update={"id": "different-id"}).model_dump_json()
            repo.db.execute("UPDATE jobs SET payload=?", (value,))
        else:
            monkeypatch.setattr(scan_preview, "MAX_PAYLOAD", 10)
    before = rows(repo)
    collector = MemoryCollector([])
    result = run(config, collector)
    assert result["status"] == "error"
    assert result["error"]["code"] == ("limit_exceeded" if fault == "oversize" else "invalid_data")
    assert collector.calls == 0
    assert rows(repo) == before


def test_closed_job_reopening_is_only_simulated(config, repo, raw, job):
    configure(config, repo)
    job.is_active = False
    with repo.transaction():
        repo.upsert(job)
    before = rows(repo)
    result = run(config, MemoryCollector([raw]))
    assert result["status"] == "ok"
    change = result["changes"][0]
    assert change["event"] == "reopened"
    assert change["before_active"] is False and change["after_active"] is True
    assert change["changed_fields"] == ["is_active"]
    assert rows(repo) == before


def test_snapshot_restore_failure_cleans_files(config, repo, monkeypatch):
    configure(config, repo)
    paths = []

    def fail_restore(archive, target, *, protected):
        paths.append(archive.parent)
        target.write_text("partial disposable output")
        raise ValueError("private-password-do-not-expose")

    monkeypatch.setattr(scan_preview, "restore_backup", fail_restore)
    collector = MemoryCollector([])
    result = run(config, collector)
    assert result["status"] == "error"
    assert result["error"]["code"] == "snapshot_failed"
    assert paths and all(not path.exists() for path in paths)
    assert collector.calls == 0
    assert "private-password" not in json.dumps(result)


def test_cancellation_cleans_temporary_files(config, repo, monkeypatch):
    configure(config, repo)
    paths = []

    async def cancel(cloned, target, **kwargs):
        paths.append(Path(cloned.settings.database_url.removeprefix("sqlite:///")))
        raise asyncio.CancelledError

    monkeypatch.setattr(scan_preview, "scan", cancel)
    with pytest.raises(asyncio.CancelledError):
        run(config, MemoryCollector([]))
    assert paths and all(not path.parent.exists() for path in paths)


@pytest.mark.parametrize("field", ["description", "employment_type"])
def test_preview_names_description_or_metadata_change_without_values(config, repo, raw, job, field):
    configure(config, repo)
    with repo.transaction():
        repo.upsert(job)
    repo.update_application(job.id, {"notes": "PRIVATE APPLICATION NOTES"})
    before = rows(repo)
    value = raw.description + " NEW DESCRIPTION SENTENCE" if field == "description" else "Full time"
    changed = raw.model_copy(update={field: value})
    result = run(config, MemoryCollector([changed]))
    assert result["status"] == "ok"
    change = result["changes"][0]
    assert change["event"] == "updated"
    assert change["before_score"] == change["after_score"]
    assert change["changed_fields"] == [
        "description_text" if field == "description" else "employment_type"
    ]
    encoded = json.dumps(result)
    assert "NEW DESCRIPTION SENTENCE" not in encoded
    assert "PRIVATE APPLICATION NOTES" not in encoded
    assert "Full time" not in encoded
    assert rows(repo) == before


def test_preview_compares_each_event_to_immediately_previous_version(config, repo, raw, job):
    configure(config, repo)
    with repo.transaction():
        repo.upsert(job)
    first = raw.model_copy(update={"description": raw.description + " Added description sentence."})
    second = first.model_copy(update={"employment_type": "Full time"})
    third = raw.model_copy(update={"employment_type": "Full time"})
    result = run(config, MemoryCollector([first, second, third]))
    assert result["status"] == "ok"
    assert [change["event"] for change in result["changes"]] == ["updated"] * 3
    assert [change["changed_fields"] for change in result["changes"]] == [
        ["description_text"],
        ["employment_type"],
        ["description_text"],
    ]
    assert "Added description sentence" not in json.dumps(result)


def test_business_metadata_and_score_reasons_reported_without_technical_noise(repo, job):
    # A version can change several business fields while retaining its total score.
    # Exercise that report boundary without relying on any particular scoring rule.
    now = datetime(2026, 9, 17, tzinfo=UTC)
    updated = job.model_copy(
        deep=True,
        update={
            "date_posted": now,
            "expected_start_date": "2027-01-01",
            "application_deadline": now + timedelta(days=14),
            "title": "Updated title",
            "location_normalized": "Paris, France",
            "city": "Paris",
            "country": "France",
            "seniority_hint": "junior",
            "minimum_experience_years": 1,
            "role_hint": "trading_technology",
            "first_seen": now,
            "last_seen": now,
            "date_updated": now,
            "is_new": False,
            "external_id": "new-technical-id",
            "fingerprint": "new-technical-fingerprint",
            "raw_payload": {"private": "RAW PAYLOAD MUST NOT LEAK"},
            "description": "<p>RAW DESCRIPTION MUST NOT LEAK</p>",
        },
    )
    updated.score_breakdown.reasons.append("Private detail from reasoning must not leak")
    with repo.transaction():
        repo.upsert(job)
        start = repo.db.execute("SELECT MAX(id) FROM job_versions").fetchone()[0]
        repo.db.execute(
            "INSERT INTO job_versions(job_id,created_at,event,payload) VALUES(?,?,?,?)",
            (job.id, now.isoformat(), "updated", updated.model_dump_json()),
        )
    result = scan_preview._changes(repo, start, {job.id: job})
    assert result[0]["changed_fields"] == [
        "application_deadline",
        "city",
        "country",
        "date_posted",
        "expected_start_date",
        "location_normalized",
        "minimum_experience_years",
        "role_hint",
        "score_breakdown",
        "seniority_hint",
        "title",
    ]
    assert result[0]["before_score"] == result[0]["after_score"]
    assert "MUST NOT LEAK" not in json.dumps(result)
    assert "Private detail" not in json.dumps(result)
