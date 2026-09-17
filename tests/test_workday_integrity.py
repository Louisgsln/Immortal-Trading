"""A successful Workday collection must contain mutually consistent postings."""

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.workday import WorkdayCollector


@pytest.fixture
def sample():
    root = Path(__file__).parent / "fixtures"
    listing = json.loads((root / "workday_search.json").read_text())["jobPostings"][0]
    detail = json.loads((root / "workday_detail.json").read_text())["jobPostingInfo"]
    return listing, detail


def collect(monkeypatch, listings, details, *, terms=None):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    config = Company(
        name="Demo Bank",
        ats="workday",
        tenant="demo",
        career_url="https://demo.wd3.myworkdayjobs.com/External",
        request_interval=0.1,
        options={"search_terms": terms or ["trading"]},
    )

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            term = json.loads(request.content)["searchText"]
            rows = listings[term] if isinstance(listings, dict) else listings
            return httpx.Response(200, json={"total": len(rows), "jobPostings": rows})
        path = request.url.path.split("/External", 1)[1]
        return httpx.Response(200, json={"jobPostingInfo": details[path]})

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await WorkdayCollector("demo", config, http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", ["private-marker"]),
        ("title", True),
        ("title", " \t "),
        ("title", None),
        ("jobDescription", {"secret": "private-marker"}),
        ("jobDescription", ["private-marker"]),
        ("jobDescription", 42),
        ("jobDescription", " \n "),
        ("id", {"value": "private-marker"}),
        ("id", 42),
        ("id", True),
        ("jobReqId", ["private-marker"]),
        ("location", ["private-marker"]),
        ("location", False),
        ("timeType", {"value": "private-marker"}),
        ("startDate", ["private-marker"]),
        ("additionalLocations", {}),
        ("additionalLocations", False),
        ("additionalLocations", "private-marker"),
        ("additionalLocations", [None]),
        ("additionalLocations", [42]),
        ("additionalLocations", [{"id": "private-marker"}]),
        ("additionalLocations", [{"descriptor": ["private-marker"]}]),
        ("additionalLocations", [{"descriptor": None}]),
    ],
)
def test_malformed_consumed_detail_fields_fail_safely(monkeypatch, sample, field, value):
    listing, detail = sample
    detail[field] = value
    with pytest.raises(SourceUnavailable) as error:
        collect(monkeypatch, [listing], {listing["externalPath"]: detail})
    assert "private-marker" not in str(error.value)


@pytest.mark.parametrize("detail", [None, [], "private-marker", 3])
def test_detail_envelope_requires_object(monkeypatch, sample, detail):
    listing, _ = sample
    with pytest.raises(SourceUnavailable, match="incomplete"):
        collect(monkeypatch, [listing], {listing["externalPath"]: detail})


def test_malformed_listing_location_is_not_silently_ignored(monkeypatch, sample):
    listing, detail = sample
    listing["locationsText"] = {"descriptor": "London"}
    with pytest.raises(SourceUnavailable, match="locationsText"):
        collect(monkeypatch, [listing], {listing["externalPath"]: detail})


@pytest.mark.parametrize("missing", [False, True])
def test_optional_missing_and_null_fields_keep_listing_location(monkeypatch, sample, missing):
    listing, detail = sample
    for field in ("location", "additionalLocations", "timeType", "startDate", "jobReqId"):
        if missing:
            detail.pop(field, None)
        else:
            detail[field] = None
    result = collect(monkeypatch, [listing], {listing["externalPath"]: detail})
    job = result.jobs[0]
    assert job.location == "2 Locations"
    assert job.employment_type is None and job.date_posted is None
    assert job.external_id == "stable-public-posting-id"
    assert not result.complete


def test_missing_all_locations_is_allowed(monkeypatch, sample):
    listing, detail = sample
    listing.pop("locationsText")
    detail.pop("location")
    detail.pop("additionalLocations")
    assert collect(monkeypatch, [listing], {listing["externalPath"]: detail}).jobs[0].location == ""


def test_descriptor_objects_and_strings_are_valid_and_deduplicated(monkeypatch, sample):
    listing, detail = sample
    detail["additionalLocations"] = [
        {"descriptor": "Paris, France", "id": "unrelated-id"},
        "Paris, France",
        "London, United Kingdom",
    ]
    job = collect(monkeypatch, [listing], {listing["externalPath"]: detail}).jobs[0]
    assert job.location == "London, United Kingdom; Paris, France"


