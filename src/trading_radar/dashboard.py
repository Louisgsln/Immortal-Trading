"""Self-contained dashboard snapshots and a loopback-only, read-only preview."""

import base64
import hashlib
import html
import json
import os
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from trading_radar.backups import database_path
from trading_radar.config import Config
from trading_radar.dashboard_data import build_dashboard_data


def _assets() -> tuple[str, str, str]:
    root = files("trading_radar").joinpath("dashboard_assets")
    return tuple(
        root.joinpath(name).read_text(encoding="utf-8")
        for name in ("index.html", "dashboard.css", "dashboard.js")
    )  # type: ignore[return-value]


def _policy(css: str, script: str, *, editable: bool = False) -> str:
    def digest(value: str) -> str:
        return base64.b64encode(hashlib.sha256(value.encode("utf-8")).digest()).decode("ascii")

    return (
        "default-src 'none'; base-uri 'none'; form-action 'none'; "
        + ("connect-src 'self'; " if editable else "connect-src 'none'; ")
        + f"script-src 'sha256-{digest(script)}'; style-src 'sha256-{digest(css)}'; img-src data:"
    )


def render_dashboard(data: dict, *, editable: bool = False) -> str:
    template, css, script = _assets()
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    # A JSON script element is still parsed by HTML: escape tag delimiters before
    # insertion. No job text becomes markup or JavaScript source.
    for character, escape in (
        ("<", "\\u003c"),
        (">", "\\u003e"),
        ("&", "\\u0026"),
        ("\u2028", "\\u2028"),
        ("\u2029", "\\u2029"),
    ):
        encoded = encoded.replace(character, escape)
    replacements = {
        "__RADAR_CSS__": css,
        "__RADAR_JS__": script,
        "__RADAR_CSP__": html.escape(_policy(css, script, editable=editable), quote=True),
        "__RADAR_DATA__": encoded,
    }
    # One pass prevents a marker in a job description from being interpreted as a
    # template placeholder after insertion.
    import re

    for marker in replacements:
        if template.count(marker) != 1:
            raise ValueError("Dashboard template is incomplete")
    return re.sub(
        "|".join(re.escape(marker) for marker in replacements),
        lambda match: replacements[match.group()],
        template,
    )


def _validate_destination(config: Config, destination: Path, overwrite: bool) -> None:
    if destination.suffix.lower() != ".html":
        raise ValueError("Choose an .html dashboard destination")
    if destination.is_symlink():
        raise ValueError("Dashboard destination must not be a symbolic link")
    resolved = destination.resolve()
    source_root = (Path.cwd() / "sources").resolve()
    if resolved == source_root or source_root in resolved.parents:
        raise ValueError("Synced sources are read-only")
    database = database_path(config.settings.database_url)
    for suffix in ("", "-wal", "-shm", "-journal", ".lock"):
        protected = Path(str(database) + suffix)
        if (
            resolved == protected
            or protected in resolved.parents
            or (destination.exists() and protected.exists() and destination.samefile(protected))
        ):
            raise ValueError("Dashboard destination overlaps the database or its sidecars")
    if os.path.lexists(destination) and (not overwrite or not destination.is_file()):
        raise ValueError("Destination exists; use --overwrite for an existing dashboard file")


def export_dashboard(
    config: Config,
    destination: Path,
    history_dir: Path = Path("data/health-history"),
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    _validate_destination(config, destination, overwrite)
    data = build_dashboard_data(config, history_dir=history_dir)
    if data["status"] == "error":
        raise ValueError("Dashboard data is unavailable; inspect the database with health")
    content = render_dashboard(data).encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".radar-dashboard-", dir=destination.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        _validate_destination(config, destination, overwrite)
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "destination": str(destination),
        "generated_at": data["generated_at"],
        "jobs": len(data["jobs"]),
        "bytes": len(content),
        "read_only": True,
    }


def create_dashboard_server(content: str, port: int = 8765) -> ThreadingHTTPServer:
    """Serve one in-memory snapshot, never a directory or an API that can write."""
    body = content.encode("utf-8")
    _, css, script = _assets()
    policy = _policy(css, script) + "; frame-ancestors 'none'"

    class Handler(BaseHTTPRequestHandler):
        server_version = "TradingRadar"
        sys_version = ""

        def log_message(self, format, *args):
            pass

        def _respond(self, status: int, payload: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", policy)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)

        def do_GET(self):
            port = cast(ThreadingHTTPServer, self.server).server_port
            hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if (
                self.headers.get("Host") not in hosts
                or self.headers.get("Sec-Fetch-Site") == "cross-site"
                or (
                    self.headers.get("Origin") is not None
                    and self.headers["Origin"] not in {"http://" + host for host in hosts}
                )
            ):
                self._respond(403, b"Local access only", "text/plain; charset=utf-8")
            elif self.path not in {"/", "/index.html"}:
                self._respond(404, b"Not found", "text/plain; charset=utf-8")
            else:
                self._respond(200, body, "text/html; charset=utf-8")

        def do_HEAD(self):
            self.do_GET()

        def _read_only(self):
            # Closing with an unread request body can reset the connection on
            # Windows before the client receives its 405. Drain only a small,
            # explicitly framed body; a partial sender must not hold us open.
            length = self.headers.get("Content-Length", "")
            if (
                self.headers.get("Transfer-Encoding") is None
                and len(self.headers.get_all("Content-Length", [])) == 1
                and length.isascii()
                and length.isdecimal()
                and len(length) <= 4
                and int(length) <= 8192
            ):
                previous_timeout = self.connection.gettimeout()
                try:
                    deadline = time.monotonic() + 0.25
                    remaining = int(length)
                    while remaining:
                        budget = deadline - time.monotonic()
                        if budget <= 0:
                            break
                        self.connection.settimeout(budget)
                        chunk = self.rfile.read1(remaining)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                except OSError:
                    pass
                finally:
                    self.connection.settimeout(previous_timeout)
            self._respond(405, b"Read-only dashboard", "text/plain; charset=utf-8")

        do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _read_only

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
