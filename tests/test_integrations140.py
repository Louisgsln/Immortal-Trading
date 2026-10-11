import asyncio
import copy
import html
import json
from pathlib import Path

import httpx
import pytest

from trading_radar.bnp import ENGLISH_SEARCH, SearchPage
from trading_radar.bnp import parse_detail as bnp_detail
from trading_radar.bnp_authority import recruitment_target
from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.millennium_campus import (
    PROFESSIONAL_BOARD,
    PROFESSIONAL_ROOT,
    job_url,
    parse_detail,
    position,
)
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.programmes import programme, programme_alertable
from trading_radar.rothschild_campus import BOARD, parse_page
from trading_radar.rothschild_campus import parse_detail as roth_detail


def fixtures():
    return json.loads(Path("tests/fixtures/integrations140.json").read_text())


def roth_company(**options):
    return Company(
        name="Rothschild & Co",
        ats="rothschild_campus",
        career_url=BOARD,
        options={"search_terms": [], **options},
    )


def roth_row():
    return next(
        r
        for r in parse_page(fixtures()["roth_p1"], 1, 100)[0]
        if "Germany - Frankfurt - Global Markets" in r["title"]
    )


def test_real_rothschild_second_page_is_required_and_three_months_is_not_long(config):
    data = fixtures()
    first, total = parse_page(data["roth_p1"], 1, 100)
    second, remaining_total = parse_page(data["roth_p2"], 2, 100)
    assert total == remaining_total == 60 and len(first) == 50 and len(second) == 10
    assert any("Equity Capital Markets" in r["title"] for r in second)
    raw = roth_detail(data["roth_detail"], roth_row(), roth_company(), "rothschild_campus")
    assert raw.external_id == "539" and raw.employment_type == "Long Term Internship"
    assert "4 January 2027" in raw.description and "31 March 2027" in raw.description
    assert raw.date_posted is None and raw.application_deadline is None
    job = normalize(raw)
    assert programme(job)["year"] == 2027
    assert "long" not in programme(job)["formats"]
    config.settings.include_internships = config.settings.internship_alerts_enabled = True
    assert not programme_alertable(job, config.settings)


@pytest.mark.parametrize(
    "before,after",
    [
        (">60</span>", ">61</span>"),
        (
            '<span class="uid-pagination-message-valuefirst">2</span>',
            '<span class="uid-pagination-message-valuefirst">1</span>',
        ),
        (">51</span>", ">1</span>"),
        ('href="/en/careers/students-and-graduates/opportunities/', 'href="https://evil.test/'),
        ("roths-career-office-event-card-title", "other-title"),
        ("uid-listings-result-list", "other-list"),
        ("Learn more", "Apply"),
    ],
)
def test_rothschild_incomplete_catalogues_and_foreign_links_fail(before, after):
    with pytest.raises(SourceUnavailable):
        assert before in fixtures()["roth_p2"]
        parse_page(fixtures()["roth_p2"].replace(before, after), 2, 100)


@pytest.mark.parametrize(
    "before,after",
    [
        ("Internship 2027</h1>", "Internship 2028</h1>"),
        ("rothschildandco.tal.net", "evil.test"),
        ("candidate/postings/539", "candidate/postings/539?token=x"),
        ("Apply now", "Closed"),
        ('class="wysiwyg"', 'class="missing"'),
    ],
)
def test_rothschild_detail_needs_employer_identity_and_full_description(before, after):
    with pytest.raises(SourceUnavailable):
        roth_detail(
            fixtures()["roth_detail"].replace(before, after),
            roth_row(),
            roth_company(),
            "rothschild_campus",
        )


