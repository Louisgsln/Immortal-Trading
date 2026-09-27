"""Verified board identities and contract evidence for the diversified expansion."""

import asyncio
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

SOURCES = {
    "mako": ("mako", "Mako", "https://www.mako.com/opportunities/job-listing/123?gh_jid=123"),
    "geneva_trading": (
        "genevatrading",
        "Geneva Trading",
        "https://job-boards.greenhouse.io/genevatrading/jobs/123",
    ),
    "da_vinci": (
        "davinciderivatives",
        "Da Vinci",
        "https://job-boards.eu.greenhouse.io/davinciderivatives/jobs/123",
    ),
    "qube_research": (
        "quberesearchandtechnologies",
        "Qube Research & Technologies",
        "https://job-boards.greenhouse.io/quberesearchandtechnologies/jobs/123",
    ),
    "man_group": (
        "mangroup",
        "Man Group",
        "https://job-boards.eu.greenhouse.io/mangroup/jobs/123",
    ),
}


def posting(source):
    _, company, url = SOURCES[source]
    metadata = {
        "mako": None,
        "geneva_trading": [{"name": "Project Alignment", "value": None}],
        "da_vinci": None,
        "qube_research": [{"name": "Employment Type", "value": "Full-time"}],
        "man_group": [{"name": "Workforce Sub-Type", "value": "Regular"}],
    }[source]
    return {
        "id": 123,
        "internal_job_id": 456,
        "company_name": company,
        "title": "Graduate Trader",
        "absolute_url": url,
        "location": {"name": "London"},
        "metadata": metadata,
        "content": "<p>Trade equity options. Full-time. Python.</p>",
        "first_published": "2026-09-01T09:00:00-04:00",
        "updated_at": "2026-09-25T09:00:00Z",
    }


def parse(source, item):
    config = load_config().companies[source]
    return parse_board(
        {"meta": {"total": 1}, "jobs": [item]},
        source,
        config,
        GreenhouseOptions(**config.options),
    )


@pytest.mark.parametrize("source", SOURCES)
def test_verified_identity_preserves_publication_and_does_not_invent_intake(source):
    job = parse(source, posting(source))[0]
    assert job.date_posted == datetime(2026, 9, 1, 13, tzinfo=UTC)
    assert job.expected_start_date is None and job.seniority_hint is None
    assert job.description == posting(source)["content"]
    expected_url = (
        "https://www.mako.com/opportunities/job-listing?gh_jid=123"
        if source == "mako"
        else SOURCES[source][2]
    )
    assert job.apply_url == expected_url


@pytest.mark.parametrize("source", SOURCES)
@pytest.mark.parametrize(
    "change",
    [
        {"company_name": "Another Company"},
        {"absolute_url": "https://evil.example/jobs/123"},
        {"id": 124},
        {"internal_job_id": False},
        {"location": {}},
        {"content": ""},
        {"first_published": "2026-09-01T09:00:00"},
    ],
)
def test_board_change_fails_closed(source, change):
    with pytest.raises(SourceUnavailable):
        parse(source, posting(source) | change)


@pytest.mark.parametrize("source", SOURCES)
def test_missing_metadata_is_not_equivalent_to_audited_null(source):
    item = posting(source)
    item.pop("metadata")
    with pytest.raises(SourceUnavailable, match="metadata missing"):
        parse(source, item)


@pytest.mark.parametrize("source", ["qube_research", "man_group"])
@pytest.mark.parametrize("contract", ["Intern", None])
def test_contract_evidence_is_preserved_even_without_intern_in_title(source, contract):
    item = posting(source)
    item["metadata"][0]["value"] = contract
    raw = parse(source, item)[0]
    assert raw.employment_type == contract
    job = score_job(normalize(raw), load_config().keywords)
    assert bool(job.score_breakdown.exclusions) == (contract == "Intern")


@pytest.mark.parametrize("source", ["qube_research", "man_group"])
@pytest.mark.parametrize("metadata", [[], [{"name": "Employment Type", "value": "Unknown"}]])
def test_missing_or_unknown_contract_rejects_selected_role(source, metadata):
    with pytest.raises(SourceUnavailable, match="employment type"):
        parse(source, posting(source) | {"metadata": metadata})


