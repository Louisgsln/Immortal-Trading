import asyncio
import html
from datetime import UTC, datetime

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.nomura_professionals import (
    BOARD,
    ROOT,
    NomuraProfessionalsCollector,
    job_url,
    parse_detail,
    parse_page,
    posted_date,
    role_metadata,
)
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def company(**options):
    return Company(name="Nomura", ats="nomura_professionals", career_url=BOARD, options=options)


def row(i=1, title="Credit Structurer - Analyst", division="Global Markets"):
    return dict(
        id=str(i),
        title=title,
        division=division,
        location="London, GB",
        url=ROOT + f"/Nomura/job/London-role/{i}/",
    )


def card(r):
    link = f'<a class="jobTitle-link" href="{html.escape(r["url"])}">{html.escape(r["title"])}</a>'
    return (
        '<tr class="data-row"><td>'
        + link
        + link
        + '</td><td headers="hdrFacility">'
        + r["division"]
        + '</td><td headers="hdrLocation">'
        + r["location"]
        + "</td></tr>"
    )


def page(rows, total=None, offset=0, term="trading"):
    total = len(rows) if total is None else total
    query = f'<input name="q" value="{html.escape(term)}">'
    if not total:
        return query + '<div id="noresults-message">Your search returned no results.</div>'
    label = f'<span class="paginationLabel">Results {offset + 1} – {min(offset + 100, total)} of {total}</span>'
    return query + label + "<table>" + "".join(card(r) for r in rows) + "</table>" + label


def detail(r, description="Corporate Title: Analyst. Trade FX. Experience 1-3 years. Python."):
    return f'''<link rel="canonical" href="{html.escape(r["url"])}">
    <div class="jobDisplayShell" itemtype="http://schema.org/JobPosting">
    <meta itemprop="hiringOrganization" content="Nomura Holdings, inc.">
    <meta itemprop="datePosted" content="Wed Sep 16 07:00:00 UTC 2026">
    <meta itemprop="validThrough" content="Sun Sep 27 23:00:00 UTC 2026">
    <span itemprop="title">{html.escape(r["title"])}</span>
    <span itemprop="address"><meta itemprop="addressLocality" content="London"></span>
    <div class="jobdescription"><p>{html.escape(description)}</p></div>
    <a class="apply" href="/talentcommunity/apply/{r["id"]}/?locale=en_US">Apply</a>
    </div>'''


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("nomura_professionals", company(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_public_pagination_mobile_dedup_department_filter_and_detail(monkeypatch, config):
    rows = [row(1, "eTrading Developer"), row(2, "Trading Controls Associate", "Operations")]
    rows += [row(i, "Accountant") for i in range(3, 101)]
    rows += [row(101)]
    offsets, details = [], []

    def handler(req):
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/Nomura/search/":
            assert req.url.params["q"] == "trading"
            offset = int(req.url.params["startrow"])
            offsets.append(offset)
            return httpx.Response(200, text=page(rows[offset : offset + 100], 101, offset))
        identifier = int(req.url.path.strip("/").split("/")[-1])
        details.append(identifier)
        return httpx.Response(200, text=detail(rows[identifier - 1]))

    result = execute(handler, monkeypatch, title_terms=["trading", "structurer", "etrading"])
    assert offsets == [0, 100, 0] and details == [1, 101]
    assert len(result.jobs) == 2 and not result.complete and result.requests == 6
    job = result.jobs[1]
    assert job.date_posted == datetime(2026, 9, 16, 7, tzinfo=UTC)
    assert job.application_deadline is None and job.expected_start_date is None
    assert job.minimum_experience_years == 1 and job.seniority_hint == "junior"
    assert "Python" in normalize(job).description_text
    assert score_job(normalize(job), config.keywords).score_breakdown.junior == 20


@pytest.mark.parametrize(
    "old,new",
    [
        ('value="trading"', 'value="other"'),
        ("of 1", "of 2000"),
        ("Results 1", "Results 2"),
        ("paginationLabel", "removed"),
        ("Global Markets", ""),
        ("London, GB", ""),
        ('headers="hdrLocation"', 'headers="hdrFacility"'),
        ("jobTitle-link", "removed"),
    ],
)
def test_bad_search_schema_fails(old, new):
    with pytest.raises(SourceUnavailable):
        parse_page(page([row()]).replace(old, new), "trading", 0, 1999)


def test_search_does_not_accept_short_duplicate_or_conflicting_mobile_rows():
    with pytest.raises(SourceUnavailable, match="incomplete"):
        parse_page(page([row()], 2), "trading", 0, 1999)
    with pytest.raises(SourceUnavailable, match="repeated"):
        parse_page(page([row(), row()]), "trading", 0, 1999)
    text = page([row()]).replace("Credit Structurer - Analyst", "Another Title", 1)
    with pytest.raises(SourceUnavailable, match="ambiguous"):
        parse_page(text, "trading", 0, 1999)


def test_empty_result_needs_explicit_marker_and_first_page():
    text = page([])
    assert parse_page(text, "trading", 0, 1999) == ([], 0)
    for invalid, offset in [(text, 100), (text.replace("noresults-message", "other"), 0)]:
        with pytest.raises(SourceUnavailable):
            parse_page(invalid, "trading", offset, 1999)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/Nomura/job/London/1/",
        "/Laser/job/London/1/",
        "http://careers.nomura.com/Nomura/job/London/1/",
        "/Nomura/job/London/1/?token=x",
        "/Nomura/job/London/1/#apply",
        "/Nomura/job/London/noid/",
    ],
)
def test_public_url_boundaries(url):
    with pytest.raises(SourceUnavailable, match="URL"):
        job_url(url)


