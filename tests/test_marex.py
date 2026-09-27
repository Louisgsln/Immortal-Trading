import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from trading_radar.collectors import build_collector
from trading_radar.config import Company, load_config
from trading_radar.education import education_mentions
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.marex import SEARCH, MarexCollector, job_url, parse_detail, parse_listing
from trading_radar.missions import mission_excerpts
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def config(**options):
    return Company(name="Marex", ats="marex", tenant="marex", career_url=SEARCH, options=options)


def row(i=1, title="Trading Analyst"):
    return dict(
        id=f"{i:014x}",
        url=f"{SEARCH}/{i:014x}-trading-analyst",
        title=title,
        location="London, GB",
        employment="Full-Time",
        department="Markets",
        published="2026-09-18T11:00:29.105Z",
    )


def metadata(rows):
    return [
        dict(
            id=r["id"],
            friendly_id=r["url"].rsplit("/", 1)[1],
            name=r["title"],
            url="https://marex.breezy.hr/p/" + r["url"].rsplit("/", 1)[1],
            company={"friendly_id": "marex"},
            location={"name": r["location"]},
            type={"name": r["employment"]},
            published_date=r["published"],
        )
        for r in rows
    ]


def page_data(rows):
    payload = json.dumps({"jobs": rows})
    # A JSON value may span multiple framework script chunks.
    middle = len(payload) // 2
    return "".join(
        "<script>self.__next_f.push(" + json.dumps([1, chunk]) + ")</script>"
        for chunk in [payload[:middle], payload[middle:]]
    )


def listing(rows):
    return (
        '<h1>Career Opportunities</h1><div id="location-select">All Locations ('
        + str(len(rows))
        + ")</div>"
        + "".join(
            f'<a class="MuiCard-root" href="{r["url"]}"><h4>{r["title"]}</h4>'
            f'<div class="MuiTypography-h6">{r["location"]}</div><h6>{r["employment"]}</h6>'
            f"<h6>{r['department']}</h6></a>"
            for r in rows
        )
        + page_data(metadata(rows))
    )


def detail(r):
    return (
        f"<div><div><h1>Career opportunities</h1><h1>{r['title']}</h1>"
        f"<div><p>{r['location']} ,</p><p>{r['department']} ,</p><p>{r['employment']}</p></div></div>"
        "<div><h5>About Marex</h5><div><p>Responsibilities</p><ul>"
        "<li>Analyse market data and assist the desk with pricing derivatives.</li>"
        "<li>Monitor trading positions and contribute to market research.</li></ul>"
        "<p>Skills and Experience</p><ul><li>A bachelor degree is preferred, but not required.</li></ul>"
        "<script>untrusted script</script><p hidden>Hidden graduate promise</p></div></div>"
        f'<a href="https://marex.breezy.hr/p/{r["url"].rsplit("/", 1)[1]}">Apply to this position</a></div>'
        "<footer>Unrelated graduate programme 2027</footer>"
    )


