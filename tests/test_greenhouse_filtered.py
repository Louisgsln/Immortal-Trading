import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company, load_config
from trading_radar.greenhouse_filtered import (
    BOARDS,
    GreenhouseFilteredCollector,
    GreenhouseOptions,
    imc_start,
    instant,
    parse_board,
)
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def config(tenant="imc", **options):
    return Company(
        name=BOARDS[tenant][0], ats="greenhouse_filtered", tenant=tenant, options=options
    )


def row(tenant="imc", i=1, **changes):
    fields = (
        {"Worker Sub Type": "Graduate", "Is Hidden Job?": None}
        if tenant == "imc"
        else {"Employment Type": "Regular", "Target Start Date": "Summer 2027"}
    )
    return (
        dict(
            id=i,
            internal_job_id=i + 100,
            title="Graduate Trader",
            company_name=BOARDS[tenant][0],
            absolute_url=f"https://{BOARDS[tenant][1]}/{tenant}/jobs/{i}",
            location={"name": "London"},
            content="&lt;p&gt;Trade FX options. Python. Full-time in August 2027.&lt;/p&gt;",
            metadata=[{"name": k, "value": v} for k, v in fields.items()],
            first_published="2026-09-01T09:00:00-04:00",
            updated_at="2026-09-16T10:00:00Z",
        )
        | changes
    )


def payload(rows):
    return {"jobs": rows, "meta": {"total": len(rows)}}


def jump_row(**changes):
    return (
        row(
            "jumptrading",
            absolute_url="https://www.jumptrading.com/hr/job?gh_jid=1",
            metadata=[{"name": "Employment Type", "value": "Full-time - Campus"}],
            title="Campus Quantitative Trader (Full-Time)",
            content="Trade FX options. Python.",
        )
        | changes
    )


def xtx_row(**changes):
    return (
        row(
            "xtxmarketstechnologies",
            title="C++ Software Engineer",
            metadata=None,
            departments=[{"name": "Tradingdev ETD Tech"}],
            content="<h2>The Role</h2><p>Join our exchange trading development team (ETD).</p>"
            "<h2>Essential Attributes</h2><p>C++ and Python.</p>",
        )
        | changes
    )


@pytest.mark.parametrize(
    "contract,junior,excluded",
    [
        ("Full-time - Campus", "junior", False),
        ("Full-time - Experienced", None, False),
        ("Jump Trading - Intern", None, True),
    ],
)
def test_jump_contract_and_campus_without_invented_year(contract, junior, excluded):
    item = jump_row(metadata=[{"name": "Employment Type", "value": contract}])
    raw = parse([item], "jumptrading")[0]
    assert raw.seniority_hint == junior and raw.employment_type == contract
    assert raw.expected_start_date is None
    job = score_job(normalize(raw), load_config().keywords)
    assert bool(job.score_breakdown.exclusions) == excluded
    assert job.score_breakdown.start == 7


@pytest.mark.parametrize(
    "url",
    [
        "https://www.jumptrading.com/hr/job?gh_jid=2",
        "https://www.jumptrading.com/hr/job?gh_jid=1&gh_jid=1",
        "https://www.jumptrading.com/hr/job?gh_jid=1&extra=yes",
        "https://www.jumptrading.com/hr/job?gh_jid=1#other",
        "https://evil.example/hr/job?gh_jid=1",
        "http://www.jumptrading.com/hr/job?gh_jid=1",
        "https://www.jumptrading.com/jumptrading/jobs/1",
    ],
)
def test_jump_rejects_wrong_public_identity(url):
    with pytest.raises(SourceUnavailable, match="URL identity"):
        parse([jump_row(absolute_url=url)], "jumptrading")


@pytest.mark.parametrize("contract", [None, "Full-time", "Campus", 1, {}])
def test_jump_rejects_unknown_contract(contract):
    with pytest.raises(SourceUnavailable, match="employment type"):
        parse(
            [jump_row(metadata=[{"name": "Employment Type", "value": contract}])],
            "jumptrading",
        )


def test_xtx_verified_role_is_retained_without_trading_in_title():
    raw = parse([xtx_row()], "xtxmarketstechnologies")[0]
    assert raw.role_hint == "trading_technology"
    assert raw.raw_payload["departments"] == ["Tradingdev ETD Tech"]
    assert raw.seniority_hint is None and raw.expected_start_date is None
    assert raw.employment_type is None
    scored = score_job(normalize(raw), load_config().keywords)
    assert scored.desk == ["TRADING_TECH"]
    assert scored.score_breakdown.trading == 22
    assert scored.score_breakdown.front_office == 15
    assert scored.score_breakdown.junior == 5
    assert not scored.score_breakdown.exclusions


