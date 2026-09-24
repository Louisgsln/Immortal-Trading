"""Quarantine integration: persistence, recovery, previews and notification safety."""

import asyncio
import json

import pytest

from trading_radar.audit import audit_sources
from trading_radar.collection_diagnostics import quarantined_sources, source_conflicts
from trading_radar.config import Company
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.health import check_health
from trading_radar.models import Collection, CollectionConflict
from trading_radar.scan_preview import preview_scan
from trading_radar.scanner import scan


class Snapshot:
    def __init__(self, jobs, conflicts=(), complete=True):
        self.result = Collection(jobs=jobs, conflicts=list(conflicts), complete=complete)

    async def collect(self):
        return self.result


class Notifier:
    def __init__(self):
        self.sent = []

    async def send(self, job, event):
        self.sent.append((job.id, event))


def conflict(raw):
    return CollectionConflict(
        external_id=raw.external_id,
        urls=[raw.apply_url, raw.apply_url + "-alias"],
        fields=["description", "employment_type"],
    )


def other(raw):
    return raw.model_copy(
        update={
            "external_id": "unrelated",
            "title": "Graduate Rates Trader 2027",
            "apply_url": "https://example.com/unrelated",
        }
    )


def run(config, repo, collector, notifier=None):
    return asyncio.run(scan(config, repo, collectors={"test": collector}, notifier=notifier))


def configure_path(config, repo):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )


def test_degraded_import_preserves_conflicted_row_and_state(config, repo, raw):
    run(config, repo, Snapshot([raw]))
    old = repo.db.execute("SELECT * FROM jobs").fetchone()
    old_source = tuple(repo.db.execute("SELECT * FROM job_sources").fetchone())
    state = repo.state("test")
    notifier = Notifier()
    metrics = run(config, repo, Snapshot([other(raw)], [conflict(raw)]), notifier)
    assert metrics.new == metrics.received == 1
    assert metrics.successful == metrics.closed == metrics.alerts == 0
    assert "test" in metrics.failed
    assert metrics.degraded["test"] == [conflict(raw)]
    assert tuple(
        repo.db.execute("SELECT * FROM jobs WHERE id=?", (old["id"],)).fetchone()
    ) == tuple(old)
    assert (
        tuple(repo.db.execute("SELECT * FROM job_sources WHERE job_id=?", (old["id"],)).fetchone())
        == old_source
    )
    for field in ("last_success", "bootstrapped", "last_count", "average_response_time"):
        assert repo.state("test")[field] == state[field]
    assert repo.state("test")["consecutive_failures"] == 1
    assert not repo.pending() and not notifier.sent
    recorded = json.loads(
        repo.db.execute("SELECT metrics FROM scan_runs ORDER BY id DESC").fetchone()[0]
    )
    assert recorded["degraded"]["test"][0]["external_id"] == raw.external_id


@pytest.mark.parametrize("complete", [False, True])
def test_all_conflicted_does_not_close_or_bootstrap(config, repo, raw, complete):
    first = run(config, repo, Snapshot([], [conflict(raw)], complete))
    assert first.received == first.successful == 0
    assert not repo.state("test")["bootstrapped"]
    run(config, repo, Snapshot([raw]))
    for _ in range(3):
        run(config, repo, Snapshot([], [conflict(raw)], complete))
    assert repo.list_jobs()[0].is_active
    assert repo.state("test")["consecutive_failures"] == 3


def test_quarantined_identifier_cannot_be_imported(config, repo, raw):
    metrics = run(config, repo, Snapshot([raw], [conflict(raw)]))
    assert metrics.failed == {"test": "ValueError"}
    assert not repo.list_jobs() and not metrics.degraded


def test_degraded_normalization_failure_rolls_back_snapshot(config, repo, raw):
    invalid = other(raw).model_copy(update={"source": "wrong"})
    metrics = run(config, repo, Snapshot([other(raw), invalid], [conflict(raw)]))
    assert metrics.failed and not metrics.degraded
    assert not repo.list_jobs()


def test_upsert_failure_rolls_back_earlier_rows(config, repo, raw, monkeypatch):
    original = repo.upsert
    calls = []

    def broken(job):
        calls.append(job)
        if len(calls) == 2:
            raise ValueError("simulated write failure")
        return original(job)

    monkeypatch.setattr(repo, "upsert", broken)
    second = other(raw).model_copy(
        update={"external_id": "third", "apply_url": "https://example.com/third"}
    )
    metrics = run(config, repo, Snapshot([other(raw), second], [conflict(raw)]))
    assert metrics.failed and not metrics.degraded and not repo.list_jobs()


