import asyncio

from trading_radar.config import Company
from trading_radar.models import Collection
from trading_radar.notifications import DeliveryUnknown
from trading_radar.scanner import scan


class MemoryCollector:
    def __init__(self, jobs, complete=True, error=False):
        self.jobs, self.complete, self.error = jobs, complete, error

    async def collect(self):
        if self.error:
            raise ValueError("simulated parser failure")
        return Collection(jobs=self.jobs, complete=self.complete)


class FakeNotifier:
    def __init__(self, error=None):
        self.sent = []
        self.error = error

    async def send(self, job, event):
        if self.error:
            raise self.error
        self.sent.append((job.id, event))


def test_source_filter_accepts_config_key_and_ats(config, repo, raw, monkeypatch):
    config.companies["second"] = Company(name="Second", ats="fixture", enabled=True)
    seen = []

    def build(key, co, http):
        seen.append(key)
        return MemoryCollector([raw.model_copy(update={"source": key, "company": co.name})])

    monkeypatch.setattr("trading_radar.scanner.build_collector", build)
    result = asyncio.run(scan(config, repo, source="test"))
    assert result.sources == 1 and seen == ["test"]
    seen.clear()
    result = asyncio.run(scan(config, repo, source="fixture"))
    assert result.sources == 2 and set(seen) == {"test", "second"}


def run(config, repo, collectors, notifier=None):
    return asyncio.run(scan(config, repo, collectors=collectors, notifier=notifier))


def test_bootstrap_then_new_alert_only_once(config, repo, raw):
    notifier = FakeNotifier()
    collector = MemoryCollector([raw])
    first = run(config, repo, {"test": collector}, notifier)
    assert first.new == 1 and not notifier.sent
    assert not repo.pending()
    new = raw.model_copy(
        update={
            "title": "Graduate FX Trader 2027",
            "external_id": "second",
            "apply_url": "https://example.com/jobs/second",
        }
    )
    collector.jobs = [raw, new]
    second = run(config, repo, {"test": collector}, notifier)
    assert second.new == 1 and second.alerts == 1
    run(config, repo, {"test": collector}, notifier)
    assert len(notifier.sent) == 1


def test_new_source_bootstraps_independently(config, repo, raw):
    notifier = FakeNotifier()
    run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    config.companies["second"] = Company(name="Second", ats="fixture", enabled=True)
    new = raw.model_copy(
        update={"source": "second", "company": "New Bank", "apply_url": "https://example.com/new"}
    )
    run(config, repo, {"second": MemoryCollector([new])}, notifier)
    assert not notifier.sent and repo.state("second")["bootstrapped"]


def test_source_failure_isolated(config, repo, raw):
    config.companies["broken"] = Company(name="Broken", ats="fixture", enabled=True)
    metrics = run(
        config, repo, {"test": MemoryCollector([raw]), "broken": MemoryCollector([], error=True)}
    )
    assert metrics.successful == 1 and "broken" in metrics.failed
    assert not repo.state("broken")["bootstrapped"]


def test_empty_and_failed_snapshots_do_not_close(config, repo, raw):
    run(config, repo, {"test": MemoryCollector([raw])})
    for _ in range(3):
        run(config, repo, {"test": MemoryCollector([])})
    assert repo.list_jobs()[0].is_active
    assert repo.state("test")["consecutive_failures"] == 3


def test_partial_snapshots_do_not_close(config, repo, raw):
    run(config, repo, {"test": MemoryCollector([raw])})
    for _ in range(3):
        run(config, repo, {"test": MemoryCollector([], complete=False)})
    assert repo.list_jobs()[0].is_active


def test_deadline_and_reopen_are_alertable(config, repo, raw):
    from datetime import UTC, datetime

    notifier = FakeNotifier()
    keeper = raw.model_copy(
        update={"external_id": "keeper", "apply_url": "https://example.com/keeper"}
    )
    run(config, repo, {"test": MemoryCollector([raw, keeper])}, notifier)
    raw.application_deadline = datetime(2027, 1, 1, tzinfo=UTC)
    run(config, repo, {"test": MemoryCollector([raw, keeper])}, notifier)
    assert notifier.sent[-1][1] == "updated"
    run(config, repo, {"test": MemoryCollector([keeper])}, notifier)
    closed = run(config, repo, {"test": MemoryCollector([keeper])}, notifier)
    assert closed.closed == 1
    run(config, repo, {"test": MemoryCollector([raw, keeper])}, notifier)
    assert notifier.sent[-1][1] == "reopened" and len(notifier.sent) == 2


def test_description_change_does_not_alert(config, repo, raw):
    notifier = FakeNotifier()
    run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    raw.description += " Extra details."
    metrics = run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    assert metrics.updated == 1 and not notifier.sent


def test_unknown_delivery_is_not_retried(config, repo, raw):
    config.settings.bootstrap_silent = False
    notifier = FakeNotifier(DeliveryUnknown())
    run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    assert repo.db.execute("SELECT status FROM alerts").fetchone()[0] == "unknown"
    notifier.error = None
    run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    assert not notifier.sent


def test_rejected_delivery_can_retry(config, repo, raw):
    config.settings.bootstrap_silent = False
    notifier = FakeNotifier(RuntimeError("rejected"))
    run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    assert len(repo.pending()) == 1
    notifier.error = None
    run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    assert len(notifier.sent) == 1


def test_disabled_alerts_do_not_build_backlog(config, repo, raw):
    config.settings.bootstrap_silent = False
    config.settings.alerts_enabled = False
    run(config, repo, {"test": MemoryCollector([raw])})
    assert not repo.pending()


def test_watch_honors_due_times(config, repo, raw):
    collector = MemoryCollector([raw])
    run(config, repo, {"test": collector})
    result = asyncio.run(scan(config, repo, collectors={"test": collector}, due_only=True))
    assert result.sources == 0


def test_expired_job_is_stored_without_alert(config, repo, raw):
    from datetime import UTC, datetime

    config.settings.bootstrap_silent = False
    raw.application_deadline = datetime(2020, 1, 1, tzinfo=UTC)
    notifier = FakeNotifier()
    result = run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    assert result.new == 1 and not notifier.sent
    assert repo.list_jobs()[0].is_expired
