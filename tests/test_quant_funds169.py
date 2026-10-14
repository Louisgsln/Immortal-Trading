"""Verified fund identities, published facts and the VPS all-score QRT scope."""

import asyncio
from copy import deepcopy

import httpx
import pytest

from tests.test_greenhouse_filtered import payload, row
from tests.test_source_expansion166 import profile
from trading_radar.collectors import build_collector
from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import API, GreenhouseOptions, parse_board
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.programmes import programme_company
from trading_radar.scoring import score_job
from trading_radar.selection import rejection_reason

BOARDS = ["xantium", "bluecrest", "dymon_asia"]


def posting(key, **changes):
    return row(profile(key).tenant, metadata=None, **changes)


def parse(key, item):
    c = profile(key)
    return parse_board(payload([item]), key, c, GreenhouseOptions(**c.options))


@pytest.mark.parametrize("key", BOARDS)
def test_audited_null_metadata_preserves_full_description_without_invented_contract(key):
    item = posting(key)
    raw = parse(key, item)[0]
    assert raw.description == item["content"] and raw.location == "London"
    assert raw.employment_type is None and raw.seniority_hint is None
    assert raw.expected_start_date is None and raw.application_deadline is None
    assert raw.date_posted.isoformat() == "2026-09-01T13:00:00+00:00"
    assert raw.apply_url == item["absolute_url"]


@pytest.mark.parametrize("key", BOARDS)
@pytest.mark.parametrize("change", ["employer", "host", "identifier", "metadata", "content"])
def test_a_changed_board_identity_or_incomplete_description_fails_closed(key, change):
    item = posting(key)
    if change == "employer":
        item["company_name"] = "Another employer"
    elif change == "host":
        item["absolute_url"] = item["absolute_url"].replace("greenhouse.io", "evil.example")
    elif change == "identifier":
        item["id"] += 1
    elif change == "metadata":
        item.pop("metadata")
    else:
        item["content"] = ""
    with pytest.raises(SourceUnavailable):
        parse(key, item)


@pytest.mark.parametrize("key", BOARDS)
def test_public_api_including_anz_uses_complete_feed_but_does_not_close_by_absence(
    key, monkeypatch
):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    c = profile(key)

    def handler(req):
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        assert str(req.url) == API + c.tenant + "/jobs?content=true"
        return httpx.Response(200, json=payload([posting(key)]))

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector(key, c, http).collect()
        finally:
            await http.close()

    result = asyncio.run(run())
    assert len(result.jobs) == 1 and result.scope_complete and not result.complete
    assert result.selection.examined == result.selection.selected == 1


@pytest.mark.parametrize("key", [*BOARDS, "cfm", "qube_research"])
@pytest.mark.parametrize(
    "title", ["Senior Quantitative Trader", "Quantitative Developer Intern 2027"]
)
def test_vps_quantitative_and_senior_roles_are_collected_then_scored(key, title):
    c = profile(key)
    settings = load_config().settings.model_copy(update={"include_internships": True})
    c = programme_company(c, settings)
    assert rejection_reason(title, GreenhouseOptions(**c.options)) is None


@pytest.mark.parametrize("key", [*BOARDS, "cfm", "qube_research"])
@pytest.mark.parametrize(
    "title",
    ["Quant Research Summer Intern", "Trading Operations Analyst", "Quant Infrastructure Engineer"],
)
def test_summer_and_support_scope_remains_excluded(key, title):
    assert rejection_reason(title, GreenhouseOptions(**profile(key).options)) is not None


def test_qrt_2027_development_stage_was_filtered_and_is_now_included_without_date_invention():
    title = "2027 - Internship, Software Engineering and Quantitative Development"
    settings = load_config().settings.model_copy(
        update={"include_internships": True, "telegram_all_new_jobs": True}
    )
    old = programme_company(deepcopy(load_config().companies["qube_research"]), settings)
    new = programme_company(profile("qube_research"), settings)
    assert rejection_reason(title, GreenhouseOptions(**old.options)) is not None
    item = row(
        new.tenant,
        title=title,
        metadata=[{"name": "Employment Type", "value": None}],
        content="<p>Four to six month internship starting in 2027. Research systematic trading.</p>",
    )
    raw = parse_board(payload([item]), "qube_research", new, GreenhouseOptions(**new.options))[0]
    assert raw.expected_start_date is None and raw.employment_type is None
    assert raw.minimum_experience_years is None
    assert "Four to six month" in raw.description
    scored = score_job(normalize(raw), load_config().keywords, settings=settings)
    assert scored.title == title


def test_sources_admit_actual_fellowship_and_front_office_titles():
    for key, title in [
        ("xantium", "Xantium Academy Fellow"),
        ("bluecrest", "Front Office Developer"),
        ("dymon_asia", "2027 AI Equity Long/Short (ELS) Fellowship Programme"),
        ("dymon_asia", "AI Research Intern"),
        ("cfm", "Portfolio Engineering - Internship"),
        ("cfm", "Financial Engineering - Stage"),
    ]:
        assert rejection_reason(title, GreenhouseOptions(**profile(key).options)) is None
