import asyncio
import html
import json

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.hsbc_professionals import BOARD, job_url, parse_detail, parse_page, position
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def company(**options):
    return Company(name="HSBC", ats="hsbc_professionals", career_url=BOARD, options=options)


def row(i=1, **changes):
    return (
        dict(
            id=i,
            name="Fixed Income Trading Associate",
            posting_name="Fixed Income Trading Associate",
            ats_job_id=str(i + 1000),
            locations=["Istanbul, Turkiye"],
            canonicalPositionUrl=BOARD + f"/job/{i}",
            isPrivate=False,
            type="ATS",
            business_unit="Corp & Inst Banking",
        )
        | changes
    )


def listing(rows, total=None, **changes):
    return (
        dict(
            domain="hsbc.com",
            isUserAuthenticated=False,
            query={"query": "trading", "location": ""},
            positions=rows,
            count=len(rows) if total is None else total,
        )
        | changes
    )


def detail_data(item):
    data = listing(
        [item],
        pid=str(item["id"]),
        singleview=True,
        isFallback=False,
        candidate={"enc_id": "must-not-be-stored"},
    )
    schema = {
        "@type": "JobPosting",
        "hiringOrganization": {"name": "HSBC"},
        "title": item["name"],
        "description": "Trade FX and government bonds. Minimum 4 years work experience. Python.",
        "employmentType": "FULL_TIME",
        "url": item["canonicalPositionUrl"] + "-trader?domain=hsbc.com",
        "datePosted": "2026-09-11T12:49:15",
        "validThrough": "2027-03-10T12:49:15",
    }
    return data, schema


def detail_html(data, schema):
    return (
        '<code id="smartApplyData">' + html.escape(json.dumps(data)) + "</code>"
        '<script type="application/ld+json">' + json.dumps(schema) + "</script>"
    )


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("hsbc_professionals", company(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_public_search_pagination_wealth_filter_and_full_detail(monkeypatch, config):
    offsets = []
    detail_ids = []
    items = [row()] + [row(i, name="Accountant", posting_name="Accountant") for i in range(2, 11)]
    items += [row(11, business_unit="Intl Wealth & Premier Banking")]

    def handler(req):
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\nDisallow: /\nAllow: /careers\nAllow: /api/apply"
            )
        if req.url.path == "/api/apply/v2/jobs":
            assert req.url.params["domain"] == "hsbc.com" and req.url.params["num"] == "10"
            offset = int(req.url.params["start"])
            offsets.append(offset)
            return httpx.Response(200, json=listing(items[offset : offset + 10], 11))
        detail_ids.append(req.url.path)
        return httpx.Response(200, text=detail_html(*detail_data(items[0])))

    result = execute(handler, monkeypatch)
    assert offsets == [0, 10, 0] and detail_ids == ["/careers/job/1"]
    assert not result.complete and result.requests == 5 and len(result.jobs) == 1
    raw = result.jobs[0]
    assert raw.external_id == "1" and raw.employment_type == "FULL_TIME"
    assert raw.date_posted is None and raw.application_deadline is None
    assert raw.expected_start_date is None and raw.seniority_hint is None
    assert "must-not-be-stored" not in raw.model_dump_json()
    assert "Minimum 4 years" in normalize(raw).description_text
    assert score_job(normalize(raw), config.keywords).score_breakdown.junior == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"count": 2000},
        {"count": True},
        {"positions": []},
        {"count": 2},
        {"domain": "other.com"},
        {"isUserAuthenticated": True},
        {"query": {"query": "other", "location": ""}},
        {"query": {"query": "trading", "location": "London"}},
        {"positions": [row(), row()], "count": 2},
    ],
)
def test_invalid_search_page_rejected(changes):
    with pytest.raises(SourceUnavailable):
        parse_page(listing([row()]) | changes, "trading", 0, 1999)


@pytest.mark.parametrize(
    "changes",
    [
        {"id": True},
        {"id": 0},
        {"isPrivate": True},
        {"isPrivate": None},
        {"type": "PROSPECT"},
        {"posting_name": "Different title"},
        {"ats_job_id": ""},
        {"locations": []},
        {"locations": [None]},
        {"canonicalPositionUrl": "https://evil.example/1"},
        {"business_unit": []},
    ],
)
def test_invalid_or_private_position_rejected(changes):
    with pytest.raises(SourceUnavailable):
        position(row(**changes))


