from datetime import timedelta

import pytest

from trading_radar.models import ExperienceEvidence
from trading_radar.scan_preview import _changes
from trading_radar.scoring import score_job


def snapshot(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def evidence(kind="industry_or_academia", years=5):
    return ExperienceEvidence(
        minimum_years=years,
        kind=kind,
        excerpt=f"{years}+ year track record of solving challenging problems through coding.",
    )


@pytest.mark.parametrize(("kind", "years"), [("industry_or_academia", 5), ("professional", 2)])
def test_correction_preserves_observations_and_application_alert_state(
    repo, job, config, kind, years
):
    job.minimum_experience_years = years
    score_job(job, config.keywords)
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
    repo.update_application(job.id, {"status": "Applied", "notes": "Keep my notes"})
    before = snapshot(repo)
    original = repo.get(job.id)
    corrected = original.model_copy(deep=True)
    corrected.minimum_experience_years = years if kind == "professional" else None
    corrected.experience_evidence = [evidence(kind, years)]
    score_job(corrected, config.keywords)
    with repo.transaction():
        assert repo.update_derived_experience(corrected)
        assert not repo.update_derived_experience(corrected)
    after = snapshot(repo)
    saved = repo.get(job.id)
    allowed = {"minimum_experience_years", "experience_evidence", "score_breakdown"}
    assert all(
        original.model_dump()[key] == value
        for key, value in saved.model_dump().items()
        if key not in allowed
    )
    assert saved.experience_evidence == corrected.experience_evidence
    for table in before.keys() - {"jobs", "job_versions", "score_history"}:
        assert before[table] == after[table]
    for table in ("job_versions", "score_history"):
        assert after[table][:-1] == before[table]
    assert (
        repo.db.execute("SELECT event FROM job_versions ORDER BY id DESC LIMIT 1").fetchone()[0]
        == "rescored"
    )


@pytest.mark.parametrize("field", ["title", "description_text", "source", "last_seen"])
def test_correction_rejects_unrelated_or_stale_source_changes(repo, job, field):
    with repo.transaction():
        repo.upsert(job)
    before = snapshot(repo)
    changed = repo.get(job.id)
    changed.experience_evidence = [evidence()]
    setattr(
        changed, field, changed.last_seen + timedelta(days=1) if field == "last_seen" else "changed"
    )
    with pytest.raises(ValueError, match="unrelated or stale"):
        with repo.transaction():
            repo.update_derived_experience(changed)
    assert snapshot(repo) == before


def test_correction_rolls_back_with_enclosing_transaction(repo, job):
    with repo.transaction():
        repo.upsert(job)
    before = snapshot(repo)
    changed = repo.get(job.id)
    changed.experience_evidence = [evidence()]
    with pytest.raises(RuntimeError):
        with repo.transaction():
            repo.update_derived_experience(changed)
            raise RuntimeError("Abort complete correction")
    assert snapshot(repo) == before


def test_new_collected_evidence_is_versioned_and_named_in_preview(repo, job):
    with repo.transaction():
        saved, _ = repo.upsert(job)
        previous = {saved.id: saved.model_copy(deep=True)}
        start = repo.db.execute("SELECT MAX(id) FROM job_versions").fetchone()[0]
        changed = saved.model_copy(deep=True)
        changed.experience_evidence = [evidence("professional", 2)]
        _, event = repo.upsert(changed)
        assert event == "updated"
        changes = _changes(repo, start, previous)
        assert changes[0]["changed_fields"] == ["experience_evidence"]
        assert repo.upsert(changed)[1] == "unchanged"
