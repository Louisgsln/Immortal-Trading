"""Small, read-only service observations; never expose Telegram control credentials."""

import json
from datetime import datetime

from trading_radar.backups import database_path
from trading_radar.config import Config
from trading_radar.digest_state import DigestState
from trading_radar.runtime_status import watcher_status


def service_observation(config: Config, now: datetime) -> dict:
    digest: dict = {"status": "unavailable"}
    try:
        path = database_path(config.settings.database_url).with_suffix(".telegram.json")
        with path.open("rb") as stream:
            raw = stream.read(32769)
        if len(raw) > 32768:
            raise ValueError("Oversized control state")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("Invalid control state")
        fields = DigestState.model_fields
        # Missing state must not silently look like the model's default preferences.
        state = DigestState.model_validate({key: value[key] for key in fields})
        digest = {
            "status": "configured",
            "enabled": state.digest_enabled,
            "time": state.digest_time,
            "last_attempt_day": state.digest_last_day,
            "time_zone": "Europe/Paris",
        }
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        pass
    try:
        watcher = watcher_status(config, now)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        watcher = {"status": "unknown", "phase": None, "at": None, "age_seconds": None}
    return {"observed_at": now.isoformat(), "watcher": watcher, "digest": digest}
