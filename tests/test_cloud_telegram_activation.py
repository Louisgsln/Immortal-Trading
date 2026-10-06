import io
import json
import os
import stat
import subprocess
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import pytest
from filelock import FileLock, Timeout

from scripts import cloud_telegram_activation as activation

# Reuse the real SQLite, delivered alert and private command-state fixture.
from tests.test_cloud_telegram_preflight import preparation as preactivation_fixture
from trading_radar.backups import verify_backup
from trading_radar.runtime_status import pulse_path

ENVIRONMENT = (
    b"# private credentials: preserve byte for byte\r\n"
    b"TELEGRAM_BOT_TOKEN='123:fixture_$()_`secret`'\r\n"
    b"TELEGRAM_CHAT_ID=456\r\n"
    b"ALERTS_ENABLED=false\r\n"
    b"TELEGRAM_CONTROL_ENABLED=false\r\n"
    b"TELEGRAM_INCIDENT_NOTICES_ENABLED=false\r\n"
    b"NOMURA_SESSION_FILE=/app/data/nomura-session/session.json\r\n"
)


@pytest.fixture
def preparation(config, repo, job, monkeypatch):
    return preactivation_fixture.__wrapped__(config, repo, job, monkeypatch)


def execute(code):
    with redirect_stdout(io.StringIO()) as output:
        exec(compile(code, "activation-container-check", "exec"), {})
    return json.loads(output.getvalue())


def test_enable_changes_only_two_assignments_and_keeps_credentials_and_optional_settings():
    expected = ENVIRONMENT.replace(b"ENABLED=false", b"ENABLED=true", 2)
    assert activation.enabled_environment(ENVIRONMENT) == expected


@pytest.mark.parametrize(
    "content",
    [
        ENVIRONMENT + b"ALERTS_ENABLED=false\n",
        ENVIRONMENT + b"export TELEGRAM_CONTROL_ENABLED=false\n",
        ENVIRONMENT.replace(b"ALERTS_ENABLED=false", b"ALERTS_ENABLED=true"),
        ENVIRONMENT.replace(b"TELEGRAM_CONTROL_ENABLED=false", b""),
    ],
)
def test_ambiguous_missing_or_already_active_flags_are_refused(content):
    with pytest.raises(ValueError):
        activation.enabled_environment(content)


def test_private_replacement_is_atomic_and_has_restricted_permissions(tmp_path):
    path = tmp_path / ".env.cloud"
    path.write_bytes(b"old")
    activation.replace_private(path, ENVIRONMENT)
    assert path.read_bytes() == ENVIRONMENT
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(tmp_path.glob(".env.cloud.write-*")) == []


def test_frozen_backup_and_live_check_preserve_sent_alert_and_command_state(
    preparation, monkeypatch
):
    before = preparation.state_path.read_bytes()
    evidence = execute(activation.FROZEN_CHECK)
    assert evidence["sent_preserves"] == 1
    assert verify_backup(preparation.path.parent / "backups" / evidence["backup"]["backup"])
    snapshot = Path(evidence["snapshot"])
    assert (snapshot.parent / "telegram-state.json").read_bytes() == before
    assert preparation.state_path.read_bytes() == before
    assert stat.S_IMODE(snapshot.stat().st_mode) == 0o600
    assert stat.S_IMODE(snapshot.parent.stat().st_mode) == 0o700
    preparation.config.settings.alerts_enabled = True
    preparation.config.settings.telegram_control_enabled = True
    monkeypatch.setenv("RADAR_ACTIVATION_SNAPSHOT", str(snapshot))
    report = execute(activation.LIVE_CHECK)
    assert report["sent_preserves"] == 1
    assert report["alertes_par_etat"] == {"sent": 1}
    assert preparation.state_path.read_bytes() == before
    with preparation.repo.db:
        preparation.repo.db.execute(
            "UPDATE alerts SET status='pending' WHERE id=?", (preparation.identifier,)
        )
    with pytest.raises(SystemExit, match="Historique"):
        execute(activation.LIVE_CHECK)


@pytest.mark.parametrize("status", ["pending", "sending", "unknown"])
def test_last_queue_check_blocks_without_creating_backup_or_modifying_state(preparation, status):
    before = preparation.state_path.read_bytes()
    with preparation.repo.db:
        preparation.repo.db.execute(
            "UPDATE alerts SET status=? WHERE id=?", (status, preparation.identifier)
        )
    with pytest.raises(SystemExit, match="file d alertes"):
        execute(activation.FROZEN_CHECK)
    assert list(preparation.path.parent.glob("telegram-activation-*")) == []
    assert not (preparation.path.parent / "backups").exists()
    assert preparation.state_path.read_bytes() == before


def test_still_running_watcher_blocks_the_frozen_check(preparation):
    with FileLock(str(pulse_path(preparation.config)) + ".lock", timeout=0):
        with pytest.raises(Timeout):
            execute(activation.FROZEN_CHECK)
    assert not (preparation.path.parent / "backups").exists()


