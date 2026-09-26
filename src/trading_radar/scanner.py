import asyncio
import json
import logging
import time
from contextlib import nullcontext
from datetime import datetime

from filelock import FileLock

from trading_radar.collection_diagnostics import quarantined_sources
from trading_radar.collectors import Collector, build_collector
from trading_radar.config import Config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.http_cache import JSONCache
from trading_radar.models import Job, ScanMetrics, utcnow
from trading_radar.normalizer import normalize
from trading_radar.notifications import DeliveryUnknown, Notifier
from trading_radar.reminders import deadline_plan, queue_reminders
from trading_radar.scoring import score_job
from trading_radar.source_schedule import due_at, scan_lock, writer_lock
from trading_radar.storage import Repository, source_identity

logger = logging.getLogger("trading_radar")


def configure_logging() -> None:
    import os

    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def log(event: str, **fields) -> None:
    logger.info(
        json.dumps({"timestamp": utcnow().isoformat(), "level": "INFO", "event": event, **fields})
    )


def meaningful_update(repo: Repository, job: Job) -> bool:
    previous = repo.db.execute(
        "SELECT payload FROM job_versions WHERE job_id=? ORDER BY id DESC LIMIT 1 OFFSET 1",
        (job.id,),
    ).fetchone()
    if not previous:
        return False
    old = Job.model_validate_json(previous[0])
    return any(
        getattr(old, field) != getattr(job, field)
        for field in ("title_normalized", "location_normalized", "application_deadline")
    )


async def deliver(
    repo: Repository,
    notifier: Notifier,
    min_score: int,
    *,
    reminders_enabled: bool = False,
    reminder_max_age_hours: float = 24,
    skip_sources: set[str] | None = None,
    only_sources: set[str] | None = None,
) -> int:
    delivered = 0
    for alert in repo.pending():
        job = repo.get(alert["job_id"])
        if job.source in (skip_sources or set()):
            continue
        if only_sources is not None and job.source not in only_sources:
            continue
        event = alert["event_key"].split(":")[-2]
        if event.startswith("deadline_j"):
            if not reminders_enabled:
                continue
            plan = deadline_plan(job, repo.application(job.id), min_score, reminder_max_age_hours)
            if not plan["eligible"] or plan["event_key"] != alert["event_key"]:
                repo.set_alert(alert["id"], "suppressed")
                continue
            job = job.model_copy(
                update={"application_deadline": datetime.fromisoformat(plan["deadline"])}
            )
        expired = job.application_deadline and job.application_deadline < utcnow()
        if (
            not job.is_active
            or expired
            or job.score_breakdown.exclusions
            or job.score_breakdown.total < min_score
        ):
            repo.set_alert(alert["id"], "suppressed")
            continue
        # Commit before network I/O. Crash recovery must not resend uncertain deliveries.
        repo.set_alert(alert["id"], "sending")
        try:
            await notifier.send(job, event)
        except DeliveryUnknown:
            repo.set_alert(alert["id"], "unknown", "DeliveryUnknown")
            log("alert_delivery_unknown", alert_id=alert["id"])
        except Exception as exc:
            repo.set_alert(alert["id"], "pending", type(exc).__name__)
            log("alert_failed", alert_id=alert["id"], error_type=type(exc).__name__)
        else:
            repo.set_alert(alert["id"], "sent")
            delivered += 1
    return delivered


