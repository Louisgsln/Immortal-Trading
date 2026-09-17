import json

from typer.testing import CliRunner

from trading_radar import cli
from trading_radar.models import Score
from trading_radar.normalizer import normalize
from trading_radar.notifications import TelegramNotifier


def tables(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }


def test_qualification_preview_apply_and_repeat_preserve_followup_without_telegram(
    repo, raw, config, tmp_path, monkeypatch
):
    raw.title = "Quant Developer | Trading Strategies | Experienced Hire"
    raw.description = (
        "Bachelor's degree in Computer Science or its foreign equivalent plus 7 years "
        "of progressive experience developing software applications. Relevant technical "
        "experience may substitute for education. Front office trading desk, equities "
        "derivatives, C#, quantitative."
    )
    job = normalize(raw)
    # Persist the pre-correction score to exercise upgrade behavior through the real CLI.
    job.score_breakdown = Score(
        trading=22, junior=5, start=7, front_office=15, asset=10, profile_fit=6
    )
    with repo.transaction():
        repo.upsert(job)
        repo.mark_success("test", 1, 0.1)
    repo.update_application(job.id, {"status": "Applied", "notes": "Preserve this follow-up"})
    before = tables(repo)
    observed_before = repo.get(job.id)
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    config.settings.alerts_enabled = True
    monkeypatch.setattr(cli, "load_config", lambda _: config)
    monkeypatch.chdir(tmp_path)

    def forbidden():
        raise AssertionError("A score recalculation must not initialize Telegram")

    monkeypatch.setattr(TelegramNotifier, "from_env", forbidden)
    runner = CliRunner()
    preview = runner.invoke(cli.app, ["rescore", "--dry-run"])
    assert preview.exit_code == 0, preview.output
    report = json.loads(preview.output)
    assert report["changed"] == report["score_changed"] == 1
    assert report["changes"][0]["before"]["score"] == 65
    assert report["changes"][0]["after"]["score"] == 0
    assert tables(repo) == before
    applied = runner.invoke(cli.app, ["rescore"])
    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.output)["rescored"] == 1
    after = tables(repo)
    for name in before.keys() - {"jobs", "job_versions", "score_history"}:
        assert after[name] == before[name]
    assert len(after["job_versions"]) == len(before["job_versions"]) + 1
    assert len(after["score_history"]) == len(before["score_history"]) + 1
    observed_after = repo.get(job.id)
    assert observed_after.score_breakdown.total == 0
    for field in ("first_seen", "last_seen", "date_updated", "is_active"):
        assert getattr(observed_after, field) == getattr(observed_before, field)
    repeated = runner.invoke(cli.app, ["rescore"])
    assert repeated.exit_code == 0, repeated.output
    assert json.loads(repeated.output)["rescored"] == 0
    assert tables(repo) == after
