import asyncio
import json
import random
import time
from collections import defaultdict
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

from trading_radar.http_cache import JSONCache, cacheable
from trading_radar.models import utcnow
from trading_radar.robots import RobotsPolicy

USER_AGENT = "TradingJobRadar/0.1 (personal public-careers monitor)"


class SourceUnavailable(RuntimeError):
    """Public source cannot currently be collected safely/reliably."""


class RequestPacing:
    """Host-wide spacing shared by otherwise independent anonymous sessions."""

    def __init__(self):
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.next_request: dict[str, float] = defaultdict(float)
        self.last_request: dict[str, float] = defaultdict(float)


class HTTPClient:
    def __init__(
        self,
        timeout: float = 20,
        retries: int = 3,
        transport=None,
        *,
        json_cache: JSONCache | None = None,
        pacing: RequestPacing | None = None,
    ):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
            transport=transport,
        )
        self.retries = retries
        self.json_cache = json_cache
        self.pacing = pacing or RequestPacing()
        self.locks = self.pacing.locks
        self.next_request = self.pacing.next_request
        self.last_request = self.pacing.last_request
        self.robots: dict[str, RobotsPolicy | None] = {}
        self.counts: dict[str, int] = defaultdict(int)

    async def close(self) -> None:
        await self.client.aclose()

    async def _request(
        self,
        url: str,
        interval: float,
        source: str,
        *,
        method: str = "GET",
        body: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        host = urlsplit(url).netloc
        async with self.locks[host]:
            for attempt in range(self.retries + 1):
                # A newly discovered Crawl-delay also applies after the robots request.
                due = max(self.next_request[host], self.last_request[host] + interval)
                await asyncio.sleep(max(0, due - time.monotonic()))
                self.last_request[host] = time.monotonic()
                self.next_request[host] = self.last_request[host] + interval
                self.counts[source] += 1
                try:
                    response = await self.client.request(method, url, json=body, headers=headers)
                except httpx.TransportError:
                    if attempt == self.retries:
                        raise SourceUnavailable("network timeout or transport error") from None
                    await asyncio.sleep(2**attempt + random.uniform(0, 0.5))
                    continue
                if response.status_code in {401, 403}:
                    raise SourceUnavailable(f"access restricted: HTTP {response.status_code}")
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == self.retries:
                        raise SourceUnavailable(f"HTTP {response.status_code} after retries")
                    delay = 2**attempt + random.uniform(0, 0.5)
                    retry_after = response.headers.get("retry-after")
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after))
                        except ValueError:
                            try:
                                delay = max(
                                    delay,
                                    (parsedate_to_datetime(retry_after) - utcnow()).total_seconds(),
                                )
                            except (TypeError, ValueError):
                                pass
                    if delay > 60:
                        raise SourceUnavailable("server requests a later retry; deferring source")
                    await asyncio.sleep(delay)
                    continue
                return response
        raise SourceUnavailable("request exhausted")

    async def get_json(self, url: str, interval: float, source: str):
        return await self._json(url, interval, source)

    async def get_conditional_json(self, url: str, interval: float, source: str):
        """Revalidate a public JSON body on every call, failing closed on errors."""
        cache = self.json_cache
        if cache is None:
            return await self.get_json(url, interval, source)
        if not cacheable(self.client.headers) or self.client.cookies or self.client.auth:
            cache.discard(source, url)
            return await self.get_json(url, interval, source)
        entry = cache.get(source, url)
        try:
            response = await self._public_response(
                url,
                interval,
                source,
                headers=entry.headers if entry else None,
                allow_not_modified=True,
            )
            if response.status_code == 304:
                # TTL/eviction may happen during an awaited network request.
                if entry is None or cache.get(source, url) is not entry:
                    raise SourceUnavailable("HTTP 304 without a valid cached body")
                if (
                    not cacheable(response.request.headers)
                    or not cacheable(response.headers)
                    or (response.headers.get("etag") and response.headers["etag"] != entry.etag)
                    or (
                        response.headers.get("last-modified")
                        and response.headers["last-modified"] != entry.last_modified
                    )
                ):
                    raise SourceUnavailable("HTTP 304 has incompatible cache metadata")
                return json.loads(entry.body)
            payload = response.json()
            if cacheable(response.request.headers):
                cache.put(source, url, response.content, response.headers)
            else:
                cache.discard(source, url)
            return payload
        except ValueError:
            cache.discard(source, url)
            raise SourceUnavailable("expected JSON; possible access challenge") from None
        except BaseException:
            cache.discard(source, url)
            raise

    async def get_text(self, url: str, interval: float, source: str) -> str:
        return (await self._public_response(url, interval, source)).text

    async def post_search_json(self, url: str, body: dict, interval: float, source: str):
        """Read-only public search endpoints that require a POST body."""
        return await self._json(url, interval, source, method="POST", body=body)

    async def _json(
        self,
        url: str,
        interval: float,
        source: str,
        *,
        method: str = "GET",
        body: dict | None = None,
    ):
        response = await self._public_response(url, interval, source, method=method, body=body)
        try:
            return response.json()
        except ValueError:
            raise SourceUnavailable("expected JSON; possible access challenge") from None

    async def _public_response(
        self,
        url: str,
        interval: float,
        source: str,
        *,
        method: str = "GET",
        body: dict | None = None,
        headers: dict[str, str] | None = None,
        allow_not_modified: bool = False,
    ):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise SourceUnavailable("only public HTTPS endpoints are supported")
        origin = f"{parts.scheme}://{parts.netloc}"
        # Use the same host lock for request pacing. Failed robots reads fail closed.
        if origin not in self.robots:
            response = await self._request(origin + "/robots.txt", interval, source)
            if response.status_code == 404:
                self.robots[origin] = None
            elif response.status_code == 200:
                self.robots[origin] = RobotsPolicy.parse(response.text)
            else:
                raise SourceUnavailable(f"robots policy unavailable: HTTP {response.status_code}")
        policy = self.robots[origin]
        if policy:
            if not policy.can_fetch(url, USER_AGENT.split("/", 1)[0]):
                raise SourceUnavailable("robots policy disallows this endpoint")
            interval = max(interval, float(policy.crawl_delay(USER_AGENT.split("/", 1)[0]) or 0))
        if allow_not_modified and self.client.cookies:
            # A robots response can establish a cookie after the initial cache check.
            headers = None
        response = await self._request(
            url, interval, source, method=method, body=body, headers=headers
        )
        if response.status_code != 200 and not (allow_not_modified and response.status_code == 304):
            raise SourceUnavailable(f"HTTP {response.status_code}")
        return response
