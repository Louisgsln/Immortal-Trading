import asyncio

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.nomura import (
    ORIGIN,
    ROUTE,
    SEARCH,
    NomuraCollector,
    job_url,
    parse_board,
    parse_detail,
)


def config(**options):
    return Company(
        name="Nomura", ats="nomura", career_url=SEARCH, request_interval=0.1, options=options
    )


def row(i=123):
    return {
        "id": str(i),
        "title": "2027 Global Markets Graduate",
        "url": ORIGIN + ROUTE + f"{i}-Markets/en-GB",
        "location": "London",
        "deadline_text": "30 Sept 2026",
    }


def card(
    i=123,
    title="2027 Global Markets Graduate",
    prefix="/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/xf-abcdef",
):
    return f'<tr class="details_row" data-oppid="{i}" data-title=" {title} "><td><a class="subject" href="{ORIGIN}{prefix}{ROUTE}{i}-Markets/en-GB">{title}</a></td><td>London</td><td>30 Sept 2026</td></tr>'


def board(cards, total=None):
    total = len(cards) if total is None else total
    return (
        f'<h2 role="alert">{total} results match!</h2><table class="solr_search_list"><thead><tr><th>Title</th><th>Location</th><th>Application Deadline</th></tr></thead><tbody>'
        + "".join(cards)
        + "</tbody></table>"
    )


def field(name, value):
    return f'<div class="form-group"><label><span class="hform_lbl_text">{name}</span></label><div class="form_value"><div class="form-control-static">{value}</div></div></div>'


def detail(i=123):
    return (
        '<h1 class="section">2027 Global Markets Graduate</h1>'
        + field("Region", "Europe")
        + field("Division", "Global Markets")
        + field("Location", "London")
        + field("Program type", "Graduate")
        + field(
            "Job description",
            "<h2>Role</h2>Trading FX<h2>Eligibility</h2>Graduate by July 2027. Python required.",
        )
        + f'<form action="{ORIGIN}/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/xf-123abc{ROUTE}{i}/apply/en-GB"><input name="__vxXSRF_Token" value="fixture-only-never-store"></form>'
    )


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("nomura", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_board_title_filter_details_and_stable_links(monkeypatch):
    urls = []

    def handler(req):
        urls.append(str(req.url))
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "jobboard" in req.url.path:
            return httpx.Response(200, text=board([card(123), card(124, "Accounting Graduate")]))
        return httpx.Response(200, text=detail())

    result = execute(handler, monkeypatch)
    assert len(result.jobs) == 1 and not result.complete and result.requests == 3
    job = result.jobs[0]
    assert job.apply_url == row()["url"] and urls[-1] == job.apply_url
    assert "Python required" in job.description
    assert job.date_posted is job.application_deadline is job.expected_start_date is None
    assert job.employment_type == "Graduate"
    assert "fixture-only-never-store" not in job.model_dump_json()
    assert "xf-" not in job.model_dump_json()


def test_context_variants_have_identical_vacancy_identity():
    first = parse_board(
        board([card(prefix="/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/xf-aaa111")]), 10
    )
    second = parse_board(
        board([card(prefix="/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/xf-bbb222")]), 10
    )
    assert first == second


@pytest.mark.parametrize(
    "text",
    [
        "<html>unavailable</html>",
        board([card()], 2),
        board([card(), card()]),
        board([card()]).replace("Application Deadline", "Date"),
        board([card()]).replace('data-oppid="123"', 'data-oppid="999"'),
        board([card()]).replace(
            'data-title=" 2027 Global Markets Graduate "', 'data-title="Other"'
        ),
        board([card()]).replace("<td>London</td>", "<td></td>"),
    ],
)
def test_incomplete_or_changed_board_fails(text):
    with pytest.raises(SourceUnavailable):
        parse_board(text, 10)


@pytest.mark.parametrize(
    "old,new",
    [
        ("2027 Global Markets Graduate", "Wrong title"),
        ("123/apply", "999/apply"),
        ("London", "Paris"),
        ("Program type", "Other"),
        ("Job description", "Summary"),
        ("Division", "Other"),
        ("<h2>Role</h2>Trading FX<h2>Eligibility</h2>Graduate by July 2027. Python required.", ""),
    ],
)
def test_detail_validation(old, new):
    with pytest.raises(SourceUnavailable):
        parse_detail(detail().replace(old, new), row(), config(), "nomura")


def test_url_scope_and_limits():
    for url in [
        row()["url"].replace("https", "http"),
        row()["url"].replace("nomuracampus.tal.net", "evil.test"),
        row()["url"] + "?redirect=x",
        ORIGIN + ROUTE + "123/apply/en-GB",
    ]:
        with pytest.raises(SourceUnavailable):
            job_url(url)
    with pytest.raises(SourceUnavailable):
        parse_board(board([card()]), 0)
    with pytest.raises(ValueError):
        NomuraCollector("nomura", config(search_terms=["trading"]), None)
    cfg = config()
    cfg.career_url = SEARCH.replace("vacancy/1", "vacancy/2")
    with pytest.raises(ValueError):
        NomuraCollector("nomura", cfg, None)


def test_failed_detail_cannot_return_partial_collection(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "jobboard" in req.url.path:
            return httpx.Response(200, text=board([card(123), card(124)]))
        if "/124-" in req.url.path:
            return httpx.Response(403)
        return httpx.Response(200, text=detail())

    with pytest.raises(SourceUnavailable):
        execute(handler, monkeypatch)


def test_detail_budget(monkeypatch):
    def handler(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, text=board([card(123), card(124)]))
        )

    with pytest.raises(SourceUnavailable, match="detail limit"):
        execute(handler, monkeypatch, max_details=1)
