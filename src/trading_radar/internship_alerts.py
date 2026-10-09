"""Explain current internship alert criteria without queuing or sending anything."""

from collections import Counter

from trading_radar.config import Config
from trading_radar.programmes import internship_policy_reasons

MESSAGES = {
    "internships_disabled": "La veille internships est désactivée.",
    "internship_alerts_disabled": "Les alertes internships sont désactivées.",
    "alerts_disabled": "Les alertes Telegram du radar sont désactivées.",
    "programme_conflict": "Les informations du programme se contredisent : consultez les extraits employeur.",
    "summer_excluded": "Les Summer Internships sont exclus des alertes.",
    "format_unconfirmed": "Le format off-cycle ou stage long n’est pas confirmé.",
    "format_outside_scope": "Le format annoncé est hors du périmètre des alertes.",
    "year_unconfirmed": "L’année du stage n’est pas confirmée.",
    "year_outside_scope": "L’année annoncée est différente de l’année ciblée.",
    "inactive": "L’offre est inactive dans le radar.",
    "expired": "La date limite de candidature est dépassée.",
    "marked_expired": "Le radar a marqué cette offre comme expirée.",
    "score_below_threshold": "Le score est inférieur au seuil d’alerte.",
    "excluded": "Les critères du radar excluent cette offre ; consultez le détail du score.",
    "source_disabled": "Cette source est désactivée dans le radar.",
    "reference_pending": "La première collecte de référence des stages n’est pas encore validée pour cette source.",
    "reference_unavailable": "La preuve de collecte de référence est indisponible.",
    "source_conflicts": "La source contient des fiches contradictoires : les alertes attendent une collecte sans conflit.",
}


def alert_criteria(
    job: dict,
    config: Config,
    coverage: dict,
    source_health: dict,
    *,
    stored_expired: bool = False,
    radar_alerts_enabled: bool | None = None,
) -> dict | None:
    observed = job["programme"]
    if observed["kind"] != "internship":
        return None
    reasons = internship_policy_reasons(observed, config.settings)
    alerts_enabled = (
        config.settings.alerts_enabled if radar_alerts_enabled is None else radar_alerts_enabled
    )
    if not alerts_enabled:
        reasons.append("alerts_disabled")
    if not job["is_active"]:
        reasons.append("inactive")
    if job["is_expired"]:
        reasons.append("expired")
    elif stored_expired:
        reasons.append("marked_expired")
    if job["score"] < config.settings.alert_min_score:
        reasons.append("score_below_threshold")
    if job["score_breakdown"]["exclusions"]:
        reasons.append("excluded")
    company = config.companies.get(job["source"])
    reference = coverage.get("sources", {}).get(job["source"], {}).get("status")
    if company is None or not company.enabled:
        reasons.append("source_disabled")
    elif coverage.get("status") == "disabled":
        pass  # Explained by the actual policy above.
    elif coverage.get("status") != "ok" or reference not in {
        "validated",
        "prevalidated",
        "pending",
    }:
        reasons.append("reference_unavailable")
    elif reference == "pending":
        reasons.append("reference_pending")
    health_status = source_health.get("status", "unavailable")
    if source_health.get("collection_conflicts"):
        reasons.append("source_conflicts")
    warnings = []
    if health_status != "fresh":
        warnings.append(
            "La source n’est pas entièrement à jour. Une prochaine collecte doit vérifier cette offre."
        )
    status = (
        "blocked"
        if any(reason != "reference_unavailable" for reason in reasons)
        else "unavailable"
        if reasons
        else "eligible"
    )
    return {
        "status": status,
        "reasons": [{"code": code, "message": MESSAGES[code]} for code in reasons],
        "warnings": warnings,
        "score_threshold": config.settings.alert_min_score,
        "target_year": config.settings.internship_target_year,
        "reference_status": reference,
        "source_status": health_status,
    }


def internship_summary(jobs: list[dict]) -> dict:
    stages = [job for job in jobs if job["programme"]["kind"] == "internship"]
    available = [job for job in stages if job["is_active"] and not job["is_expired"]]
    formats = Counter(format_ for job in available for format_ in job["programme"]["formats"])
    years = Counter(job["programme"]["year_status"] for job in available)
    return {
        "total": len(stages),
        "active": sum(job["is_active"] for job in stages),
        "available": len(available),
        "formats": dict(formats),
        "year_status": dict(years),
        "criteria_met": sum(job["internship_alert"]["status"] == "eligible" for job in available),
    }
