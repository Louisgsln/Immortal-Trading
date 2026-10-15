"""Public catalogue completeness, bank identities and off-cycle scope for lot 172."""

import asyncio
import json
from copy import deepcopy
from datetime import date

import httpx
import pytest

from tests.test_greenhouse_filtered import payload, row
from tests.test_source_expansion166 import profile
from trading_radar.collectors import build_collector
from trading_radar.config import Company, load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.lever_filtered import LeverOptions
from trading_radar.lever_filtered import parse_board as lever_board
from trading_radar.oracle import oracle_base
from trading_radar.programmes import programme_company
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import rejection_reason
from trading_radar.successfactors_public import SITES, detail, job_url, listing
from trading_radar.workable_api import ACCOUNT, BOARD, facts, rows

SOURCES = [
    "dimensional",
    "bmo",
    "us_bank",
    "sculptor",
    "bridgewater",
    "viking",
    "farallon",
    "greenland",
    "laurion",
    "gmo",
    "caxton",
    "trexquant",
    "danske",
    "smbc",
    "nordea",
]


def bank(name="SMBC"):
    return Company(
        name=name,
        ats="successfactors_public",
        career_url=SITES[name][0] + "/",
        options={
            "search_terms": ["trading"],
            "title_terms": ["trader"],
            "exclude_title_terms": [],
            "max_results_per_query": 100,
        },
    )


def sf_page(name="SMBC", total=26, offset=0, ids=None, term="trading"):
    last = total if name == "Nordea" else min(total, offset + 25)
    if not total:
        return f'<input name="q" value="{term}"><div id="noresults-message">Your search returned no results.</div>'
    ids = list(range(offset + 1, last + 1)) if ids is None else ids
    text = f'<input name="q" value="{term}"><span class="paginationLabel">Results {offset + 1} – {last} of {total}</span>'
    for i in ids:
        link = f'<a class="jobTitle-link" href="/job/London-Trader/{i}/">Trader {i}</a>'
        text += f'<tr class="data-row"><td>{link}{link}</td><td headers="hdrLocation">London, GB</td></tr>'
    return text


def sf_detail(name, i, description=None):
    if description is None:
        description = (
            name + " seeks a trader. " + "Research and execute trades in global markets. " * 8
        )
    return (
        f'<link rel="canonical" href="{SITES[name][0]}/job/London-Trader/{i}/">'
        f'<h1>Title: Trader {i}</h1><div class="jobdescription"><h2>Responsibilities</h2>'
        f"<p>{description}</p></div>"
    )


async def collect(config, handler, monkeypatch, source="test"):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
    try:
        return await build_collector(source, config, http).collect()
    finally:
        await http.close()


@pytest.mark.parametrize("name,total", [("SMBC", 26), ("Nordea", 64)])
def test_bank_complete_paginated_or_single_page_catalogue(name, total, monkeypatch):
    reads = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        reads.append(str(req.url))
        if req.url.path == "/search/":
            assert req.url.params["q"] == "trading"
            assert req.url.params["locale"] == SITES[name][1]
            return httpx.Response(200, text=sf_page(name, total, int(req.url.params["startrow"])))
        return httpx.Response(
            200, text=sf_detail(name, int(req.url.path.rstrip("/").rsplit("/", 1)[1]))
        )

    result = asyncio.run(collect(bank(name), handler, monkeypatch))
    assert len(result.jobs) == total
    assert result.scope_complete and not result.complete
    assert result.selection.examined == result.selection.selected == total
    assert sum("/search/" in url for url in reads) == (3 if name == "SMBC" else 2)
    raw = result.jobs[0]
    assert raw.date_posted is None and raw.expected_start_date is None
    assert raw.application_deadline is None and raw.minimum_experience_years is None


@pytest.mark.parametrize("change", ["short", "query", "count", "location", "duplicate"])
def test_bank_partial_or_ambiguous_tables_cannot_be_committed(change):
    text = sf_page(total=2)
    if change == "short":
        text = sf_page(total=2, ids=[1])
    elif change == "query":
        text = text.replace('value="trading"', 'value="other"')
    elif change == "count":
        text = text.replace("of 2", "of 3")
    elif change == "location":
        text = text.replace("London, GB", "")
    else:
        text = sf_page(total=2, ids=[1, 1])
    with pytest.raises(SourceUnavailable):
        listing(text, "trading", 0, 100, SITES["SMBC"][0])