@pytest.mark.parametrize(
    "changes",
    [
        {"departments": [{"name": "Shared Engineering"}]},
        {"departments": []},
        {"title": "Accountant"},
        {"content": "The Role Optimise training and inference platforms. Attributes C++."},
        {"content": "Exchange trading development team. The Role Maintain infrastructure."},
        {
            "content": "The Role Maintain infrastructure. Essential Attributes "
            "Experience with an exchange trading development team."
        },
    ],
)
def test_xtx_department_or_boilerplate_alone_is_insufficient(changes):
    assert parse([xtx_row(**changes)], "xtxmarketstechnologies") == []


@pytest.mark.parametrize("departments", [None, "Tradingdev ETD Tech", [{}], [{"name": ""}]])
def test_xtx_invalid_department_fails_source(departments):
    with pytest.raises(SourceUnavailable, match="department"):
        parse([xtx_row(departments=departments)], "xtxmarketstechnologies")


@pytest.mark.parametrize("content", [None, "No role heading", "The Role The Role duplicates"])
def test_xtx_missing_or_ambiguous_role_section_fails(content):
    with pytest.raises(SourceUnavailable, match="role"):
        parse([xtx_row(content=content)], "xtxmarketstechnologies")


def test_xtx_null_metadata_is_explicit_not_missing():
    item = xtx_row()
    del item["metadata"]
    with pytest.raises(SourceUnavailable, match="metadata missing"):
        parse([item], "xtxmarketstechnologies")


def test_xtx_hint_respects_explicit_excluded_titles():
    assert parse([xtx_row()], "xtxmarketstechnologies", exclude_title_terms=["software"]) == []


@pytest.mark.parametrize(
    "tenant,make_row", [("jumptrading", jump_row), ("xtxmarketstechnologies", xtx_row)]
)
def test_new_boards_use_public_get_and_partial_collection(tenant, make_row, monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    def handler(req):
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert (
            str(req.url) == f"https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs?content=true"
        )
        return httpx.Response(200, json=payload([make_row()]))

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector(tenant, config(tenant), http).collect()
        finally:
            await http.close()

    result = asyncio.run(run())
    assert not result.complete and len(result.jobs) == 1 and result.requests == 2


def parse(rows, tenant="imc", **options):
    return parse_board(payload(rows), tenant, config(tenant), GreenhouseOptions(**options))


@pytest.mark.parametrize("tenant", ["imc", "drweng"])
def test_public_board_wiring_and_filtered_snapshot(tenant, monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    calls = []

    def handler(req):
        calls.append(req)
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert req.url.host == "boards-api.greenhouse.io"
        assert req.url.path == f"/v1/boards/{tenant}/jobs"
        assert req.url.params["content"] == "true"
        return httpx.Response(
            200,
            json=payload(
                [
                    row(tenant),
                    row(tenant, 2, title="Accountant"),
                    row(tenant, 3, title="Senior Trader"),
                ]
            ),
        )

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector(tenant, config(tenant), http).collect()
        finally:
            await http.close()

    result = asyncio.run(run())
    assert not result.complete and result.requests == 2
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.external_id == "1"
    assert job.date_posted == datetime(2026, 9, 1, 13, tzinfo=UTC)
    assert job.expected_start_date == ("August 2027" if tenant == "imc" else "Summer 2027")
    assert "Trade FX options" in normalize(job).description_text


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        {"jobs": [], "meta": {}},
        {"jobs": [], "meta": {"total": True}},
        {"jobs": [], "meta": {"total": 1}},
        {"jobs": [], "meta": {"total": -1}},
        {"jobs": None, "meta": {"total": 0}},
    ],
)
def test_incomplete_board_fails(bad):
    with pytest.raises(SourceUnavailable):
        parse_board(bad, "imc", config(), GreenhouseOptions())


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", True),
        ("id", 0),
        ("company_name", "Other"),
        ("title", ""),
        ("absolute_url", "https://evil.test/imc/jobs/1"),
        ("absolute_url", "https://job-boards.eu.greenhouse.io/imc/jobs/999"),
        ("absolute_url", "https://job-boards.eu.greenhouse.io/imc/jobs/1?redirect=x"),
        ("internal_job_id", "1"),
        ("content", ""),
        ("content", "<script>no description</script>"),
        ("location", None),
        ("metadata", None),
        ("first_published", "2026-09-01"),
        ("application_deadline", "bad date"),
    ],
)
def test_invalid_post_prevents_partial_collection(field, value):
    bad = row(i=2)
    bad[field] = value
    with pytest.raises(SourceUnavailable):
        parse([row(), bad])


def test_prospect_hidden_and_duplicate_ids():
    prospect = row(internal_job_id=None, content="")
    hidden = row(i=2, content="")
    hidden["metadata"][1]["value"] = True
    assert parse([prospect, hidden]) == []
    with pytest.raises(SourceUnavailable, match="duplicate"):
        parse([row(), row()])
    with pytest.raises(SourceUnavailable, match="identity missing"):
        r = row()
        del r["internal_job_id"]
        parse([r])


