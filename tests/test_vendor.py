import sys
from types import SimpleNamespace

import pytest

from trading_radar.vendor import collect, map_row


class FakeFrame:
    def to_dict(self, orient):
        return [
            {
                "company": "Bank",
                "title": "Trader",
                "ats_id": "1",
                "apply_url": "https://example.com/1",
                "location": float("nan"),
            }
        ]


def test_ats_adapter_contract(monkeypatch):
    calls = []

    def search(**kwargs):
        calls.append(kwargs)
        return FakeFrame()

    monkeypatch.setitem(sys.modules, "ats_scrapers", SimpleNamespace(search=search))
    result = collect(
        "ats_dataset", {"query": "trading", "ats": "greenhouse", "limit": 50}, "dataset"
    )
    assert len(result.jobs) == 1 and not result.complete
    assert result.jobs[0].external_id == "1" and result.jobs[0].location == ""
    assert calls[0]["ats"] == "greenhouse"


def test_jobspy_contract_and_linkedin_block(monkeypatch):
    calls = []

    def scrape_jobs(**kwargs):
        calls.append(kwargs)
        return FakeFrame()

    monkeypatch.setitem(sys.modules, "jobspy", SimpleNamespace(scrape_jobs=scrape_jobs))
    result = collect("jobspy", {"site_name": ["indeed"], "search_term": "trader"}, "board")
    assert not result.complete and calls[0]["verbose"] == 0
    with pytest.raises(ValueError, match="LinkedIn"):
        collect("jobspy", {"site_name": ["linkedin"]}, "board")


def test_vendor_mapper():
    job = map_row(
        {
            "company": "Bank",
            "title": "Trader",
            "job_url": "https://example.com/1",
            "date_posted": "2026-09-15",
        },
        "board",
        False,
    )
    assert job.date_posted.year == 2026
