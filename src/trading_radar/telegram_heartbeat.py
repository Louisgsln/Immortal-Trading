"""Private scheduled radar status, with durable attempts separate from the cursor."""

import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from filelock import FileLock
from pydantic import BaseModel, ConfigDict, Field, field_validator

from trading_radar.backups import database_path
from trading_radar.config import Config
from trading_radar.notifications import TelegramNotifier
from trading_radar.runtime_status import atomic_json, format_daily_status, runtime_report
from trading_radar.telegram_digest import scheduled

logger = logging.getLogger("trading_radar.telegram")


class HeartbeatState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    version: Literal[1] = 1
    binding: str
    not_before: float = Field(ge=0)
    attempts: dict[str, str] = Field(default_factory=dict, max_length=1440)

    @field_validator("attempts")
    @classmethod
    def valid_attempts(cls, values: dict[str, str]) -> dict[str, str]:
        import re

        for clock, day in values.items():
            if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", clock):
                raise ValueError("Invalid heartbeat slot")
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError("Invalid heartbeat date")
        return values


def heartbeat_path(config: Config) -> Path:
    return database_path(config.settings.database_url).with_suffix(".heartbeat.json")


def load_state(path: Path, binding: str, now: datetime) -> HeartbeatState:
    if now.utcoffset() is None:
        raise ValueError("Heartbeat time must include a timezone")
    if path.exists():
        state = HeartbeatState.model_validate_json(path.read_text(encoding="utf-8"))
        if state.binding != binding:
            raise ValueError("Heartbeat belongs to a different destination")
        return state
    state = HeartbeatState(binding=binding, not_before=now.timestamp())
    atomic_json(path, state.model_dump())
    return state


async def check_heartbeat(
    config: Config, notifier: TelegramNotifier, control_store, now: datetime
) -> None:
    if not config.settings.telegram_heartbeat_enabled:
        return
    path = heartbeat_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + ".lock", timeout=0):
        state = load_state(path, control_store.state.binding, now)
        local_day = now.astimezone(ZoneInfo("Europe/Paris")).date()
        candidates = [
            (scheduled(day, clock), clock, day.isoformat())
            for day in (local_day - timedelta(days=1), local_day)
            for clock in config.settings.telegram_heartbeat_times
            if scheduled(day, clock) <= now
        ]
        if not candidates:
            return
        due, clock, day = max(candidates)
        if (
            due.timestamp() < state.not_before
            or now >= due + timedelta(hours=1)
            or state.attempts.get(clock, "") >= day
        ):
            return
        # A recap at this same time already carries the radar status. Keep one
        # scheduled message, even if its delivery was uncertain.
        recap = control_store.state
        combined = (
            recap.digest_enabled and recap.digest_time == clock and recap.digest_last_day == day
        )
        text = None if combined else format_daily_status(runtime_report(config, now=now))
        state.attempts[clock] = day
        atomic_json(path, state.model_dump())
    if text is None:
        return
    try:
        await notifier.send_text(text + "\n\nDétails à tout moment · /statuts", parse_mode="HTML")
        logger.info("telegram_heartbeat_delivered day=%s slot=%s", day, clock)
    except Exception as error:
        logger.warning("telegram_heartbeat_delivery_unconfirmed type=%s", type(error).__name__)
