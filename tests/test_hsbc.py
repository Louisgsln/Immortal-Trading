import asyncio

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.hsbc import (
    SEARCH,
    HSBCCollector,
    job_url,
    parse_cards,
    parse_detail,
    parse_index,
    utc_date,
)
from trading_radar.html_page import Document
from trading_radar.http import HTTPClient, SourceUnavailable


def config(**options):
    return Company(
        name="HSBC", ats="hsbc", career_url=SEARCH, request_interval=0.1, options=options
    )


def url(i=123, slug="Paris-Trading"):
    return f"https://apply.careers.hsbc.com/emergingtalent/job/{slug}/{i}/"


def card(i=123, title="Trading Graduate"):
    return f'<li class="program-item"><a class="program-text__destination-link" href="{url(i)}?feedId=1&amp;utm_source=test">{title}<span> (opens in new window)</span></a><div class="program-text__group"><dt>Programme type</dt><dd>Graduate Programme</dd></div><div class="program-text__group"><dt>Start Date</dt><dd>Mon Jul 19, 2027</dd></div></li>'


def listing(total=3, item=None):
    return f'<div data-component="ProgramFinder" data-props-settings="{"a" * 32}" data-props-skip="1" data-props-take="2" data-props-total-count="{total}"><ul class="program-finder-grid">{item or card()}</ul></div>'


def row():
    return parse_cards(Document(card()).root)[0]


def detail(i=123, title="Trading Graduate"):
    return f'<link rel="canonical" href="{url(i, "New-Slug")}"><div class="jobDisplayShell" itemtype="http://schema.org/JobPosting"><span itemprop="title">{title}</span><meta itemprop="datePosted" content="Wed Sep 02 02:00:00 UTC 2026"><meta itemprop="validThrough" content="Sat Oct 31 23:00:00 UTC 2026"><span itemprop="address"><meta itemprop="addressLocality" content="Paris"><meta itemprop="addressCountry" content="FR"></span><span class="jobdescription"><h2>Responsibilities</h2>Trade FX.<h2>Eligibility criteria</h2>Python and SQL. Less than 2 years experience.</span><a href="/talentcommunity/apply/{i}/?locale=en_GB">Apply</a></div>'


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("hsbc", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_programme_api_pagination_recheck_and_full_detail(monkeypatch):
    calls = []

    def handler(req):
        calls.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("find-a-programme"):
            return httpx.Response(200, text=listing())
        if req.url.path.endswith("get-programmes"):
            assert dict(req.url.params) == {"skip": "1", "take": "2", "count": "1", "s": "a" * 32}
            return httpx.Response(
                200,
                json=[
                    card(124, "Accounting Graduate"),
                    '<li class="content-card">Programme advice</li>',
                    card(125),
                ],
            )
        assert not req.url.query
        return httpx.Response(200, text=detail(123 if "/123/" in req.url.path else 125))

    result = execute(handler, monkeypatch)
    assert len(result.jobs) == 2 and not result.complete and result.requests == 7
    job = result.jobs[0]
    assert "Eligibility criteria" in job.description and "SQL" in job.description
    assert job.apply_url == url(123, "New-Slug")
    assert job.expected_start_date == "2027-07-19"
    assert job.date_posted.isoformat() == "2026-09-02T02:00:00+00:00"
    assert job.application_deadline.isoformat() == "2026-10-31T23:00:00+00:00"
    assert sum(call == SEARCH for call in calls) == 2


@pytest.mark.parametrize(
    "payload", [[], {}, [123], [card()], ["<li>unknown</li>"], [card(124), card(125), card(126)]]
)
def test_bad_fragment_pages_fail_atomically(monkeypatch, payload):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("find-a-programme"):
            return httpx.Response(200, text=listing())
        return httpx.Response(200, json=payload)

    with pytest.raises(SourceUnavailable):
        execute(handler, monkeypatch)


def test_catalogue_change_before_detail_fetch(monkeypatch):
    visits = 0

    def handler(req):
        nonlocal visits
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("find-a-programme"):
            visits += 1
            return httpx.Response(200, text=listing(1 if visits == 1 else 2))
        pytest.fail("No detail should be requested when catalogue changed")

    with pytest.raises(SourceUnavailable, match="catalogue changed"):
        execute(handler, monkeypatch)


@pytest.mark.parametrize(
    "old,new",
    [
        ("New-Slug/123/", "New-Slug/999/"),
        ("Trading Graduate", "Different job"),
        ('itemprop="addressCountry"', 'itemprop="other"'),
        ('itemprop="datePosted"', 'itemprop="other"'),
        ('class="jobdescription"', 'class="missing"'),
        ("/talentcommunity/apply/123/", "/talentcommunity/apply/999/"),
        ("Sat Oct 31 23:00:00 UTC 2026", "Sat Oct 31 23:00:00 UTC 2025"),
        ('rel="canonical"', 'rel="other"'),
    ],
)
def test_detail_metadata_validation(old, new):
    with pytest.raises(SourceUnavailable):
        parse_detail(detail().replace(old, new), row(), config(), "hsbc")


@pytest.mark.parametrize(
    "value", ["2026-10-31", "Sat Oct 31 23:00:00 EST 2026", "Wed Feb 31 23:00:00 UTC 2026"]
)
def test_no_implicit_timezone_or_invalid_date(value):
    with pytest.raises(SourceUnavailable):
        utc_date(value)


def test_multiple_cities_are_kept_without_merging_their_addresses():
    text = detail().replace(
        '<span itemprop="address">',
        '<span itemprop="address"><meta itemprop="addressLocality" content="Lyon"><meta itemprop="addressCountry" content="FR"></span><span itemprop="address">',
    )
    assert parse_detail(text, row(), config(), "hsbc").location == "Lyon, FR; Paris, FR"
    with pytest.raises(SourceUnavailable, match="conflicting address"):
        parse_detail(
            detail().replace(
                'content="Paris">',
                'content="Paris"><meta itemprop="addressLocality" content="Lyon">',
            ),
            row(),
            config(),
            "hsbc",
        )


def test_card_and_index_validation():
    for text in [
        card().replace("Mon Jul 19, 2027", "Unknown"),
        card().replace("Programme type", "Other"),
        card().replace('class="program-text__destination-link"', 'class="missing"'),
    ]:
        with pytest.raises(SourceUnavailable):
            parse_cards(Document(text).root)
    for text in [
        "<html>unavailable</html>",
        listing().replace("a" * 32, "invalid"),
        listing().replace('data-props-total-count="3"', 'data-props-total-count="many"'),
        listing().replace('data-props-skip="1"', 'data-props-skip="2"'),
    ]:
        with pytest.raises(SourceUnavailable):
            parse_index(text, 100)
    with pytest.raises(SourceUnavailable):
        parse_index(listing(), 1)


def test_url_and_config_scope():
    for value in [
        url().replace("https", "http"),
        url().replace("apply.careers.hsbc.com", "evil.test"),
        "https://apply.careers.hsbc.com/account/login",
    ]:
        with pytest.raises(SourceUnavailable):
            job_url(value)
    with pytest.raises(ValueError):
        HSBCCollector("hsbc", config(search_terms=["trading"]), None)
    cfg = config()
    cfg.career_url = "https://evil.test"
    with pytest.raises(ValueError):
        HSBCCollector("hsbc", cfg, None)


def test_detail_budget(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("find-a-programme"):
            return httpx.Response(200, text=listing(2))
        return httpx.Response(200, json=[card(124)])

    with pytest.raises(SourceUnavailable, match="detail limit"):
        execute(handler, monkeypatch, max_details=1)
