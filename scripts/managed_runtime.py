"""One persistent managed service: standby first, explicit cutover, grouped shutdown."""

import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from filelock import FileLock

from trading_radar.config import load_config
from trading_radar.dashboard_editor import create_editable_dashboard_server
from trading_radar.dashboard_private import PrivateDashboardAccess
from trading_radar.notifications import TelegramNotifier
from trading_radar.runtime_status import watcher_status
from trading_radar.telegram_control import ControlState
from trading_radar.telegram_heartbeat import HeartbeatState

APP = Path(__file__).resolve().parents[1]


def settings(environ: dict) -> tuple[str, Path, int]:
    mode = environ.get("RADAR_MODE", "standby")
    root = Path(environ.get("RADAR_STATE_ROOT", "/app/data/state"))
    port = int(environ.get("PORT", "10000"))
    if (
        mode not in {"standby", "active"}
        or not root.is_absolute()
        or not 1024 <= port <= 65535
        or port in {8765, 8766}
    ):
        raise ValueError("Invalid managed service settings")
    return mode, root, port


def child_environment(environ: dict, root: Path, role: str) -> dict:
    env = dict(environ)
    env["DATABASE_URL"] = f"sqlite:///{root / 'data/jobs.db'}"
    env["RADAR_CUTOVER_CONFIRMED"] = "true"
    if role in {"dashboard", "backups", "gateway"}:
        for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
            env.pop(key, None)
        env["ALERTS_ENABLED"] = "false"
        env["TELEGRAM_CONTROL_ENABLED"] = "false"
    if role == "dashboard":
        env["DASHBOARD_RADAR_ALERTS_ENABLED"] = environ.get("ALERTS_ENABLED", "false")
    return env


def validate_activation(root: Path, environ: dict) -> None:
    from scripts.cloud_runtime import preflight
    from scripts.migrate_state import RECEIPT

    receipt = json.loads((root / "data" / RECEIPT).read_text(encoding="utf-8"))
    if (
        receipt.get("format_version") != 1
        or not receipt.get("activation_id")
        or environ.get("RADAR_ACTIVATION_ID") != receipt["activation_id"]
        or environ.get("RADAR_CUTOVER_CONFIRMED") != "true"
    ):
        raise ValueError("Verified restore and explicit cutover required")
    # Validate identity before ANY child can contact Telegram.
    notifier = TelegramNotifier.from_env()
    binding = hashlib.sha256(
        (notifier.token.split(":", 1)[0] + ":" + notifier.chat_id).encode()
    ).hexdigest()
    control = ControlState.model_validate_json((root / "data/jobs.telegram.json").read_bytes())
    if control.binding != binding or receipt.get("telegram_binding") != binding:
        raise ValueError("Restored cursor belongs to another bot or chat")
    heartbeat = root / "data/jobs.heartbeat.json"
    if (
        heartbeat.exists()
        and HeartbeatState.model_validate_json(heartbeat.read_bytes()).binding != binding
    ):
        raise ValueError("Restored heartbeat belongs to another destination")
    access = PrivateDashboardAccess.from_env()
    if access.origin != environ.get("DASHBOARD_PUBLIC_ORIGIN"):
        raise ValueError("Private gateway origin mismatch")
    config = load_config(root / "config")
    preflight(config, "watch")
    preflight(config, "telegram")


def gateway_config(mode: str, port: int, access: PrivateDashboardAccess | None = None) -> str:
    private = ""
    if mode == "active":
        if access is None:
            raise ValueError("Private access required")
        private = f"""
    handle_path {access.prefix}* {{
        reverse_proxy 127.0.0.1:8765 {{
            header_up Host 127.0.0.1:8765
            header_up X-Radar-Gateway {access.gateway_secret}
            header_up -Authorization
        }}
    }}
"""
    return f"""{{
    admin off
    auto_https off
}}
:{port} {{
    header {{
        -Server
        Cache-Control "no-store"
        X-Robots-Tag "noindex, nofollow, noarchive"
        Referrer-Policy "no-referrer"
    }}
    handle /healthz {{
        reverse_proxy 127.0.0.1:8766
    }}
{private}
    handle {{
        respond "Not found" 404
    }}
}}
"""


