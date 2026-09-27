import asyncio
from datetime import date
from html import escape

import httpx
import pytest

from trading_radar import engie
from trading_radar import totalenergies as total
from trading_radar.collectors import build_collector
from trading_radar.config import Company, load_config
from trading_radar.experience import experience_requirement
from trading_radar.export import export_csv
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.notifications import format_message
from trading_radar.scoring import score_job


def company(key, **options):
    return Company(
        name="ENGIE" if key == "engie" else "TotalEnergies",
        ats=key,
        tenant=key,
        career_url=engie.SEARCH if key == "engie" else total.SEARCH,
        options=options,
    )


def card(i=1, title="Energy Trader"):
    return dict(
        id=str(i),
        title=title,
        url=f"{total.ORIGIN}/en_US/careers/JobDetail/Energy-Trader/{i}",
        country="France",
        employer="TotalEnergies Trading",
        employment="Regular position",
        published="2026-09-21",
    )


def total_page(rows, count=None, offset=0, term="trading"):
    count = len(rows) if count is None else count
    legend = f"{offset + 1}-{offset + len(rows)} of {count} results" if count else "0 results"
    return (
        f'<input name="search" value="{term}"><div class="list-controls__text__legend">{legend}</div>'
        + "".join(
            '<div class="article--result"><h3><a href="'
            + r["url"]
            + '">'
            + escape(r["title"])
            + "</a></h3><ul>"
            + "".join(
                f'<li class="list-item-{cls}">{value}</li>'
                for cls, value in [
                    ("jobCountry", r["country"]),
                    ("employmentType", r["employment"]),
                    ("jobCreationDate", "21-09-2026"),
                    ("jobEmployerCompany", r["employer"]),
                ]
            )
            + f'</ul><a href="{total.ORIGIN}/en_US/careers/ApplicationMethods?jobId={r["id"]}">Apply</a></div>'
            for r in rows
        )
    )


def total_detail(r):
    fields = {
        "Country": r["country"],
        "City": "Paris",
        "Employer company": r["employer"],
        "Type of contract": r["employment"],
        "Experience": "Minimum 3 years",
    }
    return (
        f'<link rel="canonical" href="{r["url"]}"><h2 class="banner__text__title">{escape(r["title"])}</h2>'
        + "".join(
            f'<dl class="article__content__view__field"><dt>{k}</dt><dd>{v}</dd></dl>'
            for k, v in fields.items()
        )
        + "".join(
            f'<div class="article--details"><h3 class="article__header__text__title">{k}</h3><div class="article__content__view">{v}</div></div>'
            for k, v in {
                "Activities": "<p>Responsibilities</p><ul><li>Price power derivatives and monitor trading positions on the desk.</li></ul><script>fake graduate</script><p hidden>Hidden promise</p>",
                "Candidate Profile": "<p>Qualifications</p><ul><li>A bachelor degree and professional energy markets experience.</li></ul>",
            }.items()
        )
        + f'<a href="{total.ORIGIN}/en_US/careers/ApplicationMethods?jobId={r["id"]}">Apply</a><footer>Corporate unrelated graduate programme</footer>'
    )


def engie_url(ident="123-en_US"):
    return f"{engie.ORIGIN}/job/Paris-Energy-Trader-75000/{ident}/"


def sitemap(urls):
    return (
        '<urlset xmlns="http://www.google.com/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{escape(u)}</loc><lastmod>2026-09-27</lastmod></url>" for u in urls)
        + "</urlset>"
    )


def engie_detail(title="Energy Trader", ident="123"):
    body = "<p>Key responsibilities:</p><ul><li>Price energy derivatives and manage trading positions within desk limits.</li></ul><p>Qualifications and Experience</p><ul><li>Bachelor degree and 2 years of energy trading experience required.</li></ul><script>fake graduate</script><p hidden>Hidden promise</p>"
    values = [
        f'<span itemprop="title">{escape(title)}</span>',
        "Posting Start Date: 9/21/26",
        f"Requisition ID: {ident}",
        "Paris, France, 75000",
        "ENGIE Global Markets",
        "Trading / Portfolio Management",
        "Permanent",
        "Full - Time",
        "",
        f'<span lang="en-US">{body}</span>',
        "",
        "Business Unit: Supply & Energy Management",
        "Division: Trading",
        "Legal Entity: ENGIE Global Markets",
        "Company Name: ENGIE",
        "Minimum Base Salary:",
        "Maximum Base Salary:",
        "Pay Basis:",
    ]
    return (
        f'<link rel="canonical" href="{engie_url(ident + "-en_US")}"><div class="jobDisplayShell" itemtype="http://schema.org/JobPosting">'
        + "".join('<div class="joblayouttoken">' + v + "</div>" for v in values)
        + f'<a class="unify-apply-now" href="/talentcommunity/apply/{ident}/?locale=en_US">Apply</a></div>'
    )


