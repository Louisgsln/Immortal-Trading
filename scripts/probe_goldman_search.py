"""Probe the anonymous read-only search used by higher.gs.com."""

import asyncio
import json
from pathlib import Path

from trading_radar.goldman import QUERY, SEARCH_API
from trading_radar.http import HTTPClient


async def main():
    Path("data/discovery").mkdir(parents=True, exist_ok=True)
    http = HTTPClient(retries=1)
    try:
        payload = await http.post_search_json(
            SEARCH_API,
            {
                "operationName": "GetRoles",
                "query": QUERY,
                "variables": {
                    "searchQueryInput": {
                        "page": {"pageSize": 20, "pageNumber": 0},
                        "sort": {"sortStrategy": "POSTED_DATE", "sortOrder": "DESC"},
                        "filters": [],
                        "experiences": ["EARLY_CAREER", "PROFESSIONAL"],
                        "searchTerm": "trading",
                    }
                },
            },
            2,
            "goldman",
        )
        Path("data/discovery/goldman-search.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        rows = payload.get("data", {}).get("roleSearch", {}).get("items", [])
        print(f"First page: {len(rows)} listings")
        seen = {row["externalSource"]["sourceId"]: row for row in rows}
        total = payload["data"]["roleSearch"]["totalCount"]
        if type(total) is not int or not 0 <= total <= 1999:
            raise ValueError("Unexpected result total")
        for page_number in range(1, (total + 19) // 20):
            page_payload = await http.post_search_json(
                SEARCH_API,
                {
                    "operationName": "GetRoles",
                    "query": QUERY,
                    "variables": {
                        "searchQueryInput": {
                            "page": {"pageSize": 20, "pageNumber": page_number},
                            "sort": {"sortStrategy": "POSTED_DATE", "sortOrder": "DESC"},
                            "filters": [],
                            "experiences": ["EARLY_CAREER", "PROFESSIONAL"],
                            "searchTerm": "trading",
                        }
                    },
                },
                2,
                "goldman",
            )
            Path(f"data/discovery/goldman-page-{page_number}.json").write_text(
                json.dumps(page_payload, indent=2), encoding="utf-8"
            )
            for row in page_payload["data"]["roleSearch"]["items"]:
                identifier = row["externalSource"]["sourceId"]
                if identifier in seen:
                    print(
                        json.dumps(
                            {"page": page_number, "first": seen[identifier], "duplicate": row}
                        ),
                        flush=True,
                    )
                    return
                seen[identifier] = row
            print(f"Page {page_number}: {len(seen)} unique source IDs", flush=True)
        page = await http.get_text("https://higher.gs.com/roles/167477", 2, "goldman")
        Path("data/discovery/goldman-role.html").write_text(page, encoding="utf-8")
        print(f"Role page: {len(page)} chars")
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
