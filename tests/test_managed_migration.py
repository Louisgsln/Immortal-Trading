"""Synthetic recovery proves that a host move preserves delivery and user state."""

import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from zipfile import ZipFile

import pytest
from filelock import FileLock, Timeout

from scripts import managed_runtime as runtime
from scripts import migrate_state as migration
from trading_radar.telegram_control import ControlState
from trading_radar.telegram_heartbeat import HeartbeatState
from trading_radar.wishlist import set_wishlist, wishlist_path

TOKEN = "123:synthetic"
CHAT = "456"
BINDING = hashlib.sha256(b"123:456").hexdigest()


def tables(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        return {
            name: db.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
            for (name,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }


@pytest.fixture
def portable(config, repo, job, tmp_path):
    source = Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    config.settings.database_url = f"sqlite:///{source}"
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
    alert = repo.pending()[0]["id"]
    repo.set_alert(alert, "sending")
    repo.set_alert(alert, "unknown", "DeliveryUnknown")
    repo.update_application(
        job.id, {"status": "Applied", "notes": "synthetic private notes", "next_action": "Relancer"}
    )
    set_wishlist(config, job.id, True, actor="telegram")
    set_wishlist(config, job.id, False, actor="dashboard")
    set_wishlist(config, job.id, True, actor="telegram")
    control = ControlState(
        binding=BINDING,
        offset=98765,
        digest_enabled=True,
        digest_time="09:00",
        digest_last_day="2026-10-19",
    )
    source.with_suffix(".telegram.json").write_text(control.model_dump_json())
    source.with_suffix(".heartbeat.json").write_text(
        HeartbeatState(
            binding=BINDING, not_before=1.0, attempts={"18:00": "2026-10-19"}
        ).model_dump_json()
    )
    config_dir = tmp_path / "source-config"
    shutil.copytree(Path("config"), config_dir)
    history = source.parent / "health-history"
    history.mkdir()
    (history / "synthetic.json").write_text('{"private":"synthetic history"}')
    # Never sweep unrelated local files or secrets into the bundle.
    (source.parent / ".env").write_text("TELEGRAM_BOT_TOKEN=never-export-this")
    return source, config_dir, tmp_path / "migration.zip"


def export(portable):
    source, config, archive = portable
    migration.export(source, config, archive, source_stopped=True)
    return archive


def rewrite(archive, change):
    with ZipFile(archive) as bundle:
        files = {name: bundle.read(name) for name in bundle.namelist()}
    change(files)
    modified = archive.with_name("modified.zip")
    with ZipFile(modified, "w") as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
    return modified


def test_round_trip_keeps_every_table_history_cursor_and_configuration(portable, tmp_path):
    source, config, archive = portable
    before = tables(source)
    wishes = tables(wishlist_path(source))
    original_cursor = source.with_suffix(".telegram.json").read_bytes()
    export(portable)
    manifest = migration.verify(archive)
    target = tmp_path / "new-host"
    receipt = migration.restore(archive, target)
    assert tables(target / "data/jobs.db") == before == tables(source)
    assert tables(wishlist_path(target / "data/jobs.db")) == wishes
    assert (target / "data/jobs.telegram.json").read_bytes() == original_cursor
    assert json.loads((target / "data/jobs.telegram.json").read_bytes())["offset"] == 98765
    assert (target / "data/jobs.heartbeat.json").read_bytes() == source.with_suffix(
        ".heartbeat.json"
    ).read_bytes()
    assert (target / "data/health-history/synthetic.json").read_bytes() == (
        source.parent / "health-history/synthetic.json"
    ).read_bytes()
    assert all(
        (target / "config" / name).read_bytes() == (config / name).read_bytes()
        for name in migration.CONFIG_FILES
    )
    assert receipt["activation_id"] == manifest["id"]
    assert receipt["telegram_binding"] == BINDING
    assert receipt["archive_sha256"] == migration.digest(archive)
    assert archive.stat().st_mode & 0o777 == 0o600
    with ZipFile(archive) as bundle:
        assert not any(".env" in name for name in bundle.namelist())
        assert b"never-export-this" not in b"".join(bundle.read(name) for name in bundle.namelist())


def test_export_requires_source_shutdown_and_rejects_a_live_watcher(portable):
    source, config, archive = portable
    with pytest.raises(ValueError, match="Stop all"):
        migration.export(source, config, archive, source_stopped=False)
    with FileLock(str(source.with_suffix(".watch.json.lock"))):
        with pytest.raises(Timeout):
            export(portable)
    assert not archive.exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda files: files.update({"../../outside": b"bad"}),
        lambda files: files.update({"data/jobs.telegram.json": b"tampered"}),
        lambda files: files.pop("config/companies.yaml"),
        lambda files: files.update({"data/../outside.json": b"bad"}),
    ],
)
def test_bad_bundle_never_creates_target(portable, tmp_path, change):
    bad = rewrite(export(portable), change)
    target = tmp_path / "absent"
    with pytest.raises((ValueError, KeyError)):
        migration.restore(bad, target)
    assert not target.exists()
    assert not (tmp_path / "outside").exists()


