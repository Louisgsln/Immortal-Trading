"""Public-board identity and scope contracts for lots 95 through 97."""

import asyncio
from copy import deepcopy
from uuid import UUID

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.lever_filtered import LeverOptions
from trading_radar.lever_filtered import parse_board as parse_lever
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.workday import workday_base

GH = {
    "engineers_gate": ("Engineers Gate", "https://job-boards.greenhouse.io/engineersgate/jobs/123"),
    "pdt": ("PDT Partners", "https://job-boards.greenhouse.io/pdtpartners/jobs/123"),
    "graham": (
        "Graham Capital Management, L.P.",
        "https://boards.greenhouse.io/grahamcapitalmanagement/jobs/123?gh_jid=123",
    ),
    "quantbot": ("Quantbot Technologies", "https://www.quantbot.com/careers/123?gh_jid=123"),
}


def gh_row(source, **changes):
    return {
        "id": 123,
        "internal_job_id": 456,
        "title": "Junior Quantitative Trader",
        "company_name": GH[source][0],
        "absolute_url": GH[source][1],
        "metadata": [{"name": "Employment Type", "value": "Full-time"}]
        if source == "pdt"
        else None,
        "content": "<p>Develop and execute equities trading strategies.</p>",
        "location": {"name": "London"},
        "updated_at": "2026-09-28T10:00:00Z",
    } | changes


def gh(source, rows):
    cfg = load_config().companies[source]
    return parse_board(
        {"meta": {"total": len(rows)}, "jobs": rows}, source, cfg, GreenhouseOptions(**cfg.options)
    )


@pytest.mark.parametrize("source", GH)
def test_new_greenhouse_preserves_public_identity_without_inventing_dates(source):
    job = gh(source, [gh_row(source)])[0]
    assert job.apply_url == GH[source][1]
    assert job.date_posted is None and job.seniority_hint is None
    row = gh_row(source, first_published="2026-09-26T10:00:00Z")
    assert gh(source, [row])[0].date_posted.day == 26
    assert gh(source, [gh_row(source, internal_job_id=None)]) == []


@pytest.mark.parametrize("source", GH)
@pytest.mark.parametrize(
    "change",
    [
        {"company_name": "Other employer"},
        {"absolute_url": "https://evil.example/jobs/123"},
        {"id": 124},
        {"internal_job_id": True},
        {"content": ""},
        {"location": None},
        {"metadata": {}},
    ],
)
def test_new_greenhouse_rejects_changed_identity_and_missing_detail(source, change):
    with pytest.raises(SourceUnavailable):
        gh(source, [gh_row(source, **change)])


@pytest.mark.parametrize("source", ["graham", "quantbot"])
@pytest.mark.parametrize("query", ["", "gh_jid=124", "gh_jid=123&gh_jid=123", "gh_jid=123&x=1"])
def test_custom_routes_require_exact_matching_query(source, query):
    url = GH[source][1].split("?")[0] + "?" + query
    with pytest.raises(SourceUnavailable, match="URL identity"):
        gh(source, [gh_row(source, absolute_url=url)])


@pytest.mark.parametrize("source", GH)
@pytest.mark.parametrize(
    "title",
    ["Quantitative Research Intern", "General Application - Trader", "Trading Operations Analyst"],
)
def test_new_sources_do_not_import_internships_interest_forms_or_operations(source, title):
    assert not gh(source, [gh_row(source, title=title)])


@pytest.mark.parametrize("source", GH)
def test_associate_policy_is_preserved_on_new_boards(source):
    keywords = load_config().keywords
    for title, excluded in [("Associate Trader", True), ("Analyst / Associate Trader", False)]:
        raw = gh(source, [gh_row(source, title=title)])[0]
        assert bool(score_job(normalize(raw), keywords).score_breakdown.exclusions) == excluded


@pytest.mark.parametrize("value", [None, "Unknown", [], "Full Time"])
def test_pdt_requires_audited_contract_value(value):
    with pytest.raises(SourceUnavailable, match="employment type"):
        gh("pdt", [gh_row("pdt", metadata=[{"name": "Employment Type", "value": value}])])


def valkyrie_row():
    identifier = str(UUID(int=1))
    url = f"https://jobs.lever.co/valkyrietrading/{identifier}"
    return {
        "id": identifier,
        "text": "Junior Derivatives Trader",
        "hostedUrl": url,
        "applyUrl": url + "/apply",
        "categories": {"team": "Trading", "location": "Chicago, IL", "commitment": "Full Time"},
        "description": "<p>Operate our trading system and manage daily PnL.</p>",
        "lists": [{"text": "What You'll Need", "content": "<li>Quantitative skills.</li>"}],
        "createdAt": 1785865499173,
    }


def lever(rows):
    cfg = load_config().companies["valkyrie"]
    return parse_lever(rows, "valkyrie", cfg, LeverOptions(**cfg.options))


def test_valkyrie_uses_team_without_fabricating_department_or_publication():
    raw = lever([valkyrie_row()])[0]
    assert raw.employment_type == "Full Time" and raw.date_posted is None
    assert raw.seniority_hint is None  # The title is evidence; no invented campus category.
    assert "department" not in raw.raw_payload["categories"]
    assert "createdAt" not in raw.raw_payload
    row = valkyrie_row()
    row["categories"]["team"] = "Quants"
    row["text"] = "Quantitative Researcher (Experienced)"
    assert len(lever([row])) == 1
    row["categories"]["team"] = "Trade Support"
    assert not lever([row])


@pytest.mark.parametrize("field", ["team", "location", "commitment"])
@pytest.mark.parametrize("value", [None, "", []])
def test_valkyrie_category_drift_is_not_a_successful_empty_board(field, value):
    row = valkyrie_row()
    row["categories"][field] = value
    with pytest.raises(SourceUnavailable):
        lever([row])


def test_valkyrie_still_checks_tenant_contract_and_duplicate_ids():
    row = valkyrie_row()
    row["hostedUrl"] = row["hostedUrl"].replace("valkyrietrading", "other")
    with pytest.raises(SourceUnavailable, match="URL identity"):
        lever([row])
    row = valkyrie_row()
    row["categories"]["commitment"] = "Full-Time"
    with pytest.raises(SourceUnavailable, match="employment type"):
        lever([row])
    with pytest.raises(SourceUnavailable, match="duplicate"):
        lever([valkyrie_row(), valkyrie_row()])


def test_valkyrie_collection_remains_partial_and_bounded():
    cfg = deepcopy(load_config().companies["valkyrie"])

    def transport(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, json=[valkyrie_row()])

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(transport))
        cfg.request_interval = 0.1
        try:
            result = await build_collector("valkyrie", cfg, http).collect()
            assert len(result.jobs) == 1 and result.complete is False
        finally:
            await http.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "source,tenant,site",
    [
        ("wellington", "wellington", "External"),
        ("alliancebernstein", "abglobal", "alliancebernsteincareers"),
        ("dimensional", "dimensional", "DFA_Careers"),
    ],
)
def test_asset_managers_have_verified_bounded_workday_scope(source, tenant, site):
    cfg = deepcopy(load_config().companies[source])
    assert workday_base(cfg)[1].endswith(f"/wday/cxs/{tenant}/{site}")
    assert cfg.scan_interval == 1800 and cfg.options["max_details"] == 80
    assert (
        "trading" in cfg.options["search_terms"] and "intern" in cfg.options["exclude_title_terms"]
    )
    cfg.tenant = "wrong_employer"
    with pytest.raises(ValueError, match="tenant differs"):
        workday_base(cfg)
