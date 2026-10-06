"""Deployment guards and real backup recovery; all data is synthetic and offline."""

import importlib.util
import json
import sqlite3
import threading
from pathlib import Path

import pytest

from trading_radar.backups import restore_backup, verify_backup
from trading_radar.runtime_status import WatcherPulse

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cloud_runtime", PROJECT / "scripts/cloud_runtime.py")
assert SPEC and SPEC.loader
cloud = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cloud)


@pytest.fixture
def cloud_config(config, repo):
    path = repo.db.execute("PRAGMA database_list").fetchone()[2]
    config.settings.database_url = f"sqlite:///{path}"
    config.settings.alerts_enabled = False
    return config


def test_preflight_allows_stale_sources_but_never_creates_missing_database(config, tmp_path):
    missing = tmp_path / "absent" / "jobs.db"
    config.settings.database_url = f"sqlite:///{missing}"
    with pytest.raises(ValueError, match="Existing"):
        cloud.preflight(config)
    assert not missing.parent.exists()


def test_preflight_reads_database_without_writing_or_migrating(cloud_config, repo):
    before = repo.db.iterdump()
    snapshot = list(before)
    report = cloud.preflight(cloud_config)
    assert report["database"] == "ok"
    assert report["source_health"] == "critical"  # No source has yet been collected.
    assert list(repo.db.iterdump()) == snapshot
    with repo.transaction():
        repo.db.execute("DELETE FROM schema_version")
    with pytest.raises(ValueError):
        cloud.preflight(cloud_config)
    assert repo.db.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 0


def test_preflight_validates_credentials_only_for_enabled_transports(cloud_config, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "invalid-private-token")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    cloud_config.settings.alerts_enabled = True
    with pytest.raises(ValueError):
        cloud.preflight(cloud_config)
    assert cloud.preflight(cloud_config, "backups")["database"] == "ok"
    cloud_config.settings.alerts_enabled = False
    assert cloud.preflight(cloud_config)["database"] == "ok"
    with pytest.raises(ValueError):
        cloud.preflight(cloud_config, "telegram")
    cloud_config.settings.telegram_control_enabled = True
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:synthetic")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "synthetic")
    assert cloud.preflight(cloud_config, "telegram")["database"] == "ok"


@pytest.mark.parametrize("value", [None, "false", "yes", "TRUE"])
def test_watcher_refuses_unconfirmed_cutover(cloud_config, monkeypatch, capsys, value):
    monkeypatch.setattr(cloud, "load_config", lambda: cloud_config)
    monkeypatch.setattr(cloud.sys, "argv", ["cloud_runtime.py", "watch"])
    if value is None:
        monkeypatch.delenv("RADAR_CUTOVER_CONFIRMED", raising=False)
    else:
        monkeypatch.setenv("RADAR_CUTOVER_CONFIRMED", value)
    monkeypatch.setattr(cloud.os, "execv", lambda *_: pytest.fail("Must not launch scanner"))
    assert cloud.main() == 1
    assert json.loads(capsys.readouterr().err) == {"status": "blocked", "error_type": "ValueError"}


def test_confirmed_cutover_replaces_wrapper_process(cloud_config, monkeypatch):
    calls = []
    monkeypatch.setattr(cloud, "load_config", lambda: cloud_config)
    monkeypatch.setattr(cloud.sys, "argv", ["cloud_runtime.py", "watch"])
    monkeypatch.setenv("RADAR_CUTOVER_CONFIRMED", "true")
    monkeypatch.setattr(cloud.os, "execv", lambda *args: calls.append(args))
    assert cloud.main() == 0
    assert calls == [(cloud.sys.executable, [cloud.sys.executable, "-m", "trading_radar", "watch"])]


def test_backup_keeps_tracking_and_queue_without_transport(cloud_config, repo, job, tmp_path):
    with repo.transaction():
        repo.upsert(job)
        repo.update_application(job.id, {"status": "Applied", "notes": "synthetic private notes"})
    before = list(repo.db.iterdump())
    report = cloud.backup_once(cloud_config)
    assert report["status"] == "ok"
    archive = tmp_path / "backups" / report["backup"]
    manifest = verify_backup(archive)
    destination = tmp_path / "restored" / "jobs.db"
    restore_backup(archive, destination, protected=tmp_path / "jobs.db")
    with sqlite3.connect(destination) as db:
        assert db.execute(
            "SELECT notes FROM applications WHERE job_id=?", (job.id,)
        ).fetchone() == ("synthetic private notes",)
    assert list(repo.db.iterdump()) == before
    assert manifest["tables"]["jobs"] == 1
    assert cloud.backup_once(cloud_config)["backup"] != report["backup"]


def test_backup_loop_retries_failure_without_exposing_secrets(cloud_config, monkeypatch):
    class Stop:
        def __init__(self):
            self.delays = []

        def is_set(self):
            return len(self.delays) == 2

        def wait(self, seconds):
            self.delays.append(seconds)

    calls, reports = [], []

    def backup(_):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("private-token-must-not-leak")
        return {"status": "ok", "backup": "synthetic.zip"}

    stop = Stop()
    monkeypatch.setattr(cloud, "backup_once", backup)
    monkeypatch.setattr(cloud, "atomic_json", lambda _, value: reports.append(dict(value)))
    cloud.backup_loop(cloud_config, stop)
    assert stop.delays == [600, 86400]
    assert [r["status"] for r in reports] == ["failed", "ok"]
    assert "private-token-must-not-leak" not in json.dumps(reports)


def test_stopped_backup_loop_does_not_make_snapshot(cloud_config, monkeypatch):
    stop = threading.Event()
    stop.set()
    monkeypatch.setattr(cloud, "backup_once", lambda _: pytest.fail("Already stopped"))
    cloud.backup_loop(cloud_config, stop)


def test_live_check_requires_fresh_sources_and_pulse(cloud_config, repo, monkeypatch, capsys):
    monkeypatch.setattr(cloud, "load_config", lambda: cloud_config)
    monkeypatch.setattr(cloud.sys, "argv", ["cloud_runtime.py", "check-live"])
    pulse = WatcherPulse(cloud_config)
    pulse.publish("waiting")
    assert cloud.main() == 1  # Recent pulse alone cannot prove successful collections.
    monkeypatch.setattr(cloud, "check_health", lambda _: {"status": "healthy", "ready": True})
    assert cloud.main() == 0
    pulse.publish("stopped")
    assert cloud.main() == 1
    assert "stopped" in capsys.readouterr().out
