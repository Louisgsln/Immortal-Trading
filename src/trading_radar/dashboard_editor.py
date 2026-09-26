"""Opt-in local application edits and health archives; exports remain read-only."""

import json
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import unquote

from trading_radar.config import Config
from trading_radar.dashboard import _assets, _policy, render_dashboard
from trading_radar.dashboard_applications import (
    ApplicationEditError,
    list_applications,
    read_application,
    update_application,
)
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.dashboard_http import discard_small_body
from trading_radar.monitoring import history, record_health

MAX_BODY_BYTES = 131_072


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Nonfinite JSON value")


def create_editable_dashboard_server(
    config: Config, history_dir: Path = Path("data/health-history"), port: int = 8765
) -> ThreadingHTTPServer:
    """Protect explicit local actions with a per-process token and origin checks."""
    initial = build_dashboard_data(config, history_dir=history_dir)
    if initial["status"] != "ok":
        raise ValueError("Dashboard data unavailable")
    token = secrets.token_urlsafe(32)
    _, css, script = _assets()
    policy = _policy(css, script, editable=True) + "; frame-ancestors 'none'"

    class Handler(BaseHTTPRequestHandler):
        server_version = "TradingRadar"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, format, *args):
            pass

        def respond(self, status: int, body: bytes, content_type: str) -> None:
            self.close_connection = True
            self.send_response(status)
            for name, value in {
                "Content-Type": content_type,
                "Content-Length": str(len(body)),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": policy,
                "Connection": "close",
            }.items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass

        def json(self, status: int, payload: dict) -> None:
            self.respond(
                status,
                json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def error(self, status: int, code: str, message: str) -> None:
            if not getattr(self, "body_consumed", False):
                discard_small_body(self)
            self.json(status, {"status": "error", "error": {"code": code, "message": message}})

        def local(self, *, write: bool = False) -> bool:
            port = cast(ThreadingHTTPServer, self.server).server_port
            hosts = self.headers.get_all("Host", [])
            origins = self.headers.get_all("Origin", [])
            sites = self.headers.get_all("Sec-Fetch-Site", [])
            if (
                len(hosts) != 1
                or hosts[0] not in {f"127.0.0.1:{port}", f"localhost:{port}"}
                or len(origins) > 1
                or len(sites) > 1
                or (sites and sites[0] not in {"same-origin", "same-site", "none"})
                or (origins and origins[0] != "http://" + hosts[0])
                or (write and not origins)
            ):
                self.error(403, "local_only", "Accès local à cette page requis.")
                return False
            return True

        def authorized(self) -> bool:
            values = self.headers.get_all("X-Radar-Token", [])
            if len(values) != 1 or not secrets.compare_digest(values[0].encode(), token.encode()):
                self.error(
                    403, "invalid_session", "Rechargez la page pour ouvrir une session locale."
                )
                return False
            return True

        def job_id(self) -> str | None:
            match = re.fullmatch(r"/api/applications/([A-Za-z0-9_-]{1,128})", unquote(self.path))
            return match[1] if match else None

        def do_GET(self):
            if not self.local():
                return
            if self.path in {"/", "/index.html"}:
                data = build_dashboard_data(config, history_dir=history_dir)
                data["editing"] = {"enabled": True, "token": token}
                self.respond(
                    200,
                    render_dashboard(data, editable=True).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
                return
            if self.path == "/api/applications":
                if not self.authorized():
                    return
                try:
                    self.json(200, {"status": "ok", "applications": list_applications(config)})
                except ApplicationEditError as exc:
                    self.error(exc.status, exc.code, exc.message)
                return
            job_id = self.job_id()
            if job_id is None:
                self.error(404, "not_found", "Cette ressource n’existe pas.")
                return
            if not self.authorized():
                return
            try:
                self.json(200, {"status": "ok", **read_application(config, job_id)})
            except ApplicationEditError as exc:
                self.error(exc.status, exc.code, exc.message)

        def do_HEAD(self):
            self.do_GET()

        def do_POST(self):
            if not self.local(write=True) or not self.authorized():
                return
            job_id = self.job_id()
            capture_health = self.path == "/api/health-snapshots"
            if job_id is None and not capture_health:
                self.error(404, "not_found", "Cette ressource n’existe pas.")
                return
            lengths = self.headers.get_all("Content-Length", [])
            if (
                self.headers.get_all("Transfer-Encoding")
                or self.headers.get_all("Content-Encoding")
                or len(lengths) != 1
                or not re.fullmatch(r"[0-9]{1,9}", lengths[0])
                or int(lengths[0]) < 1
            ):
                self.error(400, "invalid_request", "Le format de la requête est invalide.")
                return
            length = int(lengths[0])
            if length > MAX_BODY_BYTES:
                self.error(413, "too_large", "Le formulaire dépasse la taille autorisée.")
                return
            types = self.headers.get_all("Content-Type", [])
            if len(types) != 1 or not re.fullmatch(
                r'application/json(?:\s*;\s*charset\s*=\s*(?:utf-8|"utf-8"))?',
                types[0],
                re.IGNORECASE,
            ):
                self.error(415, "invalid_content_type", "Un formulaire JSON UTF-8 est requis.")
                return
            try:
                self.body_consumed = True
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Incomplete body")
                payload = json.loads(
                    raw.decode("utf-8"),
                    object_pairs_hook=_unique_object,
                    parse_constant=_reject_constant,
                )
                expected = set() if capture_health else {"revision", "changes"}
                if not isinstance(payload, dict) or set(payload) != expected:
                    raise ValueError("Invalid envelope")
            except (ValueError, RecursionError, TimeoutError, OSError):
                self.error(400, "invalid_request", "Le format de la requête est invalide.")
                return
            if capture_health:
                self.capture_health()
                return
            assert job_id is not None
            try:
                result = update_application(config, job_id, payload["changes"], payload["revision"])
                self.json(200, {"status": "ok", **result})
            except ApplicationEditError as exc:
                self.error(exc.status, exc.code, exc.message)

        def capture_health(self) -> None:
            try:
                snapshot = record_health(config, history_dir)
            except (OSError, ValueError):
                self.error(
                    503,
                    "health_capture_unavailable",
                    "Enregistrement non confirmé. Rechargez la page pour vérifier l’historique.",
                )
                return
            # A published archive remains successful even if another archive is unreadable.
            # Never suggest retrying a write just because refreshing its history failed.
            try:
                monitoring = {"status": "ok", **history(history_dir, limit=10)}
            except (OSError, ValueError):
                monitoring = {
                    "status": "unavailable",
                    "error": {"message": "Les archives locales n’ont pas pu être relues."},
                }
            self.json(
                201,
                {
                    "status": "ok",
                    "snapshot": {"id": snapshot["id"], "recorded_at": snapshot["recorded_at"]},
                    "monitoring": monitoring,
                },
            )

        def unsupported(self):
            self.error(405, "method_not_allowed", "Cette action n’est pas disponible.")

        do_PUT = do_PATCH = do_DELETE = do_OPTIONS = unsupported

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
