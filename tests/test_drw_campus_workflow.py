"""Campus evidence must survive preview, local repair and later rescoring."""

import asyncio
from pathlib import Path

from trading_radar.config import Company
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.models import Collection
from trading_radar.normalizer import normalize
from trading_radar.scan_preview import preview_scan
from trading_radar.scoring import score_job


def campus_raw():
    company = Company(name="DRW", ats="greenhouse_filtered", tenant="drweng")
    row = {
        "id": 101,
        "internal_job_id": 201,
        "title": "Floor Trader",
        "company_name": "DRW",
        "absolute_url": "https://job-boards.greenhouse.io/drweng/jobs/101",
        "location": {"name": "Chicago"},
        "content": (
            "<p>Join the trading desk, trade FX and use Python.</p>"
            "<p><strong>What you bring to the team</strong></p><ul><li>"
            "A bachelor's in finance and have an expected graduation date between "
            "December 2026 and June 2027</li></ul>"
        ),
        "metadata": [
            {"name": "Employment Type", "value": "Full-time"},
            {"name": "Target Start Date", "value": "Summer 2027"},
            {"name": "Website Job Category Filter", "value": ["Campus"]},
        ],
        "first_published": "2026-09-16T22:00:00Z",
        "updated_at": "2026-09-16T22:00:00Z",
    }
    return parse_board({"jobs": [row], "meta": {"total": 1}}, "drw", company, GreenhouseOptions())[
        0
    ]


def table_rows(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def test_preview_campus_reclassification_preserves_operator_data(config, repo):
    raw = campus_raw()
    assert raw.seniority_hint == "junior"
    old = score_job(normalize(raw.model_copy(update={"seniority_hint": None})), config.keywords)
    with repo.transaction():
        repo.upsert(old)
        repo.enqueue(old, "new")
    repo.update_application(old.id, {"status": "Reviewing", "notes": "Personal review"})
    baseline = table_rows(repo)
    config.settings.database_url = "sqlite:///" + str(
        Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    )
    config.companies = {"drw": Company(name="DRW", ats="greenhouse_filtered", tenant="drweng")}

    class Replay:
        async def collect(self):
            return Collection(jobs=[raw], complete=False)

    result = asyncio.run(preview_scan(config, collectors={"drw": Replay()}))
    assert result["status"] == "ok"
    assert result["metrics"]["updated"] == 1 and result["metrics"]["alerts"] == 0
    change = result["changes"][0]
    assert change["before_score"] == 79 and change["after_score"] == 94
    assert change["changed_fields"] == ["score_breakdown", "seniority", "seniority_hint"]
    assert table_rows(repo) == baseline


def test_offline_campus_repair_keeps_freshness_and_is_idempotent(config, repo):
    raw = campus_raw()
    old = score_job(normalize(raw.model_copy(update={"seniority_hint": None})), config.keywords)
    with repo.transaction():
        repo.upsert(old)
    repo.update_application(old.id, {"status": "Applied", "notes": "Do not replace"})
    before = table_rows(repo)
    corrected = old.model_copy(deep=True, update={"seniority_hint": raw.seniority_hint})
    corrected = score_job(corrected, config.keywords)
    assert corrected.score_breakdown.total == 94
    with repo.transaction():
        assert repo.update_scoring(corrected)
    stored = repo.get(old.id)
    assert stored.seniority_hint == "junior" and stored.seniority == "junior"
    allowed = {"seniority_hint", "seniority", "score_breakdown"}
    assert {k for k, v in old.model_dump().items() if stored.model_dump()[k] != v} == allowed
    after = table_rows(repo)
    for table in before.keys() - {"jobs", "job_versions", "score_history"}:
        assert before[table] == after[table]
    assert len(after["job_versions"]) == len(before["job_versions"]) + 1
    assert after["job_versions"][-1][3] == "rescored"
    with repo.transaction():
        assert not repo.update_scoring(score_job(stored.model_copy(deep=True), config.keywords))
    assert table_rows(repo) == after
