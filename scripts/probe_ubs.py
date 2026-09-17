"""Probe only the read-only anonymous UBS public job search."""

import asyncio
import json
from html.parser import HTMLParser
from pathlib import Path

from trading_radar.config import load_config
from trading_radar.http import HTTPClient


class Inputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "input" and attr.get("id") in {
            "preLoadJSON",
            "CookieValue",
            "partnerId",
            "siteId",
            "linkId",
        }:
            self.values[attr["id"]] = attr.get("value", "")


async def main():
    http = HTTPClient(retries=1)
    try:
        url = load_config().companies["ubs"].career_url
        parser = Inputs()
        parser.feed(await http.get_text(url, 2, "ubs"))
        preload = json.loads(parser.values["preLoadJSON"])
        context = json.loads(preload["SmartSearchJSONValue"])
        body = {
            "partnerId": parser.values["partnerId"],
            "siteId": parser.values["siteId"],
            "keyword": "trading",
            "location": "",
            "keywordCustomSolrFields": context["KeywordCustomSolrFields"],
            "locationCustomSolrFields": context["LocationCustomSolrFields"],
            "linkId": parser.values["linkId"],
            "Latitude": 0,
            "Longitude": 0,
            "facetfilterfields": {"Facet": []},
            "powersearchoptions": {"PowerSearchOption": []},
            "SortType": "LastUpdated",
            "pageNumber": 1,
            "encryptedSessionValue": parser.values["CookieValue"],
        }
        result = await http.post_search_json(
            "https://jobs.ubs.com/TgNewUI/Search/Ajax/ProcessSortAndShowMoreJobs", body, 2, "ubs"
        )
        root = Path("data/discovery/lot5")
        root.mkdir(parents=True, exist_ok=True)
        # Persist public job results only, never the anonymous session/bootstrap fields.
        safe = {key: result.get(key) for key in ["Jobs", "JobsCount", "PageSize", "TotalJobsCount"]}
        (root / "ubs-search.json").write_text(json.dumps(safe, indent=2), encoding="utf-8")
        print("Count:", result.get("JobsCount"), "Keys:", list(result), flush=True)
        rows = (result.get("Jobs") or {}).get("Job") or []
        for row in rows[:5]:
            fields = {q["QuestionName"]: q.get("Value") for q in row["Questions"]}
            print(
                json.dumps({k: fields.get(k) for k in ["reqid", "jobtitle", "siteid"]}), flush=True
            )
        if rows:
            detail_url = rows[0]["Link"]
            if not detail_url.startswith(
                "https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?"
            ):
                raise ValueError("Unexpected detail URL")
            detail = Inputs()
            detail.feed(await http.get_text(detail_url, 2, "ubs"))
            public = json.loads(detail.values["preLoadJSON"])
            (root / "ubs-detail.json").write_text(
                json.dumps(
                    {
                        k: public.get(k)
                        for k in [
                            "Jobdetails",
                            "JobDetailFieldsToDisplay",
                            "googlejobsMappingfielddataJson",
                            "JobId",
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print("Saved public job detail fields")
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
