"""Bounded, process-local bodies for explicit HTTP conditional revalidation."""

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class JSONCacheEntry:
    body: bytes
    etag: str | None
    last_modified: str | None
    created: float

    @property
    def headers(self) -> dict[str, str]:
        result = {}
        if self.etag:
            result["If-None-Match"] = self.etag
        if self.last_modified:
            result["If-Modified-Since"] = self.last_modified
        return result


def cacheable(headers: httpx.Headers) -> bool:
    directives = {
        part.strip().split("=", 1)[0].lower()
        for part in headers.get("cache-control", "").split(",")
    }
    return not (
        directives & {"no-store", "private"}
        or "vary" in headers
        or "authorization" in headers
        or "cookie" in headers
        or "set-cookie" in headers
    )


class JSONCache:
    """Store only bounded bodies with validators; never return unvalidated content.

    TTL is a hard residence limit since the last 200, including across 304s.
    Access is synchronous and intended for a single asyncio event loop.
    """

    def __init__(
        self,
        *,
        max_entries: int = 256,
        max_entry_bytes: int = 1024 * 1024,
        max_bytes: int = 16 * 1024 * 1024,
        ttl: float = 3600,
        clock: Callable[[], float] = time.monotonic,
    ):
        if min(max_entries, max_entry_bytes, max_bytes, ttl) <= 0:
            raise ValueError("Cache bounds and TTL must be positive")
        self.max_entries = max_entries
        self.max_entry_bytes = max_entry_bytes
        self.max_bytes = max_bytes
        self.ttl = ttl
        self.clock = clock
        self.entries: OrderedDict[tuple[str, str], JSONCacheEntry] = OrderedDict()
        self.size_bytes = 0

    def discard(self, source: str, url: str) -> None:
        entry = self.entries.pop((source, url), None)
        if entry is not None:
            self.size_bytes -= len(entry.body)

    def _purge(self) -> None:
        now = self.clock()
        for key, entry in list(self.entries.items()):
            if now - entry.created >= self.ttl:
                self.discard(*key)

    def get(self, source: str, url: str) -> JSONCacheEntry | None:
        self._purge()
        key = (source, url)
        entry = self.entries.get(key)
        if entry is not None:
            self.entries.move_to_end(key)
        return entry

    def put(self, source: str, url: str, body: bytes, headers: httpx.Headers) -> None:
        self.discard(source, url)
        self._purge()
        etag, modified = headers.get("etag"), headers.get("last-modified")
        if (
            not cacheable(headers)
            or not (etag or modified)
            or len(body) > min(self.max_entry_bytes, self.max_bytes)
            or len(url) > 4096
            or len(source) > 256
            or any(len(value) > 512 for value in (etag, modified) if value)
        ):
            return
        while self.entries and (
            len(self.entries) >= self.max_entries or self.size_bytes + len(body) > self.max_bytes
        ):
            self.discard(*next(iter(self.entries)))
        self.entries[(source, url)] = JSONCacheEntry(body, etag, modified, self.clock())
        self.size_bytes += len(body)
