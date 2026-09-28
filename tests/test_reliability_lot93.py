import asyncio
import json
from collections import defaultdict

import httpx
import pytest
from test_ubs import bootstrap, listing

from trading_radar.bnp import BNPCollector
from trading_radar.config import Company, load_config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.optiver import SEARCH, OptiverCollector
from trading_radar.snapshot_retry import SnapshotChanged
from trading_radar.ubs import BOARD, UBSCollector
from trading_radar.workday import WorkdayCollector
from trading_radar.workday_recovery import (
    BP,
    CITI,
    SITES,
    citi_operations_reference,
    citi_result,
    public_reference_title,
    verified_title,
)

REF = "12345678"
URL = CITI + "/job/london/operations-analyst/287/1234"


def detail(source="citi", **changes):
    info = {
        "@type": "JobPosting",
        "title": "Operations Analyst",
        "identifier": REF,
        "url": URL,
        "hiringOrganization": {"name": "bp"},
    }
    info.update(changes)
    link = (
        SITES["citi"] + "/job/London/Operations-Analyst_" + REF + "/apply"
        if source == "citi"
        else "/job/apply/london-operations-analyst-rq123456?"
    )
    return (
        '<script type="application/ld+json">'
        + json.dumps(info)
        + "</script>"
        + f'<h1>{info["title"]}</h1><a href="{link}">Apply</a>'
    )


def search(**attrs):
    values = {
        "id": "search-results",
        "data-keywords": REF,
        "data-total-results": "1",
        "data-total-job-results": "1",
        "data-total-pages": "1",
        "data-current-page": "1",
    }
    values.update(attrs)
    attributes = " ".join(f'{k}="{v}"' for k, v in values.items())
    return (
        f'<section {attributes}><a href="{URL.removeprefix(CITI)}">Operations Analyst</a></section>'
    )


def test_reference_search_requires_one_exact_public_result():
    assert citi_result(search(), REF) == URL
    for key in [
        "data-keywords",
        "data-total-results",
        "data-total-job-results",
        "data-total-pages",
        "data-current-page",
    ]:
        assert citi_result(search(**{key: "2"}), REF) is None
    assert citi_result(search() * 2, REF) is None
    assert citi_result(search().replace("/job/london/", "//evil.test/job/london/"), REF) is None


@pytest.mark.parametrize(
    "changes", [{"identifier": "87654321"}, {"url": URL + "x"}, {"title": ""}, {"title": None}]
)
def test_citi_identity_disagreement_remains_a_gap(changes):
    assert verified_title(detail(**changes), "citi", REF, URL) is None


@pytest.mark.parametrize(
    "transform",
    [
        lambda t: t.replace("citi.wd5.myworkdayjobs.com", "evil.test"),
        lambda t: t.replace("_12345678/apply", "_87654321/apply"),
        lambda t: t.replace("_12345678/apply", "_12345678/apply?token=x"),
        lambda t: t.replace("<h1>Operations Analyst</h1>", "<h1>Trading Analyst</h1>"),
        lambda t: t + "<h1>Operations Analyst</h1>",
        lambda t: t + t,
        lambda t: t.replace('"@type": "JobPosting"', '"@type": "Event"'),
    ],
)
def test_citi_page_must_identify_one_title_and_requisition(transform):
    assert verified_title(transform(detail()), "citi", REF, URL) is None


def test_bp_requires_exact_employer_route_and_application_reference():
    page = detail("bp")
    url = BP + "/job-description/RQ123456"
    assert verified_title(page, "bp", "RQ123456", url) == "Operations Analyst"
    assert verified_title(page, "bp", "RQ654321", url) is None
    assert verified_title(page, "bp", "RQ123456", url + "x") is None
    assert verified_title(page.replace("rq123456", "rq654321"), "bp", "RQ123456", url) is None
    assert (
        verified_title(detail("bp", hiringOrganization={"name": "other"}), "bp", "RQ123456", url)
        is None
    )


class FakeHTTP:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.counts = defaultdict(int)

    async def get_text(self, url, interval, source):
        self.calls.append(url)
        self.counts[source] += 1
        result = self.pages[url]
        if isinstance(result, Exception):
            raise result
        return result


