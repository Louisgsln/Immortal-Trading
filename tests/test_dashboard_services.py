import json
from datetime import UTC, datetime, timedelta

import pytest

from trading_radar.dashboard_services import service_observation

NOW = datetime(2026, 10, 9, 8, tzinfo=UTC)


def paths(config, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    return tmp_path / "jobs.watch.json", tmp_path / "jobs.telegram.json"


def test_live_signal_and_digest_preferences_are_read_only_and_private(config, tmp_path):
    watch, control = paths(config, tmp_path)
    watch.write_text(
        json.dumps(
            {
                "version": 1,
                "at": NOW.isoformat(),
                "phase": "waiting",
                "pid": 123,
                "instance": "private",
            }
        )
    )
    control.write_text(
        json.dumps(
            {
                "binding": "private-binding",
                "offset": 321,
                "digest_enabled": True,
                "digest_time": "09:00",
                "digest_not_before": 0,
                "digest_last_day": "2026-10-09",
            }
        )
    )
    before = {p: p.read_bytes() for p in (watch, control)}
    result = service_observation(config, NOW)
    assert result["watcher"]["status"] == "active"
    assert result["digest"] == {
        "status": "configured",
        "enabled": True,
        "time": "09:00",
        "last_attempt_day": "2026-10-09",
        "time_zone": "Europe/Paris",
    }
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert not any(
        secret in json.dumps(result) for secret in ("private-binding", "offset", "instance", "pid")
    )


@pytest.mark.parametrize(
    "raw",
    [
        "{bad",
        "[]",
        "{}",
        "{" * 2000,
        " " * 32769,
        '{"digest_enabled":"true"}',
        '{"digest_enabled":true,"digest_time":"25:00","digest_not_before":0,"digest_last_day":null}',
    ],
)
def test_unavailable_preferences_do_not_claim_default_schedule(config, tmp_path, raw):
    _, control = paths(config, tmp_path)
    control.write_text(raw)
    assert service_observation(config, NOW)["digest"] == {"status": "unavailable"}


def test_old_signal_and_absent_control_do_not_claim_active_service(config, tmp_path):
    watch, _ = paths(config, tmp_path)
    watch.write_text(
        json.dumps(
            {"version": 1, "at": (NOW - timedelta(minutes=2)).isoformat(), "phase": "waiting"}
        )
    )
    result = service_observation(config, NOW)
    assert result["watcher"]["status"] == "stale"
    assert result["digest"]["status"] == "unavailable"