def test_explicit_empty_bank_catalogue_is_distinct_from_missing_markup():
    assert listing(sf_page(total=0), "trading", 0, 100, SITES["SMBC"][0]) == ([], 0)
    with pytest.raises(SourceUnavailable):
        listing('<input name="q" value="trading">', "trading", 0, 100, SITES["SMBC"][0])


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/job/Trader/1/",
        "http://careersemea.smbcgroup.com/job/Trader/1/",
        "/job/Trader/1/?next=yes",
        "/job/Trader/1/#fragment",
        "/job/%252e%252e/1/",
        "/job/Trader%255cOther/1/",
        "/job/Trader/0/",
    ],
)
def test_bank_external_or_ambiguous_posting_urls_rejected(url):
    with pytest.raises(SourceUnavailable):
        job_url(url, SITES["SMBC"][0])


def test_bank_canonical_encoding_can_change_but_posting_id_must_match():
    row = listing(sf_page(total=1), "trading", 0, 100, SITES["SMBC"][0])[0][0]
    text = sf_detail("SMBC", 1).replace("London-Trader", "London-%2528Trader%2529")
    raw = detail(text, row, "smbc", bank())
    assert raw.external_id == "1"
    with pytest.raises(SourceUnavailable):
        detail(text.replace("/1/", "/2/"), row, "smbc", bank())


def test_bank_talent_registration_is_not_an_off_cycle_vacancy():
    row = listing(sf_page(total=1), "trading", 0, 100, SITES["SMBC"][0])[0][0]
    text = sf_detail(
        "SMBC", 1, "SMBC " + "This registration does not refer to a specific position. " * 8
    )
    assert detail(text, row, "smbc", bank()) is None


def test_bank_changed_first_page_fails_after_full_details(monkeypatch):
    calls = 0

    def handler(req):
        nonlocal calls
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/search/":
            calls += 1
            return httpx.Response(200, text=sf_page(total=1, ids=[1 if calls == 1 else 2]))
        return httpx.Response(200, text=sf_detail("SMBC", 1))

    with pytest.raises(SourceUnavailable, match="changed during"):
        asyncio.run(collect(bank(), handler, monkeypatch))


def workable_row(i=1, **changes):
    return (
        dict(
            id=i,
            shortcode=f"{i:010X}",
            title=f"Quantitative Researcher {i}",
            accountUid=ACCOUNT,
            isInternal=False,
            state="published",
            approvalStatus="approved",
            type="full",
            department=["Quantitative Research and Machine Learning"],
            published="2026-10-08T00:00:00.000Z",
            location={"city": "New York", "country": "United States"},
            remote=False,
            workplace="on_site",
        )
        | changes
    )


def trex():
    return Company(
        name="Trexquant Investment",
        ats="workable_api",
        tenant="trexquant",
        career_url=BOARD,
        options={"search_terms": [], "title_terms": ["quantitative"], "exclude_title_terms": []},
    )


def workable_detail(item):
    f = facts(item)
    return (
        f"# {f['title']}\n\n> Trexquant Investment · {f['location']} · {f['contract']} · Posted {f['posted']}\n\n"
        f"**Department:** {f['department']}\n\n## Description\nResearch and trade systematic strategies.\n\n"
        f"## Requirements\n- Python and financial research.\n\n## Apply\n"
        f"[Apply at Trexquant Investment]({BOARD}j/{f['id']}/apply)"
    )