def test_wrong_destination_blocks_without_rewriting_command_cursor(preparation):
    preparation.state_path.write_text('{"binding":"other","offset":123}')
    before = preparation.state_path.read_bytes()
    with pytest.raises(SystemExit, match="destination Telegram"):
        execute(activation.FROZEN_CHECK)
    assert preparation.state_path.read_bytes() == before


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    env_path = tmp_path / ".env.cloud"
    activation.replace_private(env_path, ENVIRONMENT)
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"sent":[[1,"old"]]}')
    # Represent live state written after a message may have been delivered.
    database = tmp_path / "jobs.db"
    database.write_bytes(b"post-send-database")
    cursor = tmp_path / "jobs.telegram.json"
    cursor.write_text('{"offset":500}')
    commands = []
    simulated = SimpleNamespace(fail_at=None, commands=commands, env=env_path)

    def compose(*args, code=None, capture=False):
        commands.append(args)
        if args == simulated.fail_at:
            raise subprocess.CalledProcessError(1, "docker", stderr="private_token_error")
        if code == activation.FROZEN_CHECK:
            return json.dumps({"snapshot": str(baseline), "backup": {"status": "ok"}})
        if code == activation.LIVE_CHECK:
            return json.dumps({"watcher": "active", "sent_preserves": 1})
        return ""

    monkeypatch.setattr(activation, "compose", compose)
    monkeypatch.setattr(activation, "inventory", lambda counts: {"counts": counts})
    monkeypatch.setattr(activation.subprocess, "run", lambda *a, **k: None)
    previous = Path.cwd()
    yield SimpleNamespace(
        project=tmp_path, env=env_path, database=database, cursor=cursor, simulated=simulated
    )
    os.chdir(previous)


def test_activation_freezes_checks_backups_then_restarts_one_service_per_role(deployment, capsys):
    assert activation.activate(deployment.project) == 0
    assert deployment.env.read_bytes() == activation.enabled_environment(ENVIRONMENT)
    calls = deployment.simulated.commands
    assert calls[0] == ("stop", "radar")
    assert calls[1][:2] == ("run", "--rm")
    assert calls[2] == ("config", "--quiet")
    assert calls[3] == ("up", "-d", "--no-deps", "radar")
    assert calls[4] == ("--profile", "telegram", "up", "-d", "--no-deps", "telegram")
    assert deployment.database.read_bytes() == b"post-send-database"
    assert deployment.cursor.read_text() == '{"offset":500}'
    assert "fixture_$()_`secret`" not in capsys.readouterr().out
    saved = next(deployment.project.glob(".env.cloud.activation-*/before"))
    assert saved.read_bytes() == ENVIRONMENT
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600


@pytest.mark.parametrize("stage", ["telegram_start", "after_possible_sends"])
def test_failure_rolls_back_flags_but_keeps_live_delivery_and_cursor_state(
    deployment, capsys, stage
):
    deployment.simulated.fail_at = (
        ("--profile", "telegram", "up", "-d", "--no-deps", "telegram")
        if stage == "telegram_start"
        else (
            "exec",
            "-T",
            "-e",
            "RADAR_ACTIVATION_SNAPSHOT=" + str(deployment.project / "baseline.json"),
            "radar",
            "python",
            "-",
        )
    )
    assert activation.activate(deployment.project) == 1
    assert deployment.env.read_bytes() == ENVIRONMENT
    assert deployment.simulated.commands[-2:] == [
        ("--profile", "telegram", "stop", "telegram"),
        ("up", "-d", "--no-deps", "radar"),
    ]
    assert deployment.database.read_bytes() == b"post-send-database"
    assert deployment.cursor.read_text() == '{"offset":500}'
    output = capsys.readouterr().out
    assert "REPRISE_ENVOIS_DESACTIVES=true" in output
    assert "private_token_error" not in output


def test_failed_audit_never_stops_or_changes_services(deployment, monkeypatch):
    def rejected(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "audit")

    monkeypatch.setattr(activation.subprocess, "run", rejected)
    assert activation.activate(deployment.project) == 1
    assert deployment.simulated.commands == []
    assert deployment.env.read_bytes() == ENVIRONMENT


def test_competing_activation_is_refused_without_modifying_services(deployment):
    with (deployment.project / ".cloud-telegram-activation.lock").open("a") as lock:
        activation.fcntl.flock(lock, activation.fcntl.LOCK_EX | activation.fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            activation.activate(deployment.project)
    assert deployment.simulated.commands == []
    assert deployment.env.read_bytes() == ENVIRONMENT


def test_failure_does_not_overwrite_concurrent_environment_changes(deployment, monkeypatch, capsys):
    original = activation.compose
    concurrent = activation.enabled_environment(ENVIRONMENT) + b"LOG_LEVEL=DEBUG\n"

    def compose(*args, **kwargs):
        if args == ("--profile", "telegram", "up", "-d", "--no-deps", "telegram"):
            deployment.env.write_bytes(concurrent)
            raise ValueError("simulated failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(activation, "compose", compose)
    assert activation.activate(deployment.project) == 1
    assert deployment.env.read_bytes() == concurrent
    assert deployment.simulated.commands[-1] == ("--profile", "telegram", "stop", "telegram")
    output = capsys.readouterr().out
    assert "REPRISE_A_VERIFIER=ValueError" in output
    assert "REPRISE_ENVOIS_DESACTIVES=true" not in output