def test_restore_never_overwrites_even_an_empty_target(portable, tmp_path):
    archive = export(portable)
    target = tmp_path / "existing"
    target.mkdir()
    with pytest.raises(ValueError, match="NEW"):
        migration.restore(archive, target)
    assert list(target.iterdir()) == []
    with pytest.raises(ValueError):
        export(portable)


def test_export_rejects_inconsistent_telegram_state_and_symlinks(portable):
    source, config, archive = portable
    pulse = source.with_suffix(".heartbeat.json")
    pulse.write_text(HeartbeatState(binding="0" * 64, not_before=0.0).model_dump_json())
    with pytest.raises(ValueError, match="destinations"):
        export(portable)
    pulse.unlink()
    settings = config / "settings.yaml"
    settings.unlink()
    settings.symlink_to(Path("config/settings.yaml").resolve())
    with pytest.raises(ValueError, match="portable"):
        export(portable)
    assert not archive.exists()


def activate_environment(monkeypatch, target, receipt):
    for name, value in {
        "DATABASE_URL": f"sqlite:///{target / 'data/jobs.db'}",
        "RADAR_ACTIVATION_ID": receipt["activation_id"],
        "RADAR_CUTOVER_CONFIRMED": "true",
        "TELEGRAM_BOT_TOKEN": TOKEN,
        "TELEGRAM_CHAT_ID": CHAT,
        "TELEGRAM_CONTROL_ENABLED": "true",
        "DASHBOARD_PUBLIC_ORIGIN": "https://synthetic.onrender.com",
        "DASHBOARD_PRIVATE_PREFIX": "/" + "p" * 43 + "/",
        "DASHBOARD_GATEWAY_SECRET": "s" * 43,
    }.items():
        monkeypatch.setenv(name, value)


def test_activation_checks_restoration_and_identity_before_starting_transports(
    portable, tmp_path, monkeypatch
):
    target = tmp_path / "target"
    receipt = migration.restore(export(portable), target)
    activate_environment(monkeypatch, target, receipt)
    runtime.validate_activation(target, runtime.os.environ)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "789")
    with pytest.raises(ValueError, match="another bot"):
        runtime.validate_activation(target, runtime.os.environ)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT)
    monkeypatch.setenv("RADAR_ACTIVATION_ID", "wrong-restore")
    with pytest.raises(ValueError, match="explicit cutover"):
        runtime.validate_activation(target, runtime.os.environ)


def test_runtime_defaults_to_inert_standby_and_rejects_accidental_active_mode(
    tmp_path, monkeypatch
):
    mode, _, port = runtime.settings({})
    assert mode == "standby" and port == 10000
    root = tmp_path / "state"
    monkeypatch.setenv("RADAR_STATE_ROOT", str(root))
    monkeypatch.setenv("RADAR_MODE", "active")
    monkeypatch.setattr(runtime.sys, "argv", ["managed_runtime.py"])
    monkeypatch.setattr(runtime, "serve", lambda *_: pytest.fail("No transport without restore"))
    assert runtime.main() == 1
    assert not root.exists()


@pytest.mark.parametrize("role", ["dashboard", "backups", "gateway"])
def test_children_without_notification_responsibility_receive_no_telegram_credentials(
    role, tmp_path
):
    env = {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": CHAT, "ALERTS_ENABLED": "true"}
    child = runtime.child_environment(env, tmp_path, role)
    assert "TELEGRAM_BOT_TOKEN" not in child and "TELEGRAM_CHAT_ID" not in child
    assert child["ALERTS_ENABLED"] == "false"
    assert child["TELEGRAM_CONTROL_ENABLED"] == "false"
    assert env["TELEGRAM_BOT_TOKEN"] == TOKEN


def test_standby_gateway_never_proxies_dashboard():
    config = runtime.gateway_config("standby", 10000)
    assert "127.0.0.1:8766" in config
    assert "127.0.0.1:8765" not in config
    assert 'respond "Not found" 404' in config


def test_active_gateway_preserves_origin_and_overwrites_internal_credentials():
    access = runtime.PrivateDashboardAccess(
        "https://synthetic.onrender.com", "/" + "p" * 43 + "/", "s" * 43
    )
    config = runtime.gateway_config("active", 10000, access)
    assert "header_up Host 127.0.0.1:8765" in config
    assert "header_up X-Radar-Gateway " + access.gateway_secret in config
    assert "header_up -Authorization" in config
    assert "header_up -Origin" not in config
