"""UBS public campus and professional boards, with anonymous bounded pagination."""

import asyncio
import html
import json
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

ROOT = "https://jobs.ubs.com"
BOARD = (
    ROOT
    + "/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5131&PageType=searchResults&SearchType=linkquery&LinkID=15232"
)
PROFESSIONAL_BOARD = BOARD.replace("siteid=5131", "siteid=5012").replace("15232", "15231")
BOARDS = {BOARD: ("5131", "15232"), PROFESSIONAL_BOARD: ("5012", "15231")}
SEARCH = ROOT + "/TgNewUI/Search/Ajax/ProcessSortAndShowMoreJobs"


class UBSOptions(SearchOptions):
    # Enumerate the selected board, then filter titles locally.
    search_terms: list[str] = Field(default_factory=list, max_length=0)


class PageInputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        key = attr.get("id")
        if tag == "input" and key in {
            "preLoadJSON",
            "CookieValue",
            "partnerId",
            "siteId",
            "linkId",
        }:
            if key in self.values:
                raise SourceUnavailable("ambiguous UBS page data")
            self.values[key] = attr.get("value") or ""


def page_data(text: str) -> tuple[dict[str, str], dict]:
    parser = PageInputs()
    parser.feed(text)
    try:
        data = json.loads(parser.values["preLoadJSON"])
        if not isinstance(data, dict) or data.get("ShowCaptcha") is True:
            raise ValueError
    except (ValueError, KeyError):
        raise SourceUnavailable("UBS public page data unavailable or access challenge") from None
    return parser.values, data


def detail_url(value: object, identifier: str | None = None, origin_site: str = "5131") -> str:
    if not isinstance(value, str):
        raise SourceUnavailable("UBS detail URL missing")
    parts = urlsplit(value)
    query = parse_qs(parts.query, keep_blank_values=True)
    if (
        parts.scheme != "https"
        or parts.netloc != "jobs.ubs.com"
        or parts.fragment
        or parts.path.lower() != "/tgnewui/search/home/homewithpreload"
        or set(query) - {"frmSiteId"} != {"partnerid", "siteid", "PageType", "jobid"}
        or ("frmSiteId" in query and query["frmSiteId"] != [origin_site])
        or any(len(v) != 1 for v in query.values())
        or query.get("partnerid") != ["25008"]
        or query.get("PageType") != ["JobDetails"]
        or not re.fullmatch(r"[0-9]+", query.get("siteid", [""])[0])
        or not re.fullmatch(r"[0-9]+", query.get("jobid", [""])[0])
        or (identifier is not None and query["jobid"] != [identifier])
    ):
        raise SourceUnavailable("invalid or mismatched UBS public job URL")
    return value


def fields(rows: object, key: str, value: str) -> dict[str, str]:
    if not isinstance(rows, list):
        raise SourceUnavailable("UBS job fields missing")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(key), str):
            raise SourceUnavailable("invalid UBS job field")
        name = row[key].lower()
        text = row.get(value)
        if not isinstance(text, str) or not name or name in result:
            raise SourceUnavailable("invalid or repeated UBS job field")
        result[name] = text
    return result


def parse_detail(data: dict, listing: dict, config: Company, source: str) -> RawJob | None:
    info = data.get("Jobdetails")
    if not isinstance(info, dict) or type(info.get("isActive")) is not bool:
        raise SourceUnavailable("UBS job detail missing")
    if not info["isActive"]:
        return None
    values = fields(info.get("JobDetailQuestions"), "VerityZone", "AnswerValue")
    identifier = listing["reqid"]
    url = detail_url(info.get("Link"), identifier, BOARDS[config.career_url][0])
    if (
        values.get("reqid") != identifier
        or not values.get("jobtitle", "").strip()
        or not values.get("jobdescription", "").strip()
    ):
        raise SourceUnavailable("UBS detail incomplete or mismatched")
    # Preserve every displayed text area, including the candidate requirements.
    sections = []
    for row in info["JobDetailQuestions"]:
        if row.get("QuestionType") == "textarea":
            label = row.get("QuestionName") or row["VerityZone"]
            sections.append(f"<h2>{html.escape(label)}</h2>" + row["AnswerValue"])
    if not sections:
        raise SourceUnavailable("UBS full description missing")
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=identifier,
        title=values["jobtitle"],
        description="\n".join(sections),
        apply_url=url,
        source_url=url,
        location=", ".join(x for x in [values.get("formtext2"), values.get("formtext23")] if x),
        # lastupdated is NOT the original publication date. Date-only deadlines need a timezone.
        raw_payload={"detail": info},
    )


class UBSCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url not in BOARDS or config.name != "UBS":
            raise ValueError("Use a verified UBS public campus or professional board")
        self.source, self.config, self.http = source, config, http
        self.site_id, self.link_id = BOARDS[config.career_url]
        self.options = UBSOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable(
                "UBS scan time budget exceeded; no snapshot committed"
            ) from None

    async def _list(self) -> dict[str, dict]:
        inputs, preload = page_data(
            await self.http.get_text(
                self.config.career_url, self.config.request_interval, self.source
            )
        )
        try:
            context = json.loads(preload["SmartSearchJSONValue"])
            if (
                inputs["partnerId"] != "25008"
                or inputs["siteId"] != self.site_id
                or inputs["linkId"] != self.link_id
                or not inputs["CookieValue"]
            ):
                raise ValueError
            body = {
                "partnerId": "25008",
                "siteId": self.site_id,
                "keyword": "",
                "location": "",
                "keywordCustomSolrFields": context["KeywordCustomSolrFields"],
                "locationCustomSolrFields": context["LocationCustomSolrFields"],
                "linkId": inputs["linkId"],
                "Latitude": 0,
                "Longitude": 0,
                "facetfilterfields": {"Facet": []},
                "powersearchoptions": {"PowerSearchOption": []},
                "SortType": "LastUpdated",
                "pageNumber": 1,
                "encryptedSessionValue": inputs["CookieValue"],
            }
        except (ValueError, KeyError, TypeError):
            raise SourceUnavailable("UBS anonymous search context missing") from None
        expected, page_size, number = None, None, 1
        found: dict[str, dict] = {}
        while expected is None or len(found) < expected:
            body["pageNumber"] = number
            result = await self.http.post_search_json(
                SEARCH, body, self.config.request_interval, self.source
            )
            if not isinstance(result, dict):
                raise SourceUnavailable("invalid UBS search response")
            total, size = result.get("JobsCount"), result.get("PageSize")
            # The public response reports 0 for its default; the UI paginates by 50.
            if type(size) is int and size == 0:
                size = 50
            rows = result.get("Jobs")
            rows = rows.get("Job") if isinstance(rows, dict) else None
            if total == 0 and rows is None:
                rows = []
            if (
                type(total) is not int
                or total < 0
                or type(size) is not int
                or not 1 <= size <= 100
                or not isinstance(rows, list)
            ):
                raise SourceUnavailable("invalid UBS pagination metadata")
            if total > self.options.max_results_per_query:
                raise SourceUnavailable("UBS result limit exceeded")
            if expected is not None and (total != expected or size != page_size):
                raise SourceUnavailable("UBS total or page size changed during pagination")
            expected, page_size = total, size
            if len(rows) != min(size, total - len(found)):
                raise SourceUnavailable("UBS returned a short or inconsistent page")
            for row in rows:
                if not isinstance(row, dict):
                    raise SourceUnavailable("invalid UBS listing")
                values = fields(row.get("Questions"), "QuestionName", "Value")
                identifier = values.get("reqid", "")
                if (
                    not re.fullmatch(r"[0-9]+", identifier)
                    or not values.get("jobtitle", "").strip()
                ):
                    raise SourceUnavailable("UBS listing identifier or title missing")
                values["url"] = detail_url(row.get("Link"), identifier, self.site_id)
                if identifier in found:
                    raise SourceUnavailable("UBS pagination repeated a posting")
                found[identifier] = values
            number += 1
        # Session/bootstrap context deliberately never enters RawJob or persisted payloads.
        return found

    def selected(self, title: str) -> bool:
        title = normalize_text(title)
        return (
            not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
        ) and not any(has(title, t) for t in self.options.exclude_title_terms)

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        rows = await self._list()
        targets = [row for row in rows.values() if self.selected(row["jobtitle"])]
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("UBS detail limit exceeded; narrow title scope")
        jobs = []
        for row in targets:
            _, data = page_data(
                await self.http.get_text(row["url"], self.config.request_interval, self.source)
            )
            job = parse_detail(data, row, self.config, self.source)
            if job is not None:
                jobs.append(job)
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
