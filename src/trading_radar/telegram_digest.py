"""One daily private digest, with a persisted attempt before delivery."""

import logging
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from trading_radar.config import Config
from trading_radar.digest_state import DigestState
from trading_radar.notifications import TelegramNotifier
from trading_radar.telegram_jobs import jobs_message

logger = logging.getLogger("trading_radar.telegram")


def scheduled(day: date, clock: str) -> datetime:
    # UTC round trip normalizes the spring gap; fold=0 chooses the first
    # occurrence during the autumn overlap. One attempt per local date.
    return datetime.combine(day, time.fromisoformat(clock), ZoneInfo("Europe/Paris")).astimezone(
        UTC
    )


def enable_digest(state: DigestState, clock: str | None, now: datetime) -> None:
    selected = DigestState(digest_time=clock or state.digest_time).digest_time
    local = now.astimezone(ZoneInfo("Europe/Paris"))
    due = scheduled(local.date(), selected)
    if due <= now:
        due = scheduled(local.date() + timedelta(days=1), selected)
    state.digest_time = selected
    state.digest_not_before = due.timestamp()
    state.digest_enabled = True


def digest_status(state: DigestState) -> str:
    status = "activé" if state.digest_enabled else "désactivé"
    last = state.digest_last_day or "aucune"
    return (
        f"Récapitulatif {status} · {state.digest_time}.\n"
        f"Dernière tentative automatique : {last}.\n"
        "/digest_on HH:MM pour activer/régler · /digest_off pour arrêter."
    )


def digest_message(config: Config, now: datetime) -> str:
    body = jobs_message(config, "new", now, max_units=4000, compact=True)
    if body.startswith("📋 Offres indisponibles"):
        return (
            "<b>🗓 Votre veille du jour</b>\n\n"
            + body
            + "\n\nÉtat des sources indisponible · /status"
        )
    return body


async def check_digest(config: Config, notifier: TelegramNotifier, store, now: datetime) -> None:
    state = store.state
    if not state.digest_enabled:
        return
    local_day = now.astimezone(ZoneInfo("Europe/Paris")).date()
    day = local_day.isoformat()
    due = scheduled(local_day, state.digest_time)
    if now < due:
        local_day -= timedelta(days=1)
        day = local_day.isoformat()
        due = scheduled(local_day, state.digest_time)
    if (
        (state.digest_last_day is not None and day <= state.digest_last_day)
        or now.timestamp() < state.digest_not_before
        or not due <= now < due + timedelta(hours=4)
    ):
        return
    text = digest_message(config, now)
    # Persist first: a crash or an ambiguous send must not duplicate the digest.
    state.digest_last_day = day
    store.save()
    try:
        await notifier.send_text(text, parse_mode="HTML")
        logger.info("telegram_digest_delivered day=%s", day)
    except Exception as error:
        logger.warning("telegram_digest_delivery_unconfirmed type=%s", type(error).__name__)
