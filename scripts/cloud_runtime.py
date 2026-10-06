"""Cloud service entry point: existing database, explicit cutover, offline backups."""

import argparse
import json
import os
import signal
import sys
import threading
from datetime import UTC, datetime
from uuid import uuid4

from filelock import FileLock

from trading_radar.backups import create_backup, database_path, verify_backup
from trading_radar.config import Config, load_config
from trading_radar.health import check_health
from trading_radar.notifications import TelegramNotifier
from trading_radar.runtime_status import atomic_json, watcher_status


def preflight(config: Config, mode: str = "watch") -> dict:
    """Check without creating/migrating a database or contacting Telegram."""
    health = check_health(config)
    if health["database"]["status"] != "ok":
        raise ValueError("Existing compatible database required")
    if mode in {"watch", "telegram"}:
        if not any(company.enabled for company in config.companies.values()):
            raise ValueError("Enabled sources required")
        if mode == "telegram" and not config.settings.telegram_control_enabled:
            raise ValueError("Telegram listener is disabled")
        if mode == "telegram" or config.settings.alerts_enabled:
            TelegramNotifier.from_env()  # Local syntax check only; no transport.
    return {
        "database": "ok",
        "source_health": health["status"],
        "alerts_enabled": config.settings.alerts_enabled,
        "cutover_confirmed": os.environ.get("RADAR_CUTOVER_CONFIRMED") == "true",
    }


def backup_once(config: Config) -> dict:
    preflight(config, "backups")
    database = database_path(config.settings.database_url)
    destination = (
        database.parent
        / "backups"
        / ("cloud-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex + ".zip")
    )
    manifest = create_backup(database, destination)
    if verify_backup(destination) != manifest:
        raise ValueError("Backup verification mismatch")
    return {"status": "ok", "backup": destination.name, "created_at": manifest["created_at"]}


def backup_loop(config: Config, stop: threading.Event) -> None:
    database = database_path(config.settings.database_url)
    status_path = database.with_suffix(".cloud-backups.json")
    with FileLock(str(status_path) + ".lock", timeout=0):
        while not stop.is_set():
            try:
                report = backup_once(config)
                delay = 86400
            except Exception as error:
                # Exceptions can contain paths or secrets: expose only their class.
                report = {"status": "failed", "error_type": type(error).__name__}
                delay = 600
            report["observed_at"] = datetime.now(UTC).isoformat()
            atomic_json(status_path, report)
            print(json.dumps(report), flush=True)
            stop.wait(delay)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("preflight", "watch", "telegram", "backups", "backup-once", "check-live")
    )
    args = parser.parse_args()
    try:
        config = load_config()
        if args.mode == "check-live":
            health, pulse = check_health(config), watcher_status(config)
            print(json.dumps({"health": health["status"], "watcher": pulse["status"]}))
            return 0 if health["ready"] and pulse["status"] == "active" else 1
        report = preflight(config, "watch" if args.mode == "preflight" else args.mode)
        if args.mode == "preflight":
            print(json.dumps(report))
        elif args.mode in {"watch", "telegram"}:
            if not report["cutover_confirmed"]:
                raise ValueError("Confirm previous workers have stopped before cutover")
            os.execv(sys.executable, [sys.executable, "-m", "trading_radar", args.mode])
        elif args.mode == "backup-once":
            print(json.dumps(backup_once(config)))
        else:
            stop = threading.Event()
            for value in (signal.SIGTERM, signal.SIGINT):
                signal.signal(value, lambda *_: stop.set())
            backup_loop(config, stop)
        return 0
    except Exception as error:
        print(
            json.dumps({"status": "blocked", "error_type": type(error).__name__}), file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