def test_pending_alerts_pause_across_scans_and_resume_after_clean_recovery(config, repo, raw):
    config.settings.bootstrap_silent = False
    run(config, repo, Snapshot([raw]))
    assert len(repo.pending()) == 1
    notifier = Notifier()
    run(config, repo, Snapshot([other(raw)], [conflict(raw)]), notifier)
    assert len(repo.pending()) == 1 and not notifier.sent
    assert quarantined_sources(repo.db) == {"test"}
    # No collection of this source: its existing pending notification stays held.
    asyncio.run(scan(config, repo, collectors={}, notifier=notifier))
    assert not notifier.sent
    recovered = run(config, repo, Snapshot([raw, other(raw)]), notifier)
    assert recovered.successful == 1 and recovered.alerts == 1
    assert not quarantined_sources(repo.db)
    assert repo.state("test")["consecutive_failures"] == 0


def test_diagnostics_survive_unrelated_scan_and_failure_then_clear_on_success(config, repo, raw):
    configure_path(config, repo)
    run(config, repo, Snapshot([raw]))
    run(config, repo, Snapshot([other(raw)], [conflict(raw)]))
    config.companies["other"] = Company(name="Other", ats="fixture", enabled=True)
    asyncio.run(scan(config, repo, collectors={"other": Snapshot([])}))

    class Broken:
        async def collect(self):
            raise ValueError("transport failure")

    run(config, repo, Broken())
    health = check_health(config)
    source = next(item for item in health["sources"] if item["source"] == "test")
    assert source["status"] == "recent_failure"
    assert source["collection_conflicts"] == [conflict(raw).model_dump()]
    assert any(item["code"] == "source_collection_conflicts" for item in health["issues"])
    audit = audit_sources(config)
    assert audit["sources"][0]["status"] == "failed"
    assert audit["sources"][0]["collection_conflicts"] == source["collection_conflicts"]
    dashboard = build_dashboard_data(config)
    assert (
        dashboard["health"]["sources"][0]["collection_conflicts"] == source["collection_conflicts"]
    )
    run(config, repo, Snapshot([raw, other(raw)]))
    health = check_health(config)
    assert health["sources"][0]["status"] == "fresh"
    assert "collection_conflicts" not in health["sources"][0]


def test_preview_reports_conflicts_and_changes_without_touching_original(config, repo, raw):
    configure_path(config, repo)
    run(config, repo, Snapshot([raw]))
    before = list(repo.db.iterdump())
    result = asyncio.run(
        preview_scan(config, collectors={"test": Snapshot([other(raw)], [conflict(raw)])})
    )
    assert result["status"] == "incomplete"
    assert len(result["changes"]) == 1
    assert result["metrics"]["degraded"]["test"][0]["external_id"] == raw.external_id
    assert list(repo.db.iterdump()) == before


def test_legacy_metrics_without_diagnostics_stay_readable(repo):
    repo.record_scan({"failed": {"test": "old error"}})
    assert source_conflicts(repo.db, "test", None) == []


def test_clean_recovery_keeps_first_success_silent(config, repo, raw):
    notifier = Notifier()
    run(config, repo, Snapshot([other(raw)], [conflict(raw)]), notifier)
    assert not repo.state("test")["bootstrapped"]
    result = run(config, repo, Snapshot([raw, other(raw)]), notifier)
    assert result.new == 1 and result.successful == 1
    assert repo.state("test")["bootstrapped"]
    assert not notifier.sent and not repo.pending()


def test_repeated_degraded_scan_is_idempotent_and_keeps_followup(config, repo, raw):
    run(config, repo, Snapshot([raw]))
    job = repo.list_jobs()[0]
    repo.update_application(job.id, {"status": "Reviewing", "notes": "Review tomorrow"})
    before = repo.application_details(job.id), repo.application_history(job.id)
    collector = Snapshot([other(raw)], [conflict(raw)])
    run(config, repo, collector)
    result = run(config, repo, collector)
    assert result.new == result.updated == result.closed == 0
    assert (repo.application_details(job.id), repo.application_history(job.id)) == before
