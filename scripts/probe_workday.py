"""Read a single public search page per observed career site; never sends applications."""

import asyncio
import json
from pathlib import Path

from trading_radar.http import HTTPClient, SourceUnavailable

TARGETS = [
    ("deutsche_bank", "db", "wd3", "DBWebsite"),
    ("morgan_stanley", "ms", "wd5", "External"),
    ("citi", "citi", "wd5", "2"),
    ("barclays", "barclays", "wd3", "External_Career_Site_Barclays"),
]


async def main(only: str | None = None):
    http = HTTPClient(retries=1)
    reports = []
    try:
        for key, tenant, instance, site in TARGETS:
            if only and key != only:
                continue
            base = f"https://{tenant}.{instance}.myworkdayjobs.com"
            try:
                payload = await http.post_search_json(
                    f"{base}/wday/cxs/{tenant}/{site}/jobs",
                    {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "trading"},
                    2,
                    key,
                )
                Path("data/discovery").mkdir(parents=True, exist_ok=True)
                Path(f"data/discovery/{key}.json").write_text(
                    json.dumps(payload, indent=2), encoding="utf-8"
                )
                report = {
                    "source": key,
                    "status": "ok",
                    "total": payload.get("total"),
                    "sample": payload.get("jobPostings", [])[:2],
                }
                page2 = await http.post_search_json(
                    f"{base}/wday/cxs/{tenant}/{site}/jobs",
                    {"appliedFacets": {}, "limit": 20, "offset": 20, "searchText": "trading"},
                    2,
                    key,
                )
                report["page2_total"] = page2.get("total")
                report["page2_count"] = len(page2.get("jobPostings", []))
                Path(f"data/discovery/{key}_page2.json").write_text(
                    json.dumps(page2, indent=2), encoding="utf-8"
                )
            except SourceUnavailable as exc:
                report = {"source": key, "status": "unavailable", "reason": str(exc)}
            reports.append(report)
            print(json.dumps(report), flush=True)
    finally:
        await http.close()
    Path("data/discovery/report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=[t[0] for t in TARGETS])
    asyncio.run(main(parser.parse_args().source))
