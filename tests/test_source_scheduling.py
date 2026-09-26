"""Collectors progress independently while transactional edits remain usable."""

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from filelock import FileLock, Timeout

from trading_radar import scanner, watcher
from trading_radar.config import Company
from trading_radar.dashboard_applications import read_application, update_application
from trading_radar.http import HTTPClient, RequestPacing, SourceUnavailable
from trading_radar.models import Collection
from trading_radar.source_schedule import due_at, scan_lock


class Pulse:
    def __init__(self):
        self.observations = []

    def check(self):
        pass

    def publish(self, phase, *, scan_started=None):
        self.observations.append((phase, scan_started))


def companies(config, *names):
    config.settings.alerts_enabled = False
    config.companies = {name: Company(name=name, enabled=True, ats="fixture") for name in names}
    for company in config.companies.values():
        company.scan_interval = 0.03


def test_fast_source_refreshes_while_another_is_still_collecting(config, repo, monkeypatch):
    companies(config, "fast", "slow")
    config.settings.concurrency = 2
    counts = {"fast": 0, "slow": 0}
    clients = []
    cancelled = []

    def http(*args, **kwargs):
        client = HTTPClient(
            *args, transport=httpx.MockTransport(lambda _: httpx.Response(404)), **kwargs
        )
        clients.append(client)
        return client

    class Collector:
        def __init__(self, source):
            self.source = source

        async def collect(self):
            counts[self.source] += 1
            if self.source == "slow":
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.append(self.source)
            return Collection(jobs=[], complete=False)

    monkeypatch.setattr(watcher, "HTTPClient", http)
    monkeypatch.setattr(scanner, "build_collector", lambda key, *_: Collector(key))

    async def run():
        stop = asyncio.Event()
        results = []
        async for result in watcher.watch_sources(config, repo, Pulse(), stop=stop, tick=0.01):
            results.append(result)
            if len(results) == 2:
                stop.set()
        return results

    results = asyncio.run(asyncio.wait_for(run(), timeout=5))
    assert len(results) == 2 and all(r.successful == 1 for r in results)
    assert counts == {"fast": 2, "slow": 1} and cancelled == ["slow"]
    assert all(client.client.is_closed for client in clients)
    assert len({id(client.pacing) for client in clients}) == 1
    assert not repo.state("slow")["consecutive_failures"]


def test_overdue_sources_take_precedence_over_repeated_fast_source(config, repo, monkeypatch):
    companies(config, "a_fast", "b_waiting", "c_waiting")
    config.settings.concurrency = 1
    order = []

    class Collector:
        def __init__(self, key):
            self.key = key

        async def collect(self):
            order.append(self.key)
            return Collection(jobs=[], complete=False)

    monkeypatch.setattr(scanner, "build_collector", lambda key, *_: Collector(key))

    async def run():
        stop = asyncio.Event()
        async for _ in watcher.watch_sources(config, repo, Pulse(), stop=stop, tick=0.01):
            if len(order) >= 3:
                stop.set()

    asyncio.run(asyncio.wait_for(run(), 5))
    assert order[:3] == ["a_fast", "b_waiting", "c_waiting"]


@pytest.mark.parametrize("first_success", [None, "2026-09-26T11:00:00+00:00"])
@pytest.mark.parametrize(
    "failures,seconds", [(1, 600), (2, 1200), (3, 2400), (4, 3600), (100, 3600)]
)
def test_failure_backoff_including_sources_never_collected(first_success, failures, seconds):
    last = datetime(2026, 9, 26, 12, tzinfo=UTC)
    state = {
        "last_success": first_success,
        "last_failure": last.isoformat(),
        "consecutive_failures": failures,
    }
    assert due_at(Company(name="Test", ats="fixture"), state) == last + timedelta(seconds=seconds)


def test_long_configured_interval_is_never_shortened_and_recovery_resets_backoff():
    now = datetime(2026, 9, 26, 12, tzinfo=UTC)
    company = Company(name="Test", ats="fixture", scan_interval=7200)
    state = {"last_success": now.isoformat(), "consecutive_failures": 0}
    assert due_at(company, state) == now + timedelta(seconds=7200)
    company.scan_interval = 300
    state["last_failure"] = (now - timedelta(hours=1)).isoformat()
    assert due_at(company, state) == now + timedelta(seconds=300)
    assert due_at(company, {}) < now


def test_dashboard_and_cli_edits_work_during_collection(config, repo, job, raw):
    config.settings.database_url = "sqlite:///" + repo.lock_path.removesuffix(".lock")
    with repo.transaction():
        repo.upsert(job)

    class Collector:
        async def collect(self):
            repo.update_application(job.id, {"notes": "CLI edit during network"})
            previous = read_application(config, job.id)
            update_application(config, job.id, {"status": "Applied"}, previous["revision"])
            await asyncio.sleep(0)
            return Collection(jobs=[raw], complete=False)

    result = asyncio.run(scanner.scan(config, repo, collectors={"test": Collector()}))
    assert result.successful == 1 and not result.failed
    assert repo.application(job.id).notes == "CLI edit during network"
    assert repo.application(job.id).status == "Applied"


def test_concurrent_manual_scanner_is_rejected_without_blocking_edits(config, repo):
    class Collector:
        async def collect(self):
            with pytest.raises(Timeout):
                await scanner.scan(config, repo, collectors={"test": self})
            with FileLock(repo.lock_path, timeout=0):
                pass
            return Collection(jobs=[], complete=False)

    assert asyncio.run(scanner.scan(config, repo, collectors={"test": Collector()})).successful == 1


