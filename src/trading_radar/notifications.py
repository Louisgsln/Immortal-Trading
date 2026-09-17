import os
import re
from typing import Protocol

import httpx

from trading_radar.models import Job


class Notifier(Protocol):
    async def send(self, job: Job, event: str) -> None: ...


class DeliveryUnknown(RuntimeError):
    """A timed-out request may have reached Telegram; do not blindly retry."""


def format_message(job: Job, event: str) -> str:
    score = job.score_breakdown
    badge = "🚨" if score.total >= 85 else "🟠"
    lines = [
        (
            f"⏰ APPLICATION DEADLINE — {event.replace('deadline_j', 'J−')} WINDOW — {score.total}/100"
            if event in {"deadline_j7", "deadline_j3", "deadline_j1"}
            else f"{badge} TRADING OPPORTUNITY — {event.upper()} — {score.total}/100"
        ),
        "",
        job.company[:150],
        job.title[:300],
        job.location_normalized[:150],
        "",
    ]
    for name, maximum in [
        ("trading", 30),
        ("junior", 20),
        ("start", 15),
        ("front_office", 15),
        ("asset", 10),
        ("profile_fit", 10),
    ]:
        lines.append(f"{name}: {getattr(score, name)}/{maximum}")
    lines += [
        "",
        f"First seen: {job.first_seen.isoformat()}",
        f"Posted: {job.date_posted.isoformat() if job.date_posted else 'Unknown'}",
        f"Deadline: {job.application_deadline.isoformat() if job.application_deadline else 'Unknown'}",
        f"Source: {job.source}",
        "",
        *[r[:200] for r in score.reasons],
        "",
        "APPLY:",
        job.apply_url[:1500],
    ]
    return "\n".join(lines)[:4000]


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, transport=None):
        if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not chat_id:
            raise ValueError("Telegram credentials missing or malformed")
        self.token, self.chat_id, self.transport = token, chat_id, transport

    @classmethod
    def from_env(cls):
        return cls(os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", ""))

    async def send(self, job: Job, event: str) -> None:
        # Do not log URL or HTTP exception text: Telegram embeds the token in the URL.
        async with httpx.AsyncClient(timeout=20, transport=self.transport) as client:
            try:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": format_message(job, event),
                        "link_preview_options": {"is_disabled": True},
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
