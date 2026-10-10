"""Actual Fixed Income off-cycle and strict public Oleeo contracts."""

import asyncio
import html
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company, Settings, load_config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.jefferies_campus import (
    BOARD,
    ORIGIN,
    PREFIX,
    ROUTE,
    canonical_detail,
    parse_detail,
)
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.programmes import programme, programme_alertable
from trading_radar.scoring import score_job
from trading_radar.start_dates import start_period
from trading_radar.targeting import jefferies_sales_trading_duties

WITNESS = json.loads(Path("tests/fixtures/jefferies_dubai130.json").read_text())


def company(**options):
    return Company(
        name="Jefferies",
        ats="jefferies_campus",
        career_url=BOARD,
        request_interval=0.1,
        options={"title_terms": ["fixed income", "quant", "trading"], **options},
    )


def row(identifier="2002", title=None):
    return {
        "id": identifier,
        "title": title or WITNESS["title"],
        "url": WITNESS["url"].replace("2002", identifier),
    }


def board(rows, total=None, next_page=None):
    cards = "".join(
        '<div class="candidate-opp-tile" data-oppid="'
        + r["id"]
        + '" data-title="'
        + html.escape(r["title"])
        + '"><a class="subject" href="'
        + r["url"].replace(PREFIX, PREFIX + "xf-abcdef123456/")
        + '">'
        + html.escape(r["title"])
        + "</a></div>"
        for r in rows
    )
    return (
        '<h1 class="job-board-title">Campus Opportunities</h1><h2 role="alert">'
        + str(len(rows) if total is None else total)
        + " results match!</h2>"
        + cards
        + ('<a href="?start=' + str(next_page) + '">Next page</a>' if next_page else "")
    )


def detail(r, changes=None):
    fields = {**WITNESS["fields"], "Opportunity ID": r["id"], **(changes or {})}
    body = '<h1 class="section">' + html.escape(r["title"]) + "</h1>"
    body += "".join(
        '<div class="form-group"><span class="hform_lbl_text">'
        + html.escape(k)
        + '</span><div class="form-control-static">'
        + v
        + "</div></div>"
        for k, v in fields.items()
    )
    return body + '<form action="' + ORIGIN + PREFIX + ROUTE + r["id"] + '/apply/en-GB"></form>'


