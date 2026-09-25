"""Compact HTML alerts and destination-bound application buttons."""

import hashlib
import hmac
import re
from html import escape
from urllib.parse import urlsplit
from uuid import UUID

from trading_radar.experience import experience_requirement
from trading_radar.missions import mission_excerpts
from trading_radar.models import Job


def application_callback(job_id: str, token: str, chat_id: str) -> str:
    identifier = UUID(job_id).hex
    message = f"ap:{chat_id}:{identifier}"
    signature = hmac.new(token.encode(), message.encode(), hashlib.sha256).hexdigest()[:16]
    return f"ap:{identifier}:{signature}"


def callback_job(data: object, token: str, chat_id: str) -> str | None:
    if not isinstance(data, str) or not re.fullmatch(r"ap:[0-9a-f]{32}:[0-9a-f]{16}", data):
        return None
    identifier = str(UUID(data.split(":")[1]))
    return (
        identifier
        if hmac.compare_digest(data, application_callback(identifier, token, chat_id))
        else None
    )


def application_keyboard(
    job_id: str, url: str, token: str, chat_id: str, *, applied: bool = False
) -> dict:
    rows = []
    try:
        parsed = urlsplit(url)
        safe = (
            parsed.scheme in {"https", "http"}
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and len(url) <= 2000
            and not any(ord(char) < 33 for char in url)
        )
    except ValueError:
        safe = False
    if safe:
        rows.append([{"text": "↗ Voir l’offre · Postuler", "url": url}])
    # Application records use UUIDs; malformed/legacy IDs must not break alert delivery.
    try:
        callback = application_callback(job_id, token, chat_id)
    except ValueError:
        return {"inline_keyboard": rows}
    if re.fullmatch(r"[1-9][0-9]*", chat_id):
        rows.append(
            [
                {
                    "text": "✅ Postulé" if applied else "✓ J’ai postulé",
                    "callback_data": callback,
                }
            ]
        )
    return {"inline_keyboard": rows}


def format_alert(job: Job, event: str) -> str:
    def clean(value: str, limit: int) -> str:
        text = " ".join(value.split())
        return escape(text[:limit] + ("…" if len(text) > limit else ""))

    score = job.score_breakdown.total
    heading = {
        "new": "NOUVELLE OPPORTUNITÉ",
        "updated": "OFFRE ACTUALISÉE",
        "reopened": "OFFRE ROUVERTE",
        "preview": "APERÇU DU NOUVEAU FORMAT",
    }.get(event, "OPPORTUNITÉ TRADING")
    if event in {"deadline_j7", "deadline_j3", "deadline_j1"}:
        heading = "ÉCHÉANCE · " + event.replace("deadline_j", "J−")
    minimum = experience_requirement(job)["minimum_years"]
    experience = f"minimum reconnu : {minimum} an(s)" if minimum is not None else "à vérifier"
    deadline = (
        job.application_deadline.strftime("%d/%m/%Y")
        if job.application_deadline
        else "non précisée"
    )
    blocks = min(10, max(0, score // 10))
    missions = mission_excerpts(job)
    if missions:
        excerpt_label = "Missions · extraits"
        excerpt = "\n".join("• " + clean(item, 240) for item in missions["excerpts"])
    else:
        excerpt_label = "Extrait de description"
        excerpt = clean(job.description_text or "Description non disponible.", 380)
    return "\n".join(
        [
            f"{'🔥' if score >= 85 else '💼'} <b>{heading}</b>",
            "",
            f"<b>{clean(job.title, 180)}</b>",
            clean(job.company, 100),
            "",
            f"📍 {clean(job.location_normalized or 'Lieu non précisé', 100)}",
            f"🗓 Début : {clean(job.expected_start_date or 'non précisé', 80)}",
            f"🎓 Expérience : {experience}",
            f"⏳ Échéance : {deadline}",
            "",
            f"<b>Priorité · {score}/100</b>  {'▰' * blocks}{'▱' * (10 - blocks)}",
            f"Trading {job.score_breakdown.trading}/30 · Junior {job.score_breakdown.junior}/20 · Front office {job.score_breakdown.front_office}/15",
            "",
            f"<b>{excerpt_label}</b>",
            f"<blockquote>{excerpt}</blockquote>",
            f"<i>Source : {clean(job.source, 80)} · Score de priorité, pas une probabilité de recrutement.</i>",
            "",
            "Ouvre l’offre, puis confirme ici une fois ta candidature envoyée.",
        ]
    )
