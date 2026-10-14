from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from tests.test_greenhouse_filtered import row
from trading_radar.config import Company
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.opportunity_details import opportunity_details
from trading_radar.programmes import programme
from trading_radar.selection import rejection_reason
from trading_radar.workday import WorkdayOptions, workday_base

KEYS = ["state_street", "mizuho", "northern_trust", "lseg", "gsa_capital", "quadrature"]


def profiles():
    return yaml.safe_load(Path("config/vps-companies.yaml").read_text())["companies"]


def sample(tenant):
    return row(
        tenant,
        company_name="GSA" if tenant == "gsacapital" else "Quadrature Capital",
        absolute_url=(
            "https://www.gsacapital.com/careers/gh/?gh_jid=1"
            if tenant == "gsacapital"
            else "https://job-boards.greenhouse.io/quadraturecapital/jobs/1"
        ),
        title="Quantitative Research Intern - Off-Cycle 2027",
        metadata=[] if tenant == "gsacapital" else None,
        content="<h2>Requirements</h2><p>Previous experience in quantitative research is preferred.</p>"
        "<h2>The internship</h2><p>Off-cycle internship for six months. Start date: 1 September 2027.</p>",
    )


@pytest.mark.parametrize("key", KEYS)
def test_new_profiles_keep_long_off_cycle_and_all_scores_collectable(key):
    config = Company(**profiles()[key])
    assert config.enabled
    assert config.scan_interval == 1800
    options = (
        GreenhouseOptions(**config.options)
        if config.ats == "greenhouse_filtered"
        else WorkdayOptions(**config.options)
    )
    assert rejection_reason("Quantitative Research Intern - Off-Cycle 2027", options) is None
    assert rejection_reason("Senior FX Trader", options) is None
    assert rejection_reason("Graduate Trader", options) is None
    assert rejection_reason("Trading Operations Analyst", options) is not None
    assert rejection_reason("Summer Internship - Trading 2027", options) is not None


@pytest.mark.parametrize("key", KEYS[:4])
def test_workday_roots_match_the_verified_tenant(key):
    config = Company(**profiles()[key])
    site, api = workday_base(config)
    assert config.tenant in api
    assert site == config.career_url
    assert config.options["verify_listing_snapshot"] is True
    assert config.options["conditional_details"] is True
    assert "trading" in config.options["search_terms"]


@pytest.mark.parametrize(
    "key,tenant", [("gsa_capital", "gsacapital"), ("quadrature", "quadraturecapital")]
)
def test_verified_fund_row_keeps_full_description_and_explicit_start(key, tenant):
    config = Company(**profiles()[key])
    payload = {"jobs": [sample(tenant)], "meta": {"total": 1}}
    before = deepcopy(payload)
    jobs = parse_board(payload, key, config, GreenhouseOptions(**config.options))
    assert len(jobs) == 1 and payload == before
    if tenant == "gsacapital":
        assert (
            jobs[0].apply_url == "https://boards.greenhouse.io/embed/job_app?for=gsacapital&token=1"
        )
    job = normalize(jobs[0])
    facts = opportunity_details(job)
    assert facts["start"]["label"] == "01/09/2027"
    assert facts["experience"]["minimum_years"] is None
    assert facts["experience"]["status"] == "qualitative"
    assert "preferred" in facts["experience"]["evidence"][0]
    assert programme(job)["kind"] == "internship"


@pytest.mark.parametrize(
    "key,tenant", [("gsa_capital", "gsacapital"), ("quadrature", "quadraturecapital")]
)
@pytest.mark.parametrize("change", ["company", "url_id", "host", "duplicate", "total"])
def test_fund_identity_and_catalogue_changes_fail_closed(key, tenant, change):
    config = Company(**profiles()[key])
    item = sample(tenant)
    payload = {"jobs": [item], "meta": {"total": 1}}
    if change == "company":
        item["company_name"] = "Another Employer"
    elif change == "url_id":
        item["absolute_url"] = (
            item["absolute_url"].replace("=1", "=2").replace("/jobs/1", "/jobs/2")
        )
    elif change == "host":
        item["absolute_url"] = (
            item["absolute_url"]
            .replace("www.gsacapital.com", "example.com")
            .replace("job-boards.greenhouse.io", "example.com")
        )
    elif change == "duplicate":
        payload["jobs"].append(deepcopy(item))
        payload["meta"]["total"] = 2
    else:
        payload["meta"]["total"] = 2
    with pytest.raises(SourceUnavailable):
        parse_board(payload, key, config, GreenhouseOptions(**config.options))


def test_quadrature_prospect_internship_is_not_an_open_vacancy():
    config = Company(**profiles()["quadrature"])
    item = sample("quadraturecapital")
    item["internal_job_id"] = None
    item["title"] = "Internships"
    assert (
        parse_board(
            {"jobs": [item], "meta": {"total": 1}},
            "quadrature",
            config,
            GreenhouseOptions(**config.options),
        )
        == []
    )


def test_gsa_events_are_not_job_opportunities():
    config = Company(**profiles()["gsa_capital"])
    options = GreenhouseOptions(**config.options)
    for title in [
        "Quant Talk - University of Oxford",
        "Trading & Technology Insight Programme 2027",
        "Digital Competition - SPARK 2026",
    ]:
        assert rejection_reason(title, options) is not None