@pytest.mark.parametrize(
    "old,new",
    [
        ('rel="canonical"', 'rel="alternate"'),
        ("/London-role/1/", "/London-role/2/"),
        ("jobDisplayShell", "other"),
        ("JobPosting", "Event"),
        ('itemprop="title"', 'itemprop="other"'),
        ("Nomura Holdings, inc.", "Other firm"),
        ('itemprop="datePosted"', 'itemprop="other"'),
        ("jobdescription", "other"),
        ('itemprop="address"', 'itemprop="other"'),
        ('content="London"', 'content=""'),
        ("/apply/1/", "/apply/2/"),
        ('class="apply"', 'class="other"'),
    ],
)
def test_detail_identity_and_required_metadata(old, new):
    with pytest.raises(SourceUnavailable):
        parse_detail(detail(row()).replace(old, new), row(), company(), "nomura_professionals")


@pytest.mark.parametrize(
    "value", ["2026-09-16", "Wed Sep 16 07:00:00 GMT 2026", "Wed Sep 99 07:00:00 UTC 2026"]
)
def test_ambiguous_or_invalid_publication(value):
    with pytest.raises(SourceUnavailable):
        posted_date(value)


@pytest.mark.parametrize(
    "text,seniority,minimum",
    [
        ("Corporate Title: Analyst Experience 1-3 years", "junior", 1),
        ("Corporate Title Analyst / Associate Experience 2 - 4 years", "junior", 2),
        ("Corporate Title: Vice President / Executive Director", "senior", None),
        ("Corporate Title: Analyst / Vice President", "senior", None),
        ("Corporate Title : Associate Experience 3+ years", None, 3),
        ("Corporate Title AVP Experience 7–10 years", "senior", 7),
        ("Corporate Title: Executive Director Experience 10 years", "senior", 10),
        ("Work with Vice Presidents. Global Markets division. Analyst colleagues.", None, None),
    ],
)
def test_only_explicit_corporate_grade_and_experience_are_used(text, seniority, minimum):
    _, actual, years = role_metadata(text)
    assert (actual, years) == (seniority, minimum)


def test_corporate_seniority_and_minimum_experience_override_junior_title(config):
    for text in [
        "Corporate Title: Vice President",
        "Corporate Title: Analyst Experience 7-10 years",
    ]:
        raw = parse_detail(detail(row(), text), row(), company(), "nomura_professionals")
        assert score_job(normalize(raw), config.keywords).score_breakdown.total == 0


@pytest.mark.parametrize("failure", ["total", "repeat", "recheck", "details"])
def test_unstable_pagination_and_limits_abort(monkeypatch, failure):
    calls = 0

    def handler(req):
        nonlocal calls
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert req.url.path == "/Nomura/search/"
        offset = int(req.url.params["startrow"])
        calls += 1
        total = 102 if failure == "total" and offset else 101
        if offset:
            rows = [row(1 if failure == "repeat" else 101)]
            if total == 102:
                rows.append(row(102))
        else:
            rows = [row(i) for i in range(1, 101)]
            if failure == "recheck" and calls > 1:
                rows[0] = row(999)
        return httpx.Response(200, text=page(rows, total, offset))

    with pytest.raises(
        SourceUnavailable,
        match={
            "total": "total changed",
            "repeat": "repeated page",
            "recheck": "catalogue changed",
            "details": "detail limit",
        }[failure],
    ):
        execute(handler, monkeypatch, max_details=1 if failure == "details" else 250)


def test_multiple_query_deduplication(monkeypatch):
    details = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/Nomura/search/":
            return httpx.Response(200, text=page([row()], term=req.url.params["q"]))
        details.append(req.url.path)
        return httpx.Response(200, text=detail(row()))

    result = execute(handler, monkeypatch, search_terms=["trading", "markets"])
    assert len(result.jobs) == 1 and len(details) == 1


def test_only_verified_config_accepted():
    with pytest.raises(ValueError, match="verified"):
        NomuraProfessionalsCollector(
            "test", company().model_copy(update={"career_url": ROOT}), None
        )


@pytest.mark.parametrize(
    "text,contract",
    [
        (
            "Job Title: Structuring [12-month Fixed Term Contract] Corporate Title: NCT",
            "12-month Fixed Term Contract",
        ),
        ("Fixed term contracts can be considered. Corporate Title: Analyst", None),
    ],
)
def test_fixed_term_contract_requires_explicit_job_heading(text, contract):
    raw = parse_detail(detail(row(), text), row(), company(), "nomura_professionals")
    assert raw.employment_type == contract and raw.expected_start_date is None