@pytest.mark.parametrize(
    "url",
    [
        BOARD + "/job/2",
        BOARD + "/job/1#apply",
        BOARD + "/job/1?token=x",
        BOARD + "/job/1/other",
        BOARD + "/job/1?domain=hsbc.com&domain=evil.com",
        "http://portal.careers.hsbc.com/careers/job/1",
    ],
)
def test_detail_url_boundary(url):
    with pytest.raises(SourceUnavailable, match="URL"):
        job_url(url, "1")


@pytest.mark.parametrize(
    "field,value",
    [
        ("pid", "2"),
        ("isFallback", True),
        ("singleview", False),
        ("positions", []),
        ("isUserAuthenticated", True),
    ],
)
def test_detail_context_must_match_listing(field, value):
    item = row()
    data, schema = detail_data(item)
    data[field] = value
    with pytest.raises(SourceUnavailable):
        parse_detail(detail_html(data, schema), position(item), company(), "hsbc_professionals")


@pytest.mark.parametrize(
    "field,value",
    [
        ("@type", "Event"),
        ("title", "Other"),
        ("description", ""),
        ("hiringOrganization", {"name": "Other"}),
        ("employmentType", None),
        ("url", BOARD + "/job/2"),
    ],
)
def test_detail_requires_full_matching_jobposting(field, value):
    item = row()
    data, schema = detail_data(item)
    schema[field] = value
    with pytest.raises(SourceUnavailable):
        parse_detail(detail_html(data, schema), position(item), company(), "hsbc_professionals")


@pytest.mark.parametrize(
    "text",
    [
        "<html>challenge</html>",
        '<code id="smartApplyData">invalid</code><script type="application/ld+json">{}</script>',
    ],
)
def test_missing_or_invalid_embedded_data(text):
    with pytest.raises(SourceUnavailable):
        parse_detail(text, position(row()), company(), "hsbc_professionals")


@pytest.mark.parametrize("failure", ["total", "repeat", "recheck", "detail_limit"])
def test_unstable_search_or_limits_fail_without_partial_result(monkeypatch, failure):
    calls = 0

    def handler(req):
        nonlocal calls
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert req.url.path == "/api/apply/v2/jobs"
        calls += 1
        offset = int(req.url.params["start"])
        total = 12 if failure == "total" and offset else 11
        if offset:
            items = [row(1 if failure == "repeat" else 11)]
            if total == 12:
                items.append(row(12))
        else:
            items = [row(i) for i in range(1, 11)]
            if failure == "recheck" and calls % 3 == 0:
                items[0] = row(99)
        return httpx.Response(200, json=listing(items, total))

    with pytest.raises(
        SourceUnavailable,
        match={
            "total": "total changed",
            "repeat": "repeated page",
            "recheck": "search changed",
            "detail_limit": "detail limit",
        }[failure],
    ):
        execute(handler, monkeypatch, max_details=1 if failure == "detail_limit" else 250)


def test_empty_public_result(monkeypatch):
    def handler(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, json=listing([]))
        )

    result = execute(handler, monkeypatch)
    assert result.jobs == [] and not result.complete


def test_cross_query_deduplication(monkeypatch):
    details = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/api/apply/v2/jobs":
            return httpx.Response(
                200, json=listing([row()], query={"query": req.url.params["query"], "location": ""})
            )
        details.append(req.url.path)
        return httpx.Response(200, text=detail_html(*detail_data(row())))

    result = execute(handler, monkeypatch, search_terms=["trading", "markets"])
    assert len(result.jobs) == 1 and len(details) == 1


