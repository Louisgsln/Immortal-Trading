"""Due times and cooperative, short-lived database writer locks."""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from filelock import FileLock, Timeout

from trading_radar.config import Company
from trading_radar.http import SourceUnavailable
from trading_radar.models import utcnow
from trading_radar.nomura_session import load_session, session_path
from trading_radar.storage import Repository


def cooldown_seconds(company: Company, failures: int) -> int:
    failures = max(0, failures)
    return max(company.scan_interval, min(3600, company.scan_interval * 2 ** min(failures, 4)))


def due_at(company: Company, state: dict) -> datetime:
    attempts = [state.get("last_success"), state.get("last_failure")]
    last = max((datetime.fromisoformat(value) for value in attempts if value), default=None)
    if last is None:
        return datetime.min.replace(tzinfo=utcnow().tzinfo)
    # Failure backoff also applies before the first successful collection. Never
    # shorten a configured interval longer than the one-hour backoff cap.
    cooldown = cooldown_seconds(company, state.get("consecutive_failures", 0))
    due = last + timedelta(seconds=cooldown)
    if company.ats == "nomura" and state.get("consecutive_failures", 0) > 0:
        # A newly validated local session permits one recovery attempt. A new
        # failure is later than this verification and restores normal backoff.
        path = session_path()
        if path:
            try:
                verified = load_session(path).verified_at
                if verified > last:
                    return min(due, verified)
            except SourceUnavailable:
                pass
    return due


def scan_lock(repo: Repository) -> FileLock:
    return FileLock(repo.lock_path.removesuffix(".lock") + ".scan.lock", timeout=0)


@asynccontextmanager
async def writer_lock(repo: Repository):
    lock = FileLock(repo.lock_path, timeout=0)
    deadline = time.monotonic() + 30
    while True:
        try:
            lock.acquire()
            break
        except Timeout:
            if time.monotonic() >= deadline:
                raise
            await asyncio.sleep(0.05)
    try:
        yield
    finally:
        lock.release()