def collect(monkeypatch, handler, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("jefferies_campus", company(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_dubai_real_missions_department_and_alternative_months():
    r = row()
    raw = parse_detail(detail(r), r, company(), "jefferies_campus")
    settings = Settings(include_internships=True, internship_alerts_enabled=True)
    job = score_job(normalize(raw), load_config().keywords, settings=settings)
    assert job.score_breakdown.total >= 70 and not job.score_breakdown.exclusions
    assert job.desk == ["SALES_TRADING"] and job.score_breakdown.front_office == 15
    assert job.score_breakdown.asset == 0  # Firm-wide equity financing prose is not role evidence.
    assert programme(job)["year"] == 2027 and programme(job)["formats"] == ["off_cycle"]
    assert programme_alertable(job, settings)
    assert start_period(job)["months"] == [1, 2]
    assert job.application_deadline is None and job.date_posted is None
    assert "xf-" not in job.apply_url and "full range" in job.description
    assert "market commentary" in jefferies_sales_trading_duties(job)


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "employer",
        "unofficial",
        "other_title",
        "department",
        "missing_duty",
        "duplicate_duties",
        "qualifications_only",
        "summer",
    ],
)
def test_a_bank_label_or_its_boilerplate_never_qualifies_the_role(change):
    r = row()
    raw = parse_detail(detail(r), r, company(), "jefferies_campus")
    if change == "source":
        raw.source = "another_campus"
    elif change == "employer":
        raw.company = "Another Bank"
    elif change == "unofficial":
        raw.source_type = "aggregator"
    elif change == "other_title":
        raw.title = "Investment Banking Internship 2027"
    elif change == "department":
        raw.description = raw.description.replace(
            "Business unit(s):</strong> Sales and Trading",
            "Business unit(s):</strong> Investment Banking",
        )
    elif change == "missing_duty":
        raw.description = raw.description.replace("trade ideas", "accounting reports")
    elif change == "duplicate_duties":
        raw.description += raw.description
    elif change == "qualifications_only":
        raw.description = raw.description.replace(
            "Your time here will look something like this", "Required Skills"
        )
    else:
        raw.employment_type = "Summer Internship"
    assert not jefferies_sales_trading_duties(normalize(raw))


def test_entire_board_is_paged_and_rechecked_without_context_or_form_submission(monkeypatch):
    rows = [row(str(2002 + i)) for i in range(51)]
    rows[1]["title"] = "2027 Risk Management Placement"
    seen = []

    def handler(req):
        assert req.method == "GET" and "xf-" not in str(req.url)
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        seen.append(str(req.url))
        if "jobboard" in req.url.path:
            start = int(req.url.params.get("start", 0))
            return httpx.Response(
                200, text=board(rows[start : start + 50], 51, 50 if not start else None)
            )
        identifier = req.url.path.split("/opp/")[1].split("-")[0]
        return httpx.Response(200, text=detail(next(r for r in rows if r["id"] == identifier)))

    result = collect(monkeypatch, handler, max_details=60)
    assert len(result.jobs) == 50 and result.scope_complete and not result.complete
    assert result.selection.examined == 51 and result.selection.selected == 50
    assert seen[-1] == seen[0] == BOARD and seen[1] == BOARD + "?start=50"


@pytest.mark.parametrize(
    "bad",
    ["events", "short", "duplicate", "next_host", "next_offset", "recheck", "total", "captcha"],
)
def test_wrong_or_incomplete_board_cannot_be_imported(monkeypatch, bad):
    rows = [row(str(2002 + i), title="2027 Operations Internship") for i in range(51)]
    calls = 0

    def handler(req):
        nonlocal calls
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        calls += 1
        start = int(req.url.params.get("start", 0))
        page = deepcopy(rows[start : start + 50])
        count = 51
        if bad == "short" and not start:
            page.pop()
        if bad == "duplicate" and start:
            page[0] = rows[0]
        if bad == "recheck" and calls == 3:
            page[0]["title"] = "2027 Different Operations Internship"
        if bad == "total" and start:
            count = 52
        text = board(page, count, 50 if not start else None)
        if bad == "events":
            text = text.replace("Campus Opportunities", "Events")
        if bad == "next_host":
            text = text.replace("?start=50", "https://example.org/?start=50")
        if bad == "next_offset":
            text = text.replace("?start=50", "?start=51")
        if bad == "captcha":
            text = '<form id="captcha-form"><altcha-widget></altcha-widget></form>'
        return httpx.Response(200, text=text)

    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, handler)


@pytest.mark.parametrize(
    "bad",
    [
        "title",
        "identity",
        "contract",
        "missing_description",
        "duplicate_field",
        "apply_identity",
        "apply_host",
    ],
)
def test_unverified_detail_is_rejected(bad):
    r = row()
    body = detail(r)
    if bad == "title":
        body = body.replace("</h1>", " Different</h1>")
    elif bad == "identity":
        body = detail(r, {"Opportunity ID": "999"})
    elif bad == "contract":
        body = detail(r, {"Program type": "Event"})
    elif bad == "missing_description":
        body = body.replace("Job description", "Unrecognized description")
    elif bad == "duplicate_field":
        body += '<div class="form-group"><span class="hform_lbl_text">Location</span><div class="form-control-static">Paris</div></div>'
    elif bad == "apply_identity":
        body = body.replace("/opp/2002/apply/", "/opp/999/apply/")
    else:
        body = body.replace(ORIGIN, "https://example.org")
    with pytest.raises(SourceUnavailable):
        parse_detail(body, r, company(), "jefferies_campus")


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/job",
        ORIGIN + PREFIX + ROUTE + "999-wrong/en-GB",
        ORIGIN + PREFIX + ROUTE.replace("pl/2", "pl/1") + "2002-event/en-GB",
        WITNESS["url"] + "?login=true",
    ],
)
def test_application_links_cannot_switch_host_board_or_identity(url):
    with pytest.raises(SourceUnavailable):
        canonical_detail(url, "2002")


@pytest.mark.parametrize(
    "statement,months",
    [
        ("January/May 2027", [1, 5]),
        ("November or February 2027", [2, 11]),
        ("January to April 2027", [1, 2, 3, 4]),
    ],
)
def test_alternative_start_months_are_not_a_continuous_range(statement, months):
    raw = RawJob(
        company="Demo",
        source="test",
        title="Off-Cycle Internship 2027",
        apply_url="https://example.org",
        expected_start_date=statement,
    )
    assert start_period(normalize(raw))["months"] == months
