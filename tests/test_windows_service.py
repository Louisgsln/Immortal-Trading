from types import SimpleNamespace

import pytest
from filelock import FileLock

from scripts import windows_service as service


@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    database = tmp_path / "jobs.db"
    database.touch()
    config = SimpleNamespace(
        settings=SimpleNamespace(database_url=f"sqlite:///{database}", alerts_enabled=True)
    )
    monkeypatch.setattr(service, "load_config", lambda _: config)
    monkeypatch.setattr(service.TelegramNotifier, "from_env", lambda: object())
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "synthetic-secret")
    return tmp_path, config


def mode(monkeypatch, value):
    monkeypatch.setattr(service.sys, "argv", ["windows_service.py", value])


def test_backup_is_verified_before_success(environment, monkeypatch):
    root, _ = environment
    mode(monkeypatch, "backup")
    calls = []
    monkeypatch.setattr(service, "create_backup", lambda db, dest: calls.append((db, dest)))
    monkeypatch.setattr(service, "verify_backup", lambda dest: calls.append(dest))
    assert service.main() == 0
    assert calls[0][0] == root / "jobs.db"
    assert calls[0][1] == calls[1]
    assert calls[1].parent == root / "data" / "backups"


def test_failed_backup_is_not_reported_as_verified(environment, monkeypatch):
    root, _ = environment
    mode(monkeypatch, "backup")
    monkeypatch.setattr(service, "create_backup", lambda *args: None)

    def fail(_):
        raise ValueError("synthetic-secret")

    monkeypatch.setattr(service, "verify_backup", fail)
    assert service.main() == 1
    log = (root / "data/windows-service/backup.log").read_text()
    assert "Verified backup" not in log and "synthetic-secret" not in log


def test_missing_database_never_bootstraps(environment, monkeypatch):
    root, _ = environment
    mode(monkeypatch, "watch")
    (root / "jobs.db").unlink()
    assert service.main() == 1
    assert not (root / "jobs.db").exists()


def test_disabled_alerts_do_not_create_telegram_transport(environment, monkeypatch):
    _, config = environment
    mode(monkeypatch, "watch")
    config.settings.alerts_enabled = False
    monkeypatch.setattr(service.TelegramNotifier, "from_env", lambda: pytest.fail("Telegram"))

    def started(*args, **kwargs):
        raise OSError("Synthetic process unavailable")

    monkeypatch.setattr(service.runpy, "run_module", started)
    assert service.main() == 1


def test_duplicate_worker_does_not_launch(environment, monkeypatch):
    root, _ = environment
    mode(monkeypatch, "watch")
    runtime = root / "data/windows-service"
    runtime.mkdir(parents=True)
    monkeypatch.setattr(service.runpy, "run_module", lambda *a, **kw: pytest.fail("Started"))
    with FileLock(str(runtime / "watch.lock")):
        assert service.main() == 0


@pytest.mark.parametrize("exit_code", [0, 7])
def test_worker_redacts_output_and_requests_restart(environment, monkeypatch, exit_code):
    root, _ = environment
    mode(monkeypatch, "watch")

    def start(module, **kwargs):
        assert service.sys.argv == ["trading-radar", "watch"]
        assert module == "trading_radar" and kwargs == {"run_name": "__main__"}
        print("URL contains synthetic-", end="")
        print("secret")
        raise SystemExit(exit_code)

    monkeypatch.setattr(service.runpy, "run_module", start)
    assert service.main() == (exit_code or 1)
    log = (root / "data/windows-service/watch.log").read_text()
    assert "synthetic-secret" not in log and "[REDACTED]" in log
