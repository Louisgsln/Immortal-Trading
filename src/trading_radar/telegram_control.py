"""Private read-only Telegram commands and bounded incident notifications."""

import asyncio
import hashlib
import logging
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from filelock import FileLock
from pydantic import ConfigDict, Field

from trading_radar.backups import database_path
from trading_radar.config import Config
from trading_radar.notifications import TelegramNotifier
from trading_radar.runtime_status import atomic_json, format_status, incident_keys, runtime_report
from trading_radar.telegram_digest import (
    DigestState,
    check_digest,
    digest_message,
    digest_status,
    enable_digest,
)
from trading_radar.telegram_jobs import jobs_message

logger = logging.getLogger("trading_radar.telegram")
HELP = "📡 Immortal Trading\n/status : activité du radar, état des sources et alertes.\n/top : jusqu’à 5 meilleures offres à examiner.\n/new : jusqu’à 5 offres découvertes depuis 24 h.\n/help : cette aide.\nListes au seuil des alertes, sources et fiches récentes. Ces commandes ne modifient pas tes candidatures."
HELP += "\n/digest : aperçu et état du récapitulatif.\n/digest_on HH:MM : activer à cette heure de Paris.\n/digest_off : arrêter le récapitulatif."


class ControlState(DigestState):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    version: Literal[1] = 1
    binding: str
    offset: int = Field(default=0, ge=0, le=2**63)
    candidate: list[str] = Field(default_factory=list)
    candidate_since: float = Field(default=0, ge=0)
    notified: list[str] = Field(default_factory=list)
    last_notice: float = Field(default=0, ge=0)


class ControlStore:
    def __init__(self, path: Path, binding: str):
        self.path = path
        if path.exists():
            self.state = ControlState.model_validate_json(path.read_text(encoding="utf-8"))
            if self.state.binding != binding:
                raise ValueError("Telegram state belongs to a different destination")
        else:
            self.state = ControlState(binding=binding)

    def save(self) -> None:
        atomic_json(self.path, self.state.model_dump())


def command_from(update: dict, chat_id: str, username: str, now: float) -> str | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat, sender = message.get("chat"), message.get("from")
    if not isinstance(chat, dict) or not isinstance(sender, dict):
        return None
    if (
        chat.get("type") != "private"
        or type(chat.get("id")) is not int
        or str(chat["id"]) != chat_id
        or type(sender.get("id")) is not int
        or str(sender["id"]) != chat_id
        or sender.get("is_bot") is not False
    ):
        return None
    date, text = message.get("date"), message.get("text")
    if type(date) is not int or not 0 <= now - date <= 300 or not isinstance(text, str):
        return None
    match = re.fullmatch(
        r"/(status|start|help|top|new|digest|digest_on|digest_off)(?:@([A-Za-z0-9_]+))?(?:[ \t]+([^\r\n]{0,128}))?",
        text.strip(),
    )
    if not match or (match[2] and match[2].casefold() != username.casefold()):
        return None
    if match[1] == "digest_on":
        argument = (match[3] or "").strip()
        if argument and not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", argument):
            return "digest_usage"
        return "digest_on" + (" " + argument if argument else "")
    if match[1] in {"digest", "digest_off"} and match[3]:
        return "digest_usage"
    return match[1]


async def api(notifier: TelegramNotifier, method: str, payload: dict):
    # Never expose exception text: the URL embeds the bot token.
    try:
        async with httpx.AsyncClient(timeout=30, transport=notifier.transport) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{notifier.token}/{method}", json=payload
            )
            if response.status_code != 200:
                raise ValueError("Telegram API status rejected")
            body = response.json()
            if not isinstance(body, dict) or body.get("ok") is not True or "result" not in body:
                raise ValueError("Telegram API acknowledgement invalid")
            return body["result"]
    except (httpx.HTTPError, ValueError, TypeError):
        raise RuntimeError("Telegram API unavailable") from None


