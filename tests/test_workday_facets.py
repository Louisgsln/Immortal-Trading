import asyncio
import copy
import json
from collections import defaultdict

import httpx
import pytest

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.workday import WorkdayCollector, WorkdayOptions


def company(**options):
    return Company(
        name="Demo Bank",
        ats="workday",
        tenant="demo",
        career_url="https://demo.wd3.myworkdayjobs.com/External",
        request_interval=0.1,
        options=options,
    )


def collect(config, handler, monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await WorkdayCollector("demo", config, http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


@pytest.mark.parametrize(
    "facets",
    [
        None,
        [],
        [("country", ["fr"])],
        "country=fr",
        {f"facet{i}": ["a"] for i in range(6)},
        {"": ["a"]},
        {1: ["a"]},
        {b"country": ["a"]},
        {"1country": ["a"]},
        {"country-name": ["a"]},
        {"country.name": ["a"]},
        {"country\n": ["a"]},
        {"écountry": ["a"]},
        {"a" * 65: ["a"]},
        {"country": []},
        {"country": "fr"},
        {"country": ("fr",)},
        {"country": {"fr"}},
        {"country": {"id": "fr"}},
        {"country": [str(i) for i in range(11)]},
        {"country": ["fr", "fr"]},
        {"country": [None]},
        {"country": [True]},
        {"country": [12]},
        {"country": [b"fr"]},
        {"country": [{"id": "fr"}]},
        {"country": [""]},
        {"country": ["  "]},
        {"country": ["a" * 129]},
    ],
)
def test_invalid_facets_are_rejected_without_coercion(facets):
    with pytest.raises(ValueError, match="Workday"):
        WorkdayOptions(applied_facets=facets)


@pytest.mark.parametrize(
    "control", ["\0", "\t", "\n", "\r", "\x1f", "\x7f", "\x85", "\u200b", "\u202e", "\ud800"]
)
def test_facet_identifiers_reject_controls_and_invisible_formatting(control):
    with pytest.raises(ValueError, match="without control characters"):
        WorkdayOptions(applied_facets={"country": [f"fr{control}us"]})


def test_facet_limits_are_inclusive_and_values_remain_exact():
    facets = {
        "a" * 64: ["x" * 128] + [str(i) for i in range(9)],
        "country": ["value shared across facets"],
        "jobFamilyGroup": ["value shared across facets"],
        "facet4": ["Opaque:ID-123"],
        "facet5": ["東京"],
    }
    assert WorkdayOptions(applied_facets=facets).applied_facets == facets


def test_default_facets_are_empty_and_not_shared():
    first, second = WorkdayOptions(), WorkdayOptions()
    first.applied_facets["country"] = ["fr"]
    assert second.applied_facets == {}


def test_facets_are_copied_from_configuration():
    facets = {"country": ["fr"]}
    config = company(applied_facets=facets)
    options = WorkdayOptions(**config.options)
    config.options["applied_facets"]["country"].append("uk")
    assert options.applied_facets == {"country": ["fr"]}
    options.applied_facets["country"].append("us")
    assert config.options["applied_facets"] == {"country": ["fr", "uk"]}


def test_facets_are_sent_on_every_page_and_term(monkeypatch):
    facets = {"country": ["fr", "uk"], "jobFamilyGroup": ["markets"]}
    config = company(applied_facets=facets, search_terms=["repo", "securities finance"])
    original = copy.deepcopy(config.options)
    bodies = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert request.method == "POST", "Excluded listings must not fetch details"
        body = json.loads(request.content)
        bodies.append(body)
        offset = body["offset"]
        rows = [
            {"title": "Trading Operations Analyst", "externalPath": f"/job/London/R{i}"}
            for i in range(offset, min(offset + 20, 23))
        ]
        return httpx.Response(200, json={"total": 23 if offset == 0 else 0, "jobPostings": rows})

    result = collect(config, handler, monkeypatch)
    assert bodies == [
        {"appliedFacets": facets, "limit": 20, "offset": offset, "searchText": term}
        for term in ["repo", "securities finance"]
        for offset in [0, 20]
    ]
    assert config.options == original
    assert result.jobs == [] and result.complete is False


def test_request_body_mutation_does_not_modify_next_request_or_config():
    facets = {"country": ["fr"]}
    config = company(applied_facets=facets, search_terms=["repo", "trading"])

    class MutatingHTTP:
        counts = defaultdict(int)

        async def post_search_json(self, url, body, interval, source):
            assert body["appliedFacets"] == {"country": ["fr"]}
            body["appliedFacets"]["country"].append("injected")
            body["appliedFacets"]["injected"] = ["extra"]
            return {"total": 0, "jobPostings": []}

    collector = WorkdayCollector("demo", config, MutatingHTTP())
    result = asyncio.run(collector.collect())
    assert collector.options.applied_facets == facets == {"country": ["fr"]}
    assert config.options["applied_facets"] == facets
    assert result.jobs == [] and result.complete is False


@pytest.mark.parametrize("facets", [{}, {"country": ["fr"]}])
def test_empty_search_remains_a_partial_inventory(facets, monkeypatch):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert json.loads(request.content)["appliedFacets"] == facets
        return httpx.Response(200, json={"total": 0, "jobPostings": []})

    result = collect(company(applied_facets=facets), handler, monkeypatch)
    assert result.jobs == []
    assert result.complete is False


@pytest.mark.parametrize(
    "payload,error",
    [
        ({"total": 2000, "jobPostings": []}, "result limit"),
        ({"total": 1, "jobPostings": []}, "short"),
        ({"total": -1, "jobPostings": []}, "metadata"),
        ({"jobPostings": []}, "metadata"),
    ],
)
def test_filtered_query_failure_refuses_snapshot(payload, error, monkeypatch):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert json.loads(request.content)["appliedFacets"] == {"country": ["fr"]}
        return httpx.Response(200, json=payload)

    with pytest.raises(SourceUnavailable, match=error):
        collect(company(applied_facets={"country": ["fr"]}), handler, monkeypatch)


def test_filtered_second_query_failure_returns_no_partial_snapshot(monkeypatch):
    details = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method != "POST":
            details.append(request)
            raise AssertionError("All searches must succeed before any detail is fetched")
        body = json.loads(request.content)
        assert body["appliedFacets"] == {"country": ["fr"]}
        if body["searchText"] == "trading":
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "jobPostings": [{"title": "Trading Analyst", "externalPath": "/job/London/R1"}],
                },
            )
        return httpx.Response(200, json={"total": 3, "jobPostings": []})

    with pytest.raises(SourceUnavailable, match="short"):
        collect(
            company(applied_facets={"country": ["fr"]}, search_terms=["trading", "repo"]),
            handler,
            monkeypatch,
        )
    assert details == []