@pytest.mark.parametrize(
    "mode", ["ok", "truncated", "duplicate", "cursor_loop", "changed", "metadata"]
)
def test_trexquant_complete_cursor_pagination_and_recheck(mode, monkeypatch):
    first_reads = 0
    searches = []

    def handler(req):
        nonlocal first_reads
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method == "POST":
            body = json.loads(req.content)
            assert body["query"] == ""
            searches.append(body)
            offset = int(body.get("token", "0"))
            items = [workable_row(i) for i in range(offset + 1, min(offset + 10, 24) + 1)]
            data = {"total": 24, "results": items}
            if offset < 20:
                data["nextPage"] = str(offset + 10)
            if offset == 0:
                first_reads += 1
                if mode == "changed" and first_reads > 1:
                    items[0]["title"] = "Quantitative Researcher changed"
            if offset == 10:
                if mode == "truncated":
                    data.pop("nextPage")
                elif mode == "duplicate":
                    items[0] = workable_row(1)
                elif mode == "cursor_loop":
                    data["nextPage"] = "10"
                elif mode == "metadata":
                    data["total"] = 25
            return httpx.Response(200, json=data)
        shortcode = req.url.path.rsplit("/", 1)[1].removesuffix(".md")
        return httpx.Response(200, text=workable_detail(workable_row(int(shortcode, 16))))

    if mode != "ok":
        with pytest.raises(SourceUnavailable):
            asyncio.run(collect(trex(), handler, monkeypatch))
        return
    result = asyncio.run(collect(trex(), handler, monkeypatch))
    assert len(result.jobs) == 24 and len(searches) == 4
    assert result.scope_complete and not result.complete and result.selection.examined == 24
    raw = result.jobs[0]
    assert raw.publication_day == date(2026, 10, 8) and raw.date_posted is None
    assert raw.application_deadline is None and raw.expected_start_date is None
    assert raw.employment_type == "Full-time" and "Python" in raw.description


@pytest.mark.parametrize(
    "change",
    [
        {"id": True},
        {"shortcode": "../1"},
        {"accountUid": "another-employer"},
        {"state": "draft"},
        {"approvalStatus": "pending"},
        {"isInternal": "false"},
    ],
)
def test_trexquant_publication_and_employer_identity_must_be_verified(change):
    with pytest.raises(SourceUnavailable):
        rows({"total": 1, "results": [workable_row(**change)]}, 100)


@pytest.mark.parametrize(
    "change",
    [
        {"published": "2026-99-99T00:00:00Z"},
        {"location": {}},
        {"department": None},
        {"type": "unknown"},
        {"remote": "false"},
        {"workplace": "unknown"},
    ],
)
def test_trexquant_ambiguous_public_fields_fail_closed(change):
    with pytest.raises(SourceUnavailable):
        facts(workable_row(**change))


def test_trexquant_unpublished_contract_remains_unknown_and_must_match_markdown():
    from trading_radar.workable_public import detail as workable_detail_parser

    item = workable_row()
    item.pop("type")
    f = facts(item)
    assert f["contract"] == "—"
    raw = workable_detail_parser(workable_detail(item), f, "trexquant", trex())
    assert raw.employment_type is None
    with pytest.raises(SourceUnavailable):
        workable_detail_parser(
            workable_detail(item).replace(" · — · ", " · Full-time · "), f, "trexquant", trex()
        )


def test_trexquant_unpublished_requirements_and_department_preserve_all_published_text():
    from trading_radar.workable_public import detail as workable_detail_parser

    item = workable_row(department=[])
    text = workable_detail(item).replace("**Department:** \n\n", "")
    text = text.replace(
        "## Requirements\n- Python and financial research.", "## Benefits\n- Research rewards."
    )
    raw = workable_detail_parser(text, facts(item), "trexquant", trex())
    assert "Research rewards" in raw.description and "Benefits" in raw.description
    assert raw.raw_payload["department"] == ""
    with pytest.raises(SourceUnavailable):
        workable_detail_parser(
            text.replace("## Apply", "## Other"), facts(item), "trexquant", trex()
        )


@pytest.mark.parametrize("tenant", ["bridgewater89", "vikingglobalinvestors"])
@pytest.mark.parametrize(
    "title", ["2027 Investment Associate Intern", "Quantitative Research Internship"]
)
def test_summer_programme_hidden_in_full_description_is_excluded(tenant, title):
    c = Company(
        name={
            "bridgewater89": "Bridgewater Associates",
            "vikingglobalinvestors": "Viking Global Investors",
        }[tenant],
        ats="greenhouse_filtered",
        tenant=tenant,
    )
    r = row(
        tenant,
        title=title,
        metadata=None if tenant.startswith("viking") else [],
        content="<p>This is a ten-week internship taking place over the summer.</p>",
    )
    assert (
        parse_board(
            payload([r]), "fund", c, GreenhouseOptions(title_terms=[], exclude_title_terms=[])
        )
        == []
    )