@pytest.mark.parametrize("failure", ["total", "repeat", "recheck"])
def test_changing_listing_restarts_once_and_discards_first_snapshot(monkeypatch, failure):
    old = [row(i) for i in range(1, 11)]
    fresh = [row(i) for i in range(101, 111)]
    pages = [(0, listing(old, 11))]
    if failure == "total":
        pages.append((10, listing([row(11), row(12)], 12)))
    if failure == "repeat":
        pages.append((10, listing([row(1)], 11)))
    if failure == "recheck":
        pages += [(10, listing([row(11)], 11)), (0, listing([row(99), *old[1:]], 11))]
    pages += [(0, listing(fresh, 11)), (10, listing([row(111)], 11)), (0, listing(fresh, 11))]
    number_of_pages = len(pages)
    details = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/api/apply/v2/jobs":
            offset, payload = pages.pop(0)
            assert int(req.url.params["start"]) == offset
            return httpx.Response(200, json=payload)
        assert not pages  # No details may be fetched from the abandoned listing.
        identifier = int(req.url.path.rsplit("/", 1)[1])
        details.append(identifier)
        assert 101 <= identifier <= 111
        return httpx.Response(200, text=detail_html(*detail_data(row(identifier))))

    result = execute(handler, monkeypatch)
    assert {j.external_id for j in result.jobs} == {str(i) for i in range(101, 112)}
    assert len(details) == 11 and result.complete is False
    assert result.requests == number_of_pages + 11 + 1  # includes robots and failed traversal


def test_restart_clears_results_from_earlier_search_terms(monkeypatch):
    pages = [
        ("trading", 0, listing([row(1)])),
        ("trading", 0, listing([row(1)])),
        ("markets", 0, listing([row(2)])),
        ("markets", 0, listing([row(3)])),
        ("trading", 0, listing([row(101)])),
        ("trading", 0, listing([row(101)])),
        ("markets", 0, listing([row(101)])),
        ("markets", 0, listing([row(101)])),
    ]
    details = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/api/apply/v2/jobs":
            term, offset, payload = pages.pop(0)
            assert req.url.params["query"] == term and int(req.url.params["start"]) == offset
            payload["query"]["query"] = term
            return httpx.Response(200, json=payload)
        details.append(req.url.path)
        assert not pages and req.url.path.endswith("/101")
        return httpx.Response(200, text=detail_html(*detail_data(row(101))))

    result = execute(handler, monkeypatch, search_terms=["trading", "markets"])
    assert len(result.jobs) == 1 and len(details) == 1
    assert result.jobs[0].external_id == "101"


@pytest.mark.parametrize("failure", ["403", "429", "malformed", "private", "identity", "detail"])
def test_restrictions_schema_or_detail_failures_do_not_restart(monkeypatch, failure):
    api_calls = 0
    detail_calls = 0

    def handler(req):
        nonlocal api_calls, detail_calls
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/api/apply/v2/jobs":
            api_calls += 1
            if failure in {"403", "429"}:
                return httpx.Response(int(failure))
            payload = listing([row()])
            if failure == "malformed":
                payload["positions"] = []
            if failure == "private":
                payload["positions"][0]["isPrivate"] = True
            if failure == "identity":
                payload["positions"][0]["canonicalPositionUrl"] = "https://evil.test/job/1"
            return httpx.Response(200, json=payload)
        detail_calls += 1
        return httpx.Response(200, text="<p>No matching posting metadata.</p>")

    with pytest.raises(SourceUnavailable):
        execute(handler, monkeypatch)
    assert api_calls == (2 if failure == "detail" else 1)
    assert detail_calls == (1 if failure == "detail" else 0)


def test_two_traversals_share_original_timeout(monkeypatch):
    original_timeout = asyncio.timeout
    original_sleep = asyncio.sleep
    budgets = []
    calls = 0

    def shortened_budget(seconds):
        budgets.append(seconds)
        return original_timeout(0.03)

    monkeypatch.setattr("trading_radar.hsbc_professionals.asyncio.timeout", shortened_budget)

    async def handler(req):
        nonlocal calls
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        calls += 1
        if calls == 1:
            return httpx.Response(200, json=listing([row(1)]))
        if calls == 2:
            return httpx.Response(200, json=listing([row(2)]))
        await original_sleep(0.1)
        pytest.fail("The retry must remain within the original deadline")

    with pytest.raises(SourceUnavailable, match="scan time budget exceeded"):
        execute(handler, monkeypatch)
    assert budgets == [600] and calls == 3
