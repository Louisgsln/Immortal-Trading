import asyncio

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.macquarie import (
    DETAIL,
    SEARCH,
    MacquarieCollector,
    job_url,
    parse_detail,
    parse_page,
)


def config(**options):
    return Company(
        name="Macquarie", ats="macquarie", career_url=SEARCH, request_interval=0.1, options=options
    )


def row(i=123, title="Trading Analyst"):
    return {"id": str(i), "title": title, "url": DETAIL + f"?jobId={i}"}


def card(i=123, title="Trading Analyst"):
    return f'<article class="article--result"><h3><a href="{row(i)["url"]}">{title}</a></h3><a href="{row(i)["url"]}">View details</a></article>'


def page(cards, total=None, number=1, term="trading"):
    total = len(cards) if total is None else total
    return (
        f'<input name="search" value="{term}"><h2 class="section__header--top">{total} items</h2><span class="currentPageLink">Page {number}</span>'
        + "".join(cards)
    )


def field(value, label="", cls=""):
    label = f'<div class="article__content__view__field__label">{label}</div>' if label else ""
    return f'<div class="article__content__view__field {cls}">{label}<div class="article__content__view__field__value">{value}</div></div>'


def detail(i=123, contract="Permanent - Full time, Junior, Mid-level"):
    metadata = (
        field(str(i), "Job ID", "field--jobcategory")
        + field("London", "Additional office locations", "field--location")
        + field(contract, cls="field--employmentterm")
        + field("16-Sep-2026", "Date", "field--date")
    )
    body = (
        "<article><h3>What role will you play?</h3>"
        + field("Trade FX and derivatives")
        + "</article><article><h3>What you offer</h3>"
        + field("Python and SQL required; zero to two years experience")
        + "</article>"
    )
    return (
        '<h2 class="title--11">Trading Analyst</h2><article class="article__content__fields">'
        + metadata
        + '</article><section class="section--without--border--top">'
        + body
        + "</section>"
    )


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    monkeypatch.setattr("trading_radar.macquarie.PAGE_SIZE", 2)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("macquarie", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_search_pagination_filter_and_cross_query_dedup(monkeypatch):
    details = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "SearchJobs" in req.url.path:
            assert req.url.params["jobRecordsPerPage"] == "2"
            offset = int(req.url.params["jobOffset"])
            return httpx.Response(
                200,
                text=page(
                    [card(123), card(124, "Accountant")] if offset == 0 else [card(125)],
                    3,
                    offset // 2 + 1,
                    req.url.params["search"],
                ),
            )
        identifier = int(req.url.params["jobId"])
        details.append(identifier)
        return httpx.Response(200, text=detail(identifier))

    result = execute(handler, monkeypatch, search_terms=["trading", "structuring"])
    assert details == [123, 125] and not result.complete and result.requests == 7
    assert result.jobs[0].seniority_hint == "junior"
    assert result.jobs[0].date_posted is None and result.jobs[0].expected_start_date is None
    assert "Python and SQL required" in result.jobs[0].description


@pytest.mark.parametrize("failure", ["duplicate", "count", "wrong_page", "filter", "short", "http"])
def test_later_page_errors_are_atomic(monkeypatch, failure):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert "SearchJobs" in req.url.path
        if req.url.params["jobOffset"] == "0":
            return httpx.Response(200, text=page([card(123), card(124)], 3))
        if failure == "http":
            return httpx.Response(403)
        return httpx.Response(
            200,
            text=page(
                [] if failure == "short" else [card(123 if failure == "duplicate" else 125)],
                4 if failure == "count" else 3,
                1 if failure == "wrong_page" else 2,
                "other" if failure == "filter" else "trading",
            ),
        )

    with pytest.raises(SourceUnavailable):
        execute(handler, monkeypatch)


@pytest.mark.parametrize(
    "old,new",
    [
        ("Trading Analyst", "Wrong title"),
        ("Job ID", "Other ID"),
        ("London", ""),
        ("What you offer", "Other heading"),
        ("Python and SQL required; zero to two years experience", ""),
        ("Trade FX and derivatives", ""),
        ("Permanent - Full time, Junior, Mid-level", ""),
    ],
)
def test_detail_validation(old, new):
    with pytest.raises(SourceUnavailable):
        parse_detail(detail().replace(old, new), row(), config(), "mac")


@pytest.mark.parametrize(
    "levels,hint",
    [
        ("Senior", "senior"),
        ("Mid-senior", "senior"),
        ("Mid-senior, Senior", "senior"),
        ("Junior", "junior"),
        ("Junior, Mid-level", "junior"),
        ("Mid-level, Senior", None),
        ("Mid-level", None),
    ],
)
def test_explicit_seniority(levels, hint):
    job = parse_detail(detail(contract="Permanent - Full time, " + levels), row(), config(), "mac")
    assert job.seniority_hint == hint


@pytest.mark.parametrize(
    "requirement,minimum",
    [
        ("6-10 years’ experience trading rates", 6),
        ("1-3 years relevant experience", 1),
        ("2–4 years of experience", 2),
        ("Graduate by 2027", None),
    ],
)
def test_experience_range_only_from_requirements(requirement, minimum):
    text = detail().replace("Python and SQL required; zero to two years experience", requirement)
    text = text.replace("Trade FX and derivatives", "Our desk has 25-30 years experience")
    assert parse_detail(text, row(), config(), "mac").minimum_experience_years == minimum
    with pytest.raises(SourceUnavailable, match="contradictory experience"):
        parse_detail(
            detail().replace(
                "Python and SQL required; zero to two years experience", "10-6 years experience"
            ),
            row(),
            config(),
            "mac",
        )


def test_scope_limits_and_malformed_cards():
    for url in [
        DETAIL + "?jobId=123&redirect=other",
        DETAIL + "?jobId=123&jobId=456",
        DETAIL + "?jobId=abc",
        DETAIL.replace("https", "http") + "?jobId=123",
        "https://evil.test/en_US/careers/JobDetail?jobId=123",
    ]:
        with pytest.raises(SourceUnavailable):
            job_url(url)
    for text, limit in [
        ("<html>unavailable</html>", 10),
        (page([card()]), 0),
        (page([card()]).replace("123", "bad"), 10),
        (page([card(), card()]), 10),
    ]:
        with pytest.raises(SourceUnavailable):
            parse_page(text, "trading", 0, limit)
    cfg = config()
    cfg.career_url = "https://evil.test"
    with pytest.raises(ValueError):
        MacquarieCollector("mac", cfg, None)


def test_detail_budget(monkeypatch):
    def handler(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, text=page([card(123), card(124)]))
        )

    with pytest.raises(SourceUnavailable, match="detail limit"):
        execute(handler, monkeypatch, max_details=1)
