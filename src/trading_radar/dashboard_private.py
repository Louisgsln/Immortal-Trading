"""Explicit passwordless editor behind a private HTTPS gateway capability."""

import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlsplit

COOKIE = "radar_session"
SESSION_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class PrivateDashboardAccess:
    origin: str
    prefix: str
    gateway_secret: str

    def __post_init__(self):
        url = urlsplit(self.origin)
        expected_netloc = (
            url.hostname + (":" + str(url.port) if url.port else "") if url.hostname else ""
        )
        if (
            url.scheme != "https"
            or not url.hostname
            or url.netloc != expected_netloc
            or url.path
            or url.query
            or url.fragment
            or url.username
            or url.password
            or not re.fullmatch(r"/[A-Za-z0-9_-]{32,128}/", self.prefix)
            or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", self.gateway_secret)
        ):
            raise ValueError("Invalid private Dashboard gateway configuration")

    @classmethod
    def from_env(cls):
        return cls(
            os.environ.get("DASHBOARD_PUBLIC_ORIGIN", ""),
            os.environ.get("DASHBOARD_PRIVATE_PREFIX", ""),
            os.environ.get("DASHBOARD_GATEWAY_SECRET", ""),
        )


class PrivateSessions:
    def __init__(self, access: PrivateDashboardAccess):
        self.access = access
        self.key = secrets.token_bytes(32)

    def sign(self, value: str) -> str:
        return hmac.new(self.key, value.encode(), hashlib.sha256).hexdigest()

    def read(self, headers) -> str | None:
        values = headers.get_all("Cookie", [])
        if len(values) != 1 or len(values[0]) > 8192:
            return None
        if sum(part.strip().startswith(COOKIE + "=") for part in values[0].split(";")) != 1:
            return None
        parsed = SimpleCookie()
        try:
            parsed.load(values[0])
            value = parsed[COOKIE].value
        except (KeyError, ValueError, CookieError):
            return None
        match = re.fullmatch(r"([A-Za-z0-9_-]{43})\.([0-9]{10})\.([a-f0-9]{64})", value)
        if not match or not 0 < int(match[2]) - time.time() <= SESSION_SECONDS:
            return None
        if not secrets.compare_digest(match[3], self.sign(match[1] + "." + match[2])):
            return None
        return value

    def mint(self) -> str:
        value = secrets.token_urlsafe(32) + "." + str(int(time.time()) + SESSION_SECONDS)
        return value + "." + self.sign(value)

    def csrf(self, session: str) -> str:
        return self.sign("csrf:" + session)

    def cookie(self, session: str) -> str:
        return f"{COOKIE}={session}; Path={self.access.prefix}; Secure; HttpOnly; SameSite=Strict; Max-Age={SESSION_SECONDS}"