@pytest.mark.parametrize("tenant", ["bridgewater89", "vikingglobalinvestors"])
def test_general_summer_boilerplate_does_not_exclude_long_internship(tenant):
    c = Company(
        name={
            "bridgewater89": "Bridgewater Associates",
            "vikingglobalinvestors": "Viking Global Investors",
        }[tenant],
        ats="greenhouse_filtered",
        tenant=tenant,
    )
    r = row(
        tenant,
        title="2027 Quantitative Research Internship",
        metadata=None if tenant.startswith("viking") else [],
        content="<p>Six-month off-cycle placement in London. We also hire summer interns.</p>",
    )
    raw = parse_board(
        payload([r]), "fund", c, GreenhouseOptions(title_terms=[], exclude_title_terms=[])
    )[0]
    assert raw.expected_start_date is None and raw.employment_type is None


def test_gmo_audited_investment_team_without_invented_junior_seniority():
    c = profile("gmo")
    identifier = "12345678-1234-4234-8234-123456789abc"
    item = dict(
        id=identifier,
        text="Corporate Credit Analyst",
        hostedUrl=f"https://jobs.lever.co/gmo/{identifier}",
        applyUrl=f"https://jobs.lever.co/gmo/{identifier}/apply",
        categories={"location": "London", "team": "Investments", "commitment": "Full-time"},
        description="Research and trade corporate credit.",
        lists=[{"text": "Requirements", "content": "<ul><li>Credit research</li></ul>"}],
    )
    raw = lever_board([item], "gmo", c, LeverOptions(**c.options))[0]
    assert raw.seniority_hint is None and raw.employment_type == "Full-time"
    changed = deepcopy(item)
    changed["categories"]["commitment"] = "Full-Time"
    with pytest.raises(SourceUnavailable):
        lever_board([changed], "gmo", c, LeverOptions(**c.options))


def test_danske_european_oracle_domain_preserves_exact_public_site():
    site = profile("danske").career_url
    root, api, number = oracle_base(site)
    assert (
        root == site
        and number == "CX_1001"
        and api.startswith("https://ejqi.fa.ocs.oraclecloud.eu/")
    )
    for changed in [
        site.replace("oraclecloud.eu", "evil.eu"),
        site + "?private=true",
        site.replace("https://", "https://user@"),
    ]:
        with pytest.raises(ValueError):
            oracle_base(changed)


@pytest.mark.parametrize("key", SOURCES)
def test_new_vps_sources_keep_senior_and_off_cycle_roles_for_all_score_review(key):
    cfg = load_config()
    settings = cfg.settings.model_copy(
        update={"include_internships": True, "telegram_all_new_jobs": True}
    )
    c = programme_company(profile(key), settings)
    options = SearchOptions(
        **{
            k: v
            for k, v in c.options.items()
            if k not in {"verify_listing_snapshot", "conditional_details"}
        }
        | {"search_terms": ["trading"]}
    )
    assert rejection_reason("Senior Quantitative Trader", options) is None
    assert rejection_reason("2027 Off-Cycle Quantitative Trading Internship", options) is None
    assert rejection_reason("Quantitative Trading Summer Internship", options) is not None
    assert rejection_reason("Trading Operations Analyst", options) is not None


def test_vps_inventory_adds_fifteen_sources_and_distinct_employers():
    configs = {key: profile(key) for key in SOURCES}
    assert len(configs) == len({c.name for c in configs.values()}) == 15
    assert all(c.enabled and c.scan_interval == 1800 for c in configs.values())
    for key in ["bmo", "us_bank", "danske", "smbc", "nordea"]:
        assert (
            rejection_reason(
                "2027 Global Markets Off-Cycle Analyst",
                SearchOptions(
                    **{
                        k: v
                        for k, v in configs[key].options.items()
                        if k not in {"verify_listing_snapshot", "conditional_details"}
                    }
                ),
            )
            is None
        )
