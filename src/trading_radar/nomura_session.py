"""Opt-in local session for the public Nomura campus board, never a CAPTCHA solver."""

import json
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from trading_radar.http import SourceUnavailable
from trading_radar.models import utcnow

HOST = "nomuracampus.tal.net"
MAX_BYTES = 65_536
MAX_AGE = timedelta(hours=12)
ENV = "NOMURA_SESSION_FILE"


def session_path() -> Path | None:
    value = os.environ.get(ENV, "").strip()
    return Path(value) if value else None


class NomuraSession:
    def __init__(self, data: object, now: datetime | None = None):
        self.now = now or utcnow()
        try:
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError
            verified = datetime.fromisoformat(data["verified_at"])
            if verified.tzinfo is None or not timedelta(0) <= self.now - verified <= MAX_AGE:
                raise ValueError
            self.user_agent = data["user_agent"]
            if not isinstance(self.user_agent, str) or not re.fullmatch(
                r"[\x20-\x7e]{1,512}", self.user_agent
            ):
                raise ValueError
            self.cookies = data["cookies"]
            if not isinstance(self.cookies, list) or not 1 <= len(self.cookies) <= 30:
                raise ValueError
            seen = set()
            for c in self.cookies:
                if not isinstance(c, dict):
                    raise ValueError
                name, value, domain, path, expiry = (
                    c[k] for k in ("name", "value", "domain", "path", "expires")
                )
                if (
                    not isinstance(name, str)
                    or not re.fullmatch(r"[A-Za-z0-9_!#$%&'*+.^`|~-]{1,128}", name)
                    or not isinstance(value, str)
                    or not re.fullmatch(
                        r"[\x21\x23-\x2b\x2d-\x3a\x3c-\x5b\x5d-\x7e]{1,8192}", value
                    )
                    or domain not in {HOST, "." + HOST}
                    or not isinstance(path, str)
                    or not re.fullmatch(r"/[\x21-\x7e]{0,1023}", path)
                    or type(expiry) not in {int, float}
                    or not (expiry == -1 or 0 < expiry < 100_000_000_000)
                    or (name, path) in seen
                ):
                    raise ValueError
                seen.add((name, path))
            self.verified_at = verified
        except (ValueError, KeyError, TypeError, OverflowError):
            raise SourceUnavailable(
                "Nomura campus CAPTCHA session invalid or expired; renewal required"
            ) from None

    def headers(self, url: str) -> dict[str, str]:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != HOST or parts.fragment:
            raise SourceUnavailable("Nomura session is restricted to its public HTTPS host")
        cookies = []
        for c in sorted(self.cookies, key=lambda c: -len(c["path"])):
            path = c["path"]
            if (c["expires"] == -1 or c["expires"] > self.now.timestamp()) and (
                parts.path == path
                or parts.path.startswith(path if path.endswith("/") else path + "/")
            ):
                cookies.append(c["name"] + "=" + c["value"])
        if not cookies:
            raise SourceUnavailable("Nomura campus CAPTCHA session expired; renewal required")
        return {"User-Agent": self.user_agent, "Cookie": "; ".join(cookies)}


def load_session(path: Path) -> NomuraSession:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError
        return NomuraSession(json.loads(raw))
    except (OSError, ValueError, UnicodeError):
        raise SourceUnavailable(
            "Nomura campus CAPTCHA session unavailable; renewal required"
        ) from None


def save_session(path: Path, data: dict) -> None:
    # Validate first, and replace atomically so a concurrent collector never reads
    # a half-written session. Only the dedicated public-board context is accepted.
    NomuraSession(data)
    raw = json.dumps(data).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise SourceUnavailable("Nomura campus CAPTCHA session exceeds local limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".nomura-session-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
