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
    "aquatic": (
        "Aquatic Capital Management",
        "https://job-boards.greenhouse.io/aquaticcapitalmanagement/jobs/123",
    ),
    "graviton": (
        "Graviton Research Capital LLP",
        "https://job-boards.greenhouse.io/gravitonresearchcapital/jobs/123",
    ),
    "aqr": ("AQR", "https://careers.aqr.com/jobs?gh_jid=123&gh_jid=123"),
    "winton": ("Winton", "https://job-boards.eu.greenhouse.io/winton/jobs/123"),
    "worldquant": ("WorldQuant", "https://job-boards.greenhouse.io/worldquant/jobs/123"),
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
        "metadata": [{"name": "Post Job?", "value": True}] if source == "aqr" else None,
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


@pytest.mark.parametrize("value", [False, None])
def test_aqr_only_explicit_publication_is_imported(value):
    row = posting("aqr")
    row["metadata"][0]["value"] = value
    assert parse("aqr", row) == []
    row["metadata"][0]["value"] = True
    assert parse("aqr", row)[0].raw_payload["fields"]["Post Job?"] is True


@pytest.mark.parametrize(
    "metadata",
    [
        [],
        [{"name": "Post Job?", "value": "true"}],
        [{"name": "Post Job?", "value": 1}],
        [{"name": "Post Job?", "value": True}, {"name": "Post Job?", "value": False}],
    ],
)
def test_aqr_visibility_must_be_unambiguous(metadata):
    with pytest.raises(SourceUnavailable):
        parse("aqr", posting("aqr") | {"metadata": metadata})


@pytest.mark.parametrize(
    "query",
    [
        "gh_jid=123",
        "gh_jid=123&gh_jid=124",
        "gh_jid=124&gh_jid=123",
        "gh_jid=123&gh_jid=123&gh_jid=123",
        "gh_jid=123&gh_jid=123&extra=1",
        "gh_jid=123&gh_jid=123#apply",
    ],
)
def test_aqr_duplicate_ids_must_both_match_exactly(query):
    with pytest.raises(SourceUnavailable, match="URL identity"):
        parse("aqr", posting("aqr") | {"absolute_url": "https://careers.aqr.com/jobs?" + query})


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
        ("g_research", "https://gresearch.wd103.myworkdayjobs.com/wday/cxs/gresearch/G-Research"),
        ("ing", "https://ing.wd3.myworkdayjobs.com/wday/cxs/ing/ICSGBLCOR"),
        (
            "blackrock",
            "https://blackrock.wd1.myworkdayjobs.com/wday/cxs/blackrock/BlackRock_Professional",
        ),
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
        assert body["offset"] == 0 and body["limit"] == 20 and body["appliedFacets"] == {}
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
        ("graviton", "Key Responsibilities:", "Required Skills &amp; Qualifications:"),
        ("aqr", "Your Role:", "What You’ll Bring:"),
        ("winton", "Your responsibilities will include:", "What we are looking for:"),
        ("worldquant", "The Role:", "What You’ll Bring:"),
        ("g_research", "The role", "The ideal candidate will have:"),
        ("blackrock", "Key Responsibilities:", "Qualifications, Knowledge and Experience:"),
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


def test_aquatic_degree_mentions_keep_alternatives_without_inventing_missions():
    raw = RawJob(
        source="aquatic",
        company="Aquatic Capital Management",
        title="Quantitative Researcher",
        apply_url=BOARDS["aquatic"][1],
        location="Chicago",
        description="<p>Candidate requirements:</p><ul><li>PhD or equivalent research experience.</li></ul>",
    )
    job = normalize(raw)
    assert education_mentions(job)["levels"]
    assert mission_excerpts(job) is None
