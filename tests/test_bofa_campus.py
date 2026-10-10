"""Public campus contracts, the real Milan witness and negative alert cases."""

import asyncio
import html
import json
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from trading_radar.bofa_campus import BOARD, BofACampusCollector, parse_detail
from trading_radar.collectors import build_collector
from trading_radar.config import Company, Settings, load_config
from trading_radar.deadlines import deadline_status, resolve_deadline
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.opportunity_facts import duration_facts
from trading_radar.programmes import programme, programme_alertable
from trading_radar.scoring import score_job
from trading_radar.start_dates import start_period

MILAN = json.loads(Path("tests/fixtures/bofa_milan129.json").read_text())
PRIME = json.loads(Path("tests/fixtures/bofa_prime129.json").read_text())


def company(**options):
    return Company(
        name="Bank of America",
        ats="bofa_campus",
        career_url=BOARD,
        request_interval=0.1,
        options=options,
    )


def listing(identifier="15033", title=None, contract=None):
    row = deepcopy(MILAN)
    row["jobRequisitionId"] = identifier
    row["jcrURL"] = row["jcrURL"].replace("15033", identifier)
    row["externalUrl"] = row["externalUrl"].replace("15033", identifier)
    if title:
        row["postingTitle"] = title
    if contract:
        row["timeType"] = row["jobSubFamily"] = contract
    return row


def schema(row):
    return {
        "@type": "JobPosting",
        "identifier": {"name": "Job_Requisition_ID", "value": row["jobRequisitionId"]},
        "hiringOrganization": {"name": "Bank of America"},
        "title": row["postingTitle"],
        "description": row["jobDescriptionExternal"],
        "employmentType": row["timeType"].upper().replace(" ", "_"),
        "datePosted": row["postedDate"],
        "jobLocation": [
            {"address": {"addressLocality": row["city"], "addressCountry": row["country"]}}
        ],
    }


def detail(row, data=None):
    data = schema(row) if data is None else data
    closing = (
        '<span class="posted-date">Apply by ' + html.escape(row["applyByDate"]) + "</span>"
        if row.get("applyByDate")
        else ""
    )
    return (
        '<meta name="job-source" content="campus">'
        '<meta name="job-path" content="' + html.escape(row["jcrURL"]) + '">'
        '<h1 class="job-description-body__title">' + html.escape(row["postingTitle"]) + "</h1>"
        '<script type="application/ld+json">' + json.dumps(data) + "</script>"
        '<a href="' + html.escape(row["externalUrl"]) + '">Apply</a>' + closing
    )


