import asyncio
import json

import httpx
import pytest

from trading_radar.bnp import SEARCH, BNPCollector, job_url, parse_detail
from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable


def config(**options):
    return Company(
        name="BNP Paribas", ats="bnp", career_url=SEARCH, request_interval=0.1, options=options
    )


def listing(i=1, title="Rates Trading Analyst"):
    return f'<article class="card-custom card-offer"><a class="card-link" href="/emploi-carriere/offre-emploi/job-{i}"><div><h3>{title}</h3></div></a></article>'


def page(rows, total, number=1, term="trading"):
    return (
        f'<input name="form[q]" value="{term}"><button class="show-results-mobile">Consulter les offres (<span>{total}</span>)</button>'
        + "".join(rows)
        + f'<div class="pagination" data-page="{number}"></div>'
    )


def detail(i=1, **changes):
    return {
        "@type": "JobPosting",
        "title": "Rates Trading Analyst",
        "identifier": {"value": f"BNP-{i}"},
        "url": f"https://group.bnpparibas/emploi-carriere/offre-emploi/job-{i}",
        "description": "<h2>Responsabilités</h2><p>Trade rates</p><h2>Requirements</h2><p>Python, 0-2 years.</p>",
        "datePosted": "2026-09-15",
        "employmentType": "CDI",
        "jobLocation": {"address": {"addressLocality": "Paris", "addressCountry": "FR"}},
        **changes,
    }


def html(record):
    return '<script type="application/ld+json">' + json.dumps(record) + "</script>"


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("bnp", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_search_preserves_query_pagination_and_deduplicates_terms(monkeypatch):
    searches = []
    details = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("toutes-offres-emploi"):
            assert req.method == "GET"
            term = req.url.params["form[q]"]
            number = int(req.url.params["page"])
            searches.append((term, number))
            rows = [
                listing(i, "Trading Operations" if i > 1 else "Rates Trading Analyst")
                for i in range((number - 1) * 10 + 1, min(number * 10 + 1, 13))
            ]
            return httpx.Response(200, text=page(rows, 12, number, term))
        details.append(str(req.url))
        return httpx.Response(200, text=html(detail()))

    result = execute(handler, monkeypatch, search_terms=["trading", "rates"])
    assert searches == [("trading", 1), ("trading", 2), ("rates", 1), ("rates", 2)]
    assert len(details) == 1 and len(result.jobs) == 1 and not result.complete
    job = result.jobs[0]
    assert job.external_id == "BNP-1" and job.location == "Paris, FR"
    assert "Python" in job.description and "Responsabilités" in job.description
    assert job.date_posted.isoformat() == "2026-09-15T00:00:00+00:00"
    assert job.expected_start_date is None and job.application_deadline is None


@pytest.mark.parametrize(
    "body,match",
    [
        ("<html>Challenge</html>", "scope or result count"),
        (page([listing()], 1, term=""), "scope or result count"),
        (page([], 1), "short"),
        (page([], 2000), "result limit"),
        (page([listing(), listing()], 2), "repeated"),
        (page([listing()], 1, number=2), "page number mismatch"),
        (page([listing(title="")], 1), "incomplete"),
    ],
)
def test_bad_search_aborts(monkeypatch, body, match):
    def handler(req):
        return (
            httpx.Response(404) if req.url.path == "/robots.txt" else httpx.Response(200, text=body)
        )

    with pytest.raises(SourceUnavailable, match=match):
        execute(handler, monkeypatch)


def test_empty_scoped_search_is_partial(monkeypatch):
    def handler(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, text=page([], 0))
        )

    result = execute(handler, monkeypatch)
    assert not result.jobs and not result.complete


@pytest.mark.parametrize(
    "changes",
    [
        {"identifier": None},
        {"description": ""},
        {"title": None},
        {"url": "https://evil.example/emploi-carriere/offre-emploi/job-1"},
        {"url": "https://group.bnpparibas/emploi-carriere/offre-emploi/job-2"},
        {"jobLocation": None},
        {"datePosted": "tomorrow"},
    ],
)
def test_bad_detail(changes):
    with pytest.raises(SourceUnavailable):
        parse_detail(html(detail(**changes)), detail()["url"], config(), "bnp")


def test_graph_locations_and_unknown_dates():
    record = detail(
        datePosted=None,
        jobLocation=[
            {"address": {"addressLocality": "Paris", "addressCountry": {"name": "France"}}},
            {"address": {"addressLocality": "London", "addressCountry": "UK"}},
        ],
    )
    job = parse_detail(
        html({"@graph": [{"@type": "BreadcrumbList"}, record]}), record["url"], config(), "bnp"
    )
    assert job.location == "Paris, France; London, UK" and job.date_posted is None


