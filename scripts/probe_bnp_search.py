"""Read BNP's public HTML search using its own GET form."""

import asyncio
import re
from pathlib import Path

from trading_radar.http import HTTPClient


async def main():
    root = Path("data/discovery/lot4")
    http = HTTPClient(retries=1)
    try:
        html = await http.get_text(
            "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi?form%5Bq%5D=trading",
            2,
            "bnp",
        )
        (root / "bnp-trading.html").write_text(html, encoding="utf-8")
        links = list(dict.fromkeys(re.findall(r'href="([^"]*/offre-emploi/[^"]+)"', html)))
        print("Links:", links, flush=True)
        if links:
            url = (
                links[0]
                if links[0].startswith("https://")
                else "https://group.bnpparibas" + links[0]
            )
            detail = await http.get_text(url, 2, "bnp")
            (root / "bnp-detail.html").write_text(detail, encoding="utf-8")
            print("Saved detail", len(detail))
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
