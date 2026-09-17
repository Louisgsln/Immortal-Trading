"""Inspect public Goldman career-page scripts to identify the public search contract."""

import asyncio
import re
from pathlib import Path

from trading_radar.http import HTTPClient


async def main():
    http = HTTPClient(retries=1)
    try:
        html = Path("data/discovery/goldman.html").read_text(encoding="utf-8")
        paths = re.findall(r'<script[^>]+src="([^\"]+)"', html)
        for path in paths:
            if not path.startswith("/_next/static/") or not any(
                key in path for key in ["/pages/results-", "/pages/_app-", "/318-", "/458-"]
            ):
                continue
            code = await http.get_text("https://higher.gs.com" + path, 2, "goldman")
            target = Path("data/discovery") / Path(path).name
            target.write_text(code, encoding="utf-8")
            print(f"Saved {target.name}: {len(code)} chars", flush=True)
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
