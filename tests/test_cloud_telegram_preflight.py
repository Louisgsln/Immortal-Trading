import hashlib
import io
import json
import re
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import pytest

from trading_radar.runtime_status import WatcherPulse
from trading_radar.source_failure import failure_summary
from trading_radar.telegram_control import ControlState

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/cloud_telegram_preflight.sh"
ROOT_CHECK, TELEGRAM_CHECK = re.findall(r"<<'PY'\n(.*?)\nPY", SCRIPT.read_text(), re.S)


@pytest.fixture
def preparation(config, repo, job, monkeypatch):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    config.settings.alerts_enabled = False
    config.settings.telegram_control_enabled = False
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
    identifier = repo.pending()[0]["id"]
    repo.set_alert(identifier, "sending")
    repo.set_alert(identifier, "sent")
    WatcherPulse(config).publish("waiting")
    path = Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    state_path = path.with_suffix(".telegram.json")
    binding = hashlib.sha256(b"123:456").hexdigest()
    state_path.write_text(ControlState(binding=binding, offset=42).model_dump_json())
    for key, value in {
        "RADAR_LANCEURS_OK": "true",
        "RADAR_CUTOVER_CONFIRMED": "true",
        "TELEGRAM_BOT_TOKEN": "123:fixture_private_token",
        "TELEGRAM_CHAT_ID": "456",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("NOMURA_SESSION_FILE", raising=False)
    responses = {
        "getMe": {"id": 123, "is_bot": True, "username": "FixtureBot"},
        "getChat": {"id": 456, "type": "private"},
        "getWebhookInfo": {"url": "", "pending_update_count": 1},
    }
    methods = []

    async def api(notifier, method, payload):
        assert method in responses
        methods.append(method)
        return responses[method]

    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected network call or message")

    monkeypatch.setattr("trading_radar.config.load_config", lambda: config)
    monkeypatch.setattr("trading_radar.telegram_control.api", api)
    monkeypatch.setattr("httpx.AsyncClient", forbidden)
    monkeypatch.setattr("trading_radar.notifications.TelegramNotifier.send_text", forbidden)
    return SimpleNamespace(
        config=config,
        repo=repo,
        identifier=identifier,
        path=path,
        state_path=state_path,
        binding=binding,
        responses=responses,
        methods=methods,
    )


def inspect(preparation, expected):
    database_before = preparation.path.read_bytes()
    state_before = preparation.state_path.read_bytes() if preparation.state_path.exists() else None
    with redirect_stdout(io.StringIO()) as output, pytest.raises(SystemExit) as stopped:
        exec(compile(TELEGRAM_CHECK, str(SCRIPT), "exec"), {})
    text = output.getvalue()
    assert "fixture_private_token" not in text
    assert "private_webhook_token" not in text
    assert stopped.value.code == (0 if expected else 1)
    assert preparation.path.read_bytes() == database_before
    assert (
        preparation.state_path.read_bytes() if preparation.state_path.exists() else None
    ) == state_before
    rows = {
        name: json.loads(value)
        for name, value in (line.split("=", 1) for line in text.splitlines())
    }
    assert rows["PREACTIVATION"]["prete"] is expected
    assert rows["PREACTIVATION"]["envois_actifs"] is False
    assert rows["PREACTIVATION"]["controle_actif"] is False
    return rows


def test_clean_queue_checks_identity_without_sending_or_consuming_updates(preparation):
    rows = inspect(preparation, True)
    assert rows["ALERTES_PAR_ETAT"] == {"sent": 1}
    assert rows["ETAT_TELEGRAM"]["offset"] == 42
    assert set(preparation.methods) == {"getMe", "getChat", "getWebhookInfo"}


@pytest.mark.parametrize("status", ["pending", "sending", "unknown"])
def test_pending_or_uncertain_alerts_block_preparation(preparation, status):
    with preparation.repo.db:
        preparation.repo.db.execute(
            "UPDATE alerts SET status=? WHERE id=?", (status, preparation.identifier)
        )
    assert "alertes_a_revoir" in inspect(preparation, False)["PREACTIVATION"]["blocages"]


def test_webhook_is_detected_without_printing_its_url(preparation):
    preparation.responses["getWebhookInfo"]["url"] = "https://example.com/private_webhook_token"
    rows = inspect(preparation, False)
    assert rows["API_TELEGRAM"]["sans_webhook"] is False


def test_state_for_another_destination_is_preserved_and_blocks_preparation(preparation):
    preparation.state_path.write_text(
        ControlState(binding="different", offset=42).model_dump_json()
    )
    rows = inspect(preparation, False)
    assert rows["ETAT_TELEGRAM"]["compatible"] is False


@pytest.mark.parametrize("offset", [None, 0])
def test_backlog_without_a_restored_cursor_blocks_preparation(preparation, offset):
    if offset is None:
        preparation.state_path.unlink()
    else:
        preparation.state_path.write_text(
            ControlState(binding=preparation.binding, offset=offset).model_dump_json()
        )
    assert "curseur_telegram_a_verifier" in inspect(preparation, False)["PREACTIVATION"]["blocages"]


def test_first_listener_can_be_prepared_when_no_updates_are_waiting(preparation):
    preparation.state_path.unlink()
    preparation.responses["getWebhookInfo"]["pending_update_count"] = 0
    inspect(preparation, True)


def test_known_competing_workers_block_preparation(preparation, monkeypatch):
    monkeypatch.setenv("RADAR_LANCEURS_OK", "false")
    assert "lanceurs_a_verifier" in inspect(preparation, False)["PREACTIVATION"]["blocages"]


def test_invalid_state_does_not_leak_its_contents(preparation):
    preparation.state_path.write_text('{"fixture_private_token": "invalid"}')
    assert (
        "etat_ou_api_telegram_indisponible"
        in inspect(preparation, False)["PREACTIVATION"]["blocages"]
    )


def test_nonprivate_chat_blocks_control_preparation(preparation):
    preparation.responses["getChat"]["type"] = "group"
    assert inspect(preparation, False)["API_TELEGRAM"]["chat_prive_valide"] is False


@pytest.mark.parametrize("worker_count,ready", [(1, True), (2, False)])
def test_host_inventory_and_failure_logs_are_sanitized(monkeypatch, worker_count, ready):
    inventory = {
        "status": "ok",
        "processes": [{"kind": "worker", "mode": "watch"}] * worker_count,
        "issues": [],
    }
    logs = json.dumps(
        {
            "event": "source_failed",
            "source": "fixture",
            "timestamp": "2026-10-06T09:00:00Z",
            "error": "HTTP 403 https://example.com/fixture_private_token",
        }
    )
    monkeypatch.setattr(
        "runpy.run_path",
        lambda path: (
            {"launcher_report": lambda: inventory}
            if path.endswith("launchers.py")
            else {"failure_summary": failure_summary}
        ),
    )
    monkeypatch.setattr(
        "subprocess.run", lambda *args, **kwargs: SimpleNamespace(stdout=logs, stderr="")
    )
    with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as errors:
        exec(compile(ROOT_CHECK, str(SCRIPT), "exec"), {})
    assert output.getvalue().strip() == str(ready).lower()
    assert "fixture_private_token" not in errors.getvalue()
    assert "https://example.com" not in errors.getvalue()
    failures = json.loads(errors.getvalue().split("ECHECS_RECENTS=", 1)[1])
    assert failures["fixture"]["http_status"] == 403
