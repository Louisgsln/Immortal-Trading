"""Inspect only the public SG job directories and referenced job pages."""

import asyncio
import re
from pathlib import Path

from trading_radar.http import HTTPClient, SourceUnavailable


async def main():
    root = Path("data/discovery/lot6")
    root.mkdir(parents=True, exist_ok=True)
    http = HTTPClient(retries=1)
    urls = {
        "directory_fr": "https://careers.societegenerale.com/fr/Technical/toutes-les-offres",
        "directory_en": "https://careers.societegenerale.com/en/Technical/all-job-offers",
        "detail_fr": "https://careers.societegenerale.com/offres-d-emploi/ingenieur-structuration-pre-trade-26000JKI-fr",
        "detail_en": "https://careers.societegenerale.com/en/job-offers/trainee-global-markets-sales-trading-societe-generale-india-mumbai-26000IZX-en",
    }
    try:
        for name, url in urls.items():
            try:
                text = await http.get_text(url, 2, "sg_probe")
                (root / f"{name}.html").write_text(text, encoding="utf-8")
                print(name, len(text), flush=True)
                if name == "directory_en":
                    links = re.findall(
                        r'href="([^"]*/job-offers/[^"]+)"[^>]*>(.*?)</a>', text, re.S
                    )
                    for link, title in links:
                        if "trading" in title.lower():
                            print(link, re.sub("<[^>]+>", "", title).strip(), flush=True)
            except SourceUnavailable as exc:
                print(name, str(exc), flush=True)
                if str(exc) == "HTTP 301":
                    # Robots was checked for this exact public URL above; inspect, don't follow.
                    response = await http._request(url, 2, "sg_probe")
                    print("Location:", response.headers.get("location"), flush=True)
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
