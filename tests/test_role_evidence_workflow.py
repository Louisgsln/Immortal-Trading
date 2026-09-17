"""Preview and CLI rescore preserve source evidence and operator data."""

import json
from pathlib import Path

from typer.testing import CliRunner

from trading_radar import scoring
from trading_radar.cli import app
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize

COMPANY_TEXT = (
    "Headquartered in Chicago with offices throughout the U.S., Canada, Europe, and Asia, "
    "we trade a variety of asset classes including Fixed Income, ETFs, Equities, FX, "
    "Commodities and Energy across all major global markets. We have also leveraged our "
    "expertise and technology to expand into three non-traditional strategies: real estate, "
    "venture capital and cryptoassets."
)


def rows(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def test_preview_rescore_and_repeat_keep_evidence_and_operator_data(
    config, repo, monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    raw = RawJob(
        company="DRW",
        source="drw",
        source_type="official",
        external_id="101",
        title="Floor Trader",
        apply_url="https://job-boards.greenhouse.io/drweng/jobs/101",
        description="Work on our trading desk using Python. " + COMPANY_TEXT,
        seniority_hint="junior",
        expected_start_date="Summer 2027",
        employment_type="Full-time",
    )
    with monkeypatch.context() as historical:
        historical.setattr(scoring, "role_evidence_text", lambda job: job.description_text)
        old = scoring.score_job(normalize(raw), config.keywords)
    assert old.score_breakdown.total == 94
    with repo.transaction():
        repo.upsert(old)
        repo.enqueue(old, "new")
    repo.update_application(old.id, {"status": "Reviewing", "notes": "Private review"})
    config.settings.database_url = "sqlite:///" + str(
        Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    )
    monkeypatch.setattr("trading_radar.cli.load_config", lambda directory: config)

    def prohibited():
        raise AssertionError("Rescoring must not construct a notifier")

    monkeypatch.setattr("trading_radar.cli.TelegramNotifier.from_env", prohibited)
    before = rows(repo)
    preview = CliRunner().invoke(app, ["rescore", "--dry-run"])
    assert preview.exit_code == 0, preview.output
    report = json.loads(preview.stdout)
    assert report["changed"] == 1 and report["score_changed"] == 1
    assert report["changes"][0]["after"]["score"] == 82
    assert rows(repo) == before
    result = CliRunner().invoke(app, ["rescore"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["rescored"] == 1
    after = rows(repo)
    for table in before.keys() - {"jobs", "job_versions", "score_history"}:
        assert after[table] == before[table]
    stored = repo.get(old.id)
    assert stored.description == old.description and stored.description_text == old.description_text
    assert stored.last_seen == old.last_seen and stored.date_updated == old.date_updated
    assert stored.seniority_hint == "junior" and stored.score_breakdown.junior == 20
    assert stored.score_breakdown.total == 82 and stored.asset_class == ["UNKNOWN"]
    assert stored.score_breakdown.matched_keywords == ["python"]
    assert len(after["job_versions"]) == len(before["job_versions"]) + 1
    repeat = CliRunner().invoke(app, ["rescore"])
    assert repeat.exit_code == 0 and json.loads(repeat.stdout)["rescored"] == 0
    assert rows(repo) == after
