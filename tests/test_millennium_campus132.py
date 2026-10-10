import asyncio
import copy
import html
import json
from pathlib import Path

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.millennium_campus import BOARD, job_url, parse_detail, parse_page, position
from trading_radar.normalizer import normalize
from trading_radar.programmes import programme, programme_alertable


def fixture():
    return json.loads(Path("tests/fixtures/millennium-campus132.json").read_text())


def company():
    return Company(name="Millennium", ats="millennium_campus", career_url=BOARD)


def detail_html(data):
    return (
        '<code id="smartApplyData">'
        + html.escape(json.dumps(data["detail"]))
        + '</code><script type="application/ld+json">'
        + json.dumps(data["schema"])
        + "</script>"
    )


def test_real_off_cycle_is_detected_without_turning_2026_into_2027(config):
    data = fixture()
    raw = parse_detail(
        detail_html(data), position(data["listing"]["positions"][0]), company(), "millennium_campus"
    )
    assert raw.external_id == "755956742250"
    assert raw.date_posted is None and raw.application_deadline is None
    assert "3 to 6 months starting in August 2026" in raw.description
    assert "candidate" not in raw.raw_payload
    job = normalize(raw)
    config.settings.include_internships = config.settings.internship_alerts_enabled = True
    assert programme(job)["year"] == 2026
    assert "off_cycle" in programme(job)["formats"]
    assert not programme_alertable(job, config.settings)


@pytest.mark.parametrize(
    "changes",
    [
        {"isPrivate": True},
        {"id": True},
        {"type": "EVENT"},
        {"canonicalPositionUrl": "https://evil.test/job/755956742250"},
        {"posting_name": "Different"},
    ],
)
def test_rejects_private_events_foreign_links_and_title_conflicts(changes):
    row = fixture()["listing"]["positions"][0] | changes
    with pytest.raises(SourceUnavailable):
        position(row)


@pytest.mark.parametrize(
    "area,key,value",
    [
        ("detail", "domain", "other.com"),
        ("detail", "isUserAuthenticated", True),
        ("detail", "isFallback", True),
        ("detail", "pid", "1"),
        ("schema", "title", "Different"),
        ("schema", "hiringOrganization", {"name": "Other"}),
        ("schema", "description", ""),
    ],
)
def test_detail_requires_anonymous_identity_and_full_employer_description(area, key, value):
    data = fixture()
    row = position(data["listing"]["positions"][0])
    data[area][key] = value
    with pytest.raises(SourceUnavailable):
        parse_detail(detail_html(data), row, company(), "millennium_campus")


def test_catalogue_pagination_recheck_and_campus_scope(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    data = fixture()
    real = data["listing"]["positions"][0]
    others = []
    for i in range(10):
        row = copy.deepcopy(real)
        row.update(
            id=i + 1,
            name="Accountant",
            posting_name="Accountant",
            ats_job_id=f"REQ-{i + 1}",
            canonicalPositionUrl=f"https://mlp.eightfold.ai/careers/job/{i + 1}",
        )
        others.append(row)
    rows = [real, *others]
    offsets = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert req.url.params["domain"] == "mlp.com"
        assert req.url.params["microsite"] == "campus-site"
        if req.url.path.endswith("/jobs"):
            offset = int(req.url.params["start"])
            offsets.append(offset)
            return httpx.Response(
                200, json=data["listing"] | {"positions": rows[offset : offset + 10], "count": 11}
            )
        return httpx.Response(200, text=detail_html(data))

    async def run():
        h = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("millennium_campus", company(), h).collect()
        finally:
            await h.close()

    result = asyncio.run(run())
    assert offsets == [0, 10, 0]
    assert result.scope_complete and not result.complete
    assert [j.external_id for j in result.jobs] == [str(real["id"])]


@pytest.mark.parametrize(
    "changes",
    [
        {"count": 38},
        {"count": True},
        {"domain": "other.com"},
        {"isUserAuthenticated": True},
        {"query": {"query": "other", "location": ""}},
    ],
)
def test_short_or_changed_search_is_not_a_success(changes):
    data = fixture()["listing"] | changes
    with pytest.raises(SourceUnavailable):
        parse_page(data, "trading", 30, 100)


@pytest.mark.parametrize(
    "url",
    [
        "https://campusjobs.mlp.com/careers/job/1?domain=other.com",
        "https://campusjobs.mlp.com/careers/job/1?domain=mlp.com&microsite=private",
        "https://campusjobs.mlp.com/careers/job/1#apply",
        "https://mlp.eightfold.ai/careers/job/2",
    ],
)
def test_job_url_identity_is_not_redirect_or_login_permission(url):
    with pytest.raises(SourceUnavailable):
        job_url(url, "1")
