"""ENGIE layout changes and a lighter, still fail-closed Nomura campus scan."""

import asyncio
from datetime import date

import httpx
import pytest

from tests.test_energy_collectors import company, engie_detail, engie_url, sitemap
from tests.test_nomura import board, card, detail
from trading_radar.config import load_config
from trading_radar.engie import EngieCollector, SnapshotChanged, parse_detail
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.nomura import NomuraCollector


def compact_detail():
    text = engie_detail()
    for value in [
        "Business Unit: Supply & Energy Management",
        "Division: Trading",
        "Legal Entity: ENGIE Global Markets",
    ]:
        text = text.replace('<div class="joblayouttoken">' + value + "</div>", "")
    return text


def test_engie_optional_organisation_fields_preserve_the_actual_job():
    before = parse_detail(engie_detail(), engie_url(), company("engie"), "engie")
    after = parse_detail(compact_detail(), engie_url(), company("engie"), "engie")
    assert before == after
    assert after.publication_day == date(2026, 9, 21)
    assert after.raw_payload["legal_entity"] == "ENGIE Global Markets"


@pytest.mark.parametrize(
    "old,new",
    [
        ("Requisition ID: 123", "Requisition ID: 456"),
        ("/apply/123/", "/apply/456/"),
        ("Company Name:", "Unknown Field:"),
        ("Minimum Base Salary:", "Company Name:"),
        ('<div class="joblayouttoken"></div>', ""),
        ('lang="en-US"', 'lang="de-DE"'),
    ],
)
def test_compact_engie_layout_still_rejects_shifted_fields_or_wrong_identity(old, new):
    with pytest.raises(SourceUnavailable):
        parse_detail(compact_detail().replace(old, new), engie_url(), company("engie"), "engie")


@pytest.mark.parametrize("kind", ["unrelated", "settles", "keeps_changing", "wrong_identity"])
def test_engie_rechecks_target_scope_and_retries_only_a_changed_snapshot(monkeypatch, kind):
    listings = 0
    details = 0

    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    def handler(req):
        nonlocal listings, details
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/sitemap.xml":
            listings += 1
            changed = (
                listings > 1 and kind == "settles" or listings % 2 == 0 and kind == "keeps_changing"
            )
            urls = [engie_url("456-en_US" if changed else "123-en_US")]
            if kind == "unrelated" and listings > 1:
                urls.append(engie_url("999-en_US").replace("Energy-Trader", "Accountant"))
            return httpx.Response(200, text=sitemap(urls))
        details += 1
        ident = "456" if "456-en_US" in req.url.path else "123"
        text = engie_detail(ident=ident)
        if kind == "wrong_identity":
            text = text.replace("Requisition ID: " + ident, "Requisition ID: 999")
        return httpx.Response(200, text=text)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            collector = EngieCollector("engie", company("engie"), http)
            if kind in {"keeps_changing", "wrong_identity"}:
                with pytest.raises(
                    SnapshotChanged if kind == "keeps_changing" else SourceUnavailable
                ):
                    await collector.collect()
            else:
                result = await collector.collect()
                assert not result.complete and len(result.jobs) == 1
                assert result.jobs[0].external_id == ("456" if kind == "settles" else "123")
                assert result.requests == 1 + listings + details
        finally:
            await http.close()

    asyncio.run(run())
    assert listings == (
        4 if kind in {"settles", "keeps_changing"} else 1 if kind == "wrong_identity" else 2
    )


def test_nomura_skips_explicit_internships_before_details_but_keeps_graduates(monkeypatch):
    monkeypatch.delenv("NOMURA_SESSION_FILE", raising=False)
    config = load_config().companies["nomura_campus"]
    assert config.scan_interval == 1800
    calls = []

    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    def handler(req):
        calls.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "jobboard" in req.url.path:
            return httpx.Response(
                200,
                text=board(
                    [
                        card(123),
                        card(124, "2027 Global Markets Graduate Internship Program"),
                        card(125, "2027 Global Markets Summer Analyst"),
                        card(126, "2027 Global Markets - Industrial Placement"),
                        card(127, "2027 Global Markets - Insight Programme"),
                    ]
                ),
            )
        assert "/123-" in req.url.path
        return httpx.Response(200, text=detail())

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            result = await NomuraCollector("nomura_campus", config, http).collect()
            assert len(result.jobs) == 1 and not result.complete
            assert result.jobs[0].title == "2027 Global Markets Graduate"
        finally:
            await http.close()

    asyncio.run(run())
    assert len(calls) == 3
