"""Inspect career-page contracts linked directly from official portals."""

import asyncio
import json
from pathlib import Path

from trading_radar.goldman import PageData
from trading_radar.http import HTTPClient, SourceUnavailable


async def main():
    root = Path("data/discovery/lot4")
    root.mkdir(parents=True, exist_ok=True)
    http = HTTPClient(retries=1)
    urls = {
        "campus_role": "https://higher.gs.com/roles/182119",
        "ubs_board": "https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5131&PageType=searchResults&SearchType=linkquery&LinkID=15232",
        "bnp_search": "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi",
        "sg_search": "https://careers.societegenerale.com/rechercher",
        "sg_js": "https://careers.societegenerale.com/themes/custom/sg_careers/js/quantum/global-quantum.js?tlclx9",
        "sg_directory": "https://careers.societegenerale.com/Technical/toutes-les-offres",
        "ubs_search_js": "https://jobs.ubs.com/TGNewUI/Scripts/app/v-639246361753053093/search.min.js",
    }
    try:
        for name, url in urls.items():
            try:
                text = await http.get_text(url, 2, name)
                (root / f"{name}.txt").write_text(text, encoding="utf-8")
                print(f"{name}: {len(text)} chars", flush=True)
                if name == "campus_role":
                    parser = PageData()
                    parser.feed(text)
                    result = json.loads("".join(parser.parts))
                    (root / "campus-role.json").write_text(
                        json.dumps(result, indent=2), encoding="utf-8"
                    )
                    print(json.dumps(result)[:14000], flush=True)
            except SourceUnavailable as exc:
                print(f"{name}: {exc}", flush=True)
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
