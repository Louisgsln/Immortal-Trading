"""Read public career pages and Oracle's candidate search; no authenticated API."""

import asyncio
import json
from pathlib import Path
from urllib.parse import urlencode

from trading_radar.http import HTTPClient, SourceUnavailable


async def main():
    http = HTTPClient(retries=1)
    directory = Path("data/discovery")
    directory.mkdir(parents=True, exist_ok=True)
    try:
        for source, url in [
            ("goldman", "https://higher.gs.com/results"),
            (
                "jpmorgan",
                "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/",
            ),
        ]:
            try:
                html = await http.get_text(url, 2, source)
                (directory / f"{source}.html").write_text(html, encoding="utf-8")
                print(json.dumps({"source": source, "page_bytes": len(html)}), flush=True)
            except SourceUnavailable as exc:
                print(json.dumps({"source": source, "error": str(exc)}), flush=True)
        url = (
            "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?"
            + urlencode(
                {
                    "onlyData": "true",
                    "expand": "requisitionList",
                    "finder": "findReqs;siteNumber=CX_1001,limit=25,offset=0,keyword=trading",
                }
            )
        )
        try:
            payload = await http.get_json(url, 2, "jpmorgan")
            (directory / "jpmorgan_search.json").write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
            print(
                json.dumps(
                    {
                        "source": "jpmorgan",
                        "keys": list(payload),
                        "first_item_keys": list((payload.get("items") or [{}])[0]),
                    }
                ),
                flush=True,
            )
        except SourceUnavailable as exc:
            print(json.dumps({"source": "jpmorgan_search", "error": str(exc)}), flush=True)
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