def execute(monkeypatch, handler, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(retries=0, transport=httpx.MockTransport(handler))
        try:
            return await build_collector("marex", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def transport(rows, calls, *, after=None, status=200):
    listings = 0

    def handler(req):
        nonlocal listings
        calls.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if str(req.url) == SEARCH:
            listings += 1
            return httpx.Response(
                200, text=listing(after if listings > 1 and after is not None else rows)
            )
        r = next(r for r in rows if r["url"] == str(req.url))
        return httpx.Response(status, text=detail(r))

    return handler


def test_real_structure_filters_before_details_and_rechecks_catalogue(monkeypatch):
    rows = [row(), row(2, "Senior Trader"), row(3, "Software Engineer")]
    calls = []
    result = execute(monkeypatch, transport(rows, calls, after=list(reversed(rows))))
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.external_id == "00000000000001"
    assert job.apply_url == "https://marex.breezy.hr/p/00000000000001-trading-analyst"
    assert job.source_url == row()["url"]
    assert job.date_posted.isoformat() == "2026-09-18T11:00:29.105000+00:00"
    assert job.seniority_hint is None
    assert not result.complete and result.requests == 4
    assert all(row(i)["url"] not in calls for i in (2, 3))
    assert calls.count(SEARCH) == 2
    assert "Unrelated" not in job.description and "untrusted" not in job.description
    assert "Hidden graduate" not in job.description
    normalized = normalize(job)
    assert len(mission_excerpts(normalized)["excerpts"]) == 2
    education = education_mentions(normalized)
    assert education["levels"] == ["bachelor"]


@pytest.mark.parametrize(
    "url",
    [
        "http://www.marex.com/careers/career-opportunities/00000000000001-role",
        "https://evil.test/careers/career-opportunities/00000000000001-role",
        "//www.marex.com/careers/career-opportunities/00000000000001-role",
        SEARCH + "/00000000000001-role?token=x",
        SEARCH + "/00000000000001-role#x",
        SEARCH + "/bad-role",
        SEARCH + "/00000000000001-role/",
        "",
    ],
)
def test_rejects_unverified_urls(url):
    with pytest.raises(SourceUnavailable):
        job_url(url)


@pytest.mark.parametrize(
    "before,after",
    [
        ("All Locations (1)", "All Locations (2)"),
        ("All Locations (1)", "All Locations (501)"),
        ("All Locations (1)", "London (1)"),
        ("Career Opportunities", "Access challenge"),
        ('id="location-select"', 'id="other"'),
        ("<h4>Trading Analyst</h4>", "<h4></h4>"),
        ('class="MuiTypography-h6"', 'class="other"'),
        ("<h6>Full-Time</h6>", "<h6></h6>"),
    ],
)
def test_catalogue_fails_closed_on_incomplete_html(before, after):
    with pytest.raises(SourceUnavailable):
        parse_listing(listing([row()]).replace(before, after), 500)


def test_duplicate_id_fails_even_with_different_slug():
    second = {**row(), "url": row()["url"] + "-changed"}
    with pytest.raises(SourceUnavailable, match="duplicate"):
        parse_listing(listing([row(), second]), 500)


@pytest.mark.parametrize(
    "before,after",
    [
        ("<h1>Trading Analyst</h1>", "<h1>Other Trader</h1>"),
        ("marex.breezy.hr", "other.breezy.hr"),
        ("00000000000001-trading-analyst", "00000000000002-trading-analyst"),
        ("<p>London, GB ,</p>", "<p>Paris, FR ,</p>"),
        ("<p>Full-Time</p>", "<p>Contract</p>"),
        ("<p>Markets ,</p>", "<p>Technology ,</p>"),
        ("<a href=", "<p>Unexpected insertion</p><a href="),
    ],
)
def test_detail_rejects_identity_metadata_and_structure_changes(before, after):
    with pytest.raises(SourceUnavailable):
        parse_detail(detail(row()).replace(before, after), row(), config(), "marex")


def test_empty_valid_catalogue_and_empty_description(monkeypatch):
    assert execute(monkeypatch, transport([], [])).jobs == []
    r = row()
    body = detail(r).split("<div><h5>", 1)[1].split("</div></div><a", 1)[0]
    with pytest.raises(SourceUnavailable, match="description"):
        parse_detail(
            detail(r).replace("<div><h5>" + body + "</div></div>", "<div>empty</div>"),
            r,
            config(),
            "marex",
        )


def test_changed_snapshot_never_returns_partial_jobs(monkeypatch):
    with pytest.raises(SourceUnavailable, match="changed"):
        execute(monkeypatch, transport([row()], [], after=[row(2)]))


def test_detail_limit_and_access_restriction(monkeypatch):
    calls = []
    with pytest.raises(SourceUnavailable, match="limit"):
        execute(monkeypatch, transport([row(), row(2)], calls), max_details=1)
    assert row()["url"] not in calls
    with pytest.raises(SourceUnavailable, match="403"):
        execute(monkeypatch, transport([row()], [], status=403))


def test_configuration_is_bound_to_verified_source_and_options():
    http = HTTPClient()
    with pytest.raises(ValueError):
        MarexCollector("marex", config().model_copy(update={"tenant": "other"}), http)
    with pytest.raises(ValueError):
        MarexCollector("marex", config().model_copy(update={"career_url": SEARCH + "/"}), http)
    with pytest.raises(ValidationError):
        MarexCollector("marex", config(search_terms=["trading"]), http)
    with pytest.raises(ValidationError):
        MarexCollector("marex", config(unknown=True), http)
    asyncio.run(http.close())


@pytest.mark.parametrize("title", ["Associate Trader", "Trading Intern", "Trading Specialist"])
def test_existing_targeting_exclusions_stay_effective(title):
    r = row(title=title)
    text = detail(r)
    if title == "Trading Specialist":
        text = text.replace(
            "A bachelor degree is preferred, but not required.",
            "Minimum 10 years industry experience.",
        )
    job = score_job(normalize(parse_detail(text, r, config(), "marex")), load_config().keywords)
    assert job.score_breakdown.total == 0 and job.score_breakdown.exclusions


@pytest.mark.parametrize(
    "date", [None, "", "2026-09-18", "2026-09-18T11:00:00", "2026-99-18T11:00:00Z"]
)
def test_publication_requires_an_explicit_valid_instant(date):
    r = {**row(), "published": date}
    with pytest.raises(SourceUnavailable, match="timestamp"):
        parse_listing(listing([r]), 500)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "00000000000002"),
        ("name", "Different vacancy"),
        ("url", "https://other.breezy.hr/p/00000000000001-trading-analyst"),
        ("company", {"friendly_id": "other"}),
        ("location", {"name": "Paris"}),
        ("type", {"name": "Contract"}),
    ],
)
def test_publication_metadata_must_match_the_visible_card(field, value):
    original = metadata([row()])
    changed = [{**original[0], field: value}]
    text = listing([row()]).replace(page_data(original), page_data(changed))
    with pytest.raises(SourceUnavailable, match="identity"):
        parse_listing(text, 500)


def test_missing_ambiguous_or_executable_page_data_is_rejected():
    text = listing([row()])
    scripts = page_data(metadata([row()]))
    for replacement in [
        "",
        scripts + scripts,
        "<script>self.__next_f.push(runCode())</script>",
        page_data([]),
    ]:
        with pytest.raises(SourceUnavailable):
            parse_listing(text.replace(scripts, replacement), 500)
