"""One bounded restart of a changing public listing, never of access refusals."""

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from trading_radar.http import SourceUnavailable

T = TypeVar("T")


class SnapshotChanged(SourceUnavailable):
    """A valid page conflicts with another page in the same listing traversal."""


async def stable_listing(read: Callable[[], Awaitable[T]], source: str) -> T:
    try:
        return await read()
    except SnapshotChanged:
        # Retry the whole listing with fresh local rows. The caller's original
        # timeout and the shared host pacing still bound both traversals.
        logging.getLogger("trading_radar").info(
            "Restarting changed public listing once: %s", source
        )
        return await read()
