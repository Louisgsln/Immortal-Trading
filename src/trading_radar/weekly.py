"""Weekly discovery funnel from a validated snapshot, without changing scores or alerts."""

from collections import Counter
from datetime import UTC, datetime, timedelta

from trading_radar.audit import timestamp
from trading_radar.opportunity_eligibility import eligible


def weekly_report(jobs: list[dict], health: dict, threshold: int, now: datetime) -> dict:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Weekly observation requires a timezone")
    instant = now.astimezone(UTC)
    cutoff = instant - timedelta(days=7)
    fresh = {s["source"] for s in health.get("sources", []) if s["status"] == "fresh"}
    counts: Counter[str] = Counter()
    blocked: Counter[str] = Counter()
    companies: dict[str, Counter] = {}
    for job in jobs:
        first = timestamp(job["first_seen"])
        if first is None or not cutoff <= first <= instant:
            continue
        counts["discovered"] += 1
        company = companies.setdefault(job["company"], Counter())
        company["discovered"] += 1
        if job["score"] >= threshold:
            counts["score70"] += 1
            company["score70"] += 1
        stage = job.get("internship_alert")
        if not job["is_active"]:
            reason = "inactive"
        elif job["is_expired"]:
            reason = "expired"
        elif job["score_breakdown"]["exclusions"]:
            reason = "excluded"
        elif job["score"] < threshold:
            reason = "score_below_threshold"
        elif stage is not None and stage["status"] != "eligible":
            reason = "internship_conditions"
        elif job["source"] not in fresh:
            reason = "source_not_fresh"
        elif not eligible(job, fresh, threshold, instant):
            reason = "tracking_or_verification"
        else:
            counts["ready"] += 1
            company["ready"] += 1
            continue
        blocked[reason] += 1
    return {
        "days": 7,
        "since": cutoff.isoformat(),
        "until": instant.isoformat(),
        "threshold": threshold,
        "discovered": counts["discovered"],
        "score70": counts["score70"],
        "ready": counts["ready"],
        "blocked": dict(blocked),
        "companies": [
            {"company": name, **{key: value[key] for key in ("discovered", "score70", "ready")}}
            for name, value in sorted(
                companies.items(), key=lambda item: (-item[1]["ready"], item[0])
            )
        ],
        "scope": "discovery_not_publication_or_sent_alerts",
    }
