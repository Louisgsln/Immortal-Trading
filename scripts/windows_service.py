"""Windows Task Scheduler entry point: existing SQLite, bounded logs, daily backups."""

import argparse
import io
import logging
import os
import runpy
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from filelock import FileLock, Timeout

from trading_radar.backups import create_backup, database_path, verify_backup
from trading_radar.config import load_config
from trading_radar.notifications import TelegramNotifier

ROOT = Path(__file__).resolve().parents[1]


class LogStream(io.TextIOBase):
    def __init__(self, logger):
        self.logger = logger
        self.buffered = ""

    def writable(self):
        return True

    def write(self, text):
        self.buffered += text
        while "\n" in self.buffered:
            line, self.buffered = self.buffered.split("\n", 1)
            self.record(line)
        if len(self.buffered) > 65536:
            self.flush()
        return len(text)

    def record(self, line):
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if token:
            line = line.replace(token, "[REDACTED]")
        self.logger.info("%s", line[:65536])

    def flush(self):
        if self.buffered:
            self.record(self.buffered)
            self.buffered = ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("watch", "dashboard", "backup"))
    args = parser.parse_args()
    os.chdir(ROOT)
    runtime = ROOT / "data" / "windows-service"
    runtime.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("windows-service")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = RotatingFileHandler(
        runtime / (args.mode + ".log"), maxBytes=10_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    try:
        with FileLock(str(runtime / (args.mode + ".lock")), timeout=0):
            config = load_config(ROOT / "config")
            if not database_path(config.settings.database_url).is_file():
                raise ValueError("Existing database required")
            if args.mode == "backup":
                destination = (
                    ROOT
                    / "data"
                    / "backups"
                    / ("scheduled-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + ".zip")
                )
                create_backup(database_path(config.settings.database_url), destination)
                verify_backup(destination)
                logger.info("Verified backup: %s", destination.name)
                return 0
            if args.mode == "watch":
                if config.settings.alerts_enabled:
                    TelegramNotifier.from_env()
                else:
                    logger.info("Collection active; Telegram notifications disabled")
                command = ["trading-radar", "watch"]
            else:
                command = [
                    "trading-radar",
                    "dashboard",
                    "serve",
                    "--edit-applications",
                    "--port",
                    "8765",
                ]
            logger.info("Starting %s", args.mode)
            # Run in the task's own process: stopping a task must not orphan a child watcher.
            (runtime / (args.mode + ".pid")).write_text(str(os.getpid()), encoding="ascii")
            output = LogStream(logger)
            previous_argv = sys.argv
            result = 0
            try:
                sys.argv = command
                with redirect_stdout(output), redirect_stderr(output):
                    try:
                        runpy.run_module("trading_radar", run_name="__main__")
                    except SystemExit as stopped:
                        result = stopped.code if isinstance(stopped.code, int) else 1
            finally:
                sys.argv = previous_argv
                output.flush()
            logger.info("Process stopped (exit %d)", result)
            return result or 1
    except Timeout:
        logger.info("Service already running; duplicate start ignored")
        return 0
    except Exception as error:
        logger.error(
            "Service failed (%s); inspect configuration and local state", type(error).__name__
        )
        return 1
    finally:
        handler.close()
        logger.removeHandler(handler)


if __name__ == "__main__":
    raise SystemExit(main())
