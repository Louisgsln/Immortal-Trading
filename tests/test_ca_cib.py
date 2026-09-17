import asyncio

import httpx
import pytest

from trading_radar.ca_cib import SEARCH, CACIBCollector, job_url, parse_detail, parse_page
from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable


def config(**options):
    return Company(
        name="Crédit Agricole CIB",
        ats="ca_cib",
        career_url=SEARCH,
        request_interval=0.1,
        options=options,
    )


def row(i=123):
    return {
        "id": str(i),
        "reference": f"2026-{i}",
        "title": "Trading Analyst",
        "url": f"https://jobs.ca-cib.com/offre-de-emploi/emploi-trading-analyst_{i}.aspx",
    }


def card(i=123, title="Trading Analyst"):
    r = row(i)
    return f'<a class="ts-offer-card__title-link" href="{r["url"]}" title="{r["reference"]}">{title}</a>'


def listing(cards, total=None, page=1):
    total = len(cards) if total is None else total
    return (
        f'<div class="ts-ol-pagination__title">Nombre de résultats : {total} offre(s)</div><span class="ts-ol-pagination-list-item__link--active">{page}</span>'
        + "".join(cards)
    )


def detail(i=123, **changes):
    fields = {
        "fldjobdescription_jobtitle": "Trading Analyst",
        "fldjobdescription_description1": "Pricing FX on a trading desk.",
        "fldjobdescription_contract": "Permanent",
        "fldjobdescription_date1": "19/07/2027",
        "fldlocation_joblocation": "Paris",
        "fldlocation_location_geographicalareacollection": "Europe, France",
        "fldapplicantcriteria_freecriteria1": "SQL and Python required.",
        "fldapplicantcriteria_experiencelevel": "0-2 years",
        **changes,
    }
    return (
        f'<h1 class="ts-offer-page__title">Trading Analyst</h1><div class="ts-offer-page__reference"><h3>Reference</h3>2026-{i}</div><div class="ts-offer-page__maj-date">Update date 01/09/2026</div>'
        + "".join(f'<div id="{k}">{v}</div>' for k, v in fields.items())
    )


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    monkeypatch.setattr("trading_radar.ca_cib.PAGE_SIZE", 2)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("ca", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_paginate_full_board_before_filter_and_fetch_all_requirements(monkeypatch):
    paths = []

    def handler(req):
        paths.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("listeoffre.aspx"):
            assert req.url.params["LCID"] == "1036"
            page = int(req.url.params["page"])
            return httpx.Response(
                200,
                text=listing(
                    [card(123), card(124, "Accountant")] if page == 1 else [card(125)], 3, page
                ),
            )
        return httpx.Response(200, text=detail(123 if "_123." in req.url.path else 125))

    result = execute(handler, monkeypatch)
    assert len(result.jobs) == 2 and not result.complete and result.requests == 5
    assert result.jobs[0].external_id == "2026-123"
    assert "SQL and Python required" in result.jobs[0].description
    assert result.jobs[0].date_posted is None
    assert result.jobs[0].expected_start_date == "2027-07-19"
    assert result.jobs[0].application_deadline is None
    assert not any("_124." in path for path in paths)


@pytest.mark.parametrize("failure", ["duplicate", "count", "short", "wrong_page", "http"])
def test_failed_later_page_never_returns_partial_collection(monkeypatch, failure):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.params.get("page") == "1":
            return httpx.Response(200, text=listing([card(123), card(124)], 3))
        assert req.url.path.endswith("listeoffre.aspx")
        if failure == "http":
            return httpx.Response(403)
        return httpx.Response(
            200,
            text=listing(
                [] if failure == "short" else [card(123 if failure == "duplicate" else 125)],
                4 if failure == "count" else 3,
                1 if failure == "wrong_page" else 2,
            ),
        )

    with pytest.raises(SourceUnavailable):
        execute(handler, monkeypatch)


@pytest.mark.parametrize(
    "key,value",
    [
        ("fldjobdescription_description1", ""),
        ("fldjobdescription_jobtitle", "Wrong title"),
        ("fldlocation_joblocation", ""),
        ("fldjobdescription_contract", ""),
        ("fldjobdescription_date1", "31/02/2027"),
    ],
)
def test_detail_rejects_missing_or_conflicting_fields(key, value):
    with pytest.raises(SourceUnavailable):
        parse_detail(detail(**{key: value}), row(), config(), "ca")


def test_missing_criteria_reference_and_duplicate_fields():
    for text in [
        detail().replace("2026-123", "2026-999"),
        detail() + '<p id="fldjobdescription_contract">Stage</p>',
        detail(fldapplicantcriteria_freecriteria1="", fldapplicantcriteria_experiencelevel=""),
    ]:
        with pytest.raises(SourceUnavailable):
            parse_detail(text, row(), config(), "ca")


@pytest.mark.parametrize(
    "label,minimum",
    [
        ("0-2 years", 0),
        ("6 - 10 ans", 6),
        ("11 ans et plus", 11),
        ("3-5 years", 3),
        ("Experienced", None),
    ],
)
def test_explicit_minimum_experience(label, minimum):
    job = parse_detail(detail(fldapplicantcriteria_experiencelevel=label), row(), config(), "ca")
    assert job.minimum_experience_years == minimum


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/offre-de-emploi/emploi-trader_123.aspx",
        "http://jobs.ca-cib.com/offre-de-emploi/emploi-trader_123.aspx",
        "https://jobs.ca-cib.com/account/login",
        "https://jobs.ca-cib.com/offre-de-emploi/emploi-trader_123.aspx?redirect=other",
    ],
)
def test_url_scope(url):
    with pytest.raises(SourceUnavailable):
        job_url(url)


def test_invalid_counts_cards_and_limits():
    for text, limit in [
        ("<html>unavailable</html>", 100),
        (listing([card()], 2), 100),
        (listing([card()]), 0),
        (listing([card()]).replace("2026-123", "2026-999"), 100),
        (listing([card(), card()]), 100),
    ]:
        with pytest.raises(SourceUnavailable):
            parse_page(text, 1, limit)
    with pytest.raises(ValueError):
        CACIBCollector("ca", config(search_terms=["trading"]), None)
    cfg = config()
    cfg.career_url = "https://evil.test"
    with pytest.raises(ValueError):
        CACIBCollector("ca", cfg, None)


def test_detail_budget_fails_before_any_details(monkeypatch):
    def handler(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, text=listing([card(123), card(124)]))
        )

    with pytest.raises(SourceUnavailable, match="detail limit"):
        execute(handler, monkeypatch, max_details=1)
