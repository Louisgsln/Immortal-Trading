import asyncio
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
import yaml

from trading_radar.config import Company
from trading_radar.deshaw import BOARD, DeshawCollector, DeshawOptions, listing, raw
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import rejection_reason
from trading_radar.workday import WorkdayOptions, workday_base


def profile(key):
    return Company(
        **yaml.safe_load(Path("config/vps-companies.yaml").read_text())["companies"][key]
    )


def data():
    return dict(
        id=1,
        displayName="Quantitative Analyst – Off-Cycle Intern 2027",
        jobUrl="Quantitative-Analyst-Off-Cycle-Intern-2027-1",
        activeOnJobsListing=True,
        shouldHideJobForAdditionalInfoRequests=False,
        jobMetadata=dict(
            isExploratory=False, workStatus="Intern", jobLocations=[dict(name="London")]
        ),
        jobDescription=dict(
            websiteDescription="Six-month off-cycle internship. Start date: 1 September 2027.",
            responsibilitiesHtml="<p>Research systematic trading strategies.</p>",
            peopleWeAreLookingFor=["Previous quantitative research experience preferred."],
        ),
    )


def page(props):
    return (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(dict(props=dict(pageProps=props)))
        + "</script>"
    )


def catalogue(item=None):
    item = item or data()
    return dict(
        jobsFetchingError=False,
        regularJobs=[dict(id=item["id"], displayName=item["displayName"], data=item)],
        internships=[],
        internalJobs=[dict(private="never consumed")],
    )


def collect(monkeypatch, *, detail=None, second=None, first=None, options=None):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    calls = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls.append(str(request.url))
        if str(request.url) == BOARD:
            props = second if len(calls) > 1 and second is not None else first or catalogue()
        else:
            props = dict(jobData=detail or data())
        return httpx.Response(200, text=page(props))

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            config = profile("deshaw")
            if options:
                config.options.update(options)
            return await DeshawCollector("deshaw", config, http).collect()
        finally:
            await http.close()

    return asyncio.run(run()), calls


def test_full_description_dates_and_metadata_are_preserved_without_render_date(monkeypatch):
    item = data() | dict(datePosted="Wed Oct 14 2026 14:41:07 GMT+0000", validToDate="2027-01-01")
    result, calls = collect(monkeypatch, detail=item)
    job = result.jobs[0]
    assert job.source_type == "official" and result.scope_complete and not result.complete
    assert job.location == "London" and job.employment_type == "Intern"
    assert "Previous quantitative research experience preferred." in job.description
    assert "Start date: 1 September 2027." in job.description
    assert job.date_posted is None and job.application_deadline is None
    assert job.minimum_experience_years is None
    assert calls == [BOARD, job.apply_url, BOARD]
    assert result.selection.selected == 1


@pytest.mark.parametrize("change", ["title", "description", "location", "id", "hidden", "prospect"])
def test_detail_changes_fail_closed(monkeypatch, change):
    item = data()
    if change == "title":
        item["displayName"] = "Other Trader"
    elif change == "description":
        item["jobDescription"]["responsibilitiesHtml"] = "<p>Other responsibilities.</p>"
    elif change == "location":
        item["jobMetadata"]["jobLocations"][0]["name"] = "Paris"
    elif change == "id":
        item["id"] = 2
    elif change == "hidden":
        item["activeOnJobsListing"] = False
    else:
        item["jobMetadata"]["isExploratory"] = True
    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, detail=item)


@pytest.mark.parametrize("change", ["duplicate", "identity", "total", "error", "missing", "url"])
def test_catalogue_integrity(monkeypatch, change):
    props = catalogue()
    if change == "duplicate":
        props["internships"] = deepcopy(props["regularJobs"])
    elif change == "identity":
        props["regularJobs"][0]["id"] = 2
    elif change == "total":
        props["regularJobs"] = []
    elif change == "error":
        props["jobsFetchingError"] = True
    elif change == "missing":
        del props["internships"]
    else:
        props["regularJobs"][0]["data"]["jobUrl"] = "https://example.com/1"
    with pytest.raises(SourceUnavailable):
        listing(page(props), 1000)


def test_catalogue_changed_during_fetch_is_not_a_success(monkeypatch):
    props = catalogue()
    props["regularJobs"][0]["data"]["jobMetadata"]["jobLocations"][0]["name"] = "Paris"
    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, second=props)


@pytest.mark.parametrize("flag", ["hidden", "prospect"])
def test_nonpublic_and_exploratory_rows_are_counted_without_import(monkeypatch, flag):
    item = data()
    if flag == "hidden":
        item["shouldHideJobForAdditionalInfoRequests"] = True
    else:
        item["jobMetadata"]["isExploratory"] = True
    result, calls = collect(monkeypatch, first=catalogue(item))
    assert not result.jobs and calls == [BOARD, BOARD]
    assert result.selection.examined == 1 and not result.selection.samples


@pytest.mark.parametrize(
    "field", ["websiteDescription", "responsibilitiesHtml", "peopleWeAreLookingFor"]
)
def test_missing_full_posting_section_is_not_a_vacancy(field):
    item = data()
    item["jobDescription"][field] = None
    with pytest.raises(SourceUnavailable):
        raw(item, "deshaw")


@pytest.mark.parametrize(
    "key", ["t_rowe_price", "aberdeen", "invesco", "trafigura", "deshaw", "scotiabank"]
)
def test_new_sources_admit_long_internships_and_senior_all_score_roles(key):
    p = profile(key)
    cls = (
        DeshawOptions
        if key == "deshaw"
        else SearchOptions
        if key == "scotiabank"
        else WorkdayOptions
    )
    options = cls(**p.options)
    assert p.enabled and p.scan_interval == 1800
    assert rejection_reason("Quantitative Analyst – Off-Cycle Intern 2027", options) is None
    assert rejection_reason("Senior Trader", options) is None
    assert rejection_reason("Trading Operations Analyst", options) is not None
    assert rejection_reason("Summer Internship - Trading", options) is not None
    if key not in {"deshaw", "scotiabank"}:
        assert workday_base(p)[0] == p.career_url
        assert p.options["verify_listing_snapshot"] and p.options["conditional_details"]