@pytest.mark.parametrize("held", [False, True])
def test_scanner_rejects_invalid_lease(config, repo, tmp_path, held):
    lease = FileLock(str(tmp_path / "other.lock")) if held else scan_lock(repo)
    if held:
        lease.acquire()
    try:
        with pytest.raises(ValueError, match="lease"):
            asyncio.run(scanner.scan(config, repo, _scan_lease=lease))
    finally:
        lease.release()


def test_hung_collector_times_out_without_losing_other_source(config, repo):
    companies(config, "good", "hung")
    config.settings.source_timeout = 0.02

    class Collector:
        def __init__(self, hang):
            self.hang = hang

        async def collect(self):
            if self.hang:
                await asyncio.Event().wait()
            return Collection(jobs=[], complete=False)

    result = asyncio.run(
        scanner.scan(config, repo, collectors={"good": Collector(False), "hung": Collector(True)})
    )
    assert result.successful == 1 and set(result.failed) == {"hung"}
    assert "time budget" in result.failed["hung"]
    assert repo.state("hung")["consecutive_failures"] == 1
    assert repo.state("good")["bootstrapped"]


def test_pending_alert_waits_for_source_recovery(config, repo, raw):
    config.settings.bootstrap_silent = False
    sent = []

    class Collector:
        fail = False

        async def collect(self):
            if self.fail:
                raise SourceUnavailable("temporary public failure")
            return Collection(jobs=[raw], complete=False)

    class Notifier:
        async def send(self, job, event):
            sent.append(job.id)

    collector = Collector()
    asyncio.run(scanner.scan(config, repo, collectors={"test": collector}))
    assert len(repo.pending()) == 1
    collector.fail = True
    asyncio.run(scanner.scan(config, repo, collectors={"test": collector}, notifier=Notifier()))
    assert not sent and len(repo.pending()) == 1
    collector.fail = False
    asyncio.run(scanner.scan(config, repo, collectors={"test": collector}, notifier=Notifier()))
    assert len(sent) == 1 and not repo.pending()


def test_separate_sessions_preserve_cookies_while_sharing_host_pacing():
    seen = []

    def handler(request):
        seen.append((request.url.path, request.headers.get("cookie")))
        return httpx.Response(200, text="ok", headers={"Set-Cookie": "board=campus; Path=/"})

    async def run():
        pacing = RequestPacing()
        first = HTTPClient(transport=httpx.MockTransport(handler), pacing=pacing)
        second = HTTPClient(transport=httpx.MockTransport(handler), pacing=pacing)
        try:
            await first._request("https://example.com/campus", 0, "campus")
            await second._request("https://example.com/professional", 0, "professional")
            await first._request("https://example.com/next", 0, "campus")
            assert first.locks["example.com"] is second.locks["example.com"]
            assert first.counts["campus"] == 2 and second.counts["professional"] == 1
        finally:
            await first.close()
            await second.close()

    asyncio.run(run())
    assert seen == [("/campus", None), ("/professional", None), ("/next", "board=campus")]


def test_separate_sessions_cannot_bypass_host_request_interval(monkeypatch):
    clock = [100.0]
    moments = []

    async def sleep(delay):
        clock[0] += delay

    def handler(request):
        moments.append(clock[0])
        return httpx.Response(200)

    monkeypatch.setattr("trading_radar.http.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("trading_radar.http.asyncio.sleep", sleep)

    async def run():
        pacing = RequestPacing()
        clients = [
            HTTPClient(transport=httpx.MockTransport(handler), pacing=pacing) for _ in range(2)
        ]
        try:
            await clients[0]._request("https://example.com/a", 2, "first")
            await clients[1]._request("https://example.com/b", 2, "second")
            await clients[0]._request("https://example.com/c", 2, "first")
        finally:
            for client in clients:
                await client.close()

    asyncio.run(run())
    assert moments == [100.0, 102.0, 104.0]


def test_targeted_collection_does_not_deliver_another_sources_backlog(config, repo, raw):
    config.settings.bootstrap_silent = False
    config.companies["other"] = Company(name="Other Bank", ats="fixture", enabled=True)
    other = raw.model_copy(
        update={
            "company": "Other Bank",
            "source": "other",
            "external_id": "other",
            "apply_url": "https://example.com/other",
        }
    )
    sent = []

    class Collector:
        def __init__(self, job):
            self.job = job

        async def collect(self):
            return Collection(jobs=[self.job], complete=False)

    class Notifier:
        async def send(self, job, event):
            sent.append(job.source)

    asyncio.run(
        scanner.scan(config, repo, collectors={"test": Collector(raw), "other": Collector(other)})
    )
    assert len(repo.pending()) == 2
    asyncio.run(
        scanner.scan(config, repo, collectors={"test": Collector(raw)}, notifier=Notifier())
    )
    assert sent == ["test"]
    assert [repo.get(item["job_id"]).source for item in repo.pending()] == ["other"]


def test_pulse_tracks_oldest_active_source_instead_of_continuous_uptime(config, repo, tmp_path):
    from trading_radar.runtime_status import WatcherPulse, watcher_status

    config.settings.database_url = "sqlite:///" + str(tmp_path / "jobs.db")
    from trading_radar.models import utcnow

    now = utcnow()
    pulse = WatcherPulse(config)
    pulse.publish("scanning", scan_started=now - timedelta(minutes=31))
    assert watcher_status(config)["status"] == "long_scan"
    pulse.publish("scanning", scan_started=now - timedelta(seconds=20))
    assert watcher_status(config)["status"] == "active"