def run(monkeypatch, key, handler, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def work():
        http = HTTPClient(retries=0, transport=httpx.MockTransport(handler))
        try:
            return await build_collector(key, company(key, **options), http).collect()
        finally:
            await http.close()

    return asyncio.run(work())


def test_total_pagination_filter_dedup_and_stable_recheck(monkeypatch):
    rows = [card()] + [card(i, "Senior Trader") for i in range(2, 22)]
    calls = []

    def handler(req):
        calls.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "/SearchJobs/" in req.url.path:
            offset = int(req.url.params["jobOffset"])
            return httpx.Response(
                200,
                text=total_page(rows[offset : offset + 20], 21, offset, req.url.params["search"]),
            )
        assert str(req.url) == rows[0]["url"]
        return httpx.Response(200, text=total_detail(rows[0]))

    result = run(monkeypatch, "totalenergies", handler, search_terms=["trading", "trader"])
    assert not result.complete and len(result.jobs) == 1
    job = normalize(result.jobs[0])
    assert job.publication_day == date(2026, 9, 21) and job.date_posted is None
    assert experience_requirement(job)["minimum_years"] == 3
    assert job.experience_evidence[0].origin == "employer_field"
    assert all(
        t not in job.description for t in ["fake graduate", "Hidden promise", "Corporate unrelated"]
    )
    assert len(calls) == 10


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('value="trading"', 'value="other"'),
        ("1-1 of 1", "2-2 of 2"),
        ("1-1 of 1", "1-1 of 501"),
        ("jobCountry", "missingCountry"),
        ("21-09-2026", "31-02-2026"),
        ("jobId=1", "jobId=2"),
        (
            "https://jobs.totalenergies.com/en_US/careers/JobDetail",
            "https://other.test/en_US/careers/JobDetail",
        ),
        ("<h3>", "<h4>"),
    ],
)
def test_total_rejects_invalid_pages(old, new):
    with pytest.raises(SourceUnavailable):
        total.parse_page(total_page([card()]).replace(old, new), "trading", 0, 500)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Minimum 3 years", "Minimum 13 years"),
    ],
)
def test_total_senior_field_prevents_alert(old, new):
    raw = total.parse_detail(
        total_detail(card()).replace(old, new), card(), company("totalenergies"), "totalenergies"
    )
    scored = score_job(normalize(raw), load_config().keywords)
    assert scored.score_breakdown.total == 0
    assert experience_requirement(scored)["minimum_years"] == 13


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("<dt>Country</dt><dd>France", "<dt>Country</dt><dd>Greece"),
        ("jobId=1", "jobId=2"),
        ("Candidate Profile", "Unexpected heading"),
        ('<link rel="canonical"', '<link rel="other"'),
        ('class="banner__text__title">Energy Trader', 'class="banner__text__title">Other Trader'),
        ("<dt>Experience</dt>", "<dt>Country</dt>"),
    ],
)
def test_total_rejects_wrong_details(old, new):
    with pytest.raises(SourceUnavailable):
        total.parse_detail(
            total_detail(card()).replace(old, new),
            card(),
            company("totalenergies"),
            "totalenergies",
        )


def test_total_empty_and_duplicate_pages():
    assert total.parse_page(total_page([]), "trading", 0, 500) == (0, [])
    with pytest.raises(SourceUnavailable):
        total.parse_page(total_page([card(), card()]), "trading", 0, 500)
    with pytest.raises(SourceUnavailable):
        total.parse_page("<h1>Search</h1>", "trading", 0, 500)


def test_total_compact_single_page_legend():
    count, rows = total.parse_page(
        total_page([card()]).replace("1-1 of 1 results", "1 result"), "trading", 0, 500
    )
    assert count == 1 and len(rows) == 1


