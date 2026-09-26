import asyncio
import copy
import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.lever_filtered import LeverOptions, section_content
from trading_radar.lever_filtered import parse_board as parse_lever
from trading_radar.missions import mission_excerpts
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job

SAMPLES = json.loads(Path("tests/fixtures/finance_boards75.json").read_text(encoding="utf-8"))


def greenhouse(source, row):
    company = load_config().companies[source]
    return parse_board(
        {"jobs": [row], "meta": {"total": 1}}, source, company, GreenhouseOptions(**company.options)
    )


@pytest.mark.parametrize("source", SAMPLES)
def test_new_board_identity_date_and_no_contact_metadata(source):
    row = copy.deepcopy(SAMPLES[source])
    if row["metadata"] is not None:
        row["metadata"].append(
            {"name": "Discipline Head", "value": {"email": "private@example.test"}}
        )
    raw = greenhouse(source, row)[0]
    assert raw.source_type == "official"
    assert raw.date_posted.isoformat() == "2026-09-26T10:00:00+00:00"
    assert "private@" not in json.dumps(raw.raw_payload)
    row.pop("first_published")
    assert greenhouse(source, row)[0].date_posted is None
    row["internal_job_id"] = None
    assert greenhouse(source, row) == []


@pytest.mark.parametrize("source", SAMPLES)
@pytest.mark.parametrize("change", ["company", "host", "id", "duplicate_query", "metadata"])
def test_new_boards_reject_changed_identity_or_schema(source, change):
    row = copy.deepcopy(SAMPLES[source])
    if change == "company":
        row["company_name"] = "Another employer"
    if change == "host":
        row["absolute_url"] = row["absolute_url"].replace("https://", "https://evil.test/")
    if change == "id":
        row["id"] += 1
    if change == "duplicate_query":
        row["absolute_url"] += "?gh_jid=1&gh_jid=2"
    if change == "metadata":
        row.pop("metadata")
    with pytest.raises(SourceUnavailable):
        greenhouse(source, row)


@pytest.mark.parametrize(
    "level,contract,valid,junior",
    [
        ("Early Careers Opportunity", "Employee-Regular", True, "junior"),
        ("Experienced Professional", "Full-time", True, None),
        ("Internship", "Employee-Intern", True, None),
        ("Internship", "Intern Full-time", True, None),
        ("Internship", "Full-time", False, None),
        ("Early Careers Opportunity", "Employee-Intern", False, None),
        ("Future category", "Full-time", False, None),
        (None, "Full-time", False, None),
        ([], "Full-time", False, None),
        ("Early Careers Opportunity", "Unknown", False, None),
    ],
)
def test_squarepoint_explicit_level_and_contract(level, contract, valid, junior):
    row = copy.deepcopy(SAMPLES["squarepoint_capital"])
    row["title"] = "Quantitative Trader"
    row["metadata"] = [
        {"name": "Employment Type", "value": contract},
        {"name": "Job Board Experience Level", "value": level},
    ]
    if not valid:
        with pytest.raises(SourceUnavailable):
            greenhouse("squarepoint_capital", row)
        return
    raw = greenhouse("squarepoint_capital", row)[0]
    assert raw.seniority_hint == junior
    if level == "Internship":
        assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0


@pytest.mark.parametrize(
    "title,accepted",
    [
        ("Quant Trading Associate - 2027 Start", False),
        ("Quant Trading Analyst / Associate", True),
        ("Quant Trading Internship - Summer 2027", False),
    ],
)
def test_campus_does_not_override_associate_or_intern_exclusions(title, accepted):
    row = copy.deepcopy(SAMPLES["chicago_trading_campus"])
    row["title"] = title
    scored = score_job(
        normalize(greenhouse("chicago_trading_campus", row)[0]), load_config().keywords
    )
    assert (scored.score_breakdown.total > 0) == accepted


@pytest.mark.parametrize("title", ["Trading & Risk", "Quantitative Research & Development"])
def test_walleye_generic_interest_posts_are_outside_configured_scope(title):
    row = copy.deepcopy(SAMPLES["walleye_capital"])
    row["title"] = title
    assert greenhouse("walleye_capital", row) == []


def lever_row(number=1):
    identifier = str(UUID(int=number))
    url = "https://jobs.lever.co/belvederetrading/" + identifier
    return {
        "id": identifier,
        "text": "Quantitative Trader - Entry Level 2027",
        "hostedUrl": url,
        "applyUrl": url + "/apply",
        "createdAt": 1785865499173,
        "categories": {
            "department": "Trading",
            "team": "Campus - Quantitative Trading",
            "commitment": "Full-Time",
            "location": "Chicago, Illinois",
        },
        "description": "<p>Join our trading team.</p>",
        "lists": [
            {
                "text": "What our Quantitative Traders do",
                "content": "<div><ul><li>Develop trading strategies.</li></ul></div>",
            },
            {
                "text": "Key qualities in great candidates",
                "content": "<div><li>Bachelor degree or equivalent experience.</li></div>",
            },
        ],
        "additional": "<p>Closing text.</p>",
    }


