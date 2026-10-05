"""Read-only inventory of known worker entry points, without exposing command lines."""

import json
import ntpath
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

MODES = {"watch", "telegram", "dashboard", "backup", "scan"}
WINDOWS_QUERY = r"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$p = @(Get-CimInstance Win32_Process -ErrorAction Stop |
  Where-Object { $_.Name -match '^(python[0-9.w]*|trading-radar|uv|py)\.exe$' } |
  Select-Object -First 2001 ProcessId,ParentProcessId,CommandLine)
$t = @(Get-ScheduledTask -TaskName 'Immortal-Trading-*' -ErrorAction SilentlyContinue |
  Select-Object -First 1001 TaskName,@{Name='State';Expression={$_.State.ToString()}})
[pscustomobject]@{processes=$p;tasks=$t} | ConvertTo-Json -Depth 4 -Compress
"""


def classify(argv: list[str], cwd: str | None = None) -> dict | None:
    if not argv:
        return None
    tokens = [token.strip('"') for token in argv]
    executable = ntpath.basename(tokens[0]).lower()
    if not re.fullmatch(
        r"python(?:w|\d+(?:\.\d+)*)?(?:\.exe)?|trading-radar(?:\.exe)?|uv(?:\.exe)?|py(?:\.exe)?",
        executable,
    ):
        return None
    for index, token in enumerate(tokens):
        name = ntpath.basename(token).lower()
        module = token == "trading_radar" and index > 0 and tokens[index - 1] == "-m"
        service = name in {"windows_entry.py", "windows_service.py"}
        if not (module or service or name in {"trading-radar", "trading-radar.exe"}):
            continue
        if index + 1 >= len(tokens) or tokens[index + 1] not in MODES:
            continue
        config = None
        if service:
            parent = ntpath.dirname(ntpath.dirname(token))
            if ntpath.isabs(parent):
                config = (
                    ntpath.join(parent, "config")
                    if "\\" in parent
                    else str(Path(parent) / "config")
                )
            elif cwd:
                config = str((Path(cwd) / parent / "config").resolve())
        else:
            directory = "config"
            for position, option in enumerate(tokens[index + 2 :], index + 2):
                if option == "--config-dir" and position + 1 < len(tokens):
                    directory = tokens[position + 1]
                elif option.startswith("--config-dir="):
                    directory = option.split("=", 1)[1]
            if ntpath.isabs(directory):
                config = (
                    ntpath.normpath(directory)
                    if "\\" in directory
                    else str(Path(directory).resolve())
                )
            elif cwd:
                config = str((Path(cwd) / directory).resolve())
        return {
            "mode": tokens[index + 1],
            "kind": "launcher" if executable in {"uv", "uv.exe", "py", "py.exe"} else "worker",
            "executable": executable,
            "config_directory": config[:1000] if config else None,
        }
    return None


def linux_inventory(proc: Path = Path("/proc")) -> dict:
    entries, unreadable = [], 0
    identifiers = sorted((p for p in proc.iterdir() if p.name.isdigit()), key=lambda p: int(p.name))
    for directory in identifiers[:5000]:
        try:
            with (directory / "cmdline").open("rb") as stream:
                raw = stream.read(65_537)
            if len(raw) > 65_536:
                unreadable += 1
                continue
            argv = [token.decode("utf-8", errors="replace") for token in raw.split(b"\0") if token]
            try:
                cwd = os.readlink(directory / "cwd")
            except OSError:
                cwd = None
            item = classify(argv, cwd)
            if item is None:
                continue
            status = (directory / "status").read_text()[:10_000]
            parent = re.search(r"^PPid:\s*(\d+)", status, re.M)
            entries.append(
                {
                    "pid": int(directory.name),
                    "parent_pid": int(parent[1]) if parent else None,
                    **item,
                }
            )
        except FileNotFoundError:
            continue  # A process can exit during this read-only observation.
        except OSError:
            unreadable += 1
    return {
        "status": "partial" if unreadable or len(identifiers) > 5000 else "ok",
        "processes": entries,
        "unreadable": unreadable,
        "tasks_status": "not_supported",
        "scheduled_tasks": [],
    }


def windows_inventory() -> dict:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", WINDOWS_QUERY],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=True,
    )
    if len(result.stdout) > 2_000_000:
        raise ValueError("Inventory size limit")
    payload = json.loads(result.stdout)
    raw = payload["processes"]
    tasks = payload["tasks"]
    if not isinstance(raw, list) or not isinstance(tasks, list):
        raise ValueError("Invalid Windows inventory")
    entries = []
    for process in raw[:2000]:
        if not isinstance(process, dict) or not isinstance(process.get("CommandLine") or "", str):
            raise ValueError("Invalid process")
        argv = shlex.split(process.get("CommandLine") or "", posix=False)
        item = classify(argv)
        if item:
            entries.append(
                {
                    "pid": int(process["ProcessId"]),
                    "parent_pid": int(process["ParentProcessId"]),
                    **item,
                }
            )
    clean_tasks = []
    for task in tasks[:1000]:
        name, state = task["TaskName"], task["State"]
        if (
            not isinstance(name, str)
            or not isinstance(state, str)
            or not name.startswith("Immortal-Trading-")
        ):
            raise ValueError("Invalid task")
        mode = name.rsplit("-", 1)[-1]
        clean_tasks.append(
            {"name": name[:200], "state": state[:40], "mode": mode if mode in MODES else "unknown"}
        )
    return {
        "status": "partial" if len(raw) > 2000 else "ok",
        "processes": entries,
        "unreadable": 0,
        "tasks_status": "partial" if len(tasks) > 1000 else "ok",
        "scheduled_tasks": clean_tasks,
    }


def launcher_report() -> dict:
    try:
        inventory = (
            windows_inventory()
            if sys.platform == "win32"
            else linux_inventory()
            if sys.platform.startswith("linux")
            else None
        )
        if inventory is None:
            raise ValueError("Unsupported platform")
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        inventory = {
            "status": "unavailable",
            "processes": [],
            "scheduled_tasks": [],
            "tasks_status": "unavailable",
            "unreadable": None,
        }
    groups: dict[tuple[str, str], list[int]] = {}
    workers = [item for item in inventory["processes"] if item["kind"] == "worker"]
    for item in workers:
        if item["mode"] not in {"watch", "telegram"}:
            continue
        # Collapse parent/child entry point wrappers for the same configuration.
        if item["config_directory"] is not None and any(
            parent["pid"] == item["parent_pid"]
            and parent["pid"] != item["pid"]
            and parent["mode"] == item["mode"]
            and parent["config_directory"] == item["config_directory"]
            for parent in workers
        ):
            continue
        key = (
            item["mode"],
            ntpath.normcase(item["config_directory"])
            if sys.platform == "win32" and item["config_directory"]
            else item["config_directory"] or "unknown",
        )
        groups.setdefault(key, []).append(item["pid"])
    issues = [
        {
            "code": "multiple_workers_unverified"
            if directory == "unknown"
            else "duplicate_workers",
            "mode": mode,
            "config_directory": None if directory == "unknown" else directory,
            "pids": pids,
        }
        for (mode, directory), pids in groups.items()
        if len(pids) > 1
    ]
    for mode in ("watch", "telegram"):
        names = [task["name"] for task in inventory["scheduled_tasks"] if task["mode"] == mode]
        if len(names) > 1:
            issues.append({"code": "multiple_scheduled_launchers", "mode": mode, "tasks": names})
    return {
        "read_only": True,
        "platform": sys.platform,
        **inventory,
        "issues": issues,
        "scope": "Known CLI/service entry points on this machine; Windows task names Immortal-Trading-*.",
        "interpretation": "A recent pulse or PID file does not prove there is only one worker. Imported calls and other scheduler names may not be identifiable.",
    }
