import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import cloud_remote_access as remote


def installed_fixture(root, integrity=remote.INTEGRITY):
    package = root / "agent/node_modules/@wonderwhy-er/desktop-commander"
    package.joinpath("dist/npm-scripts").mkdir(parents=True)
    package.joinpath("dist/index.js").write_text("// fixture\n")
    package.joinpath("dist/npm-scripts/remote.js").write_text("// fixture\n")
    package.joinpath("package.json").write_text(json.dumps({"version": remote.VERSION}))
    root.joinpath("agent/package-lock.json").write_text(
        json.dumps(
            {
                "packages": {
                    "node_modules/@wonderwhy-er/desktop-commander": {
                        "version": remote.VERSION,
                        "integrity": integrity,
                    }
                }
            }
        )
    )


def paired_lines():
    return [
        "   1. Verify this device in your browser:",
        "      https://mcp.desktopcommander.app/device/verify?user_code=ABCD-1234",
        "   2. Make sure the code matches:",
        "      ABCD-1234",
    ]


def test_pairing_status_keeps_only_user_instructions_and_private_permissions(tmp_path):
    status = remote.PairingStatus(tmp_path)
    for line in paired_lines():
        status.consume(line)
    status.consume('{"refresh_token":"fixture_private_token"}')
    saved = json.loads(status.path.read_text())
    assert saved["state"] == "awaiting_pairing"
    assert saved["pairing_code"] == "ABCD-1234"
    assert "fixture_private_token" not in status.path.read_text()
    assert stat.S_IMODE(status.path.stat().st_mode) == 0o600


@pytest.mark.parametrize(
    "url",
    [
        "https://mcp.desktopcommander.app.evil.invalid/device?code=ABCD",
        "https://private_token@mcp.desktopcommander.app/device",
        "http://mcp.desktopcommander.app/device",
        "https://mcp.desktopcommander.app:444/device",
        "https://mcp.desktopcommander.app:invalid/device",
        "https://[invalid/device",
    ],
)
def test_unexpected_pairing_destination_is_never_saved(tmp_path, url):
    status = remote.PairingStatus(tmp_path)
    status.consume(paired_lines()[0])
    status.consume(url)
    assert "pairing_url" not in status.data


def test_private_query_and_fragment_are_not_kept(tmp_path):
    status = remote.PairingStatus(tmp_path)
    status.consume(paired_lines()[0])
    status.consume("https://mcp.desktopcommander.app/device?access_token=fixture_private#secret")
    assert status.data["pairing_url"] == "https://mcp.desktopcommander.app/device"


@pytest.mark.parametrize(
    "first",
    [
        "✅ Desktop Commander Remote is connected",
        '🔧 Received tool call 1: read_file {"path":".env.cloud"}',
    ],
)
def test_tool_results_cannot_change_status_or_leak_values_after_connection(tmp_path, first):
    status = remote.PairingStatus(tmp_path)
    status.consume(first)
    before = status.path.read_bytes()
    for line in paired_lines() + [
        "TELEGRAM_BOT_TOKEN=fixture_private_token",
        "✅ Tool call read_file completed:",
        "1. Verify this device in your browser:",
        "https://mcp.desktopcommander.app/device?code=PRIVATE-CONTENT",
        " - ❌ Device startup failed: fixture_private_token",
    ]:
        status.consume(line)
    assert status.path.read_bytes() == before


def test_verification_removes_pairing_code_and_is_distinct_from_chat_access(tmp_path):
    status = remote.PairingStatus(tmp_path)
    for line in paired_lines():
        status.consume(line)
    status.consume("✅ Device verified")
    assert status.data["state"] == "connecting"
    assert "pairing_code" not in status.data
    status.consume("✅ Desktop Commander Remote is connected")
    assert status.data["state"] == "agent_connected"
    assert "chat_access_verified" not in status.data


def test_startup_failure_keeps_no_private_error_text(tmp_path):
    status = remote.PairingStatus(tmp_path)
    status.consume(" - ❌ Device startup failed: fixture_private_token")
    assert status.data["state"] == "startup_failed"
    assert "fixture_private_token" not in status.path.read_text()