def collect(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector(
                "bank_of_america_campus", company(**options), http
            ).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_milan_real_missions_score_programme_duration_and_calendar_deadline():
    raw = parse_detail(detail(MILAN), MILAN, "bank_of_america_campus", company())
    settings = Settings(include_internships=True, internship_alerts_enabled=True)
    job = score_job(normalize(raw), load_config().keywords, settings=settings)
    assert raw.external_id == "15033" and raw.employment_type == "Off-cycle internship"
    assert raw.publication_day == date(2026, 9, 22) and raw.date_posted is None
    assert raw.application_deadline is None and raw.minimum_experience_years is None
    assert raw.source_url.endswith(MILAN["jcrURL"]) and raw.apply_url == MILAN["externalUrl"]
    assert job.city == "Milan" and job.country == "IT"
    assert job.score_breakdown.total >= 70 and not job.score_breakdown.exclusions
    assert programme(job)["formats"] == ["off_cycle"] and programme(job)["year"] == 2027
    assert programme_alertable(job, settings)
    duration = duration_facts(job)
    assert duration["min_months"] == 3 and duration["max_months"] == 6
    closing = resolve_deadline(job)
    assert closing.precision == "date" and closing.day == date(2026, 10, 11)
    assert deadline_status(closing, datetime(2026, 10, 10, tzinfo=UTC)) == "upcoming"
    assert deadline_status(closing, datetime(2026, 10, 12, tzinfo=UTC)) == "expired"


def test_prime_financing_real_one_year_placement_uses_the_employer_off_cycle_contract():
    raw = parse_detail(detail(PRIME), PRIME, "bank_of_america_campus", company())
    settings = Settings(include_internships=True, internship_alerts_enabled=True)
    job = score_job(normalize(raw), load_config().keywords, settings=settings)
    assert job.external_id == "14762" and job.score_breakdown.total >= 70
    assert "SECURITIES_FINANCE" in job.desk and programme_alertable(job, settings)
    assert programme(job)["year"] == 2027 and not programme(job)["issues"]
    assert programme(job)["formats"] == ["off_cycle", "long"]
    assert duration_facts(job)["min_months"] == duration_facts(job)["max_months"] == 12
    assert start_period(job)["precision"] == "unknown"


@pytest.mark.parametrize("tag,suffix", [("p", " (Full time, off-cycle and IP)"), ("li", "")])
def test_reviewed_conversion_markup_variants_remain_separate_from_intake(tag, suffix):
    from trading_radar.internship_start_evidence import BOFA_CONVERSION

    raw = parse_detail(detail(MILAN), MILAN, "bank_of_america_campus", company())
    raw.description = "<" + tag + ">" + BOFA_CONVERSION + suffix + "</" + tag + ">"
    job = normalize(raw)
    assert start_period(job)["precision"] == "unknown"
    assert programme(job)["year"] == 2027 and not programme(job)["issues"]


@pytest.mark.parametrize(
    "change",
    [
        "employer",
        "source",
        "unofficial",
        "contract",
        "changed_paragraph",
        "actual_start",
        "structured_start",
    ],
)
def test_conditional_conversion_rule_cannot_hide_other_dates_or_employers(change):
    raw = parse_detail(detail(MILAN), MILAN, "bank_of_america_campus", company())
    if change == "employer":
        raw.company = "Another Bank"
    elif change == "source":
        raw.source = "another_campus"
    elif change == "unofficial":
        raw.source_type = "aggregator"
    elif change == "contract":
        raw.employment_type = "Full time"
    elif change == "changed_paragraph":
        raw.description = raw.description.replace("July 2028", "July 2030")
    elif change == "actual_start":
        raw.description += "<p>Internship starts January 2028.</p>"
    else:
        raw.expected_start_date = "2028-01-01"
    assert start_period(normalize(raw))["precision"] == "conflict"


def test_full_catalogue_exclusive_end_pagination_title_audit_and_recheck(monkeypatch):
    rows = [listing(str(15033 + i)) for i in range(51)]
    rows[1]["postingTitle"] = "Global Markets Operations Summer Analyst 2027"
    requests = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        requests.append(str(req.url))
        if req.url.path.endswith("campusjobssearchservlet"):
            start, end = int(req.url.params["start"]), int(req.url.params["rows"])
            assert end == start + 50 and req.url.params["search"] == "getAllJobs"
            return httpx.Response(200, json={"totalMatches": 51, "jobsList": rows[start:end]})
        identifier = req.url.path.split("/")[-2]
        return httpx.Response(
            200, text=detail(next(r for r in rows if r["jobRequisitionId"] == identifier))
        )

    result = collect(handler, monkeypatch, max_details=60)
    assert len(result.jobs) == 50 and not result.complete and result.scope_complete
    assert result.selection.examined == 51 and result.selection.selected == 50
    assert result.selection.rejected == {"excluded_title:operations": 1}
    assert result.requests == 54  # Includes the one robots request, two pages, 50 details, recheck.
    assert "start=50&rows=100" in requests[1]
    assert requests[-1] == requests[0]


@pytest.mark.parametrize(
    "failure",
    [
        "short",
        "changed_total",
        "duplicate",
        "recheck",
        "recheck_count",
        "over_limit",
        "null",
        "bool_count",
    ],
)
def test_incomplete_or_moving_catalogue_is_never_committed(monkeypatch, failure):
    rows = [listing(str(15033 + i), title="Operations Intern") for i in range(51)]
    calls = 0

    def handler(req):
        nonlocal calls
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert req.url.path.endswith("campusjobssearchservlet")
        calls += 1
        start, end = int(req.url.params["start"]), int(req.url.params["rows"])
        page = deepcopy(rows[start:end])
        count = 51
        if failure == "short" and calls == 1:
            page.pop()
        elif failure == "changed_total" and start:
            count = 52
        elif failure == "duplicate" and start:
            page[0] = rows[0]
        elif failure == "recheck" and calls == 3:
            page[0]["postingTitle"] = "Different Operations Intern"
        elif failure == "recheck_count" and calls == 3:
            count = 52
        elif failure == "over_limit":
            count = 501
        elif failure == "null":
            page = None
        elif failure == "bool_count":
            count = True
        return httpx.Response(200, json={"totalMatches": count, "jobsList": page})

    with pytest.raises(SourceUnavailable):
        collect(handler, monkeypatch)


@pytest.mark.parametrize(
    "field,value",
    [
        ("externalUrl", "https://example.org/job"),
        ("jcrURL", "/en-us/students/job-detail/999/wrong"),
        ("jobRequisitionId", "../999"),
        ("timeType", "Event"),
        ("jobSubFamily", "Full time"),
    ],
)
def test_listing_cannot_switch_identity_portal_or_programme(monkeypatch, field, value):
    row = listing()
    row[field] = value

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, json={"totalMatches": 1, "jobsList": [row]})

    with pytest.raises(SourceUnavailable):
        collect(handler, monkeypatch)


