import asyncio
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import load_config
from trading_radar.education import education_mentions
from trading_radar.finance_sections import EMPLOYERS, QUALIFICATIONS, RESPONSIBILITIES
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.missions import mission_excerpts
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job

SAMPLES = json.loads(Path("tests/fixtures/finance_boards.json").read_text(encoding="utf-8"))


def parsed(source, row):
    company = load_config().companies[source]
    return parse_board(
        {"jobs": [row], "meta": {"total": 1}}, source, company, GreenhouseOptions(**company.options)
    )


@pytest.mark.parametrize("source", SAMPLES)
def test_ten_official_boards_keep_identity_and_original_publication(source):
    raw = parsed(source, copy.deepcopy(SAMPLES[source]))[0]
    assert raw.source == source and raw.source_type == "official"
    assert raw.date_posted.isoformat() == "2026-09-26T10:00:00+00:00"
    assert raw.expected_start_date is None and raw.application_deadline is None
    row = copy.deepcopy(SAMPLES[source])
    row.pop("first_published")
    assert parsed(source, row)[0].date_posted is None
    assert load_config().companies[source].enabled


@pytest.mark.parametrize("source", SAMPLES)
@pytest.mark.parametrize(
    "mutation", ["host", "id", "query", "company", "missing_metadata", "prospect"]
)
def test_bad_board_identities_never_import_or_claim_closures(source, mutation):
    row = copy.deepcopy(SAMPLES[source])
    if mutation == "host":
        row["absolute_url"] = row["absolute_url"].replace(
            urlsplit(row["absolute_url"]).netloc, "example.test"
        )
    if mutation == "id":
        row["id"] += 1
    if mutation == "query":
        row["absolute_url"] += "&gh_jid=999"
    if mutation == "company":
        row["company_name"] = "Other Financial Firm"
    if mutation == "missing_metadata":
        row.pop("metadata")
    if mutation == "prospect":
        row["internal_job_id"] = None
        assert parsed(source, row) == []
    else:
        with pytest.raises(SourceUnavailable):
            parsed(source, row)


@pytest.mark.parametrize(
    "source,field",
    [
        ("akuna_capital", "Experience"),
        ("five_rings", "Job Classification"),
        ("hudson_river_trading", "Job Type"),
    ],
)
@pytest.mark.parametrize("value", [None, {}, ["unknown"], 1])
def test_unknown_metadata_does_not_create_a_junior_hint(source, field, value):
    row = copy.deepcopy(SAMPLES[source])
    next(m for m in row["metadata"] if m["name"] == field)["value"] = value
    with pytest.raises(SourceUnavailable):
        parsed(source, row)


def test_contradictory_campus_and_intern_contract_stays_excluded():
    row = copy.deepcopy(SAMPLES["five_rings"])
    for m in row["metadata"]:
        if m["name"] == "Employment Type":
            m["value"] = "Intern"
        if m["name"] == "Job Classification":
            m["value"] = "Campus Hire"
    job = score_job(normalize(parsed("five_rings", row)[0]), load_config().keywords)
    assert job.score_breakdown.total == 0


def test_live_adapter_uses_complete_single_response_with_partial_business_scope():
    asyncio.run(check_live_adapter())


async def check_live_adapter():
    row = SAMPLES["transmarket_group"]
    c = load_config().companies["transmarket_group"]

    async def handle(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        assert (
            str(request.url)
            == "https://boards-api.greenhouse.io/v1/boards/transmarketgroup/jobs?content=true"
        )
        return httpx.Response(200, json={"jobs": [row], "meta": {"total": 1}})

    h = HTTPClient(transport=httpx.MockTransport(handle))
    c.request_interval = 0.1
    try:
        result = await build_collector("transmarket_group", c, h).collect()
        assert len(result.jobs) == 1 and result.complete is False
    finally:
        await h.close()


@pytest.mark.parametrize("source", EMPLOYERS)
def test_employer_sections_keep_preferences_without_boilerplate(job, source):
    qualification = sorted(QUALIFICATIONS[source])[0]
    responsibility = sorted(RESPONSIBILITIES[source])[0]
    content = f"<p>About us</p><ul><li>We fund PhDs</li></ul><p>{responsibility}</p><ul><li>Develop trading strategies.</li></ul><p>{qualification}</p><ul><li>Master’s degree preferred, or equivalent work experience.</li></ul>"
    current = job.model_copy(update={"source": source, "description": content})
    assert (
        education_mentions(current)["evidence"][0]["excerpt"]
        == "Master’s degree preferred, or equivalent work experience."
    )
    assert mission_excerpts(current)["excerpts"] == ["Develop trading strategies."]


def test_new_quantitative_research_requires_role_duty_not_company_intro():
    source = "point72"
    row = copy.deepcopy(SAMPLES[source])
    row["title"] = "Quantitative Researcher"
    row["content"] = (
        "<p>Responsibilities</p><ul><li>Develop predictive models for trading strategies.</li></ul><p>Requirements</p><ul><li>Python.</li></ul>"
    )
    job = score_job(normalize(parsed(source, row)[0]), load_config().keywords)
    assert "QUANT_RESEARCH" in job.desk
    row["content"] = row["content"].replace("Responsibilities", "About us")
    assert (
        "QUANT_RESEARCH"
        not in score_job(normalize(parsed(source, row)[0]), load_config().keywords).desk
    )


@pytest.mark.parametrize(
    "source,title",
    [
        ("maven_securities", "Women in Trading"),
        ("hudson_river_trading", "Electronic Trading Support Engineer"),
        ("tower_research", "Central Trading Analyst"),
        ("schonfeld", "Trading Assistant"),
        ("akuna_capital", "Experienced Options Trader"),
    ],
)
def test_audited_out_of_scope_listings_do_not_enter_new_sources(source, title):
    row = copy.deepcopy(SAMPLES[source])
    row["title"] = title
    assert parsed(source, row) == []