def test_unsafe_directories_and_units_are_refused(tmp_path):
    target = tmp_path / "actual"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        remote.private_directory(link)
    with pytest.raises(ValueError):
        remote.systemd_string("/home/ubuntu\nExecStart=unexpected")
    with pytest.raises(ValueError):
        remote.service_unit(tmp_path, target, "root")


def test_missing_unit_allows_initial_setup_but_bus_failure_remains_visible(monkeypatch):
    def missing(arguments):
        raise subprocess.CalledProcessError(1, arguments, output="LoadState=not-found\n")

    monkeypatch.setattr(remote, "run", missing)
    assert remote.service_state()["ActiveState"] == "inactive"

    def unavailable(arguments):
        raise subprocess.CalledProcessError(1, arguments, output="", stderr="bus unavailable")

    monkeypatch.setattr(remote, "run", unavailable)
    with pytest.raises(subprocess.CalledProcessError):
        remote.service_state()


def test_systemd_paths_preserve_spaces_quotes_and_percent_literals(tmp_path):
    project = tmp_path / 'project "quoted" %data'
    unit = tmp_path / remote.SERVICE
    unit.write_text(remote.service_unit(project, tmp_path, "ubuntu"))
    assert "User=ubuntu\n" in unit.read_text()
    assert '"quoted" %%data' in unit.read_text()
    # Syntax verification only: no unit is registered or started here.
    result = subprocess.run(
        ["systemd-analyze", "verify", str(unit)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def host(tmp_path, monkeypatch):
    root = tmp_path / "private"
    project = tmp_path / "project"
    project.mkdir()
    project.joinpath("pyproject.toml").write_text("# preserved\n")
    project.joinpath("compose.cloud.yaml").write_text("# preserved\n")
    project.joinpath(".env.cloud").write_text("TELEGRAM_BOT_TOKEN=fixture_private_token\n")
    home = tmp_path / "home"
    home.mkdir()
    release = tmp_path / "os-release"
    release.write_text('ID=ubuntu\nVERSION_ID="26.04"\n')
    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path == Path("/etc/os-release"):
            return original_read(release, *args, **kwargs)
        if path == project / ".env.cloud":
            pytest.fail("Remote installation must not read the Telegram configuration")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(remote.pwd, "getpwuid", lambda _: SimpleNamespace(pw_name="ubuntu"))
    monkeypatch.setattr(remote.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(remote, "UNIT", tmp_path / remote.SERVICE)
    monkeypatch.setattr(remote, "check_other_devices", lambda: None)
    monkeypatch.setattr(
        remote, "service_state", lambda: {"ActiveState": "inactive", "MainPID": "0"}
    )
    monkeypatch.setattr(remote.time, "sleep", lambda _: None)
    return root, project, home


def test_install_pins_integrity_starts_one_service_and_never_touches_application(host, monkeypatch):
    root, project, home = host
    calls = []

    def run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        if arguments[0] == "/usr/bin/npm":
            installed_fixture(root)
        elif arguments[:2] == ["sudo", "tee"]:
            remote.UNIT.write_text(kwargs["input"])
        elif arguments[-3:] == ["enable", "--now", remote.SERVICE]:
            status = remote.PairingStatus(root)
            for line in paired_lines():
                status.consume(line)
        return SimpleNamespace(stdout="v24.0.0\n" if arguments[0] == "/usr/bin/node" else "")

    monkeypatch.setattr(remote, "run", run)
    remote.install(project, root)
    npm = next(args for args, _ in calls if args[0] == "/usr/bin/npm")
    assert f"{remote.PACKAGE}@{remote.VERSION}" in npm
    assert "--ignore-scripts" in npm
    assert sum(args[-3:] == ["enable", "--now", remote.SERVICE] for args, _ in calls) == 1
    assert not any("docker" in args or "git" in args or "reboot" in args for args, _ in calls)
    assert project.joinpath("compose.cloud.yaml").read_bytes() == b"# preserved\n"
    assert stat.S_IMODE(home.joinpath(".desktop-commander-device").stat().st_mode) == 0o700
    assert stat.S_IMODE(root.joinpath("controller.py").stat().st_mode) == 0o600


def test_wrong_package_integrity_blocks_agent_and_service_creation(host, monkeypatch):
    root, project, _ = host
    calls = []

    def run(arguments, **kwargs):
        calls.append(arguments)
        if arguments[0] == "/usr/bin/npm":
            installed_fixture(root, integrity="sha512-unexpected")
        return SimpleNamespace(stdout="v24.0.0\n" if arguments[0] == "/usr/bin/node" else "")

    monkeypatch.setattr(remote, "run", run)
    with pytest.raises(ValueError, match="empreinte"):
        remote.install(project, root)
    assert not remote.UNIT.exists()
    assert not any("tee" in args or "enable" in args for args in calls)


def test_second_install_does_not_restart_or_replace_active_agent(host, monkeypatch, capsys):
    root, project, _ = host
    installed_fixture(root)
    remote.UNIT.write_text(remote.service_unit(project, root, "ubuntu"))
    status = remote.PairingStatus(root)
    status.consume("✅ Desktop Commander Remote is connected")
    monkeypatch.setattr(remote, "service_state", lambda: {"ActiveState": "active"})
    monkeypatch.setattr(remote, "run", lambda *_a, **_kw: pytest.fail("active agent mutated"))
    remote.install(project, root)
    report = json.loads(capsys.readouterr().out.split("ACCES_DISTANT=")[1])
    assert report["service"] == "active"
    assert report["state"] == "agent_connected"
    assert report["chat_access_verified"] is False


def test_unmanaged_service_is_preserved_before_any_install_command(host, monkeypatch):
    root, project, _ = host
    remote.UNIT.write_text("# foreign service\n")
    monkeypatch.setattr(remote, "run", lambda *_a, **_kw: pytest.fail("unexpected mutation"))
    with pytest.raises(ValueError, match="meme nom"):
        remote.install(project, root)
    assert remote.UNIT.read_text() == "# foreign service\n"
    assert not root.exists()


def test_other_remote_device_prevents_installation(host, monkeypatch):
    root, project, _ = host

    def competing_agent():
        raise ValueError("Un autre agent distant est actif")

    monkeypatch.setattr(remote, "check_other_devices", competing_agent)
    monkeypatch.setattr(remote, "run", lambda *_a, **_kw: pytest.fail("unexpected mutation"))
    with pytest.raises(ValueError, match="autre agent"):
        remote.install(project, root)
    assert not remote.UNIT.exists()


def test_supervisor_filters_large_output_and_forwards_shutdown_to_the_child(tmp_path):
    root = tmp_path / "private"
    installed_fixture(root)
    agent = tmp_path / "fake-agent.py"
    pid_file = tmp_path / "agent.pid"
    agent.write_text(
        "import os,signal,time\n"
        f"open({str(pid_file)!r},'w').write(str(os.getpid()))\n"
        "signal.signal(signal.SIGTERM,lambda *_: exit(0))\n"
        + "\n".join(f"print({line!r},flush=True)" for line in paired_lines())
        + "\nprint('🔧 Received tool call 1: read_file',flush=True)\n"
        "print('fixture_private_token'*3000,flush=True)\n"
        "while True: time.sleep(0.1)\n"
    )
    program = f"""
import subprocess,sys
from pathlib import Path
from scripts import cloud_remote_access as remote
original = subprocess.Popen
def child(arguments, **kwargs):
    assert arguments[0] == '/usr/bin/node'
    return original([sys.executable, {str(agent)!r}], **kwargs)
remote.subprocess.Popen = child
raise SystemExit(remote.supervise(Path({str(root)!r})))
"""
    with subprocess.Popen(
        [sys.executable, "-c", program], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as process:
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if pid_file.exists() and (root / "status.json").is_file():
                    saved = json.loads(root.joinpath("status.json").read_text())
                    if saved.get("pairing_code") == "ABCD-1234":
                        break
                time.sleep(0.02)
            else:
                pytest.fail("supervisor did not publish pairing instructions")
            child_pid = int(pid_file.read_text())
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert process.returncode == 0
    assert stdout == "REMOTE_AGENT_EXIT=0\n"
    assert not stderr
    assert "fixture_private_token" not in root.joinpath("status.json").read_text()
    assert json.loads(root.joinpath("status.json").read_text())["state"] == "stopped"
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)
