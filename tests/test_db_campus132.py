import asyncio
import json
from pathlib import Path

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.db_campus import BOARD, catalogue, detail, position
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.programmes import programme, programme_alertable


def fixture():
    return json.loads(Path("tests/fixtures/db-campus132.json").read_text())


def company():
    return Company(
        name="Deutsche Bank", ats="db_campus", career_url=BOARD, options={"search_terms": []}
    )


def payload():
    return {
        "LanguageCode": "EN",
        "SearchResult": {
            "SearchResultCount": 1,
            "SearchResultCountAll": 1,
            "SearchResultItems": [fixture()["listing"]],
        },
    }


def test_real_long_internship_keeps_conversion_and_actual_2027_intake_separate(config):
    data = fixture()
    row = position(data["listing"])
    raw = detail(data["detail"], row, "deutsche_bank_campus", company())
    job = normalize(raw)
    original = job.description
    observed = programme(job)
    config.settings.include_internships = config.settings.internship_alerts_enabled = True
    assert observed["year"] == 2027 and observed["year_status"] == "confirmed"
    assert "long" in observed["formats"]
    assert programme_alertable(job, config.settings)
    assert "July 2028" in job.description and job.description == original
    assert raw.date_posted is None and raw.application_deadline is None
    assert raw.external_id == "75467"
    assert raw.raw_payload["published_hiring_year"] == "2027"


def test_unreviewed_conversion_year_keeps_conflict_visible():
    data = fixture()
    data["detail"]["html"] = data["detail"]["html"].replace("July 2028", "July 2029")
    job = normalize(
        detail(data["detail"], position(data["listing"]), "deutsche_bank_campus", company())
    )
    assert programme(job)["year_status"] == "conflict"


def test_presentation_whitespace_does_not_change_job_identity():
    data = fixture()
    data["listing"]["MatchedObjectDescriptor"]["PositionTitle"] = data["listing"][
        "MatchedObjectDescriptor"
    ]["PositionTitle"].replace(" - Investment", " -  Investment")
    row = position(data["listing"])
    assert (
        detail(data["detail"], row, "deutsche_bank_campus", company()).title
        == fixture()["listing"]["MatchedObjectDescriptor"]["PositionTitle"]
    )


@pytest.mark.parametrize("key,value", [("MatchedObjectId", "1"), ("MatchedObjectId", True)])
def test_listing_identifier_must_match_descriptor(key, value):
    with pytest.raises(SourceUnavailable):
        position(fixture()["listing"] | {key: value})


@pytest.mark.parametrize(
    "key,value",
    [
        ("PositionURI", "https://evil.test/requisition/1"),
        ("ApplyURI", []),
        ("PositionLocation", []),
        ("CareerLevel", []),
        ("PositionHiringYear", "maybe2027"),
    ],
)
def test_listing_identity_and_student_metadata_are_required(key, value):
    data = fixture()["listing"]
    data["MatchedObjectDescriptor"][key] = value
    with pytest.raises(SourceUnavailable):
        position(data)


@pytest.mark.parametrize(
    "key,value",
    [("SearchResultCountAll", 2), ("SearchResultCount", True), ("SearchResultItems", [])],
)
def test_truncated_catalogue_is_not_complete(key, value):
    data = payload()
    data["SearchResult"][key] = value
    with pytest.raises(SourceUnavailable):
        catalogue(data, 100)


@pytest.mark.parametrize("change", ["apply", "title", "empty"])
def test_detail_must_match_title_and_application(change):
    data = fixture()
    if change == "apply":
        data["detail"]["apply_uri"] = "https://evil.test/"
    elif change == "title":
        data["detail"]["html"] = data["detail"]["html"].replace(
            data["listing"]["MatchedObjectDescriptor"]["PositionTitle"], "Other"
        )
    else:
        data["detail"]["html"] = "<div id='db-jobad'><h1>Short</h1></div>"
    with pytest.raises(SourceUnavailable):
        detail(data["detail"], position(data["listing"]), "deutsche_bank_campus", company())


@pytest.mark.parametrize("changed", [False, True])
def test_full_catalogue_is_rechecked_and_no_application_is_submitted(monkeypatch, changed):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    requests = []

    def handler(req):
        assert req.method == "GET"
        requests.append(req.url.path)
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "graduatesearch" in req.url.path:
            query = json.loads(req.url.params["data"])
            assert query["LanguageCode"] == "EN" and query["SearchParameters"]["FirstItem"] == 1
            data = payload()
            if changed and requests.count(req.url.path) > 1:
                data["SearchResult"]["SearchResultCountAll"] = 2
            return httpx.Response(200, json=data)
        return httpx.Response(200, json=fixture()["detail"])

    async def run():
        h = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("deutsche_bank_campus", company(), h).collect()
        finally:
            await h.close()

    if changed:
        with pytest.raises(SourceUnavailable):
            asyncio.run(run())
    else:
        result = asyncio.run(run())
        assert result.scope_complete and not result.complete and len(result.jobs) == 1
