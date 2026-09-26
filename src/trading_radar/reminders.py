"""Deadline plans and idempotent queueing. Delivery revalidates the whole plan."""

from datetime import UTC, datetime, timedelta

from trading_radar.applications import Application
from trading_radar.deadlines import resolve_deadline
from trading_radar.models import Job, utcnow
from trading_radar.normalizer import digest
from trading_radar.storage import Repository

ELIGIBLE_STATUSES = {"New", "Reviewing", "To Apply"}


def deadline_plan(
    job: Job,
    application: Application,
    min_score: int = 70,
    max_age_hours: float = 24,
    now: datetime | None = None,
) -> dict:
    now = now or utcnow()
    if now.tzinfo is None:
        raise ValueError("Reminder clock requires a timezone")
    now = now.astimezone(UTC)
    deadline = resolve_deadline(job)
    remaining = (deadline.instant - now).total_seconds() if deadline.instant else None
    stage = (
        (1 if remaining <= 86400 else 3 if remaining <= 3 * 86400 else 7)
        if remaining is not None and 0 < remaining <= 7 * 86400
        else None
    )
    reason = (
        "unknown_deadline"
        if deadline.precision == "unknown"
        else "conflicting_deadline"
        if deadline.precision == "conflict"
        else "date_without_time_or_timezone"
        if deadline.instant is None
        else "closed_job"
        if not job.is_active
        else "application_already_started_or_closed"
        if application.status not in ELIGIBLE_STATUSES or application.application_date is not None
        else "below_score_threshold"
        if job.score_breakdown.exclusions or job.score_breakdown.total < min_score
        else "stale_observation"
        if job.last_seen.tzinfo is None
        or not timedelta(0) <= now - job.last_seen <= timedelta(hours=max_age_hours)
        else "expired"
        if remaining is not None and remaining <= 0
        else "outside_reminder_window"
        if stage is None
        else None
    )
    key = (
        f"{job.id}:deadline_j{stage}:{digest(deadline.instant.isoformat())}"
        if stage and deadline.instant
        else None
    )
    return {
        "job_id": job.id,
        "source": job.source,
        "company": job.company,
        "title": job.title,
        "score": job.score_breakdown.total,
        "status": application.status.value,
        "url": job.apply_url,
        "precision": deadline.precision,
        "deadline_date": deadline.day.isoformat() if deadline.day else None,
        "deadline": deadline.instant.isoformat() if deadline.instant else None,
        "deadline_source": deadline.source,
        "evidence": deadline.evidence,
        "stage_days": stage,
        "event_key": key,
        "eligible": reason is None,
        "reason": reason,
    }


def reminder_plans(
    repo: Repository, min_score: int = 70, max_age_hours: float = 24, now: datetime | None = None
) -> list[dict]:
    now = now or utcnow()
    plans = []
    for job in repo.list_jobs():
        plan = deadline_plan(job, repo.application(job.id), min_score, max_age_hours, now)
        if plan["precision"] == "unknown":
            continue
        state = repo.alert_status(plan["event_key"]) if plan["event_key"] else None
        plan["delivery_status"] = state
        if plan["eligible"] and state not in {None, "pending"}:
            plan["eligible"], plan["reason"] = False, f"delivery_{state}"
        plans.append(plan)
    return plans


def queue_reminders(
    repo: Repository,
    min_score: int,
    max_age_hours: float = 24,
    now: datetime | None = None,
    skip_sources: set[str] | None = None,
    only_sources: set[str] | None = None,
) -> int:
    """Caller owns the scanner lock and must check both alert enablement flags."""
    plans = reminder_plans(repo, min_score, max_age_hours, now)
    with repo.transaction():
        return sum(
            repo.enqueue_reminder(p["job_id"], p["event_key"])
            for p in plans
            if p["eligible"]
            and p["source"] not in (skip_sources or set())
            and (only_sources is None or p["source"] in only_sources)
        )
