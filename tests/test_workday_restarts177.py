"""One clean restart of a changing Workday traversal; no partial rows or stale gaps."""

import asyncio
import json

import httpx
import pytest

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.workday import WorkdayCollector


def row(index):
    return {
        "title": "Trading Analyst",
        "externalPath": f"/job/London/Trading-Analyst_JR{index:06d}",
        "locationsText": "London",
        "bulletFields": [f"JR{index:06d}"],
    }


def execute(monkeypatch, responder, *, initial_gaps=(), source="morgan_stanley"):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        def handler(req):
            if req.url.path == "/robots.txt":
                return httpx.Response(404)
            return responder(json.loads(req.content))

        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        company = Company(
            name="Morgan Stanley",
            ats="workday",
            career_url="https://ms.wd5.myworkdayjobs.com/External",
            options={"verify_listing_snapshot": True},
        )
        collector = WorkdayCollector(source, company, http)
        collector.listing_gaps.update(initial_gaps)
        try:
            rows = await collector._search("trading")
            return rows, collector.listing_gaps
        finally:
            await http.close()

    return asyncio.run(run())


def test_changed_total_restarts_from_zero_and_imports_only_second_snapshot(monkeypatch):
    offsets = []

    def responder(body):
        offset = body["offset"]
        offsets.append(offset)
        if len(offsets) == 1:
            return httpx.Response(
                200, json={"total": 21, "jobPostings": [row(i) for i in range(1, 21)]}
            )
        if len(offsets) == 2:
            return httpx.Response(200, json={"total": 22, "jobPostings": [row(21), row(22)]})
        return httpx.Response(
            200,
            json={
                "total": 22 if offset == 0 else 0,
                "jobPostings": [row(i) for i in (range(1, 21) if offset == 0 else range(21, 23))],
            },
        )

    rows, gaps = execute(monkeypatch, responder)
    assert len(rows) == 22 and not gaps
    assert offsets == [0, 20, 0, 20, 0]


def test_failed_attempt_gaps_are_removed_but_previous_queries_gaps_remain(monkeypatch):
    calls = 0

    def responder(body):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                json={
                    "total": 21,
                    "jobPostings": [
                        {"bulletFields": ["JR000001"]},
                        *[row(i) for i in range(2, 21)],
                    ],
                },
            )
        if calls == 2:
            return httpx.Response(200, json={"total": 22, "jobPostings": [row(21), row(22)]})
        offset = body["offset"]
        return httpx.Response(
            200,
            json={
                "total": 22 if offset == 0 else 0,
                "jobPostings": [row(i) for i in (range(1, 21) if offset == 0 else range(21, 23))],
            },
        )

    rows, gaps = execute(monkeypatch, responder, initial_gaps=["JR999999"])
    assert len(rows) == 22 and gaps == {"JR999999"}


def test_persistently_changing_listing_stops_after_one_restart(monkeypatch):
    offsets = []

    def responder(body):
        offset = body["offset"]
        offsets.append(offset)
        return httpx.Response(
            200,
            json={
                "total": 21 if offset == 0 else 22,
                "jobPostings": [row(i) for i in (range(1, 21) if offset == 0 else range(21, 23))],
            },
        )

    with pytest.raises(SourceUnavailable, match="total changed"):
        execute(monkeypatch, responder)
    assert offsets == [0, 20, 0, 20]


@pytest.mark.parametrize(
    "status,payload",
    [(403, {}), (200, {"total": 1, "jobPostings": [{}]}), (200, {"total": "1", "jobPostings": []})],
)
def test_access_refusals_and_invalid_contracts_are_not_retried(monkeypatch, status, payload):
    calls = []

    def responder(body):
        calls.append(body)
        return httpx.Response(status, json=payload)

    with pytest.raises(SourceUnavailable):
        execute(monkeypatch, responder)
    assert len(calls) == 1


def test_bofa_opaque_reference_preserves_position_and_visible_coverage_gap(monkeypatch):
    rows, gaps = execute(
        monkeypatch,
        lambda body: httpx.Response(
            200, json={"total": 1, "jobPostings": [{"bulletFields": ["26022615"]}]}
        ),
        source="bank_of_america",
    )
    assert rows == {"unavailable:26022615": {"bulletFields": ["26022615"]}}
    assert gaps == {"26022615"}


@pytest.mark.parametrize("source", ["citi", "citi_campus"])
def test_observed_nine_digit_citi_reference_is_a_gap_without_invented_fields(monkeypatch, source):
    rows, gaps = execute(
        monkeypatch,
        lambda body: httpx.Response(
            200, json={"total": 1, "jobPostings": [{"bulletFields": ["261001222"]}]}
        ),
        source=source,
    )
    assert rows == {"unavailable:261001222": {"bulletFields": ["261001222"]}}
    assert gaps == {"261001222"}


@pytest.mark.parametrize("reference", ["2610012", "2610012222", "JR261001222"])
def test_new_citi_length_does_not_accept_other_incomplete_rows(monkeypatch, reference):
    with pytest.raises(SourceUnavailable, match="malformed"):
        execute(
            monkeypatch,
            lambda body: httpx.Response(
                200, json={"total": 1, "jobPostings": [{"bulletFields": [reference]}]}
            ),
            source="citi",
        )


@pytest.mark.parametrize(
    "placeholder",
    [
        {"bulletFields": ["26022615", "other"]},
        {"bulletFields": ["26022615"], "unrecognized": True},
        {"bulletFields": [26022615]},
        {"bulletFields": ["JR036766"]},
    ],
)
def test_bofa_placeholder_extension_does_not_accept_other_missing_fields(monkeypatch, placeholder):
    with pytest.raises(SourceUnavailable, match="malformed"):
        execute(
            monkeypatch,
            lambda body: httpx.Response(200, json={"total": 1, "jobPostings": [placeholder]}),
            source="bank_of_america",
        )
