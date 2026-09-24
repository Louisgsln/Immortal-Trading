"""Bounded disposal of rejected request bodies before closing a local connection."""

import time
from http.server import BaseHTTPRequestHandler


def discard_small_body(handler: BaseHTTPRequestHandler) -> None:
    # An unread small body can cause a Windows reset before the error is received.
    # Never decode, decompress or process it; ambiguous or large framing is skipped.
    length = handler.headers.get("Content-Length", "")
    if (
        handler.headers.get("Transfer-Encoding") is not None
        or len(handler.headers.get_all("Content-Length", [])) != 1
        or not length.isascii()
        or not length.isdecimal()
        or len(length) > 4
        or int(length) > 8192
    ):
        return
    previous_timeout = handler.connection.gettimeout()
    try:
        deadline = time.monotonic() + 0.25
        remaining = int(length)
        while remaining:
            budget = deadline - time.monotonic()
            if budget <= 0:
                break
            handler.connection.settimeout(budget)
            chunk = handler.rfile.read1(remaining)
            if not chunk:
                break
            remaining -= len(chunk)
    except OSError:
        pass
    finally:
        handler.connection.settimeout(previous_timeout)