def test_reference_recovery_has_exact_host_scope_and_two_request_bound():
    h = FakeHTTP({CITI + "/search-jobs?k=" + REF: search(), URL: detail()})
    assert (
        asyncio.run(public_reference_title("citi", SITES["citi"], REF, h, 2))
        == "Operations Analyst"
    )
    assert len(h.calls) == 2
    for source, site, ref in [
        ("other", SITES["citi"], REF),
        ("citi", "https://evil.test/2", REF),
        ("citi", SITES["citi"], "12?x=1"),
    ]:
        assert asyncio.run(public_reference_title(source, site, ref, h, 2)) is None
    assert len(h.calls) == 2


@pytest.mark.parametrize(
    "value", [search(**{"data-total-results": "0"}), search() * 2, SourceUnavailable("HTTP 403")]
)
def test_reference_not_found_ambiguous_or_blocked_never_clears_gap(value):
    h = FakeHTTP({CITI + "/search-jobs?k=" + REF: value})
    assert asyncio.run(public_reference_title("citi", SITES["citi"], REF, h, 2)) is None
    assert len(h.calls) == 1


def operation_evidence():
    return {
        "total": 1,
        "jobPostings": [{"bulletFields": [REF]}],
        "facets": [
            {
                "facetParameter": "jobFamilyGroup",
                "values": [
                    {
                        "descriptor": "Operations - Transaction Services",
                        "id": "e32326e1708d01add154fc0c1201f6c0",
                        "count": 1,
                    }
                ],
            }
        ],
    }


def test_citi_classification_requires_exact_single_reference_and_audited_category():
    evidence = operation_evidence()
    assert citi_operations_reference(evidence, REF)
    assert not citi_operations_reference(evidence, "87654321")
    for total in [0, 2, True, "1"]:
        assert not citi_operations_reference({**evidence, "total": total}, REF)
    for key, value in [
        ("descriptor", "Institutional Trading"),
        ("id", "other"),
        ("count", 2),
        ("count", True),
    ]:
        changed = operation_evidence()
        changed["facets"][0]["values"][0][key] = value
        assert not citi_operations_reference(changed, REF)
    assert not citi_operations_reference({**evidence, "facets": evidence["facets"] * 2}, REF)


@pytest.mark.parametrize(
    "title,expected_gap", [("Operations Analyst", False), ("Trading Analyst", True), (None, True)]
)
def test_only_verified_out_of_scope_reference_closes_gap(monkeypatch, title, expected_gap):
    h = FakeHTTP({})
    cfg = Company(name="BP", ats="workday", career_url=SITES["bp"])
    c = WorkdayCollector("bp", cfg, h)

    async def listing(_):
        c.listing_gaps.add("RQ123456")
        return {"unavailable:RQ123456": {"bulletFields": ["RQ123456"]}}

    async def recover(*_):
        return title

    monkeypatch.setattr(c, "_search", listing)
    monkeypatch.setattr("trading_radar.workday.public_reference_title", recover)
    result = asyncio.run(c.collect())
    assert result.listing_gaps == (["RQ123456"] if expected_gap else [])
    assert not result.jobs and not result.complete


def test_bnp_scope_excludes_explicit_internships_but_keeps_analyst_associate():
    c = BNPCollector("bnp_paribas", load_config().companies["bnp_paribas"], FakeHTTP({}))
    for title in [
        "Stage - Assistant Trader (H/F)",
        "Trading Internship",
        "Intern - Trading",
        "Stagiaire Trading",
    ]:
        assert not c.selected(title)
    for title in [
        "Trading Analyst",
        "Trading Analyst / Associate",
        "Graduate Trader",
        "Trading - International Markets",
    ]:
        assert c.selected(title)


def optiver_row(i):
    return {"componentID": i, "url": f"https://www.optiver.com/job-{i}", "title": "Trader"}


