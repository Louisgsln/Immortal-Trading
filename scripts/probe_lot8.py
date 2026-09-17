"""Bounded reads of official public career pages, saved locally for inspection."""

import asyncio
import hashlib
import sys
from pathlib import Path

from trading_radar.http import HTTPClient, SourceUnavailable


async def main():
    root = Path("data/discovery/lot8")
    root.mkdir(parents=True, exist_ok=True)
    http = HTTPClient(retries=1)
    try:
        for url in sys.argv[1:]:
            try:
                response = await http._public_response(url, 2, "lot8_probe")
                path = root / (hashlib.sha256(url.encode()).hexdigest()[:12] + ".html")
                path.write_text(response.text, encoding="utf-8")
                print(path, url, len(response.text), flush=True)
            except SourceUnavailable as exc:
                print(url, str(exc), flush=True)
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
