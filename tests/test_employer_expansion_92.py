"""Employer identities, publication visibility and links for the next finance panel."""

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import load_config
from trading_radar.education import education_mentions
from trading_radar.greenhouse_filtered import API, GreenhouseOptions, parse_board
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.missions import mission_excerpts
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.workday import workday_base

BOARDS = {
    "gelber": ("Gelber Group", "https://job-boards.greenhouse.io/gelbergroup/jobs/123"),
    "verition": ("Verition Group LLC", "https://www.verition.com/open-positions?gh_jid=123"),
    "marshall_wace_graduates": (
        "Marshall Wace - Graduate & Associate roles",
        "https://job-boards.greenhouse.io/mw-tech-grad/jobs/123",
    ),
}


def posting(source):
    company, url = BOARDS[source]
    return {
        "id": 123,
        "internal_job_id": 456,
        "company_name": company,
        "absolute_url": url,
        "title": "Junior Execution Trader",
        "location": {"name": "London"},
        "content": "<p>Trade equities and FX. Full-time. Python.</p>",
        "metadata": None,
        "first_published": "2026-09-27T09:00:00-04:00",
        "updated_at": "2026-09-28T09:00:00Z",
    }


def parse(source, row):
    config = load_config().companies[source]
    return parse_board(
        {"meta": {"total": 1}, "jobs": [row]}, source, config, GreenhouseOptions(**config.options)
    )


@pytest.mark.parametrize("source", BOARDS)
def test_official_identity_keeps_publication_and_description_without_inventing_seniority(source):
    raw = parse(source, posting(source))[0]
    assert raw.apply_url == BOARDS[source][1]
    assert raw.date_posted == datetime(2026, 9, 27, 13, tzinfo=UTC)
    assert raw.description == posting(source)["content"]
    assert raw.seniority_hint is None and raw.expected_start_date is None


@pytest.mark.parametrize("source", BOARDS)
@pytest.mark.parametrize(
    "change",
    [
        {"company_name": "Another Company"},
        {"absolute_url": "https://evil.example/jobs/123"},
        {"id": 124},
        {"internal_job_id": False},
        {"content": ""},
        {"first_published": "2026-09-27T09:00:00"},
    ],
)
def test_changed_catalogue_fails_closed(source, change):
    with pytest.raises(SourceUnavailable):
        parse(source, posting(source) | change)


@pytest.mark.parametrize("source", BOARDS)
def test_absent_metadata_is_not_audited_null(source):
    row = posting(source)
    row.pop("metadata")
    with pytest.raises(SourceUnavailable, match="metadata"):
        parse(source, row)


@pytest.mark.parametrize("source", BOARDS)
@pytest.mark.parametrize(
    "title,excluded", [("Associate Trader", True), ("Analyst / Associate Trader", False)]
)
def test_associate_policy_is_preserved(source, title, excluded):
    raw = parse(source, posting(source) | {"title": title})[0]
    job = score_job(normalize(raw), load_config().keywords)
    assert bool(job.score_breakdown.exclusions) == excluded


@pytest.mark.parametrize("source", BOARDS)
def test_new_board_is_partial_and_uses_only_public_catalogue(source):
    config = deepcopy(load_config().companies[source])
    config.request_interval = 0.1

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert str(request.url) == API + config.tenant + "/jobs?content=true"
        return httpx.Response(200, json={"meta": {"total": 1}, "jobs": [posting(source)]})

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            result = await build_collector(source, config, http).collect()
            assert not result.complete and len(result.jobs) == 1
        finally:
            await http.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "source,root",
    [
        ("pimco", "https://pimco.wd1.myworkdayjobs.com/wday/cxs/pimco/pimco-careers"),
        ("cibc", "https://cibc.wd3.myworkdayjobs.com/wday/cxs/cibc/search"),
        ("td", "https://td.wd3.myworkdayjobs.com/wday/cxs/td/TD_Bank_Careers"),
        ("state_street", "https://statestreet.wd1.myworkdayjobs.com/wday/cxs/statestreet/Global"),
    ],
)
def test_observed_workday_sites_use_bounded_read_only_searches(source, root):
    config = deepcopy(load_config().companies[source])
    config.request_interval = 0.1
    assert workday_base(config)[1] == root
    observed = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert request.method == "POST" and str(request.url) == root + "/jobs"
        body = json.loads(request.content)
        assert (
            body["offset"] == 0
            and body["limit"] == 20
            and body["appliedFacets"] == config.options.get("applied_facets", {})
        )
        observed.append(body["searchText"])
        return httpx.Response(200, json={"total": 0, "jobPostings": []})

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            result = await build_collector(source, config, http).collect()
            assert not result.complete and not result.jobs
        finally:
            await http.close()

    asyncio.run(run())
    assert set(observed) == set(config.options["search_terms"])


@pytest.mark.parametrize("source", BOARDS)
@pytest.mark.parametrize(
    "title",
    [
        "Product Marketing - Trading Analyst",
        "Trading Summer Analyst",
        "Quantitative Research Talent Network",
    ],
)
def test_marketing_internships_and_prospect_pools_are_not_open_target_roles(source, title):
    assert not parse(source, posting(source) | {"title": title})


@pytest.mark.parametrize(
    "source,mission,qualification",
    [
        ("wolverine", "What You'll Do", "What We're Looking For"),
        ("gelber", "What you’ll do:", "What you’ll need:"),
        ("verition", "Responsibilities", "Qualifications"),
        ("pimco", "RESPONSIBILITIES", "REQUIREMENTS"),
        ("td", "Roles and responsibilities include:", "Qualifications"),
        (
            "state_street",
            "As an eFX Quant Analyst you will:",
            "Education &amp; Preferred Qualifications",
        ),
    ],
)
def test_audited_sections_preserve_qualifiers_without_changing_scores(
    source, mission, qualification
):
    cfg = load_config()
    raw = RawJob(
        source=source,
        company=cfg.companies[source].name,
        title="Quantitative Researcher",
        apply_url="https://example.org/jobs/123",
        location="London",
        description=f"<p><strong>{mission}</strong></p><ul><li>Execute FX trades under supervision.</li></ul>"
        f"<p><strong>{qualification}</strong></p><ul><li>A master's degree is preferred, or equivalent experience.</li></ul>",
    )
    job = score_job(normalize(raw), cfg.keywords)
    before = job.model_dump()
    assert mission_excerpts(job)["excerpts"] == ["Execute FX trades under supervision."]
    assert education_mentions(job)["levels"]
    assert job.model_dump() == before
    hidden = job.model_copy(update={"description": "<div hidden>" + raw.description + "</div>"})
    assert mission_excerpts(hidden) is None
    assert not education_mentions(hidden)["levels"]
