import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company, load_config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.sig import EMPLOYER, SEARCH, SIGCollector, parse_job, parse_page


def config(**options):
    return Company(name="Susquehanna", ats="sig", career_url=SEARCH, options=options)


def row(i=1, **changes):
    return (
        dict(
            req_id=str(i),
            slug=str(i),
            client_code="sig",
            language="en-us",
            hiring_organization=EMPLOYER,
            title="Quantitative Trader - Graduate 2027",
            internal=False,
            searchable=True,
            applyable=True,
            categories=[{"name": "New Graduates"}],
            tags1=["Quantitative Trading + Strategy"],
            tags3=["June 2027 Start"],
            employment_type=None,
            city="London",
            country="United Kingdom",
            state=None,
            multipleLocations=[],
            description="<p>Trade options on a trading desk.</p>",
            qualifications="<p>Python required.</p>",
            apply_url=f"https://careers-sig.icims.com/jobs/{i}/login",
            posted_date="2026-09-16T11:00:00+0000",
        )
        | changes
    )


def page(rows, total=None):
    total = len(rows) if total is None else total
    return {"jobs": [{"data": r} for r in rows], "totalCount": total, "count": total}


def execute(monkeypatch, rows, mutate=None, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    monkeypatch.setattr("trading_radar.sig.PAGE_SIZE", 2)
    calls = {}

    def handler(req):
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert req.url.host == "careers.sig.com"
        assert req.url.path == "/api/jobs"
        assert req.url.params["limit"] == "2"
        number = int(req.url.params["page"])
        calls[number] = calls.get(number, 0) + 1
        payload = page(rows[(number - 1) * 2 : number * 2], len(rows))
        if mutate:
            payload = mutate(payload, number, calls[number])
        return httpx.Response(200, json=payload)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("sig", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_all_pages_then_filter_and_no_application_requests(monkeypatch):
    result = execute(monkeypatch, [row(), row(2, title="Accountant"), row(3)])
    assert [j.external_id for j in result.jobs] == ["1", "3"]
    assert result.requests == 4 and not result.complete
    job = result.jobs[0]
    assert job.seniority_hint == "junior"
    assert job.expected_start_date == "June 2027 Start"
    assert job.date_posted == datetime(2026, 9, 16, 11, tzinfo=UTC)
    assert job.apply_url == SEARCH + "/1?lang=en-us"
    assert "Python required." in normalize(job).description_text
    assert job.application_deadline is None


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        page([], 1),
        {"jobs": [], "totalCount": True, "count": True},
        page([], -1),
        {"jobs": [], "totalCount": 0, "count": 1},
        {"jobs": [{}], "totalCount": 1, "count": 1},
    ],
)
def test_invalid_page(payload):
    with pytest.raises(SourceUnavailable):
        parse_page(payload, 1, 10)


@pytest.mark.parametrize(
    "key,value",
    [
        ("req_id", "x"),
        ("slug", "999"),
        ("language", "fr"),
        ("client_code", "other"),
        ("hiring_organization", "Other"),
        ("title", ""),
        ("internal", None),
        ("searchable", 1),
        ("categories", []),
        ("categories", [{"name": "Unknown"}]),
    ],
)
def test_invalid_identity_and_classification(key, value):
    with pytest.raises(SourceUnavailable):
        parse_page(page([row(**{key: value})]), 1, 10)


@pytest.mark.parametrize(
    "key,value",
    [
        ("apply_url", None),
        ("apply_url", "https://evil.test/jobs/1/login"),
        ("apply_url", "https://careers-sig.icims.com/jobs/2/login"),
        ("description", ""),
        ("qualifications", ""),
        ("city", ""),
        ("country", None),
        ("multipleLocations", [{"city": "Paris"}]),
        ("state", 123),
        ("tags3", []),
        ("tags3", ["Unknown"]),
        ("employment_type", True),
    ],
)
def test_invalid_detail_blocks_import(key, value):
    with pytest.raises(SourceUnavailable):
        parse_job(row(**{key: value}), "sig", config())


def test_contract_conflict_is_preserved_and_intern_category_wins():
    raw = parse_job(row(employment_type="INTERN"), "sig", config())
    assert raw.seniority_hint == "junior" and raw.employment_type == "INTERN"
    assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0
    raw = parse_job(
        row(categories=[{"name": "Interns + Co-ops"}], employment_type="PER_DIEM"), "sig", config()
    )
    assert raw.employment_type == "Internship"
    assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0


def test_requirements_not_duplicated():
    raw = parse_job(row(description="<p>Trade.</p><p>Python required.</p>"), "sig", config())
    assert normalize(raw).description_text.count("Python required.") == 1


def test_hidden_events_and_nontrading_functions_filtered(monkeypatch):
    rows = [
        row(1, internal=True),
        row(2, searchable=False),
        row(3, applyable=False),
        row(
            4, categories=[{"name": "Student Discovery Program"}], tags3=["Discovery Program 2027"]
        ),
        row(5, title="Trading Desk Associate", tags1=["Operations"]),
        row(6, title="Sports Trader", tags1=["Sports Analytics"]),
    ]
    result = execute(monkeypatch, rows)
    assert not result.jobs and not result.complete
    with pytest.raises(SourceUnavailable, match="function metadata"):
        execute(monkeypatch, [row(tags1=[])])


@pytest.mark.parametrize("mode", ["repeat", "count", "short", "shift"])
def test_pagination_drift_fails(monkeypatch, mode):
    rows = [row(i) for i in range(1, 5)]

    def mutate(p, n, c):
        if n == 2 and mode == "repeat":
            return page(rows[:2], 4)
        if n == 2 and mode == "count":
            return page(rows[2:], 5)
        if n == 2 and mode == "short":
            return page(rows[2:3], 4)
        if n == 1 and c == 2 and mode == "shift":
            return page(list(reversed(rows[:2])), 4)
        return p

    with pytest.raises(SourceUnavailable):
        execute(monkeypatch, rows, mutate)


def test_empty_board_limits_and_failed_second_job(monkeypatch):
    result = execute(monkeypatch, [])
    assert result.jobs == [] and not result.complete
    for options in [{"max_details": 1}, {"max_results_per_query": 1}]:
        with pytest.raises(SourceUnavailable):
            execute(monkeypatch, [row(), row(2)], **options)
    with pytest.raises(SourceUnavailable):
        execute(monkeypatch, [row(), row(2, qualifications="")])
    with pytest.raises(ValueError):
        SIGCollector("sig", config(search_terms=["trading"]), None)
    cfg = config()
    cfg.career_url = "https://other.test/jobs"
    with pytest.raises(ValueError):
        SIGCollector("sig", cfg, None)
