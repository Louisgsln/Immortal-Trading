import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import trading_radar.launchers as launchers
from trading_radar.cli import app
from trading_radar.runtime_status import WatcherPulse, watcher_status


@pytest.mark.parametrize(
    "argv,kind,mode",
    [
        (["python", "-m", "trading_radar", "watch"], "worker", "watch"),
        (["/venv/bin/python3.12", "/venv/bin/trading-radar", "telegram"], "worker", "telegram"),
        (["uv", "run", "trading-radar", "watch"], "launcher", "watch"),
        (
            ["python.exe", '"C:\\My Project\\scripts\\windows_entry.py"', "dashboard"],
            "worker",
            "dashboard",
        ),
    ],
)
def test_exact_known_entry_points(argv, kind, mode):
    item = launchers.classify(argv, "/project")
    assert item["kind"] == kind and item["mode"] == mode
    if "windows_entry.py" in " ".join(argv):
        assert item["config_directory"] == "C:\\My Project\\config"


@pytest.mark.parametrize(
    "argv",
    [
        ["python", "-c", "print('trading-radar watch')"],
        ["python", "my_script.py", "watch"],
        ["bash", "-c", "trading-radar watch"],
        ["python", "-m", "other_package", "watch"],
        ["trading-radar", "--help"],
    ],
)
def test_mentions_and_other_scripts_do_not_become_workers(argv):
    assert launchers.classify(argv) is None


def worker(pid, parent=1, mode="watch", config="/project/config", kind="worker"):
    return {
        "pid": pid,
        "parent_pid": parent,
        "mode": mode,
        "config_directory": config,
        "kind": kind,
        "executable": "python",
    }


def inventory(processes, tasks=None):
    return {
        "status": "ok",
        "processes": processes,
        "scheduled_tasks": tasks or [],
        "tasks_status": "not_supported",
        "unreadable": 0,
    }


def test_duplicates_separate_configurations_and_wrapper_trees(monkeypatch):
    processes = [
        worker(101),
        worker(102, parent=101),
        worker(201),
        worker(301, config="/other/config"),
        worker(401, kind="launcher"),
        worker(501, mode="dashboard"),
        worker(502, mode="dashboard"),
    ]
    monkeypatch.setattr(launchers, "linux_inventory", lambda: inventory(processes))
    result = launchers.launcher_report()
    assert result["read_only"]
    assert result["issues"] == [
        {
            "code": "duplicate_workers",
            "mode": "watch",
            "config_directory": "/project/config",
            "pids": [101, 201],
        }
    ]


def test_windows_unknown_configurations_and_task_aliases_require_review(monkeypatch):
    monkeypatch.setattr(launchers, "sys", SimpleNamespace(platform="win32"))
    tasks = [
        {"name": "Immortal-Trading-watch", "mode": "watch", "state": "Running"},
        {"name": "Immortal-Trading-old-watch", "mode": "watch", "state": "Ready"},
    ]
    monkeypatch.setattr(
        launchers,
        "windows_inventory",
        lambda: inventory([worker(1, config=None), worker(2, config=None)], tasks),
    )
    result = launchers.launcher_report()
    assert [item["code"] for item in result["issues"]] == [
        "multiple_workers_unverified",
        "multiple_scheduled_launchers",
    ]


def test_linux_probe_omits_command_lines_and_credential_arguments(tmp_path, monkeypatch):
    pid = tmp_path / "123"
    pid.mkdir()
    (pid / "cmdline").write_bytes(b"python\0-m\0trading_radar\0watch\0--token\0private-secret\0")
    (pid / "status").write_text("Name: python\nPPid: 10\n")
    monkeypatch.setattr(launchers.os, "readlink", lambda _: "/project")
    result = launchers.linux_inventory(tmp_path)
    assert result["status"] == "ok" and result["processes"][0]["pid"] == 123
    assert "private-secret" not in json.dumps(result)
    assert "CommandLine" not in json.dumps(result)


def test_windows_probe_is_read_only_and_drops_sensitive_arguments(monkeypatch):
    payload = {
        "processes": [
            {
                "ProcessId": 123,
                "ParentProcessId": 10,
                "CommandLine": 'python.exe "C:\\Project\\scripts\\windows_entry.py" telegram --token private-secret',
            }
        ],
        "tasks": [{"TaskName": "Immortal-Trading-telegram", "State": "Running"}],
    }

    def run(command, **kwargs):
        assert command[:3] == ["powershell.exe", "-NoProfile", "-NonInteractive"]
        assert "Get-CimInstance" in command[-1] and "Get-ScheduledTask" in command[-1]
        assert kwargs["timeout"] == 15 and kwargs["check"]
        return SimpleNamespace(stdout=json.dumps(payload))

    monkeypatch.setattr(launchers.subprocess, "run", run)
    result = launchers.windows_inventory()
    assert result["processes"][0]["mode"] == "telegram"
    assert result["scheduled_tasks"][0]["state"] == "Running"
    assert "private-secret" not in json.dumps(result)


def test_unavailable_probe_is_not_reported_as_no_workers(monkeypatch):
    def fail():
        raise OSError("private-error")

    monkeypatch.setattr(launchers, "linux_inventory", fail)
    report = launchers.launcher_report()
    assert report["status"] == "unavailable"
    assert "private-error" not in json.dumps(report)


def test_runtime_cli_reads_no_business_database_or_network(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(launchers, "linux_inventory", lambda: inventory([]))
    monkeypatch.setattr(
        "trading_radar.http.HTTPClient.__init__", lambda *a, **kw: pytest.fail("Network")
    )
    result = CliRunner().invoke(app, ["runtime"])
    assert result.exit_code == 0 and json.loads(result.stdout)["read_only"]
    assert not list(tmp_path.iterdir())


def test_watcher_pulse_identifies_process_without_claiming_uniqueness(config, tmp_path):
    config.settings.database_url = "sqlite:///" + str(tmp_path / "jobs.db")
    pulse = WatcherPulse(config)
    pulse.publish()
    value = json.loads(pulse.path.read_text())
    assert value["pid"] > 0 and value["instance"]
    assert watcher_status(config)["status"] == "active"
