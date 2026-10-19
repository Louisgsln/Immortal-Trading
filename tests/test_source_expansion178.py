"""Audited additional boards keep shared completeness, identity and internship rules."""

import asyncio
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
import yaml

from tests.test_greenhouse_filtered import payload, row
from tests.test_source_expansion172 import bank, collect, sf_detail, sf_page
from trading_radar.collectors import build_collector
from trading_radar.config import Company, load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import SourceUnavailable
from trading_radar.programmes import programme_company
from trading_radar.selection import rejection_reason
from trading_radar.successfactors_public import SITES
from trading_radar.workday import workday_base

SOURCES = {"lloyds", "lombard_odier", "janus_henderson", "belvedere", "tibra", "eclipse"}


def profiles():
    return yaml.safe_load(Path("config/vps-companies.yaml").read_text())["companies"]


def test_six_verified_employers_and_existing_source_inventory_are_preserved():
    vps = profiles()
    default = load_config().companies
    assert sum(c.get("enabled", False) for c in vps.values()) == 128
    assert len({c["name"] for c in vps.values() if c.get("enabled")}) == 116
    for source in SOURCES:
        assert default[source].model_dump() == Company(**vps[source]).model_dump()
        assert default[source].enabled
    for source in ["cfm", "qube_research", "hsbc_graduates", "bank_of_america_campus"]:
        assert vps[source]["enabled"]


@pytest.mark.parametrize("source", sorted(SOURCES))
def test_off_cycle_long_and_zero_score_senior_roles_are_not_silently_filtered(source):
    c = load_config()
    company = programme_company(
        c.companies[source], c.settings.model_copy(update={"include_internships": True})
    )
    collector = build_collector(source, company, None)
    options = collector.options
    for title in [
        "Global Markets Off-Cycle Internship 2027",
        "Quantitative Trading Intern - 6 months",
        "Senior Quantitative Researcher",
        "Graduate Trader | 2027 Intake",
    ]:
        assert rejection_reason(title, options) is None
    assert rejection_reason("Quantitative Trading Intern - Summer 2027", options) is not None
    assert rejection_reason("Talent Community Trading", options) is not None


@pytest.mark.parametrize("source,tenant", [("lloyds", "lbg"), ("lombard_odier", "lombardodier")])
def test_banks_use_employer_linked_workday_site_roots(source, tenant):
    company = load_config().companies[source]
    board, api = workday_base(company)
    assert board == company.career_url and f"/wday/cxs/{tenant}/" in api
    assert company.options["verify_listing_snapshot"] and company.options["conditional_details"]


def test_rbc_recovery_retains_queries_and_raises_only_the_bounded_catalogue_limit():
    company = load_config().companies["rbc"]
    assert company.options["max_results_per_query"] == 1000
    assert company.options["search_terms"] == [
        "trading",
        "trader",
        "quantitative",
        "structuring",
        "markets",
        "off-cycle",
        "internship",
    ]
    assert company.options["max_scan_seconds"] == 600


def test_janus_successfactors_reads_all_pages_and_rechecks_before_success(monkeypatch):
    reads = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        reads.append(req.url.path)
        if req.url.path == "/search/":
            assert req.url.params["locale"] == "en_US"
            return httpx.Response(
                200, text=sf_page("Janus Henderson", 26, int(req.url.params["startrow"]))
            )
        return httpx.Response(
            200, text=sf_detail("Janus Henderson", int(req.url.path.rstrip("/").rsplit("/", 1)[1]))
        )

    result = asyncio.run(collect(bank("Janus Henderson"), handler, monkeypatch))
    assert len(result.jobs) == 26 and result.scope_complete and not result.complete
    assert reads.count("/search/") == 3
    assert all(j.company == "Janus Henderson" for j in result.jobs)
    assert SITES["Janus Henderson"][0] == "https://jobs.janushenderson.com"


def test_eclipse_null_metadata_is_explicit_but_identity_and_count_remain_strict():
    company = load_config().companies["eclipse"]
    public = row("eclipsetrading", company_name="Eclipse Trading ", metadata=None)
    result = parse_board(
        payload([public]), "eclipse", company, GreenhouseOptions(**company.options)
    )
    assert result[0].title == "Graduate Trader" and result[0].source_type == "official"
    assert result[0].minimum_experience_years is None
    for field, value in [
        ("company_name", "Other Employer"),
        ("absolute_url", "https://evil.test/jobs/1"),
    ]:
        changed = deepcopy(public)
        changed[field] = value
        with pytest.raises(SourceUnavailable):
            parse_board(
                payload([changed]), "eclipse", company, GreenhouseOptions(**company.options)
            )
    with pytest.raises(SourceUnavailable):
        parse_board(
            {"jobs": [public], "meta": {"total": 2}},
            "eclipse",
            company,
            GreenhouseOptions(**company.options),
        )


def test_tibra_explicit_empty_catalogue_is_valid_but_never_closes_by_absence(monkeypatch):
    company = load_config().companies["tibra"]
    board = company.career_url

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("llms.txt"):
            return httpx.Response(
                200,
                text=f"# Tibra Capital Careers\nAll open roles (GET `{board}jobs.md`): 0 current openings",
            )
        return httpx.Response(
            200,
            text="# Tibra Capital — All Open Positions\n| Title | Department | Location | Type | Salary | Posted | Details |\n",
        )

    result = asyncio.run(collect(company, handler, monkeypatch))
    assert result.scope_complete and not result.complete and not result.jobs