@pytest.mark.parametrize("broken", [None, "missing", "changed", "url_alias"])
def test_optiver_boundary_overlap_recovers_all_unique_records_or_fails(monkeypatch, broken):
    c = OptiverCollector(
        "optiver", Company(name="Optiver", ats="optiver", career_url=SEARCH), FakeHTTP({})
    )
    monkeypatch.setattr("trading_radar.optiver.PAGE_SIZE", 3)
    pages = {
        0: [optiver_row(i) for i in [1, 2, 3]],
        2: [optiver_row(i) for i in [3, 4, 5]],
        4: [optiver_row(i) for i in [5, 6]],
    }
    if broken == "missing":
        pages[4] = [optiver_row(i) for i in [4, 5]]
    if broken == "changed":
        pages[2][0]["title"] = "Different"
    if broken == "url_alias":
        pages[4][1]["url"] = pages[0][0]["url"]
    calls = []

    async def page(offset):
        calls.append(offset)
        return pages[offset], 6

    monkeypatch.setattr(c, "page", page)
    if broken:
        with pytest.raises(SnapshotChanged):
            asyncio.run(c._list())
    else:
        assert {r["componentID"] for r in asyncio.run(c._list())} == set(range(1, 7))
        assert calls == [0, 2, 4, 0]


def test_ubs_query_union_keeps_ids_and_rejects_conflicting_rows(monkeypatch):
    cfg = Company(
        name="UBS",
        ats="ubs",
        career_url=BOARD,
        options={"partition_titles": True, "title_terms": ["trading", "markets"]},
    )
    c = UBSCollector("ubs", cfg, FakeHTTP({}))
    calls = []

    async def listing(term):
        calls.append(term)
        return {"1": {"jobtitle": "Trading Markets Analyst"}, term: {"jobtitle": term}}

    monkeypatch.setattr(c, "_list", listing)
    assert set(asyncio.run(c._scope())) == {"1", "trading", "markets"}
    assert calls == ["trading", "markets"]

    async def contradiction(term):
        return {"1": {"jobtitle": term}}

    monkeypatch.setattr(c, "_list", contradiction)
    with pytest.raises(SnapshotChanged):
        asyncio.run(c._scope())


@pytest.mark.parametrize("terms", [[], ["x"] * 11, [""], ["x" * 101]])
def test_ubs_partitions_remain_bounded(terms):
    cfg = Company(
        name="UBS",
        ats="ubs",
        career_url=BOARD,
        options={"partition_titles": True, "title_terms": terms},
    )
    with pytest.raises(SourceUnavailable):
        asyncio.run(UBSCollector("ubs", cfg, FakeHTTP({}))._scope())


@pytest.mark.parametrize("failure", [None, "scope_changed", "token_missing", "token_duplicate"])
def test_ubs_real_keyword_protocol_uses_anonymous_form_token(monkeypatch, failure):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    calls = []
    token = '<input name="__RequestVerificationToken" value="synthetic-form-token">'

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method == "GET":
            return httpx.Response(
                200,
                text=bootstrap()
                + token
                * (0 if failure == "token_missing" else 2 if failure == "token_duplicate" else 1),
            )
        body = json.loads(req.content)
        calls.append((req.url.path, body))
        if req.url.path.endswith("MatchedJobs"):
            assert req.headers["RFT"] == "synthetic-form-token"
            assert body["Keyword"] == "trading" and body["SiteId"] == "5131"
            return httpx.Response(
                200, json={"JobsCount": 1, "PageSize": 0, "Jobs": {"Job": [listing()]}}
            )
        assert (
            body["keyword"] == "trading" and body["linkId"] == "" and body["SortType"] == "JobTitle"
        )
        assert "RFT" not in req.headers
        return httpx.Response(
            200,
            json={
                "JobsCount": 2 if failure == "scope_changed" else 1,
                "PageSize": 0,
                "Jobs": {"Job": [listing()]},
            },
        )

    async def run():
        h = HTTPClient(retries=0, transport=httpx.MockTransport(handler))
        try:
            c = UBSCollector("ubs", Company(name="UBS", ats="ubs", career_url=BOARD), h)
            return await c._list("trading")
        finally:
            await h.close()

    if failure:
        with pytest.raises(SourceUnavailable):
            asyncio.run(run())
    else:
        rows = asyncio.run(run())
        assert list(rows) == ["123"] and len(calls) == 3
        assert "synthetic" not in json.dumps(rows)
