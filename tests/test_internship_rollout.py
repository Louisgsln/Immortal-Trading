import asyncio

from tests.test_scanner import FakeNotifier, MemoryCollector, run
from trading_radar.models import utcnow
from trading_radar.scanner import deliver


def internship(raw, key):
    return raw.model_copy(
        update={
            "title": "FX Trading Off-cycle Internship 2027",
            "employment_type": "Internship",
            "external_id": key,
            "apply_url": "https://example.com/jobs/" + key,
        }
    )


def enable(config):
    config.settings.include_internships = True
    config.settings.internship_alerts_enabled = True
    config.settings.internship_baseline_at = utcnow()


def test_expansion_baseline_silent_then_new_stage_alert_once(config, repo, raw):
    notifier = FakeNotifier()
    old = internship(raw, "old-stage")
    run(config, repo, {"test": MemoryCollector([raw, old])}, notifier)
    history_before = [tuple(row) for row in repo.db.execute("SELECT * FROM alert_history")]
    enable(config)
    added_to_baseline = internship(raw, "baseline-stage")
    baseline = MemoryCollector([raw, old, added_to_baseline])
    run(config, repo, {"test": baseline}, notifier)
    assert not notifier.sent and not repo.pending()
    new = internship(raw, "new-stage")
    baseline.jobs.append(new)
    result = run(config, repo, {"test": baseline}, notifier)
    assert result.alerts == 1 and len(notifier.sent) == 1
    run(config, repo, {"test": baseline}, notifier)
    assert len(notifier.sent) == 1
    assert all(
        row in [tuple(r) for r in repo.db.execute("SELECT * FROM alert_history")]
        for row in history_before
    )


def test_partial_snapshot_cannot_establish_baseline_full_time_still_alerts(config, repo, raw):
    notifier = FakeNotifier()
    run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    enable(config)
    first = internship(raw, "first")
    run(config, repo, {"test": MemoryCollector([raw, first], complete=False)}, notifier)
    second = internship(raw, "second")
    normal = raw.model_copy(
        update={
            "external_id": "normal",
            "apply_url": "https://example.com/normal",
            "title": "Graduate FX Trader 2027",
        }
    )
    run(config, repo, {"test": MemoryCollector([raw, first, second, normal])}, notifier)
    assert len(notifier.sent) == 1 and repo.get(notifier.sent[0][0]).title == normal.title
    third = internship(raw, "third")
    run(config, repo, {"test": MemoryCollector([raw, first, second, normal, third])}, notifier)
    assert len(notifier.sent) == 2


def test_queued_stage_is_suppressed_when_policy_disabled(config, repo, raw):
    from trading_radar.normalizer import normalize
    from trading_radar.scoring import score_job

    enable(config)
    job = score_job(normalize(internship(raw, "stage")), config.keywords, settings=config.settings)
    job, _ = repo.upsert(job)
    repo.enqueue(job, "new")
    config.settings.internship_alerts_enabled = False
    notifier = FakeNotifier()
    assert asyncio.run(deliver(repo, notifier, 70, settings=config.settings)) == 0
    assert not repo.pending() and not notifier.sent


def test_validated_search_baselines_internships_without_absence_closure(config, repo, raw):
    from trading_radar.models import Collection

    class Scoped(MemoryCollector):
        async def collect(self):
            return Collection(jobs=self.jobs, complete=False, scope_complete=True)

    notifier = FakeNotifier()
    run(config, repo, {"test": MemoryCollector([raw])}, notifier)
    enable(config)
    collector = Scoped([internship(raw, "reference")])
    assert run(config, repo, {"test": collector}, notifier).alerts == 0
    collector.jobs.append(internship(raw, "new"))
    assert run(config, repo, {"test": collector}, notifier).alerts == 1
    for _ in range(3):
        run(config, repo, {"test": collector}, notifier)
    assert all(row[0] for row in repo.db.execute("SELECT is_active FROM jobs"))