@pytest.mark.parametrize("query", ["gh_jid=124", "gh_jid=123&extra=yes", "gh_jid=123&gh_jid=123"])
def test_mako_custom_url_checks_both_identifiers(query):
    item = posting("mako")
    item["absolute_url"] = item["absolute_url"].split("?")[0] + "?" + query
    with pytest.raises(SourceUnavailable, match="URL identity"):
        parse("mako", item)


@pytest.mark.parametrize("source", SOURCES)
@pytest.mark.parametrize("title", ["Trading Operations Analyst", "Senior Trader", "Quant Intern"])
def test_expansion_filters_irrelevant_titles(source, title):
    assert not parse(source, posting(source) | {"title": title})


@pytest.mark.parametrize("source", SOURCES)
@pytest.mark.parametrize(
    "title,excluded", [("Associate Trader", True), ("Analyst / Associate Trader", False)]
)
def test_associate_policy_remains_unchanged(source, title, excluded):
    raw = parse(source, posting(source) | {"title": title})[0]
    scored = score_job(normalize(raw), load_config().keywords)
    assert bool(scored.score_breakdown.exclusions) == excluded


@pytest.mark.parametrize("source", SOURCES)
def test_collector_uses_public_api_and_returns_partial_scope(source):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert str(request.url) == API + SOURCES[source][0] + "/jobs?content=true"
        return httpx.Response(200, json={"meta": {"total": 1}, "jobs": [posting(source)]})

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler))
        config = deepcopy(load_config().companies[source])
        config.request_interval = 0.001
        try:
            result = await build_collector(source, config, http).collect()
            assert len(result.jobs) == 1 and not result.complete
        finally:
            await http.close()

    asyncio.run(run())


def test_three_banks_have_bounded_queries_and_all_new_sources_are_scheduled():
    cfg = load_config()
    for source in set(SOURCES) | {"bank_of_america", "rbc", "wells_fargo"}:
        company = cfg.companies[source]
        assert company.enabled and company.scan_interval == 1800
        assert company.request_interval >= 2
        assert company.options["max_results_per_query"] == 500
        if company.ats == "workday":
            assert company.options["max_details"] == 80
            assert company.options["search_terms"] == [
                "trading",
                "trader",
                "quantitative",
                "structuring",
            ]
    assert cfg.settings.bootstrap_silent
    assert cfg.companies["wells_fargo"].options["applied_facets"] == {
        "jobFamily": [
            "6cee717ed86e0100b32510f615390000",
            "1018d766e49a1001be3a1fcd33700000",
            "6cee717ed86e0100b3250fc26f7d0000",
            "a474682131921001babf17eb9f800000",
        ]
    }


@pytest.mark.parametrize(
    "source,mission,qualifications",
    [
        ("mako", "What you'll be doing:", "What we need from you:"),
        ("geneva_trading", "The Role:", "The Ideal Candidate"),
        ("da_vinci", "Responsibilities", "Requirements"),
        ("qube_research", "Your future role within QRT", "Your present skillset"),
        ("man_group", "Role &amp; Responsibilities", "Skills &amp; Qualifications"),
        ("bank_of_america", "Key Responsibilities:", "Required Qualifications:"),
        ("rbc", "What will you do?", "Must-have"),
        ("wells_fargo", "In this role, you will:", "Required Qualifications:"),
    ],
)
def test_audited_sections_preserve_qualifiers_and_do_not_promote_scores(
    source, mission, qualifications
):
    cfg = load_config()
    raw = RawJob(
        source=source,
        company=cfg.companies[source].name,
        title="Trader",
        apply_url="https://example.org/job/123",
        location="London",
        description=f"<p><strong>{mission}</strong></p>"
        "<ul><li>Execute FX trades under supervision.</li></ul>"
        f"<p><strong>{qualifications}</strong></p>"
        "<ul><li>A master's degree is preferred, or equivalent experience.</li></ul>",
    )
    job = score_job(normalize(raw), cfg.keywords)
    before = job.model_dump()
    assert mission_excerpts(job)["excerpts"] == ["Execute FX trades under supervision."]
    assert education_mentions(job)["levels"]
    assert job.model_dump() == before
    hidden = job.model_copy(update={"description": "<div hidden>" + raw.description + "</div>"})
    assert mission_excerpts(hidden) is None
    assert not education_mentions(hidden)["levels"]