def execute(monkeypatch, company, handler):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("test", company, http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


@pytest.mark.parametrize("changing", [False, True])
def test_rothschild_full_catalogue_rechecked_before_details(monkeypatch, changing):
    data = fixtures()
    pages = []

    def handler(req):
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("/opportunities/"):
            number = int(req.url.params["page"])
            pages.append(number)
            body = data[f"roth_p{number}"]
            if changing and len(pages) in {3, 6}:
                body = body.replace("Singapore</h3>", "Singapore revised</h3>")
            return httpx.Response(200, text=body)
        return httpx.Response(200, text=data["roth_detail"])

    if changing:
        with pytest.raises(SourceUnavailable, match="changed"):
            execute(monkeypatch, roth_company(title_terms=["global markets solutions"]), handler)
        assert pages == [1, 2, 1, 1, 2, 1]
    else:
        result = execute(
            monkeypatch, roth_company(title_terms=["global markets solutions"]), handler
        )
        assert pages == [1, 2, 1]
        assert (
            result.scope_complete
            and not result.complete
            and [j.external_id for j in result.jobs] == ["539"]
        )


def test_real_bnp_english_search_and_internship_detail_keep_reference():
    data = fixtures()
    parser = SearchPage(ENGLISH_SEARCH)
    parser.feed(data["bnp_en"])
    assert parser.query == "trading" and len(parser.rows) == 10 and parser.totals[0] > 300
    record = data["bnp_detail"][0]
    config = Company(name="BNP Paribas", ats="bnp", career_url=ENGLISH_SEARCH)
    raw = bnp_detail(
        '<script type="application/ld+json">' + json.dumps(record) + "</script>",
        record["url"],
        config,
        "bnp_paribas",
    )
    assert raw.external_id == "111111111118992" and raw.employment_type == "Trainee / Internship"
    assert "price, manage risk" in raw.description
    assert raw.expected_start_date is None and raw.application_deadline is None
    assert (
        recruitment_target(
            '<a href="https://bwelcome.hr.bnpparibas/en_US/externalcareers/JobDetails?jobId=67616">Apply</a>'
        )[0]
        == "67616"
    )


def test_bnp_listing_language_is_bound_to_search_root():
    with pytest.raises(SourceUnavailable, match="language"):
        SearchPage().feed(fixtures()["bnp_en"])


def test_bnp_english_recheck_keeps_query_and_rejects_changed_first_page(monkeypatch):
    from tests.test_bnp import detail, listing, page
    from tests.test_bnp import html as detail_html

    visits = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("all-job-offers"):
            visits.append(dict(req.url.params))
            body = page([listing()], 1).replace(
                "/emploi-carriere/offre-emploi/", "/en/careers/job-offer/"
            )
            if len(visits) == 2:
                body = body.replace("Rates Trading Analyst", "Other Trading Analyst")
            return httpx.Response(200, text=body)
        return httpx.Response(200, text=detail_html(detail()))

    config = Company(name="BNP Paribas", ats="bnp", career_url=ENGLISH_SEARCH)
    with pytest.raises(SourceUnavailable, match="first page changed"):
        execute(monkeypatch, config, handler)
    assert visits == [{"form[q]": "trading", "page": "1"}] * 2


def mlp_fixture():
    return json.loads(Path("tests/fixtures/millennium-professionals140.json").read_text())


def mlp_company():
    return Company(name="Millennium", ats="millennium_professionals", career_url=PROFESSIONAL_BOARD)


def mlp_detail_html(data):
    return (
        '<code id="smartApplyData">'
        + html.escape(json.dumps(data["detail"]))
        + '</code><script type="application/ld+json">'
        + json.dumps(data["schema"])
        + "</script>"
    )


def test_real_millennium_unicode_slug_and_independent_scope():
    data = mlp_fixture()
    row = position(data["detail"]["positions"][0], root=PROFESSIONAL_ROOT)
    raw = parse_detail(
        mlp_detail_html(data),
        row,
        mlp_company(),
        "millennium_professionals",
        root=PROFESSIONAL_ROOT,
    )
    assert raw.external_id == "755956079331" and raw.apply_url.startswith(PROFESSIONAL_ROOT)
    assert (
        "microsite" not in raw.apply_url
        and raw.date_posted is None
        and raw.application_deadline is None
    )
    assert raw.raw_payload["ats_job_id"] == "REQ-29207" and "candidate" not in raw.raw_payload


@pytest.mark.parametrize(
    "value",
    [
        "https://campusjobs.mlp.com/careers/job/1",
        "https://career.mlp.com/careers/job/1?domain=mlp.com&microsite=campus-site",
        "https://career.mlp.com/careers/job/1-a%2fb",
        "https://career.mlp.com/careers/job/1-a%5cb",
    ],
)
def test_millennium_scope_and_encoded_path_boundaries(value):
    with pytest.raises(SourceUnavailable):
        job_url(value, "1", root=PROFESSIONAL_ROOT)


def test_millennium_professional_pagination_does_not_use_campus_filter(monkeypatch):
    data = mlp_fixture()
    real = data["detail"]["positions"][0]
    rows = [real]
    for i in range(10):
        row = copy.deepcopy(real)
        row.update(
            id=i + 1,
            name="Accountant",
            posting_name="Accountant",
            canonicalPositionUrl=f"https://mlp.eightfold.ai/careers/job/{i + 1}",
        )
        rows.append(row)
    offsets = []

    def handler(req):
        assert req.url.host == "career.mlp.com"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert "microsite" not in req.url.params
        if req.url.path.endswith("/jobs"):
            offset = int(req.url.params["start"])
            offsets.append(offset)
            return httpx.Response(
                200,
                json={
                    "domain": "mlp.com",
                    "isUserAuthenticated": False,
                    "count": 11,
                    "query": {"query": "trading", "location": ""},
                    "positions": rows[offset : offset + 10],
                },
            )
        return httpx.Response(200, text=mlp_detail_html(data))

    result = execute(monkeypatch, mlp_company(), handler)
    assert offsets == [0, 10, 0] and result.scope_complete and not result.complete
    assert len(result.jobs) == 1


def test_brevan_real_off_cycle_retained_without_inventing_intake_from_conversion(config):
    data = json.loads(Path("tests/fixtures/brevan-programmes140.json").read_text())
    config.settings.include_internships = config.settings.internship_alerts_enabled = True
    jobs = [normalize(RawJob(**row)) for row in data]
    off_cycle = next(j for j in jobs if "Off Cycle" in j.title)
    facts = programme(off_cycle)
    assert facts["kind"] == "internship" and "off_cycle" in facts["formats"]
    assert facts["year_status"] == "unknown" and facts["year"] is None
    assert not programme_alertable(off_cycle, config.settings)
    assert "2028 Graduate Program" in off_cycle.description
    summer = next(j for j in jobs if "Summer" in j.title)
    assert "summer" in programme(summer)["formats"] and not programme_alertable(
        summer, config.settings
    )


@pytest.mark.parametrize("label", ["Apply Now", "Apply Now :"])
def test_observed_rothschild_branded_application_route(label):
    body = (
        fixtures()["roth_detail"]
        .replace("Apply now", label)
        .replace(
            "/vx/lang-en-GB/appcentre-1/candidate/postings/539",
            "/vx/appcentre-ext/brand-4/spa-1/candidate/so/pm/1/pl/2/opp/539-Germany-Frankfurt-Global-Markets-Solutions-January-Internship-2027/en-GB",
        )
    )
    assert roth_detail(body, roth_row(), roth_company(), "rothschild_campus").external_id == "539"


@pytest.mark.parametrize("contract", ["Permanent", "", "Summer Job"])
def test_bnp_campus_requires_internship_contract_on_every_listing(contract):
    from trading_radar.bnp import CAMPUS_SEARCH

    body = (
        fixtures()["bnp_en"]
        .replace("Permanent", "Trainee / Internship")
        .replace("Fixed Term Contract", "Trainee / Internship")
    )
    body = body.replace("Trainee / Internship", contract, 1)
    with pytest.raises(SourceUnavailable, match="contract scope"):
        SearchPage(CAMPUS_SEARCH).feed(body)


@pytest.mark.parametrize(
    "area,key,value",
    [
        ("detail", "isUserAuthenticated", True),
        ("detail", "pid", "1"),
        ("schema", "title", "Different"),
        ("schema", "description", ""),
    ],
)
def test_millennium_professional_detail_conflicts_abort(area, key, value):
    data = mlp_fixture()
    row = position(data["detail"]["positions"][0], root=PROFESSIONAL_ROOT)
    data[area][key] = value
    with pytest.raises(SourceUnavailable):
        parse_detail(
            mlp_detail_html(data),
            row,
            mlp_company(),
            "millennium_professionals",
            root=PROFESSIONAL_ROOT,
        )


def test_new_vps_sources_are_bound_to_verified_public_roots():
    import yaml

    from trading_radar.bnp import CAMPUS_SEARCH

    data = yaml.safe_load(Path("config/vps-companies.yaml").read_text())["companies"]
    sources = {
        "rothschild_campus": BOARD,
        "millennium_professionals": PROFESSIONAL_BOARD,
        "bnp_campus": CAMPUS_SEARCH,
        "brevan_howard": "https://brevanhoward.wd3.myworkdayjobs.com/BH_ExternalCareers",
    }
    for key, url in sources.items():
        company = Company(**data[key])
        assert company.career_url == url
        build_collector(
            key, company, HTTPClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
        )
    assert data["millennium_campus"]["name"] == data["millennium_professionals"]["name"]
    assert data["bnp_paribas"]["name"] == data["bnp_campus"]["name"]


@pytest.mark.parametrize("status", [403, 404, 401])
@pytest.mark.parametrize("all_unavailable", [False, True])
def test_bnp_campus_gaps_are_partial_and_do_not_hide_auth_or_all_details_failure(
    monkeypatch, status, all_unavailable
):
    from tests.test_bnp import detail, listing, page
    from tests.test_bnp import html as detail_html
    from trading_radar.bnp import CAMPUS_SEARCH

    config = Company(name="BNP Paribas", ats="bnp", career_url=CAMPUS_SEARCH)

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "all-job-offers" in req.url.path:
            rows = [
                listing(i).replace(
                    "<div><h3>", '<div><div class="offer-type">Trainee / Internship</div><h3>'
                )
                for i in [1, 2]
            ]
            return httpx.Response(
                200,
                text=page(rows, 2).replace(
                    "/emploi-carriere/offre-emploi/", "/en/careers/job-offer/"
                ),
            )
        if all_unavailable or req.url.path.endswith("job-2"):
            return httpx.Response(status)
        record = detail(
            url="https://group.bnpparibas/en/careers/job-offer/job-1",
            employmentType="Trainee / Internship",
        )
        return httpx.Response(200, text=detail_html(record))

    if all_unavailable or status == 401:
        with pytest.raises(SourceUnavailable):
            execute(monkeypatch, config, handler)
    else:
        result = execute(monkeypatch, config, handler)
        assert not result.scope_complete and not result.complete
        assert [j.external_id for j in result.jobs] == ["BNP-1"]
        assert result.listing_gaps == ["https://group.bnpparibas/en/careers/job-offer/job-2"]
