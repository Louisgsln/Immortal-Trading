"""Docker integration check: no network, credentials, live data or Telegram delivery."""

import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4


def main(image: str) -> None:
    name = "radar-managed-smoke-" + uuid4().hex
    volume = name + "-data"

    def docker(*args, check=True, timeout=60, input_text=None):
        return subprocess.run(
            ["docker", *args],
            check=check,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text,
        )

    options = [
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--mount",
        f"type=volume,src={volume},dst=/app/data",
    ]
    docker("volume", "create", volume)
    try:
        docker("run", "--detach", "--name", name, *options, image)
        health = None
        for _ in range(30):
            response = docker(
                "exec",
                name,
                "python",
                "-c",
                "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:10000/healthz',timeout=2).read().decode())",
                check=False,
            )
            if response.returncode == 0:
                health = json.loads(response.stdout)
                break
            time.sleep(1)
        assert health == {"mode": "standby", "processes_alive": True, "watcher": "disabled"}, (
            "Standby health failed"
        )
        docker(
            "exec",
            name,
            "python",
            "-c",
            "from pathlib import Path; assert not list(Path('/app/data').rglob('*.db')); Path('/app/data/persistence-test').write_text('synthetic')",
        )
        duplicate = docker("run", "--rm", *options, image, check=False, timeout=20)
        assert duplicate.returncode == 1 and '"error_type": "Timeout"' in duplicate.stderr, (
            "Shared volume did not exclude duplicate service"
        )
        docker("stop", "--time", "40", name)
        assert docker("inspect", "--format", "{{.State.ExitCode}}", name).stdout.strip() == "0", (
            "Service did not stop cleanly"
        )
        blocked = docker(
            "run", "--rm", *options, "--env", "RADAR_MODE=active", image, check=False, timeout=20
        )
        assert blocked.returncode == 1 and '"status": "blocked"' in blocked.stderr, (
            "Unrestored service was not blocked"
        )
        docker("start", name)
        docker(
            "exec",
            name,
            "python",
            "-c",
            "from pathlib import Path; assert Path('/app/data/persistence-test').read_text()=='synthetic'; assert not list(Path('/app/data').rglob('*.db'))",
        )
        assert (
            docker("inspect", "--format", "{{.Config.User}}", name).stdout.strip() == "10001:10001"
        )
        gateway = docker(
            "exec",
            "--interactive",
            name,
            "python",
            "-",
            input_text=Path(__file__).with_name("smoke_managed_gateway.py").read_text(),
        )
        assert json.loads(gateway.stdout)["sites_snapshot_compatible"] is True
        print(
            json.dumps(
                {
                    "status": "ok",
                    "standby": True,
                    "duplicate_blocked": True,
                    "unrestored_activation_blocked": True,
                    "persistent_restart": True,
                    "non_root": True,
                    "network": "none",
                }
            )
        )
    finally:
        docker("rm", "--force", name, check=False)
        docker("volume", "rm", volume, check=False)


if __name__ == "__main__":
    main(sys.argv[1])