async def scan(
    config: Config,
    repo: Repository,
    *,
    company: str | None = None,
    source: str | None = None,
    due_only: bool = False,
    collectors: dict[str, Collector] | None = None,
    notifier: Notifier | None = None,
    http: HTTPClient | None = None,
    json_cache: JSONCache | None = None,
    _scan_lease: FileLock | None = None,
) -> ScanMetrics:
    metrics = ScanMetrics()
    started = time.monotonic()
    own_http = http is None
    http = http or HTTPClient(
        config.settings.timeout, config.settings.retries, json_cache=json_cache
    )
    semaphore = asyncio.Semaphore(config.settings.concurrency)
    bootstrapped_sources: set[str] = set()
    selected = {
        key: co
        for key, co in config.companies.items()
        if co.enabled
        and (not company or co.name.casefold() == company.casefold())
        and (not source or key == source or co.ats == source)
    }
    if collectors is not None:
        selected = {key: config.companies[key] for key in collectors}

    async def run_one(key: str) -> None:
        assert http is not None
        co = selected[key]
        async with semaphore:
            state = repo.state(key)
            if due_only and utcnow() < due_at(co, state):
                return
            metrics.sources += 1
            source_start = time.monotonic()
            source_http = http
            separate_session = own_http and collectors is None and len(selected) > 1
            if separate_session:
                source_http = HTTPClient(
                    config.settings.timeout,
                    config.settings.retries,
                    json_cache=json_cache,
                    pacing=http.pacing,
                )
            log("source_started", source=key, collector=co.ats, company=co.name)
            try:
                collector = (
                    collectors[key]
                    if collectors is not None
                    else build_collector(key, co, source_http)
                )
                try:
                    async with asyncio.timeout(config.settings.source_timeout):
                        result = await collector.collect()
                except TimeoutError:
                    raise SourceUnavailable(
                        "source time budget exceeded; no snapshot committed"
                    ) from None
                if result.listing_gaps:
                    metrics.listing_gaps[key] = result.listing_gaps
                excluded = {conflict.external_id for conflict in result.conflicts}
                if any(str(raw.external_id) in excluded for raw in result.jobs):
                    raise ValueError("collector returned a quarantined identifier")
                # Normalize whole snapshot before writing. A malformed row cannot close other jobs.
                normalized = [
                    score_job(normalize(raw, config.settings.store_raw), config.keywords)
                    for raw in result.jobs
                ]
                if any(job.source != key for job in normalized):
                    raise ValueError("collector returned an incorrect source identity")
                if (
                    result.complete
                    and not result.conflicts
                    and not normalized
                    and state["last_count"] > 0
                ):
                    raise SourceUnavailable("unexpected empty full snapshot; closure deferred")
                silent = config.settings.bootstrap_silent and not state["bootstrapped"]
                if silent:
                    bootstrapped_sources.add(key)
                seen: set[str] = set()
                unique: dict[str, Job] = {}
                counts = {"new": 0, "updated": 0, "closed": 0}
                async with writer_lock(repo):
                    with repo.transaction():
                        for incoming in normalized:
                            seen.add(source_identity(incoming))
                            job, event = repo.upsert(incoming)
                            unique[job.id] = job
                            if event == "new":
                                counts["new"] += 1
                            elif event in {"updated", "reopened", "rescored"}:
                                counts["updated"] += 1
                            alertable = event in {"new", "reopened"} or (
                                event == "updated" and meaningful_update(repo, job)
                            )
                            if (
                                not silent
                                and not result.conflicts
                                and alertable
                                and not job.is_expired
                                and not job.score_breakdown.exclusions
                                and job.score_breakdown.total >= config.settings.alert_min_score
                            ):
                                if config.settings.alerts_enabled:
                                    repo.enqueue(job, event)
                        if result.complete and not result.conflicts and not result.listing_gaps:
                            counts["closed"] = repo.reconcile(
                                key, seen, config.settings.closure_after_missing_scans
                            )
                        if result.conflicts:
                            repo.record_failure(key)
                        else:
                            repo.mark_success(key, len(normalized), time.monotonic() - source_start)
                if result.conflicts:
                    metrics.degraded[key] = result.conflicts
                    metrics.failed[key] = (
                        f"Collecte dégradée : {len(result.conflicts)} référence(s) en conflit exclue(s) ; "
                        f"{len(normalized)} offre(s) validée(s) importée(s)"
                    )
                else:
                    metrics.successful += 1
                metrics.received += len(normalized)
                metrics.new += counts["new"]
                metrics.updated += counts["updated"]
                metrics.closed += counts["closed"]
                log(
                    "source_degraded" if result.conflicts else "source_success",
                    source=key,
                    collector=co.ats,
                    company=co.name,
                    jobs_found=len(normalized),
                    jobs_new=counts["new"],
                    jobs_updated=counts["updated"],
                    bootstrap=silent,
                    excluded_conflicts=len(result.conflicts),
                    incomplete_listings=len(result.listing_gaps),
                    duration=round(time.monotonic() - source_start, 3),
                )
            except Exception as exc:
                async with writer_lock(repo):
                    repo.mark_failure(key)
                # Only our sanitized exceptions may be shown; third-party errors may contain secrets.
                error = str(exc) if isinstance(exc, SourceUnavailable) else type(exc).__name__
                metrics.failed[key] = error
                log("source_failed", source=key, collector=co.ats, company=co.name, error=error)
            finally:
                metrics.requests += source_http.counts.pop(key, 0)
                if separate_session:
                    await source_http.close()

    try:
        lease = scan_lock(repo)
        if _scan_lease is not None and (
            not _scan_lease.is_locked or _scan_lease.lock_file != lease.lock_file
        ):
            raise ValueError("Invalid scanner lease")
        with nullcontext() if _scan_lease is not None else lease:
            await asyncio.gather(*(run_one(key) for key in selected))
            async with writer_lock(repo):
                blocked_sources = quarantined_sources(repo.db) | set(metrics.failed)
                if config.settings.alerts_enabled and notifier:
                    if config.settings.deadline_reminders_enabled:
                        queue_reminders(
                            repo,
                            config.settings.alert_min_score,
                            config.settings.deadline_reminder_max_age_hours,
                            skip_sources=bootstrapped_sources | blocked_sources,
                            only_sources=set(selected),
                        )
                    metrics.alerts = await deliver(
                        repo,
                        notifier,
                        config.settings.alert_min_score,
                        reminders_enabled=config.settings.deadline_reminders_enabled,
                        reminder_max_age_hours=config.settings.deadline_reminder_max_age_hours,
                        skip_sources=blocked_sources,
                        only_sources=set(selected),
                    )
                jobs = repo.list_jobs()
                metrics.relevant = sum(j.is_active and j.score_breakdown.total >= 55 for j in jobs)
                metrics.high_priority = sum(
                    j.is_active and j.score_breakdown.total >= 70 for j in jobs
                )
                metrics.duration = round(time.monotonic() - started, 3)
                if metrics.sources or metrics.alerts:
                    repo.record_scan(metrics.model_dump())
    finally:
        if own_http:
            await http.close()
    return metrics