@pytest.mark.parametrize(
    "fields",
    [
        [],
        [{"name": "Worker Sub Type", "value": "Graduate"}],
        [{"name": "Is Hidden Job?", "value": 1}],
        [{"name": "Is Hidden Job?", "value": "true"}],
        [
            {"name": "Is Hidden Job?", "value": None},
            {"name": "Worker Sub Type", "value": "Unknown"},
        ],
        [{"name": "Is Hidden Job?", "value": None}, {"name": "Is Hidden Job?", "value": None}],
        [None],
    ],
)
def test_metadata_drift_fails(fields):
    with pytest.raises(SourceUnavailable):
        parse([row(metadata=fields)])


@pytest.mark.parametrize(
    "field,value",
    [("Employment Type", None), ("Target Start Date", ""), ("Target Start Date", 2027)],
)
def test_drw_metadata_required(field, value):
    r = row("drweng")
    next(v for v in r["metadata"] if v["name"] == field)["value"] = value
    with pytest.raises(SourceUnavailable):
        parse([r], "drweng")


def test_contract_overrides_junior_title_and_experienced_is_not_senior():
    for tenant, key in [("imc", "Worker Sub Type"), ("drweng", "Employment Type")]:
        r = row(tenant)
        next(v for v in r["metadata"] if v["name"] == key)["value"] = "Intern"
        raw = parse([r], tenant)[0]
        assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0
    r = row()
    r["metadata"][0]["value"] = "Experienced"
    assert parse([r])[0].seniority_hint is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Start dates in February and August 2027.", "February and August 2027"),
        ("Join IMC full-time in February or August 2027.", "February or August 2027"),
        ("Full-time employment starting in August 2027.", "August 2027"),
        ("You may reapply in August 2027. Programme history started in 2027.", None),
    ],
)
def test_only_explicit_employment_start(text, expected):
    assert imc_start(text) == expected


def test_dates_without_fallback_and_limits():
    r = row(first_published=None, application_deadline="2026-10-01T10:00:00+02:00")
    raw = parse([r])[0]
    assert raw.date_posted is None
    assert raw.application_deadline == datetime(2026, 10, 1, 8, tzinfo=UTC)
    for value in [False, "invalid", "2027-01-01", {}]:
        with pytest.raises(SourceUnavailable):
            instant(value)
    with pytest.raises(SourceUnavailable):
        parse([row(), row(i=2)], max_results_per_query=1)
    with pytest.raises(SourceUnavailable):
        parse([row(), row(i=2)], max_details=1)
    assert parse([]) == []
    with pytest.raises(ValueError):
        GreenhouseFilteredCollector("imc", config(search_terms=["trading"]), None)
    co = config()
    co.tenant = "unverified"
    with pytest.raises(ValueError):
        GreenhouseFilteredCollector("imc", co, None)


@pytest.mark.parametrize(
    "title",
    [
        "Trading Recruiter",
        "Administrative Assistant - FICCO Trading Group",
        "Trader Assistant (Working Student)",
        "Trading Application Specialist",
    ],
)
def test_verified_non_target_roles_are_excluded(title):
    raw = parse([row(title=title)])[0]
    job = score_job(normalize(raw), load_config().keywords)
    assert job.score_breakdown.total == 0


def flow_row(**fields):
    values = {"Division": "Trading", "Start Date": "2027-08-30"} | fields
    return row("flowtraders", metadata=[{"name": k, "value": v} for k, v in values.items()])


@pytest.mark.parametrize("start", ["2027-08-30", "2026-06-01", "", None])
def test_flow_date_metadata_preserved_without_inventing_intake(start):
    raw = parse([flow_row(**{"Start Date": start})], "flowtraders")[0]
    assert raw.expected_start_date == (start or None)
    assert raw.employment_type is None
    assert raw.raw_payload["fields"]["Division"] == "Trading"


def test_flow_events_and_talent_pool_not_imported():
    r = flow_row(Division="Events")
    r["content"] = ""
    assert parse([r], "flowtraders") == []


@pytest.mark.parametrize(
    "fields",
    [
        {"Division": None},
        {"Division": ""},
        {"Start Date": False},
        {"Start Date": "2027-02-30"},
        {"Start Date": "August 2027"},
    ],
)
def test_flow_metadata_drift(fields):
    with pytest.raises(SourceUnavailable):
        parse([flow_row(**fields)], "flowtraders")


def test_flow_missing_start_field_fails():
    r = flow_row()
    r["metadata"] = r["metadata"][:1]
    with pytest.raises(SourceUnavailable):
        parse([r], "flowtraders")
