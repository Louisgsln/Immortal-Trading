import asyncio
import json

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company, load_config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.optiver import SEARCH, OptiverCollector, job_url, parse_detail, parse_page
from trading_radar.scoring import score_job


def config(**options):
    return Company(name="Optiver", ats="optiver", career_url=SEARCH, options=options)


def row(i=1, title="Graduate Trader", level="Graduate"):
    return dict(
        componentID=i,
        title=title,
        location="Amsterdam",
        experience=level,
        domain="Trading",
        href=f"/join-us/jobs/trading/amsterdam/role-{i}/",
    )


def parsed(r=None):
    return parse_page({"items": [r or row()], "totalCount": 1}, 0, 10)[0][0]


def detail(r=None, job_id=None):
    r = r or row()
    url = job_url(r["href"])
    posting = dict(
        **{"@type": "JobPosting"},
        title=r["title"],
        url=url,
        hiringOrganization={"name": "Optiver"},
        jobLocation={"name": r["location"]},
        datePosted="2026-09-16",
    )
    metadata = "".join(
        f"<div><p>{k}</p><p>{v}</p></div>"
        for k, v in [
            ("Level", r["experience"]),
            ("Location", r["location"]),
            ("Department", r["domain"]),
        ]
    )
    return (
        f'<h1>{r["title"]}</h1><meta name="jobid" content="{job_id or r["componentID"]}">'
        f'<link rel="canonical" href="{url}"><script type="application/ld+json">{json.dumps(posting)}</script>'
        + metadata
        + '<section class="rich-text-section"><p>Trade options and ETFs. Python required.</p></section>'
        + "<footer>Unrelated graduate programme 2027</footer>"
    )


def execute(monkeypatch, handler, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    monkeypatch.setattr("trading_radar.optiver.PAGE_SIZE", 2)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("optiver", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def transport(rows, calls, mutate=None, bad_detail=False, same_id=False):
    counts = {}

    def handler(req):
        calls.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/en/api/v1/jobs":
            offset = int(req.url.params["from"])
            assert req.url.params["size"] == "2"
            counts[offset] = counts.get(offset, 0) + 1
            payload = {"items": rows[offset : offset + 2], "totalCount": len(rows)}
            if mutate:
                payload = mutate(payload, offset, counts[offset])
            return httpx.Response(200, json=payload)
        r = next(r for r in rows if r["href"] == req.url.path)
        return (
            httpx.Response(403)
            if bad_detail and r["componentID"] == 2
            else httpx.Response(200, text=detail(r, 77 if same_id else None))
        )

    return handler


def test_full_pagination_then_title_filter_and_stable_ids(monkeypatch):
    calls = []
    result = execute(
        monkeypatch,
        transport(
            [
                row(),
                row(2, "Senior Trader"),
                row(3, "Software Engineer"),
                row(4, "Trading Analyst"),
            ],
            calls,
        ),
    )
    assert [j.external_id for j in result.jobs] == ["1", "4"]
    assert not result.complete
    assert len([url for url in calls if "/en/api/" in url]) == 3
    assert all("role-2" not in url and "role-3" not in url for url in calls)
    assert result.jobs[0].date_posted is None
    assert "Unrelated" not in result.jobs[0].description
    assert result.jobs[0].seniority_hint == "junior"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"items": [], "totalCount": True},
        {"items": [], "totalCount": -1},
        {"items": [], "totalCount": 11},
        {"items": [], "totalCount": 1},
        {"items": [None], "totalCount": 1},
        {"items": [{**row(), "componentID": None}], "totalCount": 1},
        {"items": [{**row(), "title": ""}], "totalCount": 1},
        {"items": [{**row(), "experience": "New taxonomy"}], "totalCount": 1},
    ],
)
def test_malformed_board_fails(payload):
    with pytest.raises(SourceUnavailable):
        parse_page(payload, 0, 10)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/join-us/jobs/trading/amsterdam/role-1/",
        "http://www.optiver.com/join-us/jobs/trading/amsterdam/role-1/",
        "//evil.test/join-us/jobs/trading/amsterdam/role-1/",
        row()["href"] + "?redirect=x",
        row()["href"] + "apply",
        row()["href"] + "#form",
        "/join-us/jobs/",
    ],
)
def test_url_scope(url):
    with pytest.raises(SourceUnavailable):
        job_url(url)