def stop_children(children: list, timeout: float = 25) -> None:
    for child in reversed(children):
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + timeout
    for child in reversed(children):
        try:
            child.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()


def serve(root: Path, mode: str, port: int) -> int:
    stop = threading.Event()
    for value in (signal.SIGTERM, signal.SIGINT):
        signal.signal(value, lambda *_: stop.set())
    children: list[subprocess.Popen] = []
    started = time.monotonic()
    config = load_config(root / "config") if mode == "active" else None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            if self.path != "/healthz":
                self.send_error(404)
                return
            alive = (
                not stop.is_set()
                and bool(children)
                and all(child.poll() is None for child in children)
            )
            watcher = "disabled"
            if config:
                watcher = watcher_status(config)["status"]
                alive = alive and (watcher == "active" or time.monotonic() - started < 180)
            body = json.dumps({"mode": mode, "processes_alive": alive, "watcher": watcher}).encode()
            self.send_response(200 if alive else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    health = ThreadingHTTPServer(("127.0.0.1", 8766), Handler)
    health.daemon_threads = True
    thread = threading.Thread(target=health.serve_forever, daemon=True)
    thread.start()
    try:
        access = PrivateDashboardAccess.from_env() if mode == "active" else None
        import tempfile

        with tempfile.TemporaryDirectory(prefix="radar-gateway-") as temporary:
            caddyfile = Path(temporary) / "Caddyfile"
            caddyfile.write_text(gateway_config(mode, port, access), encoding="utf-8")
            caddyfile.chmod(0o600)
            # Validate without printing the expanded configuration or secrets.
            subprocess.run(
                ["caddy", "validate", "--config", str(caddyfile), "--adapter", "caddyfile"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=child_environment(os.environ, root, "gateway"),
            )
            roles = ["dashboard", "backups", "watch", "telegram"] if mode == "active" else []
            for role in ["gateway", *roles]:
                if role == "gateway":
                    command = ["caddy", "run", "--config", str(caddyfile), "--adapter", "caddyfile"]
                elif role == "dashboard":
                    command = [sys.executable, str(APP / "scripts/managed_runtime.py"), "dashboard"]
                else:
                    command = [
                        sys.executable,
                        str(APP / "scripts/cloud_runtime.py"),
                        role,
                        "--config-dir",
                        str(root / "config"),
                    ]
                children.append(
                    subprocess.Popen(
                        command,
                        cwd=root if mode == "active" else APP,
                        env=child_environment(os.environ, root, role),
                        start_new_session=True,
                    )
                )
            print(
                json.dumps({"status": "running", "mode": mode, "processes": len(children)}),
                flush=True,
            )
            while not stop.wait(1):
                if any(child.poll() is not None for child in children):
                    return 1
            return 0
    finally:
        stop_children(children)
        health.shutdown()
        health.server_close()
        thread.join(timeout=5)


def main() -> int:
    try:
        mode, root, port = settings(os.environ)
        os.environ["DATABASE_URL"] = f"sqlite:///{root / 'data/jobs.db'}"
        if sys.argv[1:] == ["dashboard"]:
            server = create_editable_dashboard_server(
                load_config(root / "config"),
                root / "data/health-history",
                private_access=PrivateDashboardAccess.from_env(),
            )
            # Full HTML remains compatible with the existing Sites snapshot bridge.
            server.serve_forever()
            return 0
        if sys.argv[1:]:
            raise ValueError("Unexpected managed runtime arguments")
        root.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(root.parent / ".managed-runtime.lock"), timeout=0):
            if mode == "active":
                validate_activation(root, os.environ)
            return serve(root, mode, port)
    except Exception as error:
        print(
            json.dumps({"status": "blocked", "error_type": type(error).__name__}), file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    # Direct execution must resolve the sibling scripts package regardless of cwd.
    sys.path.insert(0, str(APP))
    raise SystemExit(main())
