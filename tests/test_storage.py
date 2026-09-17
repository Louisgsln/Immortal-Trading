import pytest

from trading_radar.normalizer import normalize


def test_idempotent_upsert(repo, job):
    with repo.transaction():
        first, event = repo.upsert(job)
        second, event2 = repo.upsert(job.model_copy(deep=True))
    assert event == "new" and event2 == "unchanged"
    assert first.id == second.id
    assert len(repo.list_jobs()) == 1
    assert repo.db.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("minimum_experience_years", 6),
        ("employment_type", "Internship"),
        ("seniority_hint", "senior"),
        ("role_hint", "trading_technology"),
    ],
)
def test_contract_and_experience_changes_create_a_version(repo, job, field, value):
    with repo.transaction():
        first, _ = repo.upsert(job)
        changed = job.model_copy(deep=True)
        setattr(changed, field, value)
        saved, event = repo.upsert(changed)
        _, repeat = repo.upsert(changed)
    assert saved.id == first.id and event == "updated" and repeat == "unchanged"
    assert getattr(repo.list_jobs()[0], field) == value
    assert repo.db.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0] == 2


def test_cross_source_dedup_prefers_official(repo, raw):
    raw.source_type, raw.source = "aggregator", "board"
    with repo.transaction():
        old, _ = repo.upsert(normalize(raw))
        raw.source_type, raw.source = "official", "official"
        raw.external_id = "official-id"
        job, event = repo.upsert(normalize(raw))
    assert job.id == old.id
    assert job.source == "official"
    assert event == "unchanged"
    assert repo.db.execute("SELECT COUNT(*) FROM job_sources").fetchone()[0] == 2


def test_distinct_requisitions_not_merged(repo, raw):
    with repo.transaction():
        repo.upsert(normalize(raw))
        raw.external_id, raw.apply_url = "different", "https://example.com/jobs/different"
        repo.upsert(normalize(raw))
    assert len(repo.list_jobs()) == 2


def test_distinct_ids_override_shared_generic_url(repo, raw):
    with repo.transaction():
        repo.upsert(normalize(raw))
        raw.external_id = "different"
        repo.upsert(normalize(raw))
    assert len(repo.list_jobs()) == 2


def test_company_scopes_url(repo, raw):
    with repo.transaction():
        repo.upsert(normalize(raw))
        raw.source, raw.company = "another", "Another Company"
        repo.upsert(normalize(raw))
    assert len(repo.list_jobs()) == 2


def test_external_id_namespaced_by_company_within_dataset(repo, raw):
    with repo.transaction():
        repo.upsert(normalize(raw))
        raw.company = "Another Company"
        raw.apply_url = "https://example.com/another-company/job"
        repo.upsert(normalize(raw))
    assert len(repo.list_jobs()) == 2


def test_change_preserves_first_seen(repo, job):
    with repo.transaction():
        repo.upsert(job)
        changed = job.model_copy(deep=True)
        changed.title = "Changed title"
        saved, event = repo.upsert(changed)
    assert event == "updated"
    assert saved.first_seen == job.first_seen
    assert repo.db.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0] == 2


def test_closure_and_reopen(repo, job):
    with repo.transaction():
        repo.upsert(job)
        assert repo.reconcile(job.source, set(), 2) == 0
        assert repo.reconcile(job.source, set(), 2) == 1
    assert not repo.get(job.id).is_active
    with repo.transaction():
        reopened, event = repo.upsert(job.model_copy(deep=True))
    assert reopened.is_active and event == "reopened"


def test_other_active_source_prevents_closure(repo, raw):
    with repo.transaction():
        job, _ = repo.upsert(normalize(raw))
        raw.source = "mirror"
        repo.upsert(normalize(raw))
        repo.reconcile("test", set(), 2)
        assert repo.reconcile("test", set(), 2) == 0
    assert repo.get(job.id).is_active


def test_atomic_rollback(repo, job):
    try:
        with repo.transaction():
            repo.upsert(job)
            raise ValueError("rollback")
    except ValueError:
        pass
    assert not repo.list_jobs()


def test_rescore_preserves_observation_and_alert_state(repo, job):
    with repo.transaction():
        repo.upsert(job)
    old = repo.get(job.id)
    changed = old.model_copy(deep=True)
    changed.score_breakdown.junior = 0
    with repo.transaction():
        assert repo.update_scoring(changed)
        assert not repo.update_scoring(changed)
    saved = repo.get(job.id)
    assert saved.first_seen == old.first_seen and saved.last_seen == old.last_seen
    assert saved.is_new == old.is_new
    assert not repo.pending()