def test_explicit_day_survives_storage_export_and_notification(repo, job, tmp_path):
    import csv

    job.publication_day = date(2026, 9, 10)
    job.date_posted = None
    with repo.transaction():
        repo.upsert(job)
    stored = repo.list_jobs()[0]
    assert stored.publication_day == date(2026, 9, 10) and stored.date_posted is None
    target = tmp_path / "export.csv"
    export_csv(repo, target)
    with target.open(encoding="utf-8-sig", newline="") as handle:
        assert next(csv.DictReader(handle))["date_posted"] == "2026-09-10"
    assert "Publication : 10/09/2026\n" in format_message(stored, "new")


def test_engie_redirect_translation_dedup_and_day(monkeypatch):
    urls = [engie_url("900"), engie_url("901"), engie_url("902")]
    seen = []

    def handler(req):
        seen.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\nDisallow: /services/\nDisallow: /talentcommunity/"
            )
        if str(req.url) == engie.SEARCH:
            return httpx.Response(200, text=sitemap(urls))
        if str(req.url) in urls:
            return httpx.Response(
                302,
                headers={
                    "Location": engie_url("123-fr_FR" if str(req.url) == urls[0] else "123-en_US")
                },
            )
        return httpx.Response(200, text=engie_detail())

    result = run(monkeypatch, "engie", handler)
    assert not result.complete and len(result.jobs) == 1
    raw = result.jobs[0]
    assert raw.external_id == "123" and raw.publication_day == date(2026, 9, 21)
    assert raw.date_posted is None and raw.apply_url == engie_url()
    assert "fake graduate" not in raw.description and "Hidden promise" not in raw.description
    assert all("/services/" not in url and "/talentcommunity/" not in url for url in seen)
    assert seen.count(engie.SEARCH) == 2


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Requisition ID: 123", "Requisition ID: 456"),
        ("9/21/26", "2/30/26"),
        ("9/21/26", "2026-09-21"),
        ("Legal Entity: ENGIE", "Legal Entity: Other"),
        ("/apply/123/", "/apply/456/"),
        ('itemprop="title"', 'itemprop="other"'),
        ('class="joblayouttoken"', 'class="unknown"'),
        ("123-en_US", "456-en_US"),
        ('lang="en-US"', 'lang="fr-FR"'),
        ("jobDisplayShell", "no-job"),
    ],
)
def test_engie_rejects_changed_identity_or_layout(old, new):
    with pytest.raises(SourceUnavailable):
        engie.parse_detail(engie_detail().replace(old, new), engie_url(), company("engie"), "engie")


@pytest.mark.parametrize(
    "url",
    [
        "http://jobs.engie.com/job/Trader/123-en_US/",
        "https://evil.test/job/Trader/123-en_US/",
        "https://jobs.engie.com@evil.test/job/Trader/123-en_US/",
        "https://jobs.engie.com/talentcommunity/apply/123/",
        "https://jobs.engie.com/job/%2fadmin/123-en_US/",
        "https://jobs.engie.com/job/%2e%2e/123-en_US/",
        "https://jobs.engie.com/job/Trader/123-en_US/?x=1",
        "https://jobs.engie.com/job/Trader/123-en_US/#other",
    ],
)
def test_engie_rejects_unapproved_destinations(url):
    assert not engie.allowed_job_url(url)


@pytest.mark.parametrize(
    "text",
    [
        "<html>CAPTCHA</html>",
        sitemap([]),
        sitemap([engie_url(), engie_url()]),
        sitemap(["https://other.test/job/Trader/123/"]),
        '<!DOCTYPE urlset [<!ENTITY entity "value">]>' + sitemap([engie_url()]),
        sitemap([engie_url()]).replace("</url>", "<loc>https://jobs.engie.com/</loc></url>"),
    ],
)
def test_engie_invalid_catalogues_fail_closed(text):
    with pytest.raises(SourceUnavailable):
        engie.parse_sitemap(text, 5000)


@pytest.mark.parametrize("key", ["engie", "totalenergies"])
def test_detail_limit_blocks_all_detail_requests(monkeypatch, key):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if str(req.url) == engie.SEARCH:
            return httpx.Response(200, text=sitemap([engie_url("1"), engie_url("2")]))
        if "/SearchJobs/" in req.url.path:
            return httpx.Response(200, text=total_page([card(), card(2)]))
        pytest.fail("detail should not be fetched")

    with pytest.raises(SourceUnavailable, match="detail limit"):
        run(monkeypatch, key, handler, max_details=1)


