"""Read public career pages and the observed Goldman campus search."""

import asyncio
import json
from pathlib import Path

from trading_radar.goldman import QUERY, SEARCH_API
from trading_radar.http import HTTPClient, SourceUnavailable


async def main():
    root = Path("data/discovery/lot4")
    root.mkdir(parents=True, exist_ok=True)
    http = HTTPClient(retries=1)
    try:

        async def page(name, url):
            try:
                text = await http.get_text(url, 2, name)
                (root / f"{name}.html").write_text(text, encoding="utf-8")
                print(f"{name}: {len(text)} chars", flush=True)
            except SourceUnavailable as exc:
                print(f"{name}: {exc}", flush=True)

        await asyncio.gather(
            page("goldman_campus", "https://higher.gs.com/campus"),
            page("ubs", "https://www.ubs.com/global/en/careers/search-jobs.html"),
            page("bnp", "https://group.bnpparibas/emploi-carriere"),
            page("societe_generale", "https://careers.societegenerale.com/"),
        )
        query = QUERY.replace("GetRoles", "GetCampusRoles").replace(
            "externalSource { sourceId }",
            "externalSource { sourceId } educationLevel startDate gradDegreeStartDate gradDegreeEndDate",
        )
        result = await http.post_search_json(
            SEARCH_API,
            {
                "operationName": "GetCampusRoles",
                "query": query,
                "variables": {
                    "searchQueryInput": {
                        "page": {"pageSize": 20, "pageNumber": 0},
                        "sort": {"sortStrategy": "POSTED_DATE", "sortOrder": "DESC"},
                        "filters": [],
                        "experiences": ["CAMPUS"],
                        "searchTerm": "trading",
                    }
                },
            },
            2,
            "goldman_campus",
        )
        (root / "campus-search.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result)[:18000])
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