def lever(rows):
    c = load_config().companies["belvedere_trading"]
    return parse_lever(rows, "belvedere_trading", c, LeverOptions(**c.options))


def test_lever_has_no_invented_publication_and_keeps_sections():
    raw = lever([lever_row()])[0]
    assert raw.date_posted is None and raw.expected_start_date is None
    assert raw.seniority_hint == "junior" and raw.source_type == "official"
    assert raw.apply_url.endswith("/apply") and not raw.source_url.endswith("/apply")
    job = score_job(normalize(raw), load_config().keywords)
    assert mission_excerpts(job)["excerpts"] == ["Develop trading strategies."]
    assert "Closing text." in job.description_text
    assert "createdAt" not in raw.raw_payload


@pytest.mark.parametrize(
    "change",
    [
        "id",
        "host",
        "tenant",
        "apply",
        "query",
        "title",
        "categories",
        "contract",
        "description",
        "lists",
        "list_heading",
        "list_body",
        "additional",
    ],
)
def test_lever_fails_closed_on_identity_and_schema_drift(change):
    row = lever_row()
    if change == "id":
        row["id"] = "not-a-uuid"
    if change == "host":
        row["hostedUrl"] = row["hostedUrl"].replace("jobs.lever.co", "evil.test")
    if change == "tenant":
        row["hostedUrl"] = row["hostedUrl"].replace("belvederetrading", "other")
    if change == "apply":
        row["applyUrl"] = row["hostedUrl"]
    if change == "query":
        row["hostedUrl"] += "?tracking=1"
    if change == "title":
        row["text"] = ""
    if change == "categories":
        row.pop("categories")
    if change == "contract":
        row["categories"]["commitment"] = "New type"
    if change == "description":
        row["description"] = None
    if change == "lists":
        row.pop("lists")
    if change == "list_heading":
        row["lists"][0]["text"] = None
    if change == "list_body":
        row["lists"][0]["content"] = ""
    if change == "additional":
        row["additional"] = {}
    with pytest.raises(SourceUnavailable):
        lever([row])


def test_lever_department_contract_and_duplicate_controls():
    row = lever_row()
    row["categories"]["department"] = "People"
    assert lever([row]) == []
    row = lever_row()
    row["categories"]["commitment"] = "Intern"
    raw = lever([row])[0]
    assert raw.seniority_hint is None
    assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0
    with pytest.raises(SourceUnavailable):
        lever([lever_row(), lever_row()])


def test_lever_section_preserves_prose_and_ignores_hidden_list():
    content = "<p>Required explanation.</p><li>One duty.</li>"
    assert section_content(content) == content
    assert (
        section_content("<div hidden><li>Hidden duty.</li></div><div><li>Real duty.</li></div>")
        == "<ul><li>Real duty.</li></ul>"
    )


@pytest.mark.parametrize(
    "scenario",
    ["single", "pages", "repeat", "changing", "excess", "bad_page", "detail_limit", "timeout"],
)
def test_lever_bounded_real_adapter(scenario, monkeypatch):
    monkeypatch.setattr("trading_radar.lever_filtered.PAGE_SIZE", 2)
    asyncio.run(collect_scenario(scenario))


async def collect_scenario(scenario):
    c = load_config().companies["belvedere_trading"]
    c.request_interval = 0.1
    if scenario == "excess":
        c.options["max_results_per_query"] = 2
    if scenario == "detail_limit":
        c.options["max_details"] = 1
    calls = []

    async def handle(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        assert request.url.host == "api.lever.co"
        assert request.url.path == "/v0/postings/belvederetrading"
        offset = int(request.url.params["skip"])
        calls.append(offset)
        if scenario == "timeout":
            raise TimeoutError()
        if scenario == "bad_page":
            return httpx.Response(200, json={"jobs": []})
        if scenario == "single":
            rows = [lever_row()]
        elif offset == 0:
            rows = [lever_row(), lever_row(2)]
            if scenario == "changing" and len(calls) > 1:
                rows[0]["text"] = "Changed Trader"
        elif scenario == "repeat":
            rows = [lever_row(), lever_row(2)]
        else:
            rows = [lever_row(3)]
        return httpx.Response(200, json=rows)

    http = HTTPClient(transport=httpx.MockTransport(handle))
    try:
        collector = build_collector("belvedere_trading", c, http)
        if scenario in {"single", "pages"}:
            result = await collector.collect()
            assert result.complete is False
            assert len(result.jobs) == (1 if scenario == "single" else 3)
            assert calls == ([0] if scenario == "single" else [0, 2, 0])
        else:
            with pytest.raises(SourceUnavailable):
                await collector.collect()
    finally:
        await http.close()