@pytest.mark.parametrize(
    "destination",
    [engie_url("456-en_US"), "https://other.test/job/Trader/1/", "/talentcommunity/apply/123/", ""],
)
def test_redirect_failure_never_returns_partial_collection(monkeypatch, destination):
    calls = []

    def handler(req):
        calls.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\nDisallow: /job/Paris-Energy-Trader-75000/456-en_US/"
            )
        if str(req.url) == engie.SEARCH:
            return httpx.Response(200, text=sitemap([engie_url("900")]))
        if str(req.url) == engie_url("900"):
            return httpx.Response(302, headers={"Location": destination})
        pytest.fail("forbidden redirect destination requested")

    with pytest.raises(SourceUnavailable):
        run(monkeypatch, "engie", handler)
    assert len(calls) == 3


@pytest.mark.parametrize("key", ["engie", "totalenergies"])
def test_catalogue_change_during_details_discards_snapshot(monkeypatch, key):
    listings = 0

    def handler(req):
        nonlocal listings
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if str(req.url) == engie.SEARCH or "/SearchJobs/" in req.url.path:
            listings += 1
            if key == "engie":
                return httpx.Response(
                    200,
                    text=sitemap(
                        [engie_url()] + ([engie_url("456-en_US")] if listings > 1 else [])
                    ),
                )
            return httpx.Response(
                200, text=total_page([card()] + ([card(2)] if listings > 1 else []))
            )
        return httpx.Response(200, text=engie_detail() if key == "engie" else total_detail(card()))

    with pytest.raises(SourceUnavailable, match="changed during"):
        run(monkeypatch, key, handler)


@pytest.mark.parametrize(
    "title", ["Associate, Energy Trader", "Energy Trading Intern", "Senior Energy Trader"]
)
def test_existing_seniority_and_internship_exclusions_are_preserved(title):
    raw = engie.parse_detail(engie_detail(title), engie_url(), company("engie"), "engie")
    assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0


def test_analyst_associate_remains_eligible():
    raw = engie.parse_detail(
        engie_detail("Analyst / Associate, Energy Trader"), engie_url(), company("engie"), "engie"
    )
    assert score_job(normalize(raw), load_config().keywords).score_breakdown.total > 0


def test_three_configured_sources_preserve_silent_first_import():
    cfg = load_config()
    assert cfg.settings.bootstrap_silent
    for key in ["totalenergies", "engie", "edf_trading"]:
        assert cfg.companies[key].enabled and cfg.companies[key].scan_interval == 1800
        assert cfg.companies[key].request_interval >= 2


@pytest.mark.parametrize("loop", [True, False])
def test_career_redirects_are_bounded_and_opt_in(monkeypatch, loop):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    calls = []

    def handler(req):
        calls.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            302, headers={"Location": engie_url("1" if loop else str(len(calls)))}
        )

    async def work():
        http = HTTPClient(retries=0, transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(SourceUnavailable, match="loop|limit"):
                await http.get_career_page(engie_url("1"), 0, "engie", engie.allowed_job_url)
            assert len(calls) <= 4
            calls.clear()
            with pytest.raises(SourceUnavailable, match="HTTP 302"):
                await http.get_text(engie_url("1"), 0, "engie")
            assert len(calls) == 1
        finally:
            await http.close()

    asyncio.run(work())


def test_total_repeated_pagination_is_not_a_complete_result(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        offset = int(req.url.params["jobOffset"])
        rows = [card(i) for i in range(1, 21)] if not offset else [card()]
        return httpx.Response(200, text=total_page(rows, 21, offset))

    with pytest.raises(SourceUnavailable, match="repeated page"):
        run(monkeypatch, "totalenergies", handler)


def test_total_nested_activity_headings_do_not_break_section_boundaries():
    page = total_detail(card()).replace(
        "<p>Responsibilities</p>", "<h3>Trading responsibilities</h3>"
    )
    job = total.parse_detail(page, card(), company("totalenergies"), "totalenergies")
    assert "<h3>Trading responsibilities</h3>" in job.description
