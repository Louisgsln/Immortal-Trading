"""Install a persistent, explicitly paired Remote Desktop Commander device on Ubuntu."""

import argparse
import fcntl
import json
import os
import pwd
import re
import signal
import stat
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

VERSION = "0.2.52"
PACKAGE = "@wonderwhy-er/desktop-commander"
INTEGRITY = (
    "sha512-VNeKfaBR6TN/8MlP/ziTpjNEeHrGOFmmzQjrwzr52kQalBJoNNISWwaSQElPFc6+"
    "I17NOOM354KbSdS/aDrqGA=="
)
SERVICE = "immortal-trading-remote.service"
MARKER = "# Managed by Immortal-Trading cloud_remote_access.py\n"
UNIT = Path("/etc/systemd/system") / SERVICE
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("Repertoire prive incompatible : installation interrompue.")
    path.chmod(0o700)


def write_private(path: Path, content: str) -> None:
    descriptor, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def root_directory() -> Path:
    return Path.home() / ".local/share/immortal-trading-remote"


def systemd_string(value: str | Path) -> str:
    value = str(value)
    if any(ord(char) < 32 for char in value):
        raise ValueError("Chemin systemd invalide.")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def service_unit(project: Path, root: Path, username: str) -> str:
    if username != "ubuntu":
        raise ValueError("Ce parcours OVH exige l utilisateur ubuntu, sans sudo devant Python.")
    # WorkingDirectory uses a single path parser, not ExecStart's quoted argument parser.
    systemd_string(project)  # Reject control characters before writing the single-value path.
    return (
        MARKER
        + f"""[Unit]
Description=Immortal-Trading remote administration device
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User={username}
WorkingDirectory={str(project).replace("%", "%%")}
ExecStart=/usr/bin/python3 -u {systemd_string(root / "controller.py")} supervise
Restart=on-failure
RestartSec=30
TimeoutStopSec=35
KillMode=control-group
UMask=0077
PrivateTmp=true
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    )


def run(arguments: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(arguments, check=True, capture_output=True, text=True, **kwargs)


def installed_package(root: Path) -> bool:
    directory = root / "agent/node_modules/@wonderwhy-er/desktop-commander"
    try:
        manifest = json.loads((directory / "package.json").read_text())
        lock = json.loads((root / "agent/package-lock.json").read_text())
        entry = lock["packages"]["node_modules/@wonderwhy-er/desktop-commander"]
        return (
            manifest["version"] == VERSION
            and entry["version"] == VERSION
            and entry["integrity"] == INTEGRITY
            and (directory / "dist/index.js").is_file()
            and (directory / "dist/npm-scripts/remote.js").is_file()
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def service_state() -> dict[str, str]:
    try:
        result = run(
            ["systemctl", "show", SERVICE, "-p", "LoadState", "-p", "ActiveState", "-p", "MainPID"]
        )
        output = result.stdout
    except subprocess.CalledProcessError as error:
        missing = dict(
            line.split("=", 1) for line in (error.stdout or "").splitlines() if "=" in line
        )
        if missing.get("LoadState") != "not-found":
            raise
        return {"LoadState": "not-found", "ActiveState": "inactive", "MainPID": "0"}
    return dict(line.split("=", 1) for line in output.splitlines() if "=" in line)


def check_other_devices(own_pid: int = 0) -> None:
    # Inspect only this account's argument vectors; never return them or read environments.
    for directory in Path("/proc").iterdir():
        if not directory.name.isdecimal() or int(directory.name) == own_pid:
            continue
        try:
            if directory.stat().st_uid != os.getuid():
                continue
            arguments = directory.joinpath("cmdline").read_bytes().split(b"\0")
            if b"remote" in arguments and any(b"desktop-commander" in arg for arg in arguments):
                raise ValueError("Un autre agent distant est actif : conserver un seul lanceur.")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue


class PairingStatus:
    """Discard raw tool arguments/results and retain only initial pairing instructions."""

    def __init__(self, root: Path):
        self.path = root / "status.json"
        self.data = {"state": "starting", "version": VERSION}
        self.expect = ""
        self.accept_output = True
        self.save()

    def save(self) -> None:
        self.data["updated_at"] = datetime.now(UTC).isoformat()
        write_private(self.path, json.dumps(self.data, ensure_ascii=False) + "\n")

    def consume(self, raw: str) -> None:
        line = ANSI.sub("", raw).strip()
        if line.startswith("🔧 Received tool call"):
            self.accept_output = False
        if not self.accept_output:
            return
        if line == "1. Verify this device in your browser:":
            self.expect = "url"
        elif line == "2. Make sure the code matches:":
            self.expect = "code"
        elif self.expect and line:
            expected, self.expect = self.expect, ""
            if expected == "url":
                try:
                    url = urlsplit(line)
                    port = url.port
                except ValueError:
                    return
                if (
                    url.scheme == "https"
                    and url.hostname in {"mcp.desktopcommander.app", "auth.desktopcommander.app"}
                    and not url.username
                    and not url.password
                    and port in {None, 443}
                    and len(line) <= 512
                ):
                    query = parse_qsl(url.query)
                    if any(key not in {"code", "user_code"} for key, _ in query):
                        url = url._replace(query="")
                    self.data["pairing_url"] = urlunsplit(url._replace(fragment=""))
                    self.data["state"] = "awaiting_pairing"
            elif re.fullmatch(r"[A-Za-z0-9-]{4,24}", line):
                self.data["pairing_code"] = line
        elif line == "✅ Device verified":
            self.data["state"] = "connecting"
            self.data.pop("pairing_url", None)
            self.data.pop("pairing_code", None)
        elif line == "✅ Desktop Commander Remote is connected":
            self.data["state"] = "agent_connected"
            self.data.pop("pairing_url", None)
            self.data.pop("pairing_code", None)
            self.accept_output = False
        elif "Device startup failed:" in line:
            self.data["state"] = "startup_failed"
        else:
            return
        self.save()


def supervise(root: Path) -> int:
    private_directory(root)
    with (root / "agent.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not installed_package(root):
            raise ValueError("Le paquet distant ne correspond pas a la version verifiee.")
        status = PairingStatus(root)
        entrypoint = root / "agent/node_modules/@wonderwhy-er/desktop-commander/dist/index.js"
        command = ["/usr/bin/node", str(entrypoint), "remote", "--disable-no-sleep"]
        environment = dict(os.environ)
        environment.pop("DEBUG_MODE", None)
        environment.pop("MCP_SERVER_URL", None)
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=environment
        ) as child:

            def forward_signal(number, _frame):
                if child.poll() is None:
                    child.send_signal(number)

            signal.signal(signal.SIGTERM, forward_signal)
            signal.signal(signal.SIGINT, forward_signal)
            assert child.stdout is not None
            # Bound individual lines; discard continuation chunks of large tool output.
            truncated = False
            while chunk := child.stdout.readline(8192):
                complete = chunk.endswith(b"\n")
                if complete and not truncated:
                    status.consume(chunk.decode("utf-8", errors="replace"))
                truncated = not complete
            result = child.wait()
        status.data["state"] = "stopped" if result == 0 else "agent_failed"
        status.data.pop("pairing_url", None)
        status.data.pop("pairing_code", None)
        status.save()
        print("REMOTE_AGENT_EXIT=" + str(result), flush=True)
        return result if result >= 0 else 128 - result


def display_status(root: Path) -> None:
    service = service_state()
    data = {"service": service.get("ActiveState", "unknown"), "chat_access_verified": False}
    if (root / "status.json").is_file():
        saved = json.loads((root / "status.json").read_text())
        for key in ("state", "version", "pairing_url", "pairing_code", "updated_at"):
            if key in saved:
                data[key] = saved[key]
    print("ACCES_DISTANT=" + json.dumps(data, ensure_ascii=False))


def install(project: Path, root: Path) -> None:
    username = pwd.getpwuid(os.getuid()).pw_name
    if username != "ubuntu" or os.geteuid() == 0:
        raise ValueError("Executer depuis SSH en tant que ubuntu, sans sudo devant Python.")
    release = dict(
        line.split("=", 1)
        for line in Path("/etc/os-release").read_text().splitlines()
        if "=" in line
    )
    if release.get("ID", "").strip('"') != "ubuntu":
        raise ValueError("Ce parcours exige Ubuntu.")
    if not (project / "compose.cloud.yaml").is_file() or not (project / "pyproject.toml").is_file():
        raise ValueError("Le repertoire choisi ne contient pas le projet cloud.")
    if UNIT.is_symlink() or (UNIT.exists() and not UNIT.read_text().startswith(MARKER)):
        raise ValueError("Un service de meme nom existe deja : aucune modification.")
    private_directory(root)
    with (root / "setup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = service_state()
        if state.get("ActiveState") == "active":
            if not UNIT.exists() or not installed_package(root):
                raise ValueError("Service actif incompatible : installation interrompue.")
            display_status(root)
            return
        check_other_devices()
        run(["sudo", "-n", "true"])
        if state.get("ActiveState") not in {"inactive", "failed", ""}:
            raise ValueError("Le service distant est en transition : reessayer apres son arret.")
        print("PREPARATION_ACCES_DISTANT", flush=True)
        run(["sudo", "apt-get", "update"])
        run(["sudo", "apt-get", "install", "-y", "nodejs", "npm", "ripgrep"])
        version = run(["/usr/bin/node", "--version"]).stdout.strip()
        if int(version.removeprefix("v").split(".")[0]) < 22:
            raise ValueError("Node.js 22 ou plus recent est requis pour les dependances du plugin.")
        private_directory(root / "agent")
        if not installed_package(root):
            run(
                [
                    "/usr/bin/npm",
                    "install",
                    "--prefix",
                    str(root / "agent"),
                    "--save-exact",
                    "--omit=dev",
                    "--ignore-scripts",
                    "--no-audit",
                    "--no-fund",
                    "--registry=https://registry.npmjs.org",
                    f"{PACKAGE}@{VERSION}",
                ]
            )
        if not installed_package(root):
            raise ValueError("Version ou empreinte npm differente : agent non execute.")
        credentials = Path.home() / ".desktop-commander-device"
        private_directory(credentials)
        credential_file = credentials / "device.json"
        if credential_file.exists() or credential_file.is_symlink():
            info = credential_file.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError(
                    "Fichier d appairage incompatible : aucune lecture ni suppression."
                )
            credential_file.chmod(0o600)
        write_private(root / "controller.py", Path(__file__).read_text())
        unit = service_unit(project, root, username)
        # tee receives the exact text on stdin; no shell interpolation of paths or credentials.
        run(["sudo", "tee", str(UNIT)], input=unit)
        run(["sudo", "chmod", "644", str(UNIT)])
        run(["sudo", "systemd-analyze", "verify", str(UNIT)])
        run(["sudo", "systemctl", "daemon-reload"])
        run(["sudo", "systemctl", "enable", "--now", SERVICE])
        for _ in range(45):
            if (root / "status.json").is_file():
                current = json.loads((root / "status.json").read_text())
                phase = current.get("state")
                if phase not in {"starting", "awaiting_pairing"} or (
                    phase == "awaiting_pairing"
                    and current.get("pairing_url")
                    and current.get("pairing_code")
                ):
                    break
            if service_state().get("ActiveState") == "failed":
                break
            time.sleep(1)
        print("INSTALLATION_ACCES_TERMINEE", flush=True)
        display_status(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "status", "stop", "supervise"))
    arguments = parser.parse_args()
    root = root_directory()
    try:
        if arguments.action == "install":
            install(Path(os.getenv("RADAR_PROJECT_DIR", os.getcwd())).resolve(), root)
        elif arguments.action == "status":
            display_status(root)
        elif arguments.action == "stop":
            run(["sudo", "systemctl", "disable", "--now", SERVICE])
            print("ACCES_DISTANT_ARRETE")
        else:
            raise SystemExit(supervise(root))
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"Etape {error.cmd[0]} interrompue (code {error.returncode}).") from None
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