async def process_updates(
    updates: object,
    config: Config,
    notifier: TelegramNotifier,
    store: ControlStore,
    username: str,
    now: float,
) -> None:
    if not isinstance(updates, list) or len(updates) > 100:
        raise ValueError("Invalid Telegram update batch")
    identifiers = []
    for update in updates:
        if (
            not isinstance(update, dict)
            or type(update.get("update_id")) is not int
            or not 0 <= update["update_id"] < 2**63
        ):
            raise ValueError("Invalid Telegram update identifier")
        identifiers.append(update["update_id"])
    if identifiers != sorted(set(identifiers)):
        raise ValueError("Unordered Telegram update batch")
    replies = 0
    for update in updates:
        if update["update_id"] < store.state.offset:
            continue
        command = command_from(update, notifier.chat_id, username, now)
        # Persist before delivery: crashes and ambiguous sends cannot replay a command.
        store.state.offset = update["update_id"] + 1
        store.save()
        if command is None or replies >= 3:
            continue
        replies += 1
        instant = datetime.fromtimestamp(now, UTC)
        if command == "digest_usage":
            text = "Utilise /digest, /digest_on HH:MM (heure de Paris) ou /digest_off. Exemple : /digest_on 09:00."
        elif command.startswith("digest_on"):
            enable_digest(store.state, command.partition(" ")[2] or None, instant)
            store.save()
            text = digest_status(store.state) + "\nDébut au prochain horaire à venir."
        elif command == "digest_off":
            store.state.digest_enabled = False
            store.save()
            text = digest_status(store.state)
        elif command == "digest":
            text = (
                digest_status(store.state)
                + "\n\nAPERÇU À LA DEMANDE\n"
                + digest_message(config, instant)
            )
        elif command in {"top", "new"}:
            text = jobs_message(config, "top" if command == "top" else "new")
        else:
            text = format_status(runtime_report(config)) if command == "status" else HELP
        try:
            await notifier.send_text(text)
            logger.info("telegram_command_delivered command=%s", command)
        except Exception as error:
            logger.warning("telegram_command_delivery_unconfirmed type=%s", type(error).__name__)


async def check_incidents(
    config: Config, notifier: TelegramNotifier, store: ControlStore, report: dict, now: float
) -> None:
    if not config.settings.telegram_incident_notices_enabled:
        return
    signature = incident_keys(report)
    state = store.state
    if signature != state.candidate:
        state.candidate, state.candidate_since = signature, now
        store.save()
        return
    if (
        signature == state.notified
        or now - state.candidate_since < 120
        or now - state.last_notice < 1800
    ):
        return
    # No repeated notice after an uncertain send or restart. /status is always available.
    state.notified, state.last_notice = signature, now
    store.save()
    heading = "⚠️ ÉTAT DU RADAR MODIFIÉ" if signature else "✅ RETOUR À UN ÉTAT NORMAL"
    try:
        await notifier.send_text(heading + "\n\n" + format_status(report))
        logger.info("telegram_incident_notice_delivered")
    except Exception as error:
        logger.warning("telegram_incident_delivery_unconfirmed type=%s", type(error).__name__)


async def run_control(config: Config) -> None:
    if not config.settings.telegram_control_enabled:
        raise ValueError("Telegram control is disabled")
    notifier = TelegramNotifier.from_env()
    if not re.fullmatch(r"[1-9][0-9]*", notifier.chat_id):
        raise ValueError("A private numeric Telegram chat is required")
    path = database_path(config.settings.database_url).with_suffix(".telegram.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + ".lock", timeout=0):
        binding = hashlib.sha256(
            (notifier.token.split(":", 1)[0] + ":" + notifier.chat_id).encode()
        ).hexdigest()
        store = ControlStore(path, binding)
        me = await api(notifier, "getMe", {})
        webhook = await api(notifier, "getWebhookInfo", {})
        if (
            not isinstance(me, dict)
            or not isinstance(me.get("username"), str)
            or not isinstance(webhook, dict)
            or webhook.get("url") != ""
        ):
            raise ValueError("Bot identity unavailable or existing webhook configured")
        await api(
            notifier,
            "setMyCommands",
            {
                "scope": {"type": "chat", "chat_id": notifier.chat_id},
                "commands": [
                    {"command": "status", "description": "État du radar et des sources"},
                    {"command": "top", "description": "Meilleures offres à examiner"},
                    {"command": "new", "description": "Offres découvertes depuis 24 h"},
                    {"command": "digest", "description": "Aperçu et réglage du récapitulatif"},
                    {
                        "command": "digest_on",
                        "description": "Activer le récapitulatif (HH:MM Paris)",
                    },
                    {"command": "digest_off", "description": "Désactiver le récapitulatif"},
                    {"command": "help", "description": "Aide du radar"},
                ],
            },
        )
        store.save()
        last_check = 0.0
        while True:
            try:
                updates = await api(
                    notifier,
                    "getUpdates",
                    {
                        "offset": store.state.offset,
                        "limit": 100,
                        "timeout": 20,
                        "allowed_updates": ["message"],
                    },
                )
                await process_updates(updates, config, notifier, store, me["username"], time.time())
                if time.monotonic() - last_check >= 60:
                    await check_incidents(
                        config, notifier, store, runtime_report(config), time.time()
                    )
                    await check_digest(config, notifier, store, datetime.now(UTC))
                    last_check = time.monotonic()
            except (OSError, ValueError, RuntimeError) as error:
                logger.warning("telegram_control_cycle_failed type=%s", type(error).__name__)
                await asyncio.sleep(10)
