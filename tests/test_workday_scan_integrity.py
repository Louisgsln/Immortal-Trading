import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

from trading_radar.config import Company
from trading_radar.http import HTTPClient
from trading_radar.scanner import scan
from trading_radar.workday import WorkdayCollector

PROTECTED_TABLES = (
    "jobs",
    "job_sources",
    "job_versions",
    "applications",
    "application_history",
    "alerts",
    "alert_history",
    "score_history",
)


def snapshot(repo):
    return {
        table: [tuple(row) for row in repo.db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
        for table in PROTECTED_TABLES
    }


@pytest.mark.parametrize("fault", ["title", "description", "duplicate_id"])
def test_workday_invalid_second_detail_preserves_snapshot_and_recovers(
    config, repo, job, monkeypatch, fault
):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    config.settings.alerts_enabled = False
    config.companies["test"] = Company(
        name="Demo Bank",
        ats="workday",
        tenant="demo",
        enabled=True,
        career_url="https://demo.wd3.myworkdayjobs.com/en-US/External",
        request_interval=0.1,
    )
    with repo.transaction():
        saved, _ = repo.upsert(job)
        repo.mark_success("test", 1, 0.1)
    repo.update_application(saved.id, {"status": "Applied", "notes": "Keep my follow-up"})
    before = snapshot(repo)
    success_before = repo.state("test")["last_success"]
    search = json.loads(Path("tests/fixtures/workday_search.json").read_text())
    search["jobPostings"][1]["title"] = "Trading Analyst Paris"
    detail = json.loads(Path("tests/fixtures/workday_detail.json").read_text())
    second = copy.deepcopy(detail)
    second["jobPostingInfo"].update(id="second-stable-id", title="Trading Analyst Paris")
    broken = copy.deepcopy(second)
    if fault == "title":
        broken["jobPostingInfo"]["title"] = "Unrelated Analyst"
    elif fault == "description":
        broken["jobPostingInfo"]["jobDescription"] = {"unexpected": "object"}
    else:
        broken["jobPostingInfo"]["id"] = detail["jobPostingInfo"]["id"]
    requested_details = []
    active_second = broken

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            return httpx.Response(200, json=search)
        requested_details.append(request.url.path)
        return httpx.Response(
            200, json=detail if request.url.path.endswith("_R1") else active_second
        )

    async def execute():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            collector = WorkdayCollector("test", config.companies["test"], http)
            return await scan(config, repo, collectors={"test": collector}, http=http)
        finally:
            await http.close()

    failed = asyncio.run(execute())
    assert len(requested_details) == 2  # One valid detail was already read before rejection.
    assert set(failed.failed) == {"test"}
    assert (failed.successful, failed.received, failed.new, failed.updated, failed.closed) == (
        0,
        0,
        0,
        0,
        0,
    )
    assert snapshot(repo) == before
    assert repo.state("test")["last_success"] == success_before
    assert repo.state("test")["consecutive_failures"] == 1
    assert repo.db.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0] == 1

    active_second = second
    recovered = asyncio.run(execute())
    assert not recovered.failed
    assert recovered.received == 2 and recovered.successful == 1
    assert recovered.closed == 0  # A keyword search never closes unseen existing jobs.
    assert repo.get(saved.id).is_active
    assert repo.application(saved.id).notes == "Keep my follow-up"
    assert repo.application(saved.id).status == "Applied"
    assert repo.state("test")["consecutive_failures"] == 0
    assert repo.db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0


def test_empty_facet_scope_does_not_close_previously_observed_jobs(config, repo, job, monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    config.settings.alerts_enabled = False
    config.settings.closure_after_missing_scans = 1
    config.companies["test"] = Company(
        name="Demo Bank",
        ats="workday",
        tenant="demo",
        enabled=True,
        career_url="https://demo.wd3.myworkdayjobs.com/External",
        request_interval=0.1,
        options={"applied_facets": {"jobFamilyGroup": ["observed-public-id"]}},
    )
    with repo.transaction():
        saved, _ = repo.upsert(job)
        repo.mark_success("test", 1, 0.1)
    repo.update_application(saved.id, {"notes": "Follow-up stays outside this search scope"})
    before = snapshot(repo)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert request.method == "POST"
        assert json.loads(request.content)["appliedFacets"] == {
            "jobFamilyGroup": ["observed-public-id"]
        }
        return httpx.Response(200, json={"total": 0, "jobPostings": []})

    async def execute():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await scan(
                config,
                repo,
                collectors={"test": WorkdayCollector("test", config.companies["test"], http)},
                http=http,
            )
        finally:
            await http.close()

    result = asyncio.run(execute())
    assert result.successful == 1 and result.received == result.closed == 0
    assert not result.failed
    assert snapshot(repo) == before
    assert repo.state("test")["last_count"] == 0
    assert repo.get(saved.id).is_active