@pytest.mark.parametrize(
    "old,new",
    [
        ("<h1>Graduate Trader</h1>", "<h1>Trader</h1>"),
        ('content="1"', 'content=""'),
        ('rel="canonical"', 'rel="alternate"'),
        ('"@type": "JobPosting"', '"@type": "Event"'),
        ('"name": "Optiver"', '"name": "Other"'),
        ("<p>Graduate</p>", "<p>Experienced</p>"),
        ("<p>Location</p>", "<p>Unknown</p>"),
        ("Trade options and ETFs. Python required.", ""),
        ("rich-text-section", "summary"),
    ],
)
def test_changed_or_incomplete_detail_fails(old, new):
    with pytest.raises(SourceUnavailable):
        parse_detail(detail().replace(old, new), parsed(), config(), "optiver")


@pytest.mark.parametrize(
    "level,hint,contract",
    [
        ("Graduate", "junior", None),
        ("Early Careers", "junior", None),
        ("Experienced", None, None),
        ("Internship", None, "Internship"),
    ],
)
def test_employer_level_and_hidden_internship_exclusion(level, hint, contract):
    r = row(title="Quantitative Trader", level=level)
    raw = parse_detail(detail(r), parsed(r), config(), "optiver")
    assert raw.seniority_hint == hint
    assert raw.employment_type == contract
    if contract:
        assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0


@pytest.mark.parametrize("kind", ["changed_total", "repeated_page", "shifted_first", "short_page"])
def test_unstable_pagination_fails(monkeypatch, kind):
    rows = [row(i) for i in range(1, 5)]

    def mutate(payload, offset, count):
        if kind == "changed_total" and offset:
            payload["totalCount"] += 1
        if kind == "repeated_page" and offset:
            payload["items"] = rows[:2]
        if kind == "shifted_first" and not offset and count > 1:
            payload["items"] = list(reversed(payload["items"]))
        if kind == "short_page" and offset:
            payload["items"].pop()
        return payload

    with pytest.raises(SourceUnavailable):
        execute(monkeypatch, transport(rows, [], mutate))


def test_budget_and_failed_detail_prevent_partial_collection(monkeypatch):
    rows = [row(), row(2)]
    with pytest.raises(SourceUnavailable, match="detail limit"):
        execute(monkeypatch, transport(rows, []), max_details=1)
    with pytest.raises(SourceUnavailable):
        execute(monkeypatch, transport(rows, [], bad_detail=True))
    with pytest.raises(SourceUnavailable, match="duplicate vacancy"):
        execute(monkeypatch, transport(rows, [], same_id=True))


def test_empty_board_and_configuration(monkeypatch):
    result = execute(monkeypatch, transport([], []))
    assert result.jobs == [] and not result.complete
    with pytest.raises(ValueError):
        OptiverCollector("optiver", config(search_terms=["trading"]), None)
    cfg = config()
    cfg.career_url += "/other"
    with pytest.raises(ValueError):
        OptiverCollector("optiver", cfg, None)


def test_trading_floor_event_excluded_by_live_configuration(monkeypatch):
    cfg = load_config().companies["optiver"]
    calls = []
    result = execute(
        monkeypatch,
        transport([row(title="Institutional Trading - The Trading Floor")], calls),
        **cfg.options,
    )
    assert result.jobs == []
    assert not any("role-1" in url for url in calls)


@pytest.mark.parametrize(
    "title",
    [
        "Career Kickstarter - Trading 2026",
        "Expressions of Interest - Graduate Quantitative Trader 2027",
        "Expression of Interest - Trader",
    ],
)
def test_events_and_talent_pools_are_not_prioritized(title):
    r = row(title=title)
    raw = parse_detail(detail(r), parsed(r), config(), "optiver")
    job = score_job(normalize(raw), load_config().keywords)
    assert job.score_breakdown.total == 0
    assert job.score_breakdown.exclusions