@pytest.mark.parametrize(
    "failure",
    [
        "identifier",
        "employer",
        "title",
        "location",
        "contract",
        "description",
        "publication",
        "missing_schema",
        "multiple_schema",
        "campus_events",
        "apply_link",
        "closing",
        "path",
        "heading",
    ],
)
def test_detail_must_confirm_every_published_identity_and_fact(failure):
    row = listing()
    data = schema(row)
    if failure == "identifier":
        data["identifier"]["value"] = "999"
    elif failure == "employer":
        data["hiringOrganization"]["name"] = "Another Bank"
    elif failure == "title":
        data["title"] = "Investment Banking Intern"
    elif failure == "location":
        data["jobLocation"][0]["address"]["addressLocality"] = "Paris"
    elif failure == "contract":
        data["employmentType"] = "SUMMER_INTERNSHIP"
    elif failure == "description":
        data["description"] = "Changed role duties"
    elif failure == "publication":
        data["datePosted"] = "09/23/2026"
    body = detail(row, data)
    if failure == "missing_schema":
        body = body.replace('"JobPosting"', '"Event"')
    elif failure == "multiple_schema":
        body += '<script type="application/ld+json">' + json.dumps(data) + "</script>"
    elif failure == "campus_events":
        body = body.replace('content="campus"', 'content="events"')
    elif failure == "apply_link":
        body = body.replace(row["externalUrl"], "https://example.org/apply")
    elif failure == "closing":
        body = body.replace("Apply by Oct 11, 2026", "Apply by Oct 12, 2026")
    elif failure == "path":
        body = body.replace(row["jcrURL"], row["jcrURL"].replace("15033", "999"))
    elif failure == "heading":
        body = body.replace("</h1>", " Changed</h1>")
    with pytest.raises(SourceUnavailable):
        parse_detail(body, row, "bank_of_america_campus", company())


@pytest.mark.parametrize(
    "title,contract",
    [
        ("Global Markets Sales and Trading Summer Analyst 2027", "Summer internship"),
        ("Global Markets Sales and Trading Off-Cycle Analyst 2026", "Off-cycle internship"),
        ("Global Markets Off-Cycle Associate 2027", "Off-cycle internship"),
    ],
)
def test_summer_wrong_intake_and_associate_do_not_become_alerts(title, contract):
    row = listing(title=title, contract=contract)
    raw = parse_detail(detail(row), row, "bank_of_america_campus", company())
    settings = Settings(include_internships=True, internship_alerts_enabled=True)
    job = score_job(normalize(raw), load_config().keywords, settings=settings)
    assert job.score_breakdown.total < 70 or not programme_alertable(job, settings)


@pytest.mark.parametrize(
    "url",
    [
        "https://campus.bankofamerica.com",
        "https://bankcampuscareers.tal.net/candidate/jobboard/vacancy/2/adv/",
        "https://ghr.wd1.myworkdayjobs.com/lateral-us",
    ],
)
def test_only_the_actual_public_student_catalogue_can_be_configured(url):
    co = company().model_copy(update={"career_url": url})
    with pytest.raises(ValueError):
        BofACampusCollector("bank_of_america_campus", co, None)


def test_limits_and_http_restrictions_fail_without_empty_success(monkeypatch):
    def handler(req):
        return httpx.Response(404 if req.url.path == "/robots.txt" else 403)

    with pytest.raises(SourceUnavailable, match="403"):
        collect(handler, monkeypatch)

    def too_many(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200, json={"totalMatches": 2, "jobsList": [listing(), listing("15034")]}
        )

    with pytest.raises(SourceUnavailable, match="detail limit"):
        collect(too_many, monkeypatch, max_details=1)