@pytest.mark.parametrize(
    "body",
    [
        "<html>Not found</html>",
        '<script type="application/ld+json">{broken}</script>',
        html([detail(), detail()]),
    ],
)
def test_missing_or_ambiguous_job(body):
    with pytest.raises(SourceUnavailable):
        parse_detail(body, detail()["url"], config(), "bnp")


@pytest.mark.parametrize(
    "url",
    [
        "http://group.bnpparibas/emploi-carriere/offre-emploi/a",
        "https://user@group.bnpparibas/emploi-carriere/offre-emploi/a",
        "/emploi-carriere/offre-emploi/%2e%2e%2fx",
        "/emploi-carriere/offre-emploi/a?token=x",
        "//evil.example/emploi-carriere/offre-emploi/a",
    ],
)
def test_only_official_detail_links(url):
    with pytest.raises(SourceUnavailable):
        job_url(url)


def test_limits_before_detail_and_403(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert req.url.path.endswith("toutes-offres-emploi")
        return httpx.Response(200, text=page([listing(), listing(2)], 2))

    with pytest.raises(SourceUnavailable, match="detail limit"):
        execute(handler, monkeypatch, max_details=1)
    calls = []

    def restricted(req):
        calls.append(req)
        return httpx.Response(403)

    with pytest.raises(SourceUnavailable, match="403"):
        execute(restricted, monkeypatch)
    assert len(calls) == 1


def test_changed_total_aborts(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        number = int(req.url.params["page"])
        return httpx.Response(
            200,
            text=page(
                [listing(i, "Trading Operations") for i in range(10)],
                11 if number == 1 else 12,
                number,
            ),
        )

    with pytest.raises(SourceUnavailable, match="total changed"):
        execute(handler, monkeypatch)


def test_invalid_career_root():
    co = config()
    co.career_url = "https://example.com/search"
    with pytest.raises(ValueError):
        BNPCollector("bnp", co, None)


@pytest.mark.parametrize("reverse", [False, True])
def test_aliases_choose_stable_url(monkeypatch, reverse):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("toutes-offres-emploi"):
            rows = [listing(1), listing(2)]
            return httpx.Response(200, text=page(rows[::-1] if reverse else rows, 2))
        return httpx.Response(200, text=html(detail(url=str(req.url))))

    result = execute(handler, monkeypatch)
    assert len(result.jobs) == 1
    assert result.jobs[0].apply_url.endswith("/job-1")


def test_reused_identifier_conflict_is_quarantined(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("toutes-offres-emploi"):
            return httpx.Response(200, text=page([listing(1), listing(2)], 2))
        return httpx.Response(200, text=html(detail(url=str(req.url), description=req.url.path)))

    result = execute(handler, monkeypatch)
    assert not result.jobs and not result.complete
    assert len(result.conflicts) == 1
    assert result.conflicts[0].external_id == "BNP-1"
    assert result.conflicts[0].fields == ["description"]
    assert result.conflicts[0].urls == [detail(1)["url"], detail(2)["url"]]


@pytest.mark.parametrize("order", [(1, 2, 3, 4), (4, 3, 2, 1), (2, 1, 4, 3)])
def test_conflicting_group_never_reenters_and_unrelated_job_survives(monkeypatch, order):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("toutes-offres-emploi"):
            return httpx.Response(200, text=page([listing(i) for i in order], 4))
        i = int(req.url.path.rsplit("-", 1)[1])
        record = detail(i if i == 4 else 1, url=str(req.url))
        if i == 2:
            record.update(
                description="Different description", employmentType="Stage", datePosted="2026-09-24"
            )
        return httpx.Response(200, text=html(record))

    result = execute(handler, monkeypatch)
    assert [job.external_id for job in result.jobs] == ["BNP-4"]
    assert len(result.conflicts) == 1
    assert result.conflicts[0].fields == ["date_posted", "description", "employment_type"]
    assert result.conflicts[0].urls == [detail(i)["url"] for i in (1, 2, 3)]


def test_detail_failure_after_conflict_still_aborts_entire_collection(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("toutes-offres-emploi"):
            return httpx.Response(200, text=page([listing(i) for i in (1, 2, 3)], 3))
        if req.url.path.endswith("job-3"):
            return httpx.Response(503)
        return httpx.Response(200, text=html(detail(url=str(req.url), description=req.url.path)))

    with pytest.raises(SourceUnavailable):
        execute(handler, monkeypatch)