@pytest.mark.parametrize("identifier", [None, "", " \t "])
def test_missing_primary_identifier_uses_requisition_without_slug_assumptions(
    monkeypatch, sample, identifier
):
    listing, detail = sample
    detail["id"] = identifier
    detail["jobReqId"] = "not-the-path-suffix"
    assert (
        collect(monkeypatch, [listing], {listing["externalPath"]: detail}).jobs[0].external_id
        == "not-the-path-suffix"
    )


@pytest.mark.parametrize("identifier", [None, "", " \t "])
def test_no_usable_identifier_fails(monkeypatch, sample, identifier):
    listing, detail = sample
    detail["id"] = detail["jobReqId"] = identifier
    with pytest.raises(SourceUnavailable, match="stable identifier"):
        collect(monkeypatch, [listing], {listing["externalPath"]: detail})


@pytest.mark.parametrize(
    "listed,returned",
    [
        ("2027 Sales & Trading Analyst", "2027 Sales &amp; Trading Analyst"),
        ("2027 Sales and Trading Analyst", " 2027\u00a0Sales AND\nTrading Analyst "),
        ("2027 Sales and Trading Analyst", "２０２７ Sales and Trading Analyst"),
        ("Trading Analyst – Équities", "Trading Analyst – E\u0301quities"),
    ],
)
def test_title_presentation_variants_are_accepted(monkeypatch, sample, listed, returned):
    listing, detail = sample
    listing["title"], detail["title"] = listed, returned
    job = collect(monkeypatch, [listing], {listing["externalPath"]: detail}).jobs[0]
    assert job.title == returned  # Preserve the provider's title in the record.


@pytest.mark.parametrize(
    "listed,returned",
    [
        ("Trading Analyst", "Trading Operations Analyst"),
        ("Trading Analyst 東京", "Trading Analyst 北京"),
        ("Trading C++ Analyst", "Trading C# Analyst"),
        ("Trading Analyst (Graduate)", "Trading Analyst Graduate"),
    ],
)
def test_changed_title_is_not_imported_under_stale_listing(monkeypatch, sample, listed, returned):
    listing, detail = sample
    listing["title"], detail["title"] = listed, returned
    with pytest.raises(SourceUnavailable, match="title changed between listing and detail"):
        collect(monkeypatch, [listing], {listing["externalPath"]: detail})


def test_cross_query_presentation_variants_fetch_one_detail(monkeypatch, sample):
    listing, detail = sample
    second = dict(listing, title=" 2027\u00a0Sales AND Trading Analyst ")
    result = collect(
        monkeypatch,
        {"trading": [listing], "trader": [second]},
        {listing["externalPath"]: detail},
        terms=["trading", "trader"],
    )
    assert len(result.jobs) == 1 and result.requests == 4  # robots, two searches, one detail


@pytest.mark.parametrize("conflicting_description", [False, True])
def test_shared_identity_across_distinct_paths_aborts_entire_collection(
    monkeypatch, sample, conflicting_description
):
    listing, detail = sample
    second = dict(listing, externalPath="/job/Paris/Trading-Analyst_R2")
    other_detail = copy.deepcopy(detail)
    if conflicting_description:
        other_detail["jobDescription"] = "A different trading role."
    with pytest.raises(SourceUnavailable, match="identifier repeated across paths"):
        collect(
            monkeypatch,
            [listing, second],
            {listing["externalPath"]: detail, second["externalPath"]: other_detail},
        )


def test_distinct_stable_id_can_share_requisition_id(monkeypatch, sample):
    listing, detail = sample
    second = dict(listing, externalPath="/job/Paris/Trading-Analyst_R2")
    other_detail = dict(detail, id="another-public-posting-id")
    result = collect(
        monkeypatch,
        [listing, second],
        {listing["externalPath"]: detail, second["externalPath"]: other_detail},
    )
    assert [job.external_id for job in result.jobs] == [
        "stable-public-posting-id",
        "another-public-posting-id",
    ]


def test_unrecognized_date_string_remains_unknown(monkeypatch, sample):
    listing, detail = sample
    detail["startDate"] = "unknown"
    assert (
        collect(monkeypatch, [listing], {listing["externalPath"]: detail}).jobs[0].date_posted
        is None
    )
