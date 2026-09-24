import os
import re
from datetime import UTC, datetime
from html import unescape
from typing import Protocol

import httpx

from trading_radar.experience import experience_requirement
from trading_radar.models import Job
from trading_radar.telegram_cards import application_keyboard, format_alert


class Notifier(Protocol):
    async def send(self, job: Job, event: str) -> None: ...


class DeliveryUnknown(RuntimeError):
    """A timed-out request may have reached Telegram; do not blindly retry."""


def format_message(job: Job, event: str) -> str:
    score = job.score_breakdown
    badge = "🚨" if score.total >= 85 else "🟠"
    events = {"new": "NOUVELLE OFFRE", "updated": "OFFRE MODIFIÉE", "reopened": "OFFRE ROUVERTE"}
    minimum = experience_requirement(job)["minimum_years"]

    def date(value: datetime | None) -> str:
        return value.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC") if value else "Non précisée"

    lines = [
        (
            f"⏰ ÉCHÉANCE DE CANDIDATURE — {event.replace('deadline_j', 'J−')} — {score.total}/100"
            if event in {"deadline_j7", "deadline_j3", "deadline_j1"}
            else f"{badge} {events.get(event, 'OPPORTUNITÉ TRADING')} — {score.total}/100"
        ),
        "",
        job.company[:150],
        job.title[:300],
        job.location_normalized[:150],
        "",
        f"Début : {(job.expected_start_date or 'Non précisé')[:100]}",
        "Expérience professionnelle : "
        + (f"minimum reconnu {minimum} an(s)" if minimum is not None else "minimum non reconnu"),
        f"Échéance : {date(job.application_deadline)}",
        "",
        "Pourquoi ce score :",
    ]
    for name, label, maximum in [
        ("trading", "Lien avec le trading", 30),
        ("junior", "Compatibilité junior", 20),
        ("start", "Calendrier", 15),
        ("front_office", "Indices front office", 15),
        ("asset", "Produits recherchés", 10),
        ("profile_fit", "Mots-clés du profil", 10),
    ]:
        lines.append(f"• {label} : {getattr(score, name)}/{maximum}")
    lines += [
        "",
        "Extrait employeur (langue d’origine) :",
        " ".join(job.description_text.split())[:500] or "Description non disponible.",
        "",
        f"Détectée le : {date(job.first_seen)}",
        f"Dernière observation : {date(job.last_seen)}",
        f"Publication : {date(job.date_posted)}",
        f"Source : {job.source[:100]}",
        "Un minimum non reconnu ne signifie pas absence d’exigence.",
        "Score de priorité, pas une probabilité de recrutement.",
        "",
        "CONSULTER L’OFFRE :",
        job.apply_url[:1500],
    ]
    return "\n".join(lines).encode("utf-16-le")[:8000].decode("utf-16-le", errors="ignore")


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, transport=None):
        if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not chat_id:
            raise ValueError("Telegram credentials missing or malformed")
        self.token, self.chat_id, self.transport = token, chat_id, transport

    @classmethod
    def from_env(cls):
        return cls(os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", ""))

    async def send(self, job: Job, event: str) -> None:
        await self.send_text(
            format_alert(job, event),
            parse_mode="HTML",
            reply_markup=application_keyboard(job.id, job.apply_url, self.token, self.chat_id),
        )

    async def send_text(
        self, text: str, *, parse_mode: str | None = None, reply_markup: dict | None = None
    ) -> None:
        visible = unescape(re.sub(r"<[^>]*>", "", text)) if parse_mode == "HTML" else text
        if not visible or len(visible.encode("utf-16-le")) // 2 > 4096:
            raise ValueError("Telegram message must contain 1 to 4096 UTF-16 units")
        # Do not log URL or HTTP exception text: Telegram embeds the token in the URL.
        async with httpx.AsyncClient(timeout=20, transport=self.transport) as client:
            try:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "link_preview_options": {"is_disabled": True},
                        **({"parse_mode": parse_mode} if parse_mode else {}),
                        **({"reply_markup": reply_markup} if reply_markup else {}),
                    },
                )
            except httpx.TransportError:
                raise DeliveryUnknown("Telegram delivery outcome unknown") from None
            if response.status_code >= 500:
                raise DeliveryUnknown("Telegram server outcome unknown")
            if response.status_code != 200:
                if not 400 <= response.status_code < 500:
                    raise DeliveryUnknown("Telegram acknowledgement status unexpected")
                raise RuntimeError(f"Telegram rejected request: HTTP {response.status_code}")
            try:
                payload = response.json()
            except ValueError:
                raise DeliveryUnknown("Telegram acknowledgement unreadable") from None
            if not isinstance(payload, dict) or type(payload.get("ok")) is not bool:
                raise DeliveryUnknown("Telegram acknowledgement invalid")
            if payload["ok"] is False:
                raise RuntimeError("Telegram did not accept notification")
